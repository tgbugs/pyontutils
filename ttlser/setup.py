from setuptools import setup

with open('README.md', 'rt') as f:
    long_description = f.read()

tests_require = ['pytest', 'pytest-runner']
setup(
    name='ttlser',
    version='1.0.0',  # FIXME package vs core serializer
    description='Deterministic turtle serialization for rdflib.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tgbugs/pyontutils/tree/master/ttlser',
    author='Tom Gillespie',
    author_email='tgbugs@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='rdflib rdf deterministic turtle ttl',
    packages=['ttlser'],
    python_requires='>=3.5',
    tests_require=tests_require,
    install_requires=[
        'docopt',
        'joblib',     # FIXME better if this were optional? or just use a PPE?
        'neurdflib',  # really 5.0.0 if my changes go in but dev < 5
    ],
    extras_require={'dev': [],
                    'test': tests_require},
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
