from setuptools import setup
from htmlfn import __version__

with open('README.md', 'rt') as f:
    long_description = f.read()

tests_require = ['pytest', 'pytest-runner']
setup(
    name='htmlfn',
    version=__version__,
    description='functions for generating html',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tgbugs/pyontutils/tree/master/htmlfn',
    author='Tom Gillespie',
    author_email='tgbugs@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='html tags functional',
    packages=['htmlfn'],
    python_requires='>=3.6',
    tests_require=tests_require,
    extras_require={'dev': [],
                    'test': tests_require,
    },
)
