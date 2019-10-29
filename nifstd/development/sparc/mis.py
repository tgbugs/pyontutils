from sparcur.utils import want_prefixes
import rdflib
import requests
mis = rdflib.Graph().parse(data=requests.get('https://cassava.ucsd.edu/sparc/exports/curation-export.ttl').content, format='turtle')
graph = mis

def reformat(ot):
    return [ot.label if hasattr(ot, 'label') and ot.label else '', ot.curie]

objects = set()
skipped_prefixes = set()
for t in graph:
    for e in t:
        if isinstance(e, rdflib.URIRef):
            oid = OntId(e)
            if oid.prefix in want_prefixes + ('tech', 'unit'):
                objects.add(oid)
            else:
                skipped_prefixes.add(oid.prefix)

objs = [OntTerm(o) if o.prefix not in ('TEMP', 'sparc') or
        o.prefix == 'TEMP' and o.suffix.isdigit() else
        o for o in objects]
term_sets = {title:[o for o in objs if o.prefix == prefix]
             for prefix, title in
             (('NCBITaxon', 'Species'),
              ('UBERON', 'Anatomy and age category'),  # FIXME
              ('FMA', 'Anatomy (FMA)'),
              ('PATO', 'Qualities'),
              ('tech', 'Techniques'),
              ('unit', 'Units'),
              ('sparc', 'MIS terms'),
              ('TEMP', 'Suggested terms'),
             )}

term_sets['Other'] = set(objs) - set(ot for v in term_sets.values() for ot in v)

trows = []
for title, terms in term_sets.items():
    rows = [reformat(ot) for ot in
                sorted(terms,
                       key=lambda ot: (ot.prefix, ot.label.lower()
                                       if hasattr(ot, 'label') and ot.label else ''))]
    [trows.append(row) for row in rows]

# organize by string putting nulls in the back
rows = sorted(trows, key=lambda x: (str(x[0]).strip() in ['None', ''], x[0].lower()))

for o in mis_label_curies:
    # some labels will be empty strings ''
    print(o.label+'\t'+o.curie)
