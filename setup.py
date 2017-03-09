#!/usr/bin/env python

from distutils.core import setup
#import glob

setup(name='osm-ro',
      version='1.0',
      description='OSM Resource Orchestrator',
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

