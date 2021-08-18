import re
import os
import sys
from setuptools import setup


def find_version(filename):
    _version_re = re.compile(r"__version__ = '(.*)'")
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            return version_match.group(1)


__version__ = find_version('pyontutils/__init__.py')


def tangle_files(*files):
    """ emacs org babel tangle blocks to files for release """

    argv = [
        'emacs',
        '--batch',
        '--quick',
        '--directory', '.',
        '--load', 'org',
        '--load', 'ob-shell',
        '--load', 'ob-python',
     ] + [arg
          for f in files
          for arg in ['--eval', f'"(org-babel-tangle-file \\"{f}\\")"']]

    os.system(' '.join(argv))


with open('README.md', 'rt') as f:
    long_description = f.read()

RELEASE = '--release' in sys.argv
if RELEASE:
    sys.argv.remove('--release')
    tangle_files(
        './docs/release.org',)

tests_require = ['pytest']
setup(
    name='pyontutils',
    version=__version__,
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
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
    ],
    keywords='ontology scigraph rdflib turtle ttl OWL',
    packages=['pyontutils'],
    python_requires='>=3.6',
    tests_require=tests_require,
    install_requires=[
        'augpathlib>=0.0.21',
        'colorlog',
        'docopt',
        'gitpython',
        'google-api-python-client',
        'google-auth-oauthlib',
        'htmlfn',
        'idlib>=0.0.1.dev7',
        "ipython; python_version < '3.7'",
        'joblib>=0.14.1',
        'lxml',
        'nest_asyncio',
        'ontquery>=0.2.6',
        'orthauth>=0.0.14',
        'pyld',
        'pyyaml',
        'requests',
        'terminaltables',
        'ttlser>=1.1.3',
    ],
    extras_require={'dev': ['pytest-cov', 'wheel'],
                    'spell': ['hunspell'],
                    'test': tests_require,
                   },
    entry_points={
        'console_scripts': [
            'googapis=pyontutils.googapis:main',
            'graphml-to-ttl=pyontutils.graphml_to_ttl:main',
            'necromancy=pyontutils.necromancy:main',
            'obo-io=pyontutils.obo_io:main',
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
    #package_data
    #data_files=[('resources',['pyontutils/resources/chebi-subset-ids.txt',])],  # not part of distro
    #data_files=[('share/idlib/local-conventions/nifstd/', ['nifstd/scigraph/curie_map.yaml']),],
    data_files=[('share/pyontutils/', ['nifstd/scigraph/curie_map.yaml']),],
)
