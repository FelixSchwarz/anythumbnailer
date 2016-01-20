#!/usr/bin/env python

import os

from setuptools import setup, find_packages


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

setup(
    name='anythumbnailer',
    version='0.1',
    description='Generic Thumbnailer library',
    long_description=read('README.txt'),

    author='Felix Schwarz',
    author_email='info@schwarz.eu',
    url='https://github.com/FelixSchwarz/anythumbnailer',
    license='MIT', # see LICENSE.txt
    packages=find_packages(),
    entry_points = {
        'console_scripts': [
            'anythumbnail = anythumbnailer.cli:main',
        ]
    }
)

