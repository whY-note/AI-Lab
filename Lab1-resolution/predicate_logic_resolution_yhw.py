'''
Predicate Logic Resolution,谓词逻辑推理
'''
variable_set = {'u', 'v', 'w', 'x', 'y', 'z', 'uu', 'vv', 'ww', 'xx', 'yy', 'zz'}  # 变量集

def split_arg(args_str):
    stack = []
    args_list = []
    curr_arg_str = []
    for c in args_str:
        if c == ',' and len(stack) == 0:
            args_list.append(''.join(curr_arg_str))
            curr_arg_str = []
        else:
            curr_arg_str.append(c)
            if c == '(':
                stack.append('(')
            elif c == ')' and stack:
                stack.pop()


class Literal():
    # 文字类
    def __init__(self, literal):
        predicate_end = literal.index('(')
        self.args_list = literal[predicate_end + 1:-1].split(',')
        if literal[0] == '~':
            self.negative = True
            self.predicate = literal[1:predicate_end]
        else:
            self.negative = False
            self.predicate = literal[0:predicate_end]

def isComplement(literal1, literal2):
    if literal1.predicate == literal2.predicate and literal1.negative != literal2.negative:
        return True
    return False

def unify(args_list1, args_list2):
    subs_map = {}  # 变量与常量映射表
    while True:
        for arg1, arg2 in zip(args_list1, args_list2):
            if arg1 not in variable_set and arg2 not in variable_set and arg1 != arg2:
                return None
            elif arg1 in variable_set and arg2 not in variable_set:
                subs_map[arg1] = arg2
                break
            elif arg1 not in variable_set and arg2 in variable_set:
                subs_map[arg2] = arg1
                break
            elif arg1 in variable_set and arg2 in variable_set:
                return None
        # 合一
        args_list1 = [subs_map[item] if item in subs_map else item for item in args_list1]
        args_list2 = [subs_map[item] if item in subs_map else item for item in args_list2]
        if args_list1 == args_list2:
            break
    return subs_map


# 得到题目要求的归结编号
def Index(literal_index, clause_index, length):
    if length == 1:  # 如果子句只有一个元素，则文字索引不再需要
        index = str(clause_index + 1)
    else:  # 否则将文字索引变为字母
        index = str(clause_index + 1) + chr(ord('a') + literal_index)
    return index


# 得到归结式
def Sequence(new_clause, subs_map, index1, index2):
    string = ''
    if subs_map == {}:  # 如果字典为空，说明不需要输出合一
        string += 'R[' + index1 + ',' + index2 + '] = '
    else:
        string += 'R[' + index1 + ',' + index2 + ']{'
        for key, value in subs_map.items():
            string += key + '=' + value + ','
        string = string[:-1]
        string += '} = '
    string += str(new_clause)
    return string


# 代入常量
def substitute_const(literal, subs_map):
    perdicate_end = literal.index('(')
    args = literal[perdicate_end + 1:-1].split(',')
    substituted = [subs_map.get(arg, arg) for arg in args]
    return f"{literal[:perdicate_end + 1]}{','.join(substituted)})"


def Refutation(KB):
    KB = list(KB)
    clause_set = KB  # 拷贝一份，防止更改原初始子句集
    support_set = [KB[-1]]  # 支持集，默认KB最后一个元素是目标子句的否定
    result = ['Result:'] + KB  # 将0位置补充元素，确保编号和列表索引对应

    while True:
        new_clause_set = []  # 保存新的子句
        clause_id1 = 0
        for clause1 in clause_set:
            clause_id2 = 0
            for clause2 in clause_set:
                if clause1 != clause2 and clause2 in support_set:
                    # 查找互补的文字
                    literal_id1 = 0
                    for literal1 in clause1:
                        literal_id2 = 0
                        for literal2 in clause2:
                            l1 = Literal(literal1)
                            l2 = Literal(literal2)

                            if isComplement(l1, l2):
                                # 合一置换
                                subs_map = unify(l1.args_list, l2.args_list)
                                if subs_map == None:
                                    continue
                                # 代入
                                new_literals_list = []
                                for literal in clause1:
                                    if literal != literal1:
                                        new_literal = substitute_const(literal, subs_map)
                                        new_literals_list.append(new_literal)
                                for literal in clause2:
                                    if literal != literal2:
                                        new_literal = substitute_const(literal, subs_map)
                                        new_literals_list.append(new_literal)
                                new_clause = tuple(set(new_literals_list))

                                # 归结子句存在于原子句集则退出
                                if any([set(new_clause) == (set(item)) for item in clause_set]):
                                    break
                                # 归结子句存在于新子句集则退出
                                if any([set(new_clause) == (set(item)) for item in new_clause_set]):
                                    break

                                # 得到索引
                                index1 = Index(literal_id1, clause_id1, len(clause1))
                                index2 = Index(literal_id2, clause_id2, len(clause2))

                                sequence = Sequence(new_clause, subs_map, index1, index2)

                                result.append(sequence)
                                new_clause_set.append(new_clause)

                                if new_clause == ():
                                    return result
                            literal_id2 += 1
                        literal_id1 += 1
                clause_id2 += 1
            clause_id1 += 1
        clause_set += new_clause_set
        support_set += new_clause_set


# 得到归结式的子句索引
def get_num(clause):
    start = clause.find('[')
    end = clause.find(']')
    number = clause[start + 1:end].split(',')
    # 将文字索引去掉
    num1 = int(''.join(item for item in number[0] if not item.isalpha()))
    num2 = int(''.join(item for item in number[1] if not item.isalpha()))
    return num1, num2


# 得到新归结式的子句索引
def Renumber(num, result, useful_process, size):
    if num <= size:  # 如果是初始子句集的，直接返回
        return num
    # 找到亲本子句
    sequence = result[num]
    begin = sequence.find('(')
    aim_clause = sequence[begin:]
    # 找到亲本子句在化简子句集的编号
    for i in range(size + 1, len(useful_process)):
        begin = useful_process[i].find('(')
        if useful_process[i][begin:] == aim_clause:
            return i


def Resequence(sequence, num1, num2, newnum1, newnum2):
    # 替换第一个编号
    start = sequence.find(num1)
    end = start + len(num1)
    sequence = sequence[:start] + newnum1 + sequence[end:]
    # 替换第二个编号
    end = start + len(newnum1)
    start = sequence.find(num2, end)
    end = start + len(num2)
    sequence = sequence[:start] + newnum2 + sequence[end:]
    return sequence


# 化简归结过程
def simplify(result, size):
    base_process = result[0:size + 1]  # 初始子句集
    useful_process = []  # 有用子句集
    number = [len(result) - 1]  # 用作队列，先将空子句的索引入列
    while number != []:
        number0 = number.pop(0)  # 提取队列首元素，即有用子句的索引
        if not result[number0] in useful_process:
            useful_process.append(result[number0])  # 将有用子句加入到有用子句集
            num1, num2 = get_num(result[number0])  # 得有用子句用到的亲本子句索引
            # 如果是初始子句集就无需加入
            if num1 > size:
                number.append(num1)
            if num2 > size:
                number.append(num2)
    # 得到新的归结过程
    useful_process.reverse()
    useful_process = base_process + useful_process
    # 将归结过程重新编号
    for i in range(size + 1, len(useful_process)):
        num1, num2 = get_num(useful_process[i])
        newnum1 = str(Renumber(num1, result, useful_process, size))
        newnum2 = str(Renumber(num2, result, useful_process, size))
        useful_process[i] = Resequence(useful_process[i], str(num1), str(num2), newnum1, newnum2)
    return useful_process


# 打印结果
def Print(result):
    print(result[0])
    for i in range(1, len(result)):
        print(i, result[i])


# 归结反演
def ResolutionFOL(KB):
    result = Refutation(KB)
    new_result = simplify(result, len(KB))
    Print(new_result)


KB1 = {('A(tony)',), ('A(mike)',), ('A(john)',), ('L(tony,rain)',), ('L(tony,snow)',),
       ('~A(x)', 'S(x)', 'C(x)'), ('~C(y)', '~L(y,rain)'), ('L(z,snow)', '~S(z)'),
       ('~L(tony,u)', '~L(mike,u)'), ('L(tony,v)', 'L(mike,v)'), ('~A(w)', '~C(w)', 'S(w)')}
ResolutionFOL(KB1)

KB2 = {('On(tony,mike)',), ('On(mike,john)',), ('Green(tony)',), ('~Green(john)',),
       ('~On(xx,yy)', '~Green(xx)', 'Green(yy)')}
ResolutionFOL(KB2)
