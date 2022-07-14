from pprint import pprint
from contextlib import nullcontext  # 3.7
from functools import wraps
import rdflib  # FIXME decouple
import ontquery as oq
from hyputils.hypothesis import idFromShareLink, shareLinkFromId
from pyontutils import sheets
from pyontutils.sheets import update_sheet_values, get_note, Sheet
from pyontutils.scigraph import Vocabulary
from pyontutils.namespaces import ilxtr, TEMP, definition, npoph
from pyontutils.namespaces import rdfs, rdf, owl
from pyontutils.utils import allMembers
from neurondm import NeuronCUT, Config, Phenotype, NegPhenotype, LogicalPhenotype
from neurondm import EntailedPhenotype
from neurondm.models.cuts import make_cut_id, fixname
from neurondm.core import log, OntId, OntTerm

try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint

def normalizeDoi(doi):
    if 'http' in doi:
        doi = '10.' + doi.split('.org/10.', 1)[-1]
    elif doi.startswith('doi:'):
        doi = doi.strip('doi:')
    elif doi.startswith('DOI:'):
        doi = doi.strip('DOI:')
    return doi


def select_by_curie_rank(results):
    ranking = 'CHEBI', 'UBERON', 'PR', 'NCBIGene', 'NCBITaxon', 'GO', 'SAO', 'NLXMOL'
    def key(result):
        if 'curie' in result:
            curie = result['curie']
        else:
            return 3, len(results) * 3

        prefix, _ = curie.split(':')
        if prefix in ranking:
            try:
                return 0, ranking.index(prefix)
            except ValueError:
                return 1, len(results) + 1
        else:
            return 2, len(results) * 2

    return sorted(results, key=key)[0]


def process_note(raw_note):
    if raw_note is None:
        return None
    p = ilxtr.literatureCitation
    for bit in  (b.strip() for b in raw_note.split('\n') if b.strip()):
        maybe_hypothesis = idFromShareLink(bit)
        if maybe_hypothesis:
            # TODO getDocInfoFromHypothesisId(maybe_hypothesis)
            yield p, rdflib.URIRef(shareLinkFromId(maybe_hypothesis))
        elif 'doi:' in bit or 'DOI:' in bit or 'doi.org' in bit:
            yield p, rdflib.URIRef('https://doi.org/' + normalizeDoi(bit))
        elif bit.startswith('http'):  # TODO parse the other things
            yield p, rdflib.URIRef(bit)
        else:
            yield p, rdflib.Literal(bit)  # FIXME cull editorial notes


class Cuts(Sheet):
    name = 'neurons-cut'


class CutsV1(Cuts):
    sheet_name = 'CUT V1.0'
    fetch_grid = True

    lnlu = {v:k for k, v in LogicalPhenotype.local_names.items()}

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'existing'):
            e_config = Config('cut-development')
            e_config.load_existing()
            # FIXME clear use case for the remaining bound to whatever query produced it rather
            # than the other way around ... how to support this use case ...
            # FIXME this ignores the sheet id mapping, and pulls in old/alternate axioms
            cls.existing = {n.origLabel.toPython():n for n in e_config.existing_pes}
            cls.existing.update({n.id_:n for n in e_config.existing_pes})
            cls.query = oq.OntQuery(oq.plugin.get('rdflib')(e_config.core_graph), instrumented=OntTerm)
            cls.sgv = Vocabulary()

        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def neurons(self, expect_pes):
        # TODO import existing ids to register by label
        self.config = Config('cut-roundtrip')
        self.skip = 'alignment label',
        self.errors = []
        self.failed = {}
        self.new = []
        self.release = []
        headers, *rows = self.values
        self.tomqc_check_ind = headers.index('tomqc')
        for i, neuron_row in enumerate(rows):
            yield from self.convert_row(i, neuron_row, headers, expect_pes)

    def convert_row(self, i, neuron_row, headers, expect_pes):
        id = None
        label_neuron  = None
        definition_neuron = None
        synonyms_neuron = None
        current_neuron = None
        phenotypes = []
        do_release = False
        predicate_notes = {}
        object_notes = {}
        other_notes = {}
        wat = {}
        def loop_internal(j, header, cell):
            nonlocal id
            nonlocal current_neuron
            nonlocal do_release
            notes = list(process_note(get_note(i + 1, j, self.cells_index)))  # + 1 since headers is removed
            if notes and not header.startswith('has'):
                _predicate = self.convert_other(header)
                if cell:
                    _object = rdflib.Literal(cell)  # FIXME curies etc.
                else:
                    _object = rdf.nil
                other_notes[_predicate, _object] = notes

            if header == 'curie':
                id = OntId(cell).u if cell else None
                return
            elif header == 'label':
                if id == OntId('NIFEXT:66').u:
                    breakpoint()
                label_neuron = cell
                if cell in self.existing:
                    current_neuron = self.existing[cell]
                elif cell:
                    # TODO
                    self.new.append(cell)
                else:
                    raise ValueError(cell)  # wat
                return
            elif header == 'Status 1.0':
                # TODO
                if cell == 'Yes':
                    do_release = True
                elif cell == 'Maybe':
                    pass
                elif cell == 'Not yet':
                    pass
                elif cell == 'Delete':
                    pass
                else:
                    pass

                return
            elif header == 'PMID':
                # TODO
                return
            elif header == 'Other reference':
                # TODO
                return
            elif header == 'Other label':
                # TODO
                return
            elif header == 'definition':
                return  # FIXME single space differences between the spreadsheet and the source

                if cell:
                    definition_neuron = rdflib.Literal(cell)

            elif header == 'synonyms':
                if cell:
                    synonyms_neuron = [rdflib.Literal(s.strip())
                                    # FIXME bare comma is extremely dangerous
                                    for s in cell.split(',')]

                return
            elif header in self.skip:
                return

            objects = []
            if cell:
                predicate = self.convert_header(header)
                if predicate is None:
                    log.debug(f'{(header, cell, notes)}')

                for object, label in self.convert_cell(cell):
                    if predicate in NeuronCUT._molecular_predicates:
                        if isinstance(object, tuple):
                            op, *rest = object
                            rest = [OntTerm(o).asIndicator().URIRef for o in rest]
                            object = op, *rest
                        elif object:
                            log.debug(f'{object!r}')
                            object = OntTerm(object).asIndicator().URIRef

                    if isinstance(label, tuple):  # LogicalPhenotype case
                        _err = []
                        for l in label:
                            if self.lower_check(l, cell):
                                _err.append((cell, label))
                        if _err:
                            self.errors.extend(_err)
                        else:
                            objects.append(object)
                    elif self.lower_check(label, cell):
                        self.errors.append((cell, label))
                    elif str(id) == object:
                        self.errors.append((header, cell, object, label))
                        object = None
                    else:
                        objects.append(object)

                if notes:
                    # FIXME this is a hack to only attach to the last value
                    # since we can't distinguish at the moment
                    wat[predicate, object] = notes
                    if object is not None:
                        # object aka iri can be none if we don't find anything
                        object_notes[object] = notes
                    else:
                        predicate_notes[predicate] = notes
                        # FIXME it might also be simpler in some cases
                        # to have this be object_notes[object] = notes
                        # because we are much less likely to have the same
                        # phenotype appear attached to the different dimensions

                        # FIXME comma sep is weak here because the
                        # reference is technically ambiguous
                        # might be an argument for the denormalized form ...
                        # or perhaps having another sheet for cases like that

            else:
                return

            if predicate and objects:
                for object in objects:  # FIXME has layer location phenotype
                    if isinstance(object, tuple):
                        op, *rest = object
                        pes = (Phenotype(r, predicate) for r in rest)  # FIXME nonhomogenous phenotypes
                        phenotypes.append(LogicalPhenotype(op, *pes))
                    elif object:
                        phenotypes.append(Phenotype(object, predicate))
                    else:
                        self.errors.append((object, predicate, cell))
            elif objects:
                self.errors.append((header, objects))
            else:
                self.errors.append((header, cell))
            # translate header -> predicate
            # translate cell value to ontology id

        #########################################

        for j, (header, cell) in enumerate(zip(headers, neuron_row)):
            loop_internal(j, header, cell)

        if current_neuron and phenotypes:
            # TODO merge current with changes
            # or maybe we just replace since all the phenotypes should be there?
            log.debug(phenotypes)
            if id is not None:
                log.debug(f'{(id, bool(id))}')

            elif label_neuron:
                id = make_cut_id(label_neuron)

            if id not in expect_pes:
                if id is not None:
                    log.error(f'{id!r} not in cuts!?')

                return

            phenotypes = sorted(set(phenotypes))
            _ep = expect_pes[id]
            if not allMembers(_ep, *phenotypes) and not neuron_row[self.tomqc_check_ind]:
            #if expect_pes[id] != len(phenotypes):
                # FIXME this is not a strict roundtrip, it may also include additions
                lp = len(phenotypes)
                lep = len(_ep)
                if lp == lep:
                    (pprint(sorted(_ep)))
                    (pprint(phenotypes))
                    pprint(set(_ep) - set(phenotypes))
                    pprint(set(phenotypes) - set(_ep))
                    _AAAAAA = id  # hack for debugger
                    print(_AAAAAA)
                log.error(f'{id!r} failed roundtrip {lp} != {lep}')
                self.failed[id] = phenotypes
                return

            neuron = NeuronCUT(*phenotypes, id_=id, label=label_neuron,
                               override=bool(id) or bool(label_neuron))
            neuron.adopt_meta(current_neuron)
            # FIXME occasionally this will error?!
            yield neuron

        else:
            return  # FIXME this polutes everything ???
        """
            fn = fixname(label_neuron)
            if not phenotypes and i:  # i skips header
                self.errors.append((i, neuron_row))  # TODO special review for phenos but not current
                phenotypes = Phenotype('TEMP:phenotype/' + fn),

            neuron = NeuronCUT(*phenotypes,
                               id_=make_cut_id(label_neuron),
                               label=label_neuron, override=True)

        """
        ###################################################

        # update the meta if there were any changes
        if definition_neuron is not None:
            neuron.definition = definition_neuron

        if synonyms_neuron is not None:
            neuron.synonyms = synonyms_neuron

        try:
            neuron.batchAnnotateByObject(object_notes)
            neuron.batchAnnotate(other_notes)
        except AttributeError as e:
            #breakpoint()
            log.exception(e) #'something very strage has happened\n', e)
            pass  # FIXME FIXME FIXME

        #neuron.batchAnnotateByPredicate(predicate_notes)  # TODO
        # FIXME doesn't quite work in this context, but there are other
        # cases where annotations to the general modality are still desireable
        # FIXME there may be no predicate? if the object fails to match?

        if do_release:
            self.release.append(neuron)


    @staticmethod
    def convert_header(header):
        if header.startswith('has'):  # FIXME use a closed namespace
            if header == 'hasLocationPhenotype':
                # can't have duplicate headers in the sheet so fix it here
                header = 'hasSomaLocatedIn'

            return npoph[header]
        else:
            return None

    @staticmethod
    def convert_other(header):
        if header == 'label':
            return rdfs.label
        elif header == 'curie':
            return rdf.type
        elif header == 'definition':
            return definition
        else:
            header = header.replace(' ', '_')
            return TEMP[header]  # FIXME

    @staticmethod
    def lower_check(label, cell):
        return label not in cell and label.lower() not in cell.lower()  # have to handle comma sep case

    _prefix_exclude = ('FMA',)
    _search_prefixes = ('UBERON', 'CHEBI', 'PR', 'NCBIGene', 'NCBITaxon',
                        'ilxtr', 'NIFEXT', 'SAO', 'NLXMOL', 'BIRNLEX', 'FMA', 'PATO')

    @classmethod
    def mapCell(cls, cell, syns=False, predicate=None):
        search_prefixes = tuple(p for p in cls._search_prefixes if p not in cls._prefix_exclude)

        if predicate and predicate in Phenotype._molecular_predicates:
            # uberon syns pollute molecular results so move it to one before birnlex
            ub, *rest, b = search_prefixes
            search_prefixes = (*rest, ub, b)

        if cell == 'contralateral':
            return ilxtr.Contralateral, cell  # XXX FIXME only BSPO has this right now
        elif cell.lower() == 'gaba receptor role':
            return ilxtr.GABAReceptor, cell

        if ':' in cell and ' ' not in cell:
            log.debug(cell)
            if 'http' in cell:
                if cell.startswith('http'):
                    t = OntTerm(iri=cell)
                else:
                    return None, None  # garbage with http inline
            else:
                t = OntTerm(cell, exclude_prefix=('FMA',))  # FIXME need better error message in ontquery

            return t.u, t.label

        if cell in ('Vertebrata', ):  # search syns
            syns = True

        def rank_mask(r):
            """
            create a boolean array testing if the current entry
            starts with the prefixes in order and what you will
            get out is arrays where the nth element is true if
            the nth prefix is matched which will then be sorted by n
            1 0 0 0 0 0 0 1 \\
            1 0 0 0 0 0 0 0 \\
            0 1 0 0 0 0 0 0 \\
            0 0 1 0 0 0 0 0 \\
            0 0 0 1 0 0 0 0 \\
            0 0 0 0 1 0 0 0 \\
            """
            # why did it take so long to think of this?
            return (
                *(r['curie'].startswith(p) for p in search_prefixes),
                'labels' in r and cell in r['labels'],
            )

        result = sorted([r for r in cls.sgv.findByTerm(cell, searchSynonyms=syns, prefix=search_prefixes)
                         if not r['deprecated']], key=rank_mask, reverse=True)
        #printD(cell, result)
        if not result:
            log.debug(f'{cell}')
            maybe = list(cls.query(label=cell, exclude_prefix=cls._prefix_exclude))
            if maybe:
                t = maybe[0]
                return t.u, t.label
            elif not syns:
                return cls.mapCell(cell, syns=True, predicate=predicate)
            else:
                return None, None
        elif len(result) > 1:
            #printD('WARNING', result)
            result = result[0] #select_by_curie_rank(result)
        else:
            result = result[0]

        return rdflib.URIRef(result['iri']), result['labels'][0]

    @classmethod
    def convert_cell(cls, cell_or_comma_sep, predicate=None):
        #printD('CONVERTING', cell_or_comma_sep)
        for cell_w_junk in cell_or_comma_sep.split(','):  # XXX WARNING need a way to alter people to this
            cell = cell_w_junk.strip()
            negative = (cell.lower().startswith('lacks') or
                        cell.lower().startswith('not '))
            if negative:
                __lacks, cell = cell.split(' ', 1)

            if cell.startswith('(OR') or cell.startswith('(AND'):
                start, *middle, end = cell.split('" "')
                OPoperator, first = start.split(' "')
                operator = OPoperator[1:]
                operator = cls.lnlu[operator]
                last, CP = end.rsplit('"')
                iris, labels = [], []
                for term in (first, *middle, last):
                    iri, label = cls.mapCell(term, predicate=predicate)
                    if label is None:
                        label = cell_or_comma_sep
                    if negative:
                        iri = LacksObject(iri)

                    iris.append(iri)
                    labels.append(label)

                yield (operator, *iris), tuple(labels)

            else:
                iri, label = cls.mapCell(cell, predicate=predicate)
                if negative:
                    iri = LacksObject(iri)

                if label is None:
                    yield iri, cell_or_comma_sep  # FIXME need a way to handle this that doesn't break things?
                else:
                    yield iri, label


class LacksObject(rdflib.URIRef):
    """ Objects that can indicate that they
        should be lifted to negative phenotypes

        This is a trick we can play to with the type system
        to pack the negative phenotype into a single object
        that could then be expanded to object.asPhenotype(predicate)

        potential alternate names:
        NegativeObject
        NegativePhenotypeValue
        AbsentObject
    """

    def asURIRef(self):
        return rdflib.URIRef(self)


class CutsV1Lite(Cuts):
    sheet_name = 'CUT V1.0'
    fetch_grid = False


class Row(sheets.Row):

    neuron_class = NeuronCUT

    entail_predicates = (
        ilxtr.hasAxonLocatedIn,
        ilxtr.hasDendriteLocatedIn,
        ilxtr.hasDendriteMorphologicalPhenotype,
    )

    def neuron_existing(self):
        curie = self.curie().value
        if curie:
            id_ = OntTerm(curie).u
            match = self.sheet.existing.get(id_)
            if match:
                match.id_ = id_
                return match

        al = self.alignment_label().value
        nrn = self.sheet.existing.get(al if al else self.label().value)

        if nrn and curie:
            nrn.id_ = id_

        return nrn

    def status(self):
        # column header renamed without warning
        return self.status_1_0()

    def include(self):
        return self.status().value == 'Yes'

    def entailed_molecular_phenotypes(self):
        cell = self.exhasmolecularphenotype()
        labels = cell.value.split(',')

        # FIXME hack
        yield OntTerm(curie='ilxtr:GABAReceptor').asPhenotype()
        yield OntTerm(curie='ilxtr:glutamateReceptor').asPhenotype()

        for label in labels:
            label = label.strip()
            term = self.sheet.sgv.findByTerm(label)
            if term:
                ot = OntTerm(iri=term[0]['iri'])
                p = ot.asPhenotype()
                yield p
                if ot.curie == 'NLXMOL:1006001':
                    yield OntTerm(curie='ilxtr:GABAReceptor').asPhenotype()
                elif ot.curie == 'SAO:1164727693':
                    yield OntTerm(curie='ilxtr:glutamateReceptor').asPhenotype()

    def asPhenotypes(self):
        log.warning(f'New neuron from sheet! {self.label().value}')
        has = [(attr, ilxtr[suffix])
               for attr, suffix in zip(self.header, self.sheet.values[0])
               if attr.startswith('has')]

        def map(attr, predicate):
            cell = getattr(self, attr)()
            value = cell.value
            if value:
                for iri, label in list(self.sheet.convert_cell(value, predicate=predicate)):
                    if ',' not in value and label != value:
                        log.warning(f'label mismatch {label!r} != {value!r}')

                    if iri is None:
                        if label == 'bed nucleus of stria terminalis juxtacapsular nucleus':
                            iri = OntTerm('UBERON:0011173', label='anterior division of bed nuclei of stria terminalis')
                        else:
                            log.debug(f'nothing found for {label}')
                            continue

                    if isinstance(iri, tuple):
                        op, *rest = iri  # TODO need combinators in future version for union/intersection of object
                        out = (op, *(NegPhenotype(r, predicate)
                                     if isinstance(r, LacksObject) else
                                     Phenotype(r, predicate)
                                     for r in rest if r is not None))
                        yield out
                        continue
                    elif isinstance(iri, LacksObject):
                        pheno = NegPhenotype(iri.asURIRef(), predicate)
                    else:
                        pheno = Phenotype(iri, predicate)

                    yield pheno.asIndicator()


        mapped = [(v, p) for attr, p in has for v in map(attr, p)]
        pes = [LogicalPhenotype(*value)
               if isinstance(value, tuple) else
               value
               #Phenotype(value, dimension)
               for value, dimension in mapped
               if value is not None]
        # moveToIndicator
        # exHasMolecularPhenotype
        # PMID
        # Other reference
        # Other label
        # definition
        # synonyms
        return pes

    def asNeuron(self):
        pes = self.asPhenotypes()
        return self.neuron_class(*pes, label=self.label().value)

    def _ec(self, nrn):
        # handle cases where we accidentally duplicated ids
        if hasattr(self, 'curie_extra'):
            ce = self.curie_extra().value
            if ce:
                eid = OntId(ce).u
                nrn.add_objects(owl.equivalentClass, eid)

    def neuron_cleaned(self, context=nullcontext()):
        # FIXME WARNING nullcontext behavior seems to have changed at some point !?
        conditional_entailed_predicates = (
            (ilxtr.hasSomaLocatedInLayer, (False or self.curie().value == 'NIFEXT:55')),  # martinotti cell
        )

        ne = self.neuron_existing()
        emp = list(self.entailed_molecular_phenotypes())
        eobjects = [e.p for e in emp]
        def should_entail(pe):
            return (pe.p in eobjects or
                    pe.e in self.entail_predicates or
                    (pe.e, True) in conditional_entailed_predicates or
                    isinstance(pe, LogicalPhenotype) and any(should_entail(_) for _ in pe.pes) or
                    # see this comment for discussion about negative phenotypes on CUTs
                    # https://github.com/SciCrunch/NIF-Ontology/issues/222#issuecomment-680175477
                    isinstance(pe, NegPhenotype))

        sheet_pes = self.asPhenotypes()
        sheet_pes = [pe.asEntailed() if should_entail(pe) else pe for pe in sheet_pes]

        if ne is None:
            curie = self.curie().value
            id_ = curie if curie else None
            nrn = self.neuron_class(*sheet_pes, id_=id_, label=self.label().value, override=id_ is None)
            self._ec(nrn)
            return nrn

        if not emp:
            # can't just return the existing neuron because it isn't bound to the current config
            # FIXME uh what an aweful design
            nrn = self.neuron_class(*ne, *sheet_pes, id_=ne.id_, label=ne.origLabel,
                                    override=True).adopt_meta(ne)
            self._ec(nrn)
            return nrn

        pes = [pe.asEntailed() if should_entail(pe) else pe for pe in ne]

        with context:
            nrn = self.neuron_class(*pes, *sheet_pes, id_=ne.id_, label=ne.origLabel, override=True)
            self._ec(nrn)
            return nrn


def main():
    #from neurondm.models.cuts import main as cuts_main
    #cuts_config, *_ = cuts_main()

    # monkey patch inside main to ensure that other code doesn't change while we are at the top level
    sheets.Row = Row

    from neurondm.compiled.common_usage_types import config as cuts_config
    cuts_neurons = cuts_config.neurons()
    expect_pes = {n.id_:n.pes for n in cuts_neurons}

    sheet = CutsV1()
    _neurons = list(sheet.neurons(expect_pes))
    config = sheet.config
    errors = sheet.errors
    new = sheet.new
    release = sheet.release

    #sheet.show_notes()
    config.write_python()
    config.write()
    #config = Config(config.name)
    #config.load_existing()  # FIXME this is a hack to get get a load_graph

    # FIXME we need this because _bagExisting doesn't deal with unionOf right now
    def trything(f):
        @wraps(f)
        def inner(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except:
                pass

        return inner

    from neurondm import Config, NeuronCUT

    failed_config = Config('cut-failed')
    [trything(NeuronCUT)(*pes, id_=id_) for id_, pes in sheet.failed.items()]
    failed_config.write_python()
    failed_config.write()

    release_config = Config('cut-release')
    [NeuronCUT(*n, id_=n.id_, label=n.origLabel, override=True).adopt_meta(n) for n in release]
    release_config.write_python()
    release_config.write()

    from neurondm.models.cuts import export_for_review
    review_rows = export_for_review(config, [], [], [], filename='cut-rt-test.csv', with_curies=True)
    from pyontutils.utils import byCol
    valuesC = byCol(sheet.values[1:],
                    header=[v.replace(' ', '_') for v in sheet.values[0]],
                    to_index=['label'])
    reviewC = byCol(review_rows[1:], header=[v.replace(' ', '_') for v in review_rows[0]], to_index=['label'])
    def grow(r):
        log.debug(r)
        # TODO implement on the object to allow joining on an index?
        # man this would be easier with sql >_< probably pandas too
        # but so many dependencies ... also diffing issues etc
        if r.label is not None:
            return valuesC.searchIndex('label', r.label)

    def key(field_value):
        field, value = field_value
        try:
            return 0, valuesC.header._fields.index(field)  # TODO warn on field mismatch
        except ValueError as e:
            log.error(f'{field} {value}')
            return 1, 0

    def replace(r, *cols):
        """ replace and reorder """
        # FIXME _super_ inefficient
        vrow = grow(r)
        log.debug('\n'.join(r._fields))
        log.debug('\n'.join(str(_) for _ in r))
        for field, value in sorted(zip(r._fields, r), key=key):
            if field in cols:
                value = getattr(vrow, field)

            yield '' if value is None else value  # completely overwrite the sheet

    breakpoint()
    rows = [list(replace(r, 'Status 1.0', 'definition', 'synonyms', 'PMID')) for r in reviewC]
    #resp = update_sheet_values('neurons-cut', 'Roundtrip', rows)
    if __name__ == '__main__':
        breakpoint()


def main():
    #cv1 = CutsV1Lite()
    sheets.Row = Row
    CutsV1.fetch_grid = False
    cv1 = CutsV1()
    hrm = [cv1.row_object(i) for i, r in enumerate(cv1.values)
           if cv1.row_object(i).exhasmolecularphenotype().value]
    to_sco = set(t for h in hrm for t in h.entailed_molecular_phenotypes())
    ros = [cv1.row_object(i + 1) for i, r in enumerate(cv1.values[1:])]
    to_fix = [r for r in ros if list(r.entailed_molecular_phenotypes())]
    #maybe_fixed = [t.neuron_cleaned() for t in to_fix]
    #assert maybe_fixed != [f.neuron_existing() for f in to_fix]
    config = Config('common-usage-types')
    _final = [r.neuron_cleaned() for r in ros if r.include()]
    final = [f for f in _final if f is not None]  # FIXME there are 16 neurons marked as yes that are missing
    #fixed = [f for f in final if [_ for _ in f.pes if isinstance(_, EntailedPhenotype)]]
    [f._sigh() for f in final]
    config.write()
    config.write_python()
    if __name__ == '__main__':
        breakpoint()


if __name__ == '__main__':
    log.setLevel('WARNING')
    main()
