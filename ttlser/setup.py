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

ttlfmt_require = ['docopt',
                  'joblib',     # FIXME better if this were optional? or just use a PPE?
]
tests_require = ['pytest'] + ttlfmt_require
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
    keywords='rdflib rdf deterministic turtle ttl',
    packages=['ttlser'],
    python_requires='>=3.7',
    tests_require=tests_require,
    install_requires=[
        'rdflib>=6.0.2',
    ],
    extras_require={'dev': ['pytest-cov', 'wheel'],
                    'ttlfmt': ttlfmt_require,
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
    data_files=[('share/ttlser/', ['test/nasty.ttl',
                                   'test/good.ttl']),],
)
