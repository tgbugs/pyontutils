from collections import defaultdict
from ilxutils.interlex_sql import IlxSql
import json
import os
import pandas as pd
from pathlib import Path
from rdflib import Graph, RDF, RDFS, OWL, BNode, URIRef, Literal
from sys import exit
from typing import Union, List, Dict, Tuple

from ilxutils.ontopandas import OntoPandas


class InterLexIngestion:

    ''' Goal is to give an additional tool to quick check if ontologies presented already have
        info within InterLex. '''

    def __init__(self, from_backup:bool=False):
        self.sql = IlxSql(db_url=os.environ.get('SCICRUNCH_DB_URL_PRODUCTION'), from_backup=from_backup)
        self.local_degrade = self.sql.local_degrade
        self.terms = self.sql.get_terms()
        self.label2rows = self.sql.get_label2rows()
        self.definition2rows = self.sql.get_definition2rows()
        self.existing_ids = self.sql.get_existing_ids()
        self.ilx2row = self.sql.get_ilx2row()
        self.ilx2existing_ids = self.sql.get_ilx2existing_ids()
        self.iri2row = self.sql.get_iri2row()
        self.curie2row = self.sql.get_curie2row()
        self.fragment2rows = self.sql.get_fragment2rows()
        self.terms_complete = self.sql.get_terms_complete()

    def grab_rdflib_graph_version(g: Graph) -> str:
        ''' Crap-shot for ontology iri if its properly in the header and correctly formated '''
        version = g.subject_objects( predicate = URIRef( OWL.versionIRI ) )
        version = [o for s, o in version]
        if len(version) != 1:
            print('versioning isn\'t correct')
        else:
            version = str(version[0])
            return version

    def fix_ilx(self, ilx_id: str) -> str:
        ''' Database only excepts lower case and underscore version of ID '''
        ilx_id = ilx_id.replace('http://uri.interlex.org/base/', '')
        if ilx_id[:4] not in ['TMP:', 'tmp_', 'ILX:', 'ilx_']:
            raise ValueError(
                'Need to provide ilx ID with format ilx_# or ILX:# for given ID ' + ilx_id)
        return ilx_id.replace('ILX:', 'ilx_').replace('TMP:', 'tmp_')

    def pull_int_tail(self, string: str) -> str:
        ''' Useful for IDs that have giberish in the front of the real ID '''
        int_tail = ''
        for element in string[::-1]:
            try:
                int(element)
                int_tail = element + int_tail
            except:
                pass
        return int_tail

    def extract_fragment(self, iri: str) -> str:
        ''' Pulls only for code/ID from the iri

        I only add the str() conversion for the iri because rdflib objects need to be converted.
        '''
        fragment = str(iri).rsplit('/')[-1].split(':', 1)[-1].split('#', 1)[-1].split('_', 1)[-1]
        return fragment

    def curie_search(self, curie:str) -> dict:
        ''' Returns the row in InterLex associated with the curie

        Note:
            Pressumed to not have duplicate curies in InterLex
        Args:
            curie: The "prefix:fragment_id" of the existing_id pertaining to the ontology
        Returns:
            None or dict
        '''
        ilx_row = self.curie2row.get(curie)
        if not ilx_row:
            return None
        else:
            return ilx_row

    def fragment_search(self, fragement:str) -> List[dict]:
        ''' Returns the rows in InterLex associated with the fragment

        Note:
            Pressumed to have duplicate fragements in InterLex
        Args:
            fragment: The fragment_id of the curie pertaining to the ontology
        Returns:
            None or List[dict]
        '''
        fragement = self.extract_fragment(fragement)
        ilx_rows = self.fragment2rows.get(fragement)
        if not ilx_rows:
            return None
        else:
            return ilx_rows

    def label_search(self, label:str) -> List[dict]:
        ''' Returns the rows in InterLex associated with that label

        Note:
            Pressumed to have duplicated labels in InterLex
        Args:
            label: label of the entity you want to find
        Returns:
            None or List[dict]
        '''
        ilx_rows = self.label2rows(self.local_degrade(label))
        if not ilx_rows:
            return None
        else:
            return ilx_rows

    def readyup_entity(
        self,
        label: str,
        type: str,
        uid: Union[int, str] = None,
        comment: str = None,
        definition: str = None,
        superclass: str = None,
        synonyms: list = None,
        existing_ids: List[dict] = None, ) -> dict:
        ''' Setups the entity to be InterLex ready

        Args:
            label: name of entity
            type: entities type
                Can be any of the following: term, cde, fde, pde, annotation, relationship
            uid: usually fine and auto completes to api user ID, but if you provide one with a
                clearance higher than 0 you can make your own custom. Good for mass imports by one
                person to avoid label collides.
            definition: entities definition
            comment: a foot note regarding either the interpretation of the data or the data itself
            superclass: entity is a sub-part of this entity
                Example: Organ is a superclass to Brain
            synonyms: entity synonyms
            existing_ids: existing curie/iris that link data | couldnt format this easier
        Returns:
            dict
        '''

        entity = dict(
            label = label,
            type = type,
        )

        if uid:
            entity['uid'] = uid

        if definition:
            entity['definition'] = definition

        if comment:
            entity['comment'] = comment

        if superclass:
            entity['superclass'] = {'ilx_id':self.fix_ilx(superclass)}

        if synonyms:
            entity['synonyms'] = [{'literal': syn} for syn in synonyms]

        if existing_ids:
            if existing_ids[0].get('curie') and existing_ids[0].get('iri'):
                pass
            else:
                exit('Need curie and iri for existing_ids in List[dict] form')
            entity['existing_ids'] = existing_ids

        return entity

    def __exhaustive_diff(self, check_list:List[dict]) -> List[List[dict]]:
        ''' Helper for exhaustive checks to see if there any matches at all besides the anchor
            OUTPUT:
                [
                    {
                        'external_ontology_row' : {},
                        'interlex_row' : {},
                        'same': {},
                    },
                    ...
                ],
        '''
        def compare_rows(external_row:dict, ilx_row:dict) -> List[dict]:
            ''' dictionary comparator '''

            def compare_values(string1:Union[str, None], string2:Union[str, None]) -> bool:
                ''' string comparator '''
                if string1 is None or string2 is None:
                    return False
                elif not isinstance(string1, str) or not isinstance(string2, str):
                    return False
                elif string1.lower().strip() != string2.lower().strip():
                    return False
                else:
                    return True

            accepted_ilx_keys = ['label', 'definition']
            local_diff = set()
            for external_key, external_value in external_row.items():

                if not external_value:
                    continue

                if isinstance(external_value, list):
                    external_values = external_value
                    for external_value in external_values:
                        for ilx_key, ilx_value in ilx_row.items():
                            if ilx_key not in accepted_ilx_keys:
                                continue
                            if compare_values(external_value, ilx_value):
                                local_diff.add(
                                    #((external_key, external_value), (ilx_key, ilx_value))
                                    ilx_key # best to just have what you need and infer the rest :)
                                )
                else:
                    for ilx_key, ilx_value in ilx_row.items():
                        if ilx_key not in accepted_ilx_keys:
                            continue
                        if compare_values(external_value, ilx_value):
                            local_diff.add(
                                #((external_key, external_value), (ilx_key, ilx_value))
                                ilx_key # best to just have what you need and infer the rest :)
                            )
            local_diff = list(local_diff)
            diff = {
                'external_ontology_row': external_row,
                'ilx_row': ilx_row,
                'same': local_diff,
            }
            return diff

        diff = []
        for check_dict in check_list:
            external_ontology_row = check_dict['external_ontology_row']
            diff.append(
                [compare_rows(external_ontology_row, ilx_row) for ilx_row in check_dict['ilx_rows']]
            )
        return diff

    def exhaustive_label_check( self,
                                ontology:pd.DataFrame,
                                label_predicate='rdfs:label',
                                diff:bool=True, ) -> Tuple[list]:
        ''' All entities with conflicting labels gets a full diff

            Args:
                ontology: pandas DataFrame created from an ontology where the colnames are predicates
                    and if classes exist it is also thrown into a the colnames.
                label_predicate: usually in qname form and is the colname of the DataFrame for the label
                diff: complete exhaustive diff if between curie matches... will take FOREVER if there are a lot -> n^2
            Returns:
                inside: entities that are inside of InterLex
                outside: entities NOT in InterLex
                diff (optional): List[List[dict]]... so complicated but usefull diff between matches only '''

        inside, outside = [], []
        header = ['Index'] + list(ontology.columns)
        for row in ontology.itertuples():

            row = {header[i]:val for i, val in enumerate(row)}
            label_obj = row[label_predicate]
            if isinstance(label_obj, list):
                if len(label_obj) != 1:
                    exit('Need to have only 1 label in the cell from the onotology.')
                else:
                    label_obj = label_obj[0]
            entity_label = self.local_degrade(label_obj)
            ilx_rows = self.label2rows.get(entity_label)
            if ilx_rows:
                inside.append({
                    'external_ontology_row': row,
                    'ilx_rows': ilx_rows,
                })
            else:
                outside.append(row)

        if diff:
            diff = self.__exhaustive_diff(inside)
            return inside, outside, diff
        return inside, outside

    def exhaustive_iri_check( self,
                              ontology:pd.DataFrame,
                              iri_predicate:str,
                              diff:bool=True, ) -> Tuple[list]:
        ''' All entities with conflicting iris gets a full diff to see if they belong

            Args:
                ontology: pandas DataFrame created from an ontology where the colnames are predicates
                    and if classes exist it is also thrown into a the colnames.
                iri_predicate: usually in qname form and is the colname of the DataFrame for iri
                    Default is "iri" for graph2pandas module
                diff: complete exhaustive diff if between curie matches... will take FOREVER if there are a lot -> n^2
            Returns:
                inside: entities that are inside of InterLex
                outside: entities NOT in InterLex
                diff (optional): List[List[dict]]... so complicated but usefull diff between matches only '''

        inside, outside = [], []
        header = ['Index'] + list(ontology.columns)
        for row in ontology.itertuples():

            row = {header[i]:val for i, val in enumerate(row)}
            entity_iri = row[iri_predicate]
            if isinstance(entity_iri, list):
                if len(entity_iri) != 0:
                    exit('Need to have only 1 iri in the cell from the onotology.')
                else:
                    entity_iri = entity_iri[0]

            ilx_row = self.iri2row.get(entity_iri)
            if ilx_row:
                inside.append({
                    'external_ontology_row': row,
                    'ilx_rows': [ilx_row],
                })
            else:
                outside.append(row)

        if diff:
            diff = self.__exhaustive_diff(inside)
            return inside, outside, diff
        return inside, outside

    def exhaustive_curie_check( self,
                                ontology:pd.DataFrame,
                                curie_predicate:str,
                                curie_prefix:str,
                                diff:bool=True, ) -> Tuple[list]:
        ''' All entities with conflicting curies gets a full diff to see if they belong

            Args:
                ontology: pandas DataFrame created from an ontology where the colnames are predicates
                    and if classes exist it is also thrown into a the colnames.
                curie_predicate: usually in qname form and is the colname of the DataFrame
                curie_prefix: Not all cells in the DataFrame will have complete curies so we extract
                    the fragement from the cell and use the prefix to complete it.
                diff: complete exhaustive diff if between curie matches... will take FOREVER if there are a lot -> n^2
            Returns:
                inside: entities that are inside of InterLex
                outside: entities NOT in InterLex
                diff (optional): List[List[dict]]... so complicated but usefull diff between matches only '''
        inside, outside = [], []
        curie_prefix = curie_prefix.replace(':', '') # just in case I forget a colon isnt in a prefix
        header = ['Index'] + list(ontology.columns)
        for row in ontology.itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            entity_curie = row[curie_predicate]
            if isinstance(entity_curie, list):
                if len(entity_curie) != 0:
                    exit('Need to have only 1 iri in the cell from the onotology.')
                else:
                    entity_curie = entity_curie[0]
            entity_curie = curie_prefix + ':' + self.extract_fragment(entity_curie)

            ilx_row = self.curie2row.get(entity_curie)
            if ilx_row:
                inside.append({
                    'external_ontology_row': row,
                    'ilx_rows': [ilx_row],
                })
            else:
                outside.append(row)
        if diff:
            diff = self.__exhaustive_diff(inside)
            return inside, outside, diff
        return inside, outside

    def exhaustive_fragment_check( self,
                                   ontology:pd.DataFrame,
                                   iri_curie_fragment_predicate:str = 'iri',
                                   cross_reference_iris:bool = False,
                                   cross_reference_fragments:bool = False,
                                   diff:bool = True, ) -> Tuple[list]:
        ''' All entities with conflicting fragments gets a full diff to see if they belong

            Args:
                ontology: pandas DataFrame created from an ontology where the colnames are predicates
                    and if classes exist it is also thrown into a the colnames.
                iri_curie_fragment_predicate: usually in qname form and is the colname of the DataFrame for iri
                    Default is "iri" for graph2pandas module
                diff: complete exhaustive diff if between curie matches... will take FOREVER if there are a lot -> n^2
            Returns:
                inside: entities that are inside of InterLex
                outside: entities NOT in InterLex
                diff (optional): List[List[dict]]... so complicated but usefull diff between matches only '''

        inside, outside = [], []
        header = ['Index'] + list(ontology.columns)
        for row in ontology.itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            entity_suffix = row[iri_curie_fragment_predicate]
            if isinstance(entity_suffix, list):
                if len(entity_suffix) != 0:
                    exit('Need to have only 1 iri in the cell from the onotology.')
                else:
                    entity_suffix = entity_suffix[0]
            entity_fragment = self.extract_fragment(entity_suffix)
            ilx_rows = self.fragment2rows.get(entity_fragment)
            if cross_reference_fragments and ilx_rows:
                ilx_rows = [row for row in ilx_rows if entity_fragment.lower() in row['iri'].lower()]
            if cross_reference_iris and ilx_rows:
                # true suffix of iris
                ilx_rows = [row for row in ilx_rows if entity_suffix.rsplit('/', 1)[-1].lower() in row['iri'].lower()]
            if ilx_rows:
                inside.append({
                    'external_ontology_row': row,
                    'ilx_rows': ilx_rows,
                })
            else:
                outside.append(row)
        if diff:
            diff = self.__exhaustive_diff(inside)
            return inside, outside, diff
        return inside, outside

    def exhaustive_ontology_ilx_diff_row_only( self, ontology_row: dict ) -> dict:
        ''' WARNING RUNTIME IS AWEFUL '''
        results = []
        header = ['Index'] + list(self.existing_ids.columns)
        for row in self.existing_ids.itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            check_list = [
                {
                    'external_ontology_row': ontology_row,
                    'ilx_rows': [row],
                },
            ]
            # First layer for each external row. Second is for each potential ilx row. It's simple here 1-1.
            result = self.__exhaustive_diff(check_list)[0][0]
            if result['same']:
                results.append(result)
        return results

    def combo_exhaustive_label_definition_check( self,
                                                 ontology: pd.DataFrame,
                                                 label_predicate:str,
                                                 definition_predicates:str,
                                                 diff = True) -> List[List[dict]]:
        ''' Combo of label & definition exhaustive check out of convenience

            Args:
                ontology: pandas DataFrame created from an ontology where the colnames are predicates
                    and if classes exist it is also thrown into a the colnames.
                label_predicate: usually in qname form and is the colname of the DataFrame for the label
                diff: complete exhaustive diff if between curie matches... will take FOREVER if there are a lot -> n^2
            Returns:
                inside: entities that are inside of InterLex
                outside: entities NOT in InterLex
                diff (optional): List[List[dict]]... so complicated but usefull diff between matches only '''

        inside, outside = [], []
        header = ['Index'] + list(ontology.columns)
        for row in ontology.itertuples():

            row = {header[i]:val for i, val in enumerate(row)}

            label_obj = row[label_predicate]
            if isinstance(label_obj, list):
                if len(label_obj) != 1:
                    exit('Need to have only 1 label in the cell from the onotology.')
                else:
                    label_obj = label_obj[0]
            entity_label = self.local_degrade(label_obj)
            label_search_results = self.label2rows.get(entity_label)
            label_ilx_rows = label_search_results if label_search_results else []

            definition_ilx_rows = []
            for definition_predicate in definition_predicates:
                definition_objs = row[definition_predicate]
                if not definition_objs:
                    continue
                definition_objs = [definition_objs] if not isinstance(definition_objs, list) else definition_objs
                for definition_obj in definition_objs:
                    definition_obj = self.local_degrade(definition_obj)
                    definition_search_results = self.definition2rows.get(definition_obj)
                    if definition_search_results:
                        definition_ilx_rows.extend(definition_search_results)

            ilx_rows = [dict(t) for t in {tuple(d.items()) for d in (label_ilx_rows + definition_ilx_rows)}]
            if ilx_rows:
                inside.append({
                    'external_ontology_row': row,
                    'ilx_rows': ilx_rows,
                })
            else:
                outside.append(row)

        if diff:
            diff = self.__exhaustive_diff(inside)
            return inside, outside, diff
        return inside, outside

def example():
    ii = InterLexIngestion(from_backup=True)
    g = Graph().parse(str(Path.home()/'Dropbox/scidumps/CUMBO/CUMBO_Definitions_20130711.owl'), format='xml')
    query = ''' SELECT ?subj ?pred ?obj WHERE {?subj ?pred ?obj;} ''' # Ontology is only 1 dimensional
    cumbo = Graph2Pandas(obj=g, query=query).df
    definition_predicates = [colname for colname in cumbo.columns if 'definition' in colname.lower()]
    results = ii.combo_exhaustive_label_definition_check(
        ontology=cumbo.head(5),
        label_predicate='rdfs:label',
        definition_predicates=definition_predicates,
        diff=True,
    )
    print(results)

if __name__ == '__main__':
    example()
''' REASON WHY JSON DIFFS SUCK
diff, external_onto_ilx_ready = diff_ontologies()

dict_1 output:
    ilx_id: {
        'label':
        'definition':
        'comment':
        'synonyms':
        'superclass':
        'existing_ids': [{'iri':, 'curie':},]
        'external_matches': [
            {
                'iri':
                'curie':
                'label': [(iri, qname, obj_string),],
                'definition': [(iri, qname, obj_string),],
                'synonyms': [(iri, qname, obj_string),],
                'superclasss': [(iri, qname, obj_string),],
            },
        ]
    },

dict_2 output:
    'iri': {
        'label':
        'definition':
        'comment':
        'synonyms':
        'superclass':
        'existing_ids': [{'iri':, 'curie':},]
        'annotations': "[{{entity_id}, {annotation_type_id}, {annotation_value}}]"
        'relationships': "[{{entity1_id}, {relationship_type_id}, {entity2_id}}]"
        'ontologies': "[{'id':{ontology_id}},]"
    }
'''
