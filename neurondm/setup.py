from setuptools import setup

with open('README.md', 'rt') as f:
    long_description = f.read()

setup(
    name='neurondm',
    version='1.0.0',  # FIXME package vs core serializer
    description='A data model for neuron types.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tgbugs/pyontutils/neurondm',
    author='Tom Gillespie',
    author_email='tgbugs@gmail.com',
    license='MIT',
    classifiers=[],
    keywords=('neuron types NIF ontology neuroscience phenotype '
              'OWL rdf rdflib data model'),
    packages=['neurondm'],  # don't package models due to data resources needs?
    install_requires=[
        'pyontutils',
    ],
    entry_points={
        'console_scripts': [
            'neurondm-example=neurondm.example',
        ],
    },
)
