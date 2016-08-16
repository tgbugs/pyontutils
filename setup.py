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
    packages = find_packages(exclude=['tests*', 'resources*','complete*']),
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
