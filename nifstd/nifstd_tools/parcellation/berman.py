import json
import subprocess
import collections
from pathlib import Path
from bs4 import BeautifulSoup
from lxml import etree
import rdflib
from pyontutils.core import resSource, LabelsBase, Collector
from pyontutils.config import auth
from nifstd_tools.parcellation import parcCore, Atlas, LabelRoot, Label
from pyontutils.namespaces import NIFRID, ilx, ilxtr, TEMP, BERCAT, nsExact
from pyontutils.namespaces import NCBITaxon, UBERON, NIFTTL, makePrefixes
from pyontutils.closed_namespaces import rdf, rdfs, owl, dc, dcterms, skos, prov


class Artifacts(Collector):
    collects = Atlas

    BermanCat = Atlas(
        iri=ilx['berman/uris/cat/versions/1'],
        label='Berman 1968 cat brain stem atlas',
        shortname='Berman Cat 1968',
        date=1968,
        hadDerivation=['http://brainmaps.org/index.php?action=metadata&datid=35'],
        definingCitations=('A. L. Berman (1968) The Brain Stem of the Cat. '
                           'A Cytoarchitectonic Atlas with Stereotaxic Coordinates. '
                           'Madison, University of Wisconsin Press.',),  # NOTE this is a tuple
        species=NCBITaxon['9685'],
        devstage=UBERON['0000113'],  # assumedly
        region=UBERON['0000955'],
        comment = (''),
    )


def clean(string):
    ''' Begining of the string can sometimes have odd noise '''
    # manual fixes in the source
    # 24/1.png
    # 9/1.png
    # 3/1.png
    #if ')' in string:  # fix in the source data
        #string = string.split(')')[0] + ')'  # remove trailing garbage
    return (string
            .replace('_', '')
            .replace('-', '')
            .replace('—', '')
            .replace('.', '')
            .replace('=', '')
            .replace('\u2018',"'")  # LEFT SINGLE QUOTATION MARK
            .replace('\u2019', "'")  # RIGHT SINGLE QUOTATION MARK
            .strip())


def get_legends(raw_text):
    legends = []
    for line in raw_text.splitlines():
        line = clean(line)
        if not line:
            continue
        try:
            abbrev, label = line.split(' ', 1)
        except ValueError as e:
            print(repr(line))
            print(repr(raw_text))
            raise e
            continue
        abbrev = clean(abbrev)
        label = clean(label)
        legends.append((abbrev, label))
    return legends


resources = auth.get_path('resources')
if resources is not None:
    # FIXME TODO this is a bad way to handle this ...
    with open(resources/ 'brainmaps-cat-abbrevs.html', 'rt') as f:
        dat = f.read()

    asoup = BeautifulSoup(dat, 'lxml')


class BermanSrc(resSource):
    run_ocr=False
    source_images=Path('~/files/cropped').expanduser()
    source = 'https://github.com/tgbugs/pyontutils.git'
    sourceFile = auth.get_path('resources') / 'berman'
    source_original = False
    artifact = Artifacts.BermanCat

    @classmethod
    def loadData(cls):
        """ Sigh, this was indeed a poorly conceived approach
        since it hard blocks when the files are not in the source
        so you can't easily bootstrap from another source and the
        cognitive overhead is way, way too high :/ 

        Adding dry_run/bootstrap to __new__ sort of helps? """
        """ Have to run this out here because resSource is handicapped """
        data = []
        if cls.source_images.exists():
            for folder in cls.source_images.glob('*'):
                plate_num = int(folder.stem)
                text_file = cls.source / f'{plate_num}.txt'
                if not text_file.exists() or cls.run_ocr:
                    legends = []
                    raw_text = ''
                    for img in folder.glob('*.png'):
                        print('num', plate_num, img.stem)
                        p = subprocess.Popen(('tesseract',
                                                img.as_posix(),
                                                'stdout', '-l', 'eng', '--oem', '2', '--psm', '6'),
                                            stdout=subprocess.PIPE)
                        bytes_text, err = p.communicate()
                        raw_text += bytes_text.decode() + '\n'

                    with open(text_file, 'wt') as f:
                        f.write(raw_text)
                else:
                    with open(text_file, 'rt') as f:
                        raw_text = f.read()

                legends = get_legends(raw_text)
                data.append((plate_num, legends))

        elif cls.source.exists():
            for text_file in cls.source.glob('*.txt'):
                plate_num = int(text_file.stem)
                with open(text_file, 'rt') as f:
                    raw_text = f.read()

                legends = get_legends(raw_text)
                data.append((plate_num, legends))

        return data

    @classmethod
    def processData(cls):
        data = cls.raw

        # ocr fixes
        # in theory could use the most frequent if > .75 are the same ...
        cor_l = {
            'abducens nerve': {'GN': '6N'},
            'alaminar spinal trigeminal nucleus, magnocellular division (14)': {'5SM': 'SSM'},
            'alaminar spinal trigeminal nucleus, parvocellular division (6)': {'5SP': 'SSP'},
            'central nucleus of the inferior colliculus (21)': {'1CC': 'ICC'},
            'cerebral cortex': {'¢': 'C'},
            'commissure of the inferior colliculi': {'1CO': 'ICO', 'I1CO': 'ICO'},
            'corpus callosum': {'198': 'CC'},
            'inferior central nucleus (13)': {'C': 'CI', 'Cl': 'CI'},
            'lateral tegmental field (3)': {'FIL': 'FTL'},
            'mesencephalic trigeminal nucleus (19)': {'SME': '5ME'},
            'motor trigeminal tract': {'SMT': '5MT'},
            'nucleus of the trapezoid body (15)': {'J': 'T'},
            'posterior interpeduncular nucleus, inner division': {'al': 'IPI'},  # wow ...
            'solitary tract': {'$': 'S'},
            'spinal trigeminal tract': {'SST': '5ST'},
            'statoacoustic nerve': {'BN': 'SN'},
            'superior central nucleus (22)': {'s': 'CS'},
            'trigeminal nerve': {'SN': '5N'},
            'zona incerta': {'Z1': 'ZI'},
        }

        cor_a = {
            #'1': {'ependymal layer', 'superficial layer'},
            #'2': {'intermediate layer', 'molecular layer'},
            #'3': {'deep layer', 'oculomotor nucleus (27)', 'pyramidal layer'},
            #'4': {'polymorph layer', 'trochlear nucleus (23)'},
            'KF': {'KollikerFuse nucleus (17)': 'KéllikerFuse nucleus (17)'},
            'SCS': {'superior colliculus, supertficial layer (25)':
                    'superior colliculus, superficial layer (25)'}}

        # close layer abbreviation issues
        # this of course means that abbrevs cannot be used as identifiers
        # but we already knew this
        abbrev_ok = {'1': {'superficial layer': 1, 'ependymal layer': 1},
                     '2': {'intermediate layer': 1, 'molecular layer': 1},
                     '3': {'oculomotor nucleus (27)': 4, 'deep layer': 1, 'pyramidal layer': 1},
                     '4': {'polymorph layer': 1, 'trochlear nucleus (23)': 1}}


        by_abbrev = collections.defaultdict(list)
        by_label = collections.defaultdict(list)
        abbrev_index = collections.defaultdict(list)
        label_index = collections.defaultdict(list)
        for n, legends in sorted(data):
            for abbrev, label in legends:
                if label in cor_l and abbrev in cor_l[label]:
                    abbrev = cor_l[label][abbrev]
                if abbrev in cor_a and label in cor_a[abbrev]:
                    label = cor_a[abbrev][label]
                by_abbrev[abbrev].append(label)
                by_label[label].append(abbrev)

                abbrev_index[abbrev].append(n)
                label_index[label].append(n)

        def dorder(thing, type=lambda v:v):
            return  {k:type(v) for k, v in sorted(thing.items(), key=lambda kv: kv[0].lower())}

        by_abbrev = dorder(by_abbrev, collections.Counter)
        by_label = dorder(by_label, collections.Counter)

        prob_a = {k:v for k, v in by_abbrev.items() if len(v) > 1}
        prob_l = {k:v for k, v in by_label.items() if len(v) > 1}

        pnorma = {k:dict(v) for k, v in prob_a.items()}
        assert pnorma == abbrev_ok, f'problem in abbrevs\n{pnorma}\n{abbrev_ok}'
        assert not prob_l, f'problem in labels {prob_l}'


        index_abbrev = dorder(abbrev_index, tuple)
        index_label = dorder(label_index, tuple)

        ia = sorted(set([(tuple(l), a, index_label[list(l)[0]], index_abbrev[a])
                         for a, l in by_abbrev.items()
                         if a not in abbrev_ok and
                         index_label[list(l)[0]] != index_abbrev[a]]))
        assert not ia, f'oops {ia}'

        il = sorted(set([(l, tuple(a), index_label[l], index_abbrev[list(a)[0]])
                         for l, a in by_label.items()
                         if list(a)[0] not in abbrev_ok and
                         index_label[l] != index_abbrev[list(a)[0]]]))
        assert not il, f'oops {il}'

        def paren_thing(label):
            if '(' in label:
                label_ws, pthing_cp = label.split('(', 1)
                return label_ws.strip(), int(pthing_cp.rstrip(')'))
            else:
                return label, None
        data_out = tuple((*paren_thing(label), list(abbrev)[0], index_label[label])
                         for label, abbrev in by_label.items())
        return data_out,

    @classmethod
    def validate(cls, d):
        return d


class BermanLabels(LabelsBase):
    """ Berman Cat labels """
    # sort by label/structure not by abbrev
    filename = 'berman-cat-labels'
    name = 'Berman 1968 cat brain stem labels'
    shortname = 'bercat'
    imports = parcCore,
    prefixes = {**makePrefixes('NIFRID', 'ilxtr', 'prov'), 'BERCAT':str(BERCAT)}
    sources = BermanSrc,
    namespace = BERCAT
    root = LabelRoot(iri=nsExact(namespace),
                     label='Berman 1968 cat label root',
                     shortname=shortname,
                     definingArtifacts=(s.artifact.iri for s in sources),
    )

    def _triples(self):
        for source in self.sources:
            for i, (label, paren_thing, abbrev, index) in enumerate(source):
                local_identifier = str(i + 1)
                iri = self.namespace[local_identifier]  # TODO load from existing
                yield from Label(labelRoot=self.root,
                                label=label,
                                #altLabel=None,
                                #synonyms=extras,
                                abbrevs=(abbrev,),
                                iri=iri,)
                if paren_thing:
                    yield iri, ilx['berman/uris/readable/hasWeirdParenValue'], rdflib.Literal(paren_thing)

                continue
                # FIXME different file ...
                region_iri = ilx['berman/uris/cat/regions/' + local_identifier]
                # FIXME incorporate version in tree or no?
                # just have it be consecutive? HRM
                yield region_iri, rdf.type, owl.Class
                yield region_iri, ilxtr.hasParcellationLabel, iri  # FIXME predicate choice ...
                yield region_iri, ilxtr.isDefinedBy, BermanSrc.artifact.iri  # FIXME
                for plate_num in index:
                    yield region_iri, ilxtr.appearsOnPlateNumber, rdflib.Literal(plate_num)  # FIXME generalize ...


def main():
    b = BermanLabels.setup()
    b.make()
    bs = BermanSrc(dry_run=True)
    breakpoint()


if __name__ == '__main__':
    main()
