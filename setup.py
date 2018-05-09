#!/usr/bin/env python3

import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
_name = "osm_common"
VERSION = "4.0.0rc2"
README = open(os.path.join(here, 'README.rst')).read()

setup(
    # python_requires='>=3.5',
    name=_name,
    description='OSM common utilities',
    long_description=README,
    # version_command=('git describe --tags --long --dirty', 'pep440-git'),
    version=VERSION,
    # python_requires='>3.5',
    author='ETSI OSM',
    author_email='alfonso.tiernosepulveda@telefonica.com',
    maintainer='Alfonso Tierno',
    maintainer_email='alfonso.tiernosepulveda@telefonica.com',
    url='https://osm.etsi.org/gitweb/?p=osm/common.git;a=summary',
    license='Apache 2.0',
    # setup_requires=['setuptools-version-command'],

    packages=[_name],
    include_package_data=True,
    # scripts=['nbi.py'],

    install_requires=[
        'pymongo',
        'aiokafka',
        'PyYAML',
        'pip',
    ],
)

