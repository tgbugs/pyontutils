#!/usr/bin/env python3
import requests
import simplejson
from collections import defaultdict as base_dd
from IPython import embed
import numpy as np

BLANK = '   '
LEAF = '──'
BRANCH = '│  '
MID_STEM = '├' + LEAF
BOT_STEM = '└' + LEAF

CYCLE = 'CYCLE DETECTED DERPS'

trans = {
    BLANK:BLANK,
    BOT_STEM:BLANK,
    BRANCH:(MID_STEM, BOT_STEM, BRANCH),
    MID_STEM:(MID_STEM, BOT_STEM, BRANCH),
}

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

def get_node(start, tree):
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

def dematerialize(parent_name, parent_node):  # FIXME we need to demat more than just leaves!
    """ Remove leaves higher in the tree that occur further down the
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
        new_lleaves = dematerialize(child_name, children)

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
def _dematerialize_leaves(parent_name, parent_node):  # FIXME we need to demat more than just leaves!
    """ Remove leaves higher in the tree that occur further down the
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
        new_lleaves = dematerialize_leaves(child_name, children)

        if child_name in new_lleaves:  # if it is a leaf!
            if child_name in lleaves:  # if it has previously been identified as a leaf!
                print('MATERIALIZATION DETECTED! LOWER PARENT:',
                      lleaves[child_name],'ZAPPING!:', child_name,
                      'OF PARENT:', parent_name)
                children.pop(child_name)
                #print('cn', child_name, 'pn', parent_name, 'BOTTOM')
            else:  # if it has NOT previously been identified as a leaf, add the parent!
                new_lleaves[child_name] = parent_name  # pass it back up to nodes above
                #print('cn', child_name, 'pn', parent_name)

        lleaves.update(new_lleaves)

    return lleaves

class defaultdict(base_dd):
    __str__ = dict.__str__
    __repr__ = dict.__repr__

    pad = '  '
    strpad = ' | '
    prefix = []
    existing = {}  # FIXME CAREFUL WITH THIS
    current_parent = None

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

            if key in pnames:  # XXX FIXME XXX
                if len(pnames[key]) > 1:  # XXX FIXME XXX parents not avail in m cases!
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

    #def __len__(self):  # can't do this!
        #return sum([len(self[k]) if self[k] else 1 for k in self])

# don't forget the incoming or you will get ALL THE THINGS
query = "http://matrix.neuinfo.org:9000/scigraph/graph/neighbors/GO:0044464?relationshipType=subClassOf&direction=INCOMING&depth=%s"
cell_part_depth = 9
direction = 'INCOMING'
root = "GO:0044464"

query = "http://matrix.neuinfo.org:9000/scigraph/graph/neighbors/NIFGA:birnlex_796?relationshipType=has_proper_part&direction=OUTGOING&depth=%s"
query = "http://matrix.neuinfo.org:9000/scigraph/graph/neighbors/NIFGA:birnlex_796?relationshipType=http://www.obofoundry.org/ro/ro.owl%23has_proper_part&direction=OUTGOING&depth=9"
direction = 'OUTGOING'
root = "NIFGA:birnlex_796"

query = "http://matrix.neuinfo.org:9000/scigraph/graph/neighbors/UBERON:0000955?relationshipType=BFO_0000050&direction=INCOMING&depth=%s"
query = "http://matrix.neuinfo.org:9000/scigraph/graph/neighbors/UBERON:0000955?relationshipType=http://purl.obolibrary.org/obo/BFO_0000050&direction=INCOMING&depth=%s"
direction = 'INCOMING'
root = "UBERON:0000955"

query = "http://matrix.neuinfo.org:9000/scigraph/graph/neighbors/UBERON:0002749?relationshipType=BFO_0000050&direction=INCOMING&depth=%s"
query = "http://matrix.neuinfo.org:9000/scigraph/graph/neighbors/UBERON:0002749?relationshipType=http://purl.obolibrary.org/obo/BFO_0000050&direction=INCOMING&depth=%s"
direction = 'INCOMING'
root = "UBERON:0002749"

query = "http://localhost:9000/scigraph/graph/neighbors/FMA:Brain?relationshipType=http%3A%2F%2Fsig.biostr.washington.edu%2Ffma3.0%23regional_part_of&direction=INCOMING&depth=10"
direction = 'INCOMING'
root = 'FMA:Brain'

#js = []
#for i in range(10):  # emperically this maxes at depth of 10 w/ 2823 terms
    #js.append(requests.get(query % i).json())

#with open('/tmp/', 'rt') as f:
    #j = simplejson.load(f)


j = requests.get(query).json()
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

if direction == 'OUTGOING':  # flip for the tree
    objects, parents = parents, objects

names = {nodes[k]:[nodes[s] for s in v] for k,v in objects.items()}
pnames = {nodes[k]:[nodes[s] for s in v] for k,v in parents.items()}


def tree(): return defaultdict(tree)

def cycle_check(puta_end, start, graph):  # XXX use find on the subtree instead!
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

def build_tree(obj, existing = {}, flat_tree = set()):  # FUCK YOU MULTIPARENT HIERARCHIES DOUBLE FUCK YOU CYCLES
    subjects = objects[obj]
    t = tree()
    t[obj]

    for sub in subjects:
        #print(sub)
        """
        cc = False
        for child in objects[sub]:
            cc = cycle_check(sub, child, objects)
            if cc:
                print('WTF M8')
                t[obj][sub][CYCLE]
                if len(parents[sub]) > 1:  # FIXME :/
                    existing[sub] = t[obj][sub]  # don't run children :/
                break
        if cc:
            continue
        #"""

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

parts, dupes = build_tree(root)

#def dicts(t): return {k: dicts(t[k]) for k in t}  # reped w/ mod class

#parts = dicts(partsd)

#def rename(tree): return {nodes[k]: rename(tree[k]) for k in tree}
def rename(tree):
    dict_ = defaultdict()
    for k in tree:
        dict_[nodes[k]] = rename(tree[k])
    return dict_

names = rename(parts)

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



level_sizes = [len(levels(parts, i)) for i in range(11)]

parent_counts = np.unique([len(v) for v in parents.values()])

print(names)
dematerialize('Brain',names)
print(names)
print(parts)

