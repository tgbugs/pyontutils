#!/usr/bin/env python3
"""Generate slim ontology files

Usage:
    slimgen [options] (chebi|gene|doid)...
    slimgen [options] all

Options:
    -h --help            show this
    -j --jobs=NJOBS      number of jobs [default: 1]
    -d --debug

"""

from pyontutils import clifun as clif
import nifstd_tools.chebi_slim
import nifstd_tools.ncbigene_slim
import nifstd_tools.doid_slim


class Options(clif.Options):
    pass


class Main(clif.Dispatcher):

    def __call__(self):
        commands = [getattr(Main, c)() for c in
                    (['chebi', 'gene', 'doid']
                     if self.options.all else
                    self.options.commands)]
        lc = len(commands)
        nj = int(self.options.jobs)
        if lc < nj:
            nj = lc

        if nj == 1:
            [command() for command in commands]

        else:
            from joblib import Parallel, delayed
            Parallel(n_jobs=nj, verbose=10)(delayed(command)()
                                            for command in commands)

    @staticmethod
    def chebi():
        return nifstd_tools.chebi_slim.main

    @staticmethod
    def gene():
        return nifstd_tools.ncbigene_slim.main

    @staticmethod
    def doid():
        return nifstd_tools.doid_slim.main

def main():
    from docopt import docopt, parse_defaults
    args = docopt(__doc__, version='slimgen 0.0.0')
    defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}
    options = Options(args, defaults)
    main = Main(options)
    if main.options.debug:
        print(main.options)

    main()


if __name__ == '__main__':
    main()
