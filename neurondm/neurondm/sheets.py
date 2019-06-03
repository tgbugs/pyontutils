import rdflib  # FIXME decouple
import ontquery as oq
from hyputils.hypothesis import idFromShareLink, shareLinkFromId
from pyontutils.sheets import update_sheet_values, get_note, Sheet
from pyontutils.scigraph import Vocabulary
from pyontutils.namespaces import ilxtr, TEMP, definition
from pyontutils.closed_namespaces import rdfs, rdf
from neurondm import NeuronCUT, Config, Phenotype, LogicalPhenotype
from neurondm.models.cuts import make_cut_id, fixname
from neurondm.core import log, OntId, OntTerm


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
            return len(results) * 3

        prefix, _ = curie.split(':')
        if prefix in ranking:
            try:
                return ranking.index(result['curie'])
            except ValueError:
                return len(results) + 1
        else:
            return len(results) * 2

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


def sheet_to_neurons(values, notes_index, expect_pes):
    # TODO import existing ids to register by label
    sgv = Vocabulary()
    e_config = Config('common-usage-types')
    e_config.load_existing()
    query = oq.OntQuery(oq.plugin.get('rdflib')(e_config.core_graph), instrumented=OntTerm)
    # FIXME clear use case for the remaining bound to whatever query produced it rather
    # than the other way around ... how to support this use case ...
    existing = {str(n.origLabel):n for n in e_config.neurons()}
    def convert_header(header):
        if header.startswith('has'):  # FIXME use a closed namespace
            return ilxtr[header]
        else:
            return None

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

    def mapCell(cell, syns=False):
        search_prefixes = ('UBERON', 'CHEBI', 'PR', 'NCBITaxon', 'NCBIGene', 'ilxtr', 'NIFEXT', 'SAO', 'NLXMOL',
                           'BIRNLEX',)

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

        result = [r for r in sgv.findByTerm(cell, searchSynonyms=syns, prefix=search_prefixes)
                  if not r['deprecated']]
        #printD(cell, result)
        if not result:
            log.debug(f'{cell}')
            maybe = list(query(label=cell, exclude_prefix=('FMA',)))
            if maybe:
                qr = maybe[0]
                return qr.OntTerm.u, qr.label
            elif not syns:
                return mapCell(cell, syns=True)
            else:
                return None, None
        elif len(result) > 1:
            #printD('WARNING', result)
            result = select_by_curie_rank(result)
        else:
            result = result[0]

        return rdflib.URIRef(result['iri']), result['labels'][0]

    def lower_check(label, cell):
        return label not in cell and label.lower() not in cell.lower()  # have to handle comma sep case

    lnlu = {v:k for k, v in LogicalPhenotype.local_names.items()}
    def convert_cell(cell_or_comma_sep):
        #printD('CONVERTING', cell_or_comma_sep)
        for cell_w_junk in cell_or_comma_sep.split(','):  # XXX WARNING need a way to alter people to this
            cell = cell_w_junk.strip()
            if cell.startswith('(OR') or cell.startswith('(AND'):
                start, *middle, end = cell.split('" "')
                OPoperator, first = start.split(' "')
                operator = OPoperator[1:]
                operator = lnlu[operator]
                last, CP = end.rsplit('"')
                iris, labels = [], []
                for term in (first, *middle, last):
                    iri, label = mapCell(term)
                    if label is None:
                        label = cell_or_comma_sep
                    iris.append(iri)
                    labels.append(label)

                yield (operator, *iris), tuple(labels)

            else:
                iri, label = mapCell(cell)
                if label is None:
                    yield iri, cell_or_comma_sep  # FIXME need a way to handle this that doesn't break things?
                else:
                    yield iri, label

    config = Config('cut-roundtrip')
    skip = 'alignment label',
    headers, *rows = values
    errors = []
    new = []
    release = []
    for i, neuron_row in enumerate(rows):
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
        for j, (header, cell) in enumerate(zip(headers, neuron_row)):
            notes = list(process_note(get_note(i + 1, j, notes_index)))  # + 1 since headers is removed
            if notes and not header.startswith('has'):
                _predicate = convert_other(header)
                if cell:
                    _object = rdflib.Literal(cell)  # FIXME curies etc.
                else:
                    _object = rdf.nil
                other_notes[_predicate, _object] = notes

            if header == 'curie':
                id = OntId(cell).u if cell else None
                continue
            elif header == 'label':
                label_neuron = cell
                if cell in existing:
                    current_neuron = existing[cell]
                elif cell:
                    # TODO
                    new.append(cell)
                else:
                    raise ValueError(cell)  # wat
                continue
            elif header == 'Status':
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

                continue
            elif header == 'PMID':
                # TODO
                continue
            elif header == 'Other reference':
                # TODO
                continue
            elif header == 'Other label':
                # TODO
                continue
            elif header == 'definition':
                continue  # FIXME single space differences between the spreadsheet and the source

                if cell:
                    definition_neuron = rdflib.Literal(cell)

                continue

            elif header == 'synonyms':
                if cell:
                    synonyms_neuron = [rdflib.Literal(s.strip())
                                    # FIXME bare comma is extremely dangerous
                                    for s in cell.split(',')]

                continue
            elif header in skip:
                continue

            objects = []
            if cell:
                predicate = convert_header(header)
                if predicate is None:
                    log.debug(f'{(header, cell, notes)}')

                for object, label in convert_cell(cell):
                    if isinstance(label, tuple):  # LogicalPhenotype case
                        _err = []
                        for l in label:
                            if lower_check(l, cell):
                                _err.append((cell, label))
                        if _err:
                            errors.extend(_err)
                        else:
                            objects.append(object)
                    elif lower_check(label, cell):
                        errors.append((cell, label))
                    elif str(id) == object:
                        errors.append((header, cell, object, label))
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
                continue

            if predicate and objects:
                for object in objects:  # FIXME has layer location phenotype
                    if isinstance(object, tuple):
                        op, *rest = object
                        pes = (Phenotype(r, predicate) for r in rest)  # FIXME nonhomogenous phenotypes
                        phenotypes.append(LogicalPhenotype(op, *pes))
                    elif object:
                        phenotypes.append(Phenotype(object, predicate))
                    else:
                        errors.append((object, predicate, cell))
            elif objects:
                errors.append((header, objects))
            else:
                errors.append((header, cell))
            # translate header -> predicate
            # translate cell value to ontology id

        if current_neuron and phenotypes:
            # TODO merge current with changes
            # or maybe we just replace since all the phenotypes should be there?
            log.debug(phenotypes)
            if id is not None:
                log.debug(f'{(id, bool(id))}')

            elif label_neuron:
                id = make_cut_id(label_neuron)

            if id not in expect_pes:
                log.error(f'{id!r} not in cuts!?')
                continue

            if expect_pes[id] != len(phenotypes):
                log.error(f'{id!r} failed roundtrip {len(phenotypes)} != {expect_pes[id]}')
                continue

            neuron = NeuronCUT(*phenotypes, id_=id, label=label_neuron,
                               override=bool(id) or bool(label_neuron))
            neuron.adopt_meta(current_neuron)
            # FIXME occasionally this will error?!
        else:
            continue  # FIXME this polutes everything ???
            fn = fixname(label_neuron)
            if not phenotypes and i:  # i skips header
                errors.append((i, neuron_row))  # TODO special review for phenos but not current
                phenotypes = Phenotype('TEMP:phenotype/' + fn),

            neuron = NeuronCUT(*phenotypes,
                               id_=make_cut_id(label_neuron),
                               label=label_neuron, override=True)

        # update the meta if there were any changes
        if definition_neuron is not None:
            neuron.definition = definition_neuron

        if synonyms_neuron is not None:
            neuron.synonyms = synonyms_neuron

        try:
            neuron.batchAnnotateByObject(object_notes)
            neuron.batchAnnotate(other_notes)
        except AttributeError as e:
            #embed()
            log.exception(e) #'something very strage has happened\n', e)
            pass  # FIXME FIXME FIXME

        #neuron.batchAnnotateByPredicate(predicate_notes)  # TODO
        # FIXME doesn't quite work in this context, but there are other
        # cases where annotations to the general modality are still desireable
        # FIXME there may be no predicate? if the object fails to match?

        if do_release:
            release.append(neuron)

    return config, errors, new, release


class Cuts(Sheet):
    name = 'neurons-cut'


class CutsV1(Cuts):
    sheet_name = 'CUT V1.0'
    fetch_grid = True


def main():
    #from neurondm.models.cuts import main as cuts_main
    #cuts_config, *_ = cuts_main()
    from IPython import embed
    from neurondm.compiled.common_usage_types import config as cuts_config
    cuts_neurons = cuts_config.neurons()
    expect_pes = {n.id_:len(n.pes) for n in cuts_neurons}

    sheet = CutsV1()
    config, errors, new, release = sheet_to_neurons(sheet.values, sheet.notes_index, expect_pes)
    #sheet.show_notes()
    config.write_python()
    config.write()
    #config = Config(config.name)
    #config.load_existing()  # FIXME this is a hack to get get a load_graph
    from neurondm import Config, NeuronCUT
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
        return valuesC.searchIndex('label', r.label)

    def key(field_value):
        field, value = field_value
        try:
            return valuesC.header._fields.index(field)  # TODO warn on field mismatch
        except ValueError as e:
            print('ERROR!!!!!!!!!!!', field, value)
            return None

    def replace(r, *cols):
        """ replace and reorder """
        # FIXME _super_ inefficient
        vrow = grow(r)
        for field, value in sorted(zip(r._fields, r), key=key):
            if field in cols:
                value = getattr(vrow, field)

            yield '' if value is None else value  # completely overwrite the sheet

    rows = [list(replace(r, 'Status', 'definition', 'synonyms', 'PMID')) for r in reviewC]
    #resp = update_sheet_values('neurons-cut', 'Roundtrip', rows)
    embed()

if __name__ == '__main__':
    main()
