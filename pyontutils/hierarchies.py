#!/usr/bin/env python3
import os
import tempfile
from copy import deepcopy
from html import escape as html_escape
from urllib.parse import quote
from collections import namedtuple
from collections import defaultdict as base_dd
import htmlfn as hfn
from pyontutils.core import OntId, log as _log
from pyontutils.utils import TermColors as tc
from ttlser import natsort
from pyontutils.namespaces import PREFIXES as uPREFIXES
try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint

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

log = _log.getChild('hierarchies')


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

    def print_tree(self, level = 0, html=False, hpr=None, tparent=None):
        output = ''

        if html:
            # LOL PYTHON adding keywords to a language to try to fix broken scope?
            # oops didn't work, can't shadow a global variable in local scope without
            # also changing the outer scope OOPS, nonlocal doesn't work with globals derp
            _MID_STEM = '<span title="{predicate}">' + MID_STEM + '</span>'  # LOL PYTHON
            _BOT_STEM = '<span title="{predicate}">' + BOT_STEM + '</span>'  # LOL PYTHON
        else:
            _MID_STEM = MID_STEM  # LOL PYTHON
            _BOT_STEM = BOT_STEM  # LOL PYTHON

        if level == 0:
            self.__class__.existing = {}  # clean up any old mess
            if len(self) == 1:
                item = [k for k in self.keys()][0]
                output += str(item)
                self.__class__.current_parent = item
                output += ''.join([v.print_tree(1, html, hpr, item) for v in self.values()])
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

        self.__class__.prefix.append(_MID_STEM)

        items = []

        def switch(symboltype, key, value):
            itparent = key
            #if key in self.existing and type(value) == type(self):
            if False:  # we deal with this by dematerializing the tree
                #print('WEEEE MULTIPARENT!', items[-1], self.current_parent)
                if len(value):
                    parent = self.existing[key]
                    __t = tree()
                    #__t['MULTIPARENT, SEE: %s' % parent]
                    __t['* %s *' % tcsort((None, value))]

                    cend = self.__class__.prefix[-1]
                    if cend == _MID_STEM:
                        self.__class__.prefix[-1] = symboltype
                    self.__class__.current_parent = key
                    value = __t.print_tree(level, html, hpr, itparent)
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
                if cend == _MID_STEM:
                    self.__class__.prefix[-1] = symboltype

                self.__class__.current_parent = key
                v = value.print_tree(level + 1, html, hpr, itparent)  # recurse here XXX

                if html and v:
                    if first_occurance:
                        ds = '<details open=""><summary>'
                    else:
                        ds = '<details><summary>'

                    key += '<span class="hide-when-open"> ... </span><br></summary>'
                    v += '</details>'

                self.__class__.prefix[-1] = cend

            else:
                v = str(value)

            items.append((str(key), v, ds, itparent))

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

        switch(BLANK, *items_list[-1])  # need to put blanks after _BOT_STEM

        def pp(k):
            out = ''.join(self.prefix)
            if html and hpr is not None and k:
                if tparent is not None:
                    k1 = tparent.strip('*').strip()
                    k2 = k.strip('*').strip()
                    if [_ for _ in (k1, k2)
                        if 'CYCLE DETECTED' in _ or
                        'ROOT' in _]:
                        return out.format(predicate='')
                    try:
                        predicate = hpr[k1, k2]
                    except KeyError as e:
                        log.exception(e)
                        return out

                    out = out.format(predicate=predicate)

            return out

        output += '\n'.join(
            ['{3}{0}{1}{2}'.format(pp(nk), k, v, ds, nk)
             for k, v, ds, nk in items[:-1]])
        self.__class__.prefix[-1] = _BOT_STEM
        output += '\n' + '{3}{0}{1}{2}'.format(pp(items[-1][-1]), *items[-1])

        if len(self.__class__.prefix) > 1:
            self.__class__.prefix.pop()

        return output

    def __str__(self, html=False, hpr=None):
        output = self.print_tree(html=html, hpr=hpr)
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

    def __html__(self, hpr=None):
        output = self.__str__(html=True, hpr=hpr)
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
                prefix, suffix = line.split(splitter, 1)
                if 'summary>' in line:
                    pre_splitter = 'summary>'
                    pre_prefix, prefix = prefix.split(pre_splitter, 1)
                    if '<span ' in prefix:
                        post_splitter = '<span '
                        prefix, postfix = prefix.split(post_splitter, 1)
                    else:
                        postfix = ''

                    _prefix = prefix.replace(' ', '\xa0')  # nbsp
                    prefix = pre_splitter.join((pre_prefix, _prefix))
                    if postfix:
                        prefix = post_splitter.join((prefix, postfix))
                else:
                    if '<span ' in prefix:
                        post_splitter = '<span '
                        prefix, postfix = prefix.split(post_splitter, 1)
                    else:
                        postfix = ''

                    prefix = prefix.replace(' ', '\xa0')  # nbsp
                    if postfix:
                        prefix = post_splitter.join((prefix, postfix))

                line = splitter.join((prefix, suffix))
            new_lines.append(line)

        # you would think that adding an permanent margin at the
        # bottom of the window would be easy ... you would be wrong
        output = '\n'.join(new_lines)
        output = output.replace('\n', ' <br>\n')
        output = output.replace('</summary> <br>', '</summary>')
        output = output.replace('</details> <br>', '</details>')
        return output


def tree():
    return TreeNode(tree)


def newTree(name, **kwargs):
    base_dict = {'prefix':[], 'existing':{}, 'current_parent':None}
    base_dict.update(kwargs)
    newTreeNode = type('TreeNode_' + str(hash(name)).replace('-','_'), (TreeNode,), base_dict)
    def Tree(): return newTreeNode(Tree)

    return Tree, newTreeNode


def queryTree(root, relationshipType, direction, depth, entail, sgg, filter_prefix, curie):
    root_iri = None  # FIXME 268
    if relationshipType == 'rdfs:subClassOf':
        relationshipType = 'subClassOf'
    elif relationshipType == 'rdfs:subPropertyOf':
        relationshipType = 'subPropertyOf'

    j = sgg.getNeighbors(root, relationshipType=relationshipType,
                         direction=direction, depth=depth, entail=entail)
    if j is None:
        raise ValueError(f'Unknown root {root}')
    elif root.startswith('http'):
        # FIXME https://github.com/SciGraph/SciGraph/issues/268
        _ids = set(n['id'] for n in j['nodes'])
        if root not in _ids:
            root_iri = root
            root = curie
            if root is None:
                raise ValueError('please provide a curie for {root_iri}')

    if filter_prefix is not None:
        j['edges'] = [e for e in j['edges']
                        if not [v for v in e.values()
                                if filter_prefix in v]]

    if hasattr(sgg, '_cache'):
        j = deepcopy(j)  # avoid dangers of mutable cache
    #flag_dep(j)

    return j, root_iri


def build_tree(tree_class, obj, objects, parents, existing=None, flat_tree=None):
    subjects = objects[obj]
    t = tree_class()
    t[obj]

    for sub in subjects:
        if sub in existing:  # the first time down gets all children
            t[obj][sub] = existing[sub]
        elif sub in flat_tree:  # prevent cycles  KEK that is faster than doing in_tree :D
            print(CYCLE, sub, 'parent is', obj)
            t[obj][CYCLE][sub]
        else:
            flat_tree.add(sub)
            subtree, _ = build_tree(tree_class, sub, objects, parents, existing, flat_tree)
            t[obj].update(subtree)

        if len(parents[sub]) > 1:
            existing[sub] = t[obj][sub]

    return t, existing
    # for each list of subjects
    # look up the subjects of that subject as if it were and object
    # and and look up those subjects subjects until there are no subjects
    # but we are not guranteed to have started at the right place
    # and so we may need to reorder ?


def pruneOutOfTree(nodes, verbose):
    testk = len(nodes)
    test = sum(len(v) for v in nodes.values())
    while True:
        if verbose:
            print(test)
        nodes = {k:[s for s in v if s in nodes or s == 'ROOT']
                    for k, v in nodes.items() if v}
        ntestk = len(nodes)
        ntest = sum(len(v) for v in nodes.values())
        if ntest == test and ntestk == testk:
            if verbose:
                print('done')
            return nodes
        else:
            test = ntest
            testk = ntestk


def process_nodes(j, root, direction, verbose):
    nodes = {n['id']:n['lbl'] for n in j['nodes']}
    nodes[CYCLE] = CYCLE  # make sure we can look up the cycle
    edgerep = ['{} {} {}'.format(nodes[e['sub']], e['pred'], nodes[e['obj']]) for e in j['edges']]
    # note that if there are multiple relations between s & p then last one wins
    # sorting by the predicate should help keep it a bit more stable
    pair_rel = {(e['sub'], e['obj'])
                if direction == 'OUTGOING' else
                (e['obj'], e['sub']):
                e['pred'] + '>'
                if direction == 'OUTGOING' else
                '<' + e['pred']
                for e in sorted(j['edges'], key = lambda e: e['pred'])}

    objects = defaultdict(list)  # note: not all nodes are objects!
    for edge in j['edges']:
        objects[edge['obj']].append(edge['sub'])

    subjects = defaultdict(list)
    for edge in j['edges']:
        subjects[edge['sub']].append(edge['obj'])

    if root not in nodes and root is not None:
        root = OntId(root).curie

    if direction == 'OUTGOING':  # flip for the tree
        objects, subjects = subjects, objects
    elif direction == 'BOTH':  # FIXME BOTH needs help!
        from pprint import pprint
        pprint(subjects)
        pprint(objects)
        pass

    # something is wrong with how we are doing subClassOf, see PAXRAT: INCOMING
    if root is not None:
        subjects[root] = ['ROOT']
        subjects = pruneOutOfTree(subjects, verbose)
        subjects[root] = []  # FIXME if OUTGOING maybe??

    ss, so = set(subjects), set(objects)
    roots = so - ss
    leaves = ss - so

    if root is None:
        if len(roots) == 1:
            root = next(iter(roots))
        else:
            root = '*ROOT*'
            nodes[root] = 'ROOT'
            objects[root] = list(roots)

    names = {nodes[k]:[nodes[s] for s in v] for k,v in objects.items()}  # children don't need filtering
    pnames = {nodes[k]:[nodes[s] for s in v] for k,v in subjects.items()}
    return nodes, objects, subjects, names, pnames, edgerep, root, roots, leaves, pair_rel


def creatTree(root,
              relationshipType=None,
              direction='INCOMING',
              depth=1,
              graph=None,
              json=None,
              filter_prefix=None,
              prefixes=uPREFIXES,
              html_head=tuple(),
              local=False,
              verbose=False,
              curie=None,
              entail=True):
    sgg = graph
    html_head = list(html_head)
    # TODO FIXME can probably switch over to the inverse of the automata I wrote for parsing trees in parc...
    if json is None:
        j, root_iri = queryTree(root, relationshipType, direction, depth, entail,
                                sgg, filter_prefix, curie)
        # FIXME stick this on sgg ...
        # FIXME some magic nonsense for passing the last query to sgg out
        # yet another reason to objectify this (heh)
        html_head.append('<link rel="http://www.w3.org/ns/prov#'
                         f'wasDerivedFrom" href="{sgg._last_url}">')  # FIXME WARNING leaking keys
    else:
        root_iri = None
        j = dict(json)
        if relationshipType is not None:
            j['edges'] = [e for e in j['edges'] if e['pred'] == relationshipType]
        #if 'meta' in j['nodes'][0]:  # check if we are safe to check meta
            #flag_dep(j)

    # filter out owl:Nothing
    j['edges'] = [e for e in j['edges'] if 'owl:Nothing' not in e.values()]

    # filter out has part meta edges
    j['edges'] = [e for e in j['edges'] if not
                  ('meta' in e and
                   'owlType' in e['meta'] and
                   'http://purl.obolibrary.org/obo/BFO_0000051' in e['meta']['owlType'])]

    if verbose:
        print(len(j['nodes']))

    (nodes, objects, subjects, names, pnames,
     edgerep, root, roots, leaves, pair_rel) = process_nodes(j, root, direction, verbose)

    if root is None:
        breakpoint()

    rootsl = '\n'.join(roots)
    tree_name = f'{rootsl}{relationshipType}{direction}{depth}'

    Tree, _ = newTree(tree_name, parent_dict=subjects)
    hierarchy, dupes = build_tree(Tree, root, objects, subjects, existing={}, flat_tree=set())
    _, nTreeNode = newTree('names' + tree_name, parent_dict=pnames)  # FIXME pnames is wrong...

    def rename(tree):
        dict_ = nTreeNode()
        for k in tree:
            dict_[nodes[k]] = rename(tree[k])
        return dict_

    htmlNodes = makeHtmlNodes(nodes, sgg, prefixes, local, root_iri, root)
    hpnames = {htmlNodes[k]:[htmlNodes[s] for s in v] for k, v in subjects.items()}
    _, hTreeNode = newTree('html' + tree_name, parent_dict=hpnames, html_head=html_head)
    html_pair_rel = {tuple(htmlNodes[_] for _ in k):v for k, v in pair_rel.items()}

    def htmlTree(tree):
        dict_ = hTreeNode()
        for k in tree:
            dict_[htmlNodes[k]] = htmlTree(tree[k])
        return dict_

    try:
        named_hierarchy = rename(hierarchy)
        html_hierarchy = htmlTree(hierarchy)
    except KeyError as e:
        log.exception(e)
        breakpoint()
        raise e

    def sub_prefixes(h):
        if prefixes is not None:
            for n, p in prefixes.items():
                if type(p) != str:
                    p = str(p)
                h = h.replace('href="' + n + ':', 'href="' + p)
                h = h.replace('>' + p, '>' + n + ':')

        return h

    html_body = sub_prefixes(html_hierarchy.__html__(hpr=html_pair_rel))
    extras = Extras(hierarchy, html_hierarchy,
                    dupes, nodes, edgerep,
                    objects, subjects,
                    names, pnames, hpnames, j,
                    html_body, str(named_hierarchy))

    return named_hierarchy, extras


def makeHtmlNodes(nodes, sgg, prefixes, local, root_iri, root):
    htmlNodes = {}
    for k, v in nodes.items():
        if ':' in k and not k.startswith('http') and not k.startswith('file'):
            prefix, suffix = k.split(':', 1)
            prefix = prefix.replace('\x1b[91m', '')  # colors :/
            if sgg is not None and not suffix and k == root:  # FIXME 268
                url = os.path.join(sgg._basePath, 'vocabulary', 'id',
                                   quote(root_iri, safe=[]))
                                   #root_iri.replace('/','%2F').replace('#','%23'))
            elif sgg is not None and local:
                url = os.path.join(sgg._basePath, 'vocabulary', 'id', k)
            elif prefix == '_' and v is None:
                log.warning(f'BLANK NODES HAVE ENTERED THE DATABASE {root_iri}')
                v = 'BLANK NODE'
            else:
                try:
                    url = str(prefixes[prefix]) + suffix
                except KeyError as e:
                    log.exception(e)
                    url = k
        else:
            if sgg is not None and local:
                url = os.path.join(sgg._basePath, 'vocabulary', 'id',
                                   quote(k, safe=[]))
                                   #k.replace('/','%2F').replace('#','%23'))
            else:
                url = k

        if v is None:  # if there is no label fail over to the url
            v = f'<{url}>'
        htmlNodes[k] = '<a target="_blank" href="{}">{}</a>'.format(url, html_escape(v))

    return htmlNodes


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

def flatten(tree, out=None):
    if out is None:
        out = []
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
    from pyontutils.scigraph import Graph
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


        breakpoint()
        return

    uberon = Query('UBERON:0000955', 'BFO:0000050', 'INCOMING', 40)
    uberon_tree, uberon_extra = creatTree(*uberon, graph=sgg)
    queries = uberon,

    uberon_flat = sorted(set(n for n in flatten(uberon_extra[0])))
    with open(f'{tempfile.tempdir}/uberon_partonomy_terms', 'wt') as f:
        f.writelines('\n'.join(uberon_flat))

    for query in queries:
        tree, extra = creatTree(*query, graph=sgg)
        dematerialize(list(tree.keys())[0], tree)
        print(tree)
        #print(extra[0])
        with open(f'{tempfile.tempdir}/' + query.root, 'wt') as f:
            f.writelines(tree.print_tree())

        level_sizes = [len(levels(tree, i)) for i in range(11)]
        print('level sizes', level_sizes)
        parent_counts = sorted(set(len(v) for v in extra[-4].values()))
        print('unique parent counts', parent_counts)
        print('num terms', len(extra[2]))

    return

    breakpoint()

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
    #breakpoint()


    #fma = Query('FMA:50801', 'None', 'INCOMING', 20)
    fma = Query('FMA:61817', 'None', 'INCOMING', 20)  # Cerebral hemisphere
    fma_tree, fma_extra = creatTree(*fma, json=json)
    with open(f'{tempfile.tempdir}/rc_combo_tree', 'wt') as f: f.write(str(fma_tree))

    breakpoint()

if __name__ == '__main__':
    main()
