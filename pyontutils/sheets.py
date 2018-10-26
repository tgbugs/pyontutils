#!/usr/bin/env python3.6
from pathlib import Path
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from pyontutils.config import devconfig
from IPython import embed

# the first time you run this you will need to use the --noauth_local_webserver args

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'

spath = Path(devconfig.secrets_file).parent


def get_oauth_service():
    store = file.Storage((spath /'google-api-token.json').as_posix())
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets((spath / 'google-api-creds.json').as_posix(), SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('sheets', 'v4', http=creds.authorize(Http()))
    return service


def get_sheet_values(spreadsheet_name, sheet_name):
    SPREADSHEET_ID = devconfig.secrets(spreadsheet_name)
    service = get_oauth_service()
    ss = service.spreadsheets()
    grid = ss.get(spreadsheetId=SPREADSHEET_ID, includeGridData=True).execute()
    notes = get_notes_from_grid(grid, sheet_name)
    result = ss.values().get(spreadsheetId=SPREADSHEET_ID, range=sheet_name).execute()
    values = result.get('values', [])
    return values, notes


def get_notes_from_grid(grid, title):
    for sheet in grid['sheets']:
        if sheet['properties']['title'] == title:
            for datum in sheet['data']:
                for i, row in enumerate(datum['rowData']):
                    for j, column in enumerate(row['values']):
                        if 'note' in column:
                            yield i, j, column['note']


def main():
    values, notes = get_sheet_values('neurons-cut', 'CUT V1.0')
    embed()

if __name__ == '__main__':
    main()
