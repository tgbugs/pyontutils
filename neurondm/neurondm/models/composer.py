import csv
import rdflib
import augpathlib as aug
from pyontutils import sheets
from pyontutils.namespaces import TEMP, ilxtr
from neurondm.models.nlp import map_predicates, main as nlp_main
from neurondm.core import log as _log, uPREFIXES, Config, Neuron

log = _log.getChild('composer')


def get_csv_sheet(path):
    with open(path, 'rt') as f:
        _rows = list(csv.reader(f))

    # remove rows that are missing a value since the export doesn't do
    # that and we will get missing if not provided
    idx = _rows[0].index('Identifier')
    rows = [r for r in _rows if r[idx]]  # Identifier

    s = sheets.Sheet(fetch=False)
    s.sheet_name = 'comprt'
    s._values = []
    s.update(rows)
    s._uncommitted_appends = {}

    return s


def main():
    exp = aug.LocalPath('~/downloads/export_2024-09-17_15-03-20.csv').expanduser()
    sht = get_csv_sheet(exp)
    cs = [sht]
    config = Config('composer-roundtrip')
    nlp_main(cs=cs, config=config, neuron_class=Neuron)  # FIXME neuron_class is incorrect and changes per model


def _oldmain():
    r1 = sht.rows()[1]
    trips = [t for t in [row_to_triple(r) for r in sht.rows()[1:]] if t is not None]
    bund = {}
    for s, p, o in trips:
        if s not in bund:
            bund[s] = []

        bund[s].append((p, o))

def row_to_triple(row):  # XXX old before reuse of nlp code
    skip = ilxtr.hasSomaPhenotype,
    s = rdflib.URIRef(row.uri().value)

    p = map_predicates(row.predicate().value)
    if p in skip:
        return
        
    v = row.identifier().value
    if v:
        if ',' in v:
            r, l = v.split(',')
            o = rdflib.URIRef(r)  # TODO region + layer
        else:
            o = rdflib.URIRef(v)
    else:
        # looks like the export contains rows even when there is no value for that phenotype
        # which is annoying because you can't tell if you screwed up or whether the data
        # actually did not contain that value
        msg = f'where value for {p}?'
        #raise NotImplementedError(msg)
        log.error(msg)
        o = TEMP.FIXME_MISSING
        return

    row.connected_from_uris()  # used for partial order probably
    row.axonal_course_poset()
    #row.relationship()
    #s.rows()[1].cells[0]
    #s.raw_values = rows
    #s._values = rows
    return s, p, o


if __name__ == '__main__':
    main()
