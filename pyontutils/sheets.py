#!/usr/bin/env python3.6
import itertools
from pathlib import Path
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from pyontutils.utils import byCol
from pyontutils.config import devconfig

spath = Path(devconfig.secrets_file).parent


def get_oauth_service(readonly=True):
    if readonly:
        store_file = 'google-api-token.json'
        SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
    else:
        store_file = 'google-api-token-rw.json'
        SCOPES = 'https://www.googleapis.com/auth/spreadsheets'

    store = file.Storage((spath / store_file).as_posix())
    creds = store.get()
    if not creds or creds.invalid:
        # the first time you run this you will need to use the --noauth_local_webserver args
        creds_file = devconfig.secrets('google', 'api', 'creds-file')
        flow = client.flow_from_clientsecrets((spath / creds_file).as_posix(), SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('sheets', 'v4', http=creds.authorize(Http()))
    return service


def update_sheet_values(spreadsheet_name, sheet_name, values, spreadsheet_service=None):
    SPREADSHEET_ID = devconfig.secrets(spreadsheet_name)
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


def get_sheet_values(spreadsheet_name, sheet_name, get_notes=True, spreadsheet_service=None):
    SPREADSHEET_ID = devconfig.secrets('google', 'sheets', spreadsheet_name)
    if spreadsheet_service is None:
        service = get_oauth_service()
        ss = service.spreadsheets()
    else:
        ss = spreadsheet_service
    if get_notes:
        grid = ss.get(spreadsheetId=SPREADSHEET_ID, includeGridData=True).execute()
        notes = get_notes_from_grid(grid, sheet_name)
        notes_index = {(i, j):v for i, j, v in notes}
    else:
        notes_index = {}

    result = ss.values().get(spreadsheetId=SPREADSHEET_ID, range=sheet_name).execute()
    values = result.get('values', [])
    return values, notes_index


def get_notes_from_grid(grid, title):
    for sheet in grid['sheets']:
        if sheet['properties']['title'] == title:
            for datum in sheet['data']:
                for i, row in enumerate(datum['rowData']):
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
    index_columns = tuple()

    def __init__(self, name=None, sheet_name=None, fetch_notes=False, readonly=True):
        """ name to override in case the same pattern is used elsewhere """
        if name is not None:
            self.name = name
        if sheet_name is not None:
            self.sheet_name = sheet_name

        self.fetch_notes = fetch_notes

        self.readonly = readonly
        self._setup()
        self.fetch()

    def _setup(self):
        if self.readonly:
            if not hasattr(Sheet, '__spreadsheet_service_ro'):
                service = get_oauth_service(self.readonly)  # I think it is correct to keep this ephimoral
                Sheet.__spreadsheet_service_ro = service.spreadsheets()

            self._spreadsheet_service = Sheet.__spreadsheet_service_ro

        else:
            if not hasattr(Sheet, '__spreadsheet_service'):
                service = get_oauth_service(self.readonly)
                Sheet.__spreadsheet_service = service.spreadsheets()

            self._spreadsheet_service = Sheet.__spreadsheet_service

    def fetch(self, fetch_notes=None):
        """ update remote values (called automatically at __init__) """
        if fetch_notes is None:
            fetch_notes = self.fetch_notes
        values, notes_index = get_sheet_values(self.name, self.sheet_name,
                                               spreadsheet_service=self._spreadsheet_service,
                                               get_notes=fetch_notes)
        self.raw_values = values
        self.values = [list(r) for r in zip(*itertools.zip_longest(*self.raw_values, fillvalue=''))]
        self.byCol = byCol(self.values, to_index=self.index_columns)
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
    """ setup oauth """
    service = get_oauth_service()
    print('sheets main ok')

if __name__ == '__main__':
    main()
