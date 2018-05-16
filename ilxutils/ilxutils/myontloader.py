from pyontutils.ontload import loadall
from os.path import join as jpth
import os
from glob import glob
import pickle
from pyontutils.core import *

'''Used to extract NIF-Ontology + imports within it, into a ttl then into a pickle for compression sake'''
graph = loadall(git_local='',repo_name='NIF-Ontology',local=True)
graph.serialize(destination='NIF-ALL.ttl', format='turtle')
#with open('NIF-ALL.pickle', 'wb') as f: pickle.dump(graph, f)
