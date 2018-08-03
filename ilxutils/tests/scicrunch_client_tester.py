""" Tests the validity of scicrunch_client and not the data outputed itselfself.
    Output tests not needed bc data is collected and replaced instead of built.
    Only known bug is tid->superclass_tid change & is corrected in dictlib.
    Crawl option is tested in test_addTerms function.

Usage:  scicrunch_client_tester.py [-h | --help]
        scicrunch_client_tester.py [-v | --version]
        scicrunch_client_tester.py [-p | -b]

Options:
    -h, --help                  Display this help message
    -v, --version               Current version of file
    -p, --production            Production SciCrunch
    -b, --beta                  Beta SciCrunch
"""
import unittest
from docopt import docopt
from ilxutils.scicrunch_client import scicrunch
from ilxutils.args_reader import read_args
from pathlib import Path as p
import warnings
import time
import pandas as pd
import requests as r
now = str(time.time()).split('.')[0]
VERSION = '0.1'
doc = docopt(__doc__, version=VERSION)
args = pd.Series({k.replace('--', ''): v for k, v in doc.items()})

with open('/home/troy/elastic_migration/auth.ini', 'r') as uk:
    vars = uk.read().split('\n')
    username = vars[0].split('=')[-1].strip()
    password = vars[1].split('=')[-1].strip()


def ignore_warnings(test_func):
    def do_test(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            test_func(self, *args, **kwargs)
    return do_test


class TestSC(unittest.TestCase):
    @ignore_warnings
    def setUp(self):
        if args.production:
            # FIXME; production doesnt have add/update values yet due to delete not really delete
            self.args = read_args(api_key=p.home() / 'keys/production_api_scicrunch_key.txt',
                                  db_url=p.home() / 'keys/production_engine_scicrunch_key.txt',
                                  production=True)
            self.elastic_base = "https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/interlex/term/{ilx_id}"
        else:
            '''currently just for beta.scicrunch.org'''
            self.args = read_args(api_key=p.home() / 'keys/production_api_scicrunch_key.txt',
                                  db_url=p.home() / 'keys/production_engine_scicrunch_key.txt',
                                  beta=True)
            self.annos_add = [{'tid': 664,  'annotation_tid': 12767, 'value': 'add_'+now}]
            self.anno_update = [{'id': 10, 'annotation_tid': 12767, 'tid': 664, 'value': now}]
            self.terms_add = [{'term': 'troy_test_'+now, 'definition': 'temp', 'type': 'cde'}]
            self.terms_add_crawl = [{'term': 'troy_test_crawl_' +
                                     now, 'definition': 'temp', 'type': 'cde'}]
            self.terms2update = [{'id': 304383, 'ilx': 'tmp_0381298', 'definition': 'update_'+now, 'existing_ids': {
                'iri': 'test.org/121', 'curie': 'test:121', 'old_iri': 'test.org/123', 'replace': True}}]
            self.elastic_base = "https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/beta2_interlex/term/{ilx_id}"
        self.sci = scicrunch(api_key=self.args.api_key,
                             base_path=self.args.base_path,
                             db_url=self.args.db_url)
        self.ids = [10]
        self.tids = [182]
        self.annotation_ids = [10]

    @ignore_warnings
    def test_identifierSearches(self):
        get = self.sci.identifierSearches(ids=self.ids, _print=False, debug=True)
        self.assertEqual(get['success'], True)
        self.assertEqual(get['data'].get('errormsg'), None)

    @ignore_warnings
    def test_addAnnotations(self):
        post = self.sci.addAnnotations(data=self.annos_add, _print=False, debug=True)[0]
        get = self.sci.getAnnotations_via_id([post['data']['id']], _print=False, debug=True)
        self.assertEqual(get['data']['value'], self.annos_add[0]['value'])
        self.assertEqual(get['data']['annotation_tid'], str(self.annos_add[0]['annotation_tid']))
        self.assertEqual(get['data']['tid'], str(self.annos_add[0]['tid']))
        self.sci.deleteAnnotations(get['data']['id'], _print=False)

    @ignore_warnings
    def test_getAnnotations_via_tid(self):
        '''returns a list of dicts bc it returns all annos conc to the term id'''
        get = self.sci.getAnnotations_via_tid(tids=self.tids, _print=False, debug=True)
        self.assertEqual(get['success'], True)
        self.assertEqual(type(get['data']), list)
        self.assertNotEqual(get['data'], None)

    @ignore_warnings
    def test_getAnnotations_via_id(self):
        get = self.sci.getAnnotations_via_id(
            annotation_ids=self.annotation_ids, _print=False, debug=True)
        self.assertEqual(get['success'], True)
        self.assertEqual(get['data'].get('errormsg'), None)

    @ignore_warnings
    def test_updateAnnotation(self):
        post = self.sci.updateAnnotations(data=self.anno_update, _print=False, debug=True)
        get = self.sci.getAnnotations_via_id(
            annotation_ids=self.annotation_ids, _print=False, debug=True)
        self.assertEqual(get['data']['value'], now)

    @ignore_warnings
    def test_addTerms(self):
        '''crawl and elastic are tested here'''
        post = self.sci.addTerms(data=self.terms_add_crawl, _print=False, debug=True, crawl=True)[0]
        get = self.sci.identifierSearches(
            [post['data']['id']], _print=False, debug=True, crawl=True)
        self.assertEqual(get['data']['id'], str(post['data']['id']))

        post = self.sci.addTerms(data=self.terms_add, _print=False, debug=True, crawl=False)[0]
        get = self.sci.identifierSearches(
            [post['data']['id']], _print=False, debug=True, crawl=False)
        self.assertEqual(get['data']['id'], str(post['data']['id']))

        url = self.elastic_base.format(ilx_id=get['data']['ilx'])
        req = r.get(url, auth=(username, password)).json()
        self.assertEqual(req['found'], True)

    @ignore_warnings
    def test_updateTerms(self):
        post = self.sci.updateTerms(data=self.terms2update, _print=False, debug=True)[0]
        get = self.sci.identifierSearches([post['data']['id']], _print=False, debug=True)
        self.assertEqual(get['data']['definition'], 'update_'+now)


if __name__ == '__main__':
    unittest.main()
