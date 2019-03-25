from aiohttp import ClientSession, TCPConnector, BasicAuth
import asyncio
from collections import defaultdict, namedtuple
from IPython import embed
import json
import pandas as pd
import random
import requests as r
import string
from sys import exit
from typing import Union, List, Dict
import ilxutils.scicrunch_client_helper as scicrunch_client_helper
import os
# TODO: create a check for superclass... if entity superclass is known to be different then create your own. else biggy back known entity
# THOUGHTS: What if you don't know if superclass is different?

class scicrunch():

    '''
        Get functions need a list of term ids
        Post functions need a list of dictionaries with their needed/optional keys & values

        identifierSearches          ids, LIMIT=25, _print=True, crawl=False
        addTerms                    data ....
        updateTerms                 data ....
        addAnnotations              data ....
        getAnnotations_via_tid      tids ....
        getAnnotations_via_id       annotation_ids ....
        updateAnntation             data ....
        deleteAnnotations           annotation_ids ....
        addRelationship             data ....
        deleteTerms                 ilx_ids .. crawl=True .
    '''

    def __init__(self, api_key, base_url, auth=('None', 'None')):
        self.api_key = api_key
        self.base_url = base_url
        self.auth = BasicAuth(auth)

    def crawl_get(self, urls):
        outputs = {}
        for url in urls:
            auth = ('scicrunch',
                    'perl22(query)')  # needed for test2.scicrunch.org
            headers = {'Content-type': 'application/json'}
            response = r.get(url, headers=headers, auth=auth)

            if response.status_code not in [200, 201]:
                try:
                    output = response.json()
                except:
                    output = response.text
                problem = str(output)
                exit(str(problem) + ' with status code [' +
                     str(response.status_code) + '] with params:' + str(data))

            else:
                output = response.json()

                if output.get('errormsg'):
                    exit(output['errormsg'])

                # Duplicates; don't exit
                elif output.get('data').get('errormsg'):
                    exit(output['data']['errormsg'])

            if not output.get('data').get('id'):
                continue

            try:
                output = {int(output['data']['id']): output['data']}  # terms
            except:
                output = {int(output['data'][0]['tid']): output['data']}  # annotations

            outputs.update(output)

        return outputs

    def crawl_post(self, total_data, _print):
        outputs = []
        for i, tupdata in enumerate(total_data):
            url, data = tupdata
            params = {
                **{'key': self.api_key, },
                **data,
            }
            auth = ('scicrunch',
                    'perl22(query)')  # needed for test2.scicrunch.org
            headers = {'Content-type': 'application/json'}
            # print(data['uid'], 'data')
            response = r.post(url, data=json.dumps(params), headers=headers, auth=auth)
            # strict codes due to odd behavior in past
            if response.status_code not in [200, 201]:
                try:
                    output = response.json()
                except:
                    output = response.text
                error = False
                if output.get('errormsg'):
                    error = output.get('errormsg')
                elif output.get('data').get('errormsg'):
                    error = output.get('data').get('errormsg')
                if error:
                    if 'could not generate ILX identifier' in error:
                        output = None
                    elif 'already exists' in error.lower():
                        print(error)
                        output = {'data':{'term':{}}}
                    else:
                        print('IN CATCH')
                        problem = str(output)
                        exit(str(problem) + ' with status code [' +
                            str(response.status) + '] with params:' + str(data))
                else:
                    print('OUT CATCH')
                    problem = str(output)
                    exit(str(problem) + ' with status code [' +
                        str(response.status) + '] with params:' + str(data))

            else:
                output = response.json()
                error = False
                if output.get('error msg'):
                    error = output['errormsg']
                # Duplicates; don't exit
                elif output.get('data').get('errormsg'):
                    error = output['data']['errormsg']
                if error:
                    print(error)
                    output = {'failed':data}
                else:
                    output = output['data']

            if _print:
                try:
                    print(i, output['label'])
                except:
                    print(i, output)

            outputs.append(output)

        return outputs

    def get(self,
            urls=False,
            LIMIT=25,
            action='Getting Info',
            _print=True,
            crawl=False):
        if crawl:
            return self.crawl_get(urls)

        async def get_single(url, session, auth):
            async with session.get(url) as response:
                if response.status not in [200, 201]:
                    try:
                        output = await response.json()
                    except:
                        output = await response.text()
                    problem = str(output)
                    exit(
                        str(problem) + ' with status code [' +
                        str(response.status) + ']')
                output = await response.json(content_type=None)
                try:
                    try:
                        output = {
                            int(output['data']['id']): output['data']
                        }  # terms
                    except:
                        output = {
                            int(output['data'][0]['tid']): output['data']
                        }  # annotations
                except:
                    print('Not able to get output')
                    exit(output)
                return output

        async def get_all(urls, connector, loop):
            if _print:
                print('=== {0} ==='.format(action))
            tasks = []
            auth = BasicAuth('scicrunch', 'perl22(query)')
            async with ClientSession(
                    connector=connector, loop=loop, auth=auth) as session:
                for i, url in enumerate(urls):
                    task = asyncio.ensure_future(get_single(url, session, auth))
                    tasks.append(task)
                return (await asyncio.gather(*tasks))

        connector = TCPConnector(
            limit=LIMIT
        )  # rate limiter; should be between 20 and 80; 100 maxed out server
        loop = asyncio.get_event_loop()  # event loop initialize
        future = asyncio.ensure_future(
            get_all(urls, connector, loop))  # tasks to do; data is in json format [{},]
        outputs = loop.run_until_complete(future)  # loop until done
        return {k: v for keyval in outputs for k, v in keyval.items()}

    def post(
        self,
        data: list,
        LIMIT: int = 20,
        action: str = 'Pushing Info',
        _print: bool = True,
        crawl: bool = False):

        if crawl: return self.crawl_post(data, _print=_print)

        async def post_single(url, data, session, i):
            # data.update({
            #     'batch-elastic': 'True'
            # })  # term should be able to handle it now
            data = json.dumps({
                **{'key': self.api_key, },
                **data,
            })
            headers = {'Content-type': 'application/json'}

            limit = 0
            output = {}
            while not output and limit < 100:

                async with session.post(url, data=data, headers=headers) as response:

                    # strict codes due to odd behavior in past
                    if response.status not in [200, 201]:
                        try:
                            output = await response.json()
                        except:
                            output = await response.text()

                        error = False
                        if output.get('errormsg'):
                            error = output.get('errormsg')
                        elif output.get('data').get('errormsg'):
                            error = output.get('data').get('errormsg')
                        if error:
                            if 'could not generate ILX identifier' in error:
                                output = None
                            elif 'already exists' in error:
                                print(error)
                                output = {'data':{'term':{}}}
                            else:
                                print('IN CATCH')
                                problem = str(output)
                                exit(str(problem) + ' with status code [' +
                                    str(response.status) + '] with params:' + str(data))
                                output = {'data':{'term':{}}}
                        else:
                            print('OUT CATCH')
                            problem = str(output)
                            exit(str(problem) + ' with status code [' +
                                str(response.status) + '] with params:' + str(data))
                            output = {'data':{'term':{}}}

                    # Missing required fields I didn't account for OR Duplicates.
                    else:
                        # allows NoneTypes to pass
                        output = await response.json(content_type=None)

                        if not output:
                            print(response.status)
                            output = None

                        # Duplicates
                        elif output.get('data').get('errormsg'):
                            print(output.get('data').get('errormsg'))
                            # print(response.status)
                            # print(data) # TODO: its hitting here and idk why


            if _print:
                try:
                    print(i, output['data']['label'])
                except:
                    print(i, output['data'])

            return output['data']

        async def bound_post(sem, url, data, session, i):
            async with sem:
                await post_single(url, data, session, i)

        async def post_all(total_data, connector, loop):
            tasks = []
            sem = asyncio.Semaphore(50)

            auth = BasicAuth('scicrunch', 'perl22(query)')
            async with ClientSession(connector=connector, auth=auth) as session:
                if _print:
                    print('=== {0} ==='.format(action))
                for i, tupdata in enumerate(total_data):
                    url, data = tupdata
                    task = asyncio.ensure_future(
                        post_single(url, data, session, i))
                    tasks.append(task)
                outputs = await asyncio.gather(*tasks)
                return outputs

        connector = TCPConnector(
            limit=LIMIT
        )  # rate limiter; should be between 20 and 80; 100 maxed out server
        loop = asyncio.get_event_loop()  # event loop initialize
        future = asyncio.ensure_future(
            post_all(data, connector, loop))  # tasks to do; data is in json format [{},]
        output = loop.run_until_complete(future)  # loop until done
        return output

    def identifierSearches(self,
                           ids=None,
                           LIMIT=25,
                           _print=True,
                           crawl=False):
        """parameters( data = "list of term_ids" )"""
        url_base = self.base_url + '/api/1/term/view/{id}' + '?key=' + self.api_key
        urls = [url_base.format(id=str(_id)) for _id in ids]
        return self.get(
            urls=urls,
            LIMIT=LIMIT,
            action='Searching For Terms',
            crawl=crawl,
            _print=_print)

    def ilxSearches(self,
                    ilx_ids=None,
                    LIMIT=25,
                    _print=True,
                    crawl=False):
        """parameters( data = "list of ilx_ids" )"""
        url_base = self.base_url + "/api/1/ilx/search/identifier/{identifier}?key={APIKEY}"
        urls = [url_base.format(identifier=ilx_id.replace('ILX:', 'ilx_'), APIKEY=self.api_key) for ilx_id in ilx_ids]
        return self.get(
            urls=urls,
            LIMIT=LIMIT,
            action='Searching For Terms',
            crawl=crawl,
            _print=_print)

    def updateTerms(self, data:list, LIMIT:int=20, _print:bool=True, crawl:bool=False,) -> list:
        """ Updates existing entities

            Args:
                data:
                    needs:
                        id              <str>
                        ilx_id          <str>
                    options:
                        definition      <str> #bug with qutations
                        superclasses    [{'id':<int>}]
                        type            term, cde, anntation, or relationship <str>
                        synonyms         {'literal':<str>}
                        existing_ids    {'iri':<str>,'curie':<str>','change':<bool>, 'delete':<bool>}
                LIMIT:
                    limit of concurrent
                _print:
                    prints label of data presented
                crawl:
                    True: Uses linear requests.
                    False: Uses concurrent requests from the asyncio and aiohttp modules

            Returns:
                List of filled in data parallel with the input data. If any entity failed with an
                ignorable reason, it will return empty for the item in the list returned.
            """

        url_base = self.base_url + '/api/1/term/edit/{id}'
        merged_data = []

        # PHP on the server is is LOADED with bugs. Best to just duplicate entity data and change
        # what you need in it before re-upserting the data.
        old_data = self.identifierSearches(
            [d['id'] for d in data], # just need the ids
            LIMIT = LIMIT,
            _print = _print,
            crawl = crawl,
        )

        for d in data: # d for dictionary
            url = url_base.format(id=str(d['id']))

            # Reason this exists is to avoid contradictions in case you are using a local reference
            if d['ilx'] != old_data[int(d['id'])]['ilx']:
                print(d['ilx'], old_data[int(d['id'])]['ilx'])
                exit('You might be using beta insead of production!')

            merged = scicrunch_client_helper.merge(new=d, old=old_data[int(d['id'])])
            merged = scicrunch_client_helper.superclasses_bug_fix(merged)  # BUG: superclass output diff than input needed
            merged_data.append((url, merged))

        resp = self.post(
            merged_data,
            LIMIT = LIMIT,
            action = 'Updating Terms', # forced input from each function
            _print = _print,
            crawl = crawl,
        )
        return resp

    def addTerms(self, data, LIMIT=25, _print=True, crawl=False):
        """
            need:
                    label           <str>
                    type            term, cde, anntation, or relationship <str>
            options:
                    definition      <str> #bug with qutations
                    superclasses    [{'id':<int>}]
                    synonyms        [{'literal':<str>}]
                    existing_ids    [{'iri':<str>,'curie':<str>'}]
                    ontologies      [{'id':<int>}]

        [{'type':'term', 'label':'brain'}]
        """
        needed = set([
            'label',
            'type',
        ])

        url_base = self.base_url + '/api/1/ilx/add'
        terms = []
        for d in data:
            if (set(list(d)) & needed) != needed:
                exit('You need keys: '+ str(needed - set(list(d))))

            if not d.get('label') or not d.get('type'): # php wont catch empty type!
                exit('=== Data is missing label or type! ===')

            d['term'] = d.pop('label') # ilx only accepts term, will need to replaced back
            #d['batch-elastic'] = 'True' # term/add and edit should be ready now
            terms.append((url_base, d))

        primer_responses = self.post(
            terms,
            action='Priming Terms',
            LIMIT=LIMIT,
            _print=_print,
            crawl=crawl)

        ilx = {}
        for primer_response in primer_responses:
            primer_response['term'] = primer_response['term'].replace('&#39;', "'")
            primer_response['term'] = primer_response['term'].replace('&#34;', '"')
            primer_response['label'] = primer_response.pop('term')
            ilx[primer_response['label'].lower()] = primer_response

        url_base = self.base_url + '/api/1/term/add'
        terms = []
        for d in data:
            d['label'] = d.pop('term')
            d = scicrunch_client_helper.superclasses_bug_fix(d)
            if not ilx.get(d['label'].lower()): # ilx can be incomplete if errored term
                continue
            try:
                d.update({'ilx': ilx[d['label'].lower()]['ilx']})
            except:
                d.update({'ilx': ilx[d['label'].lower()]['fragment']})
            terms.append((url_base, d))

        return self.post(
            terms,
            action='Adding Terms',
            LIMIT=LIMIT,
            _print=_print,
            crawl=crawl)

    def addAnnotations(self,
                       data,
                       LIMIT=25,
                       _print=True,
                       crawl=False,):

        need = set([
            'tid',
            'annotation_tid',
            'value',
            'term_version',
            'annotation_term_version',
        ])

        url_base = self.base_url + '/api/1/term/add-annotation'
        annotations = []
        for annotation in data:
            annotation.update({
                'term_version': annotation['term_version'],
                'annotation_term_version': annotation['annotation_term_version'],
                'batch-elastic': 'True',
            })

            if (set(list(annotation)) & need) != need:
                exit('You need keys: '+ str(need - set(list(annotation))))

            annotations.append((url_base, annotation))

        return self.post(
            annotations,
            LIMIT = LIMIT,
            action = 'Adding Annotations',
            _print = _print,
            crawl = crawl,
        )

    def getAnnotations_via_tid(self,
                               tids,
                               LIMIT=25,
                               _print=True,
                               crawl=False):
        """
        tids = list of term ids that possess the annoations
        """
        url_base = self.base_url + \
            '/api/1/term/get-annotations/{tid}?key=' + self.api_key
        urls = [url_base.format(tid=str(tid)) for tid in tids]
        return self.get(urls,
                        LIMIT=LIMIT,
                        _print=_print,
                        crawl=crawl)

    def getAnnotations_via_id(self,
                              annotation_ids,
                              LIMIT=25,
                              _print=True,
                              crawl=False):
        """tids = list of strings or ints that are the ids of the annotations themselves"""
        url_base = self.base_url + \
            '/api/1/term/get-annotation/{id}?key=' + self.api_key
        urls = [
            url_base.format(id=str(annotation_id))
            for annotation_id in annotation_ids
        ]
        return self.get(urls, LIMIT=LIMIT, _print=_print, crawl=crawl)

    def updateAnnotations(self,
                          data,
                          LIMIT=25,
                          _print=True,
                          crawl=False,):
        """data = [{'id', 'tid', 'annotation_tid', 'value', 'comment', 'upvote', 'downvote',
        'curator_status', 'withdrawn', 'term_version', 'annotation_term_version', 'orig_uid',
        'orig_time'}]
        """
        url_base = self.base_url + \
            '/api/1/term/edit-annotation/{id}'  # id of annotation not term id
        annotations = self.getAnnotations_via_id([d['id'] for d in data],
                                                 LIMIT=LIMIT,
                                                 _print=_print,
                                                 crawl=crawl)

        annotations_to_update = []
        for d in data:
            annotation = annotations[int(d['id'])]
            annotation.update({**d})
            url = url_base.format(id=annotation['id'])
            annotations_to_update.append((url, annotation))
        self.post(annotations_to_update,
                  LIMIT=LIMIT,
                  action='Updating Annotations',
                  _print=_print,
                  crawl=crawl)

    def deleteAnnotations(self,
                          annotation_ids,
                          LIMIT=25,
                          _print=True,
                          crawl=False,):
        """data = list of ids"""
        url_base = self.base_url + \
            '/api/1/term/edit-annotation/{annotation_id}'  # id of annotation not term id; thx past troy!
        annotations = self.getAnnotations_via_id(annotation_ids,
                                                 LIMIT=LIMIT,
                                                 _print=_print,
                                                 crawl=crawl)
        annotations_to_delete = []
        for annotation_id in annotation_ids:
            annotation = annotations[int(annotation_id)]
            params = {
                'value': ' ',  # for delete
                'annotation_tid': ' ',  # for delete
                'tid': ' ',  # for delete
                'term_version': '1',
                'annotation_term_version': '1',
            }
            url = url_base.format(annotation_id=annotation_id)
            annotation.update({**params})
            annotations_to_delete.append((url, annotation))
        return self.post(annotations_to_delete,
                         LIMIT=LIMIT,
                         _print=_print,
                         crawl=crawl)

    def addRelationships(
        self,
        data: list,
        LIMIT: int = 20,
        _print: bool = True,
        crawl: bool = False,
        ) -> list:
        """
        data = [{
            "term1_id", "term2_id", "relationship_tid",
            "term1_version", "term2_version",
            "relationship_term_version",}]
        """
        url_base = self.base_url + '/api/1/term/add-relationship'
        relationships = []
        for relationship in data:
            relationship.update({
                'term1_version': relationship['term1_version'],
                'term2_version': relationship['term2_version'],
                'relationship_term_version': relationship['relationship_term_version']
            })
            relationships.append((url_base, relationship))
        return self.post(
            relationships,
            LIMIT = LIMIT,
            action = 'Adding Relationships',
            _print = _print,
            crawl = crawl,
        )

    def deleteTermsFromElastic(self,
                               ilx_ids,
                               LIMIT=25,
                               _print=True,
                               crawl=True):
        url = self.base_url + \
            '/api/1/term/elastic/delete/{ilx_id}?key=' + self.api_key
        data = [(url.format(ilx_id=str(ilx_id)), {}) for ilx_id in ilx_ids]
        return self.post(
            data, LIMIT=LIMIT, _print=_print, crawl=crawl)

    def addTermsToElastic(
        self,
        tids,
        LIMIT = 50,
        _print = True,
        crawl = True
        ) -> list:
        url = self.base_url + '/api/1/term/elastic/upsert/{tid}?key=' + self.api_key
        data = [(url.format(tid=str(tid)), {}) for tid in tids]
        return self.post(
            data,
            LIMIT = LIMIT,
            _print=_print,
            crawl=crawl
        )

    def deprecate_entity(
        self,
        ilx_id: str,
        note = None,
        ) -> None:
        """ Tagged term in interlex to warn this term is no longer used

        There isn't an proper way to delete a term and so we have to mark it so I can
        extrapolate that in mysql/ttl loads.

        Args:
            term_id: id of the term of which to be deprecated
            term_version: version of the term of which to be deprecated

        Example: deprecateTerm('ilx_0101431', '6')
        """

        term_id, term_version = [(d['id'], d['version'])
            for d in self.ilxSearches([ilx_id], crawl=True, _print=False).values()][0]

        annotations = [{
            'tid': term_id,
            'annotation_tid': '306375', # id for annotation "deprecated"
            'value': 'True',
            'term_version': term_version,
            'annotation_term_version': '1', # term version for annotation "deprecated"
        }]
        if note:
            editor_note = {
                'tid': term_id,
                'annotation_tid': '306378', # id for annotation "editorNote"
                'value': note,
                'term_version': term_version,
                'annotation_term_version': '1', # term version for annotation "deprecated"
            }
            annotations.append(editor_note)
        self.addAnnotations(annotations, crawl=True, _print=False)
        print(annotations)

    def add_editor_note(
        self,
        ilx_id: str,
        note = None,
        ) -> None:
        """ Tagged term in interlex to warn this term is no longer used

        There isn't an proper way to delete a term and so we have to mark it so I can
        extrapolate that in mysql/ttl loads.

        Args:
            term_id: id of the term of which to be deprecated
            term_version: version of the term of which to be deprecated

        Example: deprecateTerm('ilx_0101431', '6')
        """

        term_id, term_version = [(d['id'], d['version'])
            for d in self.ilxSearches([ilx_id], crawl=True, _print=False).values()][0]

        editor_note = {
            'tid': term_id,
            'annotation_tid': '306378', # id for annotation "editorNote"
            'value': note,
            'term_version': term_version,
            'annotation_term_version': '1', # term version for annotation "deprecated"
        }
        self.addAnnotations([editor_note], crawl=True, _print=False)
        print(editor_note)

    def add_merge_properties(
        self,
        ilx1_id: str,
        ilx2_id: str,
        ) -> None:

        term1_id, term1_version = [(d['id'], d['version'])
            for d in self.ilxSearches([ilx1_id], crawl=True, _print=False).values()][0]
        term2_id, term2_version = [(d['id'], d['version'])
            for d in self.ilxSearches([ilx2_id], crawl=True, _print=False).values()][0]

        replaced_info = {
            "term1_id": term1_id,
            "term2_id": term2_id,
            "relationship_tid": '306376', # "replacedBy" id ,
            "term1_version": term1_version,
            "term2_version": term2_version,
            "relationship_term_version": '1', # "replacedBy" version,
        }
        self.addRelationships([replaced_info], crawl=True, _print=False)
        print(replaced_info)

        reason_info = {
            'tid': term1_id,
            'annotation_tid': '306377', # id for annotation "obsReason"
            'value': 'http://purl.obolibrary.org/obo/IAO_0000227', # termsMerged rdf iri
            'term_version': term1_version,
            'annotation_term_version': '1', # term version for annotation "obsReason"
        }
        self.addAnnotations([reason_info], crawl=True, _print=False)
        print(reason_info)

    def add_syn_relationship_properties(
        self,
        ilx1_id: str,
        ilx2_id: str,
        ) -> None:

        term1_id, term1_version = [(d['id'], d['version'])
            for d in self.ilxSearches([ilx1_id], crawl=True, _print=False).values()][0]
        term2_id, term2_version = [(d['id'], d['version'])
            for d in self.ilxSearches([ilx2_id], crawl=True, _print=False).values()][0]

        replaced_info = {
            "term1_id": term1_id,
            "term2_id": term2_id,
            "relationship_tid": '306379', # "isTreatedAsSynonymOf" id ,
            "term1_version": term1_version,
            "term2_version": term2_version,
            "relationship_term_version": '1', # "isTreatedAsSynonymOf" version,
        }
        self.addRelationships([replaced_info], crawl=True, _print=False)
        print(replaced_info)

    def addOntology(self, ontology_url:str) -> List[dict]:
        add_ontology_url = self.base_url + '/api/1/term/ontology/add'
        data = json.dumps({
            'url': ontology_url,
            'key': self.api_key,
        })
        response = r.post(add_ontology_url, data=data, headers={'Content-type': 'application/json'})
        print(response.status_code)
        try:
            return response.json()
        except:
            return response.text

    def force_add_term(self, entity: dict):
        """ Need to add an entity that already has a label existing in InterLex?
            Well this is the function for you!

            entity:
                need:
                        label           <str>
                        type            term, cde, pde, fde, anntation, or relationship <str>
                options:
                        definition      <str>
                        superclasses    [{'id':<int>}]
                        synonyms        [{'literal':<str>}]
                        existing_ids    [{'iri':<str>,'curie':<str>'}]
                        ontologies      [{'id':<int>}]

            example:
                entity = [{
                    'type':'term',
                    'label':'brain',
                    'existing_ids': [{
                        'iri':'http://ncbi.org/123',
                        'curie':'NCBI:123'
                    }]
                }]
        """
        needed = set([
            'label',
            'type',
        ])
        url_ilx_add = self.base_url + '/api/1/ilx/add'
        url_term_add = self.base_url + '/api/1/term/add'
        url_term_update = self.base_url + '/api/1/term/edit/{id}'

        if (set(list(entity)) & needed) != needed:
            exit('You need keys: '+ str(needed - set(list(d))))

        # to ensure uniqueness
        random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=25))
        real_label = entity['label']
        entity['label'] = entity['label'] + '_' + random_string

        entity['term'] = entity.pop('label') # ilx only accepts term, will need to replaced back
        primer_response = self.post([(url_ilx_add, entity.copy())], _print=False, crawl=True)[0]
        entity['label'] = entity.pop('term')
        entity['ilx'] = primer_response['fragment'] if primer_response.get('fragment') else primer_response['ilx']
        entity = scicrunch_client_helper.superclasses_bug_fix(entity)

        response = self.post([(url_term_add, entity.copy())], _print=False, crawl=True)[0]

        old_data = self.identifierSearches(
            [response['id']], # just need the ids
            _print = False,
            crawl = True,
        )[response['id']]

        old_data['label'] = real_label
        entity = old_data.copy()
        url_term_update = url_term_update.format(id=entity['id'])
        return self.post([(url_term_update, entity)], _print=False, crawl=True)

def main():

    sci = scicrunch(
        api_key=os.environ.get('SCICRUNCH_API_KEY'),
        base_url=os.environ.get('SCICRUNCH_BASEURL_BETA'),
    )
    entity = {
        'label': 'test_force_add_term',
        'type': 'term',
    }
    print(sci.force_add_term(entity))
    update_entity = {'id': '305199', 'ilx': 'tmp_0382117', 'label': 'test_force_add_term', 'key': 'Mf8f6S5gD6cy6cuRWMyjUeLGxUPfo0SZ'}
    # print(sci.updateTerms([update_entity], _print=False, crawl=True))

if __name__ == '__main__':
    main()
