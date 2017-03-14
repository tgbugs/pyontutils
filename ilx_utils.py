#!/usr/bin/env python3.6

import os
import json
from glob import glob
from hashlib import md5
from functools import wraps
import rdflib
from pyontutils.utils import makePrefixes, makeGraph

# ilx api implementation (will change)
import csv
import requests
from io import StringIO

#debug
from IPython import embed

# interlex api (temp version)
ILX_ENDPOINT = 'https://test.scicrunch.org/forms/term-forms/term-bulk-upload.php'
CID = 72  # SciCrunch community id
ilx_session = requests.Session()
ILX_USER, ILX_PASS = os.environ.get('ILX_USER'), os.environ.get('ILX_PASS')
ilx_session.auth = (ILX_USER, ILX_PASS)  # basic auth but fails?
def getNewIlxId(temp_id, seed, ontid):
    # Label[tab] Type[tab] Definition[tab] OntologyURLs[tab] Comment[tab] Synonym::Type[tab] Curie::Iri::Preferred[tab] Superclasses[new line]
    row = 'TOM TEST TERM', 'term', None, ontid, temp_id, None, None, None
    sio = StringIO()
    writer = csv.writer(sio, lineterminator='\n', delimiter='\t')
    writer.writerow(row)
    data = {'file':sio, 'cid':CID}
    req = requests.Request(method='POST', url=ILX_ENDPOINT, data=data)
    req.headers
    prep = req.prepare()
    resp = ilx_session.send(prep, verify=False)
    embed()
    #return 'ILX:1234567'

# file handling

__FILENAME = 'resources/ilx-replace.json'
def managed(mode='rt+'):
    func = None
    if callable(mode):
        func = mode
        mode = 'rt+'
    def managed_(function):
        function.__globals__['FIRST'] = True
        @wraps(function)
        def inner(*args, TEMP_INDEX=None, **kwargs):
            with open(__FILENAME, mode) as f:  # + maintains a lock
                if TEMP_INDEX is None:
                    TEMP_INDEX = json.load(f)
                    f.seek(0)
                output = function(*args, TEMP_INDEX=TEMP_INDEX, **kwargs)
                if f.writable():
                    json.dump(TEMP_INDEX, f, sort_keys=True, indent=4)
            return output
        return inner
    if func is not None:
        return managed_(func)
    else:
        return managed_

# check temp_id status
@managed
def ilxGetRealId(temp_id, ontid, TEMP_INDEX=None):
    # NOTE run on files after creation, ontid doesn't always exist before
    if temp_id not in TEMP_INDEX:
        print('temp_id %s found that is not in %s where did it come from?' % (temp_id, __FILENAME))
        ilxLookupOrAdd(temp_id, TEMP_INDEX=TEMP_INDEX)
    record = TEMP_INDEX[temp_id]
    if not record['ilx']:
        record['ontid'] = ontid
        real_id = getNewIlxId(temp_id, record['seed'], ontid)
        record['ilx'] = real_id

@managed
def ilxTempAdd(temp_id, seed=None, ontid=None, TEMP_INDEX=None):
    if temp_id in TEMP_INDEX:
        record = TEMP_INDEX[temp_id]
        if record['ilx']:
            return record['ilx']  # return the real identifier
        elif ontid and not record['ontid']:
            record['ontid'] = ontid
    else:
        TEMP_INDEX[temp_id] = {'ilx':None, 'seed':seed, 'ontid':ontid}

    return temp_id

def ILXREPLACE(seed):
    h = md5()
    h.update(seed.encode())
    temp_id = 'ILXREPLACE:' + h.hexdigest()
    ilxTempAdd(temp_id, seed)
    return temp_id

def ilxGet(filename):
    graph = rdflib.Graph()
    graph.parse(filename, format='turtle')
    fn = os.path.splitext(filename)[0]
    print(fn)
    mg = makeGraph(fn, graph=graph, writeloc='')
    namespace = str(mg.namespaces['ILXREPLACE'])
    query = ("SELECT DISTINCT ?v "
             "WHERE { {?v ?p ?o} UNION {?s ?v ?o} UNION {?s ?p ?v} . "
             "FILTER("
             "strstarts(str(?v), '%s') )}") % namespace
    vals = graph.query(query)
    for val, in vals:
        qn = graph.namespace_manager.qname(val)
        ilxTempAdd(qn, ontid=mg.ontid)
        print(qn, mg.ontid)
        #ilxGetRealId(qn, mg.ontid)

    ilxDoReplace(mg)
    
@managed('rt')
def ilxDoReplace(mg, TEMP_INDEX=None):
    mg.add_namespace('ILX', makePrefixes('ILX')['ILX'])
    mg.del_namespace('ILXREPLACE')
    for temp_id, record in TEMP_INDEX.items():
        if not record['ilx']:
            print('%s is missing a real ilx id. Please make sure you have run ilxGetRealId on all entires for %s' % (temp_id, mg.ontid))
        mg.replace_uriref(temp_id, record['ilx'])
    mg.write()

    if ilxDoReplace.__globals__['FIRST']:
        ilxDoReplace.__globals__['FIRST'] = False
        #embed()

def main():
    if not os.path.exists(__FILENAME):
        with open(__FILENAME, 'wt') as f:
            json.dump({}, f)

    ILXREPLACE('wowzers')
    ILXREPLACE('are you joking')
    ilxGetRealId(ILXREPLACE('wowzers'), 'http://FIXME.org/thing.ttl')
    return
    for file in glob('/home/tom/git/NIF-Ontology/ttl/generated/parcellation/*.ttl'):
        ilxGet(file)
    ilxGet('/home/tom/git/NIF-Ontology/ttl/generated/parcellation.ttl')

if __name__ == '__main__':
    main()
