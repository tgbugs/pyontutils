#!/usr/bin/env python3
import requests
from collections import namedtuple
from collections import defaultdict as base_dd
from IPython import embed
import numpy as np

BLANK = '   '
LEAF = '──'
BRANCH = '│  '
MID_STEM = '├' + LEAF
BOT_STEM = '└' + LEAF

CYCLE = 'CYCLE DETECTED DERPS'

def tcsort(item):  # FIXME SUCH WOW SO INEFFICIENT O_O
    """ get len of transitive closure assume type items is tree... """
    #if type(item[1]) == type(base_dd):
    return len(item[1]) + sum(tcsort(v) for v in item[1].items())
    #else:
        #jreturn 1

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

    children_ord = reversed(sorted([(k, v) for k, v in children.items()], key=tcsort))  # make sure we hit deepest first
    
    for child_name, _ in children_ord:  # get list so we can go ahead and pop
        print(child_name)
        new_lleaves = dematerialize(child_name, children)
        if child_name == 'Fornix':  # debugging failing demat
            pass
            #embed()
            
        if child_name in new_lleaves:  # if it is a leaf!
            if child_name in lleaves:  # if it has previously been identified as a leaf!
                print('MATERIALIZATION DETECTED! LOWER PARENT:',
                      lleaves[child_name],'ZAPPING!:', child_name,
                      'OF PARENT:', parent_name)
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

    def print_tree(self, level = 0):
        output = ''

        if level == 0:
            self.__class__.existing = {}  # clean up any old mess
            if len(self) == 1:
                item = [k for k in self.keys()][0]
                output += str(item)
                self.__class__.current_parent = item
                output += ''.join([v.print_tree(1) for v in self.values()])
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
                    value = __t.print_tree(level)
                    items.append((str(key), value))
                    self.__class__.prefix[-1] = cend
                else:
                    items.append((str(key), ' *'))  # wait... how the hell...
                return

            if key in self.parent_dict:  # XXX FIXME XXX
                if len(self.parent_dict[key]) > 1:  # XXX FIXME XXX parents not avail in m cases!
                    #print('MORE THAN ONE PARENT')
                    self.existing[key] = self.current_parent
                    key += ' *'  # mark that it will appear elsewhere

            if type(value) == type(self):
                cend = self.__class__.prefix[-1]
                if cend == MID_STEM:
                    self.__class__.prefix[-1] = symboltype

                self.__class__.current_parent = key
                v = value.print_tree(level + 1)  # recurse here XXX
                self.__class__.prefix[-1] = cend
            else:
                v = str(value)

            items.append((str(key), v))
            
        # FIXME ideally want to sort by length of the transitive closure :/
        #items_list = [a for a in reversed(sorted([i for i in self.items()], key=tcsort))]
        items_list = sorted([i for i in self.items()], key=tcsort)  # XXX best

        #items_list = [a for a in reversed(sorted([i for i in self.items()], key=lambda a: len(a[1])))]
        #items_list = sorted([i for i in self.items()], key=lambda a: len(a[1]))

        #items_list = sorted([i for i in self.items()])
        for key, value in items_list[:-1]:
            switch(BRANCH, key, value)

        switch(BLANK, *items_list[-1])  # need to put blanks after BOT_STEM

        output += '\n'.join(['{}{}{}'.format(''.join(self.prefix), k, v) for k, v in items[:-1]])
        self.__class__.prefix[-1] = BOT_STEM
        output += '\n' + '{}{}{}'.format(''.join(self.prefix), *items[-1])
        
        if len(self.__class__.prefix) > 1:
            self.__class__.prefix.pop()

        return output

    def __str__(self):
        output = self.print_tree()
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


def tree():
    return TreeNode(tree)

def newTree(name, **kwargs):
    base_dict = {'prefix':[], 'existing':{}, 'current_parent':None}
    base_dict.update(kwargs)
    newTreeNode = type('TreeNode_' + str(hash(name)).replace('-','_'), (TreeNode,), base_dict)
    def Tree(): return newTreeNode(Tree)

    return Tree, newTreeNode

def creatTree(root, relationshipType, direction, depth, url_base='matrix.neuinfo.org:9000', json=None):
    query_string = 'http://{url_base}/scigraph/graph/neighbors/{root}?relationshipType={relationshipType}&direction={direction}&depth={depth}'

    relationshipType = relationshipType.replace('#','%23')
    query = query_string.format(root=root, relationshipType=relationshipType,
                                direction=direction, depth=depth, url_base=url_base)

    if json is None:
        j = requests.get(query).json()
    else:
        j = json

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

    names = {nodes[k]:[nodes[s] for s in v] for k,v in objects.items()}
    pnames = {nodes[k]:[nodes[s] for s in v] for k,v in parents.items()}

    Tree, _ = newTree(query, parent_dict=parents)

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

    _, nTreeNode = newTree('names' + query, parent_dict=pnames)  # FIXME pnames is wrong...
    def rename(tree):
        dict_ = nTreeNode()
        for k in tree:
            dict_[nodes[k]] = rename(tree[k])
        return dict_

    hierarchy, dupes = build_tree(root)
    named_hierarchy = rename(hierarchy)

    return named_hierarchy, (hierarchy, dupes, nodes, edgerep, objects, parents, names, pnames)

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


def _main():
    Query = namedtuple('Query', ['root','relationshipType','direction','depth'])

    cell = Query("GO:0044464", 'subClassOf', 'INCOMING', 9)
    nifga = Query('NIFGA:birnlex_796', 'http://www.obofoundry.org/ro/ro.owl#has_proper_part', 'OUTGOING', 9)
    uberon = Query('UBERON:0000955', 'http://purl.obolibrary.org/obo/BFO_0000050', 'INCOMING', 9)
    uberon_cc = Query('UBERON:0002749', 'http://purl.obolibrary.org/obo/BFO_0000050', 'INCOMING', 9)
    ncbi_ins =  Query('NCBITaxon:50557', 'subClassOf', 'INCOMING', 10)
    ncbi_rod =  Query('NCBITaxon:9989', 'subClassOf', 'INCOMING', 10)

    queries = cell, nifga, uberon, uberon_cc
    queries = ncbi_ins, ncbi_rod, uberon, nifga

    url = 'localhost:9000'
    fma3_r = Query('FMA3:Brain', 'http://sig.biostr.washington.edu/fma3.0#regional_part_of', 'INCOMING', 9)
    fma3_c = Query('FMA3:Brain', 'http://sig.biostr.washington.edu/fma3.0#constitutional_part_of', 'INCOMING', 9)
    #fma3_tree, fma3_extra = creatTree(*fma3_r, url_base=url)

    fma_r = Query('FMA:50801', 'http://purl.org/sig/ont/fma/regional_part_of', 'INCOMING', 20)
    fma_c = Query('FMA:50801', 'http://purl.org/sig/ont/fma/constitutional_part_of', 'INCOMING', 20)
    fma_rch_r = Query('FMA:61819', 'http://purl.org/sig/ont/fma/regional_part_of', 'INCOMING', 20)
    #fma_tree, fma_extra = creatTree(*fma_r, url_base=url)
    #fma_tree, fma_extra = creatTree(*fma_rch_r, url_base=url)

    fma_hip = Query('FMA:275020', 'http://purl.org/sig/ont/fma/regional_part_of', 'BOTH', 20)
    fma_hip = Query('FMA:275020', 'http://purl.org/sig/ont/fma/constitutional_part_of', 'BOTH', 20)
    #fma_tree, fma_extra = creatTree(*fma_hip, url_base=url)

    fma_mfg = Query('FMA:273103', 'http://purl.org/sig/ont/fma/regional_part_of', 'BOTH', 20)
    #fma_tree, fma_extra = creatTree(*fma_mfg, url_base=url)



    ncbi_metazoa = Query('NCBITaxon:33208', 'subClassOf', 'INCOMING', 20)
    ncbi_vertebrata = Query('NCBITaxon:7742', 'subClassOf', 'INCOMING', 40)
    #ncbi_tree, ncbi_extra = creatTree(*ncbi_vertebrata, url_base=url)


    fma_tel = Query('FMA:62000', 'http://purl.org/sig/ont/fma/regional_part_of', 'INCOMING', 20)
    fma_gsc_tree, fma_gsc_extra = creatTree(*fma_tel, url_base=url)

    childs = list(fma_gsc_extra[2])  # get the curies for the left/right so we can get parents for all
    from heatmaps.scigraph_client import Graph
    g = Graph('http://localhost:9000/scigraph')
    parent_nodes = []
    for curie in childs:
        json = g.getNeighbors(curie, relationshipType='subClassOf')
        if json:
            for node in json['nodes']:
                if node['id'] != curie:
                    parent_nodes.append(node)  # should have dupes


    embed()
    return
    uberon_tree, uberon_extra = creatTree(*uberon)

    uberon_flat = [n.replace(':','_') for n in flatten(uberon_extra[0])]
    with open('/tmp/uberon_partonomy_terms', 'wt') as f:
        f.writelines('\n'.join(uberon_flat))

    for query in queries:
        tree, extra = creatTree(*query)
        dematerialize(list(tree.keys())[0], tree)
        print(tree)
        #print(extra[0])

        level_sizes = [len(levels(tree, i)) for i in range(11)]
        print('level sizes', level_sizes)
        parent_counts = np.unique([len(v) for v in extra[-3].values()])
        print('unique parent counts', parent_counts)
        print('num terms', len(extra[2]))



    embed()

def main():
    from heatmaps.scigraph_client import Graph
    g = Graph('http://localhost:9000/scigraph')
    rtco = 'http://purl.org/sig/ont/fma/constitutional_part_of'.replace('/','%2F')
    rtro = 'http://purl.org/sig/ont/fma/regional_part_of'.replace('/','%2F')
    #rtc = 'http://purl.org/sig/ont/fma/constitutional_part'.replace('/','%2F')  # FIXME the sub/pred relation is switched :/
    #rtr = 'http://purl.org/sig/ont/fma/regional_part'.replace('/','%2F')
    json_co = g.getEdges(rtco, limit=9999999999)
    json_ro = g.getEdges(rtro, limit=9999999999)
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

    Query = namedtuple('Query', ['root','relationshipType','direction','depth'])

    url = 'localhost:9000'
    #fma = Query('FMA:50801', 'None', 'INCOMING', 20)
    fma = Query('FMA:61817', 'None', 'INCOMING', 20)  # Cerebral hemisphere
    fma_tree, fma_extra = creatTree(*fma, url_base=url, json=json)
    with open('/tmp/rc_combo_tree', 'wt') as f: f.write(str(fma_tree))

    embed()

if __name__ == '__main__':
    main()
