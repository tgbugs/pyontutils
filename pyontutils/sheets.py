#!/usr/bin/env python3.7
""" api access for google sheets (and friends)
Usage:
    googapis auth (sheets|docs|drive)... [options] [--drive-scope=<SCOPE>...]

Examples:
    googapis auth sheets

Options:
    -n --readonly             set the readonly scope
    --drive-scope=<SCOPE>...  add drive scopes (overrides readonly)
                              values: appdata
                                      file
                                      metadata
                                      metadata.readonly
                                      photos.readonly
                                      readonly
                                      scripts
    --noauth_local_webserver  passthrough for oauth
    --auth_host_name=N        passthrough for oauth
    --auth_host_port=P        passthrough for oauth
    --logging_level=LL        passthrough for oauth
    -d --debug
"""
# TODO decouple oauth group sheets library
import socket
import itertools
from pathlib import Path
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from pyontutils.utils import byCol, log as _log
from pyontutils.config import devconfig

log = _log.getChild('sheets')
spath = Path(devconfig.secrets_file).parent


def get_oauth_service(api='sheets', version='v4', readonly=True, SCOPES=None):
    if readonly:  # FIXME the division isn't so clean for drive ...
        store_file = devconfig.secrets('google', 'api', 'store-file-readonly')
    else:
        store_file = devconfig.secrets('google', 'api', 'store-file')

    store = file.Storage((spath / store_file).as_posix())
    creds = store.get()
    if not creds or creds.invalid:
        # the first time you run this you will need to use the --noauth_local_webserver args
        creds_file = devconfig.secrets('google', 'api', 'creds-file')
        flow = client.flow_from_clientsecrets((spath / creds_file).as_posix(), SCOPES)
        creds = tools.run_flow(flow, store)

    service = build(api, version, http=creds.authorize(Http()))
    return service


def update_sheet_values(spreadsheet_name, sheet_name, values, spreadsheet_service=None):
    SPREADSHEET_ID = devconfig.secrets('google', 'sheets', spreadsheet_name)  # FIXME wrong order ...
    if spreadsheet_service is None:
        service = get_oauth_service(readonly=False)
        ss = service.spreadsheets()
    else:
        ss = spreadsheet_service
    """
    requests = [
        {'updateCells': {
            'start': {'sheetId': TODO,
                      'rowIndex': 0,
                      'columnIndex': 0}
            'rows': {'values'}
        }
        }]
    response = ss.batchUpdate(
        spreadsheetId=SPREADSHEET_ID, range=sheet_name,
        body=body).execute()

    """
    body = {'values': values}

    response = ss.values().update(
        spreadsheetId=SPREADSHEET_ID, range=sheet_name,
        valueInputOption='USER_ENTERED', body=body).execute()

    return response


def get_sheet_values(spreadsheet_name, sheet_name, fetch_grid=False, spreadsheet_service=None):
    SPREADSHEET_ID = devconfig.secrets('google', 'sheets', spreadsheet_name)
    if spreadsheet_service is None:
        service = get_oauth_service()
        ss = service.spreadsheets()
    else:
        ss = spreadsheet_service
    if fetch_grid:
        grid = ss.get(spreadsheetId=SPREADSHEET_ID, includeGridData=True).execute()
        notes = get_notes_from_grid(grid, sheet_name)
        notes_index = {(i, j):v for i, j, v in notes}
    else:
        grid = {}
        notes_index = {}

    result = ss.values().get(spreadsheetId=SPREADSHEET_ID, range=sheet_name).execute()
    values = result.get('values', [])
    return values, grid, notes_index


def get_notes_from_grid(grid, title):
    for sheet in grid['sheets']:
        if sheet['properties']['title'] == title:
            for datum in sheet['data']:
                for i, row in enumerate(datum['rowData']):
                    # if cell is blank it might not have values
                    if 'values' in row:
                        for j, cell in enumerate(row['values']):
                            if 'note' in cell:
                                yield i, j, cell['note']

def get_note(row_index, column_index, notes_index):
    try:
        return notes_index[row_index, column_index]
    except KeyError:
        return None


class Sheet:
    """ access a single sheet as a basis for a workflow """

    name = None
    sheet_name = None
    fetch_grid = False
    index_columns = tuple()

    def __init__(self, name=None, sheet_name=None, fetch_grid=None, readonly=True):
        """ name to override in case the same pattern is used elsewhere """
        if name is not None:
            self.name = name
        if sheet_name is not None:
            self.sheet_name = sheet_name

        if fetch_grid is not None:
            self.fetch_grid = fetch_grid

        self.readonly = readonly
        self._setup()
        self.fetch()

    def _setup(self):
        if self.readonly:
            if not hasattr(Sheet, '__spreadsheet_service_ro'):
                service = get_oauth_service(readonly=self.readonly)  # I think it is correct to keep this ephimoral
                Sheet.__spreadsheet_service_ro = service.spreadsheets()

            self._spreadsheet_service = Sheet.__spreadsheet_service_ro

        else:
            if not hasattr(Sheet, '__spreadsheet_service'):
                service = get_oauth_service(readonly=self.readonly)
                Sheet.__spreadsheet_service = service.spreadsheets()

            self._spreadsheet_service = Sheet.__spreadsheet_service

    def fetch(self, fetch_grid=None):
        """ update remote values (called automatically at __init__) """
        if fetch_grid is None:
            fetch_grid = self.fetch_grid

        values, grid, notes_index = get_sheet_values(self.name, self.sheet_name,
                                                     spreadsheet_service=self._spreadsheet_service,
                                                     fetch_grid=fetch_grid)

        self.raw_values = values
        self.values = [list(r) for r in zip(*itertools.zip_longest(*self.raw_values, fillvalue=''))]
        try:
            self.byCol = byCol(self.values, to_index=self.index_columns)
        except ValueError as e:
            log.warning('Sheet has malformed header, not setting byCol')

        self.grid = grid
        self.notes_index = notes_index

    def update(self, values):
        if self.readonly:
            raise PermissionError('sheet was loaded readonly, '
                                  'if you want to write '
                                  'reinit with readonly=False')

        update_sheet_values(self.name,
                            self.sheet_name,
                            values,
                            spreadsheet_service=self.spreadsheet_service)

    def show_notes(self):
        for i, row in enumerate(self.values):
            for j, cell in enumerate(row):
                if (i, j) in self.notes_index:
                    print(f'========================== {i} {j}',
                        cell,
                        '------------------',
                        self.notes_index[i, j],
                        sep='\n')

    def get_note(row_index, column_index):
        return get_note(row_index, column_index, self.notes_index)


def main():
    import sys
    from pyontutils.clifun import Dispatcher, Options as BaseOptions
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
                if suffix:
                    suffixes.append(suffix)

                suffixes += ['.' + s for s in self.options.drive_scope]

                if not suffixes:
                    suffixes = '',

                for suffix in suffixes:
                    yield base + 'drive' + suffix

        def auth(self):
            newline = '\n'
            scopes = list(self._scopes)
            if self.options.debug:
                log.debug(f'requesting for scopes:\n{newline.join(scopes)}')

            service = get_oauth_service(readonly=self.options.readonly, SCOPES=scopes)
            # FIXME decouple this ...
            log.info(f'Auth finished successfully for scopes:\n{newline.join(scopes)}')

    from docopt import docopt, parse_defaults
    args = docopt(__doc__, version='clifun-demo 0.0.0')
    passthrough = ('--noauth_local_webserver',
                   '--auth_host_name',
                   '--auth_host_port',
                   '--logging_level')
    to_pop = [arg for i, arg in enumerate(sys.argv)
              if i and not [None for pt in passthrough if pt in arg]]
    for arg in to_pop:
        sys.argv.pop(sys.argv.index(arg))

    defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}
    options = Options(args, defaults)
    main = Main(options)
    if main.options.debug:
        log.setLevel('DEBUG')
        print(main.options)

    main()


if __name__ == '__main__':
    main()
