#!/usr/bin/env python3.6
from pathlib import Path
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from pyontutils.config import devconfig
from IPython import embed
from interlex.utils import printD


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


def process_note(raw_note):
    bits = [b.strip() for b in raw_note.split('\n') if b.strip()]
    return raw_note


def get_note(row_index, column_index, notes_index):
    try:
        return process_note(notes_index[row_index, column_index])
    except KeyError:
        return None


def select_by_curie_rank(results):
    ranking = 'CHEBI', 'UBERON', 'PR', 'NCBIGene', 'NCBITaxon', 'GO', 'SAO', 'NLXMOL'
    def key(result):
        if 'curie' in result:
            curie = result['curie']
        else:
            return len(results) * 3
            
        prefix, _ = curie.split(':')
        if prefix in ranking:
            try:
                return ranking.index(result['curie'])
            except ValueError:
                return len(results) + 1
        else:
            return len(results) * 2

    return sorted(results, key=key)[0]


def sheet_to_neurons(values, notes_index):
    # TODO import existing ids to register by label
    from pyontutils.core import OntId
    from pyontutils.neurons import NeuronCUT, Config, Phenotype
    from pyontutils.namespaces import ilxtr
    from pyontutils.closed_namespaces import rdfs
    from pyontutils.scigraph import Vocabulary
    sgv = Vocabulary()
    e_config = Config('common-usage-types')
    e_config.load_existing()
    existing = {str(n.label):n for n in e_config.neurons}
    def convert_header(header):
        if header.startswith('has'):  # FIXME use a closed namespace
            return ilxtr[header]
        else:
            return None

    def convert_cell(cell_or_comma_sep):
        #printD('CONVERTING', cell_or_comma_sep)
        for cell_w_junk in cell_or_comma_sep.split(','):  # XXX WARNING need a way to alter people to this
            cell = cell_w_junk.strip()
            result = [r for r in sgv.findByTerm(cell, searchSynonyms=False)
                    if not r['deprecated']]
            #printD(cell, result)
            if not result:
                yield None, cell_or_comma_sep  # FIXME need a way to handle this that doesn't break things?
                continue
            elif len(result) > 1:
                #printD('WARNING', result)
                result = select_by_curie_rank(result)
            else:
                result = result[0]

            yield result['iri'], result['labels'][0]

    config = Config('cut-roundtrip')
    skip = 'alignment label',
    headers, *rows = values
    errors = []
    new = []
    for i, neuron_row in enumerate(rows):
        id = None
        label_neuron  = None
        current_neuron = None
        phenotypes = []
        for j, (header, cell) in enumerate(zip(headers, neuron_row)):
            if header == 'curie':
                id = OntId(cell).u if cell else None
                continue
            elif header == 'label':
                label_neuron = cell
                if cell in existing:
                    current_neuron = existing[cell]
                elif cell:
                    # TODO
                    new.append(cell)
                else:
                    raise ValueError(cell)  # wat
                continue
            elif header == 'Status':
                # TODO
                continue
            elif header == 'PMID':
                # TODO
                continue
            elif header == 'Other reference':
                # TODO
                continue
            elif header == 'Other label':
                # TODO
                continue
            elif header == 'Description':
                # TODO
                continue
            elif header == 'synonyms':
                # TODO
                continue
            elif header in skip:
                continue

            note = get_note(i, j, notes_index)
            objects = []
            if cell:
                printD(header, cell, note)
                predicate = convert_header(header)
                for object, label in convert_cell(cell):
                    if label != cell:
                        errors.append((cell, label))
                    else:
                        objects.append(object)
            else:
                continue

            if predicate and objects:
                for object in objects:  # FIXME has layer location phenotype
                    if object:
                        phenotypes.append(Phenotype(object, predicate))
                    else:
                        errors.append((object, predicate, cell))
            elif objects:
                errors.append((header, objects))
            else:
                errors.append((header, cell))
            # translate header -> predicate
            # translate cell value to ontology id

        if current_neuron and phenotypes:
            # TODO merge current with changes
            # or maybe we just replace since all the phenotypes should be there?
            printD(phenotypes)
            if id is not None:
                printD(id, bool(id))
            NeuronCUT(*phenotypes, id_=id, label=label_neuron, override=bool(id) or bool(label))
            # FIXME occasionally this will error?!
        else:
            errors.append((i, neuron_row))

    return config, errors, new


def main():
    values, notes_index = get_sheet_values('neurons-cut', 'CUT V1.0', get_notes=False)
    #show_notes(values, notes_index)
    config, errors, new = sheet_to_neurons(values, notes_index)
    config.write()
    embed()

if __name__ == '__main__':
    main()
