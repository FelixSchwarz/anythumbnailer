#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='anythumbnailer',
    description='Generic Thumbnailer library',
    version='0.1dev',

    author='Felix Schwarz',
    author_email='info@schwarz.eu',
    license='MIT', # see LICENSE.txt
    packages=find_packages(),
    entry_points = {
        'console_scripts': [
            'anythumbnail = anythumbnailer.cli:main',
        ]
    }
)

