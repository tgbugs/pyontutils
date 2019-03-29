from setuptools import setup

with open('README.md', 'rt') as f:
    long_description = f.read()

tests_require = ['pytest', 'pytest-runner']
setup(
    name='librdflib',
    version='0.0.1',  # FIXME package vs core serializer
    description='librdf parser for rdflib',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tgbugs/pyontutils/librdflib',
    author='Tom Gillespie',
    author_email='tgbugs@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
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
    extras_require={'dev': [],
                    'test': tests_require,
    },
    entry_points={
        'rdf.plugins.parser': [
            'librdfxml = librdflib:libRdfxmlParser',
            'libttl = librdflib:libTurtleParser',
        ],
    },
)
