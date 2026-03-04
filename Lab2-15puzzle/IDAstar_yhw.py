import time

class IDA_star:
    def __init__(self,init_state,end_state,hn_mod=0):
        '''

        :param init_state: 初始状态 (1维元组)
        :param end_state: 目标状态 (1维元组)
        :param hn_mod:
        0:曼哈顿距离
        1:曼哈顿距离+线性冲突
        2:不在目标位置上的数量
        '''
        self.init_state=init_state
        self.end_state=end_state
        self.size=(4,4)
        self.hn_mod=hn_mod

        # 移动方向
        self.directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # 上,下,左,右

        self.target_pos = self.precompute_target_positions()  # 预计算目标位置
        self.linear_conflict_cache = {}  # 线性冲突缓存

    def precompute_target_positions(self):
        """预计算每个数字的目标坐标"""
        pos_dict = {}
        for i in range(len(self.end_state)):
            num = self.end_state[i]
            if num != 0:
                pos_dict[num] = divmod(i, 4)
        return pos_dict

    def find_zero(self,state):
        """获取0的位置"""
        return divmod(state.index(0),4)

    def is_solvable(self,initial_state):
        """
        判断 15 拼图初始状态是否可解。
        :param initial_state: 二维列表表示的初始状态。
        :return: True（可解）/False（不可解）。
        """
        zero_i, zero_j = self.find_zero(initial_state)
        target_zero_i = len(initial_state) - 1
        # 计算行差
        row_diff = target_zero_i - zero_i
        # 计算逆序数
        flat = []
        for num in initial_state:
            if num != 0:
                flat.append(num)

        inv_count = 0
        for i in range(len(flat)):
            for j in range(i + 1, len(flat)):
                if flat[i] > flat[j]:
                    inv_count += 1

        return (inv_count + row_diff) % 2 == 0

    def generate_moves(self,state):
        """生成新状态"""
        moves=[]
        zero_row,zero_col=self.find_zero(state)

        for d_row,d_col in self.directions:
            new_row=zero_row+d_row
            new_col=zero_col+d_col
            if 0<=new_row<=self.size[0]-1 and 0<=new_col<=self.size[1]-1:
                # 不使用深拷贝，直接交换元素，减少拷贝的时间
                new_state=list(state)
                zero_pos_1d=zero_row*self.size[0]+zero_col
                new_zero_pos_1d=new_row*self.size[0]+new_col
                new_state[new_zero_pos_1d],new_state[zero_pos_1d]=new_state[zero_pos_1d],new_state[new_zero_pos_1d]
                
                new_state=tuple(new_state) # 转换回元组
                moves.append((new_state,(new_row,new_col)))
        return moves

    '''--------------------启发函数--------------------'''
    def cal_misplaced(self,state):
        # 不在最终位置上的数量
        num_misplaced=0
        for i in range(len(end_state)):
            if state[i]!=self.end_state[i]:
                num_misplaced+=1
        return num_misplaced

    def cal_manhattan(self, state):
        # 曼哈顿距离
        dist = 0
        for idx in range(len(state)):
            if state[idx] == 0:
                continue
            target = self.target_pos[state[idx]]  # 获取目标位置
            curr_row, curr_col = idx // self.size[1], idx % self.size[1]  # 获取当前位置
            dist += abs(target[0] - curr_row) + abs(target[1] - curr_col)
        return dist

    def cal_linear_conflict(self, state):
        """线性冲突优化"""
        # 线性冲突检测
        if state in self.linear_conflict_cache:
            return self.linear_conflict_cache[state]

        conflict = 0
        # 行冲突检测
        for row in range(4):
            tiles = [state[i] for i in range(row * 4, (row + 1) * 4) if state[i] != 0]
            for i in range(len(tiles)):
                for j in range(i + 1, len(tiles)):
                    ti, tj = tiles[i], tiles[j]
                    if (ti - 1) // 4 == row and (tj - 1) // 4 == row and ti > tj:
                        conflict += 2
        # 列冲突检测
        for col in range(4):
            tiles = [state[col + row * 4] for row in range(4) if state[col + row * 4] != 0]
            for i in range(len(tiles)):
                for j in range(i + 1, len(tiles)):
                    ti, tj = tiles[i], tiles[j]
                    if (ti - 1) % 4 == col and (tj - 1) % 4 == col and ti > tj:
                        conflict += 2
        self.linear_conflict_cache[state] = conflict

        return conflict

    def cal_hn(self, state):
        # 计算启发函数值h(n)
        if self.hn_mod == 1:
            # 使用曼哈顿距离+线性冲突
            return self.cal_manhattan(state) + self.cal_linear_conflict(state)
        elif self.hn_mod == 2:
            # 使用不在目标位置上的数量
            return self.cal_misplaced(state)
        else:
            # 默认使用曼哈顿距离
            return self.cal_manhattan(state)

    '''--------------------递归搜索--------------------'''
    def IDAstar_search(self,gn):
        curr_state=self.path[-1]
        fn=gn+self.cal_hn(curr_state)
        if fn>self.bound:
            return fn
        if curr_state==self.end_state:
            return "FOUND"

        min_cost=float('inf')
        for new_state,new_zero_pos in self.generate_moves(curr_state):
            if new_state in self.visited:
                continue
                
            self.path.append(new_state)
            self.visited.add(new_state)

            result=self.IDAstar_search(gn + 1)
            if result=="FOUND":
                return "FOUND"
            elif result<min_cost:
                min_cost=result

            self.path.pop()
            self.visited.remove(new_state)
        return min_cost

    '''--------------------IDA*算法主函数--------------------'''
    def solve(self):
        if self.is_solvable(self.init_state) == False:
            # 无解
            print("无解!")
            return False

        self.visited={self.init_state}
        self.path = [self.init_state]
        self.bound=self.cal_hn(self.init_state)

        while True:
            result=self.IDAstar_search(gn=0)
            if result=="FOUND":
                return self.path
            elif result==float('inf'):
                print("无解!")
                return None

            # 更新
            self.bound=result
            self.visited = {self.init_state}
            self.path = [self.init_state]


if __name__=="__main__":
    end_state=(1,2,3,4,
               5,6,7,8,
               9,10,11,12,
               13,14,15,0)
    init_state_dict=\
        {
         '1':(1,2,4,8,
              5,7,11,10,
              13,15,0,3,
              14,6,9,12),
         '2':(14,10,6,0,
              4,9,1,8,
              2,3,5,11,
              12,13,7,15),
         '3':(5,1,3,4,
              2,7,8,12,
              9,6,11,15,
              0,13,10,14),
         '4':(6,10,3,15,
              14,8,7,11,
              5,1,0,2,
              13,12,9,4),
         '5':(11,3,1,7,
              4,6,8,2,
              15,9,10,13,
              14,12,5,0),
         '6':(0,5,15,14,
              7,9,6,13,
              1,2,12,10,
              8,11,4,3)
        }
    for i in init_state_dict:
        init_state=init_state_dict[i]
        print(f"Problem {i}")
        start_time=time.perf_counter()

        solver=IDA_star(init_state=init_state,end_state=end_state,
                      hn_mod=1)

        solution=solver.solve()

        end_time=time.perf_counter()

        step_num=0
        for solutioin_step in solution:
            if step_num==0:
                print("initial state:")
            else:
                print(f"Step {step_num}")

            # 格式化输出
            for i in range(len(solutioin_step)):
                print(f"{solutioin_step[i]:-3d}",end="")
                if i%4==3:
                    print()
            step_num+=1
            print()
        print(f"总步骤数：{step_num-1}")
        print(f"用时：{end_time - start_time}s\n")




