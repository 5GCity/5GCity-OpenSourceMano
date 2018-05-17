#!/usr/bin/env python3

import os
from setuptools import setup

_name = "osm_lcm"
# version is at first line of osm_lcm/html_public/version
here = os.path.abspath(os.path.dirname(__file__))
VERSION = "4.0.1rc1"
with open(os.path.join(here, 'README.rst')) as readme_file:
    README = readme_file.read()

setup(
    name=_name,
    description='OSM North Bound Interface',
    long_description=README,
    # version_command=('git describe --tags --long --dirty', 'pep440-git'),
    version=VERSION,
    # python_requires='>3.5.0',
    author='ETSI OSM',
    author_email='alfonso.tiernosepulveda@telefonica.com',
    maintainer='Alfonso Tierno',
    maintainer_email='alfonso.tiernosepulveda@telefonica.com',
    url='https://osm.etsi.org/gitweb/?p=osm/LCM.git;a=summary',
    license='Apache 2.0',

    packages=[_name],
    include_package_data=True,
    data_files=[('/etc/osm/', ['osm_lcm/lcm.cfg']),
                ('/etc/systemd/system/', ['osm_lcm/osm-lcm.service']),
                ],
    dependency_links=[
        "git+https://osm.etsi.org/gerrit/osm/common.git@master#egg=osm-common-0.1.4"
    ],
    install_requires=[
        'pymongo', 'PyYAML',
        # 'osm-common',
    ],
    # setup_requires=['setuptools-version-command'],
    # test_suite='nose.collector',
    # entry_points='''
    #     [console_scripts]
    #     osm=osm_lcm.lcm:lcm
    #     ''',
)
