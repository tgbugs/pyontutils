import io

col_total = []
col_appdx = []

with open ('pyontutils/resources/swanson_aligned.txt', 'r') as f:
    for line in f:
        if (line.startswith('Appendix')):
            col_appdx = []
            col_appdx.append(line.strip('\n'))
            col_total.append(col_appdx)
        else:
            if not (line.startswith('#')):
                child = line.split('.....')
                count = 0
                for term in child:
                    if term == '':
                        count+=1
                    else:
                        col_child=[]
                        col_child.append(count)
                        idx=term.find('(')
                        idxc=term.find(')')
                        if idx>0:
                            col_child.append(term[0:idx-1])
                            col_child.append(term[idx+1:idxc])
                            col_appdx.append(col_child)
                        else:
                            col_child.append(term.strip('\n'))
                            col_appdx.append(col_child)


f.closed
print(col_total)



