""" Sparc View Tree
WorkFlow:
    1. Create schema class
    2. Create sheet importing schema class
    3. update collect_sheets in GoogleSheets
    4. any merging in graphs and harding is down in the following
        functions in GoogleSheets (merge_graphs & hardcode_graph_paths)
    5. rerun sheet.py to generate sparc_terms.txt/csv to use
    6. OPTIONAL: edit sparc_terms.txt manually for any last minute complicated tasks

Notes:
    - grid needs to be enabled to allow bold traversal
    - new sheets == need work flow
"""
from collections import defaultdict, OrderedDict
from copy import deepcopy
import csv
from flask import url_for
from itertools import zip_longest
from pathlib import Path
from pyontutils.config import auth
from pyontutils.sheets import Sheet
from pyontutils.core import makeGraph, qname, OntId, OntTerm
from htmlfn import htmldoc, titletag, atag, ptag, nbsp
from typing import Union, Dict, List
from sys import exit
import yaml
VERSION = '0.0.1'
YML_DISPLAY_DELIMITER = '\t'
YML_DELIMITER = '\u1F4A9'
REC_DD = lambda: defaultdict(REC_DD)

resources = auth.get_path('resources')


def open_custom_sparc_view_yml(seperate_curies: bool = True) -> dict:
    ''' Custom yaml is a normal yaml without colons and curies delimited by 4 spaces
        This causes last list elements to be a dictionary of None values which is fine bc
        labels should not be repeating '''

    def ordered_load(stream, Loader=yaml.SafeLoader, object_pairs_hook=OrderedDict):
        class OrderedLoader(Loader):
            pass
        def construct_mapping(loader, node):
            loader.flatten_mapping(node)
            return object_pairs_hook(loader.construct_pairs(node))
        OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            construct_mapping)
        return yaml.load(stream, OrderedLoader)

    def sep_curies(src_graph, delimiter=YML_DELIMITER):
        graph = deepcopy(src_graph)
        visited, stack = set(), [graph]
        while stack:
            dict_ = stack.pop()
            for key, value in dict_.copy().items():
                label, *curies = key.split(delimiter)
                if label == 'CURIES':
                    continue
                dict_[label] = dict_.pop(key)
                if isinstance(value, dict):
                    dict_[label].update({'CURIES': curies})
                    stack.append(value)
                else:
                    dict_[label] = {'CURIES': curies}

        return graph

    with open(resources / 'sparc_term_versions/sparc_terms2-mod.txt', 'rt') as infile:
        raw_yaml = ''
        for line in infile.readlines()[1:]:
            # last line doesnt have newline so we cant just replace it
            raw_yaml += line.replace('\n', '').replace(YML_DISPLAY_DELIMITER, YML_DELIMITER) + ':\n'
        if seperate_curies:
            sparc_view = sep_curies(ordered_load(raw_yaml, yaml.SafeLoader))
        else:
            sparc_view = ordered_load(raw_yaml, yaml.SafeLoader)

    return sparc_view


def tag_row(row: list, url: url_for = None, tier_level: int = 0) -> list:
    ''' Tag each element in the row; atag the curies & ptag everything else '''

    tagged_row = []
    spaces = nbsp * 8 * tier_level

    if not row:
        return row
    if not isinstance(row, list):
        row = [row]
    for i, element in enumerate(row):
        if i > 0:
            spaces = ''
        try:
            oid = OntId(element)
            # TODO: should this have spaces?
            tagged_curie = atag(oid.iri, oid.curie)
            tagged_row.append(tagged_curie)
        except:
            if url:
                tagged_row.append(ptag(spaces + atag(url, element)))
            else:
                tagged_row.append(spaces + element)

    return tagged_row


def hyperlink_tree(tree: dict) -> list:

    def linearize_graph(dict_: dict, tier_level: int = 0) -> tuple:
        """ Recursively pull nested dictionaries out of print order"""
        for key, value in dict_.items():
            if key == 'CURIES':
                continue
            row = [key] + dict_[key]['CURIES']
            yield (row, tier_level)
            if isinstance(value, dict):
                yield from linearize_graph(value, tier_level + 1)

    hyp_rows = []
    for row, tier_level in linearize_graph(tree):
        tagged_row = tag_row(row=row, tier_level=tier_level)
        hyp_rows.append(tagged_row)

    return hyp_rows


class SheetPlus(Sheet):
    ''' Appending to Sheet functionality '''

    def create_master_csv_rows(self):
        ''' structure matches UBERON google sheet '''

        def linearize_graph(dict_: dict, index: int = 0) -> tuple:
            """ Recursively pull nested dictionaries out of print order"""
            for key, value in dict_.items():
                if key == 'CURIES':
                    continue
                yield (key, index)
                if list(value.keys()) == ['CURIES']:
                    index += 1
                if isinstance(value, dict):
                    yield from linearize_graph(value, index + 1)

        # Reason beind taking the already made yaml instead of using the tree is not having to wait
        # ~40 seconds to reload queried curies
        sparc = open_custom_sparc_view_yml()
        rows = []
        for entity, index in list(linearize_graph(sparc))[:]:
            if len(rows) - 1 < index:
                rows += [[]]
            # Dealing with lower entities list being smaller than the upper entities list
            try:
                while True:
                    if len(rows[index-1]) - 1 > len(rows[index]):
                        rows[index] += ['']
                    else:
                        break
            except:
                pass
            rows[index] += [entity]
            # Dealing with upper entities list being smaller than the lower entities list
            try:
                if len(rows[index-1]) < len(rows[index]):
                    seed = index
                    while seed:
                        rows[seed-1] += ['']
                        seed -= 1
            except:
                pass

        # Dealing with new columns being shorter than previous columns
        row_length = max([len(row) for row in rows])

        for index in range(len(rows)):
            while True:
                if len(rows[index]) < row_length:
                    rows[index] += ['']
                else:
                    break

        return rows

    def get_html_rows(self, dict_={}):
        if not dict_:
            dict_ = self.tree
        rows = [
            [(8 * nbsp * tier_level) + label + (nbsp * 8)] # + curies
            for label, curies, tier_level  in self.linearize_graph(dict_)
        ]
        return rows

    def get_rows(self, dict_={}):
        spaces = ' ' * 4
        if not dict_:
            dict_ = self.tree
        rows = []
        for label, curies, tier_level in self.linearize_graph(dict_):
            if curies:
                rows.append(
                    (spaces * tier_level) + label +
                    YML_DISPLAY_DELIMITER +
                    YML_DISPLAY_DELIMITER.join(curies))
            else:
                rows.append((spaces * tier_level) + label)
        return rows

    def fix_curie(self, curie):
        if not curie:
            return curie
        curie = curie.strip().upper()
        return curie

    def linearize_graph(self, dict_: dict, tier_level: int = 0) -> tuple:
        # TODO: need to put the {str:None,} -> [str,]
        """ Recursively pull nested dictionaries out of print order"""
        for key, value in dict_.items():
            label, curie = self.curie_splitter(key) # self.normt(key)
            if curie:
                curies = [self.fix_curie(curie)]
            else:
                if label:
                    curies = self.query_scigraph_for_curies(label)
                else:
                    continue
            yield (label, curies, tier_level)
            if isinstance(value, dict) or isinstance(value, OrderedDict):
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

    def query_scigraph_for_curies(self, label: str, prefixes:List[str] = ['UBERON', 'ILX']) -> list:
        curies = []
        # return []
        # for prefix in prefixes:
        # BUG: prefixes cant be used because it gives random errors if the prefix isn't exact
        for prefix in prefixes:
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
        return string.strip()

    def populate_location_grid(self):
        for y, row in enumerate(self.raw_values):
            for x, value in enumerate(row):
                self.location_grid[self.name][self.sheet_name][(x, y)] = self.clean(value)

    def get_sub_column(self, start_index, column, end_index=None):
        od = OrderedDict()
        [
            od.update({self.clean(row[column]):None})
            for row in self.values[start_index:end_index]
            if row[column]
        ]
        return od

    def get_sub_header_indexes(self, start_index, column):
        ''' Parse for bold text and returns its coordinates '''
        for sheet in self.grid['sheets']:
            if sheet['properties']['title'] == self.sheet_name:
                for datum in sheet['data']:
                    for i, row in enumerate(datum['rowData'][start_index:], start_index):
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

    def build(self):
        self.tree = REC_DD()
        self.location_grid = REC_DD()
        self.populate_location_grid()
        self.populate_graph()

    def populate_graph(self, colname, start_index=0, column=0):
        ''' Example for a single column sheet with no header '''
        ### NOT HEADER
        self.tree[self.name][self.sheet_name][colname] = self.get_sub_column(
            start_index = start_index, column = column)


class UberonTermsSheet1Schema(SheetPlus):

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
            term = self.clean(term).title()
            sub_term = self.clean(self.values[sub_terms_index][column]).title()
            # iterative terms could be blank
            if term:
                last_term = term

            if sub_term:
                terms_list = self.get_sub_column(
                    start_index = sub_terms_index + 1,
                    column = column,
                )
                self.tree[self.name][self.sheet_name][last_term][sub_term] = terms_list
            elif term:
                terms_list = self.get_sub_column(
                    start_index = terms_index + 1,
                    column = column,
                )
                self.tree[self.name][self.sheet_name][term] = terms_list


class SpinalTerminologySheet1Schema(SheetPlus):

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
                self.tree[self.name][self.sheet_name][header] = terms_list
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
                        self.tree[self.name][self.sheet_name][header][sub_header] = sub_terms_list


class SpinalTerminologySheet2Schema(SheetPlus):

    def populate_graph(self):
        self.tree[self.name][self.sheet_name]['Gross Anatomy'] = self.get_sub_column(
            start_index = 1,
            column = 0)


class ParcellationUberonSchema(SheetPlus):

    def populate_graph(self):
        ### NOT HEADER
        self.tree[self.name][self.sheet_name]['UBERON'] = self.get_sub_column(
            start_index = 2,
            column = 0)


class ParcellationAllenSchema(SheetPlus):

    def populate_graph(self):
        ### NOT HEADER
        self.tree[self.name][self.sheet_name]['Allen Mouse Brainstem'] = self.get_sub_column(
            start_index = 0,
            column = 0)


class ParcellationPaxinosSchema(SheetPlus):

    def populate_graph(self):
        term_dict = {}
        for row in self.values[1:]:
            row = [cell for cell in row if cell]
            lable_curie = '-'.join(row)
            term_dict[lable_curie] = None
        self.tree[self.name][self.sheet_name]['Paxinos Rat Brainstem'] = term_dict


class ParcellationBermanSchema(SheetPlus):

    def populate_graph(self):
        ### NOT HEADER
        self.tree[self.name][self.sheet_name]['Berman Cat Brainstem'] = self.get_sub_column(
            start_index = 0,
            column = 0)


class ParcellationNieuwenhuysSchema(SheetPlus):

    def populate_graph(self):
        term_dict = OrderedDict()
        for row in self.raw_values[:]:
            row = [cell for cell in row if cell]
            lable_curie = YML_DELIMITER.join(row)
            term_dict[lable_curie] = None
        self.tree[self.name][self.sheet_name]['Nieuwenhuys'] = term_dict


class UberonTermsSheet1(UberonTermsSheet1Schema):
    name = 'uberon-terms'
    sheet_name = 'Sheet1'
    fetch_grid = False


class SpinalTerminologySheet1(SpinalTerminologySheet1Schema):
    name = 'spinal-terminology'
    sheet_name = 'Sheet1'
    fetch_grid = True

class SpinalTerminologySheet2(SpinalTerminologySheet2Schema):
    name = 'spinal-terminology'
    sheet_name = 'Sheet2'
    fetch_grid = False

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
            SpinalTerminologySheet2(),
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
        self.tree = OrderedDict()
        self.location_grid = {}
        for sheet in self.sheets:
            self.tree.update(sheet.tree[sheet.name][sheet.sheet_name])
            self.location_grid = {**sheet.location_grid, **self.location_grid}

        # use grid location to relocate headers/sub_headers
        for top, bottom in header_mappings:
            tname, tsheet_name, tcolumn, tindex = top
            bname, bsheet_name, bcolumn, bindex = bottom
            top_header = self.location_grid[tname][tsheet_name][(tcolumn, tindex)]
            bot_header = self.location_grid[bname][bsheet_name][(bcolumn, bindex)]
            try:
                term_nested_dict = self.tree.pop(bot_header)
            except:
                term_nested_dict = self.tree.pop(self.clean(bot_header))
            self.tree[top_header][bot_header] = term_nested_dict

    def hardcode_graph_paths(self):
        # displacements and creations
        self.tree['Atlas Nomenclature'] = {}
        self.tree['Atlas Nomenclature']['Allen Mouse Brainstem'] = self.tree.pop('Allen Mouse Brainstem')
        self.tree['Atlas Nomenclature']['Paxinos Rat Brainstem'] = self.tree.pop('Paxinos Rat Brainstem')
        self.tree['Atlas Nomenclature']['Berman Cat Brainstem'] = self.tree.pop('Berman Cat Brainstem')
        self.tree['Peripheral Nervous System'] = {}
        self.tree['Peripheral Nervous System']['Ganglia'] = self.tree.pop('Ganglia')
        self.tree['Spinal Cord']['Segmental Anatomy'] = {}
        self.tree['Spinal Cord']['Segmental Anatomy']['Lamina Of Spinal Cord'] = self.tree['Spinal Cord'].pop('Lamina of spinal cord')
        self.tree['Spinal Cord']['Segmental Anatomy']['Spinal Cord Internal Structures Per Segment'] = self.tree['Spinal Cord'].pop('Spinal cord internal structures per segment')
        self.tree['Spinal Cord']['Segmental Anatomy']['Spinal Cord Segments'] = self.tree['Spinal Cord'].pop('Spinal cord segments')
        self.tree['Spinal Cord']['Segmental Anatomy']['Spinal Cord Subsegments'] = self.tree['Spinal Cord'].pop('Spinal cord subsegments')

        # Remove empty columns
        headers_to_pop = []
        for header, sub_header_on in self.tree.items():
            if len(self.tree[header]) == 0:
                headers_to_pop.append(header)
        [self.tree.pop(header) for header in headers_to_pop]


def main():
    gsheets = GoogleSheets()
    with open(resources / 'sparc_term_versions/sparc_terms3.txt', 'w') as outfile:
        outfile.write(f'### YAML DELIMITER  ==  {YML_DELIMITER} ###')
        outfile.write('\n')
        outfile.write('\n'.join(gsheets.get_rows()))

    with open(resources / 'sparc_term_versions/sparc_terms3.csv', "w") as csv_file:
        writer = csv.writer(csv_file, delimiter=',', lineterminator='\n')
        csv_rows = gsheets.create_master_csv_rows()
        for line in csv_rows:
            writer.writerow(line)


if __name__ == '__main__':
    main()
