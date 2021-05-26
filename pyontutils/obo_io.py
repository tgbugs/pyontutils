#!/usr/bin/env python3
"""python .obo file parser and writer

Usage:
    obo-io [options] <obofile> [<output-name>]
    obo-io --help

Options:
    -h --help             show this
    -d --debug            break after parsing
    -t --out-format=FMT   output to this format
                          options are obo or ttl [default: obo]
    -o --overwrite        write the format, overwrite existing
    -w --write            write the output
    -s --strict           fail on missing definitions
    -r --robot            match the format produced by robot
    -n --no-stamp         do not add date, user, and program header stamp

based on the obo 1.2 / 1.4 (ish) spec defined at
https://owlcollab.github.io/oboformat/doc/GO.format.obo-1_2.html
https://owlcollab.github.io/oboformat/doc/GO.format.obo-1_4.html
lacks appropraite levels of testing for production use

acts as a command line script or as a python module
also converts to ttl format but the conversion convetions are ill defined

When writing a file if the path for the obofile exists it will not
overwrite what you have but instead will append a number to the end.

ALWAYS MANUALLY CHECK YOUR OUTPUT THIS SUCKER IS FLAKY
"""

#subsetdef: NAME "desc"
#synonymtypedef: NAME "desc" SCOPE
#idspace: NAME URI "desc"
#id-mapping: NAME TARGET

#def: "definition" [dbxrefs]
#subset: subsetdef  ! if it is not a subsetdef ParseError it
#synonym: "name" SCOPE synonymtypedef [xrefs]  ! parse error on no match a std
#xref: TODO
#is_a: #XXX we are not going to support all the other crazy stuff
#intersection_of: ! at least 2
#union_of: ! at least 2
#relationship: Typedef.id Term.id
#is_obsolete: ! true or false
#replaced_by: ! only if is_obsolete: true
#consider: ! only if is_obsolete: true

#dbxref: <name> "<description>" {modifiers}


####
# TODO
# add docopt support for conversion from obo -> ttl, probably should mve obo_tag_to_ttl to its own file?
# figure out how to properly manage references, specfically deleting, because callback hell is NOT the right way
# figure out how to multiple terms with the same id, there was a bug in how I generated the 2nd verion due to
    # the fact that the old ID was still used in the Terms od, on reloading we now fail
# __setter__ validation on value for non generated values needs to happen
# deal with how to initiailize a header (ie remove the of dependence?) maybe deferred relationshiph resolution could solve this?
# pass tvpairstores to tvpair so that we can walk all the way back up the chain if needs be
# nlx_qual_ is not getting split correctly to nlx_qual:

__title__ = 'obo-io'
__author__ = 'Tom Gillespie'

import os
import ast
import inspect
import pathlib
from types import MethodType
from datetime import datetime
from getpass import getuser
from collections import OrderedDict
import rdflib
from docopt import docopt
from pyontutils.core import OntId
from pyontutils.utils import makeSimpleLogger
from pyontutils.qnamefix import cull_prefixes
from pyontutils.namespaces import makeNamespaces, NIFRID, definition
from pyontutils.namespaces import TEMP, PREFIXES as uPREFIXES, OntCuries
from pyontutils.closed_namespaces import rdf, rdfs, owl, oboInOwl
try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint

log = makeSimpleLogger('obo-io')

fobo, obo, NIFSTD, NOPE = makeNamespaces('fobo', 'obo', 'NIFSTD', '')

N = type('N', (object,), dict(__repr__=lambda self: '<N many>'))()  # use to define 'many' for tag counts
TW = 4  # tab width

OBO_VER_DEFAULT = '1.4'
OBO_VER_ROBOT = '1.4-robot'


class od(OrderedDict):
    pass

od.__repr__ = dict.__repr__

# this is our current (horrible) conversion from obo to ttl
obo_tag_to_ttl = {
    #'id': (lambda s, p: rdflib.URIRef(s), rdf.type, owl.Class), '%s rdf:type owl:Class ;\n',
    'name': rdfs.label,
    'def': definition,
    'acronym': NIFRID.acronym,
    'synonym': NIFRID.synonym,
    'is_a': rdfs.subClassOf,
    'xref': oboInOwl.hasDbXref,
    #'xref':

}
def id_fix(value):
    """ fix @prefix values for ttl """
    if value.startswith('KSC_M'):
        if 'KSC_M' not in OntCuries:
            OntCuries({'KSC_M': 'http://uri.interlex.org/fakeobo/uris/obo/KSC_M_'})
    else:
        value = value.replace(':','_')
        if (value.startswith('ERO') or
            value.startswith('OBI') or
            value.startswith('GO') or
            value.startswith('UBERON') or
            value.startswith('IAO')):
            value = 'obo:' + value
        elif value.startswith('birnlex') or value.startswith('nlx'):
            value = 'NIFSTD:' + value
        elif value.startswith('MESH'):
            value = ':'.join(value.split('_'))
        else:
            value = ':' + value

    return OntId(value).URIRef


class OboFile:
    """ Python representation of the obo file structure split into tag-value
        pair stanzas the header is currently its own special stanza.
        type_def = ('<header>','<stanza>')

        Modifying the content of a loaded OboFile.

        Find the class that you want to modify using `t = of.Terms['PREFIX:12345467']`
        You can then access tags as python attributes. For example
        `t.xref += [TVPair('xref: ASDF:123 ! a new xref')]`.
    """

    def __init__(self, *args, path=None, data=None, header=None, terms=None,
                 typedefs=None, instances=None, strict=False):
        self.path = path
        self.Terms = od()
        self.Terms.names = {}
        self.Typedefs = od()
        self.Typedefs.names = {}
        self.Instances = od()
        self.Instances.names = {}
        self.Headers = od()  #LOL STUPID FIXME
        self.Headers.names = {}  # FIXME do not want? what about imports?
        if path is not None:  # FIXME could spec path here?
            if path.exists():  # FIXME decouple OboContainer and file via .parse
                if data is not None:
                    raise TypeError('path= and data= are mutually exclusive')
                #od_types = {type_.__name__:type_od for type_,type_od in zip((Term, Typedef, Instance),(self.Terms,self.Typedefs,self.Instances))}
                #LOL GETATTR
                with open(path, 'rt') as f:
                    data = f.read()

        if data is not None:
            #deal with \<newline> escape
            data = data.replace(' \n','\n')  # FXIME need for arbitrary whitespace
            data = data.replace('\<newline>\n',' ')
            # TODO remove \n!.+\n
            sections = data.split('\n[')
            header_block = sections[0]
            self.header = Header(header_block, self)
            stanzas = sections[1:]
            for block in stanzas:
                block_type, block = block.split(']\n',1)
                type_ = stanza_types[block_type]
                #odt = od_type[block_type]
                t = type_(block, self)  # FIXME :/
                self.add_tvpair_store(t)

            missing = {k:v for k, v in self.Terms.items() if isinstance(v, list)}
            if missing:
                msg = (('The following identifiers were referenced '
                        'but have no definition\n') + '\n'.join(sorted(missing)))
                log.debug(msg)
                log.error(f'{len(missing)} identifiers were referenced '
                          'but have no definition')
                if strict:
                    raise ValueError(msg)

            self.missing = missing

        elif header is not None:
            self.header = header
            self.Terms = terms  # TODO this should take iters not ods
            self.Typedefs = typedefs
            self.Instances = instances
        elif header is None:
            self.header = Header(obofile=self)

    def add_tvpair_store(self, tvpair_store):
        # TODO resolve terms
        #add store to od
        #add store to od.__dict__
        #add store to od.names
        tvpair_store.append_to_obofile(self)

    def add(self, *tvpair_stores):
        for store in tvpair_stores:
            self.add_tvpair_store(store)

    def write(self, path=None, format='obo', overwrite=False,
              stamp=True, version=OBO_VER_DEFAULT):  #FIXME this is bugged
        """ Write file, will not overwrite files with the same name
            outputs to obo by default but can also output to ttl if
            passed format='ttl' when called. """

        if path is None:
            path = self.path
            if path is None:
                raise ValueError('self.path is not set so path= cannot be None')

        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)

        if path.exists() and not overwrite:
            suffixes = path.suffixes
            n = 1
            if len(path.suffixes) > 1:
                try:
                    n = int(path.suffixes[-2][1:]) + 1
                except ValueError:
                    pass

            suffix = f'.{n}{path.suffix}'
            path = path.with_name(path.stem).with_suffix(suffix)
            final_path = self.write(path=path,
                                    format=format,
                                    overwrite=overwrite,
                                    stamp=stamp,
                                    version=version,)
            if path == final_path:
                log.warning(f'path exists, renaming to {path}')
        else:
            # FIXME streaming output that can use the stream setters from aug
            if format == 'obo':
                value = self.asObo(stamp=stamp, version=version)
            elif format == 'ttl':
                value = self.__ttl__()
            else:
                raise NotImplementedError(f'No exporter for file type {format}!')

            with open(path, 'wt', encoding='utf-8') as f:
                f.write(value)

        return path

    def __ttl__(self):
        g = rdflib.Graph()
        DNS = self.header.default_namespace.value.upper()
        iri_prefix = fobo[DNS + '_']
        argh = [(DNS, iri_prefix),
                ('owl', owl),
                ('definition', definition),
                ('NIFSTD', NIFSTD),
                ('NIFRID', NIFRID),
                ('obo', obo),
                ('', NOPE),]

        if hasattr(self.header, 'idspace'):
            for tvp in self.header.idspace:
                prefix, iri, *comment = tvp.value.split(' ')
                namespace = iri + '_'  # http://www.obofoundry.org/id-policy.html
                argh.append((prefix, namespace))
        else:
            argh.append(('TEMP', TEMP))
 
        for prefix, namespace in argh:
            g.bind(prefix, namespace)

        [g.add(t) for t in self.triples()]
         
        out = g.serialize(format='nifttl', encoding='utf-8')
        return out.decode()

    def triples(self):
        def ttlify(values):
            for s in values:
                if not isinstance(s, list):
                    yield from s.triples()
        for thing in ('Terms', 'Typedefs', 'Instances'):
            yield from ttlify(getattr(self, thing).values())

        ontid = fobo[self.header.ontology.value + '.ttl']
        yield ontid, rdf.type, owl.Ontology

    def asObo(self, stamp=True, version=OBO_VER_DEFAULT):
        def oboify(values):
            return [s.asObo(version=version) for s in values if not isinstance(s, list)]

        stores = [self.header.asObo(stamp=stamp, version=version)]
        stores += oboify(self.Terms.values())
        stores += oboify(self.Typedefs.values())
        stores += oboify(self.Instances.values())
        return '\n'.join(stores) + '\n'

    def __repr__(self):
        s = 'OboFile instance with %s Terms, %s Typedefs, and %s Instances' % (
            len(self.Terms), len(self.Typedefs), len(self.Instances))

        return s


class TVPair:  #TODO these need to be parented to something!
    """ Python representation of obo tag-value pairs, all tag-value pairs that
        require specially structured values are implemented below in the
        special children section.
        _type_ = '<tag-value pair>'
        _type_def = ('<tag>', '<value>', '{<trailing modifiers>}', '<comment>')

        NOTE: This class acts both as a parser and as an internal representation
        of the TVPair. In the future it will be refactored as has been done with
        the special_children classes.
    """
    _reserved_ids = ('OBO:TYPE','OBO:TERM','OBO:TERM_OR_TYPE','OBO:INSTANCE')
    _escapes = {
        '\\n':'\n',
        '\W':' ',
        '\\t':'\t',
        '\:':':',
        '\,':',',
        '\\"':'"',
        '\\\\':'\\',
        '\(':'(',
        '\)':')',
        '\[':'[',
        '\]':']',
        '\{':'{',
        '\}':'}',
              }
    def __init__(self, line=None, tag=None, value=None, modifiers=None, comment=None, parent=None, type_od=None, **kwargs):  # TODO kwargs for specific tags
        self.parent = parent
        self.type_od = type_od

        if line is not None:
            self.parse(line)
            self.validate(warn=True)
        else:
            self.make(tag, value, modifiers, comment, **kwargs)
            self.validate()

    @staticmethod
    def factory(tag, value=None, modifiers=None, comment=None, dict_=None, parent=None, type_od=None, **kwargs):
        tvp = TVPair(tag=tag, value=value, modifiers=modifiers, comment=comment, parent=None, type_od=type_od, **kwargs)
        if dict_:
            dict_[TVPair.esc_(tag)] = tvp
        else:
            return tvp

    def validate(self, warn=False):  # TODO
        if self.tag == 'id':
            if self.value in self._reserved_ids:
                raise AttributeError('You may not use reserved term %s as an id.' % self.value)
        # TODO validate kwargs
        #
        #warn if we are loading an ontology and there is an error but don't fail
        #id
        #name
        #def
        #synonym
        if not warn:
            #print('PLS IMPLMENT ME! ;_;')
            pass  # TODO

    def _value(self):
        return self.value

    @property
    def __value(self):
        return self._value()

    def parse(self, line):
        # we will handle extra parse values by sticking them on the tvpair instance
        tag, value = line.split(':',1)
        self.tag = tag
        value.strip()
        comm_split = value.split('\!')
        try:
            # comment
            tail, comment = comm_split[-1].split('!',1)
            if tail.count('"') % 2 == 1 and comment.count('"') % 2 == 1:  # so dumb
                comment = None
                value = comm_split[-1]
            else:
                comment = comment.strip()
                comm_split[-1] = tail
                value = '\!'.join(comm_split)

        except ValueError:
            comment = None

        value = value.strip()
        value, self.trailing_modifiers = self._parse_modifiers(value)  # FIXME make it a class??

        if tag in special_children:
            self._value = special_children[tag].parse(value, self)
            self.value = self.__value
            if type(self.value) == DynamicValue:
                self._comment = self._value.target.name.value  # LOL
                self.comment = self.__comment
            else:
                self.comment = comment
        else:
            self.value = value
            self.comment = comment

    def _parse_modifiers(self, value):
        # DEAL WITH TRAILING MODIFIERS
        stack = [None]
        inmod = False
        instring = False
        _nv = ''
        modifiers = tuple()
        for char in value:
            if char == '{' and not inmod:
                inmod = True
                stack.append('IN-MODIFIER')
                _current_modifier = ''
                _current_value = ''
            elif char == '}' and stack[-1] == 'IN-MODIFIER':
                modifiers += (_current_modifier, _current_value),
                _current_modifier = ''
                _current_value = ''
                stack.pop(-1)
                inmod = False
            elif inmod and char == '"' and not instring:
                instring = True
                stack.append('"')
            elif inmod and char == '"' and stack[-1] == '"':
                stack.pop(-1)
                instring = False
            else:
                if inmod and instring:
                    _current_value += char
                elif inmod:
                    if char == ' ':
                        pass
                    elif char == '=':
                        pass
                    elif char == ',':
                        modifiers += (_current_modifier, _current_value),
                        _current_modifier = ''
                        _current_value = ''
                    else:
                        _current_modifier += char
                else:
                    _nv += char

        return _nv.strip(), modifiers

    def _comment(self):
        return self.comment

    @property
    def __comment(self):
        return self._comment()

    def make(self, tag, value=None, modifiers=None, comment=None, **kwargs):
        self.tag = tag
        self.trailing_modifiers = modifiers
        self.comment = comment
        if tag in special_children:
            kwargs['tvpair'] = self
            self._value = special_children[tag](**kwargs)
            self.value = self.__value  # this seems dubiously effective?
            if type(self.value) == DynamicValue:
                self._comment = self._value.target.name.value  # LOL
                self.comment = self.__comment
        else:
            self.value = value

    def __eq__(self, other):
        if type(self) == type(other):
            if self.value == other.value:
                return True
            else:
                return False
        else:
            return False

    def __ne__(self, other):
        return not other == self

    def __lt__(self, other):
        if type(self) == type(other):
            if not isinstance(self._value, MethodType):
                return self._value < other._value
            else:
                return self.value < other.value
        else:
            return False  # pairs themselves don't know anyting about their ordering

    def __gt__(self, other):
        if type(self) == type(other):
            return not self < other
        else:
            return False  # pairs themselves don't know anyting about their ordering

    @staticmethod
    def _format_trailing_modifiers(trailing_modifiers, key=lambda kv: kv):
        if key is None:
            ordered = trailing_modifiers
        else:
            ordered = sorted(set(trailing_modifiers), key=key)

        tm = ', '.join([f'{k}="{v}"' for k, v in ordered])
        return f' {{{tm}}}'

    def asObo(self, version=OBO_VER_DEFAULT):
        string = '{}: {}'.format(self.tag, self._value())

        if self.trailing_modifiers:
            tm = self.trailing_modifiers
            if version == OBO_VER_ROBOT:
                key = None  # don't change the order at all
            else:
                key = lambda kv: kv

            string += self._format_trailing_modifiers(self.trailing_modifiers,
                                                      key=key)

        if self.comment:
            # TODO: autofill is_a comments
            string += " ! " + self._comment()

        return string

    def __str__(self):
        return self.asObo()

    def __ttl__(self):
        pass

    def triples(self, subject=None):
        if subject is None:
            subject = rdflib.BNode()

        if self.tag == 'id':
            yield id_fix(self.value), rdf.type, owl.Class

        elif self.tag in obo_tag_to_ttl:
            predicate = obo_tag_to_ttl[self.tag]
            if self.tag == 'def':
                #value = self._value.text.replace('"','\\"')
                value = self._value.text
                object = rdflib.Literal(value)

            elif self.tag == 'synonym':
                value = self._value.text.lower()
                object = rdflib.Literal(value)

            elif self.tag == 'is_a':
                if self._value.target == self._value.DANGLING:  # we dangling
                    value = self._value.target_id
                else:
                    value = id_fix(self._value.target.id_.value)

                object = rdflib.URIRef(value)

            elif self.tag == 'name':
                value = self.value.lower()  # capitalize only proper nouns as needed
                object = rdflib.Literal(value)

            elif self.tag == 'xref':
                value = self.value
                if '\:' in value:
                    value = value.replace('\:', ':')
                try:
                    object = OntId(value).URIRef
                except (OntId.UnknownPrefixError, OntId.BadCurieError) as e:
                    object = rdflib.Literal(value)  # FIXME

            else:
                value = self.value
                if '\:' in value:
                    value = value.replace('\:', ':')
                object = rdflib.URIRef(value)

            yield subject, predicate, object

    def __repr__(self):
        return self.__class__.__name__ + ' <' + str(self) + '>'

    @staticmethod
    def esc(string):
        for f, r in TVPair._escapes:
            string = string.replace(f, r)
        return string

    @staticmethod
    def esc_(string):
        """ fix strings for use as names in classes """
        if string == 'id':  # dont clobber id
            return 'id_'
        elif string == 'def':  # avoid syntax errors
            return 'def_'
        return string.replace('-','_').replace(':','')


class TVPairStore:
    """
        Ancestor class for stanzas and headers.
    """

    @classmethod
    def _robot_tags(cls):
        raise NotImplementedError('subclassit')

    def __new__(cls, *args, **kwargs):
        cls._tags = od()
        for tag, limit in cls._all_tags:
            cls._tags[tag] = limit
        cls.__new__ = cls.___new__  # enforce runonce
        return super().__new__(cls)

    @classmethod
    def ___new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self, block=None, obofile=None, tvpairs=tuple(), **pairs):
        # keep _tags out of self.__dict__ and add new tags for all instances
        if obofile is not None:
            type_od = getattr(obofile, self.__class__.__name__+'s')
        else:
            type_od = None
            #raise TypeError('TVPairStores need an OboFile, even if it is a fake one.')  # FIXME just don't check stuff instead?

        for tag, limit in self._tags.items():
            if limit == N:
                self.__dict__[TVPair.esc_(tag)] = []  # may need a list

        if block is not None:
            lines = block.split('\n')
            for line in lines:
                if line:
                    if line[0] != '!':  # we do not parse comments
                        tvpair = TVPair(line, parent=self, type_od=type_od)
                        self.add_tvpair(tvpair)
            warn = True
        else:
            for tvpair in tvpairs:  # FIXME, sorta need a way to get the type_od to them more naturally?
                self.add_tvpair(tvpair)
            for tag, value in pairs.items():
                self.add_tvpair(TVPair(tag=tag, value=value))
            warn = False

        #clean up empty tags
        to_pop = []
        for tag, value in self.__dict__.items():
            if not value:
                to_pop.append(tag)

        for tag in to_pop:
            self.__dict__.pop(tag)

        self.validate(warn)

    def append_to_obofile(self, obofile):
        raise NotImplementedError('Please implement me in your subclass!')

    def add_tvpair(self, tvpair):
        tag = tvpair.tag
        dict_tag = TVPair.esc_(tag)

        if tag not in self.__dict__:
            if tag not in self._tags:
                log.warning(f'TAG NOT IN {tag} for {self.__class__}')
                self._tags[tag] = N
                log.warning(self._tags[tag])
                self.__dict__[dict_tag] = []
            elif self._tags[tag] == N:
                if dict_tag not in self.__dict__:
                    self.__dict__[dict_tag] = []

        if self._tags[tag] == N:
            try:
                self.__dict__[dict_tag].append(tvpair)
            except KeyError as e:
                breakpoint()
                raise e
        else:
            self.__dict__[dict_tag] = tvpair

    def add(self, *tvpairs, **pairs):
        """ You can add simple pairs as kwargs or complex pairs as args. """
        for tvpair in tvpairs:
            self.add_tvpair(tvpair)

        for tag, value in pairs.items():
            self.add_tvpair(TVPair(tag=tag, value=value))

    @property
    def tvpairs(self):
        return self._tvpairs()

    def _tvpairs(self, source_dict=None, version=OBO_VER_DEFAULT):
        if version == OBO_VER_DEFAULT:
            index = tuple(self._tags)
        elif version == OBO_VER_ROBOT:
            index = tuple(self._robot_tags())
        else:
            raise NotImplementedError('unknown version: {version}')

        if not source_dict:
            source_dict = self.__dict__
        #_ = [print(a, b) for a, b in zip(sorted(index), sorted(source_dict))]

        def key(value):
            if isinstance(value, list):
                value = value[0]

            return index.index(value.tag)

        out = []
        for tvp in sorted(source_dict.values(), key=key):
            if type(tvp) == list:
                out.extend(sorted(tvp))
            elif type(tvp) == property:
                breakpoint()
            else:
                out.append(tvp)

        return out

    def __ttl__(self):
        g = rdflib.Graph()
        [g.add(t) for t in self.triples()]
        # TODO go peek at how we removed prefixes for neurons
        return g.serialize(format='nifttl', encoding='utf-8')

    def triples(self):
        id_pair, *rest = self.tvpairs
        (subject, predicate, object), = id_pair.triples()
        yield subject, predicate, object
        for pair in rest:
            yield from pair.triples(subject)

    def __iter__(self):
        yield from self.tvpairs

    def asObo(self, version=OBO_VER_DEFAULT):
        return '\n'.join(tvpair.asObo(version=version) for tvpair
                         in self._tvpairs(version=version)) + '\n'

    def __str__(self):
        return self.asObo()

    def __repr__(self):
        return ' '.join(str(tvpair) for tvpair in self.tvpairs) + ' '

    def validate(self, warn=False):
        tags = []
        for tag, tvp in self.__dict__.items():
            #print(tvp)
            if tvp:
                if type(tvp) == list:
                    tags.append(tvp[0].tag)
                else:
                    try:
                        tags.append(tvp.tag)
                    except AttributeError as e:
                        breakpoint()
                        raise e
            else:
                raise AttributeError('Tag %s has no values!' % tag)

        for tag in self._r_tags:
            if tag not in tags:
                if warn:
                    log.warning('probably a multipart definition')  # TODO
                    #raise ImportWarning('%s %s is missing a required tag %s' %
                                        #(self.__class__.__name__, str(self), tag))
                else:
                    raise AttributeError('%s must have a tag of type %s' %
                                         (self.__class__.__name__, tag))


class Header(TVPairStore):
    """ Header class. """

    _r_tags = ('format-version', )
    _r_defaults = (OBO_VER_DEFAULT,)
    _all_tags = (
        ('format-version', 1),
        ('data-version', 1),
        ('date', 1),
        ('saved-by', 1),
        ('auto-generated-by', 1),
        ('import', N),
        ('subsetdef', N),
        ('synonymtypedef', N),
        ('default-namespace', 1),
        ('namespace-id-rule', N),
        ('idspace', N),  # PREFIX http://uri
        ('treat-xrefs-as-equivalent', N),
        ('treat-xrefs-as-genus-differentia', N),
        ('treat-xrefs-as-relationship', N),
        ('treat-xrefs-as-is_a', N),
        ('treat-xrefs-as-has-subclass', N),
        ('treat-xrefs-as-reverse-genus-differentia', N),
        ('id-mapping', N),
        ('default-relationship-id-prefix', 1),
        ('relax-unique-identifier-assumption-for-namespace', N),
        ('relax-unique-label-assumption-for-namespace', N),
        ('property_value', N),
        ('remark', N),
        ('ontology', 1),
        ('owl-axioms', N),
    )

    _datetime_fmt = '%d:%m:%Y %H:%M'  # WE USE ZULU

    @classmethod
    def _robot_tags(cls):
        order = (  # FIXME missing the cases above
            'format-version',

            'data-version',
            'date',
            'saved-by',
            'auto-generated-by',

            'subsetdef',
            'synonymtypedef',
            'default-namespace',
            'treat-xrefs-as-equivalent',
            'treat-xrefs-as-is_a',
            'import',
            'ontology',
            'property_value',
            'owl-axioms',
            'treat-xrefs-as-has-subclass',
            'treat-xrefs-as-reverse-genus-differentia',
                 )

        return order

    def __init__(self, block=None, obofile=None, tvpairs=tuple(), **pairs):
        for tag, value in zip(self._r_tags, self._r_defaults):
            if tag not in pairs or TVPair(tag=tag, value=value) not in tvpairs:
                pairs[tag] = value

        super().__init__(block=block, obofile=obofile, tvpairs=tvpairs, **pairs)

    def append_to_obofile(self, obofile):
        obofile.header = self

    def asObo(self, stamp=True, version=OBO_VER_DEFAULT):
        """ When we write to file overwrite the relevant variables without
            also overwriting the original data. """

        if stamp:
            updated = {k:v for k, v in self.__dict__.items()}
            log.debug(str(tuple(updated.keys())))
            TVPair.factory('date', datetime.strftime(datetime.utcnow(),
                                                    self._datetime_fmt),
                        dict_=updated)
            TVPair.factory('auto-generated-by', __title__, dict_=updated)
            TVPair.factory('saved-by', getuser(), dict_=updated)
            tvpairs = self._tvpairs(updated)
        else:
            updated = None  # strict roundtrip

        return '\n'.join(str(tvpair) for
                         tvpair in self._tvpairs(updated,
                                                 version=version)) + '\n'

    def __str__(self):
        return self.asObo()


class Stanza(TVPairStore):
    """ Stanza class.
        _types = ('Term', 'Typedef', 'Instance')
    """
    _type_ = '<stanza>'
    _type_def = ('[<Stanza name>]','<tag-value pair>')
    _r_tags = ['id', 'name',]
    _all_tags = (
        ('id', 1),
        ('is_anonymous', 1),
        ('name',1),
        ('namespace', 1),
        ('alt_id', N),
        ('def', 1),
        ('comment', 1),
        ('subset', N),
        ('synonym', N),
        ('acronym', N),  # i think it is just better to add this
        ('xref', N),
        ('instance_of', 1), ##
        ('property_value', N), ##
        ('domain', 1), #
        ('range', 1), #
        ('builtin', 1),
        ('holds_over_chain', N),
        ('is_anti_symmetric', 1), #
        ('is_cyclic', 1), #
        ('is_reflexive', 1), #
        ('is_symmetric', 1), #
        ('is_transitive', 1), #
        ('is_functional', 1), #
        ('is_inverse_functional', 1), #
        ('is_a', N),
        ('intersection_of', N),  # no relationships, typedefs
        ('union_of', N),  # min 2, no relationships, typedefs
        ('equivalent_to', N),  # no relationships, typedefs
        ('disjoint_from', N),  # no relationships, typedefs
        ('inverse_of', 1), #
        ('transitive_over', N), #
        ('equivalent_to_chain', N), #
        ('disjoint_over', N), #
        ('relationship', N),
        ('is_obsolete', 1),
        ('consider', N),
        ('created_by', 1),
        ('creation_date', 1),
        ('replaced_by', N),
        ('consider', N),
        ('expand_assertion_to', 1),  # FIXME cardinality?
        ('expand_expression_to', 1),  #
        ('is_metadata_tag', 1),  #
        ('is_class_level', 1),  #

    )
    _typedef_only_tags = [
        'domian',
        'range',
        'inverse_of',
        'transitive_over',
        'is_cyclic',
        'is_reflexive',
        'is_symmetric',
        'is_anti_symmetric',
        'is_transitive',
        'expand_assertion_to',
        'expand_expression_to',
        'is_metadata_tag',
        'is_class_level',
    ]

    @classmethod
    def _robot_tags(cls):
        rt = [t for t, _ in cls._all_tags]
        tb = [
            ['property_value', 'is_obsolete'],
            ['replaced_by', 'consider'],
        ]
        for tag, before in tb:
            rt.remove(tag)
            rt.insert(rt.index(before), tag)

        return rt

    def __new__(cls, *args, **kwargs):
        cls._all_tags = [tag for tag in cls._all_tags
                         if tag[0] not in cls._bad_tags]
        instance = super().__new__(cls, *args, **kwargs)
        cls.__new__ = super().__new__  # enforce runonce
        return instance  # we return here so we chain the runonce

    def __init__(self, block=None, obofile=None, tvpairs=tuple(), **pairs):
        if block is not None and obofile is not None:
            super().__init__(block, obofile)
        else:
            super().__init__(tvpairs=tvpairs, **pairs)

        if obofile is not None:
            self.append_to_obofile(obofile)
        else:
            #print('Please be sure to add this to the typd_od yourself!')
            pass  # TODO

    def append_to_obofile(self, obofile):
        type_od = getattr(obofile, self.__class__.__name__+'s')
        callbacks = type_od.get(self.id_.value, None)
        if type(callbacks) == list:
            for callback in callbacks:
                callback(self)  # fill in is_a
            type_od.pop(self.id_.value)  # reset the order

        elif type(callbacks) == type(self):
            #log.debug(self.id_)
            if set(self.__dict__) == set(callbacks.__dict__):
                pass
            else:
                callbacks.__dict__.update(self.__dict__)  # last one wins
                #raise ValueError('IT WOULD SEEM WE ALREADY EXIST! PLS HALP')  # TODO

        type_od[self.id_.value] = self
        type_od.__dict__[TVPair.esc_(self.id_.value)] = self
        if hasattr(self, 'name'):
            if self.name.value not in type_od.names:  # add to names
                type_od.names[self.name.value] = self
            elif type(type_od.names[self.name.value]) == list:
                type_od.names[self.name.value].append(self)
            else:
                existing = type_od.names.pop(self.name.value)
                type_od.names[self.name.value] = [existing, self]

    def asObo(self, version=OBO_VER_DEFAULT):
        return ('['+ self.__class__.__name__ +']\n' +
                super().asObo(version=version))

    def __str__(self):
        return self.asObo()


class Term(Stanza):
    _bad_tags = ['instance_of']
    def __new__(cls, *args, **kwargs):
        cls._bad_tags += cls._typedef_only_tags
        instance = super().__new__(cls, *args, **kwargs)
        cls.__new__ = super().__new__
        return instance

    def dedupe_synonyms(self):
        if getattr(self, 'synonym', None):
            last_wins = {}
            for s in self.synonym:
                if type(s._value) == str:
                    #log.debug(s._value)
                    key = s.value
                else:
                    key = s._value.text
                last_wins[key] = s
            self.synonym = sorted(list(last_wins.values()),key=lambda a:a.value)


class Typedef(Stanza):
    _bad_tags = ('union_of', 'intersection_of', 'instance_of')
    # now allowed? 'disjoint_from'

    @classmethod
    def _robot_tags(cls):
        rt = [t for t, _ in cls._all_tags]
        tb = [
            # yes this is a horrible implementation
            ['property_value', 'domain'],
            ['property_value', 'is_transitive'],
            ['property_value', 'is_a'],
        ]
        done = []
        for tag, before in tb:
            if tag in rt and tag not in done and before in rt:
                rt.remove(tag)
                rt.insert(rt.index(before), tag)
                done.append(tag)

        return rt



class Instance(Stanza):
    _r_tags = ['instance_of',]
    def __new__(cls, *args, **kwargs):
        cls._bad_tags += cls._typedef_only_tags
        cls._r_tags = super()._r_tags + cls._r_tags
        instance = super().__new__(cls, *args, **kwargs)
        cls.__new__ = super().__new__
        return instance


stanza_types = {type_.__name__:type_ for type_ in (Term, Typedef, Instance)}

###
#   Special children
###

class Value:
    tag = None
    seps = ' ',
    brackets = {'[':']', '{':'}', '(':')', '<':'>', '"':'"', ' ':' '}
    brackets.update({v:k for k, v in brackets.items()})

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self, value, *args):
        self.value = value  # FIXME causes heterogenous types

    def value(self):
        raise NotImplemented('Impl in subclass pls.')

    def __lt__(self, other):
        return self.value() < other.value()

    def __gt__(self, other):
        return not self < other

    def __str__(self):
        return str(self.value())

    def __repr__(self):
        return self.__class__.__name__ + ' <' + str(self) + '>'

    def __call__(self):
        return self.value()

    @classmethod
    def parse(cls, value, *args):
        if type(value) == tuple:  # make nice for super()
            new_args = value
        elif type(value) == str:
            new_args = value,
        #kwargs = {name:value for name, value in zip(cls.fields, split)}
        #return cls.__new__(cls, **kwargs)
        #instance = cls.__new__(cls, *new_args)
        instance = cls(*new_args)
        return instance


class DynamicValue(Value):
    """ callbacks need to be isolated here for relationship, is_a and internal xrefs"""

    class DANGLING:
        """ Awating a value at the end of parsing. """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def get_target(self, tvpair):
        def callback(target, s=self):
            log.debug(f'{target.id_.value} calling back {self.tag}')
            s.target = target

        self.target = self.DANGLING
        if tvpair.type_od is None:  # TODO need a way to fill these in on add
            self.target += ' ' + self.target_id
            return

        target = tvpair.type_od.get(self.target_id, None)
        if type(target) == list:
            tvpair.type_od[self.target_id].append(callback)
        elif target is None:
            tvpair.type_od[self.target_id] = [callback]
        else:  # its a Term or something
            #print('map', test.id_, 'to', tag, value)
            self.target = target

    def value(self):
        if self.target == self.DANGLING:
            return self.target_id

        elif type(self.target) == str:
            log.warning('Pretty sure this shouldn\'t happen now?')
            return self.target

        else:
            return str(self.target.id_.value)


class Is_a(DynamicValue):
    tag = 'is_a'
    seps = ' ',
    def __init__(self, target_id, tvpair):
        self.target_id = target_id
        self.get_target(tvpair)
        #print('yes i have a target id you lying sack of shit',self.target_id)

    @classmethod
    def parse(cls, value, tvpair):
        target_id = value
        split = (target_id, tvpair)
        return super().parse(split)


class Relationship(DynamicValue):
    tag = 'relationship'
    seps = ' ', ' '
    def __init__(self, typedef, target_id, tvpair):
        self.typedef = typedef  #FIXME this is also an issue
        self.target_id = target_id
        self.get_target(tvpair)

    def value(self):
        return self.typedef + ' ' + super().value()

    @classmethod
    def parse(cls, value, tvpair):
        typedef, target_id = value.split(' ')
        split = (typedef, target_id, tvpair)
        return super().parse(split)


class Def_(Value):
    tag = 'def'
    seps = '"', '['
    def __init__(self, text, xrefs=[], **kwargs):
        self.text = text
        self.xrefs = xrefs

    def value(self):
        out = ''
        out += self.seps[0]
        out += self.text
        out += self.seps[0]
        out += ' '
        out += self.seps[1]
        out += ', '.join([str(xref) for xref in self.xrefs])
        out += self.brackets[self.seps[1]]
        return out

    @classmethod
    def parse(cls, value, tvpair):
        try:
            text, xrefs = value[1:-1].split('" [')
        except ValueError:
            raise ValueError('No xrefs found! Please add square brackets [] at the end of each def:')  # FIXME?!?
        xrefs = [Xref.parse(xref, tvpair) for xref in xrefs.split(',')]
        split = (text, xrefs)
        return super().parse(split)


class Id_mapping(Value):
    tag = 'id-mapping'
    seps = ' ', ' '
    def __init__(self, id_, target, **kwargs):
        self.id_ = id_
        self.target = target

    def value(self):
        out = ''
        out += self.id_
        out += self.seps[0]
        out += self.target
        return out

    @classmethod
    def parse(cls, value, *args):
        id_, target = value.split(' ')
        split = (id_, target)
        return super().parse(split)


class Idspace(Value):
    tag = 'idspace'
    seps = ' ', ' ', '"'
    def __init__(self, name, uri, desc=None, **kwargs):
        self.name = name
        self.uri = uri
        self.desc = desc

    def value(self):
        out = ''
        out += self.name
        out += self.seps[0]
        out += self.uri
        if self.desc:
            out += self.seps[1]
            out += self.seps[2]
            out += self.desc
            out += self.seps[2]
        return out

    @classmethod
    def parse(cls, value, *args):
        name, uri_description = value.split(' ', 1)
        uri, description  = uri_description.split(' "')
        description = description[:-1]
        split = (name, uri, description)
        return super().parse(split)


class Property_value(Value):
    tag = 'property_value'
    seps = ' ', ' ', ' '
    def __init__(self, type_id, val, datatype=None, **kwargs):
        self.type_id = type_id
        self._val = val
        self.datatype = datatype

    def __lt__(self, other):
        if type(self) == type(other):
            self.datatype != other.datatype
        else:
            return False

    def __gt__(self, other):
        if type(self) == type(other):
            return not self < other
        else:
            return False

    @property
    def val(self):
        if self._val.startswith('"'):
            return ast.literal_eval(self._val)

        return self._val

    def value(self):
        dt = ' ' + self.datatype if self.datatype else ''
        return f'{self.type_id} {self._val}{dt}'

    @classmethod
    def parse(cls, value, *args):
        type_id, val_datatype = value.split(' ', 1)
        if val_datatype.startswith('"'):
            _val, _datatype = val_datatype.rsplit('"', 1)
            val = _val[1:]
            val = f'"{val}"'  # string escaping madness
            datatype = _datatype.strip()
            if not datatype:
                datatype = None

        else:
            try:
                val, datatype = val_datatype.split(' ', 1)
            except ValueError:
                val = val_datatype
                datatype = None

        split = (type_id, val, datatype)
        return super().parse(split)


class Subsetdef(Value):
    tag = 'subsetdef'
    seps = ' ', '"'
    filed = 'name', 'desc'
    def __init__(self, name, desc, **kwargs):
        self.name = name
        self.desc = desc

    def value(self):
        return self.name + self.seps[0] + self.seps[1] + self.desc + self.seps[1]

    @classmethod
    def parse(cls, value, *args):
        name, description = value.split(' "', 1)
        description = description[:-1]
        split = (name, description)
        return super().parse(split)


class Synonym(Value):
    tag = 'synonym'
    seps = '"', ' ', ' ', '['
    def __init__(self, text, scope=None, typedef=None, xrefs=[], **kwargs):
        self.text = text
        self.scope = scope  # FIXME scope defaults
        self.typedef = typedef
        self.xrefs = xrefs

    def value(self):
        out = ''
        out += self.seps[0]
        out += self.text
        out += self.seps[0]
        if self.scope:
            out += self.seps[1]
            out += self.scope
        if self.typedef:
            out += self.seps[2]
            out += self.typedef
        out += ' '
        out += self.seps[3]
        out += ', '.join([str(xref) for xref in self.xrefs])
        out += self.brackets[self.seps[3]]
        return out

    def __lt__(self, other):
        return self.text.lower() < other.text.lower()

    @classmethod
    def parse(cls, value, tvpair):
        try:
            text, scope_typedef_xrefs = value[1:-1].split('" ', 1)
        except ValueError:
            raise ValueError('Malformed synonym: line you are probably missing xrefs.')  # FIXME?!?
        try:
            if scope_typedef_xrefs.startswith('['):  # single space no scopedef typeref
                scope_typedef, xrefs = scope_typedef_xrefs.split('[', 1)
            else:
                scope_typedef, xrefs = scope_typedef_xrefs.split(' [', 1)
        except ValueError:
            raise ValueError('No xrefs found! Please add square brackets [] at the end of each synonym:')  # FIXME?!?
        xrefs = [Xref.parse(xref, tvpair) for xref in xrefs.split(',')]
        scope_typedef.strip().rstrip()
        if scope_typedef:
            try:
                scope, typedef = scope_typedef.split(' ')
            except ValueError:  # TODO look in tvpair.parent.header for synonymtypedef
                scope = scope_typedef
                typedef = None
        else:
            scope = None
            typedef = None
        split = (text, scope, typedef, xrefs)
        return super().parse(split)


class Synonymtypedef(Value):
    tag = 'synonymtypedef'
    seps = ' ', '"', ' '
    def __init__(self, name, desc, scope=None, **kwargs):  #FIXME '' instead of None?
        self.name = name
        self.desc = desc
        self.scope = scope

    def value(self):
        out = ''
        out += self.name
        out += self.seps[0]
        out += self.seps[1]
        out += self.desc
        out += self.seps[1]
        if self.scope:
            out += self.seps[2]
            out += self.scope
        return  out

    @classmethod
    def parse(cls, value, *args):
        name, description_scope = value.split(' "', 1)
        description, scope = description_scope.split('"', 1)  # FIXME escapes :/
        scope = scope.strip()
        split = (name, description, scope)
        return super().parse(split)


class Xref(Value):  # TODO link internal ids, finalize will require cleanup, lots of work required here
    tag = 'xref'
    seps = ' ', '"'
    def __init__(self, name, desc=None, **kwargs):
        self.name = name
        self.desc = desc

    def value(self):
        out = ''
        out += self.name
        if self.desc:
            out += self.seps[0]
            out += self.seps[1]
            out += self.desc
            out += self.seps[1]
        return out

    def __lt__(self, other):
        return self.value().lower() < other.value().lower()

    @classmethod
    def parse(cls, value, tvpair):
        value.strip().rstrip()  # in case we get garbage in from a bad split
        try:
            name, description = value.split(' "', 1)
            description = description[:-1]
        except ValueError as e:
            name = value.strip()  # TODO dangling stuff?
            description = None
        split = (name, description)
        return super().parse(split)


class Consider(Value):
    tag = 'consider'
    seps = ' ',
    def __init__(self, other, tvpair):
        self.other = other

    def value(self):
        return self.other

    @classmethod
    def parse(cls, value, tvpair):
        target_id = value
        split = (target_id, tvpair)
        return super().parse(split)

    def __lt__(self, other):
        return self.value().lower() < other.value().lower()


special_children = {sc.tag:sc for sc in (Subsetdef,
                                         Synonymtypedef,
                                         Idspace,
                                         Id_mapping,
                                         Def_,
                                         Synonym,
                                         Xref,
                                         Relationship,
                                         Is_a,
                                         Property_value,
                                         Consider,
                                         )}


def deNone(*args):
    for arg in args:
        if arg == None:
            yield ''
        else:
            yield arg


__all__ = [c.__name__ for c in (OboFile, TVPair, Header, Term, Typedef, Instance)]


def main():
    args = docopt(__doc__, version='obo-io 0')
    path_in = pathlib.Path(args['<obofile>'])

    if args['--debug']:
        log.setLevel('DEBUG')
    else:
        log.setLevel('INFO')

    if path_in.suffix != '.obo':  # FIXME pretty sure a successful parse should be the measure here?
        # TODO TEST ME!
        raise TypeError(f'{path_in} has wrong extension {path_id.suffix} != .obo !')

    if path_in.exists():
        of = OboFile(path=path_in, strict=args['--strict'])
        if args['--out-format'] == 'ttl':
            ttl = of.__ttl__()
    else:
        raise FileNotFoundError(path_in)

    if args['<output-name>']:
        path_out = pathlib.Path(args['<output-name>'])
    else:
        path_out = path_in.with_suffix('.' + args['--out-format'])

    if args['--write'] or args['--overwrite']:
        of.write(path=path_out,
                 format=args['--out-format'],
                 overwrite=args['--overwrite'],
                 stamp=not args['--no-stamp'],
                 version=OBO_VER_ROBOT if args['--robot'] else OBO_VER_DEFAULT,)

    if args['--debug']:
        breakpoint()


if __name__ == '__main__':
    main()
