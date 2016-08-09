#!/usr/bin/env python

from distutils.core import setup

setup(
    name='testapp',
    version='0.1.0',
    description='',
    author='Kennedy Brown',
    packages=['testapp'],
    install_requires=open("requirements.txt", "r").readlines(),
    scripts=['bin/testapp'],
)
