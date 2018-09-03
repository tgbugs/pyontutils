#!/usr/bin/env python3.6
import os
from copy import deepcopy
from html import escape as html_escape
from collections import namedtuple
from collections import defaultdict as base_dd
import requests
from pyontutils.utils import TermColors as tc
from pyontutils.ttlser import natsort
from pyontutils.scigraph import Graph
from pyontutils.namespaces import PREFIXES as uPREFIXES
from IPython import embed

BLANK = '   '
LEAF = '──'
BRANCH = '│  '
MID_CON = '├'
MID_STEM = MID_CON + LEAF
BOT_CON = '└'
BOT_STEM = BOT_CON + LEAF
TOP_CON = '┌'

CYCLE = 'CYCLE DETECTED'

DEP = 'http://www.w3.org/2002/07/owl#deprecated'

Query = namedtuple('Query', ['root','relationshipType','direction','depth'])
Extras = namedtuple('Extras', ['hierarchy', 'html_hierarchy',
                               'dupes', 'nodes', 'edgerep',
                               'objects', 'parents',
                               'names', 'pnames', 'hpnames',
                               'json', 'html', 'text'])

def alphasortkey(keyvalue):
    key, value = keyvalue
    if key is None:
        return ('z' * 10,)
    if '>' in key:
        key = key.split('>', 1)[-1]
    return natsort(key)

def tcsort(item):  # FIXME SUCH WOW SO INEFFICIENT O_O
    """ get len of transitive closure assume type items is tree... """
    return len(item[1]) + sum(tcsort(kv) for kv in item[1].items())

def in_tree(node, tree):  # XXX TODO
    if not tree:
        return False
    elif node in tree:
        return True
    else:
        for subtree in tree.values():
            if in_tree(node, subtree):
                return True
        return False

def get_node(start, tree, pnames):
    """ for each parent find a single branch to root """
    def get_first_branch(node):
        if node not in pnames:  # one way to hit a root
            return []
        if pnames[node]:  # mmmm names
            fp = pnames[node][0]
            if cycle_check(node, fp, pnames):
                fp = pnames[node][1]  # if there are double cycles I WILL KILL FOR THE PLEASURE IF IT
            print(fp)
            return [fp] + get_first_branch(fp)
        else:
            return []

    branch = get_first_branch(start)

    for n in branch[::-1]:
        tree = tree[n]

    assert start in tree, "our start wasnt in the tree! OH NO!"
    branch = [start] + branch
    print('branch', branch)
    return tree, branch

def flag_dep(json_):
    for node in json_['nodes']:
        if DEP in node['meta']:
            curie = node['id']
            label = node['lbl']
            node['id'] = tc.red(curie)
            node['lbl'] = tc.red(label)
            for edge in json_['edges']:
                if edge['sub'] == curie:
                    edge['sub'] = tc.red(curie)
                elif edge['obj'] == curie:
                    edge['obj'] = tc.red(curie)

def cycle_check(puta_end, start, graph):  # XXX use the flat_tree trick!
    visited = []
    def inner(next_):
        if next_ not in graph:  # since these aren't actually graphs and some nodes dont have parents
            return False
        elif not graph[next_]:
            return False
        elif puta_end in graph[next_]:
            return True
        elif next_ in visited:
            print('CYCLE: ', visited + [next_])
            return False  # A DIFFERENT CYCLE WAS DETECTED will handle later
        else:
            visited.append(next_)
            test = any([inner(c) for c in graph[next_]])
            visited.pop()
            return test

    return inner(start)

def dematerialize(parent_name, parent_node):  # FIXME we need to demat more than just leaves!
    #FIXME still an issue: Fornix, Striatum, Diagonal Band
    """ Remove nodes higher in the tree that occur further down the
        SAME branch. If they occur down OTHER branchs leave them alone.

        NOTE: modifies in place!
    """
    lleaves = {}
    children = parent_node[parent_name]

    if not children:  # children could be empty ? i think this only happens @ root?
        #print('at bottom', parent_name)
        lleaves[parent_name] = None
        return lleaves

    children_ord = reversed(sorted(sorted(((k, v)
                                           for k, v in children.items()),
                                          key=alphasortkey),
                                          #key=lambda a: f'{a[0]}'.split('>')[1] if '>' in f'{a[0]}' else f'a[0]'),
                                          #key=lambda a: a[0].split('>') if '>' in a[0] else a[0]),
                                   key=tcsort))  # make sure we hit deepest first

    for child_name, _ in children_ord:  # get list so we can go ahead and pop
        #print(child_name)
        new_lleaves = dematerialize(child_name, children)
        if child_name == 'magnetic resonance imaging':  # debugging failing demat
            pass
            #embed()

        if child_name in new_lleaves or all(l in lleaves for l in new_lleaves):
            # if it is a leaf or all childs are leaves as well
            if child_name in lleaves:  # if it has previously been identified as a leaf!
                #print('MATERIALIZATION DETECTED! LOWER PARENT:',
                      #lleaves[child_name],'ZAPPING!:', child_name,
                      #'OF PARENT:', parent_name)
                children.pop(child_name)
                #print('cn', child_name, 'pn', parent_name, 'BOTTOM')
            #else:  # if it has NOT previously been identified as a leaf, add the parent!
                #new_lleaves[child_name] = parent_name  # pass it back up to nodes above
                #print('cn', child_name, 'pn', parent_name)
        #else:  # it is a node but we want to dematerizlize them too!
        lleaves[child_name] = parent_name

        lleaves.update(new_lleaves)

    return lleaves

class defaultdict(base_dd):
    __str__ = dict.__str__
    __repr__ = dict.__repr__

class TreeNode(defaultdict):  # FIXME need to factory this to allow separate trees!

    pad = '  '
    #prefix = []
    #existing = {}  # FIXME CAREFUL WITH THIS
    #current_parent = None
    html_head = ''

    def print_tree(self, level = 0, html=False):
        output = ''

        if level == 0:
            self.__class__.existing = {}  # clean up any old mess
            if len(self) == 1:
                item = [k for k in self.keys()][0]
                output += str(item)
                self.__class__.current_parent = item
                output += ''.join([v.print_tree(1, html) for v in self.values()])
                #self.__class__.prefix.pop()  # FIXME causes errors???
                self.__class__.existing = {}  # clean up new mess
                self.__class__.current_parent = None
                return output
            elif len(self) > 1:  # FIXME need a way to pop the last prefix!
                level = 1
                output += '\n.'

        if not self:
            return output
        elif len(self) > 1:  # not sure why we need this... :/
            output += '\n'

        self.__class__.prefix.append(MID_STEM)

        items = []

        def switch(symboltype, key, value):
            #if key in self.existing and type(value) == type(self):
            if False:  # we deal with this by dematerializing the tree
                #print('WEEEE MULTIPARENT!', items[-1], self.current_parent)
                if len(value):
                    parent = self.existing[key]
                    __t = tree()
                    #__t['MULTIPARENT, SEE: %s' % parent]
                    __t['* %s *' % tcsort((None, value))]

                    cend = self.__class__.prefix[-1]
                    if cend == MID_STEM:
                        self.__class__.prefix[-1] = symboltype
                    self.__class__.current_parent = key
                    value = __t.print_tree(level, html)
                    items.append((str(key), value))
                    self.__class__.prefix[-1] = cend
                else:
                    items.append((str(key), ' *'))  # wait... how the hell...
                return

            first_occurance = True
            if key in self.parent_dict:  # XXX FIXME XXX
                if len(self.parent_dict[key]) > 1:  # XXX FIXME XXX parents not avail in m cases!
                    #print('MORE THAN ONE PARENT')
                    first_occurance = not key in self.existing
                    self.existing[key] = self.current_parent
                    key += ' *'  # mark that it will appear elsewhere

            ds = ''
            if type(value) == type(self):
                cend = self.__class__.prefix[-1]
                if cend == MID_STEM:
                    self.__class__.prefix[-1] = symboltype

                self.__class__.current_parent = key
                v = value.print_tree(level + 1, html)  # recurse here XXX
                if html and v and not first_occurance:
                    ds = '<details><summary>'
                    key += ' ... <br></summary>'
                    v += '</details>'
                self.__class__.prefix[-1] = cend
            else:
                v = str(value)

            items.append((str(key), v, ds))

        items_list = sorted(sorted(((f'{k}', v)  # XXX best
                                    for k, v in self.items()),
                                   key=alphasortkey),
                            key=tcsort)

        #items_list = [a for a in reversed(sorted([i for i in self.items()], key=tcsort))]
        #items_list = [a for a in reversed(sorted([i for i in self.items()], key=lambda a: len(a[1])))]
        #items_list = sorted([i for i in self.items()], key=lambda a: len(a[1]))
        #items_list = sorted([i for i in self.items()])

        for key, value in items_list[:-1]:
            switch(BRANCH, key, value)

        switch(BLANK, *items_list[-1])  # need to put blanks after BOT_STEM

        output += '\n'.join(['{3}{0}{1}{2}'.format(''.join(self.prefix), k, v, ds) for k, v, ds in items[:-1]])
        self.__class__.prefix[-1] = BOT_STEM
        output += '\n' + '{3}{0}{1}{2}'.format(''.join(self.prefix), *items[-1])

        if len(self.__class__.prefix) > 1:
            self.__class__.prefix.pop()

        return output

    def __str__(self, html=False):
        output = self.print_tree(html=html)
        # FIXME gotta do cleanup here for now :/
        self.__class__.prefix = []
        self.__class__.existing = {}  # clean up new mess
        self.__class__.current_parent = None
        return output

    def __repr__(self, level = 0):
        pad = level * self.pad

        output = '{'
        if self.values():
            output +=  '\n'

        items = []
        for key, value in self.items():
            if type(value) == type(self):
                v = value.__repr__(level = level + 1)
            else:
                v = repr(value)

            items.append((repr(key), v))

        output += ',\n'.join(['{}{}: {}'.format(pad, k, v) for k, v in items])

        output += '}'

        return output

    def __html__(self):
        output = self.__str__(html=True)
        lines = output.split('\n')
        new_lines = []
        for line in lines:
            if MID_CON in line:
                splitter = MID_CON
            elif BOT_CON in line:
                splitter = BOT_CON
            else:
                splitter = None

            if splitter:
                prefix, suffix = line.split(splitter)
                prefix = prefix.replace(' ', '\xa0')  # nbsp
                line = splitter.join((prefix, suffix))
            new_lines.append(line)
        output = '\n'.join(new_lines)
        output = output.replace('\n', ' <br>\n')
        output = output.replace('</summary> <br>', '</summary>')
        output = output.replace('</details> <br>', '</details>')
        html_head = '\n    '.join(self.html_head)
        output = ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" '
                  '"http://www.w3.org/TR/html4/loose.dtd">\n'
                  '<html>\n'
                  '  <head>\n'
                  '    <meta charset="UTF-8">\n'
                  f'    {html_head}\n'
                  '    <style>\n'
                  '    body { font-family: Dejavu Sans Mono;\n'
                  '           font-size: 10pt; }\n'
                  '    a:link { color: black; }\n'
                  '    a:visited { color: grey; }\n'
                  '    details summary::-webkit-details-marker { display: none; }\n'
                  '    details > summary:first-of-type { list-style-type: none; }\n'
                  '    </style>\n'
                  '  </head>\n'
                  '  <body>\n'
                  + output + '\n'
                  '  </body>\n</html>')
        return output

def tree():
    return TreeNode(tree)

def newTree(name, **kwargs):
    base_dict = {'prefix':[], 'existing':{}, 'current_parent':None}
    base_dict.update(kwargs)
    newTreeNode = type('TreeNode_' + str(hash(name)).replace('-','_'), (TreeNode,), base_dict)
    def Tree(): return newTreeNode(Tree)

    return Tree, newTreeNode

def creatTree(root, relationshipType, direction, depth, graph=None, json=None, filter_prefix=None, prefixes=uPREFIXES, html_head='', local=False, verbose=False):
    # TODO FIXME can probably switch over to the inverse of the automata I wrote for parsing trees in parc...
    if json is None:
        if relationshipType == 'rdfs:subClassOf':
            relationshipType = 'subClassOf'
        j = graph.getNeighbors(root, relationshipType=relationshipType, direction=direction, depth=depth)
        if filter_prefix is not None:
            j['edges'] = [e for e in j['edges'] if not [v for v in e.values() if filter_prefix in v]]

        if hasattr(graph, '_cache'):
            j = deepcopy(j)  # avoid dangers of mutable cache
        #flag_dep(j)
    else:
        j = dict(json)
        j['edges'] = [e for e in j['edges'] if e['pred'] == relationshipType]
        #if 'meta' in j['nodes'][0]:  # check if we are safe to check meta
            #flag_dep(j)

    if verbose:
        print(len(j['nodes']))

    nodes = {n['id']:n['lbl'] for n in j['nodes']}
    nodes[CYCLE] = CYCLE  # make sure we can look up the cycle
    edgerep = ['{} {} {}'.format(nodes[e['sub']], e['pred'], nodes[e['obj']]) for e in j['edges']]

    objects = defaultdict(list)  # note: not all nodes are objects!
    for edge in j['edges']:
        objects[edge['obj']].append(edge['sub'])

    parents = defaultdict(list)
    for edge in j['edges']:
        parents[edge['sub']].append(edge['obj'])

    if direction == 'OUTGOING' or direction == 'BOTH':  # flip for the tree  # FIXME BOTH needs help!
        objects, parents = parents, objects

    def pruneOutOfTree(n):
        testk = len(n)
        test = sum(len(v) for v in n.values())
        while True:
            if verbose:
                print(test)
            n = {k:[s for s in v if s in n or s == 'ROOT'] for k, v in n.items() if v}
            ntestk = len(n)
            ntest = sum(len(v) for v in n.values())
            if ntest == test and ntestk == testk:
                if verbose:
                    print('done')
                return n
            else:
                test = ntest
                testk = ntestk

    parents[root] = ['ROOT']
    parents = pruneOutOfTree(parents)
    parents[root] = []

    names = {nodes[k]:[nodes[s] for s in v] for k,v in objects.items()}  # children don't need filtering
    pnames = {nodes[k]:[nodes[s] for s in v] for k,v in parents.items()}

    tree_name = root + relationshipType + direction + str(depth)
    Tree, _ = newTree(tree_name, parent_dict=parents)

    def build_tree(obj, existing = {}, flat_tree = set()):
        subjects = objects[obj]
        t = Tree()
        t[obj]

        for sub in subjects:
            if sub in existing:  # the first time down gets all children
                t[obj][sub] = existing[sub]
            elif sub in flat_tree:  # prevent cycles  KEK that is faster than doing in_tree :D
                print(CYCLE, sub, 'parent is', obj)
                t[obj][CYCLE][sub]
            else:
                flat_tree.add(sub)
                subtree, _ = build_tree(sub, existing, flat_tree)
                t[obj].update(subtree)

            if len(parents[sub]) > 1:
                existing[sub] = t[obj][sub]

        return t, existing
        # for each list of subjects
        # look up the subjects of that subject as if it were and object
        # and and look up those subjects subjects until there are no subjects
        # but we are not guranteed to have started at the right place
        # and so we may need to reorder ?

    _, nTreeNode = newTree('names' + tree_name, parent_dict=pnames)  # FIXME pnames is wrong...
    def rename(tree):
        dict_ = nTreeNode()
        for k in tree:
            dict_[nodes[k]] = rename(tree[k])
        return dict_

    htmlNodes = {}
    for k, v in nodes.items():
        if ':' in k and not k.startswith('http') and not k.startswith('file'):
            prefix, suffix = k.split(':')
            prefix = prefix.strip('\x1b[91m')  # colors :/
            if graph is not None and local:
                url = os.path.join(graph._basePath, 'vocabulary', 'id', k)
            else:
                url = str(prefixes[prefix]) + suffix
        else:
            if graph is not None and local:
                url = os.path.join(graph._basePath, 'vocabulary',
                                   k.replace('/','%2F').replace('#','%23'))
            else:
                url = k
        if v is None:  # if there is no label fail over to the url
            v = f'<{url}>'
        htmlNodes[k] = '<a target="_blank" href="{}">{}</a>'.format(url, html_escape(v))
    hpnames = {htmlNodes[k]:[htmlNodes[s] for s in v] for k, v in parents.items()}
    _, hTreeNode = newTree('html' + tree_name, parent_dict=hpnames, html_head=html_head)
    def htmlTree(tree):
        dict_ = hTreeNode()
        for k in tree:
            dict_[htmlNodes[k]] = htmlTree(tree[k])
        return dict_

    hierarchy, dupes = build_tree(root)
    try:
        named_hierarchy = rename(hierarchy)
        html_hierarchy = htmlTree(hierarchy)
    except KeyError as e:
        embed()
        raise e

    def sub_prefixes(h):
        if prefixes is not None:
            for n, p in prefixes.items():
                if type(p) != str:
                    p = str(p)
                h = h.replace('href="' + n + ':', 'href="' + p)
                h = h.replace('>' + p, '>' + n + ':')
        return h

    html = sub_prefixes(html_hierarchy.__html__())
    extras = Extras(hierarchy, html_hierarchy,
                    dupes, nodes, edgerep,
                    objects, parents,
                    names, pnames, hpnames, j,
                    html, str(named_hierarchy))
    return named_hierarchy, extras

def levels(tree, p, l = 0):
    if p == 0:
        return [k for k in tree.keys()]
    elif p == l:
        return tree.keys()
    else:
        lvls = []
        for ls in [levels(t, p, l + 1) for t in tree.values()]:
            lvls.extend(ls)

        return lvls

def count(tree): return sum([count(tree[k]) if tree[k] else 1 for k in tree])

def todict(tree): return {k:todict(v) for k, v in tree.items()}

def flatten(tree, out=[]):
    for name, subtree in tree.items():
        out.append(name)
        flatten(subtree, out)
    return out

def inv_edges(json):
    """Switch obj/sub for a set of edges (makes fixing known inverse edges MUCH easier)"""
    for edge in json['edges']:
        sub, obj = edge['sub'], edge['obj']
        edge['sub'] = obj
        edge['obj'] = sub

        edge['pred'] += 'INVERTED'


def main():
    sgg = Graph(cache=True)
    sgg_local = Graph(cache=True)

    fma3_r = Query('FMA3:Brain', 'http://sig.biostr.washington.edu/fma3.0#regional_part_of', 'INCOMING', 9)
    fma3_c = Query('FMA3:Brain', 'http://sig.biostr.washington.edu/fma3.0#constitutional_part_of', 'INCOMING', 9)
    #fma3_tree, fma3_extra = creatTree(*fma3_r, graph=sgg_local)

    fma_r = Query('FMA:50801', 'http://purl.org/sig/ont/fma/regional_part_of', 'INCOMING', 20)
    fma_c = Query('FMA:50801', 'http://purl.org/sig/ont/fma/constitutional_part_of', 'INCOMING', 20)
    fma_rch_r = Query('FMA:61819', 'http://purl.org/sig/ont/fma/regional_part_of', 'INCOMING', 20)
    #fma_tree, fma_extra = creatTree(*fma_r, graph=sgg_local)
    #fma_tree, fma_extra = creatTree(*fma_rch_r, graph=sgg_local)

    fma_hip = Query('FMA:275020', 'http://purl.org/sig/ont/fma/regional_part_of', 'BOTH', 20)
    fma_hip = Query('FMA:275020', 'http://purl.org/sig/ont/fma/constitutional_part_of', 'BOTH', 20)
    #fma_tree, fma_extra = creatTree(*fma_hip, graph=sgg_local)

    fma_mfg = Query('FMA:273103', 'http://purl.org/sig/ont/fma/regional_part_of', 'BOTH', 20)
    #fma_tree, fma_extra = creatTree(*fma_mfg, graph=sgg_local)

    fma_tel = Query('FMA:62000', 'http://purl.org/sig/ont/fma/regional_part_of', 'INCOMING', 20)
    if False:
        fma_gsc_tree, fma_gsc_extra = creatTree(*fma_tel, graph=sgg_local)

        childs = list(fma_gsc_extra[2])  # get the curies for the left/right so we can get parents for all
        g = Graph(cache=True)
        parent_nodes = []
        for curie in childs:
            json = g.getNeighbors(curie, relationshipType='subClassOf')
            if json:
                for node in json['nodes']:
                    if node['id'] != curie:
                        parent_nodes.append(node)  # should have dupes


        embed()
        return

    uberon = Query('UBERON:0000955', 'BFO:0000050', 'INCOMING', 40)
    uberon_tree, uberon_extra = creatTree(*uberon, graph=sgg)
    queries = uberon,

    uberon_flat = sorted(set(n for n in flatten(uberon_extra[0])))
    with open('/tmp/uberon_partonomy_terms', 'wt') as f:
        f.writelines('\n'.join(uberon_flat))

    for query in queries:
        tree, extra = creatTree(*query, graph=sgg)
        dematerialize(list(tree.keys())[0], tree)
        print(tree)
        #print(extra[0])
        with open('/tmp/' + query.root, 'wt') as f:
            f.writelines(tree.print_tree())

        level_sizes = [len(levels(tree, i)) for i in range(11)]
        print('level sizes', level_sizes)
        parent_counts = sorted(set(len(v) for v in extra[-4].values()))
        print('unique parent counts', parent_counts)
        print('num terms', len(extra[2]))

    return

    embed()

def _main():
    rtco = 'http://purl.org/sig/ont/fma/constitutional_part_of'
    rtro = 'http://purl.org/sig/ont/fma/regional_part_of'
    #rtc = 'http://purl.org/sig/ont/fma/constitutional_part'.replace('/','%2F')  # FIXME the sub/pred relation is switched :/
    #rtr = 'http://purl.org/sig/ont/fma/regional_part'.replace('/','%2F')
    json_co = sgg_local.getEdges(rtco, limit=9999999999)
    json_ro = sgg_local.getEdges(rtro, limit=9999999999)
    #json_c = g.getEdges(rtc, limit=9999999999)
    #json_r = g.getEdges(rtr, limit=9999999999)
    #inv_edges(json_c)
    #inv_edges(json_r)

    json = json_ro
    #json['nodes'].extend(json_co['nodes'])
    #json['edges'].extend(json_co['edges'])

    #json['nodes'].extend(json_c['nodes'])
    #json['edges'].extend(json_c['edges'])
    #json['nodes'].extend(json_r['nodes'])
    #json['edges'].extend(json_r['edges'])
    #embed()


    #fma = Query('FMA:50801', 'None', 'INCOMING', 20)
    fma = Query('FMA:61817', 'None', 'INCOMING', 20)  # Cerebral hemisphere
    fma_tree, fma_extra = creatTree(*fma, json=json)
    with open('/tmp/rc_combo_tree', 'wt') as f: f.write(str(fma_tree))

    embed()

if __name__ == '__main__':
    main()
