#!/usr/bin/env python3
"""python .obo file parser and writer

    Usage:
        obo-io <obofile>
        obo-io --ttl <obofile> [<ttlfile>]
        obo-io --help
    Options:
        -h --help       show this
        -t --ttl        convert obo file to ttl and exit

    based on the obo 1.2 spec defined at
    https://oboformat.googlecode.com/svn/trunk/doc/GO.format.obo-1_2.html

    acts as a command line script or as a python module
    also converts to ttl format but the conversion convetions are ill defined

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

__title__ = 'obo_io'
__author__ = 'Tom Gillespie'

import os
import inspect
from datetime import datetime
from getpass import getuser
from collections import OrderedDict
import rdflib
from docopt import docopt
import pyontutils.utils
from pyontutils.qnamefix import cull_prefixes
from pyontutils.namespaces import makeNamespaces, NIFRID, definition, PREFIXES as uPREFIXES
from pyontutils.closed_namespaces import rdf, owl
from IPython import embed

fobo, obo, NIFSTD, NOPE = makeNamespaces('fobo', 'obo', 'NIFSTD', '')

N = -1  # use to define 'many ' for tag counts
TW = 4  # tab width

class od(OrderedDict):
    pass

od.__repr__ = dict.__repr__

# this is our current (horrible) conversion from obo to ttl
obo_tag_to_ttl = {
    'id':'%s rdf:type owl:Class ;\n',
    'name':' ' * TW + 'rdfs:label "%s"@en ;\n',
    'def':' ' * TW + 'definition: "%s"@en ;\n',
    'acronym':' ' * TW + 'NIFRID:acronym "%s"@en ;\n',
    'synonym':' ' * TW + 'NIFRID:synonym "%s"@en ;\n',
    'is_a':' ' * TW + 'rdfs:subClassOf %s ;\n',
    #'xref':

}
def id_fix(value):
    """ fix @prefix values for ttl """
    if value.startswith('KSC_M'):
        pass
    else:
        value = value.replace(':','_')
        if value.startswith('ERO') or value.startswith('OBI') or value.startswith('GO') or value.startswith('UBERON') or value.startswith('IAO'):
            value = 'obo:' + value
        elif value.startswith('birnlex') or value.startswith('nlx'):
            value = 'NIFSTD:' + value
        elif value.startswith('MESH'):
            value = ':'.join(value.split('_'))
        else:
            value = ':' + value
    return value


class OboFile:
    """ Python representation of the obo file structure split into tag-value
        pair stanzas the header is currently its own special stanza.
        type_def = ('<header>','<stanza>')

        Usage: To load an obo file from somwhere on disk initialize an OboFile
        instance with the full path to the obo file you want to load.
        To write an obofile call obofileinstance.write(). If the filename for
        the obofile exists it will not overwrite what you have but will append
        a number to the end.

        To output to ttl format call str_to_write = obofileinstance.__ttl__()
        and then write str_to_write to file.  TODO implement .writettl()
    """
    def __init__(self, filename=None, header=None, terms=None, typedefs=None, instances=None):
        self.filename = filename
        self.Terms = od()
        self.Terms.names = {}
        self.Typedefs = od()
        self.Typedefs.names = {}
        self.Instances = od()
        self.Instances.names = {}
        self.Headers = od()  #LOL STUPID FIXME
        self.Headers.names = {}  # FIXME do not want? what about imports?
        if filename is not None:  # FIXME could spec filename here?
            #od_types = {type_.__name__:type_od for type_,type_od in zip((Term, Typedef, Instance),(self.Terms,self.Typedefs,self.Instances))}
            #LOL GETATTR
            with open(filename, 'rt') as f:
                data = f.read()
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
                raise ValueError('ERROR: The following identifiers were referenced but have no definition ' + ' '.join(missing))

        elif header is not None:
            self.header = header
            self.Terms = terms  # TODO this should take iters not ods
            self.Typedefs = typedefs
            self.Instances = instances
        elif header is None:
            self.header = None

    def add_tvpair_store(self, tvpair_store):
        # TODO resolve terms
        #add store to od
        #add store to od.__dict__
        #add store to od.names
        tvpair_store.append_to_obofile(self)

    def write(self, filename, type_='obo'):  #FIXME this is bugged
        """ Write file, will not overwrite files with the same name
            outputs to obo by default but can also output to ttl if
            passed type_='ttl' when called.
        """
        if os.path.exists(filename):
            name, ext = filename.rsplit('.',1)
            try:
                prefix, num = name.rsplit('_',1)
                n = int(num)
                n += 1
                filename = prefix + '_' + str(n) + '.' + ext
            except ValueError:
                filename = name + '_1.' + ext
            print('file exists, renaming to %s' % filename)
            self.write(filename, type_)

        else:
            with open(filename, 'wt', encoding='utf-8') as f:
                if type_ == 'obo':
                    f.write(str(self))  # FIXME this is incredibly slow for big files :/
                elif type_ == 'ttl':
                    f.write(self.__ttl__())
                else:
                    raise TypeError('No exporter for file type %s!' % type_)


    def __ttl__(self):
        #stores = [self.header.__ttl__()]
        stores = []
        stores += [s.__ttl__() for s in self.Terms.values()]# if not print(s)]
        stores += [s.__ttl__() for s in self.Typedefs.values()]
        stores += [s.__ttl__() for s in self.Instances.values()]
        DNS = self.header.default_namespace.value.upper()
        ontid = fobo[self.header.ontology.value + '.ttl']
        iri_prefix = fobo[DNS + '_']
        g = rdflib.Graph()
        prefixes = [f'@prefix {DNS}: <{iri_prefix}> .']
        argh = (('owl', owl),
                ('definition', definition),
                ('NIFSTD', NIFSTD),
                ('NIFRID', NIFRID),
                ('obo', obo),
                ('', NOPE),)
        for prefix, iri in (*g.namespaces(), *argh):
            prefixes.append(f'@prefix {prefix}: <{iri}> .')
        for tvp in self.header.idspace:
            prefix, iri, *comment = tvp.value.split(' ')
            prefixes.append(f'@prefix {prefix}: <{iri}_> .')

        g.parse(data='\n'.join(prefixes + stores), format='turtle')
        g.add((ontid, rdf.type, owl.Ontology))

        og = cull_prefixes(g, prefixes={DNS:iri_prefix, **uPREFIXES})
        out = og.g.serialize(format='nifttl')
        return out.decode()


    def __str__(self):
        stores = [str(self.header)]
        stores += [str(s) for s in self.Terms.values()]
        stores += [str(s) for s in self.Typedefs.values()]
        stores += [str(s) for s in self.Instances.values()]
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
            #print(self)
            self.validate(warn=True)
        else:
            self.make(tag, value, modifiers, comment, **kwargs)
            self.validate()

    @staticmethod
    def factory(tag, value=None, modifiers=None, comment=None, dict_=None, parent=None, type_od=None, **kwargs):
        tvp = TVPair(tag=tag, value=value, modifiers=comment, comment=comment, parent=None, type_od=type_od, **kwargs)
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
        try:
            tag, value = line.split(':',1)
            self.tag = tag
            value.strip()
            comm_split = value.split('\!')
            try:
                # comment
                tail, comment = comm_split[-1].split('!',1)
                comment = comment.strip()
                comm_split[-1] = tail
                value = '\!'.join(comm_split)

            except ValueError:
                comment = None

            value = value.strip()

            # DEAL WITH TRAILING MODIFIERS
            trailing_modifiers = None

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
        except BaseException as e:
            embed()
            raise

        self.tag = tag
        self.trailing_modifiers = trailing_modifiers

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
            self.value = self.__value
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

    def __str__(self):
        string = '{}: {}'.format(self.tag, self._value())

        if self.trailing_modifiers:
            string += " " + str(self.trailing_modifiers)

        if self.comment:
            # TODO: autofill is_a comments
            string += " ! " + self._comment()

        return string

    def __ttl__(self):

        if self.tag in obo_tag_to_ttl:
            if self.tag == 'id':
                value = id_fix(self.value)
            elif self.tag == 'def':
                value = self._value.text.replace('"','\\"')
            elif self.tag == 'synonym':
                value = self._value.text.lower()
            elif self.tag == 'is_a':
                if type(self._value.target) == str:  # we dangling
                    value = self._value.target_id
                else:
                    value = id_fix(self._value.target.id_.value)
            elif self.tag == 'name':
                value = self.value.lower()  # capitalize only proper nouns as needed
            else:
                value = self.value

            return obo_tag_to_ttl[self.tag] % value
        else:
            return ''

    def __repr__(self):
        return str(self)

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
    def __new__(cls, *args, **kwargs):
        cls._tags = od()
        for tag, limit in cls._all_tags:
            cls._tags[tag] = limit
        cls.__new__ = cls.___new__  # enforce runonce
        return super().__new__(cls)

    @classmethod
    def ___new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self, block=None, obofile=None, tvpairs=None):
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
        raise NotImplemented('Please implement me in your subclass!')


    def add_tvpair(self, tvpair):
        tag = tvpair.tag
        dict_tag = TVPair.esc_(tag)

        if tag not in self.__dict__:
            if tag not in self._tags:
                print('TAG NOT IN', tag)
                self._tags[tag] = N
                print(self._tags[tag])
                self.__dict__[dict_tag] = []
            elif self._tags[tag] == N:
                self.__dict__[dict_tag] = []

        if self._tags[tag] == N:
            try:
                self.__dict__[dict_tag].append(tvpair)
            except KeyError:
                embed()
                raise
        else:
            self.__dict__[dict_tag] = tvpair

    @property
    def tvpairs(self):
        return self._tvpairs()

    def _tvpairs(self, source_dict=None):
        index = tuple(self._tags)

        def key_(tvpair):
            out = index.index(tvpair.tag)
            if self._tags[tvpair.tag] == N:
                tosort = []
                for tvp in self.__dict__[TVPair.esc_(tvpair.tag)]:
                    tosort.append(tvp._value())
                sord = sorted(tosort, key=lambda a: a.lower())  # FIXME isn't quit right
                out += sord.index(tvpair._value()) / (len(sord) + 1)
            return out

        tosort = []
        if not source_dict:
            source_dict = self.__dict__
        for tvp in source_dict.values():
            if type(tvp) == list:
                tosort.extend(tvp)
            elif type(tvp) == property:
                embed()
            else:
                tosort.append(tvp)
        return sorted(tosort, key=key_)

    def __ttl__(self):
        block = ''.join(tvpair.__ttl__() for tvpair in self.tvpairs)
        return block.rstrip('\n').rstrip(';') + '.\n'

    def __str__(self):
        return '\n'.join(str(tvpair) for tvpair in self.tvpairs) + '\n'

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
                    except AttributeError:
                        embed()
                        raise
            else:
                raise AttributeError('Tag %s has no values!' % tag)

        for tag in self._r_tags:
            if tag not in tags:
                if warn:
                    print('probably a multipart definition')  # TODO
                    #raise ImportWarning('%s %s is missing a required tag %s' %
                                        #(self.__class__.__name__, str(self), tag))
                else:
                    raise AttributeError('%s must have a tag of type %s' %
                                         (self.__class__.__name__, tag))


class Header(TVPairStore):
    """ Header class. """
    _r_tags = ('format-version', )
    _r_defaults = ('1.2',)
    _all_tags = (
        ('format-version', 1),
        ('data-version', 1),
        ('date', 1),
        ('saved-by', 1),
        ('auto-generated-by', 1),
        ('ontology', 1),
        ('import', N),
        ('subsetdef', N),
        ('synonymtypedef', N),
        ('idspace', N),  # PREFIX http://uri
        ('id-mapping', N),
        ('default-relationship-id-previx', 1),
        ('default-namespace', 1),
        ('remark', N),
    )
    _datetime_fmt = '%d:%m:%Y %H:%M'  # WE USE ZULU

    def append_to_obofile(self, obofile):
        obofile.header = self

    def __str__(self):
        """ When we write to file overwrite the relevant variables without
            also overwriting the original data.
        """
        updated = {k:v for k, v in self.__dict__.items()}
        print(updated.keys())
        TVPair.factory('date', datetime.strftime(datetime.utcnow(), self._datetime_fmt),dict_=updated)
        TVPair.factory('auto-generated-by', __title__, dict_=updated)
        TVPair.factory('saved-by', getuser(), dict_=updated)
        tvpairs = self._tvpairs(updated)
        return '\n'.join(str(tvpair) for tvpair in tvpairs) + '\n'


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
        ('domain', 1), #
        ('range', 1), #
        ('is_anti_symmetric', 1), #
        ('is_cyclic', 1), #
        ('is_reflexive', 1), #
        ('is_symmetric', 1), #
        ('is_transitive', 1), #
        ('is_a', N),
        ('inverse_of', 1), #
        ('transitive_over', N), #
        ('intersection_of', N),  # no relationships, typedefs
        ('union_of', N),  # min 2, no relationships, typedefs
        ('disjoint_from', N),  # no relationships, typedefs
        ('relationship', N),
        ('property_value', N), ##
        ('is_obsolete', 1),
        ('replaced_by', N),
        ('consider', N),
        ('created_by', 1),
        ('creation_date', 1),
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
        'is_metadata_tag',
    ]
    def __new__(cls, *args, **kwargs):
        cls._all_tags = [tag for tag in cls._all_tags if tag[0] not in cls._bad_tags]
        instance = super().__new__(cls, *args, **kwargs)
        cls.__new__ = super().__new__  # enforce runonce
        return instance  # we return here so we chain the runonce

    def __init__(self, block=None, obofile=None, tvpairs=None):
        if block is not None and obofile is not None:
            super().__init__(block, obofile)
        else:
            super().__init__(tvpairs=tvpairs)

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
            print(self.id_)
            if set(self.__dict__) == set(callbacks.__dict__):
                pass
            else:
                callbacks.__dict__.update(self.__dict__)  # last one wins
                #raise ValueError('IT WOULD SEEM WE ALREADY EXIST! PLS HALP')  # TODO
        type_od[self.id_.value] = self
        type_od.__dict__[TVPair.esc_(self.id_.value)] = self
        if self.name.value not in type_od.names:  # add to names
            type_od.names[self.name.value] = self
        elif type(type_od.names[self.name.value]) == list:
            type_od.names[self.name.value].append(self)
        else:
            existing = type_od.names.pop(self.name.value)
            type_od.names[self.name.value] = [existing, self]

    def __str__(self):
        return '['+ self.__class__.__name__ +']\n' + super().__str__()


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
                    print(s._value)
                    key = s.value
                else:
                    key = s._value.text
                last_wins[key] = s
            self.synonym = sorted(list(last_wins.values()),key=lambda a:a.value)


class Typedef(Stanza):
    _bad_tags = ('union_of', 'intersection_of', 'disjoint_from', 'instance_of')


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
        self.value = value

    def value(self):
        raise NotImplemented('Impl in subclass pls.')

    def __str__(self):
        return str(self.value())

    def __repr__(self):
        return str(self.value())

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
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def get_target(self, tvpair):
        def callback(target):
            print(target, 'calling back',self)
            self.target = target

        self.target = 'DANGLING'
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
        #for arg, sep in (self.args, self.seps):  # TODO
            #print(arg, sep)
        return str(target)


class Is_a(DynamicValue):
    tag = 'is_a'
    seps = ' ',
    def __init__(self, target_id, tvpair):
        self.target_id = target_id
        self.get_target(tvpair)
        #print('yes i have a target id you lying sack of shit',self.target_id)

    def value(self):
        if type(self.target) == str:
            return self.target
        else:
            return str(self.target.id_.value)

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
        if type(self.target) == str:
            return self.target
        else:
            return str(self.target.id_.value)

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
        self.val = val
        self.datatype = datatype

    def value(self):
        s = self.seps[0]
        out = ''
        out += self.type_id + s + self.val
        if self.datatype:
            out += s + self.datatype
        return out

    @classmethod
    def parse(cls, value, *args):
        type_id, val_datatype = value.split(' ', 1)
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

    @classmethod
    def parse(cls, value, tvpair):
        value.strip().rstrip()  # in case we get garbage in from a bad split
        try:
            name, description = value.split(' "', 1)
            description = description[:-1]
        except ValueError:
            name = value  # TODO dangling stuff?
            description = None
        split = (name, description)
        return super().parse(split)


special_children = {sc.tag:sc for sc in (Subsetdef, Synonymtypedef, Idspace, Id_mapping, Def_, Synonym, Xref, Relationship, Is_a)}

def deNone(*args):
    for arg in args:
        if arg == None:
            yield ''
        else:
            yield arg

__all__ = [OboFile.__name__, TVPair.__name__, Header.__name__, Term.__name__, Typedef.__name__, Instance.__name__]

def main():
    args = docopt(__doc__, version='obo_io 0')
    if args['--ttl']:
        filename = args['<obofile>']
        if os.path.exists(filename):
            of = OboFile(filename)
            if args['<ttlfile>']:
                ttlfilename = args['<ttlfile>']
            else:
                fname, ext = filename.rsplit('.',1)
                if ext != 'obo':  # FIXME pretty sure a successful parse should be the measure here?
                    # TODO TEST ME!
                    raise TypeError('%s has wrong extension %s != obo !' % (filename, ext) )
                ttlfilename = fname + '.ttl'
            of.__ttl__()
            of.write(ttlfilename, type_='ttl')
        else:
            raise FileNotFoundError('No file named %s exists at that path!' % filename)
    else:
        filename = args['<obofile>']
        of = OboFile(filename=filename)
        ttl = of.__ttl__()
        embed()

if __name__ == '__main__':
    main()
