# class UberonTerms(Sheet):
#     name = UBERON_TERMS
#     sheet_name = 'Sheet1'
#
#     def get_terms(self):
#         ''' Uberon has trailing empty cells in the sheet assuming its the value of the most recent
#             left cell with a value '''
#         terms_list = []
#         terms_index = 1
#         sub_terms_index = 2
#         last_value_index = 0
#         terms_dict = defaultdict(list)
#         records = []
#         for i, term in enumerate(self.raw_values[terms_index]):
#             sub_term = self.values[sub_terms_index][i]
#             if term:
#                 records.append(
#                     (self.name, term, i)
#                 )
#                 last_term = term
#             if sub_term:
#                 records.append(
#                     (self.name, '|_____ '+sub_term, i)
#                 )
#         return records
#
#     def get_term_list(self, colummn):
#         start_index = 3
#         return [row[int(colummn)] for row in self.values[start_index:] if row[int(colummn)]]
#
#
# class SpinalTerminology1(Sheet):
#     name = SPINAL_TERMINOLOGY
#     sheet_name = 'Sheet1'
#
#     def get_terms(self):
#         terms_list = []
#         headers_index = 0
#         headers_column_start = 1 # 1 header doesnt have a value
#         for i, term in enumerate(self.raw_values[headers_index][headers_column_start:], headers_column_start):
#             terms_list.append((SPINAL_TERMINOLOGY_1, term, i))
#         return terms_list
#
#     def get_term_list(self, colummn):
#         start_index = 1
#         return [row[int(colummn)] for row in self.values[start_index:] if row[int(colummn)]]
#
#
# class SpinalTerminology2(Sheet):
#     name = SPINAL_TERMINOLOGY
#     sheet_name = 'Sheet2'
#
#     def get_terms(self):
#         terms_list = []
#         headers_index = 0
#         headers_column_start = 0
#         for i, term in enumerate(self.raw_values[headers_index][headers_column_start:]):
#             terms_list.append((SPINAL_TERMINOLOGY_1, term, i))
#         return terms_list
#
#     def get_term_list(self, colummn):
#         start_index = 1
#         return [row[int(colummn)] for row in self.values[start_index:] if row[int(colummn)]]
#
#
# class ParcellationBrainstemMappings(Sheet):
#     name = PARCELLATION_BRAINSTEM
#     sheet_name = 'Mappings'
#
#     def get_terms(self):
#         terms_list = []
#         headers_index = 0
#         headers_column_start = 0
#         for i, term in enumerate(self.raw_values[headers_index][headers_column_start:]):
#             term = f'{term} (Mappings)'
#             terms_list.append((PARCELLATION_BRAINSTEM_MAPPINGS, term, i))
#         return terms_list
#
#     def get_term_list(self, colummn):
#         start_index = 1
#         return [row[int(colummn)] for row in self.values[start_index:] if row[int(colummn)]]
#
#
# class ParcellationBrainstemUberon(Sheet):
#     name = PARCELLATION_BRAINSTEM
#     sheet_name = 'UBERON'
#
#     def get_terms(self):
#         terms_list = []
#         headers_index = 0
#         headers_column_start = 0
#         for i, term in enumerate(self.raw_values[headers_index][headers_column_start:]):
#             terms_list.append((PARCELLATION_BRAINSTEM_UBERON, term, i))
#         return terms_list
#
#     def get_term_list(self, colummn):
#         start_index = 1
#         return [row[int(colummn)] for row in self.values[start_index:] if row[int(colummn)]]
#
#
# class ParcellationBrainstemAllenMouse(Sheet):
#     name = PARCELLATION_BRAINSTEM
#     sheet_name = 'Allen Mouse'
#
#     def get_terms(self):
#         return [(PARCELLATION_BRAINSTEM_ALLEN_MOUSE, 'Allen Mouse Sheet', 0)]
#
#     def get_term_list(self, colummn):
#         start_index = 0
#         return [row[int(colummn)] for row in self.values[start_index:] if row[int(colummn)]]
#
#
# class ParcellationBrainstemPaxinosRat(Sheet):
#     name = PARCELLATION_BRAINSTEM
#     sheet_name = 'Paxinos Rat'
#
#     def get_terms(self):
#         return [(PARCELLATION_BRAINSTEM_PAXINOS_RAT, 'Paxinos Rat Sheet', 0)]
#
#     def get_term_list(self, colummn):
#         start_index = 0
#         return [row[1:3] for row in self.values[start_index:]]
#
#
# class ParcellationBrainstemBermanCat(Sheet):
#     name = PARCELLATION_BRAINSTEM
#     sheet_name = 'Berman Cat'
#
#     def get_terms(self):
#         return [(PARCELLATION_BRAINSTEM_BERMAN_CAT, 'Berman Cat Sheet', 0)]
#
#     def get_term_list(self, colummn):
#         start_index = 0
#         return [row[int(colummn)] for row in self.values[start_index:] if row[int(colummn)]]
#
#
# class ParcellationBrainstemNieuwenhuys(Sheet):
#     name = PARCELLATION_BRAINSTEM
#     sheet_name = 'Nieuwenhuys'
#
#     def get_terms(self):
#         terms_list = []
#         headers_index = 0
#         headers_column_start = 0
#         for i, term in enumerate(self.raw_values[headers_index][headers_column_start:]):
#             terms_list.append((PARCELLATION_BRAINSTEM_NIEUWENHUYS, term, i))
#         return terms_list
#
#     def get_term_list(self, colummn):
#         start_index = 1
#         return [row[int(colummn)] for row in self.values[start_index:] if row[int(colummn)]]
# class GoogleSheets:
#
#     def __init__(self):
#         self.sheets = {}
#         self.sheets[UBERON_TERMS] = UberonTerms()
#         self.sheets[SPINAL_TERMINOLOGY_1] = SpinalTerminology1()
#         self.sheets[SPINAL_TERMINOLOGY_2] = SpinalTerminology2()
#         # Mappings not needed at the moment
#         # self.sheets[PARCELLATION_BRAINSTEM_MAPPINGS] = ParcellationBrainstemMappings()
#         self.sheets[PARCELLATION_BRAINSTEM_UBERON] = ParcellationBrainstemUberon()
#         self.sheets[PARCELLATION_BRAINSTEM_ALLEN_MOUSE] = ParcellationBrainstemAllenMouse()
#         self.sheets[PARCELLATION_BRAINSTEM_PAXINOS_RAT] = ParcellationBrainstemPaxinosRat()
#         self.sheets[PARCELLATION_BRAINSTEM_BERMAN_CAT] = ParcellationBrainstemBermanCat()
#         self.sheets[PARCELLATION_BRAINSTEM_NIEUWENHUYS] = ParcellationBrainstemNieuwenhuys()
#
#     def get_terms(self):
#         terms = []
#         terms += self.sheets[UBERON_TERMS].get_terms()
#         terms += self.sheets[SPINAL_TERMINOLOGY_1].get_terms()
#         terms += self.sheets[SPINAL_TERMINOLOGY_2].get_terms()
#         # Mappings not needed at the moment
#         # terms += self.sheets[PARCELLATION_BRAINSTEM_MAPPINGS].get_terms()
#         terms += self.sheets[PARCELLATION_BRAINSTEM_UBERON].get_terms()
#         terms += self.sheets[PARCELLATION_BRAINSTEM_ALLEN_MOUSE].get_terms()
#         terms += self.sheets[PARCELLATION_BRAINSTEM_PAXINOS_RAT].get_terms()
#         terms += self.sheets[PARCELLATION_BRAINSTEM_BERMAN_CAT].get_terms()
#         terms += self.sheets[PARCELLATION_BRAINSTEM_NIEUWENHUYS].get_terms()
#         return terms
#
#     def get_term_list(self, source, column):
#         return self.sheets[source].get_term_list(column)
