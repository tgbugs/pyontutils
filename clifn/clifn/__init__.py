"""Helper classes for organizing docopt programs

Usage:
    clifun-demo [options]
    clifun-demo sub-command-1 [options] <args>...
    clifun-demo sub-command-2 sub-command-1 [options] <args>...

Usage-Bad:
    Example:
        clifun-demo [options] <args>...
        clifun-demo cmd [options]
    Reason: <args>... masks cmd

Options:
    -o --optional      an optional argument
    -d --debug
"""

import re
import sys
from types import GeneratorType
from keyword import kwlist
from terminaltables import AsciiTable

__version__ = '0.0.1'


def python_identifier(string:str):
    """ pythonify a string for use as an identifier """

    to_empty = r'[<>\(\)\+…\x83]'
    s = string.strip()
    s = re.sub(to_empty, '', s)
    s = s.replace('#', 'number')
    s = re.sub('[^0-9a-zA-Z_]', '_', s)
    if s and s[0].isdigit():
        s = 'n_' + s
    s = re.sub('^[^a-zA-Z_]+', '_', s)
    s = s.lower()
    if s in kwlist:
        # avoid syntax errors and provide a consistent rule
        # for how to convert keywords into safe identifiers
        s = s + '_'

    return s


class Options:

    @classmethod
    def setup(cls, doc, argv=None, **kwargs):
        """ kwargs are passed to docopt """
        from docopt import docopt, parse_defaults
        args = docopt(doc, argv=argv, **kwargs)
        defaults = {o.name:o.value if o.argcount else None
                    for o in parse_defaults(doc)}
        options = cls(args, defaults, argv=argv)
        return options, args, defaults

    # there is only ever one of these because of how docopt works
    def __new__(cls, args, defaults, argv=None):
        cls = type(cls.__name__, (cls,), {})  # prevent persistence of args
        cls._args = args
        cls._defaults = defaults
        cls._argv = sys.argv if argv is None else argv
        for arg, value in cls._args.items():
            ident = python_identifier(arg.strip('-'))

            @property
            def options_property(self, value=value):
                f""" {arg} {value} """
                return value

            if hasattr(cls, ident):  # complex logic in properties
                ident = '_default_' + ident

            setattr(cls, ident, options_property)

        return super().__new__(cls)

    @property
    def commands(self):
        cmd_args = {k:v for k, v in self._args.items()
                    if v and not any(k.startswith(c) for c in ('-', '<'))}

        for k in sorted(cmd_args, key=lambda k: self._argv.index(k)):
            yield python_identifier(k)

    def asKwargs(self, cull_none=True):
        # use dir here so that both the dynamically added properties
        # and the statically defined properties are included
        out = {k:getattr(self, k)
               for k in dir(self.__class__)
               if k!= 'commands' and  # FIXME change to _commands
               isinstance(getattr(self.__class__, k), property)}
        if cull_none:
            out = {k:v for k, v in out.items() if v is not None}

        return out

    def __repr__(self):
        def key(kv, counter=[0]):
            k, v = kv
            counter[0] += 1
            return (not bool(v),
                    k.startswith('-'),
                    k.startswith('<'),
                    counter[0] if not any(k.startswith(c) for c in ('-', '<')) else 0,
                    k)

        rows = [[k, '' if v is None or v is False
                 else ('x' if v is True
                       else ('_' if isinstance(v, list) else v))]
                for k, v in sorted([(k, v) for k, v in self._args.items()
                                    if v or k.startswith('-')
                ], key=key)
        ]
        atable = AsciiTable([['arg', '']] + rows, title='docopt args')
        atable.justify_columns[1] = 'center'
        return atable.table


class Dispatcher:
    port_attrs = tuple()  # request from above
    child_port_attrs = tuple()  # force on below
    parent = None

    class _CommandNotFoundError(Exception):
        """ Oops! """

    def __init__(self, options_or_parent, port_attrs=tuple()):
        if isinstance(options_or_parent, Dispatcher):
            parent = options_or_parent
            self.parent = parent
            self.options = parent.options
            if not port_attrs:
                port_attrs = self.port_attrs

            all_attrs = set(parent.child_port_attrs) | set(port_attrs)
            for attr in all_attrs:
                if attr in parent.child_port_attrs:
                    # ok to skip if parent doesn't have
                    # what it wants to give
                    value = getattr(parent, attr, None)
                    if value is None:
                        continue
                else:
                    # fail if any required by child are missing
                    value = getattr(parent, attr)

                setattr(self, attr, value)

        else:
            self.options = options_or_parent

    def _oops(self):
        raise self._CommandNotFoundError

    def __call__(self, previous_command=None):
        # FIXME this might fail to run annos -> shell correctly
        for command in self.options.commands:
            if command == previous_command:
                continue

            try:
                value = getattr(self, command, self._oops)()
                if isinstance(value, GeneratorType):
                    value = list(value)

                return value
            except self._CommandNotFoundError:
                # this is a hack to not have to deal with command ordering 
                # basically the structure of the subdispatchers should take
                # care of this automatically regardless of the dict ordering
                continue

        else:
            return self.default()

    def default(self):
        raise NotImplementedError('docopt I can\'t believe you\'ve done this')


def main():
    options, *ad = Options.setup(__doc__, version='clifun-demo 0.0.0')

    class Main(Dispatcher):
        """
        The dispatcher for the demo.
        Normally this class is at the top level NOT in main.
        """

        def default(self):
            return ('default', *self.options.args)

        def sub_command_1(self):
            return ('sc1', *self.options.args)

        def sub_command_2(self):
            return ('sc2', self.options.sub_command_1, *self.options.args)

    main = Main(options)
    if main.options.debug:
        print(main.options)

    out = main()
    print(out)
    assert out
    return out


if __name__ == '__main__':
    main()
