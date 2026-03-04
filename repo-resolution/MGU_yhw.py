def split_args(args_str):
    stack=[]
    args_list=[]
    curr_arg_str=[]
    for c in args_str:
        if c==',' and len(stack)==0:
            args_list.append(''.join(curr_arg_str))
            curr_arg_str=[]
        else:
            curr_arg_str.append(c)

            if c=='(':
                stack.append('(')
            elif c==')' and stack:
                stack.pop()

    # 处理最后1个参数
    if curr_arg_str:
        args_list.append(''.join(curr_arg_str))
    return args_list


def parse_term(term_str):
    # 对项进行解析
    if '(' in term_str:
        # 以第一个'('为函数名与参数的分隔
        func_end_index=term_str.index('(')
        # 提取函数名
        func_name=term_str[:func_end_index]
        # 提取参数
        args=split_args(term_str[func_end_index+1:-1])

        # 递归求所有嵌套的参数
        func_args=[parse_term(a) for a in args]
        return {"type":'func',"name":func_name, "args":func_args}
    elif len(term_str)==2:  # 认为是变量
        return {"type": 'var', 'name': term_str}
    else:  # 其他，认为是常量
        return {"type": 'const', 'name': term_str}

class AtomicFormula:
    def __init__(self,af_str):
        pred_end_index=af_str.index('(')
        self.predicate = af_str[:pred_end_index]  # 提取谓词
        args=split_args(af_str[pred_end_index+1:-1])  # 提取参数
        self.args =[parse_term(a) for a in args]

def substitute(term,subs_map):
    # subs_map是替换映射表
    # 替换
    if term['type']=='var':
        # 如果subs_map中有term['name']，则取出替换项，并返回；否则，无法替换，返回term
        return subs_map.get(term['name'],term)
    elif term['type']=='func':
        new_args=[substitute(a,subs_map) for a in term['args']]
        return {'type':'func','name':term['name'],'args':new_args}
    else:
        # 这时 term['type'] == 'const'
        return term

# 比较两个项是否完全相等
def deep_equal(term1,term2):
    if term1['type']!=term2['type']:
        return False
    if term1['type']=='var':
        return term1['name']==term2['name']
    elif term1['type']=='const':
        return term1['name'] == term2['name']
    elif term1['type']=='func':
        if term1['name'] != term2['name'] or len(term1['args'])!=len(term2['args']) :
            return False

        # 递归比较每一项是否完全相等
        return all(deep_equal(a1,a2) for a1,a2 in zip(term1['args'],term2['args']))
    return False

def occurs_check(var_name, term, subs_map):
    term = substitute(term, subs_map)
    if term['type'] == 'var':
        return term['name'] == var_name
    elif term['type'] == 'func':
        return any(occurs_check(var_name, arg, subs_map) for arg in term['args'])
    else:
        return False

def unify_var(var,term,subs_map):
    var_name = var['name']
    term=substitute(term,subs_map)

    # 如果 项term 与 变量var 完全相等，说明已经替换过
    if term['type']=='var' and term['name']==var_name:
        return subs_map.copy()
    # occurs检查
    if occurs_check(var_name, term, subs_map):
        return None

    # 更新替换映射表
    new_subs_map = subs_map.copy()
    new_subs_map[var_name] = term

    # 把替换映射表中的所有变量重新替换一次
    for subs in new_subs_map:
        new_subs_map[subs]=substitute(new_subs_map[subs],new_subs_map)

    return new_subs_map

def unify(term1,term2,subs_map):
    # 合一
    term1_subs = substitute(term1,subs_map)
    term2_subs = substitute(term2, subs_map)

    # 比较两个项是否完全相等
    if deep_equal(term1_subs,term2_subs):
        # 如果完全相等，则直接返回原映射表
        return subs_map.copy()

    # 以下情况是两个项不完全相等
    # 情况1：term1是变量
    if term1['type']=='var':
        return unify_var(term1,term2,subs_map)

    # 情况2：term2是变量
    if term2['type'] == 'var':
        return unify_var(term2,term1,subs_map)

    # 情况3：term1,term2都是函数
    if term1['type'] == 'func' and term2['type'] == 'func':
        if term1['name']!=term2['name'] or len(term1['args'])!=len(term2['args']):
            return None
        for a1,a2 in zip(term1['args'],term2['args']):
            subs_map=unify(a1,a2,subs_map)
            if subs_map is  None:
                return None
        return subs_map
    return None

def term_to_string(term):
    if term['type'] == 'var':
        return term['name']
    elif term['type'] == 'const':
        return term['name']
    elif term['type'] == 'func':
        args = ', '.join(term_to_string(arg) for arg in term['args'])
        return f"{term['name']}({args})"

def MGU(af_str1,af_str2):

    af1=AtomicFormula(af_str1)
    af2=AtomicFormula(af_str2)
    if af1.predicate!=af2.predicate:
        raise ValueError("These two atomic formulas have different predicates")
    elif len(af1.args)!=len(af2.args):
        raise ValueError("The numbers of arguments are different")

    subs_map={}  # 初始化替换映射表
    for a1,a2 in zip(af1.args,af2.args):
        unified_subs_map=unify(a1,a2,subs_map)
        if unified_subs_map is None:
            return {}
        subs_map=unified_subs_map

    subs_map_str={}
    for var_name in subs_map:
        term=subs_map[var_name]
        subs_map_str[var_name]=term_to_string(term)

    return subs_map_str


# test
print("Ex1:\n",MGU('P(xx,a)', 'P(b,yy)'))

print("Ex2:\n",MGU('P(a,xx,f(g(yy)))', 'P(zz,f(zz),f(uu))'))

print("Ex3:\n",MGU('Q(a,f(g(h(b)),c))','Q(xx,f(yy,zz))'))

print("Ex4:\n",MGU('P(xx,a,f(g(yy)))', 'P(f(zz),zz,f(uu))'))

print("Ex5:\n",MGU('P(a,xx,h(g(zz)))','P(zz,h(yy),h(yy))'))

print("Ex6:\n",MGU('P(xx,xx)','P(yy,f(yy))'))  # 无法合一