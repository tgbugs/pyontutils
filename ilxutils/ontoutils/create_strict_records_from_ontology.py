from sys import exit
from tools import open_json

class Ontology2DataFrame():

    query = """
        select ?subj ?pred ?obj
        where {
            ?subj rdf:type ?type .
            ?subj ?pred ?obj .
        } """

    def __init__(self, ontology):
        self.g = ontology  # could be path
        self.path = ontology  # could be graph
        self.rqname = {}
        self.df = self.ontology2df()

    def eval_type(self, _type):
        if _type.lower().strip() == 'all':
            return '?type'
        else:
            return _type

    def qname(self, uri):
        '''Returns qname of uri in rdflib graph while also saving it'''
        try:
            prefix, namespace, name = self.g.compute_qname(uri)
            qname = prefix + ':' + name
            self.rqname[qname] = uri
            return qname
        except:
            try:
                print('prefix:', prefix)
                print('namespace:', namespace)
                print('name:', name)
            except:
                print('Could not print from compute_qname')
            exit('No qname for ' + uri)

    def ontology2df(self):
        '''Updates self.g or self.path bc you could only choose 1'''

        if isinstance(self.path, str) or isinstance(self.path, p):
            self.path = str(self.path)
            filetype = p(self.path).suffix
            if filetype == '.json':
                self.g = None
                try:
                    records = open_json(self.path)
                    return pd.DataFrame(records)
                except:
                    exit('Json file is not in records format.')
            if filetype == '.pickle':
                self.g = None
                return pickle.load(open(self.path, 'rb'))
            elif filetype == '.ttl' or filetype == '.rdf':
                self.g = rdflib.Graph()
                self.g.parse(self.path, format='turtle')
                return self.get_sparql_dataframe()
            elif filetype == '.nt':
                self.g = rdflib.Graph()
                self.g.parse(self.path, format='nt')
                return self.get_sparql_dataframe()
            elif filetype == '.owl' or filetype == '.xrdf':
                self.g = rdflib.Graph()
                try:
                    self.g.parse(self.path, format='xml')
                except:
                    # some owl formats are more rdf than owl
                    self.g.parse(self.path, format='turtle')
                return self.get_sparql_dataframe()
            else:
                exit('Format options: owl, ttl, df_pickle, rdflib.Graph()')
            try:
                return self.get_sparql_dataframe()
                self.path = None
            except:
                exit('Format options: owl, ttl, df_pickle, rdflib.Graph()')

        elif isinstance(self.g, rdflib.graph.Graph):
            self.path = None
            return self.get_sparql_dataframe()

        else:
            exit('Obj given is not str, pathlib obj, or an rdflib.Graph()')

    def get_sparql_dataframe(self):
        self.result = self.g.query(self.query)

        cols = set(['qname'])
        indx = set()
        data = {}

        for i, binding in enumerate(self.result.bindings):

            subj_binding = binding[rdflib.term.Variable('subj')]
            pred_binding = binding[rdflib.term.Variable('pred')]
            obj_binding  = binding[rdflib.term.Variable('obj')]

            subj = subj_binding
            pred = self.qname(pred_binding)
            obj  = obj_binding

            # stops at BNodes; could be exanded here
            if isinstance(subj, BNode):
                continue
            elif isinstance(pred, BNode):
                continue
            elif isinstance(obj, BNode) and obj:
                continue
            else:
                subj = str(subj)
                pred = str(pred)
                obj  = str(obj)

            # Prepare defaultdict home if it doesn't exist
            if not data.get(subj):
                data[subj] = defaultdict(list)
                # I really dont think i need this...
                # data[subj]['qname'] = self.qname(subj_binding)

            data[subj][pred].append(obj)
            cols.add(pred)
            indx.add(subj)

        # Building DataFrame
        df = pd.DataFrame(columns=cols, index=indx)
        for key, value in data.items():
            df.loc[str(key)] = pd.Series(value)

        del data

        return df


class CommonPredMap:

    common2preds = {
        'label': [
            'label',
            'prefLabel',
            'preferred_name',
            'altLabel',
            'casn1_label',
        ],
        'definition': [
            'definition',
            'definition:',
            'birnlexDefinition',
            'externallySourcedDefinition',
            'IAO_0000115',
        ],
        'synonym': [
            'hasExactSynonym',
            'hasNarrowSynonym',
            'hasBroadSynonym',
            'hasRelatedSynonym',
            'systematic_synonym',
            'synonym',
        ],
        'superclass': [
            'subClassOf',
        ],
        'type': [
            'type',
        ],
        'existing_ids': [
            'existingIds',
            'existingId',
        ],
    }

    def __init__(self):
        self.create_pred2common()

    def create_pred2common(self):
        ''' Takes list linked to common name and maps common name to accepted predicate
            and their respected suffixes to decrease sensitivity.
        '''
        self.pred2common = {}
        for common_name, ext_preds in self.common2preds.items():
            for pred in ext_preds:
                pred = pred.lower().strip()
                self.pred2common[pred] = common_name

    def clean_pred(self, pred, ignore_warning=False):
        ''' Takes the predicate and returns the suffix, lower case, stripped version
        '''
        original_pred = pred
        pred = pred.lower().strip()
        if 'http' in pred:
            pred = pred.split('/')[-1]
        elif ':' in pred:
            if pred[-1] != ':': # some matches are "prefix:" only
                pred = pred.split(':')[-1]
        else:
            if not ignore_warning:
                exit('Not a valid predicate: ' + original_pred + '. Needs to be an iri "/" or curie ":".')
        return pred

    def get_common_pred(self, pred):
        ''' Gets version of predicate and sees if we have a translation to a common relation.
            INPUT:
                pred = predicate from the triple
            OUTPUT:
                Common relationship or None
        '''
        pred = self.clean_pred(pred)
        common_pred = self.pred2common.get(pred)
        return common_pred

    def accepted_pred(self, pred, extras=[]):
        if self.get_common_pred(pred):
            return True
        if extras:
            pred = self.clean_pred(pred)
            extras = [e.lower().strip() for e in extras]
            if pred in extras:
                return True
        return False


class CleanOntology(CommonPredMap, Ontology2DataFrame):

    def __init__(self, ontology):
        CommonPredMap.__init__(self)
        Ontology2DataFrame.__init__(self):


    for i, row in mesh.iterrows():
        row = row[~row.isnull()]
        for pred, objs in row.items():
            if ipm.accepted_pred(pred, extras=extras):
                pred = ipm.clean_pred(pred, ignore_warning=True)
                cols.add(pred)

    records = []
    for i, row in mesh.iterrows():
        row = row[~row.isnull()]
        row.pop('qname')
        data = {p:None for p in cols}
        for pred, objs in row.items():
            if ipm.accepted_pred(pred, extras=extras):
                pred = ipm.clean_pred(pred, ignore_warning=True)
                data[pred] = objs
        data['code'] = row.name.rsplit('/', 1)[-1]
        records.append(data)
