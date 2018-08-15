from docopt import docopt
from IPython import embed
from ilxutils.cli import Client
import json
import os
import requests as r
from sys import exit
import time
import unittest
VERSION = '0.0.2'
# ILX:0108124 == "Organ" | term
# ILX:0101431 == "brain" | term
# ILX:0107497 == "Neuron" | term
# ILX:0112772 == "Afferent projection" | relationship
# ILX:0115071 == "hasConstraint" | annotation

def now():
    time.sleep(1)
    return str(int(time.time()))

class TestCli(unittest.TestCase):
    term_now = now()
    anno_now = now()
    rela_now = now()
    """
    Entity Examples
    """
    good_entities_to_test = [
        ('term', 'ILX:0101431', 'test_' + term_now, 'test_definition'),  # create term
        ('annotation', 'ILX:0101431', 'test_' + anno_now),  # create annotation
        ('relationship', 'ILX:0101431', 'test_' + rela_now),  # create relationship
    ]
    bad_entities_to_test = [
        ('purple', 'ILX:0101431', 'test_' + now()), # fake type
        ('term', 'ILX:FakeID', 'fake superclass'), # bad superclass
        ('term', 'ILX:0101431', 'test_' + term_now),  # duplicate entity; same everything
        ('annotation', 'ILX:0101431', 'test_' + term_now),  # duplicate entity; diff type
        ('term', 'ILX:0107497', 'test_' + term_now),  # duplicate entity; diff superclass
        ('relationship', 'ILX:0107497', 'test_' + term_now),  # dup diff super and type
    ]
    """
    Triple Examples
    """
    good_triples_to_test = [
        ('ILX:0101431', 'definition:', 'def_' + term_now),  # class definition
        ('ILX:0101431', 'comment', 'comment_' + term_now),  # class comment
        ('ILX:0107497', 'rdfs:subClassOf', 'ILX:0101431'),  # class superclass
        ('ILX:0101431', 'NIFRID:synonym', 'Mind'),  # class comment
        #('ILX:0101431', 'ilxtr:existingId', 'https://test.org/' + now()),  # class comment
    ]
    bad_triples_to_test = [
        ('FakeID', 'definition:', 'This is a fake'),  # subj doesnt exist
        ('ILX:0101431', 'meme', 'Do all the work!'),  # made-up predicate
        ('ILX:0101431', 'rdfs:subClassOf', 'ILX:FakeID'),  # superclass doesnt exist
        ('ILX:0101431', 'ilxtr:existingId', 'not a uri'),  # duplicate term diff
    ]

    def setUp(self):
        self.client = Client(test=True)

    def test(self):
        term = self.client.add_entity(*self.good_entities_to_test[0])
        anno = self.client.add_entity(*self.good_entities_to_test[1])
        rela = self.client.add_entity(*self.good_entities_to_test[2])
        self.assertEqual(term['success'], True)
        self.assertEqual(anno['success'], True)
        self.assertEqual(rela['success'], True)

        for entity in self.bad_entities_to_test:
            self.assertEqual(self.client.add_entity(*entity), 'failed')

        for triple in self.good_triples_to_test:
            self.assertEqual(self.client.add_triple(*triple)['success'], True)

        for triple in self.bad_triples_to_test:
            self.assertEqual(self.client.add_triple(*triple), 'failed')

        # Annotation proptery
        anno_entity = ('ILX:0101431', anno['data']['ilx'], "value_" + self.term_now)
        anno = self.client.add_triple(*anno_entity)
        self.assertEqual(anno['success'], True)
        # Relationship property
        rela_entity = ('ILX:0101431', rela['data']['ilx'], term['data']['ilx'])
        rela = self.client.add_triple(*rela_entity)
        self.assertEqual(rela['success'], True)

    def test_get(self):
        good_output, success = self.client.get_data_from_ilx('ILX:0101431')
        self.assertEqual(success, True)
        bad_output, success = self.client.get_data_from_ilx('FAKEID')
        self.assertEqual(success, False)

if __name__ == '__main__':
    unittest.main()
