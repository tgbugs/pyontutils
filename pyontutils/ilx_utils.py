#!/usr/bin/env python3.6

import os
import json
from glob import glob
from hashlib import md5
from functools import wraps
import robobrowser
import rdflib
from pyontutils.utils import makePrefixes, makeGraph
from pyontutils.scigraph_client import Vocabulary

# ilx api implementation (will change)
import csv
import requests
from io import StringIO

#debug
from IPython import embed

sgv = Vocabulary()

# scicrunch login stuff
#SC_EM = os.environ.get('SC_EM', None)
#SC_PASS = os.environ.get('SC_PASS', None)
SESS_COOKIE = None  # getSessionCookie(SC_EM, SC_PASS)


# interlex api (temp version)
ILX_SERVER = 'https://beta.scicrunch.org/'
ILX_ENDPOINT = 'forms/term-forms/term-bulk-upload.php'  # test.scicrunch.org will create real records
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

__FILENAME = os.path.join(os.path.dirname(__file__), 'resources/nif-ilx-replace.json')

def setfilename(filepath):
    if not os.path.exists(filepath):
        dn = os.path.dirname(filepath)
        if dn and not os.path.exists(dn):
            os.mkdir(dn)  # hack for creating resources inside site-packages which will likely fail with permissions errors if --user was not installed by pip :/
        with open(filepath, 'wt') as f:
            f.write('{}\n')
    global __FILENAME
    __FILENAME = filepath

# check temp_id status

setfilename(__FILENAME)

def managed(mode='rt+'):
    func = None
    if callable(mode):
        func = mode
        mode = 'rt+'
    def managed_(function):
        function.__globals__['FIRST'] = True
        @wraps(function)
        def inner(*args, TEMP_INDEX=None, **kwargs):
            print(__FILENAME)
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

class RecMan:
    """ A completely unsafe way to read and write
        python dicts to json on disk """
    def __init__(self, recfilepath):
        self._check_exists_or_create(recfilepath)
        self.filepath = recfilepath
        self._file = None
        self.DATA = {}

    def write(self):
        with open(self.filepath, 'wt') as f:
            json.dump(self.DATA, f, sort_keys=True, indent=4)

    def read(self):
        with open(self.filepath, 'rt') as f:
            self.DATA = json.load(f)

def makeIlxRec(label,
               definition='',
               type='term',
               comment='',
               synonyms=tuple(),
               existing_ids=tuple(),
               superclass=None,
               ontologies=tuple()):
        out = {'label':label,
               'definition':definition,
               'type':str(type),
               'comment':str(comment),
               'synonyms':[{'literal':str(s), 'type':''} for s in synonyms],
               'existing_ids':[{'curie':c, 'iri':'', 'preferred':'0'} for c in existing_ids],
               'superclass':{'label':superclass}, 'ontologies':[{'url':str(u)} for u in ontologies]}
        return out

@managed
def ilxGetRealId(temp_id, ontid, TEMP_INDEX=None):
    # NOTE run on files after creation, ontid doesn't always exist before
    if temp_id not in TEMP_INDEX:
        print('temp_id %s found that is not in %s where did it come from?' % (temp_id, __FILENAME))
        ilxLookupOrAdd(temp_id, TEMP_INDEX=TEMP_INDEX)
    record = TEMP_INDEX[temp_id]
    if not record['ilx']:
        record['ontid'] = ontid
        real_id = getNewIlxId(temp_id, ontid)
        record['ilx'] = real_id

@managed
def ilxAddTempId(temp_id, ontid=None, TEMP_INDEX=None):  # FIXME simplify
    if temp_id in TEMP_INDEX:
        record = TEMP_INDEX[temp_id]
        if record['ilx']:
            return record['ilx']  # return the real identifier
        elif ontid and not record['ontid']:
            record['ontid'] = ontid
    else:
        TEMP_INDEX[temp_id] = {'ilx':None, 'ontid':ontid}

    return temp_id

@managed
def ilxLookupExisting(temp_id, TEMP_INDEX=None):
    return TEMP_INDEX[temp_id]  # KeyError ok here

def ILXREPLACE(seed):
    h = md5()
    h.update(seed.encode())
    temp_id = 'ILXREPLACE:' + h.hexdigest()
    try:
        e = ilxLookupExisting(temp_id)
        if e is not None:
            return e
        else:
            print(temp_id, 'has been read from a file but has not been replaced.')
    except KeyError:
        pass

    return temp_id

def loadGraphFromFile(filename, prefixes=None):
    graph = rdflib.Graph()
    graph.parse(filename, format='turtle')
    fn = os.path.splitext(filename)[0]
    print(fn)
    mg = makeGraph(fn, prefixes=prefixes, graph=graph, writeloc='')
    return mg

def getSessionCookie(username, password):
    url = ILX_SERVER
    br = robobrowser.RoboBrowser()
    br.open(url)
    form = br.get_form(id=0)
    form['email'].value = username
    form['password'].value = password
    br.submit_form(form)
    session_cookie = br.session.cookies['PHPSESSID']
    return {'Cookie': 'PHPSESSID=%s' % session_cookie}

def makeJsonFromExisting(existing, order=None):
    if order is None:
        order = getSubOrder(existing)
    recs = [existing[id_]['rec'] for id_ in order]
    return recs

def getIlxForRecords(existing):
    order = getSubOrder(existing)
    recs = makeJsonFromExisting(existing, order)
    with open('/tmp/externaltest.json', 'wt') as f:
        json.dump(recs, f, sort_keys=True, indent=4)
    file = json.dumps(recs, sort_keys=True).encode()
    data = {'cid':b'NaN'}
    session = requests.Session()
    req = requests.Request(method='POST', url=ILX_SERVER + ILX_ENDPOINT, data=data, files={'file': ('ilx_utils_upload.json', file, 'application/json')})  # the 'file' keyword is required to get all of this to work
    req.headers.update(SESS_COOKIE)
    req.headers['Connection'] = 'keep-alive'
    prep = req.prepare()
    resp = session.send(prep)
    tuples = decodeIlxResp(resp)
    mergeIds(existing, order, tuples)  #  FIXME once the API works as designed we need to refactor so we dont mutate state here, but for now there isn't really an option because of all the checks we need to do extracting ids from text :/
    if existing[order[0]]['id'] is None:
        raise ValueError('The call to the interlex API does not seem to have worked!')
    return resp

def mergeIds(existing, order, tuples):
    for temp_id, (label, id_) in zip(order, tuples):
        elabel = existing[temp_id]['rec']['label']
        if elabel != label:
            raise ValueError('%s does not match %s! The order of ids is probably incorrect.')
        existing[temp_id]['id'] = id_

def ilxIdFix(id_):  # TODO have to deal with namespaces (e.g. uri.interlex.org/tgbugs/ilx_1234567)
    if 'beta' in ILX_SERVER:
        return id_.replace('tmp_','ILX:')
    else:
        return id_.replace('ilx_','ILX:')

def decodeIlxResp(resp):
    """ We need this until we can get json back directly and this is SUPER nasty"""
    lines = [_ for _ in resp.text.split('\n') if _]  # strip empties

    if 'successfull' in lines[0]:
        return [(_.split('"')[1],
                 ilxIdFix(_.split(': ')[-1]))
                for _ in lines[1:]]
    elif 'errors' in lines[0]:
        return [(_.split('"')[1],
                 ilxIdFix(_.split('(')[1].split(')')[0]))
                for _ in lines[1:]]

def saveRecords(existing, json_location):
    with open(json_location, 'wt') as f:
        json.dump(existing, f, sort_keys=True, indent=4)

def writeGraph(graph, target_graph, temp_ids_ids):
    if target_graph is None:
        target_graph = graph

    graph.add_known_namespace('ILX')
    target_graph.add_known_namespace('ILX')
    for prefix in graph.namespaces:
        if prefix not in target_graph.namespaces and prefix != 'ILXREPLACE':
            target_graph.add_known_namespace(prefix)
    for temp_id, id_ in temp_ids_ids:
        graph.replace_uriref(temp_id, id_)
        s = graph.expand(id_)
        for p, o in graph.g.predicate_objects(s):
            target_graph.add_recursive((s, p, o), graph)

    graph.write()
    target_graph.write()

def buildReplaceStruct(existing, graphs_files):
    graph_temp_id_map = {}
    fg = {file:graph for graph, file in graphs_files}
    for temp_id, dict_ in existing.items():
        for f in dict_['files']:
            if fg[f] not in graph_temp_id_map:
                graph_temp_id_map[fg[f]] = []
            graph_temp_id_map[fg[f]].append((temp_id, existing[temp_id]['id']))
    return graph_temp_id_map

def wholeProcess(filenames, existing, target_filename=None, json_location='ilx-records.json', getIlx=False, write=True): # FIXME when dealing with multiple files we need to collect all the files in the set :/ this can't operate on a single file
    # load all graphs
    graphs_files = [(loadGraphFromFile(f), f) for f in filenames]
    target_graph = loadGraphFromFile(target_filename) if target_filename is not None else None
    # create records for all files
    for graph, _ in graphs_files:
        createRecordsFromGraph(graph, existing, target_graph)
    if not existing:
        raise TypeError('Graphs do not contain any temporary identifiers.')
    # get ilx for all the records
    if getIlx:
        getIlxForRecords(existing)
    saveRecords(existing, json_location)
    # write the records for all graph-target pairs, if a single output target is specified it will be used for all input files
    if write:
        gtim = buildReplaceStruct(existing, graphs_files)
        for g, temp_ids_ids in gtim.items():
            writeGraph(g, target_graph, temp_ids_ids)

def createRecordsFromGraph(graph, existing, target_graph=None):
    mg = graph
    graph = mg.g
    s = rdflib.URIRef(makePrefixes('OBOANN')['OBOANN'] + 'synonym')
    if target_graph is None:
        target_ontology_iri = mg.ontid
    else:
        target_ontology_iri = target_graph.ontid

    if 'ILXREPLACE' in mg.namespaces:
        namespace = str(mg.namespaces['ILXREPLACE'])
    else:
        print('Nothing needs to be replaced in', mg.filename)
        return 
    query = ("SELECT DISTINCT ?v "
             "WHERE { {?v ?p ?o} UNION {?s ?v ?o} UNION {?s ?p ?v} . "
             "FILTER("
             "strstarts(str(?v), '%s') )}") % namespace
    vals = graph.query(query)
    #existing = {}  # TODO this needs to populate from an existing source ie the ontology, and a tempid -> realid map?
    for val, in vals:
        qn = graph.namespace_manager.qname(val)
        try:
            labs = list(graph.objects(val, rdflib.RDFS.label))
            label = str(labs[0])
        except IndexError:
            label = None  # not defined here but we need to collect info here anyway
        definition = list(graph.objects(val, rdflib.namespace.SKOS.definition))
        if definition: definition = definition[0]
        synonyms = list(graph.objects(val, s))
        superclass = [_ for _ in graph.objects(val, rdflib.RDFS.subClassOf) if type(_) == rdflib.URIRef]
        superclass = superclass[0] if superclass else None
        try:
            superclass = graph.namespace_manager.qname(superclass)
        except (TypeError, ValueError) as e:
            print('ERROR: superclass of', qn, 'not a proper uri', superclass)
            superclass = None
        rec = makeIlxRec(label, definition, type='term', comment=qn, synonyms=synonyms, existing_ids=[], superclass=superclass, ontologies=[target_ontology_iri])
        if qn in existing:
            _tmp = set(existing[qn]['files'])
            _tmp.add(mg.filename)  # prevent duplicate files from multiple runs
            existing[qn]['files'] = list(_tmp)
            newrec = {}
            for k, v in existing[qn]['rec'].items():
                if v:
                    newrec[k] = v
                else:
                    newrec[k] = rec[k]
            existing[qn]['rec'] = newrec

        else:
            existing[qn] = {'id':None,
                            'sc':superclass,  # make sorting easier
                            'files':[mg.filename],
                            #'done':False,  # we probably don't need this
                            'rec':rec}

    superToLabel(existing)

def superToLabel(existing):
    for v in existing.values():
        sc = v['sc']

        if sc:
            try:
                l = existing[sc]['rec']['label']
            except KeyError:  # FIXME this happens when the superclass is not to a tempid, using sc breaks tests
                l = sgv.findById(sc)['labels'][0]  # pull the label out of scigraph so that the interlex api can match it by label as well
            v['rec']['superclass']['label'] = l
            if not l:
                print('WARNING! class', sc, 'has no label!')

def getSubOrder(existing):
    """ Alpha sort by the full chain of parents. """
    alpha = list(zip(*sorted(((k, v['rec']['label']) for k, v in existing.items()), key=lambda a: a[1])))[0]
    depths = {}
    def getDepth(id_):
        if id_ in depths:
            return depths[id_]
        else:
            if id_ in existing:
                names_above = getDepth(existing[id_]['sc'])
                depths[id_] = names_above + [existing[id_]['rec']['label']]
                return depths[id_]
            else:
                return ['']

    for id_ in existing:
        getDepth(id_)

    print(sorted(depths.values()))

    def key_(id_):
        return depths[id_]

    return sorted(depths, key=key_)

def replaceFile(filename):
    readFile(filename)
    
@managed('rt')
def ilxDoReplace(mg, TEMP_INDEX=None):
    mg.add_known_namespace('ILX')
    mg.del_namespace('ILXREPLACE')
    for temp_id, record in TEMP_INDEX.items():
        if not record['ilx']:
            print('%s is missing a real ilx id. Please make sure you have run ilxGetRealId on all entires for %s' % (temp_id, mg.ontid))
        mg.replace_uriref(temp_id, record['ilx'])
    mg.write()

    if ilxDoReplace.__globals__['FIRST']:
        ilxDoReplace.__globals__['FIRST'] = False
        #embed()

def ilx_json_to_tripples(j):  # this will be much eaiser if everything can be exported as a relationship or an anotation
    g = makeGraph('do not write me', prefixes=makePrefixes('ILX', 'ilx', 'owl', 'skos', 'OBOANN'))
    def pref(inp): return makePrefixes('ilx')['ilx'] + inp
    id_ =  pref(j['ilx'])
    type_ = {'term':'owl:Class','relationship':'owl:ObjectProperty','annotation':'owl:AnnotationProperty'}[j['type']]
    out = []  # TODO need to expand these
    out.append( (id_, rdflib.RDF.type, type_) )
    out.append( (id_, rdflib.RDFS.label, j['label']) )
    out.append( (id_, 'skos:definition', j['definition']) )
    for syndict in j['synonyms']:
        out.append( (id_, 'OBOANN:synonym', syndict['literal']) )
    for superdict in j['superclasses']:  # should we be returning the preferred id here not the ilx? or maybe that is a different json output?
        out.append( (id_, rdflib.RDFS.subClassOf, pref(superdict['ilx'])) )
    for eid in j['existing_ids']:
        out.append( (id_, 'ilx:someOtherId', eid['iri']) )  # predicate TODO
    [g.add_node(*o) for o in out]
    return g.g.serialize(format='nifttl')  # other formats can be choosen

def main():
    #with open('ilxjson.json', 'rt') as f:
        #a = ilx_json_to_tripples(json.load(f))
        #print(a.decode())
    #return
    if not os.path.exists(__FILENAME):
        with open(__FILENAME, 'wt') as f:
            json.dump({}, f)

    ILXREPLACE('wowzers')
    ILXREPLACE('are you joking')
    ilxGetRealId(ILXREPLACE('wowzers'), 'http://FIXME.org/thing.ttl')
    #return
    for file in glob('/home/tom/git/NIF-Ontology/ttl/generated/parcellation/*.ttl'):
        ilxGet(file)
    ilxGet('/home/tom/git/NIF-Ontology/ttl/generated/parcellation.ttl')

if __name__ == '__main__':
    main()
