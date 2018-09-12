""" Maps external ontology predicates to interlex predicates if there is a one.
AUTHOR: Troy Sincomb
"""
from sys import exit
from ilxutils.tools import *


class IlxPredMap:
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

    def get_common_pred(self, pred):
        ''' Gets version of predicate and sees if we have a translation to a common relation.
            INPUT:
                pred = predicate from the triple
            OUTPUT:
                Common relationship or None
        '''
        pred = pred.lower().strip()
        if 'http' in pred:
            pred = pred.split('/')[-1]
        elif ':' in pred:
            if pred[-1] != ':': # some matches are "prefix:" only
                pred = pred.split(':')[-1]
        else:
            exit('Not a valid predicate: ' + pred + '. Needs to be an iri "/" or curie ":".')
        common_pred = self.pred2common.get(pred)
        return common_pred

def main():
    ipm = IlxPredMap()
    print(ipm.pred2common)


if __name__ == '__main__':
    main()
