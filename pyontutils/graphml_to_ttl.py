#!/usr/bin/env python3.6
"""convert graphml files to ttl files

Usage:
    graphml-to-ttl [options] <file>
    graphml-to-ttl methods [options] <file>

Options:
    -o --output-location=LOC    write converted files to [default: /tmp/]

"""
import os
import re
from collections import namedtuple
from docopt import docopt
from lxml import etree
from rdflib import URIRef, RDFS, Namespace
from IPython import embed
from pyontutils.core import makeGraph, makePrefixes, createOntology, rdf, rdfs, owl
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
            label, *_ = label if label else [None]
            yield (id, style_type, style_width, label)

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
            source_a = None if source_a == 'none' else source_a
            target_a = None if target_a == 'none' else target_a
            label, *_ = label if label else [None]
            yield (id, s, o, style_type, style_width, source_a, target_a, label)


workflow = Namespace('https://uri.interlex.org/scibot/uris/readable/workflow/')
RRIDCUR = Namespace('https://uri.interlex.org/scibot/uris/readable/RRIDCUR/')


class WorkflowMapping(Flatten):

    def base(self):
        a = rdf.type
        yield workflow.hasNextStep, a, owl.ObjectProperty
        yield workflow.hasTag, a, owl.ObjectProperty
        yield workflow.hasReplyTag, a, owl.ObjectProperty
        yield workflow.hasTagOrReplyTag, a, owl.ObjectProperty

        wf = workflow
        yield wf.annotation, a, owl.Class
        yield wf.pageNote, a, owl.Class
        yield wf.reply, a, owl.Class
        yield wf.tag, a, owl.Class

    def nodes(self):
        for id, style_type, style_width, label in super().nodes():
            s = id
            yield s, rdf.type, owl.Class
            if style_type == 'dashed':
                yield 'TODO', 'TODO', 'TODO'
            elif (style_type, style_width) == ('line', '1.0'):
                if label == 'RRID:':
                    yield 'TODO', 'TODO', 'TODO'

    def edges(self):
        for id, s, o, style_type, style_width, source, target, label in super().edges():
            # this is where we really want case again :/
            if style_type == 'dashed':
                p = workflow.hasNextStep
            elif (style_type, style_width) == ('dashed_dotted', '2.0'):
                p = workflow.hasTag
                #yield o, rdfs.subClassOf, workflow.tag
            elif (style_type, style_width) == ('line', '1.0'):
                p = workflow.hasReplyTag
            elif (style_type, style_width) == ('line', '2.0'):  # TODO may need arrow
                p = workflow.hasTagOrReplyTag

            yield s, p, o


line_style_type_to_oop = {  # for workflows
                          'dashed':'workflow:next',
}

border_type_to_class = {  # for workflows
                        'line':'workflow:annotation-or-reply',
                        'dashed':'workflow:action',
}

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
    print(args)
    outloc = args['--output-location']
    filename = os.path.splitext(os.path.basename(args['<file>']))[0]
    parser = etree.XMLParser(remove_blank_text=True)
    e = etree.parse(args['<file>'], parser)
    graph = e.find(abv['graph'])
    #nodes = graph.findall(abv['node'])
    #edges = graph.findall(abv['edge'])

    nodes = xpath(e, '//'+abv['node'])
    edges = xpath(e, '//'+abv['edge'])

    w = WorkflowMapping(args['<file>'])
    ns = list(w.nodes())
    es = list(w.edges())

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

    newgraph = makeGraph(filename, prefixes=PREFIXES, writeloc=outloc)
    for et in set(edge_to_ttl.values()):
        if et != 'SKIP':
            newgraph.add_op(et)

    for eid, (source, target, edge_type) in edge_dict.items():
        node_dict[source][1].append((edge_type, target))
        #print(source, edge_type, target)
        if edge_type == 'SKIP':
            newgraph.add_trip(source, 'rdf:type', 'owl:Class')
        elif edge_type is not None:
            newgraph.add_class(source)
            newgraph.add_class(target)
            try:
                if edge_type == 'rdfs:subClassOf':
                    newgraph.add_trip(source, edge_type, target)
                else:
                    newgraph.add_hierarchy(target, edge_type, source)
            except ValueError as e:
                raise ValueError(f'{source} {edge_type} {target}') from e

        label = node_dict[source][0]

        if '(id' in label:
            label, rest = label.split('(id')
            id_, rest = rest.split(')', 1)
            newgraph.add_trip(source, 'FIXME:REPLACEID', id_)
            label = label.strip() + rest.strip()
        if '(syns' in label:
            label, rest = label.split('(syns')
            syns, rest = rest.split(')', 1)
            if ',' in syns:
                syns = [newgraph.add_trip(source,'NIFRID:synonym',s.strip()) for s in syns.split(',') if s]  #FIXME
            else:
                syns = [newgraph.add_trip(source,'NIFRID:synonym',s) for s in syns.split(' ') if s]  #FIXME
            label = label.strip() + rest.strip()
        if '(note' in label:
            while '(note' in label:
                label, rest = label.split('(note', 1)
                note, rest = rest.split(')', 1)
                newgraph.add_trip(source, 'rdfs:comment', note)
                label = label.strip() + rest.strip()
        if '(def' in label:
            label, rest = label.split('(def')
            def_, rest = rest.split(')', 1)
            def_ = def_.replace('\n', ' ')
            newgraph.add_trip(source, 'NIFRID:definition', def_.strip())
            label = label.strip() + rest
        if '#FIXME' in label:
            label, note = label.split('#FIXME')
            label = label.replace('\n','').strip()
            note = note.replace('\n',' ').strip()
            newgraph.add_trip(source, 'rdfs:comment', note)
        if args['methods']:
            clabel = label.capitalize()
        else:
            clabel = label
        newgraph.add_trip(source, 'rdfs:label', clabel)

    newgraph.write()
    if args['methods']:
        Query = namedtuple('Query', ['root','relationshipType','direction','depth'])
        json = newgraph.make_scigraph_json('rdfs:subClassOf', direct=True)
        t, te = creatTree(*Query('FIXME:n0', 'rdfs:subClassOf', 'INCOMING', 20), json=json)  # methods
        t, te = creatTree(*Query('FIXME:n236', 'rdfs:subClassOf', 'INCOMING', 20), json=json)  # techniques
        print(t)

        with open(os.path.join(outloc, filename + '.txt'), 'wt') as f:
            f.write(str(t))
        with open(os.path.join(outloc, filename + '.html'), 'wt') as f:
            f.write(te.html)

if __name__ == '__main__':
    main()
