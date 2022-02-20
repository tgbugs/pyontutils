from pyontutils import sheets
from pyontutils.sheets import Sheet
from pyontutils.namespaces import ilxtr
from neurondm.sheets import CutsV1, Row as RowBase
from neurondm.core import Config, NeuronEBM
from neurondm.phenotype_namespaces import Species


class NeuronNerves(NeuronEBM):
    owlClass = ilxtr.NeuronNerves
    shortname = 'nerves'


class Row(RowBase):

    entail_predicates = tuple()
    neuron_class = NeuronNerves

    def include(self):
        return True

    def neuron_existing(self):
        return None

    def entailed_molecular_phenotypes(self):
        return []


class FromNLP(Sheet):
    name = 'nlp-pns'


class NervesEBM(CutsV1, FromNLP):
    name = 'nlp-pns'
    sheet_name = 'evidence-based modeling statements'
    fetch_grid = False

    _prefix_exclude = tuple()


def main():

    sheets.Row = Row  # monkey patch

    ner = NervesEBM()
    ros = [ner.row_object(i + 1) for i, r in enumerate(ner.values[1:])]
    config = Config('nerves')
    _final = [r.neuron_cleaned(context=NeuronNerves(Species.Human)) for r in ros if r.include()]
    # FIXME TODO add references
    final = _final
    [f._sigh() for f in final]
    config.write()
    config.write_python()
    neurons = config.neurons()
    n = neurons[0]
    return config,


if __name__ == '__main__':
    main()
