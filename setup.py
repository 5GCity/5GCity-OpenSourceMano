from setuptools import setup, find_packages

setup(
    name='osmclient',
    version='0.1',
    author='Mike Marchetti',
    author_email='mmarchetti@sandvine.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click', 'prettytable', 'pyyaml', 'pycurl'
    ],
    test_suite='nose.collector',
    entry_points='''
        [console_scripts]
        osm=osmclient.scripts.osm:cli
        ''',
)
