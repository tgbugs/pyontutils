import pickle
import itertools
from pathlib import Path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pyontutils.utils import byCol, log as _log
from pyontutils.config import auth

# TODO decouple oauth group sheets library

log = _log.getChild('sheets')


def _FakeService():
    """ use if you need a fake service from build """

    class e:
        execute = lambda : {'sheets':[],}
    class v:
        def get(range=None):
            return []
    class g:
        def get(spreadsheetId=None, includeGridData=None, range=None):
            return e
        values = lambda : g
    class s:
        spreadsheets = lambda : g

    return s


def get_oauth_service(api='sheets', version='v4', readonly=True):
    """ outward facing API for accessing oauth creds """
    return _get_oauth_service(api=api, version=version, readonly=readonly)


def _get_oauth_service(api='sheets', version='v4', readonly=True, SCOPES=None):
    """ Inner implementation for get oauth. If you see this function used directly
        anywhere other than in googapis it is almost certainly a mistake. """

    if readonly:  # FIXME the division isn't so clean for drive ...
        _auth_var = 'google-api-store-file-readonly'
    else:
        _auth_var = 'google-api-store-file'

    try:
        store_file = auth.get_path(_auth_var)
    except KeyError as e:
        _msg = (f'No value found for {_auth_var} in {auth._path}\n'
                'See the previous error for more details about the cause.')
        raise ValueError(_msg) from e

    if store_file is None:
        msg = (f'No file exists at the path specified by {_auth_var} in {auth._path}')
        raise ValueError(msg)

    # TODO log which file it is writing to ...
    if store_file.exists():
        with open(store_file, 'rb') as f:
            try:
                creds = pickle.load(f)
            except pickle.UnpicklingError as e:
                # FIXME need better way to trace errors in a way
                # that won't leak secrets by default
                log.error(f'problem in file at path for {_auth_var}')
                raise e
    else:
        creds = None
        if SCOPES is None:
            raise TypeError('SCOPES has not been set, possibly because this is\n'
                            'being called by a function that expects the store file\n'
                            'to already exist. Please run `googapis auth` with the\n'
                            'appropriate scope.')

    if not creds or not creds.valid:
        # the first time you run this you will need to use the --noauth_local_webserver args
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_file = auth.get_path('google-api-creds-file')
            flow = InstalledAppFlow.from_client_secrets_file((creds_file).as_posix(), SCOPES)
            creds = flow.run_console()

        with open(store_file, 'wb') as f:
            pickle.dump(creds, f)

    service = build(api, version, credentials=creds)
    return service


def update_sheet_values(spreadsheet_name, sheet_name, values, spreadsheet_service=None):
    SPREADSHEET_ID = auth.dynamic_config.secrets('google', 'sheets', spreadsheet_name)  # FIXME wrong order ...
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


def default_filter_cell(cell):
    remove = (
        'userEnteredValue',
        'effectiveValue',
        'userEnteredFormat',
        'effectiveFormat',
        'padding',
        'verticalAlignment',
        'wrapStrategy',
        'textFormat',
    )
    for k in remove:
        cell.pop(k, None)


def get_sheet_values(spreadsheet_name, sheet_name, fetch_grid=False, spreadsheet_service=None,
                     filter_cell=default_filter_cell):
    SPREADSHEET_ID = auth.dynamic_config.secrets('google', 'sheets', spreadsheet_name)
    if spreadsheet_service is None:
        service = get_oauth_service()
        ss = service.spreadsheets()
    else:
        ss = spreadsheet_service

    result = ss.values().get(spreadsheetId=SPREADSHEET_ID, range=sheet_name).execute()
    values = result.get('values', [])

    if fetch_grid:
        def num_to_ab(n):
            string = ''
            while n > 0:
                n, remainder = divmod(n - 1, 26)
                string = chr(65 + remainder) + string
            return string

        rm = len(values)
        cm = max([len(c) for c in values])
        cml = num_to_ab(cm)
        ranges = f'{sheet_name}!$A$1:${cml}'
        #ranges = result['range']  # overshoots, which is bad for the 1000 cell case

        grid = ss.get(spreadsheetId=SPREADSHEET_ID,
                      ranges=ranges,
                      includeGridData=True).execute()

        for sheet in grid['sheets']:
            sheet.pop('bandedRanges', None)
            for d in sheet['data']:
                d.pop('rowMetadata')
                d.pop('columnMetadata')

        cells = get_cells_from_grid(grid, sheet_name, filter_cell)
        cells_index = {(i, j):v for i, j, v in cells}
    else:
        grid = {}
        cells_index = {}

    return values, grid, cells_index


def get_cells_from_grid(grid, title, filter_cell):
    for sheet in grid['sheets']:
        if sheet['properties']['title'] == title:
            for datum in sheet['data']:
                for i, row in enumerate(datum['rowData']):
                    # if cell is blank it might not have values
                    if 'values' in row:
                        for j, cell in enumerate(row['values']):
                            if filter_cell is not None:
                                filter_cell(cell)

                            yield i, j, cell


def get_note(row_index, column_index, cells_index):
    try:
        cell = cells_index[row_index, column_index]
        if 'note' in cell:
            return cell['note']

    except KeyError:
        return None


class Cell:
    def __init__(self, sheet, row_index, column_index):
        self.sheet = sheet
        self.row_index = row_index
        self.column_index = column_index

    @property
    def column_header(self):
        return self.sheet.byCol.header[self.column_index]

    @property
    def row_header(self):
        if self.sheet.byCol.index_columns:
            col = self.sheet.byCol.index_columns[0]
            row_header_column_index = self.sheet.byCol.header.index(col)
            return self.sheet.values[self.row_index][row_header_column_index]

    @property
    def value(self):
        return self.sheet.values[self.row_index][self.column_index]

    @property
    def grid(self):
        return self.sheet.get_cell(self.row_index, self.column_index)

    @property
    def hyperlink(self):
        return self.grid.get('hyperlink', None)


class Sheet:
    """ access a single sheet as a basis for a workflow """

    name = None
    sheet_name = None
    fetch_grid = False
    index_columns = tuple()

    def __init__(self, name=None, sheet_name=None, fetch_grid=None, readonly=True,
                 filter_cell=default_filter_cell):
        """ name to override in case the same pattern is used elsewhere """
        if name is not None:
            self.name = name
        if sheet_name is not None:
            self.sheet_name = sheet_name

        if fetch_grid is not None:
            self.fetch_grid = fetch_grid

        self.readonly = readonly
        self._setup()
        self.fetch(filter_cell=filter_cell)

    @classmethod
    def _sheet_id(cls):
        return auth.dynamic_config.secrets('google', 'sheets', cls.name)

    @classmethod
    def _uri_human(cls):
        # TODO sheet_name -> gid ??
        return f'https://docs.google.com/spreadsheets/d/{cls._sheet_id()}/edit'

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

    def fetch(self, fetch_grid=None, filter_cell=None):
        """ update remote values (called automatically at __init__) """
        if fetch_grid is None:
            fetch_grid = self.fetch_grid

        values, grid, cells_index = get_sheet_values(self.name, self.sheet_name,
                                                     spreadsheet_service=self._spreadsheet_service,
                                                     fetch_grid=fetch_grid,
                                                     filter_cell=filter_cell)

        self.raw_values = values
        self.values = [list(r) for r in zip(*itertools.zip_longest(*self.raw_values, fillvalue=''))]
        try:
            self.byCol = byCol(self.values, to_index=self.index_columns)
        except ValueError as e:
            log.error(e)
            log.warning('Sheet has malformed header, not setting byCol')
        except IndexError as e:
            log.error(e)
            log.warning('Sheet has no header, not setting byCol')

        self.grid = grid
        self.cells_index = cells_index

        #self._lol_g, self._lol_c = grid, cells_index  # WHAT! this causes the problem !?
        #import copy
        #self._lol_g, self._lol_c = copy.deepcopy(grid), copy.deepcopy(cells_index)  # as does this

        #for sheet in grid['sheets']:

        #self.grid = {}  # grid is BAD
        #self.cells_index = {}  # cells_index is BAD

        #_asdf = pickle.dumps(grid)
        #print('grid', len(_asdf) / 1024 ** 2)
        #_asdf = pickle.dumps(cells_index)
        #print('cells_index', len(_asdf) / 1024 ** 2)

        #_asdf = pickle.dumps(self)
        #print(len(_asdf) / 1024 ** 2)

    def update(self, values):
        """ update all values at the same time """
        if self.readonly:
            raise PermissionError('sheet was loaded readonly, '
                                  'if you want to write '
                                  'reinit with readonly=False')

        update_sheet_values(self.name,
                            self.sheet_name,
                            values,
                            spreadsheet_service=self._spreadsheet_service)

    def show_notes(self):
        for i, row in enumerate(self.values):
            for j, cell in enumerate(row):
                if (i, j) in self.cells_index:
                    print(f'========================== {i} {j}',
                        cell,
                        '------------------',
                        self.cells_index[i, j]['note'],
                        sep='\n')

    def get_note(self, row_index, column_index):
        return get_note(row_index, column_index, self.cells_index)

    def get_cell(self, row_index, column_index):
        try:
            return self.cells_index[row_index, column_index]
        except KeyError:
            return {}  # need to return the empty dict for type safety
        #grid = [s for s in self.grid['sheets'] if s['properties']['title'] == self.sheet_name][0]
        #rd = grid['data'][0]['rowData']

    def cell_object(self, row_index, column_index):
        return Cell(self, row_index, column_index)
