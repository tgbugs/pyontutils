from setuptools import setup

with open('README.md', 'rt') as f:
    long_description = f.read()

setup(
    name='ttlser',
    version='1.0.0',  # FIXME package vs core serializer
    description='Deterministic turtle serialization for rdflib.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tgbugs/pyontutils/ttlser',
    author='Tom Gillespie',
    author_email='tgbugs@gmail.com',
    license='MIT',
    classifiers=[],
    keywords='rdflib rdf deterministic turtle ttl',
    packages=['ttlser'],
    install_requires=[
        'docopt',
        'joblib',     # FIXME better if this were optional? or just use a PPE?
        'neurdflib',  # FIXME rdflib>=5.0.0 if I can get my changes merged
    ],
    entry_points={
        'console_scripts': [
            'ttlfmt=ttlser.ttlfmt:main',
        ],
        'rdf.plugins.serializer': [
            'nifttl = ttlser:CustomTurtleSerializer',
            'detttl = ttlser:CustomTurtleSerializer',
            'cmpttl = ttlser:CompactTurtleSerializer',
            'uncmpttl = ttlser:CompactTurtleSerializer',
            'rktttl = ttlser:CompactTurtleSerializer',
        ],
    },
)
