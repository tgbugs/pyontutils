def ncbigenemapping(may_need_ncbigene_added):
    from pyontutils.config import devconfig
    from pyontutils.core import OntId
    from pathlib import Path
    import requests
    from bs4 import BeautifulSoup
    from lxml import etree
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

    base = Path(devconfig.resources, 'genesearch')
    if not base.exists():
        base.mkdir()

    for resp in done2.values():
        fn = OntId(resp.url).quoted
        with open(base / fn, 'wb') as f:
            f.write(resp.content)

    so_much_soup = [BeautifulSoup(resp.content, 'lxml') for resp in done2.values()]

    trees = []
    for i, soup in enumerate(so_much_soup):
        pre = soup.find_all('pre')
        if pre:
            for p in pre[0].text.split('\n\n'):
                if p:
                    tree = etree.fromstring(p)
                    trees.append(tree)
        else:
            print('WAT', urls[i])

    dimension = 'ilxtr:hasExpressionPhenotype'
    errors = []
    to_add = []
    mapping = {}
    for tree in trees:
        taxon = tree.xpath('//Org-ref//Object-id_id/text()')[0]
        geneid = tree.xpath('//Gene-track_geneid/text()')[0]
        genename = tree.xpath('//Gene-ref_locus/text()')[0]
        if genename in may_need_ncbigene_added and taxon == '10090':
            print(f'{genename} = Phenotype(\'NCBIGene:{geneid}\', {dimension!r}, label={genename!r}, override=True)')
            to_add.append(geneid)
            mapping[genename] = f'NCBIGene:{geneid}'
        else:
            errors.append((geneid, genename, taxon))

    print(errors)
    _ = [print('NCBIGene:' + ta) for ta in to_add]

    #wat.find_all('div', **{'class':'rprt-header'})
    #wat.find_all('div', **{'class':'ncbi-docsum'})

    return mapping, to_add
