#!/usr/bin/env python

from setuptools import setup
#import glob

requirements = [
    "PyYAML",
    "bottle",
    "mysqldb",
    "jsonschema",
    "paramiko",
    "argcomplete",
    "requests",
    "logutils",
    "pip",
    "novaclient",
    "keystoneclient",
    "glanceclient",
    "neutronclient",
    "cinderclient",
    "boto",
    "pyvcloud",
    "progressbar",
    "prettytable",
    "pyvmomi",
]

setup(name='osm-ro',
      version='1.0',
      description='OSM Resource Orchestrator',
      long_description=open('README.rst').read(),
      author='ETSI OSM',
      author_email='alfonso.tiernosepulveda@telefonica.com',
      maintainer='garciadeblas',
      maintainer_email='gerardo.garciadeblas@telefonica.com',
      url='https://osm.etsi.org/gitweb/?p=osm/RO.git;a=summary',
      license='Apache 2.0',
      #packages=['ro-server', 'ro-client'],
      #py_modules=glob.glob('*.py')
      py_modules=['console_proxy_thread',
                  'db_base',
                  'httpserver',
                  'nfvo_db',
                  'nfvo',
                  'openmanoclient',
                  'openmanoconfig',
                  'openmanod',
                  'openmano_schemas',
                  'utils',
                  'vimconn_openstack',
                  'vimconn_openvim',
                  'vimconn',
                  'vimconn_vmware',
                  'vmwarecli',
                  'vmwarerecli',
                 ],
     install_requires=requirements,
     #package_data={'': ['vnfs', 'scenarios', 'instance-scenarios', 'database_utils/mano_db_structure.sql']}
     data_files=[('/etc/osm/', ['openmanod.cfg']),
                 ('/etc/systemd/system/', ['openmano.service']),
                 ('vnfs', ['vnfs']),
                 ('scenarios', ['scenarios']),
                 ('instance-scenarios', ['instance-scenarios']),
                 ('database_utils', ['database-utils']),
                ],
     scripts=['openmanod.py', 'openmano', 'scripts/service-openmano', 'scripts/openmano-report',]
     )

