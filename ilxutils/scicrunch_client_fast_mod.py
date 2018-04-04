import pandas as pd
import requests as r
import json
from sqlalchemy import create_engine, inspect, Table, Column
import numpy as np
import asyncio
import sys
import math as m
import progressbar
from aiohttp import ClientSession, TCPConnector, BasicAuth
from args_reader import read_args
from collections import defaultdict, namedtuple
import dictlib
from interlex_sql import interlex_sql

class scicrunch():

    def __init__(self, key, base_path, engine_key, auth=('None','None')):
        self.key = key
        self.base_path = base_path
        self.auth = BasicAuth(auth)
        self.sql = interlex_sql(engine_key=engine_key)

    def createBar(self, maxval):
        return progressbar.ProgressBar(maxval=maxval, \
            widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])

    def get(self, urls, LIMIT=50, action='Getting Info'):
        async def get_single(url, session, auth):
            async with session.get(url) as response:
                if response.status not in [200, 201]:
                    try:
                        output = await response.json()
                    except:
                        output = await response.text()
                    problem = str(output)
                    sys.exit(str(problem)+' with status code ['+str(response.status)+']')
                output = await response.json()
                try:
                    try:
                        output={int(output['data']['id']):output['data']} #terms
                    except:
                        output={int(output['data'][0]['tid']):output['data']} #annotations
                except:
                    return {url:None}
                return output

        async def get_all(urls, connector, loop):
            print('=== {0} ==='.format(action))
            tasks = []
            auth = BasicAuth('scicrunch', 'perl22(query)')
            async with ClientSession(connector=connector, loop=loop, auth=auth) as session:
                bar = self.createBar(len(urls)); bar.start()
                for i, url in enumerate(urls):
                    task = asyncio.ensure_future(get_single(url, session, auth))
                    tasks.append(task)
                    bar.update(i)
                bar.finish()
                return (await asyncio.gather(*tasks))

        connector = TCPConnector(limit=LIMIT) # rate limiter; should be between 20 and 80; 100 maxed out server
        loop = asyncio.get_event_loop() # event loop initialize
        future = asyncio.ensure_future(get_all(urls, connector, loop)) # tasks to do; data is in json format [{},]
        outputs = loop.run_until_complete(future) # loop until done
        return {k:v for keyval in outputs for k, v in keyval.items()}

    def post(self, data, LIMIT=50, action='Pushing Info'):

        async def post_single(url, data, session, i):
            params = {**{'key':self.key}, **data} #**{'batch-elastic':'True'}}
            headers = {'Content-type': 'application/json'}
            async with session.post(url, data=json.dumps(params), headers=headers) as response:
                if response.status not in [200, 201]:
                    try:
                        output = await response.json()
                    except:
                        output = await response.text()
                    problem = str(output)
                    sys.exit(str(problem)+' with status code ['+str(response.status)+'] with params:'+str(params))
                output = await response.json()
                try:
                    print(i, output['data']['label'])
                except:
                    print(i, output['data'])
                return output['data']

        async def post_all(total_data, connector, loop):
            tasks = []
            auth = BasicAuth('scicrunch', 'perl22(query)')
            async with ClientSession(connector=connector, loop=loop, auth=auth) as session:
                print('=== {0} ==='.format(action))
                bar = self.createBar(len(total_data)); bar.start()
                for i, tupdata in enumerate(total_data):
                    url, data = tupdata
                    task = asyncio.ensure_future(post_single(url, data, session, i)) #FIXME had to copy to give new address
                    tasks.append(task)
                    bar.update(i)
                bar.finish()
                return (await asyncio.gather(*tasks))

        connector = TCPConnector(limit=LIMIT) # rate limiter; should be between 20 and 80; 100 maxed out server
        loop = asyncio.get_event_loop() # event loop initialize
        future = asyncio.ensure_future(post_all(data, connector, loop)) # tasks to do; data is in json format [{},]
        outputs = loop.run_until_complete(future) # loop until done
        return outputs

    def identifierSearches(self, ids=None, HELP=False, LIMIT=50):
        if HELP:
            sys.exit('parameters( data = "list of term_ids" )')

        url_base = self.base_path + '/api/1/term/view/{0}' + '?key=' + self.key
        urls = [url_base.format(str(tid)) for tid in ids]
        term_data = self.get(urls=urls, LIMIT=LIMIT, action='Searching For Terms')
        return term_data

    '''need    {'id'}'''
    '''option  {definition, superclasses={'id'}, type, synonym={'literal'}
                existing_ids={'iri','prefix','change'=T/F, delete=T/F}}'''
    def updateTerms(self, data, HELP=False, LIMIT=50, sql=False):
        if HELP:
            sys.exit('data = "list of term dicts"')

        #label_to_id = self.sql.get_labels_to_ids_dict()
        #for d in data:
        #    if not d.get('id'):
        #        d['id'] = label_to_id[d['label'].lower().strip()]

        if sql:
            old_data = dictlib.fill_data(data, self.sql)
        else:
            old_data = self.identifierSearches([d['id'] for d in data])

        #print('old', old_data, '\n', 'end')

        url_base = self.base_path + '/api/1/term/edit/{0}'
        merged_data = []
        for d in data:
            url = url_base.format(str(d['id']))
            merged = dictlib.merge(new=d, old=old_data[int(d['id'])])
            merged = dictlib.superclasses_bug_fix(merged) #BUG
            merged_data.append((url, merged))

        self.post(merged_data, LIMIT=LIMIT, action='Updating Terms')

    def addTerms(self, data, HELP=False, LIMIT=50, sql=False):

        url_base = self.base_path + '/api/1/ilx/add'
        terms = []
        for d in data:
            terms.append((url_base, d))
        ilx = self.post(terms, LIMIT=LIMIT)
        ilx = {d['term']:d for d in ilx}

        url_base = self.base_path + '/api/1/term/add'
        terms = []
        for d in data:
            d['label'] = d.pop('term')
            try:
                d.update({'ilx':ilx[d['label']]['ilx']})
            except:
                d.update({'ilx':ilx[d['label']]['fragment']})
            terms.append((url_base, d))
        self.post(terms, LIMIT=LIMIT, action='Adding Terms')

    """ {'tid':'', 'annotation_tid':'', 'value':''} """
    def addAnnotations(self, data, HELP=False, LIMIT=50, sql=False):
        if HELP:
            sys.exit('data = list of dict {"tid","annotation_tid","value"}')

        url_base = self.base_path + '/api/1/term/add-annotation'
        annotations = []
        for annotation in data:
            annotation.update({
                'term_version':'1',
                'annotation_term_version':'1',
                'batch-elastic':'True',
            })
            annotations.append((url_base, annotation))
        self.post(annotations, LIMIT=LIMIT, action='Adding Annotations')

    def getAnnotations(self, tids, HELP=False, LIMIT=50):
        if HELP:
            sys.exit('data = list of tids')

        url_base = self.base_path + '/api/1/term/get-annotations/{0}' + '?key=' + self.key
        urls = [url_base.format(str(tid)) for tid in tids]
        return self.get(urls, LIMIT=LIMIT)

    def updateAnntationValues(self, data, HELP=False, LIMIT=50):
        if HELP:
            sys.exit('data = list of dict {"tid","annotation_tid","value"}')

        url_base = self.base_path + '/api/1/term/edit-annotation/{0}' # id of annotation not term id
        term_annotations = self.getAnnotations([d['tid'] for d in data])

        annotations_to_update = []
        for d in data:
            for annotation in term_annotations[d['tid']]:
                if str(annotation['annotation_tid']) == str(d['annotation_tid']):
                    annotation['value'] = d['value']
                    url = url_base.format(annotation['id'])
                    annotations_to_update.append((url, annotation))
        print(annotations_to_update)
        self.post(annotations_to_update, LIMIT=LIMIT)

    def updateAnntationType(self, data, HELP=False, LIMIT=50):
        if HELP:
            sys.exit('data = list of dict {"tid","annotation_tid","value"}')

        url_base = self.base_path + '/api/1/term/edit-annotation/{0}' # id of annotation not term id
        term_annotations = getAnnotations([d['tid'] for d in data])
        annotations_to_update = []
        for d in data:
            for annotation in term_annotations[d['tid']]:
                if annotation['value'] == d['value']:
                    annotation['annotation_tid'] = d['annotation_tid']
                    url = url_base.format(annotation['id'])
                    annotations_to_update.append((url, annotation))

        self.post(annotations_to_update, LIMIT=LIMIT)

    def deleteAnnotations(self, tids, HELP=False, LIMIT=50):
        if HELP:
            sys.exit('data = list of tids')

        url_base = self.base_path + '/api/1/term/edit-annotation/{0}' # id of annotation not term id
        term_annotations = getAnnotations(tids)
        annotations_to_delete = []
        for tid in tids:
            for annotation in term_annotations[tid]:
                params = {
                    'value':' ', #for delete
                    'annotation_tid':' ', #for delete
                    'tid':' ', #for delete
                    'term_version':'1',
                    'key':self.key,
                    'annotation_term_version':'1',
                }
                url = url_base.format(annotation['id'])
                annotations_to_update.append((url, params))

        self.post(annotations_to_delete, LIMIT=LIMIT)

    """
        Adds relationships by connection 2 term ids with the relationship ids
        use -> [{"term_1_id", "term_2_id", "relationship_tid"},]
    """
    def addRelationship(self, data, HELP=False, LIMIT=50):
        if HELP:
            sys.exit('data = {"term_1_id", "term_2_id", "relationship_tid"}')

        url_base = self.base_path + '/api/1/term/add-relationship'
        relationships = []
        for relationship in data:
            relationship.update({
                'term1_version':'1',
                'term2_version':'1',
                'relationship_term_version':'1'
            })
            relationships.append((url_base, relationship))
        self.post(relationships, LIMIT=LIMIT, action='Adding Relationships')




def main():
    args = read_args()
    sci=scicrunch(key=args['api_key'], base_path=args['base_path'], engine_key=args['engine_key'])
    #example term is troysincomb 38918 tmp_0138415
    #https://test2.scicrunch.org/scicrunch/interlex/view/tmp_0138415?searchTerm=troysincomb
    #https://test2.scicrunch.org/api/1/ilx/search/identifier/tmp_0138415?key=

    terms = [{
        #'term':'troysincomb',
        'id':38918,
        'existing_ids':[{
            'tid':38918,
            'curie':'ILX:0003',
            'iri':'http://t3db.org/toxins/T3D0002',
            'preferred':0,
            'change':False
        }],
        'definition':'employee',
        'synonyms':[{'literal':'trenton'}],
        'superclasses': [{
            'id': '146',
            #'ilx': 'tmp_0100145',
            #'label': 'A1 neuron',
            #'definition': 'Any abdominal neuron (FBbt_00001987) that is part of some larval abdominal segment 1 (FBbt_00001748).',
            #'status': '0'
        }],
    }]
    #annotations = [{'tid':38918,'annotation_tid':15034,'value':'testvaluess'}]
    #sci.addTerms(terms)
    #annotations = sci.getAnnotations([38918])
    terms = sci.updateTerms(terms, sql=False)
    #sci.updateAnntationValues(annotations)
    print(terms)

if __name__ == '__main__':
    main()
