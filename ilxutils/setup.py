from setuptools import setup, find_packages

setup(
    name='interlexutils',
    version='0.0.2',
    description='Uploads terms to SciCrunch',
    long_description='',
    url='https://github.com/tmsincomb/interlexutils',
    author='Troy Sincomb',
    author_email='troysincomb@gmail.com',
    license='MIT',
    keywords='scicrunch sci',
    packages=['ilxutils'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    install_requires=[
        'pandas',
        'requests',
    	'progressbar2',
    	'aiohttp',
    	'asyncio',
    	'sqlalchemy',
    ],
    entry_points={
        'console_scripts': [
            'scicrunch_client = ilxutils.scicrunch_client : main',
            'interlex_sql = ilxutils.interlex_sql : main',
            'args_reader = ilxutils.args_reader : main',
            'interlex = ilxutils.cli: main',
        ],
    },
)
