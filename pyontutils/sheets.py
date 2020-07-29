import pickle
import itertools
from pathlib import Path
from urllib.parse import urlparse
import idlib
import htmlfn as hfn
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pyontutils.utils import byCol, log as _log
from pyontutils.config import auth
from pyontutils.clifun import python_identifier

# TODO decouple oauth group sheets library

log = _log.getChild('sheets')

CELL_DID_NOT_EXIST = type('CellDidNotExist', (object,), {})()
CELL_REMOVED = type('CellRemoved', (object,), {})()  # FIXME this is ... bad? or is IndexError worse?


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
        _p = 'RUNTIME_CONFIG' if auth._path is None else auth._path
        # FIXME bad error message, need to check whether the key is even in
        # the user config, and yes we need our way to update the user config
        # and warn about unexpected formats for orthauth configs
        msg = (f'No file exists at the path specified by {_auth_var} in {_p}')
        log.debug(auth._runtime_config)
        log.debug(auth.user_config._runtime_config)
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


def update_sheet_values(spreadsheet_name, sheet_name, values, spreadsheet_service=None, SPREADSHEET_ID=None):
    if SPREADSHEET_ID is None:
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


def num_to_ab(n):
    string = ''
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


def get_sheet_values(spreadsheet_name, sheet_name, fetch_grid=False, spreadsheet_service=None,
                     filter_cell=default_filter_cell, SPREADSHEET_ID=None):
    if SPREADSHEET_ID is None:
        SPREADSHEET_ID = auth.dynamic_config.secrets('google', 'sheets', spreadsheet_name)

    if spreadsheet_service is None:
        service = get_oauth_service()
        ss = service.spreadsheets()
    else:
        ss = spreadsheet_service

    result = ss.values().get(spreadsheetId=SPREADSHEET_ID, range=sheet_name).execute()
    values = result.get('values', [])

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
    def grid(self):
        return self.sheet.get_cell(self.row_index, self.column_index)

    @property
    def hyperlink(self):
        return self.grid.get('hyperlink', None)

    @property
    def atag(self):
        return hfn.atag(self.hyperlink, self.value)

    def asTerm(self):
        # TODO as identifier ?
        return idlib.from_oq.OntTerm(iri=self.hyperlink, label=self.value)

    @property
    def _range(self):
        ci = self.column_index
        if ci < 0:
            ci = len(self.sheet.values[0]) + ci

        c = num_to_ab(ci + 1)

        ri = self.row_index
        if ri < 0:
            ri = len(self.sheet.values) + ri

        r = ri + 1
        return f'{c}{r}'

    @property
    def range(self):
        return f'{self.sheet.sheet_name}!{self._range}'


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

        return [python_identifier(v)
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


class Column:

    def __init__(self, sheet, column_index):
        self.sheet = sheet
        self.column_index = column_index
        self.index = self.column_index
        self._trouble = {}
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
            row_header_column_index = self.sheet.byCol.header.index(col)
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
        self._uncommitted_deletes = {}
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
        return auth.dynamic_config.secrets('google', 'sheets', cls.name)

    @classmethod
    def _uri_human(cls):
        # TODO sheet_name -> gid ??
        return f'https://docs.google.com/spreadsheets/d/{cls._sheet_id()}/edit'

    @classmethod
    def _open_uri(cls):
        import webbrowser
        webbrowser.open(cls._uri_human(uri))

    def _setup(self):
        if self.readonly:
            if not hasattr(Sheet, '_Sheet__spreadsheet_service_ro'):
                # I think it is correct to keep this ephimoral
                service = get_oauth_service(readonly=self.readonly)
                Sheet.__spreadsheet_service_ro = service.spreadsheets()

            self._spreadsheet_service = Sheet.__spreadsheet_service_ro

        else:
            if not hasattr(Sheet, '_Sheet__spreadsheet_service'):
                service = get_oauth_service(readonly=self.readonly)
                Sheet.__spreadsheet_service = service.spreadsheets()

            self._spreadsheet_service = Sheet.__spreadsheet_service

    def metadata(self):
        # TODO figure out the caching here
        resp = (self._spreadsheet_service
                .get(spreadsheetId=self._sheet_id())
                .execute())
        self._meta = resp
        # TODO use this to create generic subclasses
        # on the fly for each sheet?
        return self._meta

    def fetch(self, fetch_grid=None, filter_cell=None):
        """ update remote values (called automatically at __init__) """
        self._stash_uncommitted()
        if fetch_grid is None:
            fetch_grid = self.fetch_grid

        self.metadata()

        values, grid, cells_index = get_sheet_values(
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

    def _update_old(self, values):
        """ update all values at the same time """
        if self.readonly:
            raise PermissionError('sheet was loaded readonly, '
                                  'if you want to write '
                                  'reinit with readonly=False')

        # FIXME this needs to updated the values attached to _THIS_ sheet
        # as well
        # FIXME also this bypasses the commit mechanism
        update_sheet_values(self.name,
                            self.sheet_name,
                            values,
                            spreadsheet_service=self._spreadsheet_service,
                            SPREADSHEET_ID=self._sheet_id())

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

        if cell not in self._uncommitted_updates:
            try:
                self._uncommitted_updates[cell] = cell.value  # store the old values
            except IndexError:
                # there was no old value so not storing the cell
                # will have to figure out how to remove values
                # that forced the extension of the rows I'm sure
                pass

        if value == CELL_REMOVED:
            self._incomplete_removes[cell] = value

        try:
            row_values = self.values[cell.row_index]
        except IndexError:
            raise  # this is needed to force over to append

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
        if row not in self.values:
            self.values.append(row)
            row_object = Row(self, self.values.index(row))
            self._uncommitted_appends[row_object] = row
        else:
            # FIXME should we allow identical duplicate rows?
            # or do we require another mechanism for that?
            raise ValueError('row already in sheet')

    def _row_from_index(self, index_column=None, value=None, row=None,
                        fail=False):
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

    def _error_when_uncommited(self):
        if self._uncommitted_appends or self._uncommitted_updates:
            raise ValueError('Sheet currently has uncommited appends or updates.')

    def _error_when_in_delete(self):
        # managing deletes is not simple because the row index has to be
        # shifted based on the number of deletes, same issue for all
        # other operations as well ... SIGH, basically don't stack
        # deletes with anything else right now :/
        if self._uncommitted_deletes:
            raise ValueError('Sheet currently has uncommited deletes.')

    def delete(self, *rows):
        """ get me outa here """
        if self.uncommitted():
            raise ValueError('Sheet has uncommited changes, no deletes '
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
        # remove the new rows
        self._uncommitted_appends = {}
        # restore the previous rows
        self._uncommitted_updates = {}
        # restore the previous rows, note that all rows >= row_index += 1
        # have to use list.insert(row_object.row_index, )

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

    def commit(self):
        # FIXME need clear documentation about the order in which these things execute
        self._commit_appends()  # has to go first in cases where an added row is later updated
        self._commit_updates()

        # deletes go last so that they don't rearrange the sheet and shift
        # cell definitions for everything else
        self._commit_deletes()

        # implementaiton note:
        # deletes are cases where we explicitly delete rows on our end
        # removes are used during an update where where are not explicit
        # deletes, therefore have to clean up the local blook keeping of
        # the removed cells after the commit finishes
        # NOTE: this means that checking len of the values lists during
        # during a call to update may return an incorrect value not entirely
        # sure how to test for that, fix involves checking _incomplete_removes
        self._complete_removes()  # FIXME could rewrite these as deletes?


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

    def _commit_appends(self):

        def sigh(vs):  # FIXME
            return ['' if v == CELL_REMOVED else v for v in vs]

        if not self._uncommitted_appends:
            return

        data = []
        for oclass in (Row, Column):
            objects = sorted((o for o in self._uncommitted_appends
                              if isinstance(o, oclass)),
                             key=lambda o: o.index)
            if objects:
                blob = dict(
                    range = self._appendRange(objects),
                    values = [sigh(o.values) for o in objects],  # FIXME object -> string issue
                    majorDimension = oclass.__name__.capitalize() + 'S',
                )
                data.append(blob)
                # FIXME overlapping cells are added twice

        body = {'valueInputOption': 'USER_ENTERED',
                'data': data,}

        resp = (self._spreadsheet_service.values()
                .batchUpdate(spreadsheetId=self._sheet_id(), body=body)
                .execute())

        self._uncommitted_appends = {}

    def _commit_updates(self):
        data = [{'range': cell.range, 'values': [[cell._value_str]]}
                for cell in self._uncommitted_updates]
        body = {'valueInputOption': 'USER_ENTERED',
                'data': data,}
        resp = (self._spreadsheet_service.values()
                .batchUpdate(spreadsheetId=self._sheet_id(), body=body)
                .execute())

        self._uncommitted_updates = {}

    def _commit_deletes(self):
        if not self._uncommitted_deletes:
            return

        # TODO columns ?

        # delete from the bottom up to avoid changes in the indexing
        row_objects = sorted(self._uncommitted_deletes, key= lambda r: r.row_index)
        # can't use rmin and rmax because there might be gaps

        # FIXME there are some seriously nasty concurrency issues lurking here

        data = [
            {'deleteDimension': {
                'range': {
                    'sheetId': self.sheetId(),
                    'dimension': 'ROWS' if isinstance(row_object, Row) else 'COLUMNS',
                    'startIndex': row_object.row_index,
                    'endIndex': row_object.row_index + 1,  # have to delete at least one whole row
                }}}
            for row_object in row_objects[::-1]]  # remove last first just in case
        body = {'requests': data}
        resp = (self._spreadsheet_service
                .batchUpdate(spreadsheetId=self._sheet_id(), body=body)
                .execute())

        self._uncommitted_deletes = {}

    def _complete_removes(self):
        for cell in sorted(self._incomplete_removes,
                           # this runs backwards removing the most distant first
                           key=lambda c: (-c.row_index, -c.column_index)):
            columns = self.values[cell.row_index]
            columns.pop(cell.column_index)
            if not columns:
                self.values.pop(cell.row_index)

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
