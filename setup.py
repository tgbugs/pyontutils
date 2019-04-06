import re
from setuptools import setup


def find_version(filename):
    _version_re = re.compile(r"__version__ = '(.*)'")
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            return version_match.group(1)


__version__ = find_version('pyontutils/__init__.py')

with open('README.md', 'rt') as f:
    long_description = f.read()

tests_require = ['pytest', 'pytest-runner']
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
    ],
    keywords='ontology scigraph rdflib turtle ttl OWL',
    packages=['pyontutils'],
    python_requires='>=3.6',
    tests_require=tests_require,
    install_requires=[
        'appdirs',
        'docopt',
        'gitpython',
        'google-api-python-client',
        'hyputils',
        'ipython',
        'joblib',
        'lxml',
        'oauth2client',
        'ontquery>=0.0.8',
        'psutil',
        'pyyaml',
        'requests',
        'ttlser',
    ],
    extras_require={'dev': ['pytest-cov', 'wheel'],
                    'spell': ['hunspell'],
                    'test': tests_require,
                   },
    #package_data
    #data_files=[('resources',['pyontutils/resources/chebi-subset-ids.txt',])],  # not part of distro
    entry_points={
        'console_scripts': [
            'graphml-to-ttl=pyontutils.graphml_to_ttl:main',
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
