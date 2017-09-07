"""
Copyright (c) 2015 SONATA-NFV and Paderborn University
ALL RIGHTS RESERVED.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Neither the name of the SONATA-NFV, Paderborn University
nor the names of its contributors may be used to endorse or promote
products derived from this software without specific prior written
permission.

This work has been performed in the framework of the SONATA project,
funded by the European Commission under Grant number 671517 through
the Horizon 2020 and 5G-PPP programmes. The authors would like to
acknowledge the contributions of their colleagues of the SONATA
partner consortium (www.sonata-nfv.eu).
"""
"""
Additional setup that installs 'son-emu-cli' in standalone mode.
"""
from setuptools import setup, find_packages

setup(name='sonemucli',
      version='1.0',
      license='Apache 2.0',
      description='CLI client for son-emu',
      url='http://github.com/sonata-emu',
      author_email='sonata-dev@sonata-nfv.eu',
      package_dir={'': 'src'},
      packages=find_packages('src'),
      install_requires=[
          'tabulate',
          'argparse',
          'pytest',
          'requests',
          'prometheus_client',
          'urllib3'
      ],
      zip_safe=False,
      entry_points={
          'console_scripts': [
              'son-emu-cli=emuvim.cli.son_emu_cli:main',
          ],
      },
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
)
