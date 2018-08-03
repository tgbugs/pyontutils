""" Interlex add Triple for examples. Will have the same post triple commands for real ILX.

Usage:
    interlex post entity <rdf:type> <rdfs:subClassOf> <rdfs:label>
    interlex post triple <subject> <predicate> <object>

Examples:
    >>> export INTERLEX_API_KEY=$(cat path/to/my/api/key)
    >>> export INTERLEX_API_KEY=your_key_without_quotes

    >>> interlex post entity "term" ILX:0101431 "magical neuron"
    output: 'Entity <rdfs:label> was created with ILX ID <ilx_id> and of type <rdfs:type>'

    >>> interlex post triple ILX:1234567 definition: "entities definition"

    # annotation logic -> <term_ilx> <annotation_ilx> <str>
    >>> interlex post triple ILX:1234567 ILX:1234568 "annotation value"

    # relationship logic -> <term1_ilx> <relationship_ilx> <term2_ilx>
    >>> interlex post triple ILX:1234567 ILX:1234568 ILX:1234569

Commands:
    post triple     post a triple for give user
    post entity     create new entity in interlex
"""
from docopt import docopt
from IPython import embed
import json
import os
import requests as r
from sys import exit
VERSION = '0.0.1'


def superclasses_bug_fix(data):
    # BUG: need to make a real post about this so James can fix it
    for i, value in enumerate(data['superclasses']):
        data['superclasses'][i]['superclass_tid'] = data['superclasses'][i].pop('id')
    return data

def label_bug_fix(label):
    return label.replace('"', '&#34;').replace("'", '&#39;')

class Client:

    ttl2sci_map = {
        'rdf:type' : 'type',
        'rdfs:label': 'label',
        'definition:': 'definition',
        'rdfs:subClassOf': 'superclasses',
        'comment': 'comment',
        'NIFRID:synonym': 'synonyms',
        #'ilxtr:existingId': 'existing_ids', # too unorganized for this
    }

    def __init__(self):
        self.auth = ('scicrunch', 'perl22(query)')  # for test2.scicrunch.org
        self.headers = {'Content-type': 'application/json'}
        self.base_path = 'https://beta.scicrunch.org/api/1/'
        self.APIKEY = os.environ.get('INTERLEX_API_KEY')

    def get(self, url):
        req = r.get(url, headers=self.headers, auth=self.auth)
        return self.process_request(req)

    def post(self, url, data):
        data.update({'key': self.APIKEY})
        req = r.post(url, data=json.dumps(data),
                     headers=self.headers, auth=self.auth)
        return self.process_request(req)

    def process_request(self, req):
        req.raise_for_status()
        output = req.json()
        try:
            error = output['data'].get('errormsg')
        except:
            error = output.get('errormsg')
        finally:
            if error:
                exit(error)
            return output

    def fix_ilx(self, ilx_id):
        return ilx_id.replace('ILX:', 'ilx_')

    def get_data_from_ilx(self, ilx_id):
        url_base = self.base_path + \
            "ilx/search/identifier/{identifier}?key={APIKEY}"
        url = url_base.format(identifier=ilx_id.replace('ILX:', 'ilx_'),
                              APIKEY=self.APIKEY)
        return self.get(url)['data']

    def search_by_label(self, label):
        url_base = self.base_path + 'term/search/{term}?key={api_key}'
        url = url_base.format(term=label, api_key=self.APIKEY)
        return self.get(url)

    def are_ilx(self, ilx_ids):
        total_data = []
        for ilx_id in ilx_ids:
            ilx_id = ilx_id.replace('http', '').replace('.', '').replace('/', '')
            data = self.get_data_from_ilx(ilx_id)
            if data.get('id'):
                total_data.append(data)
            else:
                total_data.append({})
        return total_data

    def add_triple(self, triple, debug=False):
        subj, pred, obj = triple
        subj_data, pred_data, obj_data = self.are_ilx([subj, pred, obj])
        # RELATIONSHIP PROPERTY
        if subj_data.get('id') and pred_data.get('id') and obj_data.get('id'):
            if pred_data['type'] != 'relationship':
                if debug:
                    return 'failed'
                else:
                    exit('Adding a relationship as formate "term1_ilx relationship_ilx term2_ilx"')
            return self.add_relationship(term1=subj_data, relationship=pred_data, term2=obj_data, debug=debug)
        # ANNOTATION PROPERTY
        elif subj_data.get('id') and pred_data.get('id'):
            if pred_data['type'] != 'annotation':
                if debug:
                    return 'failed'
                else:
                    exit('Adding a relationship as formate "term_ilx annotation_ilx value"')
            return self.add_annotation(entity=subj_data, annotation=pred_data, value=obj, debug=debug)
        # UPDATE ENTITY
        elif subj_data.get('id'):
            data = subj_data
            pred = self.ttl2sci_map.get(pred)
            if not pred:
                if debug:
                    return 'failed'
                else:
                    exit(pred + ' doesn not have correct RDF format or It is not an option')
            data = self.custom_update(data, pred, obj, debug=debug)
            if data == 'failed':  # for debugging custom_update
                return data
            data = superclasses_bug_fix(data)
            url_base = self.base_path + 'term/edit/{id}'
            url = url_base.format(id=data['id'])
            output = self.post(url, data)
            if debug:
                return 'success'
            else:
                print('success')
        else:
            if debug:
                return 'failed'
            else:
                exit('The ILX ID(s) provided do not exist')

    def add_relationship(self, term1, relationship, term2, debug=False):
        url = self.base_path + 'term/add-relationship'
        data = {'term1_id': term1['id'],
                'relationship_tid': relationship['id'],
                'term2_id': term2['id'],
                'term1_version': term1['version'],
                'relationship_term_version': relationship['version'],
                'term2_version': term2['version']}
        output = self.post(url, data)
        if debug:
            return 'success'
        else:
            print('success')

    def add_annotation(self, entity, annotation, value, debug=False):
        url = self.base_path + 'term/add-annotation'
        data = {'tid':entity['id'],
                'annotation_tid':annotation['id'],
                'value':value,
                'term_version':entity['version'],
                'annotation_term_version':annotation['version']}
        output = self.post(url, data)
        if debug:
            return 'success'
        else:
            print('success')

    def custom_update(self, data, pred, obj, debug=False):
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
                    super_data = self.get_data_from_ilx(ilx_id=_obj)
                    if super_data.get('id'):
                        data[pred].append({'id': super_data['id'], 'ilx': _obj})
                    else:
                        if debug:
                            return 'failed'
                        else:
                            exit('Your superclass ILX ID' + _obj + ' does not exist.')
            elif pred == 'existing_ids':  # FIXME need to autogenerate curies from a map
                iris = [d['iri'] for d in data[pred]]
                if obj not in iris:
                    if 'http' not in obj:
                        if debug:
                            return 'failed'
                        else:
                            exit('exisiting id value must be a uri containing "http"')
                    data[pred].append({'curie': self.qname(obj), 'iri': obj, 'preferred': '0'})
                data = self.preferred_change(data)
            else:
                if debug:
                    return 'failed'
                else:
                    exit(pred + ' Has slipped through the cracks')
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

    def add_entity(self, triple, debug=False):
        rdf_type, superclass, label = triple

        bp = 'Entity {label} already exisits with ILX ID {ilx_id} and of type {rdf_type}'
        pp = 'Entity {label} was created with ILX ID {ilx_id} and of type {rdf_type}'
        accepted_types = ['term', 'cde', 'annotation', 'relationship', 'fde']
        if rdf_type not in accepted_types:
            if debug:
                return 'failed'
            else:
                exit('rdf_type must be one of the following: ' + accepted_types)
        _super = self.fix_ilx(superclass)
        _super_data = self.get_data_from_ilx(ilx_id=_super)
        if not _super_data['id']:
            if debug:
                return 'failed'
            else:
                exit(superclass + ' is does not exist and cannot be used as a superclass.')

        data = self.search_by_label(label)['data']
        # TODO: ' or " converted and then algo search says it doesnt exists if inputed again
        ex_pre_data = [d for d in data if self.is_equal(d['label'], label_bug_fix(label))] if data else None

        if ex_pre_data:
            ex_pre_data = ex_pre_data[0]
            ex_data = self.get_data_from_ilx(ilx_id=ex_pre_data['ilx'])
            ex_super = ex_data['superclasses']
            ex_uid = ex_data['uid']
            user_url = 'https://scicrunch.org/api/1/user/info?key={api_key}'
            user_data = self.get(user_url.format(api_key=self.APIKEY))['data']
            if str(ex_data['uid']) == str(user_data['id']):
                if debug:
                    return 'failed'
                else:
                    exit(bp.format(label=label,
                                   ilx_id=ex_data['ilx'],
                                   rdf_type=ex_data['type']))
            ex_super_ilx = ex_data['ilx'] if ex_super else ''
            types_equal = self.is_equal(ex_data['type'], rdf_type)
            supers_equal = self.is_equal(ex_super_ilx, _super_data['ilx'])
            if not types_equal or not supers_equal:
                ex_data = None
        else:
            ex_data = None

        if ex_data:
            if debug:
                return 'failed'
            else:
                exit(bp.format(label=label,
                               ilx_id=self.fix_ilx(ex_data['ilx']),
                               rdf_type=ex_data['type']))
        else:
            url = self.base_path + 'ilx/add'
            data = {'term': label,
                    'superclasses': [{'ilx': self.fix_ilx(superclass)}],
                    'type': rdf_type}
            output = self.post(url, data)['data']
            if output.get('ilx'):
                ilx_id = output['ilx']
            else:
                ilx_id = output['fragment']  # archetype of beta
            url = self.base_path + 'term/add'
            data = {'label': label.replace('&#39;', "'").replace('&#34;', '"'),
                    'ilx': ilx_id,
                    'superclasses': [{'ilx': self.fix_ilx(superclass)}],
                    'type': rdf_type}
            output = self.post(url, data)
            if debug:
                if output['success']:
                    return output
                else:
                    return 'failed'
            else:
                print(pp.format(label=output['data']['label'],
                                ilx_id=output['data']['ilx'],
                                rdf_type=output['data']['type']))

    def is_equal(self, string1, string2):
        return string1.lower().strip() == string2.lower().strip()


def main():
    doc = docopt(__doc__, version=VERSION)
    client = Client()
    if doc.get('triple'):
        triple = (doc['<subject>'],
                  doc['<predicate>'],
                  doc['<object>'])
        client.add_triple(triple)
    elif doc.get('entity'):
        triple = (doc['<rdf:type>'],
                  doc['<rdfs:subClassOf>'],
                  doc['<rdfs:label>'])
        client.add_entity(triple)


if __name__ == '__main__':
    main()
