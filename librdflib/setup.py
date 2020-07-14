import re
from setuptools import setup


def find_version(filename):
    _version_re = re.compile(r"__version__ = '(.*)'")
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            return version_match.group(1)


__version__ = find_version('librdflib/__init__.py')

with open('README.md', 'rt') as f:
    long_description = f.read()

tests_require = ['pytest']
setup(
    name='librdflib',
    version=__version__,
    description='librdf parser for rdflib',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tgbugs/pyontutils/tree/master/librdflib',
    author='Tom Gillespie',
    author_email='tgbugs@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    keywords='rdflib librdf rdf parser parsing ttl rdfxml',
    packages=['librdflib'],
    python_requires='>=3',
    tests_require=tests_require,
    install_requires=[
        'rdflib',  # really 5.0.0 if my changes go in but dev < 5
    ],
    extras_require={'dev': ['pytest-cov', 'wheel'],
                    'test': tests_require,
    },
    entry_points={
        'rdf.plugins.parser': [
            'librdfxml = librdflib:libRdfxmlParser',
            'libttl = librdflib:libTurtleParser',
        ],
    },
)
