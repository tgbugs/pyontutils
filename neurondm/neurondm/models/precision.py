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
    shortname = 'prepain'
    _no_origLabel_hack = True


from sparcur.sheets import Sheet
class PRE(Sheet):
    _do_cache = True
    _re_cache = True
    name = 'npo-precision'
    sheet_name = 'NPO-Template (Individual cell types/species)'

from pyontutils.sheets import Row

def _subject_uri(self):
    nid = self.neuron_id()
    v = nid.value
    if v and not v.startswith('http://'):
        nid.value = 'http://uri.interlex.org/tgbugs/uris/readable/neurons/precision/' + v.lower().replace(' ', '/')

    return nid

def _proposed_action(self):
    return self.neuron_id()

def _predicate_uri(self):
    #return self.relation_type()
    return self.npo_property()

def _object_uri(self):
    return self.npo_property_value_iri()

def _object(self):
    return self.property_value_label()

Row.subject_uri = _subject_uri
Row.proposed_action = _proposed_action
Row.predicate_uri = _predicate_uri
Row.object_uri = _object_uri
Row.object = _object


def main():
    config = Config('precision')
    cs = [PRE()]
    nlp_main(cs=cs, config=config, neuron_class=NeuronPrecision)
    nrns = config.neurons()
    breakpoint()


if __name__ == '__main__':
    main()
