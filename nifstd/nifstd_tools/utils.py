import psutil
from pyontutils.utils import makeSimpleLogger

log = makeSimpleLogger('nifstd-tools')
logd = log.getChild('data')


def memoryCheck(vms_max_kb):
    """ Lookup vms_max using getCurrentVMSKb """
    safety_factor = 1.2
    vms_max = vms_max_kb
    vms_gigs = vms_max / 1024 ** 2
    buffer = safety_factor * vms_max
    buffer_gigs = buffer / 1024 ** 2
    vm = psutil.virtual_memory()
    free_gigs = vm.available / 1024 ** 2
    if vm.available < buffer:
        raise MemoryError('Running this requires quite a bit of memory ~ '
                          f'{vms_gigs:.2f}, you have {free_gigs:.2f} of the '
                          f'{buffer_gigs:.2f} needed')


def currentVMSKb():
    p = psutil.Process(os.getpid())
    return p.memory_info().vms


from pyontutils.core import OntId
from pyontutils.config import auth
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from lxml import etree


def ncbigenemapping(may_need_ncbigene_added):
    #urlbase = 'https://www.ncbi.nlm.nih.gov/gene/?term=Mus+musculus+'
    urlbase = ('https://www.ncbi.nlm.nih.gov/gene?term='
               '({gene_name}[Gene%20Name])%20AND%20{taxon_suffix}[Taxonomy%20ID]&'
               'report=xml')
    urls = [urlbase.format(gene_name=n, taxon_suffix=10090) for n in may_need_ncbigene_added]
    done2 = {}
    for u in urls:
        if u not in done2:
            print(u)
            done2[u] = requests.get(u)

    base = auth.get_path('resources') / 'genesearch'
    if not base.exists():
        base.mkdir()

    for resp in done2.values():
        fn = OntId(resp.url).quoted
        with open(base / fn, 'wb') as f:
            f.write(resp.content)

    so_much_soup = [(resp.url, BeautifulSoup(resp.content, 'lxml')) for resp in done2.values()]

    trees = []
    for i, (url, soup) in enumerate(so_much_soup):
        pre = soup.find_all('pre')
        if pre:
            for p in pre[0].text.split('\n\n'):
                if p:
                    tree = etree.fromstring(p)
                    trees.append((url, tree))
        else:
            print('WAT', urls[i])

    dimension = 'ilxtr:hasExpressionPhenotype'
    errors = []
    to_add = []
    mapping = {}
    for url, tree in trees:
        taxon = tree.xpath('//Org-ref//Object-id_id/text()')[0]
        geneid = tree.xpath('//Gene-track_geneid/text()')[0]
        genename = tree.xpath('//Gene-ref_locus/text()')[0]
        if genename in may_need_ncbigene_added and taxon == '10090':
            print(f'{genename} = Phenotype(\'NCBIGene:{geneid}\', {dimension!r}, label={genename!r}, override=True)')
            to_add.append(geneid)
            mapping[genename] = f'NCBIGene:{geneid}'
        else:
            errors.append((geneid, genename, taxon, url))

    print(errors)
    _ = [print('NCBIGene:' + ta) for ta in to_add]

    #wat.find_all('div', **{'class':'rprt-header'})
    #wat.find_all('div', **{'class':'ncbi-docsum'})

    return mapping, to_add, errors
