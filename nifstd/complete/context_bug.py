#!/usr/bin/env python3

import inspect
from pathlib import Path
from collections import MutableMapping


def stack_magic(stack):
    if len(stack) > 2 and 'exec_module' in [f.function for f in stack]:
        if '__builtins__' not in stack[1][0].f_locals:
            index = 2  # we are in function scope in module context
        else:
            index = 1
    else:
        index = -1

    out = stack[index][0].f_locals
    return out


class graphBase:
    LocalNames = {}


def addLNBase(LocalName, phenotype, g=None):
    inj = {v:k for k, v in graphBase.LocalNames.items()}
    if not LocalName.isidentifier():
        raise NameError('LocalName \'%s\' is no a valid python identifier' % LocalName)
    if g is None:
        raise TypeError('please pass in the globals for the calling scope')
    if LocalName in g and g[LocalName] != phenotype:
        raise NameError('%r is already in use as a LocalName for %r'
                        % (LocalName, g[LocalName]))
    elif phenotype in inj and inj[phenotype] != LocalName:
        raise ValueError(('Mapping between LocalNames and phenotypes must be injective.\n'
                          'Cannot cannot bind %r to %r.\n'
                          'It is already bound to %r') %
                         (LocalName, phenotype, inj[phenotype]))
    g[LocalName] = phenotype


def setLocalNameBase(LocalName, phenotype, g=None):
    addLNBase(LocalName, phenotype, g)
    graphBase.LocalNames[LocalName] = phenotype


class injective(type):
    render_types = tuple()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return dict()

    def __new__(cls, name, bases, inj_dict):
        self = super().__new__(cls, name, bases, dict(inj_dict))
        self.debug = False
        return self

    def __enter__(self):
        self.inside_only = 'YES WE ARE INSIDE'
        stack = inspect.stack()
        if self.debug:
            s0 = stack[0]
            print(s0.function, Path(s0.filename).name, s0.lineno)
        g = stack_magic(stack)
        self._existing = set()
        setLocalNameBase(f'setBy_{self.__name__}', self.__name__, g)
        for k in dir(self):
            v = getattr(self, k)  # use this instead of __dict__ to get parents
            if any(isinstance(v, t) for t in self.render_types):
                if k in graphBase.LocalNames:  # name was in enclosing scope
                    self._existing.add(k)
                setLocalNameBase(k, v, g)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.inside_only = None
        del self.inside_only
        stack = inspect.stack()
        if self.debug:
            s0 = stack[0]
            print(s0.function, Path(s0.filename).name, s0.lineno)
        g = stack_magic(stack)
        for k in dir(self):
            v = getattr(self, k)  # use this instead of __dict__ to get parents
            if k not in self._existing and any(isinstance(v, t) for t in self.render_types):
                try:
                    g.pop(k)
                    graphBase.LocalNames.pop(k)  # this should only run if g pops correctly? XXX FIXME?
                except KeyError:
                    raise KeyError('%s not in globals, are you calling resetLocalNames from a local scope?' % k)


class LocalNameManager(metaclass=injective):
    """ Base class for sets of local names for phenotypes.
        Local name managers are singletons and do not need to be instantiated.
        Can be used in a context manager or globally via setLocalNames.
        It is possible to subclass to add your custom names to a core. """
    render_types = str, list


class IO(LocalNameManager):
    #debug = True  # doesn't work
    render_types = str, list
    ERROR = 'HEY KIDS WATCH THIS'

IO.debug = True  # more crazyness is that this has to be set here not in class scope

def test_outside():
    try:
        IO.inside_only
        raise ValueError('OUTSIDE INCORRECT')
    except AttributeError:
        #print('OUTSIDE fails as expected')
        pass

def test_inside():
    try:
        test_outside()
        raise ValueError('INSIDE INCORRECT')
    except ValueError:
        #print('INSIDE fails as expected')
        pass

test_outside()
print('global scope')
with IO:
    print('inside')
    print(IO.inside_only)
    print('still inside')
    test_inside()

test_outside()



print('function scope')
def function():
    test_outside()
    with IO:
        print('inside')
        print(IO.inside_only)
        print('still inside')
    test_outside()

function()


print('global scope 2')
with IO:
    print('inside')
    print(ERROR)
    print('still inside')


print('function scope 2')
def function():
    with IO:
        print('inside')
        print(locals())
        print(ERROR)
        print('still inside')

function()
