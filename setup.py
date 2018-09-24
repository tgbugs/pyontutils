import os
import shutil
from setuptools import setup

# since setuptools cannot actually exclude files so just grab the ones we want

with open('README.md', 'rt') as f:
    long_description = f.read()

files = [
    'pyontutils/__init__.py',
    'pyontutils/closed_namespaces.py',
    'pyontutils/combinators.py',
    'pyontutils/config.py',
    'pyontutils/core.py',
    'pyontutils/docs.py',  # for dev
    'pyontutils/graphml_to_ttl.py',
    'pyontutils/hierarchies.py',
    'pyontutils/htmlfun.py',
    'pyontutils/ilxcli.py',
    'pyontutils/ilx_utils.py',
    'pyontutils/namespaces.py',
    'pyontutils/necromancy.py',
    'pyontutils/neurons/core.py',
    'pyontutils/neurons/lang.py',
    'pyontutils/obo_io.py',
    'pyontutils/ontload.py',
    'pyontutils/ontree.py',
    'pyontutils/ontutils.py',
    'pyontutils/overlaps.py',
    'pyontutils/phenotype_namespaces.py',
    'pyontutils/qnamefix.py',
    'pyontutils/scig.py',
    'pyontutils/scigraph.py',
    'pyontutils/scigraph_deploy.py',
    'pyontutils/scigraph_client.py',
    'pyontutils/scr_sync.py',
    'pyontutils/ttlfmt.py',
    'pyontutils/ttlser.py',
    'pyontutils/utils.py',
]

try:
    os.mkdir('export')
    os.mkdir('export/neurons')
    for f in files:
        shutil.copyfile(f, f.replace('pyontutils','export'))
    setup(
        name='pyontutils',
        version='0.0.3',
        description='utilities for working with the NIF ontology, SciGraph, and turtle',
        long_description=long_description,
        long_description_content_type='text/markdown',
        url='https://github.com/tgbugs/pyontutils',
        author='Tom Gillespie',
        author_email='tgbugs@gmail.com',
        license='MIT',
        classifiers=[],
        keywords='nif nifstd ontology scigraph rdflib turtle ttl',
        package_dir={'pyontutils':'export'},
        packages=['pyontutils'],
        install_requires=[
            'docopt',
            'flask',
            'gitpython',
            'ipython',
            'joblib',
            'lxml',
            'ontquery',
            'psutil',
            'pymysql',
            'pyyaml',
            'rdflib',
            'requests',
            'robobrowser',
            'sqlalchemy',
        ],
        extras_require={'dev':[
            'hunspell',
            'jupyter',
            'mysql-connector',
            'protobuf',
            'psycopg2',
        ]},
        #package_data
        #data_files=[('resources',['pyontutils/resources/chebi-subset-ids.txt',])],  # not part of distro
        scripts=['bin/ttlcmp'],
        entry_points={
            'console_scripts': [
                'graphml-to-ttl=pyontutils.graphml_to_ttl:main',
                'ilxcli=pyontutils.ilxcli:main',
                'necromancy=pyontutils.necromancy:main',
                'ont-catalog=pyontutils.make_catalog:main',
                'ont-docs=pyontutils.docs:main',
                'ontload=pyontutils.ontload:main',
                'ontree=pyontutils.ontree:main',
                'ontutils=pyontutils.ontutils:main',
                'overlaps=pyontutils.overlaps:main',
                'qnamefix=pyontutils.qnamefix:main',
                'registry-sync=pyontutils.scr_sync:main',
                'scigraph-codegen=pyontutils.scigraph_codegen:main',
                'scigraph-deploy=pyontutils.scigraph_deploy:main',
                'scig=pyontutils.scig:main',
                'ttlfmt=pyontutils.ttlfmt:main',
            ],
        },
    )

finally:
    shutil.rmtree('export')
