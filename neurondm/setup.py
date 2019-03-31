from setuptools import setup

with open('README.md', 'rt') as f:
    long_description = f.read()

tests_require = ['pytest', 'pytest-runner']
setup(
    name='neurondm',
    version='1.0.0',  # FIXME package vs core serializer
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
        'pyontutils>=0.1.0',
    ],
    extras_require={'dev': [],
                    'test': tests_require,
                    'notebook': ['jupyter'],
    },
    entry_points={
        'console_scripts': [
        ],
    },
)
