""" Maps external ontology predicates to interlex predicates if there is a one.
AUTHOR: Troy Sincomb
"""
from sys import exit
from ilxutils.tools import *
from typing import Dict, List, NewType, Union


class IlxPredMap:

    common2preds = {
        'label': [
            'label',
            'prefLabel',
        ],
        'definition': [
            'definition',
            'definition:',
            'birnlexDefinition',
            'externallySourcedDefinition',
            'IAO_0000115',
            'isDefinedBy',
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
            'superclasses',
            'superclass',
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

    def get_fragment_id(self, iri: str) -> str:
        # simulate a fragmented id
        _id = iri.rsplit('/', 1)[-1]
        if '=' in _id:
            _id = _id.rsplit('=', 1)[-1]
        elif '#' in _id:
            _id = _id.rsplit('#', 1)[-1]
        elif '_' in _id:
            _id = _id.rsplit('_', 1)[-1]
        return _id

    def clean_pred(self, pred):
        ''' Takes the predicate and returns the suffix, lower case, stripped version
        '''
        original_pred = pred
        pred = pred.lower().strip()
        if 'http' in pred:
            pred = self.get_fragment_id(pred)
        elif ':' in pred:
            if pred[-1] != ':': # some matches are "prefix:" only
                pred = pred.split(':')[-1]
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

    def expand_accepted_preds(self, accepted_preds):
        for pred, objs in accepted_preds.items():
            pred = pred.lower().strip()
            if self.common2preds.get(pred):
                for obj in objs:
                    obj = obj.lower().strip()
                    if self.pred2common.get(obj):
                        exit(obj + ': already exists in pred2common')
                    self.pred2common[obj] = pred
            else:
                print('WARNING:', pred, 'is not in common2preds so nothing will change.')


def main():
    ipm = IlxPredMap()
    print(ipm.pred2common)


if __name__ == '__main__':
    main()
