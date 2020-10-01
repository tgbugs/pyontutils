#!/usr/bin/env python3.7

from pathlib import Path
import rdflib
from pyontutils.utils import rowParse, relative_path
from pyontutils.namespaces import ilxtr
from neurondm.lang import *
from neurondm.phenotype_namespaces import BBP


class NeuronMarkram2015(NeuronEBM):
    owlClass = ilxtr.NeuronMarkram2015
    shortname = 'Markram2015'


class table1(rowParse):
    citation = 'Markram et al Cell 2015'
    pmid = 'PMID:26451489'
    _sep = '|'

    def __init__(self, *args, **kwargs):
        with BBP:
            self._context = Neuron(Rat, S1, Interneuron, GABA)
            super().__init__(*args, **kwargs)

    def Morphological_type(self, value):
        syn, abrv = value.split(' (')
        syn = syn.strip()
        abrv = abrv.rstrip(')').strip()
        # print((syn, abrv))
        self._mtype = BBP[abrv]

        self._m_syn = syn
        self._m_abrev = abrv
        return self._mtype

    def Other_morphological_classifications(self, value):
        return  #  skipping all of this for now due to bitufted nonsense etc
        values = value.split(self._sep)
        output = []
        callbacks = []

        for v in values:
            if '/' in v:
                prefix, a_b = v.split(' ')
                a, b = a_b.split('/')
                #output.append(prefix + ' ' + a)
                #output.append(prefix + ' ' + b)
            else:
                prefix = v.rstrip('cell').strip()
                #output.append(v)

            label = prefix + ' phenotype'
            output.append(label)

        for v in output:
            self.graph.add_trip(self._morpho_parent_id, 'NIFRID:synonym', v)

    def Predominantly_expressed_Ca2_binding_proteins_and_peptides(self, value):
        p_edge = ilxtr.hasExpressionPhenotype
        with BBP:
            p_map = {
                'CB':CB,
                'PV':PV,
                'CR':CR,
                'NPY':NPY,
                'VIP':VIP,
                'SOM':SOM,
            }

        NEGATIVE = False
        POSITIVE = True  # FIXME this requires more processing prior to dispatch...
        e_edge = ''
        e_map = {
            '-':NEGATIVE,
            '+':POSITIVE,
            '++':POSITIVE,
            '+++':POSITIVE,
        }
        NONE = 0
        LOW = 1
        MED = 2
        HIGH = 3
        s_map = {
            '-':NONE,
            '+':LOW,
            '++':MED,
            '+++':HIGH,
        }

        values = value.split(self._sep)
        self._moltypes = []
        for v in values:
            abrv, score_paren = v.split(' (')
            score = score_paren.rstrip(')')
            molecule = BBP[abrv] #p_map[abrv]
            exists = e_map[score]
            score = s_map[score]
            if exists:
                self._moltypes.append(molecule)
            else:
                self._moltypes.append(NegPhenotype(molecule))

        return self._moltypes

    def Electrical_types(self, value):  # FIXME these are mutually exclusive types, so they force the creation of subClasses so we can't apply?
        e_map = {
            'b':b,
            'c':c,
            'd':d,
        }
        l_map = {
            'AC':AC,
            'NAC':NAC,
            'STUT':STUT,
            'IR':IR,
        }

        values = value.split(self._sep)
        self._etypes = []
        for v in values:
            early_late, score_pct_paren = v.split(' (')
            score = int(score_pct_paren.rstrip('%)'))
            e_name, l_name = early_late[0], early_late[1:]
            #early, late = e_map[e_name], l_map[l_name]
            early, late = BBP[e_name], BBP[l_name]
            lpe = LogicalPhenotype(AND, early, late)
            self._etypes.append(lpe)

        return self._etypes

    def Other_electrical_classifications(self, value):
        valid_mappings = {'Fast spiking':FS,
                          'Non-fast spiking':NegPhenotype(FS),  # only in this very limited context
                          'Regular spiking non-pyramidal':RSNP}

        values = value.split(self._sep)
        self._other_etypes = []
        for v in values:
            if v in valid_mappings:
                self._other_etypes.append(valid_mappings[v])

        return self._other_etypes

    def _row_post(self):
        with self._context:
            n = NeuronMarkram2015(self._mtype,
                                  *[m.asEntailed() for m in self._moltypes],
                                  label=self._m_syn)
            n.abbrevs = [rdflib.Literal(self._m_abrev)]

            for etype in self._etypes:
                NeuronMarkram2015(etype, self._mtype, *self._other_etypes, *self._moltypes)

    def _end(self):
        graphBase.out_graph.add((NeuronMarkram2015.owlClass,
                                 ilxtr.modelSource,
                                 OntId('https://doi.org/10.1016/j.cell.2015.09.029').u))

        graphBase.write()
        graphBase.write_python()


def main():
    import csv
    from neurondm.core import auth
    with open(auth.get_path('resources') / '26451489 table 1.csv', 'rt') as f:
        rows = [list(r) for r in zip(*csv.reader(f))]

    config = Config('markram-2015',
                    source_file=relative_path(__file__, no_wd_value=__file__))
    table1(rows)
    return config,


__globals__ = globals()  # fuck you python

if __name__ == '__main__':
    with BBP:
        main()
