#!/usr/bin/env python3.7

from neurondm.sheets import Sheet
from neurondm import OntId, OntTerm, Config, NeuronEBM, Neuron
from pyontutils.utils import byCol, relative_path
from pyontutils.namespaces import ilxtr
from pyontutils.closed_namespaces import rdfs


class APIN(Sheet):
    name = 'apinatomy-to-npo'
    sheet_name = 'Bolser-Lewis EBM'

    @staticmethod
    def convert(value):
        if value == 'Projection neuron':
            e = ilxtr.ProjectionPhenotype
        else:
            e = value

        return OntId(e.strip()) if ':' in e else e.strip()

    @property
    def reduced(self):
        et = tuple()
        header = self.values[0]
        skip = [header[i] for i, (h, *rest) in enumerate(self.byCol.cols) if not any(rest)]
        for row in self.values[1:31]:
            if not any(row):
                continue

            stuff = []
            for h, column in zip(header, row):
                if h in skip:
                    continue

                predicate = ilxtr[h] if h != 'label' else rdfs.label
                if column:
                    if h == 'label':
                        objects = [column]
                    else:
                        objects = [self.convert(e) for e in column.split(',')]
                else:
                    objects = et
                
                stuff.append((predicate, objects))

            yield stuff

    @property
    def bags(self):
        for row in self.reduced:
            phenotypes = []
            label = None
            for predicate, objects in row:
                if predicate == rdfs.label:
                    if objects:
                        label = objects[0]

                    continue
                for o in objects:
                    pheno = OntTerm(o).asPhenotype(predicate=predicate)
                    phenotypes.append(pheno)

            yield label, phenotypes


class BolserLewisNeuron(NeuronEBM):
    owlClass = ilxtr.NeuronBolserLewis
    shortname = 'bolew'
    

def main():
    a = APIN()
    config = Config('bolser-lewis',
                    source_file=relative_path(__file__, no_wd_value=__file__))
    bags = list(a.bags)
    for label, bag in bags:
        BolserLewisNeuron(*bag, label=label, override=True)

    Neuron.write()
    Neuron.write_python()
    return config,


if __name__ == '__main__':
    main()
