'''
The principle of propositional logic,命题逻辑推理
'''
def isComplement(l1,l2):
    '''
        判断两个文字是否互补
        :param l1: letter1
        :param l2: letter2
        :return:
        若互补，返回True
        否则，返回False
        '''
    if l1.startswith('~'):
        return l1[1:]==l2
    elif l2.startswith('~'):
        return l2[1:]==l1
    else:
        return False

def make_id_str(clause,letter):
    '''
    根据letter在子句中的位置，生成替换中的id（字符串形式）
    :param clause: 子句 结构{'id':int ,'elements': list }
    :param letter:
    :return: id_str
    '''
    id_str=str(clause['id'])
    if len(clause['elements'])>1:
        id_str+=chr(97+clause['elements'].index(letter))
    return id_str


def ResolutionProp(KB):
    clauses=[] # 子句集 结构： [{'id':int ,'elements': list }]
    step_str_list=[]
    clause_id=1

    # 处理原有的子句
    for clause in KB:
        # clause为KB中的每一个子句
        elements=list(clause)
        clauses.append({'id':clause_id,'elements':elements})
        step_str=', '.join(elements)
        step_str_list.append(f"{clause_id} ({step_str})")
        clause_id+=1

    processed_pairs=set()
    # processed_clauses=set(tuple( sorted(c['elements'])) for c in clauses)
    new_clauses=clauses.copy()

    while new_clauses:
        new_clauses_copy=new_clauses.copy()
        new_clauses=[]
        for c1 in new_clauses_copy:
            for c2 in clauses:
                if c1['id']>=c2['id']: # 避免重复处理
                    continue
                pair= (c1['id'],c2['id'])
                if pair in processed_pairs: # 说明这一对子句已经处理过
                    continue
                processed_pairs.add(pair)

                # 查找互补对
                for l1 in c1['elements']:
                    for l2 in c2['elements']:

                        # 寻找互补的文字
                        if isComplement(l1,l2):

                            # 生成新的子句
                            new_elements=[]
                            for ll in c1['elements']:
                                if ll!=l1:
                                    new_elements.append(ll)
                            for ll in c2['elements']:
                                if ll!=l2:
                                    new_elements.append(ll)

                            # 生成推理步骤
                            c1_id_str = make_id_str(c1,l1)
                            c2_id_str = make_id_str(c2,l2)

                            new_elements_str=', '.join(new_elements)
                            step_str_list.append(f"{clause_id} "
                                                 f"R[{c1_id_str},{c2_id_str}] = ({new_elements_str})")

                            if not new_elements:
                                return step_str_list

                            new_clauses.append({'id': clause_id, 'elements': new_elements})
                            clauses.append({'id': clause_id, 'elements': new_elements})
                            clause_id += 1

        new_clauses=new_clauses_copy
    return step_str_list

KB = {('FirstGrade',), ('~FirstGrade', 'Child'), ('~Child',)}
# KB={('F','M'),('~F','C'),('~M',),('~C',)}
steps = ResolutionProp(KB)
for step in steps:
    print(step)
