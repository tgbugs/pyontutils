from collections import defaultdict
from itertools import zip_longest
from pathlib import Path
from pyontutils.config import devconfig
from pyontutils.sheets import Sheet
from pyontutils.core import makeGraph, qname, OntId, OntTerm
from htmlfn import htmldoc, titletag, atag, ptag, nbsp
from typing import Union, Dict, List
from IPython import embed
from sys import exit
VERSION = '0.0.1'


class SheetPlus(Sheet):
    ''' Appending to Sheet functionality '''

    def get_html_rows(self, dict_={}):
        if not dict_:
            dict_ = self.graph
        rows = [
            [(8 * nbsp * tier_level) + label + (nbsp * 8)] # + curies
            for label, curies, tier_level  in self.linearize_graph(dict_)
        ]
        return rows

    def get_rows(self, dict_={}):
        if not dict_:
            dict_ = self.graph
        rows = []
        for label, curies, tier_level in self.linearize_graph(dict_):
            if curies:
                rows.append((4 * ' ' * tier_level) + label + '\t' + '\t'.join(curies))
            else:
                rows.append((4 * ' ' * tier_level) + label)
        return rows

    def fix_curie(self, curie):
        if not curie:
            return curie
        curie = curie.strip().upper()
        return curie

    def linearize_graph(self, dict_: dict, tier_level: int = 0) -> tuple:
        """ Recursively pull nested dictionaries out of print order"""
        for key, value in sorted(dict_.items()):
            label, curie = self.curie_splitter(key) # self.normt(key)
            if curie:
                curies = [self.fix_curie(curie)]
            else:
                if label:
                    curies = self.query_scigraph_for_curies(label)
                else:
                    continue
            yield (label, curies, tier_level)
            if isinstance(value, dict):
                yield from self.linearize_graph(value, tier_level + 1)

    def curie_splitter(self, string):
        ''' Splites string at curie. Only works if curie is at the end '''
        stop_chars = [',', ';', ':', '-'] # curators puts these chars b/w label and curie
        label_prefix = None # label + curie without id
        id_ = None # curie id
        label = '' # final label
        prefix = '' # final prefix

        if not string:
            return string, str()

        # if it's not possible for the string to be a curie - return
        if ':' not in string:
            return string, str()
        else:
            label_prefix, id_ = string.rsplit(':', 1)
            # see if id even is an id
            try:
                int(id_)
            except:
                return string, str()

        for i, char in enumerate(label_prefix[::-1]):
            if char in stop_chars:
                i += 1
                label = label_prefix[:len(label_prefix) - i]
                break
            else:
                prefix = char + prefix

        # sanity checks
        if not label:
            raise TypeError(f'label == {label}. Should be str.')
        if not prefix:
            raise TypeError(f'prefix == {prefix}. Should be str.')
        if not id_:
            raise TypeError(f'id_ == {id_}. Should be str.')

        label = label.strip()
        curie = (prefix + ':' + id_).strip()
        return label, curie

    def normalize_term(self, term, prefix=''):
        # TODO: this wont work, need to do multiple rsplit()s
        # common splits are: ",", ":", " - "
        term, *curie = term.split('\u1F4A9')
        if curie:
            curie, = curie
            oid = OntId(curie)
            curie = atag(oid.iri, oid.curie)
            row = [prefix + term, curie]
        else:
            curies = self.get_atag_from_scigraph_label_query(term)
            row = [prefix + term] + curies
        return row

    def get_atag_from_scigraph_label_query(self, label: str, prefixes:List[str] = ['UBERON', 'ILX', 'MBA', 'PAXRAT', 'BERCAT']) -> atag:
        atags = []
        for prefix in prefixes:
            # TODO: if not stipped the label will return nothing. Seems to be trailing spaces
            neighbors = [v.OntTerm for v in OntTerm.query(label=label.strip(), prefix=prefix)]
            if not neighbors:
                continue
            for neighbor in neighbors:
                oid = OntId(neighbor)
                atags += [atag(oid.iri, oid.curie)]
        atags = list(set(atags))
        return atags

    def query_scigraph_for_curies(self, label: str, prefixes:List[str] = ['UBERON', 'ILX']) -> list:
        curies = []
        for prefix in prefixes:
            # TODO: if not stipped the label will return nothing. Seems to be trailing spaces
            neighbors = [v.OntTerm for v in OntTerm.query(label=label.strip(), prefix=prefix)]
            if not neighbors:
                continue
            for neighbor in neighbors:
                oid = OntId(neighbor)
                curies.append(oid.curie)
        return curies

    def clean(self, string):
        if not string:
            return string
        return string.strip().title()

    def populate_location_grid(self):
        for y, row in enumerate(self.raw_values):
            for x, value in enumerate(row):
                self.location_grid[self.name][self.sheet_name][(x, y)] = self.clean(value)

    def get_sub_column(self, start_index, column, end_index=None):
        return {self.clean(row[column]):None for row in self.values[start_index:end_index] if row[column]}

    def get_sub_header_indexes(self, start_index, column):
        ''' Parse for bold text and returns its coordinates '''
        for sheet in self.grid['sheets']:
            if sheet['properties']['title'] == self.sheet_name:
                for datum in sheet['data']:
                    for i, row in enumerate(datum['rowData'][start_index:]):
                        if 'values' in row:
                            try:
                                cell = row['values'][column]
                            except:
                                continue
                            if 'effectiveFormat' in cell:
                                if 'textFormat' in cell['effectiveFormat']:
                                    if cell['effectiveFormat']['textFormat'].get('bold'):
                                        if 'userEnteredValue' in cell:
                                            if cell['userEnteredValue'].get('stringValue'):
                                                yield i


class UberonTermsSheet1Schema(SheetPlus):

    def build(self):
        # BUG: this is the wrong name and hasnt changed yet -_-
        self.values[2][4] = 'General spinal cord anatomy'
        rec_dd = lambda: defaultdict(rec_dd)
        self.graph = rec_dd()
        self.location_grid = rec_dd()
        self.populate_location_grid()
        self.populate_graph()

    def populate_graph(self):
        ''' Uberon has trailing empty cells in the sheet assuming its the value of the most recent
            left cell with a value '''

        # Get Header & Sub-Header Indexes
        for index, term in enumerate(self.raw_values):
            if term:
                terms_index = index
                sub_terms_index = index + 1
                break

        # Build graph
        for column, term in enumerate(self.raw_values[terms_index]):
            term = self.clean(term)
            sub_term = self.clean(self.values[sub_terms_index][column])
            # iterative terms could be blank
            if term:
                last_term = term

            if sub_term:
                terms_list = self.get_sub_column(
                    start_index = sub_terms_index + 1,
                    column = column,
                )
                self.graph[self.name][self.sheet_name][last_term][sub_term] = terms_list
            elif term:
                terms_list = self.get_sub_column(
                    start_index = terms_index + 1,
                    column = column,
                )
                self.graph[self.name][self.sheet_name][term] = terms_list


class SpinalTerminalogySheet1Schema(SheetPlus):

    def build(self):
        # BUG: They haven't named it in the table yet so it is left blank.
        self.raw_values[0][0] = 'Internal Anatomy'
        self.values[0][0] = 'Internal Anatomy'

        rec_dd = lambda: defaultdict(rec_dd)
        self.graph = rec_dd()
        self.location_grid = rec_dd()
        self.populate_location_grid()
        self.populate_graph()

    def populate_graph(self):
        ''' Will have to use grid to find headers and nest headers if anywhere in the column.
            The values that aren't headers will be trailing '''

        # Get Header Index
        for index, header in enumerate(self.raw_values):
            if header:
                headers_index = index
                break

        # Find Sub-Headers and fill in graph accordingly
        for column, header in enumerate(self.raw_values[headers_index]):
            header = self.clean(header)
            sub_header_indexes = list(self.get_sub_header_indexes(
                start_index = headers_index + 1,
                column = column
            ))
            if not sub_header_indexes:
                terms_list = self.get_sub_column(
                    start_index = headers_index + 1,
                    column = column,
                )
                self.graph[self.name][self.sheet_name][header] = terms_list
            else:
                for index, row in enumerate(self.values[headers_index + 1:]):
                    sub_header = row[column]
                    sub_header = self.clean(sub_header)
                    if not sub_header:
                        continue
                    try:
                        sub_header_index = sub_header_indexes[sub_header_indexes.index(index)]
                    except:
                        continue
                    if sub_header_index:
                        try:
                            end_index = sub_header_indexes[sub_header_indexes.index(index) + 1] - 1
                        except:
                            end_index = None
                        sub_terms_list = self.get_sub_column(
                            start_index = sub_header_index + 1,
                            end_index =  end_index,
                            column = column,
                        )
                        self.graph[self.name][self.sheet_name][header][sub_header] = sub_terms_list


class ParcellationUberonSchema(SheetPlus):

    def build(self):
        rec_dd = lambda: defaultdict(rec_dd)
        self.graph = rec_dd()
        self.location_grid = rec_dd()
        self.populate_location_grid()
        self.populate_graph()

    def populate_graph(self):
        ### NOT HEADER
        self.graph[self.name][self.sheet_name]['UBERON'] = self.get_sub_column(start_index=2, column=0)


class ParcellationAllenSchema(SheetPlus):

    def build(self):
        rec_dd = lambda: defaultdict(rec_dd)
        self.graph = rec_dd()
        self.location_grid = rec_dd()
        self.populate_location_grid()
        self.populate_graph()

    def populate_graph(self):
        ### NOT HEADER
        self.graph[self.name][self.sheet_name]['Allen Mouse Brainstem'] = self.get_sub_column(0, 0)


class ParcellationPaxinosSchema(SheetPlus):

    def build(self):
        rec_dd = lambda: defaultdict(rec_dd)
        self.graph = rec_dd()
        self.location_grid = rec_dd()
        self.populate_location_grid()
        self.populate_graph()

    def populate_graph(self):
        term_dict = {}
        for row in self.values[1:]:
            row = [cell for cell in row if cell]
            lable_curie = '-'.join(row)
            term_dict[lable_curie] = None
        self.graph[self.name][self.sheet_name]['Paxinos Rat Brainstem'] = term_dict


class ParcellationBermanSchema(SheetPlus):

    def build(self):
        rec_dd = lambda: defaultdict(rec_dd)
        self.graph = rec_dd()
        self.location_grid = rec_dd()
        self.populate_location_grid()
        self.populate_graph()

    def populate_graph(self):
        ### NOT HEADER
        self.graph[self.name][self.sheet_name]['Berman Cat Brainstem'] = self.get_sub_column(0, 0)


class ParcellationNieuwenhuysSchema(SheetPlus):

    def build(self):
        rec_dd = lambda: defaultdict(rec_dd)
        self.graph = rec_dd()
        self.location_grid = rec_dd()
        self.populate_location_grid()
        self.populate_graph()

    def populate_graph(self):
        term_dict = {}
        for row in self.values[:]:
            row = [cell for cell in row if cell]
            lable_curie = ' - '.join(row)
            term_dict[lable_curie] = None
        self.graph[self.name][self.sheet_name]['Nieuwenhuys'] = term_dict


class UberonTermsSheet1(UberonTermsSheet1Schema):
    name = 'uberon-terms'
    sheet_name = 'Sheet1'
    fetch_grid = False


class SpinalTerminologySheet1(SpinalTerminalogySheet1Schema):
    name = 'spinal-terminology'
    sheet_name = 'Sheet1'
    fetch_grid = True


class ParcellationUberon(ParcellationUberonSchema):
    name = 'parcellation-brainstem'
    sheet_name = 'UBERON'
    fetch_grid = False


class ParcellationAllen(ParcellationAllenSchema):
    name = 'parcellation-brainstem'
    sheet_name = 'Allen Mouse'
    fetch_grid = False


class ParcellationPaxinos(ParcellationPaxinosSchema):
    name = 'parcellation-brainstem'
    sheet_name = 'Paxinos Rat'
    fetch_grid = False


class ParcellationBerman(ParcellationBermanSchema):
    name = 'parcellation-brainstem'
    sheet_name = 'Berman Cat'
    fetch_grid = False


class ParcellationNieuwenhuys(ParcellationNieuwenhuysSchema):
    name = 'parcellation-brainstem'
    sheet_name = 'Nieuwenhuys'
    fetch_grid = False


class GoogleSheets(SheetPlus):

    def __init__(self):
        self.sheets = []
        self.collect_sheets()
        self.build_graphs()
        self.merge_graphs()
        self.hardcode_graph_paths()

    def collect_sheets(self):
        self.sheets.extend([
            UberonTermsSheet1(),
            SpinalTerminologySheet1(),
            ParcellationUberon(),
            ParcellationAllen(),
            ParcellationPaxinos(),
            ParcellationBerman(),
            ParcellationNieuwenhuys(),
        ])

    def build_graphs(self):
        for sheet in self.sheets:
            sheet.build()

    def merge_graphs(self):
        header_mappings = [
            # ((name, sheetname, (char, int)), (name, sheetname, (char, int)))
            (('uberon-terms', 'Sheet1', 3, 1), ('spinal-terminology', 'Sheet1', 0, 0)),
            (('uberon-terms', 'Sheet1', 3, 1), ('spinal-terminology', 'Sheet1', 1, 0)),
            (('uberon-terms', 'Sheet1', 3, 1), ('spinal-terminology', 'Sheet1', 2, 0)),
            (('uberon-terms', 'Sheet1', 3, 1), ('spinal-terminology', 'Sheet1', 3, 0)),
            (('uberon-terms', 'Sheet1', 3, 1), ('spinal-terminology', 'Sheet1', 5, 0)),
            (('uberon-terms', 'Sheet1', 3, 1), ('spinal-terminology', 'Sheet1', 6, 0)),
        ]

        # combine graphs
        self.graph = {}
        self.location_grid = {}
        for sheet in self.sheets:
            self.graph = {**sheet.graph[sheet.name][sheet.sheet_name], **self.graph}
            self.location_grid = {**sheet.location_grid, **self.location_grid}

        # use grid location to relocate headers/sub_headers
        for top, bottom in header_mappings:
            tname, tsheet_name, tcolumn, tindex = top
            bname, bsheet_name, bcolumn, bindex = bottom
            top_header = self.location_grid[tname][tsheet_name][(tcolumn, tindex)]
            bot_header = self.location_grid[bname][bsheet_name][(bcolumn, bindex)]
            term_nested_dict = self.graph.pop(bot_header)
            self.graph[top_header][bot_header] = term_nested_dict

    def hardcode_graph_paths(self):
        # displacements and creations
        self.graph['Atlas Nomenclature'] = {}
        self.graph['Atlas Nomenclature']['Allen Mouse Brainstem'] = self.graph.pop('Allen Mouse Brainstem')
        self.graph['Atlas Nomenclature']['Paxinos Rat Brainstem'] = self.graph.pop('Paxinos Rat Brainstem')
        self.graph['Atlas Nomenclature']['Berman Cat Brainstem'] = self.graph.pop('Berman Cat Brainstem')
        self.graph['Peripheral Nervous System'] = {}
        self.graph['Peripheral Nervous System']['Ganglia'] = self.graph.pop('Ganglia')
        self.graph['Spinal Cord']['Segment Anatomy'] = {}
        self.graph['Spinal Cord']['Segment Anatomy']['Lamina Of Spinal Cord'] = self.graph['Spinal Cord'].pop('Lamina Of Spinal Cord')
        self.graph['Spinal Cord']['Segment Anatomy']['Spinal Cord Internal Structures Per Segment'] = self.graph['Spinal Cord'].pop('Spinal Cord Internal Structures Per Segment')
        self.graph['Spinal Cord']['Segment Anatomy']['Spinal Cord Segments'] = self.graph['Spinal Cord'].pop('Spinal Cord Segments')
        self.graph['Spinal Cord']['Segment Anatomy']['Spinal Cord Subsegments'] = self.graph['Spinal Cord'].pop('Spinal Cord Subsegments')

        # Remove empty columns
        headers_to_pop = []
        for header, sub_header_on in self.graph.items():
            if len(self.graph[header].keys()) == 0:
                headers_to_pop.append(header)
        [self.graph.pop(header) for header in headers_to_pop]


def main():
    gsheets = GoogleSheets()
    with open(Path(devconfig.resources, 'sparc_terms2.txt'), 'w') as outfile:
        outfile.write('\n'.join(gsheets.get_rows()))


if __name__ == '__main__':
    main()
