""" Interlex add Triple for examples. Will have the same post triple commands for real ILX.

    Notes:
    1. In beta some old and all new ILX IDs are TMP: prefix instead
    2. To install go into the 1st ilxutils directory and run pip3 setup.py install
    3. cli.log will be created in your current directory (info and errors created per line)

Usage:
    interlex post entity <rdf:type> <rdfs:sub*Of> <rdfs:label> [<definition:>]
    interlex post triple <subject> <predicate> <object>
    interlex get <identifier>

Examples:
    export INTERLEX_API_KEY=$(cat path/to/my/api/key)
    export INTERLEX_API_KEY=your_key_without_quotes

    interlex post entity "term" ILX:0101431 "magical neuron"
    interlex post triple ILX:1234567 definition: "entities definition"

    # annotation logic -> <term_ilx> <annotation_ilx> <str>
    interlex post triple ILX:1234567 ILX:1234568 "annotation value"

    # relationship logic -> <term1_ilx> <relationship_ilx> <term2_ilx>
    interlex post triple ILX:1234567 ILX:1234568 ILX:1234569

    interlex get ILX:0101431

Commands:
    post triple     post a triple for give user
    post entity     create new entity in interlex
    get             requests data from the ilx identifier provided
"""
from docopt import docopt
from IPython import embed
import json
import logging
import os
import requests as r
from sys import exit
VERSION = '0.0.1'
logging.basicConfig(filename='cli.log',level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING) # removes noise


def superclasses_bug_fix(data):
    ''' PHP returns "id" in superclass but only accepts superclass_tid '''
    for i, value in enumerate(data['superclasses']):
        data['superclasses'][i]['superclass_tid'] = data['superclasses'][i].pop('id')
    return data


def label_bug_fix(label):
    ''' PHP error currently in beta.scicrunch.org '''
    return label.replace('"', '&#34;').replace("'", '&#39;')


class Client:

    ttl2sci_map = {
        'rdf:type': 'type',
        'rdfs:label': 'label',
        'definition:': 'definition',
        'rdfs:subClassOf': 'superclasses',
        'rdfs:subProperty': 'superclass',
        'comment': 'comment',
        'NIFRID:synonym': 'synonyms',
        # 'ilxtr:existingId': 'existing_ids', # too unorganized for this
    }

    def __init__(self, test=False):
        self.test = test # True to bypass printing specific errors and just getting raw error
        self.auth = ('scicrunch', 'perl22(query)')  # for test2.scicrunch.org
        self.headers = {'Content-type': 'application/json'}
        self.base_path = 'https://beta.scicrunch.org/api/1/'
        self.APIKEY = os.environ.get('INTERLEX_API_KEY')

    def log_info(self, data):
        info = 'label={label}, id={id}, ilx={ilx}, superclass_tid={super_id}'
        info_filled = info.format(label=data['label'],
                                  id=data['id'],
                                  ilx=data['ilx'],
                                  super_id=data['superclasses'][0]['superclass_tid'])
        logging.info(info_filled)
        return info_filled

    def log_error(self, error):
        logging.error(error)
        exit(error)

    def get(self, url):
        req = r.get(url, headers=self.headers, auth=self.auth)
        return self.process_request(req)

    def post(self, url, data):
        data.update({'key': self.APIKEY})
        req = r.post(url, data=json.dumps(data),
                     headers=self.headers, auth=self.auth)
        return self.process_request(req)

    def process_request(self, req):
        req.raise_for_status() # cant general check. Duplicates return 400s
        try:
            output = req.json()
        except:
            exit(req.text)
        try:
            error = output['data'].get('errormsg')
        except:
            error = output.get('errormsg')
        finally:
            if error:
                exit(error)
            return output

    def is_equal(self, string1, string2):
        return string1.lower().strip() == string2.lower().strip()

    def test_check(self, error):
        if self.test:
            return 'failed'
        else:
            self.log_error(error)

    def fix_ilx(self, ilx_id):
        return ilx_id.replace('ILX:', 'ilx_').replace('TMP:', 'tmp_')

    def check_success(self, output):
        if output['data'].get('ilx'):
            return True
        else:
            return False

    def get_data_from_ilx(self, ilx_id):
        ilx_id = self.fix_ilx(ilx_id)
        url_base = self.base_path + \
            "ilx/search/identifier/{identifier}?key={APIKEY}"
        url = url_base.format(identifier=ilx_id,
                              APIKEY=self.APIKEY)
        output = self.get(url)

        success = self.check_success(output)
        return output, success

    def search_by_label(self, label):
        url_base = self.base_path + 'term/search/{term}?key={api_key}'
        url = url_base.format(term=label, api_key=self.APIKEY)
        return self.get(url)

    def are_ilx(self, ilx_ids):
        total_data = []
        for ilx_id in ilx_ids:
            ilx_id = ilx_id.replace('http', '').replace('.', '').replace('/', '')
            data, success = self.get_data_from_ilx(ilx_id)
            if success:
                total_data.append(data['data'])
            else:
                total_data.append({})
        return total_data

    def add_triple(self, subj, pred, obj):
        subj_data, pred_data, obj_data = self.are_ilx([subj, pred, obj])
        # RELATIONSHIP PROPERTY
        if subj_data.get('id') and pred_data.get('id') and obj_data.get('id'):
            if pred_data['type'] != 'relationship':
                return self.test_check('Adding a relationship as formate \
                                       "term1_ilx relationship_ilx term2_ilx"')
            return self.add_relationship(term1=subj_data,
                                         relationship=pred_data,
                                         term2=obj_data)
        # ANNOTATION PROPERTY
        elif subj_data.get('id') and pred_data.get('id'):
            if pred_data['type'] != 'annotation':
                return self.test_check('Adding a relationship as formate \
                                       "term_ilx annotation_ilx value"')
            return self.add_annotation(entity=subj_data,
                                       annotation=pred_data,
                                       value=obj)
        # UPDATE ENTITY
        elif subj_data.get('id'):
            data = subj_data
            _pred = self.ttl2sci_map.get(pred)
            if not _pred:
                error = pred + " doesnt not have correct RDF format or It is not an option"
                return self.test_check(error)
            data = self.custom_update(data, _pred, obj)
            if data == 'failed':  # for debugging custom_update
                return data
            data = superclasses_bug_fix(data)
            url_base = self.base_path + 'term/edit/{id}'
            url = url_base.format(id=data['id'])
            return self.post(url, data)
        else:
            return self.test_check('The ILX ID(s) provided do not exist')

    def add_relationship(self, term1, relationship, term2):
        url = self.base_path + 'term/add-relationship'
        data = {'term1_id': term1['id'],
                'relationship_tid': relationship['id'],
                'term2_id': term2['id'],
                'term1_version': term1['version'],
                'relationship_term_version': relationship['version'],
                'term2_version': term2['version']}
        return self.post(url, data)

    def add_annotation(self, entity, annotation, value):
        url = self.base_path + 'term/add-annotation'
        data = {'tid': entity['id'],
                'annotation_tid': annotation['id'],
                'value': value,
                'term_version': entity['version'],
                'annotation_term_version': annotation['version']}
        return self.post(url, data)

    def custom_update(self, data, pred, obj):
        if isinstance(data[pred], str):
            data[pred] = str(obj)
        else:
            if pred == 'synonyms':
                literals = [d['literal'] for d in data[pred]]
                if obj not in literals:
                    data[pred].append({'literal': obj})
            elif pred == 'superclasses':
                ilx_ids = [d['ilx'] for d in data[pred]]
                if obj not in ilx_ids:
                    _obj = obj.replace('ILX:', 'ilx_')
                    super_data, success = self.get_data_from_ilx(ilx_id=_obj)
                    super_data = super_data['data']
                    if success:
                        data[pred].append({'id': super_data['id'], 'ilx': _obj})
                    else:
                        return self.test_check('Your superclass ILX ID '
                                                + _obj + ' does not exist.')
            elif pred == 'existing_ids':  # FIXME need to autogenerate curies from a map
                iris = [d['iri'] for d in data[pred]]
                if obj not in iris:
                    if 'http' not in obj:
                        return self.test_check('exisiting id value must \
                                               be a uri containing "http"')
                    data[pred].append({
                        'curie': self.qname(obj),
                        'iri': obj,
                        'preferred': '0'
                    })
                data = self.preferred_change(data)
            else:
                return self.test_check(pred + ' Has slipped through the cracks')
        return data

    # FIXME: need to sql all curie to iri mappings and put them here
    def qname(self, iri):
        return 'dummy:' + iri.rsplit('/', 1)[-1]

    def preferred_change(self, data):
        ranking = [
            'CHEBI',
            'NCBITaxon',
            'COGPO',
            'CAO',
            'DICOM',
            'UBERON',
            'NLX',
            'NLXANAT',
            'NLXCELL',
            'NLXFUNC',
            'NLXINV',
            'NLXORG',
            'NLXRES',
            'NLXSUB'
            'BIRNLEX',
            'SAO',
            'NDA.CDE',
            'PRO',
            'NIFEXT',
            'ILX',
        ]
        mock_rank = ranking[::-1]
        score = []
        old_pref_index = None
        for i, d in enumerate(data['existing_ids']):
            if int(d['preferred']) == 1:
                old_pref_index = i
            if d.get('curie'):
                pref = d['curie'].split(':')[0]
                if pref in mock_rank:
                    score.append(mock_rank.index(pref))
                else:
                    score.append(-1)
            else:
                score.append(-1)

        new_pref_index = score.index(max(score))
        new_pref_iri = data['existing_ids'][new_pref_index]['iri']
        if new_pref_iri.rsplit('/', 1)[0] == 'http://uri.interlex.org/base':
            if old_pref_index:
                if old_pref_index != new_pref_index:
                    return data
        for e in data['existing_ids']:
            e['preferred'] = 0
        data['existing_ids'][new_pref_index]['preferred'] = 1
        return data

    def add_entity(self, rdf_type, superclass, label, definition=None):

        # Checks if you inputed the right type
        rdf_type = rdf_type.lower().strip().replace('owl:Class', 'term')
        accepted_types = ['owl:Class', 'term', 'cde', 'annotation', 'relationship', 'fde']
        if rdf_type not in accepted_types:
            error = 'rdf_type must be one of the following: {accepted_types}'
            return self.test_check(error.format(accepted_types=accepted_types))

        # Pulls superclass data out and checks if it exists
        superclass_data, success = self.get_data_from_ilx(ilx_id=superclass)
        superclass_data = superclass_data['data']
        if not success:
            error = '{superclass} is does not exist and cannot be used as a superclass.'
            return self.test_check(error.format(superclass=superclass))

        # Searchs database to see if the term exists. Will return anything similar,
        # but we want only what is_equal
        search_results = self.search_by_label(label)['data']
        search_results = [sr for sr in search_results
                          if self.is_equal(sr['label'], label_bug_fix(label))]

        # If search_results is not empty, we need to see if the type and superclass are also a
        # match. If not, you can create this entity. HOWEVER. If you are the creator of an entity,
        # you can only have one label of any type or superclass
        if search_results:
            search_hits = 0
            for entity in search_results: # garunteed to only have one match if any
                entity, success = self.get_data_from_ilx(ilx_id=entity['ilx']) # get all the metadata
                entity = entity['data']
                user_url = 'https://scicrunch.org/api/1/user/info?key={api_key}'
                user_data = self.get(user_url.format(api_key=self.APIKEY))
                user_data = user_data['data']
                if str(entity['uid']) == str(user_data['id']): # creator check
                    bp = 'Entity {label} already created by you with ILX ID {ilx_id} and of type {rdf_type}'
                    return self.test_check(bp.format(label=label,
                                                     ilx_id=entity['ilx'],
                                                     rdf_type=entity['type']))
                types_equal = self.is_equal(entity['type'], rdf_type) # type check
                entity_super_ilx = entity['superclasses'][0]['ilx'] if 'superclasses' in entity and entity['superclasses'] else ''
                supers_equal = self.is_equal(entity_super_ilx, superclass_data['ilx'])
                if types_equal and supers_equal:
                    bp = 'Entity {label} already exisits with ILX ID {ilx_id} and of type {rdf_type}'
                    return self.test_check(bp.format(label=label,
                                                     ilx_id=self.fix_ilx(entity['ilx']),
                                                     rdf_type=entity['type']))

        # Generates ILX ID and does a validation check
        url = self.base_path + 'ilx/add'
        data = {'term': label,
                'superclasses': [{
                    'id': superclass_data['id'],
                    'ilx': superclass_data['ilx']}],
                'type': rdf_type,}
        data = superclasses_bug_fix(data)
        output = self.post(url, data)['data']
        if output.get('ilx'):
            ilx_id = output['ilx']
        else:
            ilx_id = output['fragment']  # archetype of beta

        # Uses generated ILX ID to make a formal row in the database
        url = self.base_path + 'term/add'
        data = {'label': label.replace('&#39;', "'").replace('&#34;', '"'),
                'ilx': ilx_id,
                'superclasses': [{
                    'id': superclass_data['id'],
                    'ilx': superclass_data['ilx']}],
                'type': rdf_type}
        data = superclasses_bug_fix(data)
        if definition:
            data.update({'definition':definition})
        return self.post(url, data)


def main():
    doc = docopt(__doc__, version=VERSION)

    client = Client()
    if doc.get('triple'):
        response = client.add_triple(subj = doc['<subject>'],
                                    pred = doc['<predicate>'],
                                    obj  = doc['<object>'])
    elif doc.get('entity'):
        response = client.add_entity(rdf_type   = doc['<rdf:type>'],
                                    superclass = doc['<rdfs:sub*Of>'],
                                    label      = doc['<rdfs:label>'],
                                    definition = doc['<definition:>'])
    elif doc.get('get'):
        response, success = client.get_data_from_ilx(doc['<identifier>'])
    else:
        response = {'data':''}

    print(client.log_info(response['data']))


if __name__ == '__main__':
    main()
