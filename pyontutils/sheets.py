import ast
import copy
import pickle
import itertools
from pathlib import Path
from numbers import Number
from urllib.parse import urlparse
import idlib
import htmlfn as hfn
from terminaltables import AsciiTable
from pyontutils.utils import byCol, log as _log
from pyontutils.config import auth
from pyontutils.clifun import python_identifier

# TODO decouple oauth group sheets library

log = _log.getChild('sheets')

CELL_DID_NOT_EXIST = type('CellDidNotExist', (object,), {})()
CELL_REMOVED = type('CellRemoved', (object,), {})()  # FIXME this is ... bad? or is IndexError worse?
__scopes_error_message = (
    'SCOPES has not been set, possibly because this is\n'
    'being called by a function that expects the store file\n'
    'to already exist. Please run `googapis auth` with the\n'
    'appropriate scope.')


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

def _get_oauth_service(
        api='sheets', version='v4', readonly=True, SCOPES=None,
        store_file=None, service_account_file=None):
    """ Inner implementation for get oauth. If you see this function used
        anywhere other than in googapis it is almost certainly a mistake. """

    if service_account_file is None:
        try:
            service_account_file = auth.get_path(
                'google-api-service-account-file')
        except KeyError:
            # not required to be set, and in many cases will not be due to
            # needing slightly different permissions in slightly different cases
            pass

    if service_account_file is not None:
        if SCOPES is None:
            base = 'https://www.googleapis.com/auth/'
            suffix = '.readonly' if readonly else ''
            scope = {'sheets': 'spreadsheets',
                    'docs': 'doccuments'}[api]  # KeyError on unknown api
            SCOPES=[base + scope + suffix]

        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=SCOPES)

        store_file = False  # bypass is None since we have creds
    else:
        creds = None

    if store_file is None:
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
            _p = 'RUNTIME_CONFIG' if auth._path is None else auth._path
            _u = ('RUNTIME_CONFIG' if auth.user_config._path is None
                else auth.user_config._path)
            # FIXME bad error message, need to check whether the key is even in
            # the user config, and yes we need our way to update the user config
            # and warn about unexpected formats for orthauth configs
            # XXX this branch happens when the keys are in the user config
            # but they are null and no secrets path is set
            msg = ('The file (or absense of file) specified by '
                   f'{_auth_var} in {_p} and {_u} cound not be found')

            if hasattr(auth, '_runtime_config'):
                log.debug(auth._runtime_config)

            if hasattr(auth.user_config, '_runtime_config'):
                log.debug(auth.user_config._runtime_config)

            raise ValueError(msg)

    # TODO log which file it is writing to ...
    if store_file and store_file.exists():
        with open(store_file, 'rb') as f:
            try:
                creds = pickle.load(f)
            except pickle.UnpicklingError as e:
                # FIXME need better way to trace errors in a way
                # that won't leak secrets by default
                log.error(f'problem in file at path for {_auth_var}')
                raise e
    elif creds:
        pass  # got them from the service account file
    else:
        creds = None
        if SCOPES is None:
            raise TypeError(__scopes_error_message)

    if not creds or service_account_file is None and not creds.valid:
        # the first time you run this you will need to use the --noauth_local_webserver args
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow # XXX slow import
            creds_file = auth.get_path('google-api-creds-file')
            flow = InstalledAppFlow.from_client_secrets_file((creds_file).as_posix(), SCOPES)
            creds = flow.run_console()

        with open(store_file, 'wb') as f:
            pickle.dump(creds, f)

    if SCOPES is not None:
        # if SCOPES is None then it is up to the user to make sure
        # they correctly match scopes, we don't warn them here
        _missing = [scope for scope in SCOPES if scope not in creds.scopes]
        if _missing:
            msg = (
                f'credentials in {store_file} lack '
                f'authorization for {_missing}')

            raise ValueError(msg)

    from googleapiclient.discovery import build
    service = build(api, version, credentials=creds)
    return service


def update_sheet_values(spreadsheet_name, sheet_name, values,
                        spreadsheet_service=None, SPREADSHEET_ID=None):
    if SPREADSHEET_ID is None:
        SPREADSHEET_ID = auth.user_config.secrets('google', 'sheets', spreadsheet_name)  # FIXME wrong order ...

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


def num_to_ab(n):
    string = ''
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


def get_sheet_values(spreadsheet_name, sheet_name, fetch_grid=False, spreadsheet_service=None,
                     filter_cell=default_filter_cell, SPREADSHEET_ID=None):
    if SPREADSHEET_ID is None:
        SPREADSHEET_ID = auth.user_config.secrets('google', 'sheets', spreadsheet_name)

    if spreadsheet_service is None:
        service = get_oauth_service()
        ss = service.spreadsheets()
    else:
        ss = spreadsheet_service

    result = ss.values().get(spreadsheetId=SPREADSHEET_ID, range=sheet_name).execute()
    values = result.get('values', [])

    results_formula = ss.values().get(spreadsheetId=SPREADSHEET_ID, range=sheet_name,
                                      valueRenderOption='FORMULA').execute()
    values_formula = results_formula.get('values', [])

    if fetch_grid:
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

    return values, values_formula, grid, cells_index


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
    def row(self):
        return Row(self.sheet, self.row_index)

    @property
    def column(self):
        return Column(self.sheet, self.column_index)

    def __repr__(self):
        # TODO deleted ??
        changed = '*' if self in self.sheet._uncommitted_updates else ' '
        #return f'<Cell{changed} {self.row_index:>4},{self.column_index:>4} -> {self.value!r}>'
        return f'<Cell{changed} {self.range} -> {self.value!r}>'

    def __hash__(self):
        return hash((self.__class__, self.sheet, self.row_index, self.column_index))

    def __eq__(self, other):
        """ cell equality is equality of location, not contents """
        s = self.sheet, self.row_index, self.column_index
        o = other.sheet, other.row_index, other.column_index
        return s == o

    @property
    def column_header(self):
        return self.sheet.byCol.header[self.column_index]
        # FIXME normalized vs unnormalized
        return self.sheet.values[0][self.column_index]

    @property
    def row_header(self):
        if self.sheet.index_columns:
            col = self.sheet.index_columns[0]
            # FIXME how to handle normalized names once we remove byCol?
            row_header_column_index = self.sheet.byCol.header.index(col)
            return self.sheet.values[self.row_index][row_header_column_index]

    @property
    def value(self):
        return self.sheet.values[self.row_index][self.column_index]

    @value.setter
    def value(self, value):
        self.sheet._setCellValue(self, value)

    @property
    def _value_str(self):
        # FIXME TODO this needs a proper systematic solution
        # that can support more that just updating strings
        v = self.value
        if v == CELL_REMOVED:
            return ''
        else:
            return v

    @property
    def value_formula(self):
        # XXX HACK not kept in sync DO NOT USE THIS IF YOU MODIFY THE SHEET
        return self.sheet._values_formula[self.row_index][self.column_index]

    @property
    def grid(self):
        return self.sheet.get_cell(self.row_index, self.column_index)

    @property
    def hyperlink(self):
        # FIXME see if we can get this in some other way than the grid e.g. via ValueRenderOption=FORMULA
        if self.grid:
            return self.grid.get('hyperlink', None)
        else:
            vf = self.value_formula
            prefix = '=HYPERLINK'
            if vf.startswith(prefix):
                tup_str = vf[len(prefix):]
                link, text = ast.literal_eval(tup_str)
                return link

    @property
    def atag(self):
        return hfn.atag(self.hyperlink, self.value)

    def asTerm(self):
        # TODO as identifier ?
        return idlib.from_oq.OntTerm(iri=self.hyperlink, label=self.value)

    def _ciri(self):
        ci = self.column_index
        if ci < 0:
            ci = len(self.sheet.values[0]) + ci

        ri = self.row_index
        if ri < 0:
            ri = len(self.sheet.values) + ri

        return ci, ri

    @property
    def _range(self):
        ci, ri =  self._ciri()
        c = num_to_ab(ci + 1)
        r = ri + 1
        return f'{c}{r}'

    @property
    def range(self):
        return f'{self.sheet.sheet_name}!{self._range}'

    def _obj_coord(self):
        ci, ri = self._ciri()
        sid = self.row.sheet.sheetId()  # FIXME perf?
        return {
            'sheetId': sid,
            'rowIndex': ri,
            'columnIndex': ci,
        }

    def _obj_range(self):
        ci, ri = self._ciri()
        sid = self.row.sheet.sheetId()  # FIXME perf?
        return {
            'sheetId': sid,
            'startRowIndex': ri,
            'endRowIndex': ri + 1,
            'startColumnIndex': ci,
            'endColumnIndex': ci + 1,
        }

    def _obj_update(self):
        return {'updateCells': {
            'rows': [
                {'values': [self._obj_value(),]},],
            'fields': 'userEnteredValue',
            #'start': self._obj_coord(),  # only need one of start or range
            'range': self._obj_range(),}}

    def _obj_value(self):
        value = self._value_str
        if isinstance(value, bool):
            d = {'boolValue': value}
        elif isinstance(value, Number):
            d = {'numberValue': value}
        else:
            d = {'stringValue': value}

        return {'userEnteredValue': d}


class Row:

    def __init__(self, sheet, row_index):
        self.sheet = sheet
        self.row_index = row_index
        self.index = self.row_index
        self._trouble = {}
        for column_index, name in enumerate(self.header):
            def f(ci=column_index):
                return self.cell_object(ci)

            if not hasattr(self, name):
                setattr(self, name, f)
            else:
                self._trouble[name] = f

    def ___getattr__(self, attr):
        # doesn't work
        if attr in self._trouble:
            return self._trouble[attr]
        else:
            #return super().__getattr__(attr)
            return getattr(self, attr)

    def __repr__(self):
        changed = ('+' if self in self.sheet._uncommitted_appends
                   else ('-' if self in self.sheet._uncommitted_deletes
                         else ('*' if [c for c in self.cells
                                       if c in self.sheet._uncommitted_updates] else ' ')))
        return f'<Row{changed} {self.range}>'

    def __hash__(self):
        return hash((self.__class__, self.sheet, self.row_index))

    def __eq__(self, other):
        """ cell equality is equality of location, not contents """
        s = self.sheet, self.row_index
        o = other.sheet, other.row_index
        return s == o

    @property
    def header(self):
        # FIXME normalized vs unnormalized
        try:
            if not self.sheet.values:
                return []
        except AttributeError as e:
            breakpoint()
            raise e

        return ['' if v == CELL_DID_NOT_EXIST else python_identifier(v)
                for v in self.sheet.values[0]
                # FIXME really bad semantics here
                if v != CELL_REMOVED]

    def __getitem__(self, column_index):
        return self.sheet.values[self.row_index][column_index]

    def cell_object(self, column_index):
        return Cell(self.sheet, self.row_index, column_index)

    @property
    def values(self):  # FIXME naming ?
        return self.sheet.values[self.row_index]

    @values.setter
    def values(self, values):
        """ NOTE if the maximum column index in the existing
            sheet is larger than the number of values provided
            any existing values beyond the end of the provided
            values WILL NOT BE CHANGED.
            row.values -> | a | b | c | d |
            row.values =  | e | f |
            row.values -> | e | f | c | d |
        """
        for column_index, v in enumerate(values):
            self.cell_object(column_index).value = v

    @property
    def cells(self):
        return [self.cell_object(column_index)
                for column_index, _ in enumerate(self.values)]

    @property
    def range(self):
        start = self.cell_object(0)
        end = self.cell_object(-1)
        return f'{self.sheet.sheet_name}!{start._range}:{end._range}'

    def rowFromIndex(self, index):
        return self.__class__(self.sheet, index)

    def rowFromOffset(self, offset):
        return self.rowFromIndex(self.row_index + offset)

    def rowAbove(self, negative_offset=1):
        return self.rowFromOffset(-negative_offset)

    def rowBelow(self, positive_offset=1):
        return self.rowFromOffset(positive_offset)

    def _obj_coord(self):
        return self.cell_object(0)._obj_coord()

    def _obj_range(self):
        first = self.cell_object(0)._obj_range()
        last = self.cell_object(-1)._obj_range()
        out = {k:v for k, v in first.items()}
        out['endRowIndex'] = last['endRowIndex']
        out['endColumnIndex'] = last['endColumnIndex']
        return out

    def _obj_row(self):
        return {'values': [cell._obj_value() for cell in self.cells]}

    def _obj_update(self):
        return {'updateCells': {
            'rows': [{'values': [cell._obj_value() for cell in self.cells]}],
            'fields': 'userEnteredValue',
            #'start': self._obj_coord(),  # only need one of start or range
            'range': self._obj_range(),}}


class Column:

    def __init__(self, sheet, column_index):
        self.sheet = sheet
        self.column_index = column_index
        self.index = self.column_index
        self._trouble = {}
        # XXX index cols can be out of sync if the 0th row is rewritten
        if self.sheet.index_columns:  # FIXME primary key for row ???
            for row_index, name in enumerate(self.header):
                def f(ri=row_index):
                    return self.cell_object(ri)

                if not hasattr(self, name):
                    setattr(self, name, f)
                else:
                    self._trouble[name] = f

    def ___getattr__(self, attr):
        # doesn't work
        if attr in self._trouble:
            return self._trouble[attr]
        else:
            #return super().__getattr__(attr)
            return getattr(self, attr)

    def __repr__(self):
        changed = ('+' if self in self.sheet._uncommitted_appends
                   else ('-' if self in self.sheet._uncommitted_deletes
                         else ('*' if [c for c in self.cells
                                       if c in self.sheet._uncommitted_updates] else ' ')))
        return f'<Column{changed} {self.range}>'

    def __hash__(self):
        return hash((self.__class__, self.sheet, self.column_index))

    def __eq__(self, other):
        """ cell equality is equality of location, not contents """
        s = self.sheet, self.column_index
        o = other.sheet, other.column_index
        return s == o

    @property
    def header(self):
        if self.sheet.index_columns:
            # FIXME multi column primary keys ??
            # FIXME normalization ??
            col = self.sheet.index_columns[0]
            try:
                row_header_column_index = getattr(self.sheet.row_object(0), col)().column_index
            except AttributeError as e:
                # the 0th row does not have a cell matching the index column
                # the index column is specified by the class and is not dynamic
                # the caller must handle this case explicitly because index
                # columns are not dynamic
                raise e

            # urg the perf
            return [r[row_header_column_index] for r in self.sheet.values]

    def __getitem__(self, row_index):
        return self.sheet.values[row_index][self.column_index]

    def cell_object(self, row_index):
        return Cell(self.sheet, row_index, self.column_index)

    @property
    def values(self):
        # TODO we can update this
        # and either way need it as a property to make operations
        # over rows and columns homogenous
        return [v[self.column_index] for v in self.sheet.values]

    @property
    def cells(self):
        return [self.cell_object(row_index)
                for row_index, _ in enumerate(self.sheet.values)]

    @property
    def range(self):
        start = self.cell_object(0)
        end = self.cell_object(-1)
        return f'{self.sheet.sheet_name}!{start._range}:{end._range}'

        minr = 1  # anticipating arbitrary column ranges
        maxr = len(self.sheet.values) + 1
        ci = self.column_index
        if ci < 0:
            ci = len(self.sheet.values[0]) + ci

        c = num_to_ab(ci + 1)
        return f'{self.sheet.sheet_name}!{c}{minr}:{c}{maxr}'

    def columnFromIndex(self, index):
        return self.__class__(self.sheet, index)

    def columnFromOffset(self, offset):
        return self.columnFromIndex(self.column_index + offset)

    def columnLeft(self, negative_offset=1):
        return self.columnFromOffset(-negative_offset)

    def columnRight(self, positive_offset=1):
        return self.columnFromOffset(positive_offset)

    def _obj_coord(self):
        return self.cell_object(0)._obj_coord()

    def _obj_range(self):
        first = self.cell_object(0)._obj_range()
        last = self.cell_object(-1)._obj_range()
        out = {k:v for k, v in first.items()}
        out['endRowIndex'] = last['endRowIndex']
        out['endColumnIndex'] = last['endColumnIndex']
        return out


class Sheet:
    """ access a single sheet as a basis for a workflow """

    name = None
    sheet_name = None
    fetch_grid = False
    index_columns = tuple()

    def __init__(self, name=None, sheet_name=None,
                 fetch=True, fetch_grid=None,
                 readonly=True, filter_cell=default_filter_cell):
        """ name to override in case the same pattern is used elsewhere """
        if name is not None:
            self.name = name
        if sheet_name is not None:
            self.sheet_name = sheet_name

        if fetch_grid is not None:
            self.fetch_grid = fetch_grid

        # TODO can probably unify these since can dispatch on Cell/Row
        self._uncommitted_updates = {}
        self._uncommitted_appends = {}
        self._uncommitted_extends = {}
        self._uncommitted_deletes = {}
        self._uncommitted_thunks = []
        self._incomplete_removes = {}  # different than deletes for now

        self.readonly = readonly
        self._setup()
        if fetch:
            self.fetch(filter_cell=filter_cell)

    @classmethod
    def fromUrl(cls, url):
        u = urlparse(url)
        _, ss, d, spreadsheet_id, edit = u.path.split('/')
        if ss != 'spreadsheets':
            raise ValueError(f'Not a spreadsheet? {url}')

        _, sheetId = u.fragment.split('=')
        sheetId = int(sheetId)
        _sheet_id = classmethod(lambda cls: spreadsheet_id)
        Temp = type('SomeSheet', (cls,), dict(_sheet_id=_sheet_id))
        temp = Temp(fetch=False)
        meta = temp.metadata()
        for s in meta['sheets']:
            if s['properties']['sheetId'] == sheetId:
                sheet_name = s['properties']['title']
                break

        return type('SomeSheet', (cls,), dict(_sheet_id=_sheet_id,
                                              sheet_name=sheet_name))

    @classmethod
    def _sheet_id(cls):
        return auth.user_config.secrets('google', 'sheets', cls.name)

    @classmethod
    def _uri_human(cls):
        # TODO sheet_name -> gid ??
        return f'https://docs.google.com/spreadsheets/d/{cls._sheet_id()}/edit'

    @classmethod
    def _open_uri(cls):
        import webbrowser
        webbrowser.open(cls._uri_human(uri))

    _saf = None  # SIGH
    def _setup(self):
        if not hasattr(Sheet, '_Sheet__drive_service_ro'):
            service = _get_oauth_service(
                api='drive', version='v3',
                SCOPES=['https://www.googleapis.com/auth/drive.metadata.readonly'],
                service_account_file=self._saf)
            Sheet.__drive_service_ro = service.files()

        self._drive_service = Sheet.__drive_service_ro

        if self.readonly:
            if not hasattr(Sheet, '_Sheet__spreadsheet_service_ro'):
                # I think it is correct to keep this ephimoral
                service = _get_oauth_service(
                    readonly=self.readonly,
                    service_account_file=self._saf)
                Sheet.__spreadsheet_service_ro = service.spreadsheets()

            self._spreadsheet_service = Sheet.__spreadsheet_service_ro

        else:
            if not hasattr(Sheet, '_Sheet__spreadsheet_service'):
                service = _get_oauth_service(
                    readonly=self.readonly,
                    service_account_file=self._saf)
                Sheet.__spreadsheet_service = service.spreadsheets()

            self._spreadsheet_service = Sheet.__spreadsheet_service

    def metadata(self):
        # TODO figure out the caching here
        resp = (self._spreadsheet_service  # FIXME annoying attribute error here when _only_cache = True
                .get(spreadsheetId=self._sheet_id())
                .execute())
        self._meta = resp
        # TODO use this to create generic subclasses
        # on the fly for each sheet?
        return self._meta

    def metadata_file(self):
        """ XXX WARNING drive api metadata updated asynchronously and
        may be delayed for multiple minutes """
        resp = (self._drive_service
                .get(fileId=self._sheet_id(),
                     supportsAllDrives=True,
                     fields='*')
                .execute())
        self._meta_file = resp
        return self._meta_file

    def _fetch_from_other_sheet(self, other):
        """ fix for rate limits when testing """
        self._meta = copy.deepcopy(other._meta)
        self._meta_file = copy.deepcopy(other._meta_file)
        self.raw_values = copy.deepcopy(other.raw_values)
        self._values = copy.deepcopy(other._values)
        if hasattr(other, 'byCol'):
            self.byCol = copy.deepcopy(other.byCol)
        self.grid = copy.deepcopy(other.grid)
        self.cells_index = copy.deepcopy(other.cells_index)

    #fetch_count = 0
    def fetch(self, fetch_grid=None, filter_cell=None, fetch_meta=True):
        """ update remote values (called automatically at __init__) """
        #self.__class__.fetch_count += 1
        #log.debug(f'fetch count: {self.__class__.fetch_count}')
        self._stash_uncommitted()
        if fetch_grid is None:
            fetch_grid = self.fetch_grid

        if fetch_meta:
            self.metadata()
            self.metadata_file()

        values, values_formula, grid, cells_index = get_sheet_values(
            self.name,
            self.sheet_name,
            spreadsheet_service=self._spreadsheet_service,
            fetch_grid=fetch_grid,
            filter_cell=filter_cell,
            SPREADSHEET_ID=self._sheet_id())

        self.raw_values = values
        self._values = [list(r) for r in
                        zip(*itertools.zip_longest(*self.raw_values,
                                                   fillvalue=''))]

        # FIXME XXX WARNING values_formula is NOT KEPT IN SYNC RIGHT NOW
        self.raw_values_formula = values_formula
        self._values_formula = [
            list(r) for r in
            zip(*itertools.zip_longest(*self.raw_values_formula,
                                       fillvalue=''))]
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

        self._reapply_uncommitted()

        if fetch_meta:
            return self._meta, self._meta_file, self.raw_values, self.raw_values_formula, grid
        else:
            return None, None, self.raw_values, self.raw_values_formula, grid

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, values):
        """ NOTE this will not delete/erase existing values beyond the ends
            of the provided values. Explicitly update a range for that or
            use self.update which will blank existing values. """
        for i, row_values in enumerate(values):
            try:
                self.row_object(i).values = row_values
            except IndexError:
                self._appendRow(row_values)

    def update(self, values):
        """ update all values at the same time """
        old_lv = len(self._values[0]) if self._values else 0
        lv = len(values)
        raw_values = [[''] * old_lv] + values
        update_values = [list(r) for r in
                         zip(*itertools.zip_longest(
                             *raw_values, fillvalue=CELL_REMOVED))][1:]

        lev = len(self._values)
        if lv < lev:
            nblank = lev - lv
            nc = len(update_values[0])  # FIXME values = [] ??
            update_values += [[CELL_REMOVED] * nc] * nblank

        self.values = update_values
        self._delete_rest()

    def sheetId(self):
        """ the tab aka sheetId not the _sheet_id aka spreadsheetId """
        # maximum confusion
        for s in self._meta['sheets']:
            props = s['properties']
            if props['title'] == self.sheet_name:
                return props['sheetId']

    def createRemoteSheet(self):
        if self.sheetId() is not None:
            raise TypeError(f'Sheet {self.sheet_name} already exists!')

        data = [{'addSheet':
                 {'properties':
                  {'title': self.sheet_name,
                   }}}]

        body = {'requests': data}
        resp = (self._spreadsheet_service
                .batchUpdate(spreadsheetId=self._sheet_id(), body=body)
                .execute())
        added = [reply['addSheet'] for reply in resp['replies'] if 'addSheet' in reply]
        self._meta['sheets'].extend(added)
        if not hasattr(self, '_values'):
            self.fetch()  # FIXME so many network calls

        return resp

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

    def rows(self):
        return [self.row_object(i) for i, _ in enumerate(self.values)]

    def columns(self):
        return [self.column_object(i) for i, _ in enumerate(self.values[0])]

    @property
    def cells(self):
        out = []
        for i, _ in enumerate(self.values):
            ro = self.row_object(i)
            out.append(ro.cells)

        return out

    def cell_object(self, row_index, column_index):
        return Cell(self, row_index, column_index)

    def row_object(self, row_index):
        return Row(self, row_index)

    def column_object(self, column_index):
        return Column(self, column_index)

    def _setCellValue(self, cell, value):
        """ call before making the change """
        if isinstance(value, Cell):
            raise TypeError(f'values should not be of type Cell: {value}')

        self._error_when_in_delete()

        try:
            if cell.value == value:
                #if value == CELL_REMOVED and cell not in self._incomplete_removes:
                    #breakpoint()
                    #self._incomplete_removes[cell] = value

                # there wasn't actually a change so we don't store it
                return

            if cell not in self._uncommitted_updates:
                _cv = cell.value
                if value == '' and _cv == None or value == None and _cv == '':
                    # don't push changes related to empty string vs None very bad
                    # for perf due to some lurking quadraticness
                    pass
                else:
                    self._uncommitted_updates[cell] = cell.value  # store the old values
        except IndexError:
            # there was no old value so not comparing and not storing
            # the cell will have to figure out how to remove values
            # that forced the extension of the rows I'm sure
            pass

        if value == CELL_REMOVED:
            self._incomplete_removes[cell] = value

        try:
            row_values = self.values[cell.row_index]
        except IndexError:
            raise  # IndexError is used to force append

        try:
            row_values[cell.column_index] = value
        except IndexError as e:
            self._appendColCell(cell, row_values, value, e)

    def _appendColCell(self, cell, row_values, value, e):
        lc = len(row_values)
        if cell.column_index > lc + 1:
            msg = (f'Column index {cell.column_index} > {lc} + 1 '
                    'current max index + 1')
            raise IndexError(msg) from e
        else:
            self._appendColBlank()
            if cell not in self._uncommitted_updates:
                # XXX somehow this is never called?
                self._uncommitted_updates[cell] = cell.value
            row_values[cell.column_index] = value

    def _appendColBlank(self):
        # FIXME TODO make sure that the bottom right corner of a double
        # append with a row and a column is flagged correctly

        # and here is the cost of a schema change over all rows ...
        for row in self.values:
            row.append(CELL_DID_NOT_EXIST)

        new_column = Column(self, len(row) - 1)
        self._uncommitted_appends[new_column] = new_column.values  # TODO handle this for rollback

        # FIXME not sure if this is the right way to handle getting the * to show up
        # but I think it is, this way we have a column of values that "does not exist"
        # that we can detect was added, rather than trying to account for which columns
        # were addeded or subtracted, and this avoids the risk of accidetnally pushing
        # the random object to the remote since None -> null -> discarded
        for cell in new_column.cells:
            cell.value = ''  # FIXME object -> string issue

    def _appendRow(self, row):
        # NOTE this intentionally does not go in the byCol index
        # it should be added after commit completes, but byCol is static
        # and we need to remove it as a dependency at some point ...
        self._error_when_in_delete()

        lrow = len(row)
        # FIXME ensure that lrow actually has max length
        ncols = len(self.values[0]) if self.values else lrow  # mostly safe
        if lrow < ncols:
            # ensure padding to avoid hard to debug index errors
            # and mutate in place so that anyone dealing with a
            # reference to the original row has the corrected version
            row.extend(['' for _ in range(ncols - lrow)])
        elif lrow > ncols:
            # XXX doing this here is safe for reapply uncommitted because
            # it just adds the rows again, so we get back to the same state
            n_new_cols = lrow - ncols
            for i in range(n_new_cols):
                self._appendColBlank()

        row_index = len(self.values)  # don't have to add 1 in this case
        if row in self.values:
            existing_index = self.values.index(row)
            msg = (
                f'A duplicate row (indexes {existing_index} {row_index}) '
                f'has been added to a sheet! {self}')
            log.warning(msg)

        self.values.append(row)
        row_object = Row(self, row_index)
        self._uncommitted_appends[row_object] = row

        if row and row[-1] == CELL_REMOVED:
            # we have to append cell removed and then remove it
            # otherwise the row.extend fill with '' will trigger it
            # may be possible to avoid that without having to add this
            # here, but for now we do the stupid and complete thing
            start = row.index(CELL_REMOVED)
            for i, value in enumerate(row[start:]):
                col_index = start + i
                cell = self.cell_object(row_index, col_index)
                self._incomplete_removes[cell] = value

    def _row_from_index(self, index_column=None, value=None, row=None, fail=False):
        """ REMINDER: this expects the passed row to have the same structure
            as the remote row """

        if index_column is None:
            index_column = self.index_columns[0]

        if (value is None and row is None or
            value is not None and row is not None):
            raise TypeError('one and only one of value or row is required')

        cell_index_header = getattr(self.row_object(0), index_column)()
        if row:
            index_value = row[cell_index_header.column_index]
        else:
            index_value = value

        row_object = getattr(cell_index_header.column, index_value)().row

        return row_object, index_value

    def insert(self, *rows):
        """ you know it """
        for row in rows:
            try:
                row_object, index_value = self._row_from_index(row=row)
                raise ValueError('Row with pkey {value!r} already exists!\n'
                                 'You should probably rollback your changes.')
            except AttributeError:
                self._appendRow(row)

    def _error_when_uncommitted(self):
        if self._uncommitted_appends or self._uncommitted_updates:
            raise ValueError('Sheet currently has uncommitted appends or updates.')

    def _error_when_in_delete(self):
        # managing deletes is not simple because the row index has to be
        # shifted based on the number of deletes, same issue for all
        # other operations as well ... SIGH, basically don't stack
        # deletes with anything else right now :/
        if self._uncommitted_deletes:
            raise ValueError('Sheet currently has uncommitted deletes.')

    def delete(self, *rows):
        """ get me outa here """
        if self.uncommitted():
            raise ValueError('Sheet has uncommitted changes, no deletes '
                             'may be added to this transaction.')

        row_objects = sorted([self._row_from_index(row=row)[0] for row in rows],
                             key=lambda ro: ro.row_index)

        # backwards so indexes don't shift under us
        for row_object in row_objects[::-1]:
            if row_object in self._uncommitted_deletes:
                raise ValueError('very bad things have happened here')

            self._uncommitted_deletes[row_object] = self.values.pop(row_object.row_index)

    def upsert(self, *rows):
        """ update or insert one or more rows
            WARNING: DO NOT USE THIS IF THE PRIMARY INDEX COLUMN IS NOT UNIQUE
            We do not currently have support for composite primary keys. """

        # FIXME this assumes that the column headers are the same
        for row in rows:
            try:
                row_object, index_value = self._row_from_index(row=row)
                row_object.values = row
            except AttributeError:
                self._appendRow(row)

    def rollback(self):
        """ remove all changes staged for commit to the local version """
        # TODO
        if not self.uncommitted():
            raise ValueError('There are no uncommitted changes to roll back!')

        raise NotImplementedError('TODO')
        # remove any explicit extensions
        self._uncommitted_extends = {}  # TODO also deletes
        # remove the new rows
        self._uncommitted_appends = {}
        # restore the previous rows
        self._uncommitted_updates = {}
        # restore the previous rows, note that all rows >= row_index += 1
        # have to use list.insert(row_object.row_index, )
        self._uncommitted_thunks = []

        [self.values.insert(row_object.row_index, previously_deleted_row)
         for row_object, previously_deleted_row in
         sorted(self._uncommitted_deletes.items(),
                # have to insert lowest first so that we don't try to insert
                # into a position in the list that doesn't exist since we
                # previously removed it
                key=lambda kv: kv[0].row_index)]
        self._uncommitted_deletes = {}

    def uncommitted(self):
        return {**self._uncommitted_appends,
                **self._uncommitted_updates,
                **self._uncommitted_deletes}

    def _delete_rest(self):
        """ add a thunk to delete rest, will run after all other
        operations and then in the order of any other arbitrary thunks
        that generate requests """
        # FIXME I'm sure there will be a case where we might want to
        # run some arbitrary request in some other sequence, but we'll
        # deal with that if it comes up
        self._make_thunk(self._delete_rest_impl)

    def _make_thunk(self, f):
        # FIXME are these call once so we should error if they are
        # requested more than once per commit?
        existing = [f for f, thunk in self._uncommitted_thunks]
        if f in existing:
            raise ValueError(f'{f} already registered to be called')

        try:
            raise Exception('original call site')
        except Exception as e:
            def call(__exception=e):
                try:
                    return f()
                except Exception as e:
                    raise e from __exception

            self._uncommitted_thunks.append((f, call))

    def _values_less_removed(self):
        return [new_row for row in self.values
                for new_row in ([value for value in row if value != CELL_REMOVED],)
                if new_row]

    def _delete_rest_impl(self):
        """ remove rows and columns beyond limits of current values
        we can't use self._uncommitted_deletes here because we can
        only delete rows and columns that are actually in values
        and we intentionally do not pull empty rows and empty columns
        so this has to go elsewhere
        """

        sid = self.sheetId()

        # have to do this so that complete removes only happens after
        # all other requests have succeeded and completed, including
        # the delete, because if the delete fails at the end we have
        # cannot call complete removes because it is destructive
        _values = self.values
        _lr = len(_values)
        _lc = len(_values[0])  # mostly safe
        # i, j will be the negative index of the bottom right non-removed cell
        for i, row in enumerate(_values[::-1]):
            if row[0] == CELL_REMOVED:
                continue

            for j, value in enumerate(row[::-1]):
                if value != CELL_REMOVED:
                    break

            if value != CELL_REMOVED:
                break

        lr = _lr - i
        lc = _lc - j

        if not hasattr(self, '_meta'):
            self.metadata()

        this_meta = [s for s in self._meta['sheets'] if s['properties']['sheetId'] == sid][0]
        gp = this_meta['properties']['gridProperties']
        nr = gp['rowCount']
        nc = gp['columnCount']
        requests = []
        if nr > lr:
            requests.append(
                {'deleteDimension': {
                    'range': {
                        'sheetId': sid,
                        'dimension': 'ROWS',
                        'startIndex': lr,
                    }}})

        if nc > lc:
            requests.append(
                {'deleteDimension': {
                    'range': {
                        'sheetId': sid,
                        'dimension': 'COLUMNS',
                        'startIndex': lc,
                    }}})

        yield from requests

    def _commit_thunks_requests(self):
        # FIXME deferred calling of thunks means that
        # debugging the traceback could be a nightmare
        for f, thunk in self._uncommitted_thunks:
            yield from thunk()

    def _commit_requests(self):
        # FIXME there is some lurking quadraticness in here e.g. when
        # trying to update ALL cells in a big sheet ~100k sheets
        yield from self._commit_appends_requests()
        yield from self._commit_updates_requests()
        yield from self._commit_deletes_requests()
        # XXX arbitrary requests come last and they are populated by
        # calling all _uncommitted_thunks in order and they are called
        # and emitted after all others because we need to be sure that
        # local and remote values are synchronized for aribtrary calls
        yield from self._commit_thunks_requests()

    #commit_count = 0
    def commit(self):
        #self.__class__.commit_count += 1
        #log.debug(f'commit count: {self.__class__.commit_count}')
        requests = list(self._commit_requests())
        if requests:
            body = {'requests': requests}
            resp = (self._spreadsheet_service
                    .batchUpdate(spreadsheetId=self._sheet_id(), body=body)
                    .execute())

            self._uncommitted_extends = {}
            self._uncommitted_appends = {}
            self._uncommitted_updates = {}
            self._uncommitted_deletes = {}
            self._uncommitted_thunks = []
            self._complete_removes()

    def _obj_coord_range(self, ordered):
        obj_coord = ordered[0]._obj_coord()
        first = ordered[0]._obj_range()
        last = ordered[-1]._obj_range()
        obj_range = {k:v for k, v in first.items()}
        obj_range['endRowIndex'] = last['endRowIndex']
        obj_range['endColumnIndex'] = last['endColumnIndex']
        return obj_coord, obj_range

    def _obj_update_rows(self, ordered_rows):
        obj_coord, obj_range = self._obj_coord_range(ordered_rows)
        return {
            'updateCells': {
                'rows': [row._obj_row() for row in ordered_rows],
                'fields': 'userEnteredValue',
                #'start': obj_coord,  # only need one of start or range
                'range': obj_range,}}

    def _obj_update_cols(self, ordered_cols):
        obj_coord, obj_range = self._obj_coord_range(ordered_cols)
        rows = [{'values': [cell._obj_value() for cell in row_frag]}
                for row_frag in zip(*[list(c.cells) for c in ordered_cols])]
        return {
            'updateCells': {
                'rows': rows,
                'fields': 'userEnteredValue',
                #'start': obj_coord,  # only need one of start or range
                'range': obj_range,}}

    def _commit_appends_requests(self):  # values
        requests = []
        extend_objects = []
        for oclass in (Row, Column):
            objects = sorted((o for o in self._uncommitted_appends
                              if isinstance(o, oclass)),
                             key=lambda o: o.index)
            if objects:
                extend_objects.extend(objects)
                if oclass is Row:
                    blob = self._obj_update_rows(objects)
                elif oclass is Column:
                    blob = self._obj_update_cols(objects)
                else:
                    raise Exception('wat')
                requests.append(blob)

        # sheet updates
        yield from self._commit_extends_requests(extend_objects)
        yield from requests

    def _commit_extends_requests(self, objects):  # sheet
        # FIXME we haven't had any test cases where extends have been
        # issued independent of data but as implemented this is
        # completely broken for that case
        if not self._uncommitted_extends and not objects:
            return

        # TODO columns ?

        if not objects:
            objects = sorted(self._uncommitted_extends, key=lambda o: o.index)

        # FIXME there are some seriously nasty concurrency issues lurking here

        sid = self.sheetId()
        # FIXME extending with a bunch of CELL_REMOVED
        requests = [
            {'insertDimension': {
                'inheritFromBefore': bool(self.raw_values),  # if raw_values is empty there is nothing to inherit
                'range': {
                    'sheetId': sid,
                    'dimension': 'ROWS' if isinstance(object, Row) else 'COLUMNS',
                    'startIndex': object.index,
                    'endIndex': object.index + 1,  # have to delete at least one whole row
                }}}
            for object in objects]

        yield from requests

    def _commit_updates_requests(self): # values
        # more overhead, but effectively the same as what we did before
        requests = [cell._obj_update() for cell in self._uncommitted_updates]
        yield from requests

    def _commit_deletes_requests(self):  # sheet
        if not self._uncommitted_deletes:
            return

        # TODO columns ?

        # delete from the bottom up to avoid changes in the indexing
        row_objects = sorted(self._uncommitted_deletes, key=lambda r: r.row_index)
        # can't use rmin and rmax because there might be gaps

        # FIXME there are some seriously nasty concurrency issues lurking here

        requests = [
            {'deleteDimension': {
                'range': {
                    'sheetId': self.sheetId(),
                    'dimension': 'ROWS' if isinstance(row_object, Row) else 'COLUMNS',
                    'startIndex': row_object.row_index,
                    'endIndex': row_object.row_index + 1,  # have to delete at least one whole row
                }}}
            for row_object in row_objects[::-1]]  # remove last first just in case

        yield from requests

    def _appendRange(self, objects):
        """ WARNING objects must be sorted, non-empty,
            and have values of uniform length """
        no = len(objects)
        _rmin = len(self.values) + no
        _rmax = 0
        _cmin = len(self.values[0]) + no
        _cmax = 0

        for o in (objects[0], objects[-1]):
            cells = o.cells
            for cell in (cells[0], cells[-1]):
                _rmin = cell.row_index if cell.row_index < _rmin else _rmin
                _rmax = cell.row_index if cell.row_index > _rmax else _rmax
                _cmin = cell.column_index if cell.column_index < _cmin else _cmin
                _cmax = cell.column_index if cell.column_index > _cmax else _cmax

        rmin = _rmin + 1
        rmax = _rmax + 1
        cmin = num_to_ab(_cmin + 1)
        cmax = num_to_ab(_cmax + 1)
        return f'{self.sheet_name}!{cmin}{rmin}:{cmax}{rmax}'

    def _complete_removes(self):
        for cell in sorted(
                self._incomplete_removes,
                # this runs backwards removing the most distant first
                key=lambda c: (-c.row_index, -c.column_index)):
            columns = self.values[cell.row_index]
            columns.pop(cell.column_index)
            if not columns:
                self.values.pop(cell.row_index)

        #if self._values_less_removed() != self.values:
            #breakpoint()
        self._incomplete_removes = {}

    def _stash_uncommitted(self):
        self._stash = {c:c.value for c in self._uncommitted_updates}
        # TODO do we revert here?

    def _reapply_uncommitted(self):
        """ if fetch is called, reapply our changes """

        # FIXME TODO detect changes in number of rows etc.
        # and/or use the index columns ...

        old_u = self._uncommitted_updates  # keep in case something goes wrong ?
        self._uncommitted_updates = {}  # reset this to capture the new starting values
        old_a = self._uncommitted_appends  # in the event someone else appended rows, don't klobber
        self._uncommitted_appends = {}
        ds = (old_a, self._stash)
        for d in ds:
            for k, v in d.items():
                if isinstance(k, Row):
                    # FIXME WARNING replay is not consistent if dict insertion is
                    # not preserved, e.g. in old versions of python
                    self._appendRow(v)
                elif isinstance(k, Cell):
                    self._setCellValue(k, v)
                else:
                    raise NotImplementedError('Unhandled type {type(k)}')

        self._stash = None

    @property
    def title(self):
        if not hasattr(self, '_metadata'):
            self.metadata()

        return self._meta['properties']['title'] + ' sheet ' + self.sheet_name

    def asPretty(self, limit=30):
        rows = [[c[:limit] + ' ...' if isinstance(c, str)
                 and len(c) > limit else c
                 for c in r] for r in self.values]
        table = AsciiTable(rows, title=self.title)
        return table.table
