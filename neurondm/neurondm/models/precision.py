import re
from collections import defaultdict
from urllib.parse import quote as url_quote
import rdflib
from pyontutils.sheets import Sheet
from pyontutils.namespaces import ilxtr, TEMP, rdfs, skos, owl, interlex_namespace
from neurondm.core import Config, NeuronEBM, Phenotype, EntailedPhenotype, NegPhenotype, log, OntCuries, OntId, add_partial_orders, IntersectionOf
from neurondm import orders

from neurondm.models.nlp import map_predicates, main as nlp_main


class NeuronPrecision(NeuronEBM):
    owlClass = ilxtr.NeuronPrecision
    shortname = 'Precision'
    _no_origLabel_hack = True


from sparcur.sheets import Sheet
class PREOld(Sheet):
    _do_cache = True
    _re_cache = True
    name = 'npo-precision-old'
    sheet_name = 'NPO-Template (Individual cell types/species)'


class PRE(Sheet):
    _do_cache = True
    _re_cache = True
    name = 'npo-precision'
    sheet_name = 'PNS Cells to NPO'


from pyontutils.sheets import Row

def _subject_uri(self, nocite=False):
    gp = 'guinea pig'
    nid = self.neuron_id()
    if nocite and self.predicate_uri().value == 'ilxtr:literatureCitation':
        nid.value = ''
    else:
        v = nid.value
        if v and not v.startswith('http://'):
            pref = 'http://uri.interlex.org/tgbugs/uris/readable/neurons/precision/'
            if gp in v:
                v = v.replace(gp, 'guinea-pig')
            nid.value =  pref + v.lower().replace(' ', '/')

    return nid

#def _proposed_action(self):
    #return self.neuron_id()

def _predicate_uri(self):
    #return self.relation_type()
    return self.npo_property()

def _object_uri(self):
    return self.npo_property_value_iri()

def _object(self):
    if self.object_uri().value.strip():
        return self.property_value_label()
    else:
        return type('temp_cell', tuple(), {'value': ''})()

def _object_text(self):
    if not self.object_uri().value.strip():
        return self.property_value_label()
    else:
        return type('temp_cell', tuple(), {'value': ''})()

def _union_set(self):
    return self.union_set_number()

def ncbigene(nrns):
    pref = 'http://www.ncbi.nlm.nih.gov/gene/'
    c = nrns[0].out_graph.namespace_manager.curie
    ncbigene_ids = [c(p.p) for n in nrns for p in n.pes if p.p.startswith(pref)]
    print('\n'.join(ncbigene_ids))


def main():
    attrs = (
        'subject_uri',
        #'proposed_action',
        'predicate_uri',
        'object_uri',
        'object_text',
        'object',
        'union_set',
    )
    saved = {a: getattr(Row, a) for a in attrs if hasattr(Row, a)}
    Row.subject_uri = _subject_uri
    #Row.proposed_action = _proposed_action
    Row.predicate_uri = _predicate_uri
    Row.object_uri = _object_uri
    Row.object_text = _object_text
    Row.object = _object
    Row.union_set = _union_set

    #config = Config('bhuiyan-2024')
    config = Config('precision')
    NeuronEBM.out_graph.add(
        (NeuronPrecision.owlClass,
         ilxtr.modelSource,
         OntId('https://doi.org/10.1126/sciadv.adj9173').u))

    cs = [PRE()]
    nlp_main(cs=cs, config=config, neuron_class=NeuronPrecision)
    nrns = config.neurons()
    #ncbigene(nrns)

    for a in attrs:  # restore old row state
        if a in saved:
            setattr(Row, saved[a])
        else:
            delattr(Row, a)

    return config,


if __name__ == '__main__':
    main()
