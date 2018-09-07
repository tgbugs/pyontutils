""" Maps external ontology predicates to interlex predicates if there is a one.
"""
from ilxutils.tools import *


class IlxPredMap:
    ilx2ext_map = {
        'label':
            ['rdfs:label',
             'skos:prefLabel',
             'preferred_name',
             'altLabel',
             'casn1_label',],
        'definition':
            ['definition:',
             'skos:definition',
             'NIFRID:birnlexDefinition',
             'NIFRID:externallySourcedDefinition',
             'obo:IAO_0000115', ],
        'synonym':
            ['oboInOwl:hasExactSynonym',
             'oboInOwl:hasNarrowSynonym',
             'oboInOwl:hasBroadSynonym',
             'oboInOwl:hasRelatedSynonym',
             'go:systematic_synonym',
             'NIFRID:synonym', ],
        'superclass':
            ['rdfs:subClassOf', ],
        'type':
            ['rdf:type', ],
        'existing_ids':
            ['ilxtr:existingIds',
             'ilxtr:existingId', ],
    }

    def __init__(self):
        self.create_ext2ilx_map()

    def create_ext2ilx_map(self):
        self.ext2ilx_map = {}
        for common_name, ext_preds in self.ilx2ext_map.items():
            for pred in ext_preds:
                self.ext2ilx_map[degrade(pred)] = common_name
                if ':' in pred:  # In case the ontology prefix not shared
                    suffix = pred.split(':')[1]
                    self.ext2ilx_map[degrade(suffix)] = common_name

    def pred_degrade(self, pred):
        pred_degraded = self.ext2ilx_map.get(degrade(pred))
        if pred_degraded:
            return pred_degraded
        elif not pred_degraded and pred[-1] != ':':
            try:
                partial_tar_com_pred = self.ext2ilx_map.get(
                    degrade(pred.split(':')[1]))
            except:
                print(pred)
                exit(degrade(pred))
            return partial_tar_com_pred
        else:
            return None


def main():
    ipm = IlxPredMap()
    print(ipm.ext2ilx_map)


if __name__ == '__main__':
    main()
