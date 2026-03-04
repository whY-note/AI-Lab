from typing import Dict, TypedDict, List, Optional
from langgraph.graph import END, MessageGraph
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain.agents import AgentExecutor, Tool
from langchain.agents.output_parsers import JSONAgentOutputParser
from langchain.agents.format_scratchpad import format_log_to_str
from langchain.tools.render import render_text_description
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain_community.embeddings import DashScopeEmbeddings
from langchain.agents import initialize_agent, AgentType
import os
import random
import json
from pydantic import BaseModel

# 设置API密钥
os.environ["DASHSCOPE_API_KEY"] ="sk-e0bd9dc4ea794204a0b1c3dbacb0a968"
os.environ["TAVILY_API_KEY"]="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"

# 设置游戏角色，按6人的角色配置
ROLES = {
    "Merlin": "好人，知道所有坏人身份但不能被发现",
    "Percival": "好人，知道梅林和莫甘娜的样子，但不知道具体谁是梅林",
    "Loyal Servant1": "好人，不知道其他角色身份",
    "Loyal Servant2": "好人，不知道其他角色身份",
    "Assassin": "坏人，游戏结束时可以刺杀梅林",
    "Morgana": "坏人，伪装成梅林迷惑派西维尔"
}

# 初始化语言模型
llm = ChatOpenAI(
    model="qwen-turbo",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0.7
)

# 初始化DashScope嵌入模型
embeddings = DashScopeEmbeddings(
    model="text-embedding-v1",  # DashScope的嵌入模型
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
)
# 定义工具
def calculate_mission_success_probability(mission_team: List[str]) -> str:
    """计算任务成功概率的工具"""
    good_players = sum(1 for p in mission_team if p in ["Merlin", "Percival", "Loyal Servant1","Loyal Servant2"])
    bad_players = sum(1 for p in mission_team if p in ["Assassin", "Morgana", "Mordred"])
    success_prob = 0.8 - 0.2 * bad_players + 0.1 * good_players
    return f"任务成功概率: {min(max(success_prob, 0), 1):.0%}"

class VotingInput(BaseModel):
    votes: Dict[str, bool]

def analyze_voting_patterns(input: str) -> str:
    """分析投票模式工具"""
    import json
    try:
        votes_data = json.loads(input)
        votes = votes_data.get("votes", [])

        if not votes:
            return "没有投票数据。"

        approvals = [v for v in votes if v["vote"].lower() in ("yes", "approve", "true")]
        opposers = [v for v in votes if v["vote"].lower() in ("no", "reject", "false")]

        result = f"共有 {len(votes)} 名玩家参与投票。\n"
        result += f"赞成人数: {len(approvals)}，反对人数: {len(opposers)}。\n"

        if len(opposers) > len(approvals):
            result += "团队意见分歧较大，可能存在阵营对立。"
        elif len(opposers) == 0:
            result += "全员一致赞成，团队高度一致。"
        else:
            result += "团队中存在部分不信任或怀疑。"

        return result
    except Exception as e:
        return f"投票分析失败: {e}"


# 创建工具集
tools = [
    Tool(
        name="MissionSuccessCalculator",
        func=calculate_mission_success_probability,
        description="计算给定任务团队的成功概率"
    ),
    Tool(
        name="VotingPatternAnalyzer",
        func=analyze_voting_patterns,
        description="分析投票模式以识别潜在行为模式",
    ),
    Tool(
        name="TavilySearch",
        func=TavilySearch(max_results=2),
        description="使用Tavily搜索引擎获取最新信息"
    )
]

# 创建RAG检索工具
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
avalon_rules = """
阿瓦隆游戏规则:
1. 游戏分为好人阵营和坏人阵营
2. 好人包括梅林、派西维尔和2位忠臣
3. 坏人包括刺客和莫甘娜
4. 游戏进行5轮任务，每轮需要组队执行
5. 团队需要投票通过后才能执行任务
6. 坏人可以 sabotage 任务
7. 游戏结束时刺客可以刺杀梅林

各个玩家的能力：
梅林	知道所有坏人（除了莫德雷德，如有）身份，但不能暴露自己
派西维尔	知道“梅林”和“莫甘娜”的两个候选人（无法区分谁是谁）
莫甘娜	冒充梅林，出现在派西维尔面前
刺客	若游戏进入刺杀阶段，有一次刺杀梅林的机会
忠臣	无特殊能力，通过逻辑和行为判断他人身份

胜利条件：
好人阵营胜利条件：
成功完成3次任务，且梅林未被刺杀
坏人阵营胜利条件：
成功破坏3次任务，或成功识破并刺杀梅林

战术建议
对于好人：
梅林需要巧妙引导投票与任务，但不能太明显；
派西维尔需要保护梅林并识破莫甘娜；
忠臣需认真分析行为逻辑、投票模式、发言内容；

对于坏人：
卧底应表现得像好人，避免暴露身份；
投票时制造分歧、引导失败任务；
刺客要利用游戏历史，准确识别梅林。
"""
documents = text_splitter.create_documents([avalon_rules])
vectorstore = FAISS.from_documents(documents, embeddings)  # 使用DashScope嵌入模型
retriever = vectorstore.as_retriever()

def rag_retriever(query: str) -> str:
    """RAG检索工具函数"""
    docs = retriever.get_relevant_documents(query)
    return "\n\n".join(doc.page_content for doc in docs)

tools.append(
    Tool(
        name="AvalonRulesRetriever",  # RAG检索工具
        func=rag_retriever,
        description="检索阿瓦隆游戏规则和策略"
    )
)


# 定义Agent状态
class AgentState(TypedDict):
    messages: List[Dict]
    memory: Dict[str, any]
    current_round: int
    mission_team: List[str]
    votes: Dict[str, bool]
    game_history: List[Dict]


# 定义Agent基础类
class AvalonAgent:
    def __init__(self, name: str, role: str, is_human: bool = False):
        self.name = name
        self.role = role
        self.is_human = is_human
        self.memory_short = ConversationBufferMemory(memory_key="chat_history", return_messages=True)  # 短期记忆
        self.memory_long = ConversationSummaryMemory(llm=llm, memory_key="summary")  # 长期记忆

        # 创建Agent执行器
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = (
                RunnablePassthrough.assign(
                    agent_scratchpad=lambda x: format_log_to_str(x["intermediate_steps"]),
                    chat_history=lambda x: self.memory_short.load_memory_variables({})["chat_history"],
                    summary=lambda x: self.memory_long.load_memory_variables({})["summary"],
                )
                | prompt
                | llm.bind(stop=["\nObservation:"])
                | JSONAgentOutputParser()
        )

        self.executor = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            memory=self.memory_short,
            handle_parsing_errors=True,
            verbose=True
        )

    def _get_system_prompt(self) -> str:
        return f"""
        你现在正在参与阿瓦隆游戏。
        你是一个阿瓦隆游戏中的{self.role}角色。
        你的目标是{'帮助好人阵营完成任务' if self.role in ['Merlin', 'Percival', 'Loyal Servant1','Loyal Servant2'] else '破坏任务并隐藏身份'}。
        你的特殊能力: {ROLES[self.role]}
        游戏当前阶段: {{current_round}}/5轮
        当前任务团队: {{mission_team}}
        已知信息: {{summary}}

        你可以使用以下策略:
        1. ToT (思维树): 当需要复杂决策时，考虑多种可能性
        2. ReAct (推理+行动): 结合推理和工具使用
        3. Reflection: 回顾游戏历史分析其他玩家行为

        请谨慎行动，不要暴露你的身份。
        
        你必须严格遵循以下格式进行回应：

        ---
        Thought: （你的思考过程，简洁明确）
        Action: 工具名称（必须是以下之一：VotingPatternAnalyzer, MissionSuccessCalculator, AvalonRulesRetriever, TavilySearch）
        Action Input: JSON格式的输入，例如：
        {{
          "votes": [{{"player": "Alice", "vote": "yes"}}, ...]
        }}
        
        或者
        
        Final Answer: 你的结论或建议
        ---
        
        绝对不要返回普通散文，请始终包含 Action 或 Final Answer。
        """

    def act(self, state: AgentState) -> Dict:
        if isinstance(state, str):
            state = json.loads(state)
        if self.is_human:
            input_msg = state["messages"][-1]["content"]
            human_input = input(f"{self.name}({self.role}), 请输入你的发言: {input_msg}\n> ")
            return {"messages": [HumanMessage(content=human_input)]}

        # 更新记忆
        for msg in state["messages"]:

            if msg["role"] == "human":
                self.memory_short.chat_memory.add_user_message(str(msg["content"]))
            else:
                self.memory_short.chat_memory.add_ai_message(str(msg["content"]))

        # 准备输入
        last_msg = state["messages"][-1]["content"]
        input_dict = {
            "input": last_msg,
            "votes": state.get("votes", []),
            "current_round": state["current_round"],
            "mission_team": ", ".join(state["mission_team"]),
            "intermediate_steps": []
        }
        # 调用智能体（Agent），根据输入进行决策
        response = self.executor.invoke(input_dict)

        # 更新长期记忆
        self.memory_long.save_context(
            {"input": last_msg},
            {"output": response["output"]}
        )

        return {"messages": [AIMessage(content=response["output"])]}


# 创建游戏模拟器
class AvalonGameSimulator:
    def __init__(self):
        # 初始化5个智能体
        self.agents = [
            AvalonAgent("agent1", "Merlin"),
            AvalonAgent("agent2", "Percival"),
            AvalonAgent("agent3", "Loyal Servant1"),
            AvalonAgent("agent4", "Morgana"),
            AvalonAgent("agent5", "Assassin")
        ]

        # 初始化1个玩家
        self.user = AvalonAgent("玩家", "Loyal Servant2", is_human=True)

        # 初始化游戏状态
        self.game_state = {
            "current_round": 1,
            "mission_team": [],
            "votes": {},
            "game_history": [],
            "good_wins": 0,
            "evil_wins": 0
        }

    def assign_roles(self):
        """随机分配角色"""
        roles = list(ROLES.keys())
        random.shuffle(roles)
        for i, agent in enumerate(self.agents[:4]):
            agent.role = roles[i]
        print("角色分配完成")

    def start_game(self):
        print("阿瓦隆游戏开始!")
        self.assign_roles()

        # 游戏主循环 (5轮任务)
        for round_num in range(1, 6):
            self.game_state["current_round"] = round_num
            print(f"\n=== 第 {round_num} 轮任务 ===")

            # 1. 组队阶段
            self.team_selection_phase()
            # 2. 轮流发言阶段
            self.speaking_phase()
            # 3. 投票阶段
            if not self.voting_phase():
                continue  # 投票未通过，重新组队

            # 4. 任务执行阶段
            self.mission_execution_phase()

            # 检查游戏结束条件
            if self.game_state["good_wins"] >= 3 or self.game_state["evil_wins"] >= 3:
                break

        # 游戏结束，刺客刺杀梅林阶段
        self.assassination_phase()

    def team_selection_phase(self):
        """组队阶段"""
        print("\n[组队阶段]")
        team_size = self.get_team_size()
        print(f"需要选择 {team_size} 名玩家组成任务团队")

        # 简单的AI组队逻辑 - 实际中可以更复杂
        candidates = [agent.name for agent in self.agents] + [self.user.name]
        self.game_state["mission_team"] = random.sample(candidates, team_size)

        print(f"任务团队已组成: {', '.join(self.game_state['mission_team'])}")

        # 通知所有玩家
        message = f"第 {self.game_state['current_round']} 轮任务团队: {', '.join(self.game_state['mission_team'])}"
        self.broadcast_message(message)

    def speaking_phase(self):
        self.broadcast_message("现在进入轮流发言阶段，请按顺序发表对局势的看法")
        all_players = self.agents + [self.user]
        for i, player in enumerate(all_players):
            # 通知当前玩家发言
            if player.is_human:
                # 人类玩家输入发言
                print(f"\n{player.name}({player.role})，请发言（{i + 1}/{len(all_players)}）")
                print("请分析当前局势，推测好人坏人身份")
                speech = input("你的发言内容: ")
            else:
                # AI玩家自动生成发言
                response = player.act({
                    "messages": [{
                        "role": "system",
                        "content": f"请发言（{i + 1}/{len(all_players)}），分析当前局势，推测好人坏人"
                    }],
                    "current_round": self.game_state["current_round"],
                    "mission_team": self.game_state["mission_team"],
                    "votes": self.game_state.get("votes", {}),
                    "game_history": self.game_state["game_history"]
                })
                speech = response["messages"][0].content
                print(f"\n{player.name}({player.role}) 发言: {speech}")

            # 广播该玩家的发言给所有人
            self.broadcast_message({
                "type": "speech",
                "player": player.name,
                "content": response["messages"][0].content,
                "to": "all"
            })

            # 记录发言到游戏历史
            self.game_state["game_history"].append({
                "round": self.game_state["current_round"],
                "phase": "speaking",
                "player": player.name,
                "content": speech
            })
    def voting_phase(self) -> bool:
        """投票阶段，返回是否通过"""
        print("\n[投票阶段]")
        self.game_state["votes"] = {}

        # 收集所有玩家投票
        for agent in self.agents + [self.user]:
            if agent.is_human:
                vote = input(f"{agent.name}, 你是否赞成当前任务团队? (y/n): ")
                self.game_state["votes"][agent.name] = vote.lower() == 'y'
            else:
                # AI根据角色和游戏历史决定投票
                reasoning = ("作为好人，我信任这个团队" if agent.role in ["Merlin", "Percival", "Loyal Servant1","Loyal Servant2"]
                             else "作为坏人，我需要让团队看起来可疑")
                vote = random.random() > 0.3 if agent.role in ["Merlin", "Percival",
                                                               "Loyal Servant"] else random.random() > 0.7
                self.game_state["votes"][agent.name] = vote
                print(f"{agent.name}({agent.role}) 投票: {'赞成' if vote else '反对'} - {reasoning}")

        # 计算投票结果
        approvals = sum(self.game_state["votes"].values())
        total_votes = len(self.game_state["votes"])
        passed = approvals > total_votes / 2

        print(f"投票结果: {approvals}赞成/{total_votes}")
        self.broadcast_message(f"任务团队投票结果：{approvals}/{total_votes} 人支持。")

        # 记录游戏历史
        self.game_state["game_history"].append({
            "round": self.game_state["current_round"],
            "mission_team": self.game_state["mission_team"],
            "votes": self.game_state["votes"],
            "passed": passed,
            "result": None
        })

        return passed

    def mission_execution_phase(self):
        """任务执行阶段"""
        print("\n[任务执行阶段]")

        # 简单模拟任务成功/失败
        good_players = sum(1 for p in self.game_state["mission_team"]
                           if any(a.role in ["Merlin", "Percival", "Loyal Servant1","Loyal Servant2"]
                                  for a in self.agents + [self.user] if a.name == p))
        bad_players = len(self.game_state["mission_team"]) - good_players

        # 坏人可以选择破坏任务
        sabotage = False
        for agent in self.agents:
            if agent.name in self.game_state["mission_team"] and agent.role in ["Assassin", "Morgana"]:
                if random.random() > 0.5:  # 50%几率破坏
                    sabotage = True
                    print(f"{agent.name}({agent.role}) 选择破坏任务")
                    break

        # 决定任务结果 (需要至少一次破坏才会失败)
        success = not sabotage
        if success:
            self.game_state["good_wins"] += 1
            print("任务成功! 好人阵营得1分")
        else:
            self.game_state["evil_wins"] += 1
            print("任务失败! 坏人阵营得1分")

        # 更新游戏历史
        self.game_state["game_history"][-1]["result"] = "成功" if success else "失败"
        self.broadcast_message(f"任务结果: {'成功' if success else '失败'}")

        print(f"当前比分: 好人 {self.game_state['good_wins']} - 坏人 {self.game_state['evil_wins']}")

    def assassination_phase(self):
        """刺客刺杀梅林阶段"""
        print("\n[游戏结束，刺客刺杀梅林阶段]")

        # 找出刺客和梅林
        assassin = next(a for a in self.agents if a.role == "Assassin")
        merlin = next(a for a in self.agents if a.role == "Merlin")

        # 刺客猜测梅林
        print(f"{assassin.name}(刺客) 正在尝试识别梅林...")
        candidates = [a.name for a in self.agents if a.role != "Assassin"] + [self.user.name]
        guess = random.choice(candidates)

        if guess == merlin.name:
            print(f"刺客成功刺杀了梅林! 坏人阵营获胜!")
        else:
            print(f"刺客错误刺杀了 {guess} (真正的梅林是 {merlin.name})! 好人阵营获胜!")

    def broadcast_message(self, message: str | dict):
        """向所有玩家发送消息（message 应为字符串或可转字符串的内容）"""
        # 将 dict 类型消息格式化为字符串，确保 content 为字符串类型
        if isinstance(message, dict):
            if "player" in message and "content" in message:
                message_str = f"{message['player']} 发言：{message['content']}"
            else:
                message_str = json.dumps(message, ensure_ascii=False)
        else:
            message_str = str(message)

        # votes 格式标准化
        votes_data = {
            "votes": [
                {"player": name, "vote": "yes" if (
                    vote if isinstance(vote, bool) else vote.lower() in ['y', 'yes', 'true', '赞成']) else "no"}
                for name, vote in self.game_state["votes"].items()
            ]

        }

        # 构造传入 agent 的状态字典
        state = {
            "messages": [{"role": "system", "content": message_str}],
            "current_round": self.game_state["current_round"],
            "mission_team": self.game_state["mission_team"],
            "votes": votes_data,
            "game_history": self.game_state["game_history"]
        }

        # 向所有 Agent 广播
        for agent in self.agents + [self.user]:
            agent.act(state)

    # def broadcast_message(self, message: str):
    #     """向所有玩家发送消息"""
    #     for agent in self.agents + [self.user]:
    #         # if agent.is_human:
    #         #     print(f" {message}")
    #         # else:
    #         #     # 对于AI玩家，直接记录消息而不调用工具
    #         #     agent.memory_short.chat_memory.add_message(HumanMessage(content=message))
    #
    #         # votes_data = {
    #         #     "votes": {name: bool(vote) for name, vote in self.game_state["votes"].items()}
    #         # } if self.game_state.get("votes") else {"votes": {}}
    #
    #         votes_data = {
    #             "votes": {
    #                 name: vote if isinstance(vote, bool) else vote.lower() == "y"
    #                 for name, vote in self.game_state["votes"].items()
    #             }
    #         }
    #
    #         # 创建消息字典，确保content是字符串
    #         message_dict = {
    #             "messages": [{
    #                 "role": "system",
    #                 "content": str(message)  # 确保content是字符串
    #             }],
    #             "current_round": self.game_state["current_round"],
    #             "mission_team": self.game_state["mission_team"],
    #             "votes": votes_data,
    #             "game_history": self.game_state["game_history"]
    #         }
    #         agent.act(json.dumps({
    #             "messages": [{"role": "system", "content": message}],
    #             "current_round": self.game_state["current_round"],
    #             "mission_team": self.game_state["mission_team"],
    #             "votes": votes_data, #self.game_state["votes"],
    #             "game_history": self.game_state["game_history"]
    #         },ensure_ascii=False))


    def get_team_size(self) -> int:
        """根据回合返回需要的团队人数"""
        return [2, 3, 3, 4, 4][self.game_state["current_round"] - 1]


# 运行游戏
if __name__ == "__main__":
    game = AvalonGameSimulator()
    game.start_game()