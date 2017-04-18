#!/usr/bin/env python

from setuptools import setup
from setuptools.command.install import install
from os import system
#import glob

_name = 'osm_ro'
_version = '1.0.0'
_description = 'OSM Resource Orchestrator'
_author = 'ETSI OSM'
_author_email = 'alfonso.tiernosepulveda@telefonica.com'
_maintainer = 'garciadeblas'
_maintainer_email = 'gerardo.garciadeblas@telefonica.com'
_license = 'Apache 2.0'
_url = 'https://osm.etsi.org/gitweb/?p=osm/RO.git;a=summary'
_requirements = [
    "PyYAML",
    "bottle",
    "MySQL-python",
    "jsonschema",
    "paramiko",
    "argcomplete",
    "requests",
    "logutils",
    "python-novaclient",
    "python-keystoneclient",
    "python-glanceclient",
    "python-neutronclient",
    "python-cinderclient",
    "pyvcloud",
    "progressbar",
    "prettytable",
    "pyvmomi",
    "boto",
]

class ROInstaller(install):
    def run(self):
        cmd = 'echo "Running install script"'
        system(cmd)
        install.run(self)

setup(name=_name,
      version = _version,
      description = _description,
      long_description = open('README.rst').read(),
      author = _author,
      author_email = _author_email,
      maintainer = _maintainer,
      maintainer_email = _maintainer_email,
      url = _url,
      license = _license,
      packages = [_name],
      #packages = ['osm_ro', 'osm_roclient'],
      package_dir = {_name: _name},
      package_data = {_name: ['vnfs/*.yaml', 'vnfs/examples/*.yaml',
                         'scenarios/*.yaml', 'scenarios/examples/*.yaml',
                         'instance-scenarios/examples/*.yaml', 'database_utils/*',
                         'scripts/install-openmano*.sh']},
      data_files = [('/etc/osm/', ['openmanod.cfg']),
                   ('/etc/systemd/system/', ['osm-ro.service']),
                   ],
      scripts=['openmanod', 'openmano', 'osm_ro/scripts/service-openmano.sh', 'osm_ro/scripts/openmano-report.sh',],
      install_requires=_requirements,
      include_package_data=True,
      cmdclass = {'install': ROInstaller},
      )

