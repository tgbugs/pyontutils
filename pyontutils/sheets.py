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
    res = ss.get(spreadsheetId=SPREADSHEET_ID, includeGridData=True).execute()
    # res['sheets'][1]['data'][0]['rowData'][0]  # lota data but no comments yet ...
    #embed()
    result = ss.values().get(spreadsheetId=SPREADSHEET_ID, range=sheet_name).execute()
    values = result.get('values', [])
    return values

def main():
    values = get_sheet_values('neurons-cut', 'CUT V1.0')
    embed()

if __name__ == '__main__':
    main()
