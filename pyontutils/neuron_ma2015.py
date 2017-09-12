#!/usr/bin/env python3.6

from pyontutils.utils import rowParse, refile
import pyontutils.neuron_example as ne
from IPython import embed

context = (ne.Rat, ne.S1, ne.INT, ne.GABA)
def NeuronC(*args, **kwargs):
    return ne.Neuron(*args, *context)

class table1(rowParse):
    citation = 'Markhram et al Cell 2015'
    pmid = 'PMID:26451489'
    _sep = '|'

    def Morphological_type(self, value):
        syn, abrv = value.split(' (')
        syn = syn.strip()
        abrv = abrv.rstrip(')').strip()
        print((syn, abrv))
        self._mtype = ne.__dict__[abrv]

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
        p_edge = ne.pred.hasExpressionPhenotype
        p_map = {
            'CB':ne.CB,
            'PV':ne.PV,
            'CR':ne.CR,
            'NPY':ne.NPY,
            'VIP':ne.VIP,
            'SOM':ne.SOM,
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
            molecule = ne.__dict__[abrv] #p_map[abrv]
            exists = e_map[score]
            score = s_map[score]
            if exists:
                self._moltypes.append(molecule)
            else:
                self._moltypes.append(ne.NegPhenotype(molecule))

        return self._moltypes

    def Electrical_types(self, value):  # FIXME these are mutually exclusive types, so they force the creation of subClasses so we can't apply?
        e_map = {
            'b':ne.b,
            'c':ne.c,
            'd':ne.d,
        }
        l_map = {
            'AC':ne.AC,
            'NAC':ne.NAC,
            'STUT':ne.STUT,
            'IR':ne.IR,
        }

        values = value.split(self._sep)
        self._etypes = []
        for v in values:
            early_late, score_pct_paren = v.split(' (')
            score = int(score_pct_paren.rstrip('%)'))
            e_name, l_name = early_late[0], early_late[1:]
            #early, late = e_map[e_name], l_map[l_name]
            early, late = ne.__dict__[e_name], ne.__dict__[l_name]
            lpe = ne.LogicalPhenotype(ne.AND, early, late)
            self._etypes.append(lpe)

        return self._etypes

    def Other_electrical_classifications(self, value):
        valid_mappings = {'Fast spiking':ne.FS,
                          'Non-fast spiking':ne.NegPhenotype(ne.FS),  # only in this very limited context
                          'Regular spiking non-pyramidal':ne.RSNP}

        values = value.split(self._sep)
        self._other_etypes = []
        for v in values:
            if v in valid_mappings:
                self._other_etypes.append(valid_mappings[v])

        return self._other_etypes

    def _row_post(self):
        for etype in self._etypes:
            NeuronC(etype, *self._other_etypes, self._mtype, *self._moltypes)

    def _end(self):
        ne.WRITE()

if __name__ == '__main__':
    import csv
    with open(refile(__file__, 'resources/26451489 table 1.csv'), 'rt') as f:
        rows = [list(r) for r in zip(*csv.reader(f))]
    table1(rows)

