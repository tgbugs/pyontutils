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
        from neurondm.core import auth
        olr = Path(auth.get_path('ontology-local-repo'))
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

tests_require = ['pytest', 'pytest-runner']
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
        ],
        keywords=('neuron types NIF ontology neuroscience phenotype '
                'OWL rdf rdflib data model'),
        packages=['neurondm'],  # don't package models due to data resources needs?
        python_requires='>=3.6',
        tests_require=tests_require,
        install_requires=[
            'hyputils>=0.0.4',
            'pyontutils>=0.1.7',
        ],
        extras_require={'dev': ['pytest-cov', 'wheel'],
                        'test': tests_require,
                        'notebook': ['jupyter'],
        },
        entry_points={
            'console_scripts': [
            ],
        },
        data_files=[('share/neurondm', ontology_data_files)]
    )
finally:
    if RELEASE:
        resources.rmtree()
