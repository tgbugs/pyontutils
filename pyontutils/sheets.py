#!/usr/bin/env python3.6
from pathlib import Path
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
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


def update_sheet_values(spreadsheet_name, sheet_name, values):
    SPREADSHEET_ID = devconfig.secrets(spreadsheet_name)
    service = get_oauth_service(readonly=False)
    ss = service.spreadsheets()
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


def get_sheet_values(spreadsheet_name, sheet_name, get_notes=True):
    SPREADSHEET_ID = devconfig.secrets(spreadsheet_name)
    service = get_oauth_service()
    ss = service.spreadsheets()
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


def show_notes(values, notes_index):
    for i, row in enumerate(values):
        for j, cell in enumerate(row):
            if (i, j) in notes_index:
                print(f'========================== {i} {j}',
                      cell,
                      '------------------',
                      notes_index[i, j],
                      sep='\n')


def get_note(row_index, column_index, notes_index):
    try:
        return notes_index[row_index, column_index]
    except KeyError:
        return None
