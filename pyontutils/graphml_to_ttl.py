#!/usr/bin/env python3.6
"""convert graphml files to ttl files

Usage:
    graphml-to-ttl [options] <file>
    graphml-to-ttl methods [options] <file>
    graphml-to-ttl workflow [options] <file>
    graphml-to-ttl paper [options] <file>

Options:
    -o --output-location=LOC    write converted files to [default: /tmp/]

"""
import os
import re
from itertools import chain
from collections import namedtuple, defaultdict
from lxml import etree
from docopt import docopt
from rdflib import URIRef, BNode, Namespace, Graph
from IPython import embed
from pyontutils.core import makeGraph
from pyontutils.qnamefix import cull_prefixes
from pyontutils.namespaces import makePrefixes, TEMP, PREFIXES as uPREFIXES
from pyontutils.combinators import restriction, restrictionN, allDifferent, members, unionOf, oneOf
from pyontutils.closed_namespaces import rdf, rdfs, owl
from pyontutils.hierarchies import creatTree

#from check_ids import safe_write  # that file very deprecated, pull safewrite out if you really need it

abv = {
    'graphml':"{http://graphml.graphdrawing.org/xmlns}graphml",
    'graph':"{http://graphml.graphdrawing.org/xmlns}graph",
    'node':"{http://graphml.graphdrawing.org/xmlns}node",
    'edge':"{http://graphml.graphdrawing.org/xmlns}edge",
    'data':"{http://graphml.graphdrawing.org/xmlns}data",
    'ShapeNode':'{http://www.yworks.com/xml/graphml}ShapeNode',
    'NodeLabel':"{http://www.yworks.com/xml/graphml}NodeLabel",
    'BorderStyle':"{http://www.yworks.com/xml/graphml}BorderStyle",
    'PolyLineEdge':"{http://www.yworks.com/xml/graphml}PolyLineEdge",
    'EdgeLabel':"{http://www.yworks.com/xml/graphml}EdgeLabel",
    'LineStyle':"{http://www.yworks.com/xml/graphml}LineStyle",
}

edge_to_ttl = {
    'is_a':'rdfs:subClassOf',
    'is-a':'rdfs:subClassOf',
    'part of':'BFO:0000050',
    'on_property':'FIXME:onProperty',
    'ROOT':'SKIP',
    'realizes':'FIXME:realizses',
    'executes/implements/realizes':'FIXME:realizes',
    'executed by/implemented by/realized by':'FIXME:realizedBy',
    'describes':'FIXME:describes',
    'described by':'FIXME:describedBy',
    'specified by':'FIXME:specifiedBy',
    'specifies':'FIXME:specifies',
    'a way of realizing':'FIXME:realizes',
    'can be realized by':'FIXME:realizedBy',
    'can specify':'FIXME:specifies',
    'assoc_method':'FIXME:assoc_method',  # FIXME
    'assoc_system':'FIXME:associatedNeuralSystem',
    'assoc_measurement':'FIXME:associatedMeasurement',  # FIXME
    'is_produced_by':'FIXME:producedBy',  # FIXME
    'symbolizes':'FIXME:symbolizes',
    'assoc_measureable':'FIXME:assoc_measureable',  # FIXME
}
edge_replace = lambda a: edge_to_ttl[a] if a in edge_to_ttl else a  # FIXME it is time to abstract this...


def by2(one, two, *rest):
    yield one, two
    yield from by2(*rest)


class Flatten:
    def __init__(self, filename):
        self.filename = os.path.splitext(os.path.basename(filename))[0]
        parser = etree.XMLParser(remove_blank_text=True)
        self.e = etree.parse(filename, parser)

        self.namespaces = {k if k else '_':v for k, v in next(self.e.iter()).nsmap.items()}
        self.xpath = self.mkx(self.e)

    def mkx(self, element):
        def xpath(path, e=element):
            return e.xpath(path, namespaces=self.namespaces)

        return xpath

    def nodes(self):
        # this works but would require a by_n function
        #self.xpath('//_:node/@id|//_:node//y:BorderStyle/@type|'
        #'//_:node//y:BorderStyle/@width|//_:node//y:NodeLabel/text()[1]')
        for node in self.xpath('//_:node'):
            xpath = self.mkx(node)
            id, style_type, style_width, *label = xpath(
                '@id|'
                '_:data//y:BorderStyle/@type|'
                '_:data//y:BorderStyle/@width|'
                '_:data//y:NodeLabel/text()[1]'
            )
            # see key definition section of a graphml file for key defs
            maybe_url = xpath('_:data[@key="d4"]/text()')
            url = maybe_url[0] if maybe_url else None
            maybe_desc = xpath('_:data[@key="d5"]/text()')
            desc = maybe_desc[0] if maybe_desc else None
            label, *_ = label if label else [None]
            yield (id, style_type, style_width, label, desc, url)

    def edges(self):
        for edge in self.xpath('//_:edge'):
            xpath = self.mkx(edge)
            id, s, o, style_type, style_width, source_a, target_a, *label = xpath(
                '@id|@source|@target|'
                '_:data//y:LineStyle/@type|'
                '_:data//y:LineStyle/@width|'
                '_:data//y:Arrows/@source|'
                '_:data//y:Arrows/@target|'
                '_:data//y:EdgeLabel/text()'
            )
            # see key definition section of a graphml file for key defs
            maybe_url = xpath('_:data[@key="d8"]/text()')
            url = maybe_url[0] if maybe_url else None
            maybe_desc = xpath('_:data[@key="d9"]/text()')
            desc = maybe_desc[0] if maybe_desc else None
            source_a = None if source_a == 'none' else source_a
            target_a = None if target_a == 'none' else target_a
            label, *_ = label if label else [None]
            yield (id, s, o, style_type, style_width, source_a, target_a, label, desc, url)


class TripleExport:

    @property
    def triples(self):
        for s, p, o in self.base():
            if p == a:
                self.types[s] = o
            yield s, p, o

        for s, p, o in self.nodes():
            if p == a:
                self.types[s] = o
            yield s, p, o

        yield from self.edges()
        yield from self.post()

    def graph(self, graph=Graph()):
        [graph.add(t) for t in self.triples]
        self.post_graph(graph)
        out_mgraph = cull_prefixes(graph,
                                   prefixes={**dict(workflow=workflow, RRIDCUR=RRIDCUR),
                                             **uPREFIXES})

        for c, i in out_mgraph.g.namespaces():  # will add but not take away
            graph.bind(c, i)

        return out_mgraph.g


workflow = Namespace('https://uri.interlex.org/scibot/uris/readable/workflow/')
RRIDCUR = Namespace('https://uri.interlex.org/scibot/uris/RRIDCUR/')
a = rdf.type
wf = workflow


class WorkflowMapping(Flatten, TripleExport):

    def __init__(self, filename):
        super().__init__(filename)
        self.node_name_lookup = {}
        self.types = {}
        self.different_tags = set()
        self.edge_object_shift = {}  # s - o -> s - new_obj - o

    def insert_object(self, id, s_new):
        id_new = BNode()  # just an id
        self.edge_object_shift[id] = id_new
        self.node_name_lookup[id_new] = s_new

    def common(self):
        yield workflow.hasNextStep, a, owl.ObjectProperty
        yield workflow.hasTagOrReplyTag, a, owl.ObjectProperty
        yield workflow.hasTag, a, owl.ObjectProperty
        yield workflow.hasTag, rdfs.subPropertyOf, wf.hasTagOrReplyTag
        yield workflow.hasReplyTag, a, owl.ObjectProperty
        yield workflow.hasReplyTag, rdfs.subPropertyOf, wf.hasTagOrReplyTag

        yield workflow.hasOutput, a, owl.ObjectProperty
        yield workflow.hasOutputTag, a, owl.ObjectProperty
        yield workflow.hasOutputTag, rdfs.subPropertyOf, workflow.hasOutput
        yield workflow.hasOutputExact, a, owl.ObjectProperty
        yield workflow.hasOutputExact, rdfs.subPropertyOf, workflow.hasOutput

        yield wf.state, a, owl.Class

        yield wf.annotation, a, owl.Class
        yield wf.pageNote, a, owl.Class
        yield wf.exact, a, owl.Class
        yield wf.reply, a, owl.Class
        yield wf.tag, a, owl.Class
        isAttachedTo = restriction(wf.isAttachedTo, wf.annotation)
        yield from isAttachedTo(wf.exact)
        yield from isAttachedTo(wf.tag)
        refersTo = restriction(wf.refersTo, wf.annotation)
        yield from refersTo(wf.reply)
        yield wf.pageNoteInstance, a, wf.pageNote  # wf.exactNull ...

    def base(self):
        yield from self.common()

        yield workflow.initiatesAction, a, owl.ObjectProperty

        # FIXME these should not have to be asserted
        # but the order of nodes is all wrong :/
        yield RRIDCUR.Kill, a, wf.tagCurator
        yield RRIDCUR.Validated, a, wf.tagCurator
        yield RRIDCUR.UnresolvedCur, a, wf.tagScibot

        yield wf.tagScibot, a, owl.Class
        yield wf.tagScibot, rdfs.subClassOf, wf.tag
        yield wf.tagCurator, a, owl.Class
        yield wf.tagCurator, rdfs.subClassOf, wf.tag

        hasCurator = restriction(wf.isAttachedTo, restrictionN(wf.hasCurator, workflow.curator))
        yield from hasCurator(wf.tagCurator)

        yield wf.putativeRRID, a, owl.Class
        yield wf.scibotRRID, a, owl.Class
        yield wf.scibotRRID, rdfs.subClassOf, wf.putativeRRID
        yield wf.resolvingRRID, a, owl.Class
        yield wf.resolvingRRID, rdfs.subClassOf, wf.putativeRRID
        yield wf.canonicalRRID, a, owl.Class
        yield wf.canonicalRRID, rdfs.subClassOf, wf.resolvingRRID

        yield wf.RRID, a, wf.tagCurator

    def nodes(self):
        a = rdf.type
        for id, style_type, style_width, label, desc, url in super().nodes():
            s = None
            if desc == 'legend':
                continue
            if url:
                if url.startswith('exact'):
                    s = workflow[url]
                    yield s, a, workflow.exact
                elif url.startswith('RRIDscibot'):
                    s = workflow[url]
                    yield s, a, workflow.tagScibot
                elif any(url.startswith(prefix) for prefix in ('release', 'resolver')):
                    s = wf[url]
                else:
                    s = TEMP[url]
            else:
                if label == 'RRID:':
                    s = workflow['RRID']
                elif label.startswith('RRIDCUR:'):
                    s = RRIDCUR[label.split(':')[-1]]
                    self.different_tags.add(s)
                elif ' + ' in label:
                    suffixes = label.split(' + ')  # FIXME
                    s = BNode()
                    # union of is the right way to go here I think, because union
                    # implies that both must be present, not either or ...
                    yield from unionOf(*(workflow[sfx] for sfx in suffixes))(s)
                    #self.node_name_lookup[id] = s
                    #self.types[s] = wf.tag
                    #continue  # can't yield the type this node
                elif label in ('DOI', 'PMID'):
                    s = wf[label]
                    yield s, a, wf.tag
                else:
                    s = TEMP[label]

            if s is None:  # FIXME if this happens this late we don't get the error message
                raise ValueError(f'unhandled node {id} {lable}')
            else:
                self.node_name_lookup[id] = s

            #yield s, rdf.type, owl.Class
            if isinstance(s, BNode):
                #yield s, a, owl.NamedIndividual  # FIXME apparently this doesn't serializer properly ...
                yield s, a, wf.tag
            elif style_type == 'dashed':
                yield s, a, workflow.state
            elif (style_type, style_width) == ('line', '1.0'):
                pass
            elif (style_type, style_width) == ('line', '2.0'):
                pass
            elif (style_type, style_width) == ('dashed_dotted', '2.0'):
                #yield s, wf.isAttachedTo, wf.pageNote
                self.insert_object(id, wf.pageNoteInstance)
                yield wf.pageNoteInstance, wf.hasTag, s
                if s not in self.types:
                    yield s, a, wf.tagCurator
            elif (style_type, style_width) == ('dotted', '2.0'):
               # yield s, wf.isAttachedTo, wf.pageNote
                self.insert_object(id, wf.pageNoteInstance)
                yield wf.pageNoteInstance, wf.hasTag, s
                if s not in self.types:
                    yield s, a, wf.tagScibot
            else:
                msg = f'{id} {label} has unhandled type {style_type} {style_width}'
                raise ValueError(msg)

    def edges(self):
        for id, s_id, o_id, style_type, style_width, source, target, label, desc, url in super().edges():
            if o_id in self.edge_object_shift:
                o_id, __old = self.edge_object_shift[o_id], o_id
                #print('shifting', __old, self.node_name_lookup[__old])

            if desc == 'legend':
                continue
            s = self.node_name_lookup[s_id]
            p = None  # prevent poluation from previous loop
            o = self.node_name_lookup[o_id]
            # this is where we really want case again :/
            if style_type == 'dashed':
                # TODO if dashed -dashed-> line => line is scibot output
                if self.types[o] == wf.exact:
                    p = wf.hasOutputExact
                elif o == wf.pageNoteInstance:
                    p = wf.hasOutput
                elif self.types[s] in (wf.tagCurator, wf.tagScibot) and self.types[o] == wf.state:
                    p = wf.initiatesAction  # TODO naming
                elif self.types[o] in (wf.tag, wf.tagCurator, wf.tagScibot):
                    p = wf.hasOutputTag
                else:
                    p = workflow.hasNextStep

            elif (style_type, style_width) == ('dashed_dotted', '2.0'):
                p = workflow.hasTag
                if 'exactMaybeRRID' in s:  # FIXME doesn't generalize well...
                    yield o, a, workflow.tagScibot
                elif o not in self.types:
                    yield o, a, workflow.tagCurator
                else:
                    continue

            elif (style_type, style_width) == ('line', '1.0'):
                p = workflow.hasReplyTag
                if o not in self.types:
                    yield o, a, workflow.tagCurator

            elif (style_type, style_width) == ('dotted', '2.0'):
                p = workflow.hasNextStepRepeat

            elif (style_type, style_width) == ('line', '3.0'):  # TODO may need arrow
                p = workflow.hasTagOrReplyTag
                if o not in self.types:
                    yield o, a, workflow.tagCurator

            if p is None:
                msg = f'{s} {o} has unhandled predicate {style_type} {style_width}'
                raise ValueError(msg)

            yield s, p, o

    def post(self):
        yield from allDifferent(None, members(*self.different_tags))

    def post_graph(self, graph):
        for p in (wf.hasTag, wf.hasReplyTag, wf.hasTagOrReplyTag, wf.hasOutputTag):
            stags = defaultdict(set)
            for s, o, in graph[:p:]:
                stags[s].add(o)

            for s, oneof in stags.items():
                if len(oneof) > 1:
                    [graph.remove((s, p, o)) for o in oneof]
                    b = BNode()
                    graph.add((s, p, b))
                    graph.add((b, a, wf.tag))
                    # note that these are not owl semantics so it is unhappy
                    #graph.add((b, a, owl.NamedIndividual))
                    for t in oneOf(*oneof)(b):
                        graph.add(t)


class PaperIdMapping(WorkflowMapping):
    def base(self):
        yield from self.common()

        yield RRIDCUR.KillPageNote, a, wf.tagCurator  # FIXME hardcoded

        yield wf.DOI, a, wf.tag
        yield wf.PMID, a, wf.tag


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key = alphanum_key)


def xpath(node, expression):  # this is how to (sortof) do xpaths with the nasty uris
    return etree.ETXPath(expression)(node)


def make_ttl(node_dict):  # FIXME we need to deal with the prefixes earlier
    outputs = []
    for nid, (label, targets) in node_dict.items():
        TW = len(':%s ' % nid)
        out = '%s rdf:type owl:Class ;\n\n' % nid
        out += ' ' * TW
        out += 'rdfs:label "%s"@en ' % label.replace('\n','\\n')
        if len(targets):
            out += ';\n\n'
            for etype, target in targets:
                out += ' ' * TW
                #out += edge_to_ttl[etype] + ' :%s ; # %s\n\n' % (target, node_dict[target][0].replace('\n','\\n'))
                out += edge_replace(etype) + ' %s ;\n\n' % target

            #try:
                #out, comment = out.split('#',1)
                #out = out.rstrip(' \n').rstrip(';') + '. #%s\n\n' % comment
            #except:
            out = out.rstrip('\n').rstrip(';') + '.\n\n\n\n'

        else:
            out += '.\n\n\n\n'

        outputs.append(out)

    return ''.join(natural_sort(outputs))

# TODO identifier mapping needs to happen before here

PREFIXES = {**makePrefixes('owl','skos','BFO','NIFRID'), **{
    'FIXME':'http://fixme.org/',
}}
_PREFIXES = {
    'owl':'http://www.w3.org/2002/07/owl#',
    'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs':'http://www.w3.org/2000/01/rdf-schema#',
    'skos':'http://www.w3.org/2004/02/skos/core#',
    #'NIF':'http://uri.neuinfo.org/nif/nifstd/',  # for old ids??
    #'obo_annot':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  #FIXME OLD??
    #'oboInOwl':'http://www.geneontology.org/formats/oboInOwl#',  # these aren't really from OBO files but they will be friendly known identifiers to people in the community
}


def main():
    args = docopt(__doc__, version='0.1')
    outloc = args['--output-location']
    filename = os.path.splitext(os.path.basename(args['<file>']))[0]

    mgraph = makeGraph(filename, prefixes=uPREFIXES, writeloc=outloc)

    if args['workflow']:
        w = WorkflowMapping(args['<file>'])
        [mgraph.g.add(t) for t in w.triples]
        w.post_graph(mgraph.g)

    elif args['paper']:
        w = PaperIdMapping(args['<file>'])
        [mgraph.g.add(t) for t in w.triples]
        w.post_graph(mgraph.g)

    elif args['methods']:
        parser = etree.XMLParser(remove_blank_text=True)
        e = etree.parse(args['<file>'], parser)
        #graph = e.find(abv['graph'])
        nodes = xpath(e, '//'+abv['node'])
        edges = xpath(e, '//'+abv['edge'])
        node_dict = {}
        for node in nodes:  # slow but who cares
            id_ = node.get('id')
            #label = xpath(node, '//'+abv['NodeLabel'])[0].text
            idstr = '[@id="%s"]//' % id_
            label = xpath(e, '//'+abv['node']+idstr+abv['NodeLabel'])[0].text
            targets = []
            node_dict['FIXME:' + id_] = label, targets

        edge_dict = {}
        edge_types = set()
        for edge in edges:
            id_ = edge.get('id')
            #print(id_)
            idstr = '[@id="%s"]//' % id_
            source = 'FIXME:' + edge.get('source')
            target = 'FIXME:' + edge.get('target')
            out = xpath(edge, '//'+abv['edge']+idstr+abv['EdgeLabel'])
            edge_type = out[0].text if out else None
            #print(edge_type)
            edge_dict[id_] = source, target, edge_replace(edge_type)
            edge_types.add(edge_type)

        for et in set(edge_to_ttl.values()):
            if et != 'SKIP':
                mgraph.add_op(et)

        for eid, (source, target, edge_type) in edge_dict.items():
            node_dict[source][1].append((edge_type, target))
            #print(source, edge_type, target)
            if edge_type == 'SKIP':
                mgraph.add_trip(source, 'rdf:type', 'owl:Class')
            elif edge_type is not None:
                mgraph.add_class(source)
                mgraph.add_class(target)
                try:
                    if edge_type == 'rdfs:subClassOf':
                        mgraph.add_trip(source, edge_type, target)
                    else:
                        mgraph.add_hierarchy(target, edge_type, source)
                except ValueError as e:
                    raise ValueError(f'{source} {edge_type} {target}') from e

            label = node_dict[source][0]

            if '(id' in label:
                label, rest = label.split('(id')
                id_, rest = rest.split(')', 1)
                mgraph.add_trip(source, 'FIXME:REPLACEID', id_)
                label = label.strip() + rest.strip()
            if '(syns' in label:
                label, rest = label.split('(syns')
                syns, rest = rest.split(')', 1)
                if ',' in syns:
                    syns = [mgraph.add_trip(source,'NIFRID:synonym',s.strip()) for s in syns.split(',') if s]  #FIXME
                else:
                    syns = [mgraph.add_trip(source,'NIFRID:synonym',s) for s in syns.split(' ') if s]  #FIXME
                label = label.strip() + rest.strip()
            if '(note' in label:
                while '(note' in label:
                    label, rest = label.split('(note', 1)
                    note, rest = rest.split(')', 1)
                    mgraph.add_trip(source, 'rdfs:comment', note)
                    label = label.strip() + rest.strip()
            if '(def' in label:
                label, rest = label.split('(def')
                def_, rest = rest.split(')', 1)
                def_ = def_.replace('\n', ' ')
                mgraph.add_trip(source, 'NIFRID:definition', def_.strip())
                label = label.strip() + rest
            if '#FIXME' in label:
                label, note = label.split('#FIXME')
                label = label.replace('\n','').strip()
                note = note.replace('\n',' ').strip()
                mgraph.add_trip(source, 'rdfs:comment', note)
            if args['methods']:
                clabel = label.capitalize()
            else:
                clabel = label
            mgraph.add_trip(source, 'rdfs:label', clabel)

        Query = namedtuple('Query', ['root','relationshipType','direction','depth'])
        json = mgraph.make_scigraph_json('rdfs:subClassOf', direct=True)
        t, te = creatTree(*Query('FIXME:n0', 'rdfs:subClassOf', 'INCOMING', 20), json=json)  # methods
        t, te = creatTree(*Query('FIXME:n236', 'rdfs:subClassOf', 'INCOMING', 20), json=json)  # techniques
        print(t)

        with open(os.path.join(outloc, filename + '.txt'), 'wt') as f:
            f.write(str(t))
        with open(os.path.join(outloc, filename + '.html'), 'wt') as f:
            f.write(te.html)

    out_graph = cull_prefixes(mgraph.g,
                              prefixes={**dict(workflow=workflow, RRIDCUR=RRIDCUR),
                                        **uPREFIXES})
    out_graph.filename = mgraph.filename
    out_graph.write()


if __name__ == '__main__':
    main()
