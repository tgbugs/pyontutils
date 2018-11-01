""" To quick test Elastic to make sure it's behaving normally

Usage:
    elastic_search.py [-h | --help]
    elastic_search.py [-v | --version]
    elastic_search.py [--username=<path>] [--password=<path>]

Options:
    -h, --help                Display this help message
    -v, --version             Current version of file
    -u, --username=<path>     Username for Elastic [default: keys/elastic_username.txt]
    -p, --password=<path>     Password for Elastic [default: keys/elastic_password.txt]
"""
from docopt import docopt
import pandas as pd
from pathlib import Path as p
import requests as r
from sys import exit
import asyncio
from aiohttp import ClientSession, TCPConnector, BasicAuth
import math as m
from IPython import embed
from ilxutils.tools import *
from ilxutils.args_reader import doc2args
VERSION = '0.0.2'

# TODO: will have to asyncio it later
# TODO: basic auth search a list of ids to get it ready for concurrent searchs; crawl str or list < 10 elements


class ElasticSearch:
    def __init__(self, user, password):
        self.username, self.password = self.clean_auth(user, password)
        self.base_url = 'https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/interlex'

    def clean_auth(self, *args):
        return tuple(map(open_txt, filter(is_file, map(fix_path, args))))

    def get(self, url, data=None, auth=None):
        req = r.get(url, data=data, auth=auth)
        req.raise_for_status()
        try:
            output = req.json()
            return output['_source']
        except:
            if req.text:
                exit(req.text)
            else:
                exit(url + ', returns None')

    def get_async(self, urls, LIMIT, _print, debug, action):

        async def get_single(url, session, auth):
            url_suffix = url.rsplit('/', 1)[-1]
            async with session.get(url) as response:
                if response.status not in [200, 201]:
                    try:
                        output = await response.json()
                    except:
                        output = await response.text()
                    problem = str(output)
                    if debug:
                        return {'status_error': url_suffix}
                    # returns 'found':False... real data doesnt have 'found'; see the problem?
                    return None
                    # exit(
                    #     str(problem) + ' with status code [' +
                    #     str(response.status) + ']')

                output = await response.json(content_type=None)
                if not output:
                    if debug:
                        return {'None': url_suffix, 'failed': url_suffix}
                    exit(url + ' returns NoneType object')
                elif output.get('errormsg'):
                    if debug:
                        return {'errormsg': url_suffix, 'failed': url_suffix}
                    exit(url + ' returns errormsg: ' + str(output['errormsg']))
                elif not output.get('_source'):
                    if debug:
                        return {'unknown': url_suffix, 'failed': url_suffix}
                    exit(url + ' unknown error ' + str(output))
                else:
                    if debug:
                        return {'success': url_suffix}
                    if _print:
                        print(output['_source'])
                    return output['_source']

        async def get_all(urls, connector, loop):
            if _print:
                print('=== {0} ==='.format(action))
            tasks = []
            auth = BasicAuth(self.username, self.password)
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
        return outputs
        # return {k: v for keyval in outputs for k, v in keyval.items()}

    def search_by_ilx_id(self, ilx_id):
        ilx_id = str(ilx_id)
        ilx_id = ilx_id if 'ilx_' in ilx_id else ('ilx_' + ilx_id)
        url = '/'.join([self.base_url, 'term', ilx_id])
        return self.get(url, auth=(self.username, self.password))

    def search_by_ilx_ids(self, ilx_ids, LIMIT=25, _print=True, debug=False):
        urls = []
        for ilx_id in ilx_ids:
            ilx_id = str(ilx_id)
            ilx_id = ilx_id if 'ilx_' in ilx_id else ('ilx_' + ilx_id)
            urls.append('/'.join([self.base_url, 'term', ilx_id]))
        action = 'Searching Elastic via ILX IDs'
        return self.get_async(urls, LIMIT=LIMIT, _print=_print, debug=debug, action=action)


def batch(data, seg_length, func, **kwargs):
    total_data = [data[x:x + seg_length]
                  for x in range(0, len(data), seg_length)]
    total_count = m.floor(len(data) / seg_length)
    output = []
    for i, data in enumerate(total_data[:1], 0):
        print('Batch', i, 'out of', total_count)
        output.extend(func(data, **kwargs))
    print(output)
    return output


def main():
    doc = docopt(__doc__, version=VERSION)
    args = doc2args(doc)
    es = ElasticSearch(user='keys/.elastic_username',
                       password='keys/.elastic_password',)
    hit = es.search_by_ilx_id('ilx_0101431')
    embed()
    #hit = es.search_by_ilx_id(ilx_id='ilx_0101431')
    #hit = es.search_by_ilx_ids(ilx_ids=['ilx_010143'], _print=False, debug=True)
    #terms = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_terms_backup')
    #ilx_ids = list(terms.ilx)
    #records = batch(ilx_ids[:1000], 100,
    #                es.search_by_ilx_ids, _print=False, debug=True)
    #df = pd.DataFrame.from_records(records)
    #print(list(df))
    #create_json(list(df.failed), p.home() / 'Dropbox/failed_elastic')


if __name__ == '__main__':
    main()
