import os
import shutil
from setuptools import setup, find_packages

# since setuptools cannot actually exclude files so just grab the ones we want

files = [
    'pyontutils/__init__.py',
    'pyontutils/hierarchies.py',
    'pyontutils/ilxcli.py',
    'pyontutils/ilx_utils.py',
    'pyontutils/necromancy.py',
    'pyontutils/neurons.py',
    'pyontutils/neuron_lang.py',
    'pyontutils/obo_io.py',
    'pyontutils/ontload.py',
    'pyontutils/ontrefactor.py',
    'pyontutils/overlaps.py',
    'pyontutils/phenotype_namespaces.py',
    'pyontutils/qnamefix.py',
    'pyontutils/scig.py',
    'pyontutils/scigraph.py',
    'pyontutils/scigraph-deploy.py',
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
            'gitpython',
            'ipython',
            'joblib',
            'lxml',
            'numpy',
            'psutil',
            'psycopg2',
            'pyyaml',
            'rdflib',
            'requests',
            'robobrowser',
            'sqlalchemy',
        ],
        #extras_require
        #package_data
        #data_files=[('resources',['pyontutils/resources/chebi-subset-ids.txt',])],  # not part of distro
        entry_points={
            'console_scripts': [
                'ilxcli=pyontutils.ilxcli:main',
                'necromancy=pyontutils.necromancy.py:main',
                'ontload=pyontutils.ontload:main',
                'ontrefactor=pyontutils.ontrefactor:main',
                'overlaps=pyontutils.overlaps:main',
                'qnamefix=pyontutils.qnamefix:main',
                'scigraph-codegen=pyontutils.scigraph:main',
                'scigraph-deploy=pyontutils.scigraph_deploy:main',
                'scig=pyontutils.scig:main',
                'ttlfmt=pyontutils.ttlfmt:main',
            ],
        },
    )

finally:
    shutil.rmtree('export')
