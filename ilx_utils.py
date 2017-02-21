#!/usr/bin/env python3.5

import os
import json
from hashlib import md5
from functools import wraps
import rdflib
from pyontutils.utils import makePrefixes, makeGraph

rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')

__FILENAME = 'resources/ilx-replace.json'
def managed(function):
    @wraps(function)
    def inner(*args, TO_REPLACE=None, **kwargs):
        with open(__FILENAME, 'rt+') as f:  # + maintains a lock
            if TO_REPLACE is None:
                TO_REPLACE = json.load(f)
                f.seek(0)
            output = function(*args, TO_REPLACE=TO_REPLACE, **kwargs)
            json.dump(TO_REPLACE, f, sort_keys=True, indent=4)
        return output
    return inner

@managed
def ilxGetRealId(temp_id, ontid, TO_REPLACE=None):
    # NOTE run on files after creation, ontid doesn't always exist before
    if temp_id not in TO_REPLACE:
        print('temp_id %s found that is not in %s where did it come from?' % (temp_id, __FILENAME))
        ilxLookupOrAdd(temp_id, TO_REPLACE=TO_REPLACE)
    record = TO_REPLACE[temp_id]
    if not record['ilx']:
        record['ontid'] = ontid
        real_id = getNewIlxId(temp_id, record['seed'], ontid)
        record['ilx'] = real_id

def getNewIlxId(temp_id, seed, ontology):
    return 'FAKE:1234567'

@managed
def ilxRepAdd(torep, seed=None, TO_REPLACE=None):
    if torep in TO_REPLACE:
        record = TO_REPLACE[torep]
        if record['ilx']:
            return record['ilx']  # return the real identifier
    else:
        TO_REPLACE[torep] = {'ilx':None, 'seed':seed, 'ontology':None}

    return torep

def ILXREPLACE(seed):
    h = md5()
    h.update(seed.encode())
    torep = 'ILXREPLACE:' + h.hexdigest()
    ilxRepAdd(torep, seed)
    return torep

def ilxGet(filename):
    graph = rdflib.Graph()
    graph.parse(filename, format='turtle')
    fn = os.path.splitext(filename)[0]
    print(fn)
    mg = makeGraph(fn, graph=graph)
    namespace = str(mg.namespaces['ILXREPLACE'])
    query = ("SELECT DISTINCT ?v "
             "WHERE { {?v ?p ?o} UNION {?s ?v ?o} UNION {?s ?p ?v} . "
             "FILTER("
             "strstarts(str(?v), '%s') )}") % namespace
    vals = graph.query(query)
    for val, in vals:
        qn = graph.namespace_manager.qname(val)
        print(qn)
    
@managed
def ilxDoReplace(graph, TO_REPLACE=None):
    pass

def main():
    if not os.path.exists(__FILENAME):
        with open(__FILENAME, 'wt') as f:
            json.dump({}, f)
        
    ILXREPLACE('wowzers')
    ILXREPLACE('are you joking')
    ilxGetRealId(ILXREPLACE('wowzers'), 'http://FIXME.org/thing.ttl')
    ilxGet('/home/tom/git/NIF-Ontology/ttl/generated/parcellation.ttl')

if __name__ == '__main__':
    main()
