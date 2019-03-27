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
    classifiers=[],
    keywords='html tags functional',
    packages=['htmlfn'],
)
