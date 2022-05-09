import os
import shlex
import shutil
import subprocess

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# Obtain version from env (incremented by CI), or from git (local dev)
version = 'unknown'
if os.environ.get('VERSION'):
    version = os.environ['VERSION']
else:
    if shutil.which('git'):
        gitcmd = shlex.split('git rev-parse --short HEAD')
        gitproc = subprocess.run(gitcmd, capture_output=True, check=False)
        version = f"git.{gitproc.stdout.decode().strip()}"

setup(
    name='django_informixdb',
    version=version,
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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    keywords='django informix',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=['django>=3.2.0,<5', 'pyodbc~=4.0.21'],
    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage'],
    },
)
