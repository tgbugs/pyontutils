#!/usr/bin/env python3
""" api access for google sheets (and friends)
Usage:
    googapis auth (sheets|docs|drive)... [options] [--drive-scope=<SCOPE>...]

Examples:
    googapis auth sheets

Options:
    --store-file=<PATH>...    write to a specific store file
    -n --readonly             set the readonly scope
    --drive-scope=<SCOPE>...  add drive scopes (overrides readonly)
                              values: appdata
                                      file
                                      metadata
                                      metadata.readonly
                                      photos.readonly
                                      readonly
                                      scripts
    -d --debug
"""

import sys
from pathlib import Path
from pyontutils.utils import log
from pyontutils.clifun import Dispatcher, Options as BaseOptions
from pyontutils.sheets import _get_oauth_service

log = log.getChild('googapis')


class Options(BaseOptions):
    drive_scopes = (
        'appdata',
        'file',
        'metadata',
        'metadata.readonly',
        'photos.readonly',
        'readonly',
        'scripts',)

    def __new__(cls, args, defaults):
        bads = []
        for scope in args['--drive-scope']:
            if scope not in cls.drive_scopes:
                bads.append(scope)

        if bads:
            log.error(f'Invalid scopes! {bads}')
            sys.exit(1)

        return super().__new__(cls, args, defaults)

    @property
    def store_file(self):
        return Path(self._args['--store-file']).resolve()


class Main(Dispatcher):

    @property
    def _scopes(self):
        base = 'https://www.googleapis.com/auth/'
        suffix = '.readonly' if self.options.readonly else ''
        if self.options.sheets:
            yield base + 'spreadsheets' + suffix

        if self.options.docs:
            yield base + 'doccuments' + suffix

        if self.options.drive:
            suffixes = []

            suffixes += ['.' + s for s in self.options.drive_scope]

            if suffix and not suffixes:
                suffixes.append(suffix)

            if not suffixes:
                suffixes = '',

            for suffix in suffixes:
                yield base + 'drive' + suffix

    def auth(self):
        newline = '\n'
        scopes = list(self._scopes)
        if self.options.debug:
            log.debug(f'requesting for scopes:\n{newline.join(scopes)}')

        service = _get_oauth_service(readonly=self.options.readonly, SCOPES=scopes,
                                     store_file=self.options.store_file)
        # FIXME decouple this ...
        log.info(f'Auth finished successfully for scopes:\n{newline.join(scopes)}')


def main():
    from docopt import docopt, parse_defaults
    args = docopt(__doc__, version='googapis 0.0.0')
    defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}
    options = Options(args, defaults)
    main = Main(options)
    if main.options.debug:
        log.setLevel('DEBUG')
        print(main.options)

    main()


if __name__ == '__main__':
    main()
