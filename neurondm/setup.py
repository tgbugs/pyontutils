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
        ### KILL IT WITH FIRE
        try:
            from neurondm.core import auth  ### this is NOT ok
        except Exception:
            # can't catch an error that you can never import because
            # it will be raised before you can import it ... SIGH
            import orthauth as oa
            from pyontutils.config import auth as pauth
            auth = oa.configure(Path('neurondm/auth-config.py').resolve(), include=pauth)
        ###

        olr = Path(auth.get_path('ontology-local-repo'))

        ### KILL IT WITH FIRE
        if not olr.exists():
            original = auth.get('ontology-local-repo')
            raise FileNotFoundError(f'ontology local repo does not exist: {olr}'
                                    f'path expanded from {original}')
        elif olr.repo.active_branch.name != auth.get('neurons-branch'):
            # FIXME yes indeed having to call Config in a way that is
            # invoked at import time is REALLY REALLY BAD :/
            raise ValueError('git is on the wrong branch! '
                             f'{olr.repo.active_branch}')
        ###

        resources = Path(resources)
        resources.mkdir()  # if we add resources to git, this will error before we delete by accident
        paths = [olr / rp for rp in relpaths]
        for p in paths:
            p.copy_to(resources / p.name)

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
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Operating System :: POSIX :: Linux',
            'Operating System :: MacOS :: MacOS X',
            'Operating System :: Microsoft :: Windows',
        ],
        keywords=('neuron types NIF ontology neuroscience phenotype '
                'OWL rdf rdflib data model'),
        packages=['neurondm', 'neurondm.models'],  # don't package models due to data resources needs?
        python_requires='>=3.6',
        tests_require=tests_require,
        install_requires=[
            'hyputils>=0.0.8',
            'pyontutils>=0.1.31',
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
