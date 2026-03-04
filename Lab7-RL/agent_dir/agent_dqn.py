import os
import random
import numpy as np
import torch
from tensorboardX import SummaryWriter
from torch import nn, optim
from agent_dir.agent import Agent
from collections import deque

class QNetwork(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(QNetwork, self).__init__()
        # 网络结构
        self.net = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.LayerNorm(hidden_size),  # 添加层归一化
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.LayerNorm(hidden_size),# 添加层归一化
            nn.Linear(hidden_size, output_size)
        )

    def forward(self, inputs):
        return self.net(inputs)


class ReplayBuffer:
    # 回放缓冲区
    def __init__(self, buffer_size):
        self.buffer=deque(maxlen=buffer_size)

    def __len__(self):
        return len(self.buffer)

    def push(self, *transition):
        self.buffer.append(transition)

    def sample(self, batch_size):
        '''
        choose sample from buffer randomly
        :param batch_size: the number of sample per batch
        :return: sample
        '''
        # choose sample randomly
        transitions = random.sample(self.buffer, batch_size)
        # get all values
        state, action, reward, next_state, done = zip(*transitions)
        return np.array(state), action, reward, np.array(next_state), done

    def clean(self):
        # clean the buffer
        self.buffer.clear()


class AgentDQN(Agent):
    # DGN智能体
    def __init__(self, env, args):
        super(AgentDQN, self).__init__(env)
        self.args=args
        # 设备配置（优先使用GPU）
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # 创建唯一的日志目录，避免不同训练任务的数据混淆
        self.log_dir = self._create_unique_log_dir()
        self.writer = SummaryWriter(log_dir=self.log_dir)  # TensorBoard日志记录器

        # set arguments
        self.batch_size=args.batch_size
        self.lr=args.lr
        self.gamma=args.gamma
        self.epsilon= 0.02
        self.min_epsilon = args.min_epsilon
        self.num_episodes = args.num_episodes  # 训练总 episodes 数
        self.minimal_size = args.minimal_size  # 最小训练样本数
        self.target_update=args.target_update

        # 设置随机种子
        random.seed(args.seed)
        np.random.seed(args.seed)
        self.env.reset(seed=args.seed)
        torch.manual_seed(args.seed)

        # 网络维度设置
        self.hidden_dim = args.hidden_size  # 隐藏层维度
        self.state_dim = self.env.observation_space.shape[0]  # 状态空间维度
        self.action_dim = self.env.action_space.n  # 动作空间维度
        # 初始化评估网络和目标网络
        self.q_net = QNetwork(self.state_dim, self.hidden_dim, self.action_dim).to(self.device)
        self.target_q_net = QNetwork(self.state_dim, self.hidden_dim, self.action_dim).to(self.device)
        self.optimizer = optim.Adam(self.q_net.parameters(), lr=self.lr)  # 优化器
        self.tau = 0.01  # 软更新系数，控制目标网络更新速度

        self.count=0
        self.replay_buffer = ReplayBuffer(args.buffer_size)  # 经验回放缓冲
        self.return_list = []  # 存储每轮回报

    def _create_unique_log_dir(self):
        # 创建唯一的日志目录，使用6位随机字符串标识
        random_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
        log_dir = f"./logs/dqn_{random_id}"
        os.makedirs(log_dir, exist_ok=True)
        return log_dir

    def init_game_setting(self):
        pass

    def train(self):
        for i in range(10):
            for episode in range(self.num_episodes//10):
                # 初始化本轮的回报
                episode_return=0

                # 重置环境（兼容新旧Gym版本）
                reset_result = self.env.reset()
                # 处理不同版本的返回结果
                if isinstance(reset_result, tuple) and len(reset_result) == 2:
                    # 新版本Gym (0.26+): (observation, info)
                    observation = reset_result[0]
                else:
                    # 旧版本Gym: 直接返回observation
                    observation = reset_result

                # 确保观测值是正确的一维数组
                if not isinstance(observation, np.ndarray):
                    observation = np.array(observation, dtype=np.float32)
                if len(observation.shape) > 1:
                    observation = observation.flatten()

                while True:
                    # 根据当前状态选动作
                    action =self.make_action(observation)

                    # 执行动作
                    step_result=self.env.step(action)
                    if len(step_result) == 4:
                        # 旧版本: observation, reward, done, info
                        next_observation, reward, done, _ = step_result
                        truncated = False
                    elif len(step_result) == 5:
                        # 新版本: observation, reward, done, truncated, info
                        next_observation, reward, done, truncated, info = step_result
                    else:
                        # 默认处理
                        next_observation, reward, done, truncated = step_result[0], step_result[1], step_result[
                            2], False

                    # 确保next_observation是正确格式，即一维数组
                    if not isinstance(next_observation, np.ndarray):
                        next_observation = np.array(next_observation, dtype=np.float32)
                    if len(next_observation.shape) > 1:
                        next_observation = next_observation.flatten()

                    # 合并done和truncated（新版本特性）
                    is_done = done or truncated

                    # 将样本存入经验回放缓冲区
                    self.replay_buffer.push(observation, action, reward, next_observation, is_done)

                    # 当缓冲区样本数足够时开始训练
                    if len(self.replay_buffer) > self.minimal_size:
                        # 从缓冲区采样mini-batch
                        states, actions, rewards, next_states, dones = self.replay_buffer.sample(self.batch_size)
                        # 数据类型转换并加载到指定设备
                        states = torch.FloatTensor(states).to(self.device)
                        actions = torch.LongTensor(actions).view(-1, 1).to(self.device)

                        rewards = [r if not d else -10 for r, d in zip(rewards, dones)]  # 失败时增加惩罚
                        rewards = torch.FloatTensor(rewards).view(-1, 1).to(self.device)
                        next_states = torch.FloatTensor(next_states).to(self.device)
                        dones = torch.FloatTensor(dones).view(-1, 1).to(self.device)

                        # 计算当前状态-动作的Q值
                        q_values = self.q_net(states).gather(1, actions)
                        # 计算下一状态的最大Q值（使用目标网络）
                        max_next_q_values = self.target_q_net(next_states).max(1)[0].view(-1, 1).detach()

                        # 计算TD目标值
                        q_targets = rewards + self.gamma * max_next_q_values * (1 - dones)
                        # 计算损失（均方误差）
                        loss = torch.mean(torch.nn.functional.mse_loss(q_values, q_targets))

                        # 优化器梯度清零
                        self.optimizer.zero_grad()
                        # 反向传播计算梯度
                        loss.backward()
                        # 添加梯度裁剪 (防止梯度爆炸)
                        torch.nn.utils.clip_grad_norm_(self.q_net.parameters(), max_norm=10)
                        # 更新网络参数
                        self.optimizer.step()

                        # 定期更新目标网络（硬更新）
                        if self.count % self.target_update == 0:
                            self.target_q_net.load_state_dict(self.q_net.state_dict())

                        self.count += 1  # 更新计数器
                        # 更新探索率（设置下限防止完全失去探索能力）
                        self.epsilon = max(self.epsilon * 0.995, 0.01)

                    observation=next_observation  # 更新状态
                    episode_return+=reward  # 累加收益

                    if done or truncated:
                        break

                # 记录本轮回报
                self.return_list.append(episode_return)
                # 写入TensorBoard日志
                self.writer.add_scalar('Reward/Episode', episode_return, len(self.return_list))

                # 每10轮episode输出一次平均回报
                if (episode + 1) % 10 == 0:
                    avg_return = np.mean(self.return_list[-10:])
                    print(
                        f"Episode {episode + 1:04d}, Average Return: {avg_return:.2f}, Epsilon: {self.epsilon:.3f}")

    def make_action(self, observation, test=True):
        """
        根据当前状态选择动作 ，这里使用ε-贪婪策略
        Return predicted action of your agent
        Input:observation
        Return:action
        """
        # 确保observation是正确格式
        if not isinstance(observation, np.ndarray):
            observation = np.array(observation, dtype=np.float32)
        if len(observation.shape) > 1:
            observation = observation.flatten()

        if not test or np.random.random() < self.epsilon:
            # 探索：随机选择动作
            action = np.random.randint(self.action_dim)
        else:
            # 利用：选择Q值最大的动作
            with torch.no_grad():  # 测试时不需要计算梯度
                # 转换为张量并添加批次维度
                observation_tensor = torch.FloatTensor(observation).unsqueeze(0).to(self.device)
                q_values = self.q_net(observation_tensor)
                action = q_values.argmax().item()
        return action


    def run(self):
        self.train()
        print(self.log_dir)
