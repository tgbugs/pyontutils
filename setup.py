import os
import shutil
from setuptools import setup

# since setuptools cannot actually exclude files so just grab the ones we want

with open('README.md', 'rt') as f:
    long_description = f.read()

files = [
    'pyontutils/__init__.py',
    'pyontutils/annotation.py',
    'pyontutils/closed_namespaces.py',
    'pyontutils/combinators.py',
    'pyontutils/config.py',
    'pyontutils/core.py',
    'pyontutils/graphml_to_ttl.py',
    'pyontutils/hierarchies.py',
    'pyontutils/ilxcli.py',
    'pyontutils/ilx_utils.py',
    'pyontutils/namespaces.py',
    'pyontutils/necromancy.py',
    'pyontutils/obo_io.py',
    'pyontutils/ontload.py',
    'pyontutils/ontutils.py',
    'pyontutils/overlaps.py',
    'pyontutils/qnamefix.py',
    'pyontutils/scig.py',
    'pyontutils/scigraph.py',
    'pyontutils/scigraph_deploy.py',
    'pyontutils/scigraph_client.py',
    'pyontutils/utils.py',
]

try:
    os.mkdir('export')
    os.mkdir('export/neurons')
    for f in files:
        shutil.copyfile(f, f.replace('pyontutils','export'))
    setup(
        name='pyontutils',
        version='0.1.0',
        description='utilities for working with the NIF ontology, SciGraph, and turtle',
        long_description=long_description,
        long_description_content_type='text/markdown',
        url='https://github.com/tgbugs/pyontutils',
        author='Tom Gillespie',
        author_email='tgbugs@gmail.com',
        license='MIT',
        classifiers=[
            'Development Status :: 4 - Beta',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
        ],
        keywords='ontology scigraph rdflib turtle ttl OWL',
        package_dir={'pyontutils':'export'},
        packages=['pyontutils'],
        install_requires=[
            'docopt',
            'gitpython',
            'hyputils',
            'ipython',
            'joblib',
            'lxml',
            'ontquery>=0.0.4',
            'psutil',
            'pyyaml',
            'neurdflib',
            'requests',
            'robobrowser',
            'ttlser',
        ],
        extras_require={'dev':[
            'google-api-python-client',
            'hunspell',
            'jupyter',
            'mysql-connector',
            'oauth2client',
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
                'ontload=pyontutils.ontload:main',
                'ontutils=pyontutils.ontutils:main',
                'overlaps=pyontutils.overlaps:main',
                'qnamefix=pyontutils.qnamefix:main',
                'scigraph-codegen=pyontutils.scigraph_codegen:main',
                'scigraph-deploy=pyontutils.scigraph_deploy:main',
                'scig=pyontutils.scig:main',
            ],
        },
    )

finally:
    shutil.rmtree('export')
