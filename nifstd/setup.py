import re
import os
import sys
from pathlib import Path
from setuptools import setup


def find_version(filename):
    _version_re = re.compile(r"__version__ = '(.*)'")
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            return version_match.group(1)


__version__ = find_version('nifstd_tools/__init__.py')


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
        './scigraph/README.org',)


tests_require = ['pytest']
setup(
    name='nifstd-tools',
    version=__version__,
    description='utilities for working with the NIF ontology',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tgbugs/pyontutils/tree/master/nifstd',
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
    keywords='nif nifstd ontology pyontutils neuroscience',
    packages=['nifstd_tools'],
    python_requires='>=3.7',
    tests_require=tests_require,
    install_requires=[
        'beautifulsoup4',
        'flask',
        'nbconvert',
        'nbformat',
        'networkx',
        'psutil',
        'pymysql',
        'pyontutils>=0.1.26',
        'sqlalchemy',
    ],
    extras_require={'dev': ['mysql-connector',
                            'protobuf',
                            'pytest-cov',
                            'wheel',
                           ],
                    'spell': ['hunspell'],
                    'test': tests_require,
    },
    scripts=['bin/ttlcmp'],
    entry_points={
        'console_scripts': [
            'ont-docs=nifstd_tools.docs:main',
            'ontree=nifstd_tools.ontree:main',
            'registry-sync=nifstd_tools.scr_sync:main',
            'slimgen=nifstd_tools.slimgen:main',
        ],
    },
    data_files=[('share/nifstd/resources/sparc_term_versions/',
                 ['resources/sparc_term_versions/sparc_terms2-mod.txt']),
                ('share/nifstd/resources/',
                 [p.as_posix() for p in Path('resources').iterdir()
                  if p.is_file() and
                  not p.name.startswith('.') and
                  p.suffix[1:] not in
                  ('confd', 'rc', 'service', 'socket', 'tmp', 'spec')],)])
