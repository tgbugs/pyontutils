import re
import sys
from setuptools import setup


def find_version(filename):
    _version_re = re.compile(r"__version__ = '(.*)'")
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            return version_match.group(1)


__version__ = find_version('neurondm/__init__.py')

with open('README.md', 'rt') as f:
    long_description = f.read()

RELEASE = '--release' in sys.argv
if RELEASE:
    sys.argv.remove('--release')


def _ontology_data_files():
    resources = 'resources'
    relpaths = ['ttl/phenotype-core.ttl',
                'ttl/phenotype-indicators.ttl',
                'ttl/phenotypes.ttl',
                'ttl/generated/part-of-self.ttl',]
    if RELEASE:
        from augpathlib import RepoPath as Path
        from neurondm.core import auth  ### this is NOT ok
        from pyontutils.core import OntResGit
        olr = Path(auth.get_path('ontology-local-repo'))

        ### KILL IT WITH FIRE
        if not olr.exists():
            original = auth.get('ontology-local-repo')
            raise FileNotFoundError(f'ontology local repo does not exist: {olr}'
                                    f'path expanded from {original}')
        #elif olr.repo.active_branch.name != auth.get('neurons-branch'):
            # FIXME yes indeed having to call Config in a way that is
            # invoked at import time is REALLY REALLY BAD :/
            #raise ValueError('git is on the wrong branch! '
                             #f'{olr.repo.active_branch}')
        ###

        ref = auth.get('neurons-branch')
        resources = Path(resources)
        resources.mkdir()  # if we add resources to git, this will error before we delete by accident
        paths = [olr / rp for rp in relpaths]
        for p in paths:
            org = OntResGit(p, ref=ref)
            target = resources / p.name
            generator = org.data
            with open(target, 'wb') as f:
                for chunk in generator:
                    f.write(chunk)

    else:
        from pathlib import Path
        resources = Path(resources)
        paths = [Path(rp) for rp in relpaths]

    return resources.absolute(), [(resources / p.name).as_posix() for p in paths]


resources, ontology_data_files = _ontology_data_files()
print('ontology_data_files:\n\t' + '\n\t'.join(ontology_data_files))

models_require = ['nifstd-tools>=0.0.6']
tasic_require = ['pandas', 'anytree']
tests_require = ['pytest'] + models_require
try:
    setup(
        name='neurondm',
        version=__version__,
        description='A data model for neuron types.',
        long_description=long_description,
        long_description_content_type='text/markdown',
        url='https://github.com/tgbugs/pyontutils/tree/master/neurondm',
        author='Tom Gillespie',
        author_email='tgbugs@gmail.com',
        license='MIT',
        classifiers=[
            'Development Status :: 4 - Beta',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
            'Programming Language :: Python :: 3.12',
            'Programming Language :: Python :: 3.13',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Operating System :: POSIX :: Linux',
            'Operating System :: MacOS :: MacOS X',
            'Operating System :: Microsoft :: Windows',
        ],
        keywords=('neuron types NIF ontology neuroscience phenotype '
                'OWL rdf rdflib data model'),
        packages=['neurondm', 'neurondm.models'],  # don't package models due to data resources needs?
        python_requires='>=3.7',
        tests_require=tests_require,
        install_requires=[
            'hyputils>=0.0.10',
            'pyontutils>=0.1.38',
        ],
        extras_require={'dev': ['pytest-cov', 'wheel'],
                        'test': tests_require,
                        'models': models_require,
                        'tasic': tasic_require,
                        'notebook': ['jupyter'],
        },
        entry_points={
            'console_scripts': [
            ],
        },
        data_files=[('share/neurondm', ontology_data_files),
                    ]
    )
finally:
    if RELEASE:
        resources.rmtree()
