import rdflib
import augpathlib as aug
from pyontutils import sheets
from pyontutils.core import OntGraph, OntId, populateFromJsonLd
from pyontutils.config import auth
from pyontutils.namespaces import (rdf, rdfs, owl, ilxtr, NIFRID,
                                   definition, editorNote, OntCuries)
from pyld.jsonld import JsonLdProcessor


context_prefixes = {prefix:{'@id': str(ns), '@prefix': True}
                    for prefix, ns in
                    {'rdf': rdf,
                     'rdfs': rdfs,
                     'owl': owl,
                     'ilxtr': ilxtr,
                     'mod': ilxtr['modality/'],
                     'NIFRID': NIFRID,
                     }.items()}


class PanProjectProtocols(sheets.Sheet):
    name = 'pan-project-protocols'


PPP = PanProjectProtocols

class ModalityHBP(PPP):
    sheet_name = 'HBP modality'


class ModalityBICCN(PPP):
    sheet_name = 'BICCN modality'


class ModalitySPARC(PPP):
    sheet_name = 'SPARC modality'


class Recuration(PPP):
    sheet_name = 'Recuration'


class Approaches(PPP):
    # see also map-identifiers.py and methods/ for the rest of this
    sheet_name = 'Modalities Merged'
    index_columns = 'id',
    context_row = {
        'id': '@id',
        'rdfs_subclassof': {'@id': 'rdfs:subClassOf', '@type': '@id'},
        'label': 'rdfs:label',
        'display_label': 'ilxtr:displayLabel',
        'definition': str(definition),
        'hbp_definition': 'ilxtr:definitionHBP',
        'sparc_definition': 'ilxtr:definitionSPARC',
        'hbp_existing': 'ilxtr:existingHBP',
        'sparc_existing': 'ilxtr:existingSPARC',
        'biccn_existing': 'ilxtr:existingBICCN',
        'synonyms': 'NIFRID:synonym',
        'note': str(editorNote),
    }

    def fromJsonLd(self, blob):
        # we will need a generic approach for this
        raise NotImplementedError('TODO')

    def asJsonLd(self):
        classes = []
        for row in self.rows()[1:]:
            if row.id().value and row.name().value:
                obj = {}
                for attr in self.context_row:
                    cell = getattr(row, attr)()
                    value = cell.value
                    if value:
                        obj[attr] = value

                if obj:
                    obj['@type'] = 'owl:Class'
                    classes.append(obj)

        return {
            '@context': {
                '@version': 1.1,  # lol json-ld must be an int not a string
                **context_prefixes,
                **self.context_row,
            },
            '@graph': classes}

    @property
    def graph(self):
        if not hasattr(self, '_graph'):
            self._graph = populateFromJsonLd(OntGraph(), self.asJsonLd())
            OntCuries.populate(self._graph)
            self.populateHeader(self._graph)

        return self._graph

    @property
    def pathTtl(self):
        olr = aug.RepoPath(auth.get_path('ontology-local-repo'))
        path = olr / 'ttl' / 'approach.ttl'
        return path

    def populateHeader(self, graph):
        path = self.pathTtl
        s = rdflib.URIRef(path.remote_uri_machine())
        # TODO prov
        pairs = ((rdf.type, owl.Ontology),
                 (rdfs.label, rdflib.Literal('Experimental approaches.')),)
        for p, o in pairs:
            graph.add((s, p, o))

    def writeTtl(self):
        self.graph.write(self.pathTtl)


def main():
    def diff():
        mh = ModalityHBP()
        mb = ModalityBICCN()
        ms = ModalitySPARC()
        values = [row for sheet in (mb, mb, ms) for row in sheet.values]
        unique = set([v[0] for v in values if v[0] != 'name'])
        all_u  = set([v[0] for v in ma.values if v[0] != 'name'])
        missing = unique - all_u
        extra = all_u - unique

    ma = Approaches()
    ma.writeTtl()


if __name__ == '__main__':
    main()
