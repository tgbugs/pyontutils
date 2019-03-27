from setuptools import setup

# since setuptools cannot actually exclude files so just grab the ones we want

with open('README.md', 'rt') as f:
    long_description = f.read()

setup(
    name='nifstd-tools',
    version='0.0.1',
    description='utilities for working with the NIF ontology',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tgbugs/pyontutils/nifstd',
    author='Tom Gillespie',
    author_email='tgbugs@gmail.com',
    license='MIT',
    classifiers=[],
    keywords='nif nifstd ontology pyontutils neuroscience',
    packages=['nifstd_tools'],
    install_requires=[
        'flask',
        'pymysql',
        'pyontutils>=0.1.0'
        'sqlalchemy',
    ],
    extras_require={'dev':[
        'hunspell',
        'mysql-connector',
        'protobuf',
    ]},
    entry_points={
        'console_scripts': [
            'ont-docs=nifstd_tools.docs:main',
            'ontree=nifstd_tools.ontree:main',
            'registry-sync=nifstd_tools.scr_sync:main',
        ],
    },
)

