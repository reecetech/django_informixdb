from setuptools import setup, find_packages
from codecs import open
from os import path

from django_informixdb import __version__
here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='django_informixdb',
    version=__version__,
    description='A database driver for Django to connect to an Informix db via ODBC',
    long_description=long_description,
    url='https://github.com/reecetech/django_informixdb',
    author='Reecetech',
    author_email='opensource@reecetech.com.au',
    license='APLv2',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='django informix',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=['django>=1.9.6', 'pyodbc>=4.0.21'],
    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage'],
    },
)
