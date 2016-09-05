#!/usr/bin/env python3.5
"""
    A collection of reused functions and classes.
"""

import os
import re
import asyncio
import inspect
from functools import wraps
from multiprocessing import Manager
import rdflib
from rdflib.extras import infixowl

def async_getter(function, listOfArgs):
    async def future_loop(future_):
        loop = asyncio.get_event_loop()
        futures = []
        for args in listOfArgs:
            future = loop.run_in_executor(None, function, *args)
            futures.append(future)
        print('Futures compiled')
        responses = []
        for f in futures:
            responses.append(await f)
        future_.set_result(responses)
    future = asyncio.Future()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(future_loop(future))
    return future.result()

def mysql_conn_helper(host, db, user, port=3306):
    kwargs = {
        'host':host,
        'db':db,
        'user':user,
        'port':port,
        'password':None,  # no you may NOT pass it in
    }
    with open(os.path.expanduser('~/.mypass'), 'rt') as f:
        entries = [l.strip().split(':', 4) for l in f.readlines()]
    for e_host, e_port, e_db, e_user, e_pass in entries:
        e_port = int(e_port)
        if host == e_host:
            print('yes:', host)
            if  port == e_port:
                print('yes:', port)
                if db == e_db or e_db == '*':  # FIXME bad * expansion
                    print('yes:', db)
                    if user == e_user:
                        print('yes:', user)
                        kwargs['password'] = e_pass  # last entry wins
    e_pass = None
    if kwargs['password'] is None:
        raise ConnectionError('No password as found for {user}@{host}:{port}/{db}'.format(**kwargs))

    return kwargs

class makeGraph:
    SYNONYM = 'OBOANN:synonym'  # dangerous with prefixes

    def __init__(self, name, prefixes):
        self.name = name
        self.namespaces = {p:rdflib.Namespace(ns) for p, ns in prefixes.items()}
        self.g = rdflib.Graph()
        [self.g.namespace_manager.bind(p, ns) for p, ns in prefixes.items()]

    @property
    def filename(self):
        return '/tmp/' + self.name + '.ttl'

    def write(self, convert=True):
        with open(self.filename, 'wb') as f:
            f.write(self.g.serialize(format='turtle'))
            print('yes we wrote the first version...', self.name)
        if hasattr(self.__class__, '_to_convert'):
            self.__class__._to_convert.append(self.filename)
        elif convert:  # this will confuse everyone, convert=False still runs if in side the with block...
            self.owlapi_conversion((self.filename,))

    def owlapi_conversion(self, files):
        os.system('java -cp ' +
            os.path.expanduser('~/git/ttl-convert/target/'
                               'ttl-convert-1.0-SNAPSHOT-jar-with-dependencies.jar') +
                  ' scicrunch.App ' + ' '.join(files))

    def expand(self, curie):
        prefix, suffix = curie.split(':',1)
        if prefix not in self.namespaces:
            raise KeyError('Namespace prefix does exist:', prefix)
        return self.namespaces[prefix][suffix]

    def check_thing(self, thing):
        if type(thing) != rdflib.term.URIRef and type(thing) != rdflib.term.BNode:
            try:
                return self.expand(thing)
            except (KeyError, ValueError) as e:
                if thing.startswith('http') and ' ' not in thing:  # so apparently some values start with http :/
                    return rdflib.URIRef(thing)
                else:
                    raise TypeError('Unknown format:', thing)
        else:
            return thing

    def add_ont(self, ontid, label, shortName=None, comment=None, version=None):
        self.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
        self.add_node(ontid, rdflib.RDFS.label, label)
        if comment:
            self.add_node(ontid, rdflib.RDFS.comment, comment)
        if version:
            self.add_node(ontid, rdflib.OWL.versionInfo, version)
        if shortName:
            self.add_node(ontid, rdflib.namespace.SKOS.altLabel, shortName)

    def add_class(self, id_, subClassOf=None, synonyms=tuple(), label=None, autogen=False):
        self.add_node(id_, rdflib.RDF.type, rdflib.OWL.Class)
        if autogen:
            label = ' '.join(re.findall(r'[A-Z][a-z]*', id_.split(':')[1]))
        if label:
            self.add_node(id_, rdflib.RDFS.label, label)
        if subClassOf:
            self.add_node(id_, rdflib.RDFS.subClassOf, subClassOf)

        [self.add_node(id_, self.SYNONYM, s) for s in synonyms]

    def add_op(self, id_, label=None, subPropertyOf=None, inverse=None, transitive=False):
        self.add_node(id_, rdflib.RDF.type, rdflib.OWL.ObjectProperty)
        if inverse:
            self.add_node(id_, rdflib.OWL.inverseOf, inverse)
        if subPropertyOf:
            self.add_node(id_, rdflib.RDFS.subPropertyOf, subPropertyOf)
        if label:
            self.add_node(id_, rdflib.RDFS.label, label)
        if transitive:
            self.add_node(id_, rdflib.RDF.type, rdflib.OWL.TransitiveProperty)

    def add_node(self, target, edge, value):
        if not value:  # no empty values!
            return
        target = self.check_thing(target)
        edge = self.check_thing(edge)
        try:
            if value.startswith(':') and ' ' in value:  # not a compact repr AND starts with a : because humans are insane
                value = ' ' + value
            value = self.check_thing(value)
        except (TypeError, AttributeError) as e:
            value = rdflib.Literal(value)  # trust autoconv
        self.g.add( (target, edge, value) )

    def add_hierarchy(self, parent, edge, child):
        """ Helper function to simplify the addition of part_of style
            objectProperties to graphs. FIXME make a method of makeGraph?
        """
        if type(parent) != rdflib.URIRef:
            parent = self.check_thing(parent)

        if type(edge) != rdflib.URIRef:
            edge = self.check_thing(edge)

        if type(child) != infixowl.Class:
            if type(child) != rdflib.URIRef:
                child = self.check_thing(child)
            child = infixowl.Class(child, graph=self.g)

        restriction = infixowl.Restriction(edge, graph=self.g, someValuesFrom=parent)
        child.subClassOf = [restriction] + [c for c in child.subClassOf]

    def get_equiv_inter(self, curie):
        """ get equivelant classes where curie is in an intersection """
        start = self.expand(curie)
        linkers = [t[0] for t in self.g.triples((None, None, start)) if type(t[0]) is rdflib.BNode]  # RDF.first?
        subjects = []
        for linker in linkers:
            linker2 = list(self.g.subjects(rdflib.OWL.intersectionOf, linker))
            assert len(linker2) == 1
            linker2 = linker2[0]
            subject = list(self.g.subjects(rdflib.OWL.equivalentClass, linker2))
            assert len(subject) == 1
            subject = subject[0]
            subjects.append(subject)

        return subjects

    def make_scigraph_json(self, edge, label_edge=None, direct=False):  # for checking trees
        if label_edge is None:
            label_edge = rdflib.RDFS.label
        else:
            label_edge = self.expand(label_edge)
        json_ = {'nodes':[], 'edges':[]}
        restriction = self.expand(edge)
        if direct:
            trips = list(self.g.triples((None, restriction, None)))
            done = []
            for obj, pred, sub in trips:
                try:
                    olab = list(self.g.objects(obj, label_edge))[0].toPython()
                except IndexError:  # no label
                    olab = obj.toPython()
                try:
                    slab = list(self.g.objects(sub, label_edge))[0].toPython()
                except IndexError:  # no label
                    slab = sub.toPython()

                obj = self.g.namespace_manager.qname(obj)
                sub = self.g.namespace_manager.qname(sub)
                json_['edges'].append({'sub':sub,'pred':edge,'obj':obj})
                if sub not in done:
                    node = {'lbl':slab,'id':sub, 'meta':{}}
                    #if sdep: node['meta'][rdflib.OWL.deprecated.toPython()] = True
                    json_['nodes'].append(node)
                    done.append(sub)
                if obj not in done:
                    node = {'lbl':olab,'id':obj, 'meta':{}}
                    #if odep: node['meta'][rdflib.OWL.deprecated.toPython()] = True
                    json_['nodes'].append(node)
                    done.append(obj)
            return json_

        linkers = list(self.g.subjects(rdflib.OWL.onProperty, restriction))
        done = []
        for linker in linkers:
            try:
                obj = list(self.g.objects(linker, rdflib.OWL.someValuesFrom))[0]
            except IndexError:
                obj = list(self.g.objects(linker, rdflib.OWL.allValuesFrom))[0]
            if type(obj) != rdflib.term.URIRef:
                continue  # probably encountere a unionOf or something and don't want
            try:
                olab = list(self.g.objects(obj, label_edge))[0].toPython()
            except IndexError:  # no label
                olab = obj.toPython()
            odep = True if list(self.g.objects(obj, rdflib.OWL.deprecated)) else False
            obj = self.g.namespace_manager.qname(obj)
            sub = list(self.g.subjects(rdflib.RDFS.subClassOf, linker))[0]
            try:
                slab = list(self.g.objects(sub, label_edge))[0].toPython()
            except IndexError:  # no label
                slab = sub.toPython()
            sdep = True if list(self.g.objects(sub, rdflib.OWL.deprecated)) else False
            sub = self.g.namespace_manager.qname(sub)
            json_['edges'].append({'sub':sub,'pred':edge,'obj':obj})
            if sub not in done:
                node = {'lbl':slab,'id':sub, 'meta':{}}
                if sdep: node['meta'][rdflib.OWL.deprecated.toPython()] = True
                json_['nodes'].append(node)
                done.append(sub)
            if obj not in done:
                node = {'lbl':olab,'id':obj, 'meta':{}}
                if odep: node['meta'][rdflib.OWL.deprecated.toPython()] = True
                json_['nodes'].append(node)
                done.append(obj)

        return json_

    def __enter__(self):
        m = Manager()
        self.__class__._to_convert = m.list()
        return self

    def __exit__(self, type, value, traceback):
        self.owlapi_conversion(sorted(set(self.__class__._to_convert)))

def chunk_list(list_, size):
    """ Split a list list_ into sublists of length size.
        NOTE: len(chunks[-1]) <= size. """
    ll = len(list_)
    chunks = []
    for start, stop in zip(range(0, ll, size), range(size, ll, size)):
        chunks.append(list_[start:stop])
    chunks.append(list_[stop:])  # snag unaligned chunks from last stop
    return chunks

class dictParse:
    """ Base class for building dict parsers (that can also handle lists).
        Methods should be named after the keys in the dict and specify
        what to do with the contents.
    """
    def __init__(self, thing, order=[]):
        if type(thing) == dict:
            if order:
                for key in order:
                    func = getattr(self, key, None)
                    if func:
                        func(thing.pop(key))
            self._next_dict(thing)

        #elif type(thing) == list:
            #self._next_list(thing)
        else:
            print('NOPE')

    def _next_dict(self, dict_):
        for key, value in dict_.items():
            func = getattr(self, key, None)
            if func:
                func(value)

    def _next_list(self, list_):
        for value in list_:
            if type(value) == dict:
                self._next_dict(value)

    def _terminal(self, value):
        print(value)
        pass

class rowParse:
    """ Base class for parsing a list of fixed lenght lists whose
        structure is defined by a header (eg from a csv file).
        Methods should match the name of the 'column' header.
    """

    class SkipError(BaseException):
        pass

    def __init__(self, rows, header=None, order=[]):
        if header is None:
            header = [c.split('(')[0].strip().replace(' ','_').replace('+','') for c in rows[0]]
            rows = rows[1:]
        eval_order = []
        self._index_order = []
        for column in order:
            index = header.index(column)
            self._index_order.append(index)
            eval_order.append(header.pop(index))
        eval_order.extend(header)  # if not order then just do header order

        self.lookup = {index:name for index, name in enumerate(eval_order)}

        for name, obj in inspect.getmembers(self):
            if inspect.ismethod(obj) and not name.startswith('_'):  # FIXME _ is hack
                _set = '_set_' + name
                setattr(self, _set, set())
                @wraps(obj)
                def getunique(value, set_=_set, func=obj):  # ah late binding hacks
                    getattr(self, set_).add(value)
                    return func(value)
                setattr(self, name, getunique)

        self._next_rows(rows)
        self._end()

    def _order_enumerate(self, row):
        i = 0
        for index in self._index_order:
            yield i, row.pop(index)
            i += 1
        for value in row:
            yield i, value
            i += 1

    def _next_rows(self, rows):
        for self._rowind, row in enumerate(rows):
            skip = False
            for i, value in self._order_enumerate(row):
                func = getattr(self, self.lookup[i], None)
                if func:
                    try:
                        func(value)
                    except self.SkipError:
                        skip = True  # ick
                        break
            if not skip:
                self._row_post()

    def _row_post(self):
        """ Run this code after all columns have been parsed """
        pass

    def _end(self):
        """ Run this code after all rows have been parsed """
        pass

class _TermColors:
    ENDCOLOR = '\033[0m'
    colors = dict(
    BOLD = '\033[1m',
    FAINT = '\033[2m',  # doesn't work on urxvt
    IT = '\033[3m',
    UL = '\033[4m',
    BLINKS = '\033[5m',
    BLINKF = '\033[6m',  # same as S?
    REV = '\033[7m',
    HIDE = '\033[8m',  # doesn't work on urxvt
    XOUT = '\033[9m',  # doesn't work on urxvt
    FONT1 = '\033[10m',  # doesn't work on urxvt use '\033]50;%s\007' % "fontspec"
    FONT2 = '\033[11m',  # doesn't work on urxvt
    FRAKTUR = '\033[20m',  # doesn't work on urxvt
    OFF_BOLD = '\033[21m',
    NORMAL = '\033[22m',
    OFF_IT = '\033[23m',
    OFF_UL = '\033[24m',
    OFF_BLINK = '\033[25m',
    POSITIVE = '\033[27m',
    OFF_HIDE = '\033[28m',
    RED = '\033[91m',
    GREEN = '\033[92m',
    YELLOW = '\033[93m',
    BLUE = '\033[94m',
    )

    def __init__(self):
        for color, esc in self.colors.items():  # esc blocks runtime changes
            def latebindingfix(string, e=esc):
                return self.endcolor(e + string)
            setattr(self, color.lower(), latebindingfix)

    def endcolor(self, string):
        if string.endswith(self.ENDCOLOR):
            return string
        else:
            return string + self.ENDCOLOR

TermColors = _TermColors()

class scigPrint:

    _shorten_ = {
        'PR':'http://purl.obolibrary.org/obo/PR_',
        'dc':'http://purl.org/dc/elements/1.1/',
        'owl':'http://www.w3.org/2002/07/owl#',
        'rdfs':'http://www.w3.org/2000/01/rdf-schema#',
        'skos':'http://www.w3.org/2004/02/skos/core#',
        'NIFGA':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-GrossAnatomy.owl#',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        'OBOOWL':'http://www.geneontology.org/formats/oboInOwl#',
        'NIFSUB':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Subcellular.owl#',
        'UBERON':'http://purl.obolibrary.org/obo/UBERON_',
        'BIRNANN':'http://ontology.neuinfo.org/NIF/Backend/BIRNLex_annotation_properties.owl#',
        'NCBITaxon':'http://purl.obolibrary.org/obo/NCBITaxon_',
        'BRAINInfo':'http://braininfo.rprc.washington.edu/centraldirectory.aspx?ID=',
    }

    shorten = {v:k for k, v in _shorten_.items()}

    @staticmethod
    def wrap(string, start, ind, wrap_=80):
        if len(string) + start <= wrap_:
            return string
        else:
            out = ''
            ends = [_ for _ in range(wrap_ - start, len(string), wrap_ - ind - 4)] + [None]
            starts = [0] + [e for e in ends]
            blocks = [string[s:e] if e else string[s:] for s, e in zip(starts, ends)]
            return ('\n' + ' ' * (ind + 4)).join(blocks)

    @staticmethod
    def sv(asdf, start, ind):
        if type(asdf) is not bool and asdf.startswith('http'):
            for iri, short in scigPrint.shorten.items():
                if iri in asdf:
                    return scigPrint.wrap(asdf.replace(iri, short + ':'), start, ind)
            print('YOU HAVE FAILED!?', asdf)
            return scigPrint.wrap(repr(asdf), start, ind)
        else:
            return scigPrint.wrap(repr(asdf), start, ind)

    @staticmethod
    def pprint_node(node):
        node = node['nodes'][0]  # no edges here...
        print('---------------------------------------------------')
        print(node['id'], '  ', node['lbl'])
        print()
        for k, v in sorted(node['meta'].items()):
            for iri, short in scigPrint.shorten.items():
                if iri in k:
                    k = k.replace(iri, short + ':')
                    break
            if v:
                asdf = v[0]

                if len(v) > 1:
                    print(' ' * 4 + '%s:' % k, '[')
                    _ = [print(' ' * 8 + scigPrint.sv(_, 8, 8)) for _ in v]
                    print(' ' * 4 + ']')
                else:
                    base = ' ' * 4 + '%s:' % k
                    print(base, scigPrint.sv(asdf, len(base) + 1, 4))

        print()

