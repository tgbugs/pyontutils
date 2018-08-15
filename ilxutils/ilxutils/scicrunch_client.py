import pandas as pd
import requests as r
import json
from sqlalchemy import create_engine, inspect, Table, Column
import numpy as np
import asyncio
from sys import exit
import math as m
import time
from IPython import embed
from aiohttp import ClientSession, TCPConnector, BasicAuth
from ilxutils.args_reader import read_args
from collections import defaultdict, namedtuple
import ilxutils.dictlib as dictlib
from ilxutils.interlex_sql import IlxSql
from pathlib import Path as p
'''
    Get functions need a list of term ids
    Post functions need a list of dictionaries with their needed/optional keys & values

    identifierSearches          ids, LIMIT=50, _print=True, crawl=False
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


class scicrunch():
    def __init__(self, api_key, base_path, db_url, auth=('None', 'None')):
        self.key = api_key
        self.base_path = base_path
        self.auth = BasicAuth(auth)
        # must be > 6691 items to be worth it as limit=25
        self.sql = IlxSql(db_url=db_url)

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
                **{'key': self.key, },
                **data,
            }
            auth = ('scicrunch',
                    'perl22(query)')  # needed for test2.scicrunch.org
            headers = {'Content-type': 'application/json'}
            response = r.post(url, data=json.dumps(params), headers=headers, auth=auth)

            # strict codes due to odd behavior in past
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

            if _print:
                try:
                    print(i, output['data']['label'])
                except:
                    print(i, output['data'])

            outputs.append(output['data'])

        return outputs

    def get(self,
            urls=False,
            LIMIT=50,
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

    def post(self,
             data,
             LIMIT=50,
             action='Pushing Info',
             _print=True,
             crawl=False):
        if crawl:
            return self.crawl_post(data, _print=_print)

        async def post_single(url, data, session, i):
            if 'Annotation' in action:
                data.update({
                    'batch-elastic': 'True'
                })  # term endpoints cant handle this key yet
            data = json.dumps({
                **{'key': self.key, },
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
                            output = await response.text
                        problem = str(output)
                        exit(
                            str(problem) + ' with status code [' +
                            str(response.status) + '] with params:' + str(data))

                    else:
                        text = await response.text()

                    if not text:  # text doesnt break like json does... I know this looks bad
                        output = None

                    else:
                        # allows NoneTypes to pass
                        output = await response.json(content_type=None)

                        if not output:
                            output = None

                        elif output.get('errormsg') == 'could not generate ILX identifier':
                            output = None

                        # Duplicates
                        elif output.get('data').get('errormsg'):
                            print(data)
                            # exit(output) # TODO: might want to expand this for server crashes

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
                           LIMIT=50,
                           _print=True,
                           crawl=False):
        """parameters( data = "list of term_ids" )"""
        url_base = self.base_path + '/api/1/term/view/{id}' + '?key=' + self.key
        urls = [url_base.format(id=str(_id)) for _id in ids]
        return self.get(
            urls=urls,
            LIMIT=LIMIT,
            action='Searching For Terms',
            crawl=crawl,
            _print=_print)

    def updateTerms(self,
                    data,
                    LIMIT=50,
                    _print=True,
                    crawl=False,
                    use_sql=False,):
        """
            need:
                    id              <int/str>
            options:
                    definition      <str> #bug with qutations
                    superclasses    [{'id':<int>}]
                    type            term, cde, anntation, or relationship <str>
                    synonym         {'literal':<str>}
                    existing_ids    {'iri':<str>,'curie':<str>','change':<bool>, 'delete':<bool>}
        """
        old_data = self.identifierSearches(
            [d['id'] for d in data], LIMIT=LIMIT, _print=_print, crawl=crawl)
        url_base = self.base_path + '/api/1/term/edit/{id}'
        merged_data = []
        for d in data:
            url = url_base.format(id=str(d['id']))
            merged = dictlib.merge(new=d, old=old_data[int(d['id'])])
            merged = dictlib.superclasses_bug_fix(merged)  # BUG
            merged_data.append((url, merged))
        return self.post(
            merged_data,
            LIMIT=LIMIT,
            action='Updating Terms',
            _print=_print,
            crawl=crawl)

    def addTerms(self, data, LIMIT=50, _print=True, crawl=False, use_sql=False):
        """
            need:
                    label           <str>
                    type            term, cde, anntation, or relationship <str>
            options:
                    definition      <str> #bug with qutations
                    superclasses    [{'id':<int>}]
                    synonym         {'literal':<str>}
                    existing_ids    {'iri':<str>,'curie':<str>','change':<bool>, 'delete':<bool>}
        """
        needed = set([
            'label',
            'type',
        ])

        url_base = self.base_path + '/api/1/ilx/add'

        terms = []
        for d in data:
            if (set(list(d)) & needed) != needed:
                exit('You need keys: '+ str(needed - set(list(d))))

            if not d.get('label') or not d.get('type'): # php wont catch empty type!
                exit('=== Data is missing label or type! ===')

            d['term'] = d.pop('label')
            terms.append((url_base, d))

        ilx = self.post(
            terms,
            action='Priming Terms',
            LIMIT=LIMIT,
            _print=_print,
            crawl=crawl)

        ilx = {d['term']: d for d in ilx}

        url_base = self.base_path + '/api/1/term/add'
        terms = []
        for d in data:
            d['label'] = d.pop('term')
            d = dictlib.superclasses_bug_fix(d)
            try:
                d.update({'ilx': ilx[d['label']]['ilx']})
            except:
                d.update({'ilx': ilx[d['label']]['fragment']})
            terms.append((url_base, d))

        return self.post(
            terms,
            action='Adding Terms',
            LIMIT=LIMIT,
            _print=_print,
            crawl=crawl)

    def addAnnotations(self,
                       data,
                       LIMIT=50,
                       _print=True,
                       crawl=False,
                       use_sql=False):

        need = set([
            'tid',
            'annotation_tid',
            'value',
            'term_version',
            'annotation_term_version',
        ])

        url_base = self.base_path + '/api/1/term/add-annotation'
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

        return self.post(annotations,
                         LIMIT=LIMIT,
                         action='Adding Annotations',
                         _print=_print,
                         crawl=crawl)

    def getAnnotations_via_tid(self,
                               tids,
                               LIMIT=50,
                               _print=True,
                               crawl=False):
        """
        tids = list of term ids that possess the annoations
        """
        url_base = self.base_path + \
            '/api/1/term/get-annotations/{tid}?key=' + self.key
        urls = [url_base.format(tid=str(tid)) for tid in tids]
        return self.get(urls,
                        LIMIT=LIMIT,
                        _print=_print,
                        crawl=crawl)

    def getAnnotations_via_id(self,
                              annotation_ids,
                              LIMIT=50,
                              _print=True,
                              crawl=False):
        """tids = list of strings or ints that are the ids of the annotations themselves"""
        url_base = self.base_path + \
            '/api/1/term/get-annotation/{id}?key=' + self.key
        urls = [
            url_base.format(id=str(annotation_id))
            for annotation_id in annotation_ids
        ]
        return self.get(urls, LIMIT=LIMIT, _print=_print, crawl=crawl)

    def updateAnnotations(self,
                          data,
                          LIMIT=50,
                          _print=True,
                          crawl=False,
                          use_sql=False):
        """data = [{'id', 'tid', 'annotation_tid', 'value', 'comment', 'upvote', 'downvote',
        'curator_status', 'withdrawn', 'term_version', 'annotation_term_version', 'orig_uid',
        'orig_time'}]
        """
        url_base = self.base_path + \
            '/api/1/term/edit-annotation/{id}'  # id of annotation not term id
        if use_sql:
            annotations = self.sql.get_client_ready_annos([d['id'] for d in data])
        else:
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
                          LIMIT=50,
                          _print=True,
                          crawl=False,):
        """data = list of tids"""
        url_base = self.base_path + \
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

    def addRelationships(self,
                         data,
                         HELP=False,
                         LIMIT=50,
                         _print=True,
                         crawl=False,
                         use_sql=False):
        """
        data = [{
            "term1_id", "term2_id", "relationship_tid",
            "term1_version", "term2_version",
            "relationship_term_version",}]
        """
        url_base = self.base_path + '/api/1/term/add-relationship'
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
            LIMIT=LIMIT,
            action='Adding Relationships',
            _print=True,
            crawl=False)

    def deleteTermsFromElastic(self,
                               ilx_ids,
                               LIMIT=50,
                               _print=True,
                               crawl=True):
        url = self.base_path + \
            '/api/1/term/elastic/delete/{ilx_id}?key=' + self.key
        data = [(url.format(ilx_id=str(ilx_id)), {}) for ilx_id in ilx_ids]
        return self.post(
            data, LIMIT=LIMIT, _print=_print, crawl=crawl)

    def addTermsToElastic(self,
                          tids,
                          LIMIT=50,
                          _print=True,
                          crawl=True):
        url = self.base_path + \
            '/api/1/term/elastic/upsert/{tid}?key=' + self.key
        data = [(url.format(tid=str(tid)), {}) for tid in tids]
        return self.post(
            data, LIMIT=LIMIT, _print=_print, crawl=crawl)


def main():
    args = read_args(api_key=p.home() / 'keys/production_api_scicrunch_key.txt',
                     db_url=p.home() / 'keys/beta_engine_scicrunch_key.txt', beta=True, cafe=True)
    # args = read_args(api_key=p.home() / 'keys/production_api_scicrunch_key.txt',
    #                  db_url=p.home() / 'keys/production_engine_scicrunch_key.txt', production=True)
    #sql = IlxSql(db_url=args.db_url)
    sci = scicrunch(api_key=args.api_key,
                    base_path=args.base_path, db_url=args.db_url)
    #data = ['ilx_0115064']
    #data = [{'id':4511, 'existing_ids':{'iri': 'test2.org/456', 'curie':'test:456'}}]
    annotation_samples = [
    # {
    #     'tid': '1432',
    #     'annotation_tid': '304709',
    #     'value': '\'\'Belliveau JW\'\', Kennedy DN Jr, McKinstry RC, Buchbinder BR, Weisskoff RM, Cohen \nMS, Vevea JM, Brady TJ, Rosen BR. Functional mapping of the human visual cortex\nby magnetic resonance imaging. Science. 1991 Nov 1;254(5032):716-9. PubMed PMID: \n1948051'
    # },
    {
        'tid': '1432',
        'annotation_tid': '304708',
        'value': '<a href="https://www.ncbi.nlm.nih.gov/pubmed/1948051">PMID:1948051</a>',
        'term_version': 1,
        'annotation_term_version' : 1,
    },
    # {
    #     'tid': '1432',
    #     'annotation_tid': '304710',
    #     'value': 'BIRNLEX:2058',
    # }
    ]
    # output = sci.addTerms([
    #     {'label':'PubMed Annotation Source', 'type':'annotation'},
    #     {'label':'PubMed Summary', 'type':'annotation'},
    #     {'label':'PubMed URL', 'type':'annotation'},
    # ], LIMIT=10)
    output = sci.addAnnotations(annotation_samples, crawl=True)
    print(output)

'''
Hoersch D, Otto H, Joshi CP, Borucki B, Cusanovich MA, Heyn MP. Role of a Conserved Salt
Bridge between the PAS Core and the N-Terminal Domain in the Activation of the Photoreceptor
Photoactive Yellow Protein. Biophysical Journal. 2007;93(5):1687-1699. doi:10.1529/biophysj.107.106633.
'''
if __name__ == '__main__':
    main()
