from setuptools import setup, find_packages

setup(
    name='ilxutils',
    version='0.0.2',
    description='Uploads terms to SciCrunch',
    long_description='',
    url='https://github.com/tmsincomb/ilxutils',
    author='Troy Sincomb',
    author_email='troysincomb@gmail.com',
    license='MIT',
    keywords='interlex',
    packages=['ilxutils'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    install_requires=[
        'pandas',
        'requests',
    	'progressbar2',
    	'aiohttp',
    	'asyncio',
    	'sqlalchemy',
        'pathlib',
    ],
    # TODO: add a get functionality thats more specific query
    # entry_points={
    #     'console_scripts': [
    #         'ilxutils = ilxutils.cli: main',
    #     ],
    # },
)
