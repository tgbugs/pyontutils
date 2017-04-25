import os
import shutil
from setuptools import setup, find_packages

# since setuptools cannot actually exclude files so just grab the ones we want

files = [
    'pyontutils/__init__.py',
    'pyontutils/hierarchies.py',
    'pyontutils/ilx_utils.py',
    'pyontutils/neurons.py',
    'pyontutils/neuron_lang.py',
    'pyontutils/nif_load.py',
    'pyontutils/obo_io.py',
    'pyontutils/scig.py',
    'pyontutils/scigraph.py',
    'pyontutils/scigraph_client.py',
    'pyontutils/ttlfmt.py',
    'pyontutils/ttlser.py',
    'pyontutils/utils.py',
]

os.mkdir('export')
for f in files:
    shutil.copyfile(f, f.replace('pyontutils','export'))

try:
    setup(
        name='pyontutils',
        version='0.0.1',
        description='utilities for working with the NIFSTD ontology and SciGraph',
        long_description=' ',
        url='https://github.com/tgbugs/pyontutils',
        author='Tom Gillespie',
        author_email='tgbugs@gmail.com',
        license='MIT',
        classifiers=[],
        keywords='nif nifstd ontology scigraph',
        package_dir={'pyontutils':'export'},
        packages=['pyontutils'],
        install_requires=[
            'docopt',
            'numpy',
            'psycopg2',
            'requests',
            'ipython',
            'gitpython',
            'rdflib',
            'sqlalchemy',
            'pyyaml',
            'lxml',
        ],
        #extras_require
        #package_data
        #data_files=[('resources',['pyontutils/resources/chebi-subset-ids.txt',])],  # not part of distro
        entry_points={
            'console_scripts': [
                'scigraph-codegen=pyontutils.scigraph:main',
                'scig=pyontutils.scig:main',
                'ttlfmt=pyontutils.ttlfmt:main',
            ],
        },
    )

finally:
    shutil.rmtree('export')
