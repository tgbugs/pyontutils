"""
    A collection of reused functions and classes.
"""

import os
import inspect
from functools import wraps
import rdflib
from rdflib.extras import infixowl

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
    def __init__(self, name, prefixes):
        self.name = name
        self.namespaces = {p:rdflib.Namespace(ns) for p, ns in prefixes.items()}
        self.g = rdflib.Graph()
        [self.g.namespace_manager.bind(p, ns) for p, ns in prefixes.items()]
        self.write_loc = '/tmp/ttl_files'

    def write(self, delay=False):
        with open('/tmp/' + self.name + '.ttl', 'wb') as f:
            f.write(self.g.serialize(format='turtle'))
        if delay:
            with open(self.write_loc, 'at') as f:
                f.write('/tmp/' + self.name + '.ttl\n')
        else:
            with open(self.write_loc, 'wt') as f:
                f.write('/tmp/' + self.name + '.ttl\n')
            self.owlapi_conversion()

    def owlapi_conversion(self):
        os.system('java -cp ' +
            os.path.expanduser('~/git/ttl-convert/target/'
                               'ttl-convert-1.0-SNAPSHOT-jar-with-dependencies.jar') +
                  ' scicrunch.App ' + self.write_loc)

    def reset_writeloc(self):
        with open(self.write_loc, 'wt') as f:
            f.write('')

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

    def add_node(self, target, edge, value):
        target = self.check_thing(target)
        edge = self.check_thing(edge)
        try:
            if value.startswith(':') and ' ' in value:  # not a compact repr AND starts with a : because humans are insane
                value = ' ' + value
            value = self.check_thing(value)
        except (TypeError, AttributeError) as e:
            value = rdflib.Literal(value)  # trust autoconv
        self.g.add( (target, edge, value) )

    def __enter__(self):
        self.reset_writeloc()
        return self

    def __exit__(self, type, value, traceback):
        self.owlapi_conversion()

def add_hierarchy(graph, parent, edge, child):
    """ Helper function to simplify the addition of part_of style
        objectProperties to graphs. FIXME make a method of makeGraph?
    """
    if type(child) != infixowl.Class:
        child = infixowl.Class(child, graph=graph)
    restriction = infixowl.Restriction(edge, graph=graph, someValuesFrom=parent)
    child.subClassOf = [restriction] + [c for c in child.subClassOf]

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

    def _order_enumerate(self, row):
        i = 0
        for index in self._index_order:
            yield i, row.pop(index)
            i += 1
        for value in row:
            yield i, value
            i += 1

    def _next_rows(self, rows):
        for row in rows:
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

