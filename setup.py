from setuptools import setup, find_packages

setup(
    name='osm_im',
    description='OSM Information Model',
    long_description = open('README.rst').read(),
    version_command=('git describe --tags --long --dirty', 'pep440-git'),
    author='Mike Marchetti',
    author_email='mmarchetti@sandvine.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'pyangbind'
    ],
    setup_requires=['setuptools-version-command'],
    test_suite='nose.collector',
)
