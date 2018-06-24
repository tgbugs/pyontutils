import requests
import pandas as pd
import numpy as np
import json
import sys

ranking = [
    'CHEBI',
    'NCBITaxon',
    'COGPO',
    'CAO',
    'DICOM',
    'UBERON',
    'NLX',
    'NLXANAT',
    'NLXCELL',
    'NLXFUNC',
    'NLXINV',
    'NLXORG',
    'NLXRES',
    'BIRNLEX',
    'SAO',
]


class scicrunch():
    def __init__(self, base_path=None, key=None, verbose=False, cache=False):
        self.session = requests.Session()
        self.base_path = base_path
        self.key = key

    def clean_iri(self, iri):
        return str(iri).lower().strip().replace('/', '').replace('\\', '')

    def preferred_change(self, data, term):
        df = pd.DataFrame(data).replace({np.nan: None})
        #ORGANIZE RANKING
        reverse_rank = ranking[::-1]  #make highest value is preferred
        ranking_list = []
        for curie in df.curie:  #matches rank with reverse index
            if not curie:
                ranking_list.append(
                    -1)  #default -1 for those that arent in ranking list
                continue
            prefix = curie.split(':')[0]
            if prefix in reverse_rank:
                ranking_list.append(reverse_rank.index(prefix))
            else:
                ranking_list.append(
                    -1)  #default -1 for those that arent in ranking list
        if ranking_list.count(-1) != len(ranking_list):
            ranking_list = [
                1 if max(ranking_list) == v else 0 for v in ranking_list
            ]  #all max values are 1 else 0
            preferred_index = ranking_list.index(1)  #grabs first 1 index
            filtered_ranking_list = [0] * len(ranking_list)
            filtered_ranking_list[
                preferred_index] = 1  #goal is to only allow 1 option for replacement

            #APPEND RANKING
            df['ranking'] = pd.Series(
                ranking_list
            )  #used for filtering if to see if preferred already exists
            df['filtered_ranking_list'] = pd.Series(
                filtered_ranking_list
            )  #for ranking with limited 1 option, used inputing new preferred

            #PREFERRED TRIAL
            sub_df = df[df.ranking ==
                        1]  #segment dataframe where ranking is highest
            if sub_df[
                    sub_df.preferred ==
                    1].empty:  #if preferred curie does not already exist in correct row
                df.preferred = 0  #flush
                df.loc[df.filtered_ranking_list == 1,
                       'preferred'] = 1  #top preferred curie is made preferred
                df = df.drop(
                    ['ranking', 'filtered_ranking_list'],
                    axis=1)  #delete ranking columns

            #PHP BUG
            df.iri = df.iri.str.replace('\\', '')  #fixed bug

            existing_ids = df.to_dict('records')  #wth, this exists?!
            #print(term)
            return existing_ids
        else:
            return data

    def check_web_connection(self, i, req, term):
        if req.status_code not in [200, 201]:
            sys.exit('Error code [' + str(req.status_code) + '] Stopped at ' +
                     str(term) + ' with index ' + str(i))

    def ilxTermSearch(self, i=None, term=None):
        url = self.base_path + '/api/1/ilx/search/term/' + term + '?key=' + self.key
        req = self.session.get(url)
        self.check_web_connection(i=i, req=req, term=term)
        output = req.json()
        return output if output['data'] else []

    def updateTerm(self,
                   i=None,
                   existing_ids=None,
                   term=None,
                   tid=None,
                   curie=None,
                   iri=None,
                   preferred=0,
                   superclasses=None,
                   ontologies=None,
                   synonyms=None,
                   relationships=None,
                   annotations=None,
                   mappings=None,
                   comment=None):
        url = self.base_path + '/api/1/term/edit/' + str(tid)

        #FIXME later should have an option to add exisiting ids
        #if data.get('new_existing_ids'):

        existing_ids = self.preferred_change(existing_ids, term)

        request_params = {
            'key': self.key,
            'existing_ids': existing_ids,
            'superclasses': superclasses,
            'ontologies': ontologies,
            'synonyms': synonyms,
            'relationships': relationships,
            'annotations': annotations,
            'mappings': mappings,
            'comment': comment,
        }
        headers = {'Content-type': 'application/json'}
        req = self.session.post(
            url, data=json.dumps(request_params), headers=headers)
        self.check_web_connection(i=i, req=req, term=term)
        output = req.json()
        return output

    def termSearch(self, i=None, term=None):
        url = self.base_path + '/api/1/term/search/' + term + '?key=' + self.key
        #print(url)
        req = self.session.get(url)
        self.check_web_connection(i=i, req=req, term=term)
        output = req.json()
        return output if output['data'] else []

    def ilxIdentifierSearch(self, i, ilx):
        url = self._basePath + '/ilx/search/identifier/' + ilx + '?key=' + self.key
        req = self.session.get(url)
        self.check_web_connection(i=0, req=req, term=ilx)
        output = req.json()
        return output if output['data'] else []

    def identifierSearch(self, identifier):
        url = self.base_path + '/api/1/term/view/' + str(
            identifier) + '?key=' + self.key
        #print(url)
        req = self.session.get(url)
        self.check_web_connection(i=None, req=req, term=identifier)
        output = req.json()
        return output if output['data'] else {}

    '''
    Will request deletion, but won't completely delete term by itself
    '''

    def deleteTerm(self, i=None, ilx=None):
        url = self.base_path + '/api/1/term/elastic/delete/' + ilx + '?key=' + self.key
        output = self.session.post(url).json()
        return output if output['data'] else []
