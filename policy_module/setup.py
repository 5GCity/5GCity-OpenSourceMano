import setuptools


def parse_requirements(requirements):
    with open(requirements) as f:
        return [l.strip('\n') for l in f if l.strip('\n') and not l.startswith('#')]


_author = "Benjamín Díaz"
_name = 'osm_policy_module'
_author_email = 'bdiaz@whitestack.com'
_version = '1.0'
_description = 'OSM Policy Module'
_maintainer = 'Benjamín Díaz'
_maintainer_email = 'bdiaz@whitestack.com'
_license = 'Apache 2.0'
_url = 'https://osm.etsi.org/gitweb/?p=osm/MON.git;a=tree'

setuptools.setup(
    name=_name,
    version=_version,
    description=_description,
    long_description=open('README.rst').read(),
    author=_author,
    author_email=_author_email,
    maintainer=_maintainer,
    maintainer_email=_maintainer_email,
    url=_url,
    license=_license,
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=parse_requirements('requirements.txt'),
    entry_points={
        "console_scripts": [
            "pm-dbsync = osm_policy_module.cmd.dbsync:main",
            "pm-agent = osm_policy_module.cmd.policy_module_agent:main",
        ]
    }
)
