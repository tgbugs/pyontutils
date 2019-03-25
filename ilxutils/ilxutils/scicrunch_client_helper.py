import sys


def superclasses_bug_fix(term_data):

    if term_data.get('superclasses'):
        for i, value in enumerate(term_data['superclasses']):
            try:
                term_data['superclasses'][i]['superclass_tid'] = term_data[
                    'superclasses'][i].pop('id')
            except:
                pass
    return term_data


def preferred_change(data):
    ''' Determines preferred existing id based on curie prefix in the ranking list '''
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
        'PR',
        'IAO',
        'NIFEXT',
        'OEN',
        'ILX',
    ]
    mock_rank = ranking[::-1]
    score = []
    old_pref_index = None
    for i, d in enumerate(data['existing_ids']):
        if not d.get('preferred'): # db allows None or '' which will cause a problem
            d['preferred'] = 0
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


def merge(new, old):
    ''' synonyms and existing_ids are part of an object bug that can create duplicates if in the same batch '''

    for k, vals in new.items():

        if k == 'synonyms':
            new_synonyms = vals
            if old['synonyms']:
                old_literals = [syn['literal'].lower().strip() for syn in old['synonyms']]
                for new_synonym in new_synonyms:
                    if new_synonym['literal'].lower().strip() not in old_literals:
                        old['synonyms'].append(new_synonym) # default is a list in SciCrunch, that's why this works without initing old['synonyms']
            else:
                old['synonyms'].extend(new['synonyms'])

        elif k == 'existing_ids':
            iris = [e['iri'] for e in old['existing_ids']]
            for new_existing_id in vals:

                new_existing_id['preferred'] = 0

                if 'change' not in list(new_existing_id):  # notion that you want to add it
                    new_existing_id['change'] = False

                if new_existing_id.get('delete') == True:
                    if new_existing_id['iri'] in iris:
                        new_existing_ids = []
                        for e in old['existing_ids']:
                            if e['iri'] != new_existing_id['iri']:
                                new_existing_ids.append(e)
                        old['existing_ids'] = new_existing_ids
                    else:
                        print(new_existing_id)
                        sys.exit("You want to delete an iri that doesn't exist")

                elif new_existing_id.get('replace') == True:
                    if not new_existing_id.get('old_iri'):
                        sys.exit(
                            'Need to have old_iri as a key to have a ref for replace'
                        )
                    old_iri = new_existing_id.pop('old_iri')
                    if old_iri in iris:
                        new_existing_ids = []
                        for e in old['existing_ids']:
                            if e['iri'] == old_iri:
                                if new_existing_id.get('curie'):
                                    e['curie'] = new_existing_id['curie']
                                if new_existing_id.get('iri'):
                                    e['iri'] = new_existing_id['iri']
                            new_existing_ids.append(e)
                        old['existing_ids'] = new_existing_ids
                    else:
                        print(new_existing_id)
                        sys.exit("You want to replace an iri that doesn't exist", '\n', new)

                else:
                    if new_existing_id['iri'] not in iris and new_existing_id['change'] == True:
                        sys.exit('You want to change iri that doesnt exist ' + str(new))
                    elif new_existing_id['iri'] not in iris and new_existing_id['change'] == False:
                        old['existing_ids'].append(new_existing_id)
                    elif new_existing_id['iri'] in iris and new_existing_id['change'] == True:
                        new_existing_ids = []
                        for e in old['existing_ids']:
                            if e['iri'] == new_existing_id['iri']:
                                if not new_existing_id.get('curie'):
                                    new_existing_id['curie'] = e['curie']
                                new_existing_ids.append(new_existing_id)
                            else:
                                new_existing_ids.append(e)
                        old['existing_ids'] = new_existing_ids
                    elif new_existing_id['iri'] in iris and new_existing_id['change'] == False:
                        pass  # for sanity readability
                    else:
                        sys.exit('Something broke while merging in existing_ids')

        elif k in ['definition', 'superclasses', 'id', 'type', 'comment', 'label', 'uid', 'ontologies']:
            old[k] = vals

        # TODO: still need to mark them... but when batch elastic for update works
        # old['uid'] = 34142  # DEBUG: need to mark as mine manually until all Old terms are fixed

    ''' REMOVE REPEATS; needs to exist due to server overloads '''
    if old.get('synonyms'):
        visited = {}
        new_synonyms = []
        for synonym in old['synonyms']:
            if not visited.get(synonym.get('literal')):
                new_synonyms.append(synonym)
                visited[synonym['literal']] = True
        old['synonyms'] = new_synonyms

    visited = {}
    new_existing_ids = []
    for e in old['existing_ids']:
        if not visited.get(e['iri']):
            new_existing_ids.append(e)
            visited[e['iri']] = True
    old['existing_ids'] = new_existing_ids
    old = preferred_change(old)

    return old

def test():
    new = {'id': 427103, 'ilx': 'ilx_0503992', 'existing_ids':
        [{'iri':'http://purl.obolibrary.org/obo/UBERON_0018412', 'curie': 'UBERON:0018412'}]}
    old = {'id': 427103, 'ilx': 'ilx_0503992', 'existing_ids':
        [{'iri':'http://purl.obolibrary.org/obo/UBERON_0018413', 'curie': 'UBERON:0018413'}]}
    merge(new, old)

if __name__ == '__main__':
    test()
