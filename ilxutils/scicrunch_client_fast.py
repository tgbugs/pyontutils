import pandas as pd
import requests as r
import json
from sqlalchemy import create_engine, inspect, Table, Column
import numpy as np
import asyncio
import sys
import math as m
import progressbar
from aiohttp import ClientSession, TCPConnector
from args_reader import read_args

class scicrunch():

    def __init__(self, key, base_path):
        self.key = key
        self.base_path = base_path
        self.terms = {}

    def createBar(self, maxval):
        return progressbar.ProgressBar(maxval=maxval, \
            widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])

    async def identifierSearch(self, identifier, session):
        url = self.base_path + '/api/1/term/view/' + str(identifier) + '?key=' + self.key
        headers = {'Content-type': 'application/json'}
        async with session.get(url) as response:
            if response.status not in [200, 201]:
                output = await response.text
                problem = str(output)
                sys.exit(str(problem)+' with status code ['+str(response.status)+'] with params:'+str(params))
            output = await response.json()
            #print(output)
            output={int(output['data']['id']):output['data']}
            self.terms.update(output)
            #return output

    async def get_all(self, total_data, connector, loop):
        """Launch requests for all web pages."""
        tasks = []
        async with ClientSession(connector=connector,loop=loop) as session:
            bar = self.createBar(len(total_data)); bar.start()
            for i, data in enumerate(total_data):
                task = asyncio.ensure_future(self.identifierSearch(data, session))
                #task = self.identifierSearch(data, session)
                tasks.append(task)
                bar.update(i)
            bar.finish()
            _ = await asyncio.gather(*tasks)
            #return data
    def identifierSearchs(self, data=None, HELP=False):
        if HELP: sys.exit('parameters( data = "list of term_ids" )')
        connector = TCPConnector(limit=50) # rate limiter; should be between 20 and 80; 100 maxed out server
        loop = asyncio.get_event_loop() # event loop initialize
        future = asyncio.ensure_future(self.get_all(data, connector, loop)) # tasks to do; data is in json format [{},]
        loop.run_until_complete(future) # loop until done
        #FIXME
        #terms_dict = {}
        #for term in self.terms:
        #terms_dict.update(term)
        return self.terms#terms_dict

    """======================================================================"""
    async def update_term(self, data, session, i):
        url = self.base_path + '/api/1/term/edit/' + str(data['id'])

        #FIXME
        data.pop('annotation_tid', None)
        data.pop('value', None)
        data.pop('tid', None)

        params = {**{'key':self.key}, **data} #**{'batch-elastic':'True'}}
        headers = {'Content-type': 'application/json'}
        async with session.post(url, data=json.dumps(params), headers=headers) as response:
            if response.status not in [200, 201]:
                output = await response.text
                problem = str(output)
                sys.exit(str(problem)+' with status code ['+str(response.status)+'] with params:'+str(params))
            output = await response.json()
            print(i, output['data']['label'])

    async def update_terms(self, total_data, connector):
        """Launch requests for all web pages."""
        tasks = []
        async with ClientSession(connector=connector) as session:
            print('=== Updating Terms ===')
            bar = self.createBar(len(total_data)); bar.start()
            for i, data in enumerate(total_data):
                task = asyncio.ensure_future(self.update_term(data.copy(), session, i)) #FIXME had to copy to give new address
                tasks.append(task)
                bar.update(i)
            bar.finish()
            _ = await asyncio.gather(*tasks)

    def updateTerms(self, data):
        connector = TCPConnector(limit=25) # rate limiter; should be between 20 and 80; 100 maxed out server
        loop = asyncio.get_event_loop() # event loop initialize
        future = asyncio.ensure_future(self.update_terms(data, connector)) # tasks to do; data is in json format [{},]
        loop.run_until_complete(future) # loop until done
        #url  = self.base_path + '/php/batch-upsert-terms.php?key=' + self.key
        #r.get(url)

    """======================================================================"""
    async def add_annotation(self, data, session, i):
        url = self.base_path + '/api/1/term/add-annotation'
        params = {
            **data,
            'batch-elastic':'True',
            'term_version':'1',
            'key':self.key,
            'annotation_term_version':'1',
            'comment':'None',
        }
        headers = {'Content-type': 'application/json'}
        async with session.post(url, data=json.dumps(params), headers=headers) as response:
            output = await response.json()
            if response.status not in [200, 201]:
                output = await response.text
                problem = str(output)
                sys.exit(str(problem)+' with status code ['+str(response.status)+'] with params:'+str(params))
            output = await response.json()
            print(i, output['data'])

    async def add_annotations(self, total_data, connector):
        """Launch requests for all web pages."""
        tasks = []
        async with ClientSession(connector=connector) as session:
            print('=== Adding Annotations ===')
            bar = self.createBar(len(total_data)); bar.start()
            for i, data in enumerate(total_data):
                task = asyncio.ensure_future(self.add_annotation(data, session, i))
                tasks.append(task)
                bar.update(i)
            bar.finish()
            _ = await asyncio.gather(*tasks)

    def addAnnotations(self, data):
        connector = TCPConnector(limit=25) # rate limiter; should be between 20 and 80; 100 maxed out server
        loop = asyncio.get_event_loop() # event loop initialize
        future = asyncio.ensure_future(self.add_annotations(data, connector)) # tasks to do; data is in json format [{},]
        loop.run_until_complete(future) # loop until done
        url  = self.base_path + '/php/batch-upsert-terms.php?key=' + self.key
        r.get(url)

    """======================================================================"""
    async def edit_annotation(self, data, session):
        url = self.base_path + '/api/1/term/edit-annotation/' + str(data['id'])
        #extra = {'term_version':'1', 'annotation_term_version':'1'} #need this
        params = {**data, 'key':self.key}
        #print(params)
        headers = {'Content-type': 'application/json'}
        async with session.post(url, data=json.dumps(params), headers=headers) as response:
            output = await response.json()
            if response.status not in [200, 201]:
                problem = str(output)
                sys.exit(str(problem)+' with status code ['+str(response.status)+'] with params:'+str(params))
            print(output)
    async def edit_annotations(self, total_data, connector):
        """Launch requests for all web pages."""
        tasks = []
        async with ClientSession(connector=connector) as session:
            print('=== Editing Annotations ===')
            bar = self.createBar(len(total_data)); bar.start()
            for i, data in enumerate(total_data):
                task = asyncio.ensure_future(self.edit_annotation(data, session))
                tasks.append(task)
                bar.update(i)
            bar.finish()
            _ = await asyncio.gather(*tasks)
    def editAnnotations(self, data):
        connector = TCPConnector(limit=50) # rate limiter; should be between 20 and 80; 100 maxed out server
        loop = asyncio.get_event_loop() # event loop initialize
        future = asyncio.ensure_future(self.edit_annotations(data, connector)) # tasks to do; data is in json format [{},]
        loop.run_until_complete(future) # loop until done

    """======================================================================"""
    async def delete_annotation(self, identifier, session):
        url = self.base_path + '/api/1/term/edit-annotation/' + str(identifier)
        params = {
            'value':' ', #for delete
            'annotation_tid':' ', #for delete
            'tid':' ', #for delete
            'term_version':'1',
            'key':self.key,
            'annotation_term_version':'1',
        }
        headers = {'Content-type': 'application/json'}
        async with session.post(url, data=json.dumps(params), headers=headers) as response:
            output = await response.json()
            if response.status not in [200, 201]:
                problem = str(output)
                sys.exit(str(problem)+' with status code ['+str(response.status)+'] with params:'+str(params))
    async def delete_annotations(self, total_data, connector):
        """Launch requests for all web pages."""
        tasks = []
        async with ClientSession(connector=connector) as session:
            print('=== Deleting Annotations ===')
            bar = self.createBar(len(total_data)); bar.start()
            for i, data in enumerate(total_data):
                task = asyncio.ensure_future(self.delete_annotation(data, session))
                tasks.append(task)
                bar.update(i)
            bar.finish()
            _ = await asyncio.gather(*tasks)
    def deleteAnnotationsVIAannotationId(self, data):
        connector = TCPConnector(limit=50) # rate limiter; should be between 20 and 80; 100 maxed out server
        loop = asyncio.get_event_loop() # event loop initialize
        future = asyncio.ensure_future(self.delete_annotations(data, connector)) # tasks to do; data is in json format [{},]
        loop.run_until_complete(future) # loop until done

    """======================================================================"""
    async def get_annotation(self, tid, session):
        url = self.base_path + '/api/1/term/get-annotations/' + str(tid) + '?key=' + self.key
        print(url)
        async with session.get(url) as response:
            output = await response.json()
            if response.status not in [200, 201]:
                problem = str(output)
                sys.exit(str(problem)+' with status code ['+str(response.status)+']')
            return output['data']
    async def get_annotations(self, total_data, connector):
        """Launch requests for all web pages."""
        tasks = []
        async with ClientSession(connector=connector) as session:
            print('=== Getting Annotations ===')
            bar = self.createBar(len(total_data)); bar.start()
            for i, data in enumerate(total_data):
                task = asyncio.ensure_future(self.get_annotation(data, session))
                tasks.append(task)
                bar.update(i)
            bar.finish()
            annotations = await asyncio.gather(*tasks)
            return annotations
    def getAnnotationsVIAtid(self, data):
        connector = TCPConnector(limit=20) # rate limiter; should be between 20 and 80; 100 maxed out server
        loop = asyncio.get_event_loop() # event loop initialize
        future = asyncio.ensure_future(self.get_annotations(data, connector)) # tasks to do; data is in json format [{},]
        annotations = loop.run_until_complete(future) # loop until done
        return annotations
        #url  = self.base_path + '/php/batch-upsert-terms.php?key=' + self.key
        #r.get(url)

    """======================================================================"""
    async def add_term(self, data, session):
        """ add to ilx """
        url = self.base_path + '/api/1/ilx/add'
        params = {
            'key':self.key,
            'term':str(data['label']),
        }
        headers = {'Content-type': 'application/json'}
        async with session.post(url, data=json.dumps(params), headers=headers) as response:
            post_ilx = await response.json()

            limit = 0 #BUG; server needs to breath sometimes
            while post_ilx.get('errormsg') == 'could not generate ILX identifier' and limit < 100:
                async with session.post(url, data=json.dumps(params), headers=headers) as response:
                    post_ilx = await response.json()
                    limit+=1

            if response.status not in [200, 201]:
                problem = str(post_ilx)
                sys.exit(str(problem)+' with status code ['+str(response.status)+'] with params:'+str(params))
            try:
                data['ilx'] = post_ilx['data']['ilx']
            except:
                data['ilx'] = post_ilx['data']['fragment']
        print(post_ilx)
        """ add to scicrunch """
        url = self.base_path + '/api/1/term/add'
        params = {
            "key":self.key,
            'label':data['label'],
            'definition':data.get('definition'),
            'type':data['type'],
            'ilx':data['ilx'],
            'cid':'0',
        }
        if data.get('synonyms'):
            params['synonyms'] = [{'literal':data.get('synonyms')}]

        if data.get('superclass_ilx'):
            params['superclasses'] = [{
                    'label':data.get('superclass_label'),
                    'ilx':data.get('superclass_ilx'),
                    'superclass_tid':data.get('superclass_tid')
                }]

        headers = {'Content-type': 'application/json'}
        async with session.post(url, data=json.dumps(params), headers=headers) as response:
            output = await response.json()
            if response.status not in [200, 201]:
                problem = str(output)
                sys.exit(str(problem)+' with status code ['+str(response.status)+'] with params:'+str(params))
            output = {output['data']['label']:output['data']}
            return output

    async def add_terms(self, total_data, connector):
        """Launch requests for all web pages."""
        tasks = []
        async with ClientSession(connector=connector) as session:
            print('=== Adding Terms ===')
            bar = self.createBar(len(total_data)); bar.start()
            for i, data in enumerate(total_data):
                task = asyncio.ensure_future(self.add_term(data, session))
                tasks.append(task)
                bar.update(i)
            bar.finish()
            data = await asyncio.gather(*tasks)
            return data
    def addTerms(self, data):
        connector = TCPConnector(limit=50) # rate limiter; should be between 20 and 80; 100 maxed out server
        loop = asyncio.get_event_loop() # event loop initialize
        future = asyncio.ensure_future(self.add_terms(data, connector)) # tasks to do; data is in json format [{},]
        terms = loop.run_until_complete(future) # loop until done
        terms_dict = {}
        for term in terms:
            terms_dict.update(term)
        return terms_dict
        #url  = self.base_path + '/php/batch-upsert-terms.php?key=' + self.key
        #r.get(url)


def main():
    args = read_args()
    sci=scicrunch(key=args['api_key'], base_path=args['base_path'])
    sci.identifierSearchs(help=True)
    #total_annotations=sci.getAnnotationsVIAtid([304379])
    #print(total_annotations)
    #sys.exit()
    #production
    #annotation_ids = []
    #for annotations in total_annotations:
    #    for annotation in annotations:
    #        if annotation['value'] == 'None':
    #            annotation_ids.append(annotation['id'])
    #print(annotation_ids)
    #sci.deleteAnnotationsVIAannotationId(annotation_ids)

    #sci.deleteAnnotationsVIAid(ids)
if __name__ == '__main__':
    main()
