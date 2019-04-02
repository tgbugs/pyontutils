import re
from setuptools import setup


def find_version(filename):
    _version_re = re.compile(r"__version__ = '(.*)'")
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            return version_match.group(1)


__version__ = find_version('ttlser/__init__.py')

with open('README.md', 'rt') as f:
    long_description = f.read()

tests_require = ['pytest', 'pytest-runner']
setup(
    name='ttlser',
    version=__version__,
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
        'neurdflib',  # really 5.0.0 if my changes go in but dev < 5
    ],
    extras_require={'dev': [],
                    'ttlfmt': ['docopt',
                               'joblib',     # FIXME better if this were optional? or just use a PPE?
                              ],
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
