from setuptools import setup

with open('README.md', 'rt') as f:
    long_description = f.read()

setup(
    name='htmlfn',
    version='0.0.1',
    description='functions for generating html',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tgbugs/pyontutils/htmlfn',
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
    tests_require=['pytest', 'pytest-runner'],
    extras_require={'dev':[]},
)
