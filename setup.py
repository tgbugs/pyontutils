from setuptools import setup, find_packages

setup(
    name='pyontutils',
    version='0',
    description='utilities for working with the NIFSTD ontology and SciGraph',
    long_description=' ',
    url='https://github.com/tgbugs/pyontutils',
    author='Tom Gillespie',
    author_email='tgbugs@gmail.com',
    license='MIT',
    classifiers=[],
    keywords='nif nifstd ontology scigraph',
    packages=['pyontutils'], #.hierarchies', 'pyontutils.scigraph_client', 'pyontutils.utils'],
    package_dir={'pyontutils':'./'},
    #scripts=['scigraph.py', 'scig.py',],
    install_requires=[
        'docopt',
        'numpy',
        'psycopg2',
        'requests',
        'ipython',
        'rdflib',
        'sqlalchemy',
        'yaml',
        'lxml',
    ],
    #extras_require
    #package_data
    #data_files
    entry_points={
        'console_scripts': [
            'scig=scig:main',
        ],
    },
)
