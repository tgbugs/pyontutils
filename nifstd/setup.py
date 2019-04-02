from setuptools import setup
from nifstd_tools import __version__

# since setuptools cannot actually exclude files so just grab the ones we want

with open('README.md', 'rt') as f:
    long_description = f.read()

tests_require = ['pytest', 'pytest-runner']
setup(
    name='nifstd-tools',
    version=__version__,
    description='utilities for working with the NIF ontology',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tgbugs/pyontutils/tree/master/nifstd',
    author='Tom Gillespie',
    author_email='tgbugs@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='nif nifstd ontology pyontutils neuroscience',
    packages=['nifstd_tools'],
    python_requires='>=3.6',
    tests_require=tests_require,
    install_requires=[
        'flask',
        'nbconvert',
        'nbformat',
        'pymysql',
        'pyontutils>=0.1.0',
        'robobrowser',
        'sqlalchemy',
    ],
    extras_require={'dev': ['hunspell',
                            'mysql-connector',
                            'protobuf',
    ],
                    'test': tests_require,
    },
    scripts=['bin/ttlcmp'],
    entry_points={
        'console_scripts': [
            'ont-docs=nifstd_tools.docs:main',
            'ontree=nifstd_tools.ontree:main',
            'registry-sync=nifstd_tools.scr_sync:main',
        ],
    },
)
