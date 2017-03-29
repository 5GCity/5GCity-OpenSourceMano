import pytest

def pytest_addoption(parser):
    parser.addoption('--so-host', action='store', default='127.0.0.1')
    parser.addoption('--so-port', action='store', default='8008')
    parser.addoption('--so-user', action='store', default='admin')
    parser.addoption('--so-pass', action='store', default='admin')
    parser.addoption('--vim-type', action='store')
    parser.addoption('--vim-host', action='store')
    parser.addoption('--vim-user', action='store')
    parser.addoption('--vim-tenant', action='store')
    parser.addoption('--vim-pass', action='store')
    parser.addoption('--package-location', action='store')
    return parser

@pytest.fixture(scope='session')
def so_host(request):
    """Fixture that returns --so-host option value"""
    return request.config.getoption("--so-host")

@pytest.fixture(scope='session')
def so_port(request):
    """Fixture that returns --so-port option value"""
    return request.config.getoption("--so-port")
 
@pytest.fixture(scope='session')
def so_user(request):
    """Fixture that returns --so-user option value"""
    return request.config.getoption("--so-user")

@pytest.fixture(scope='session')
def so_pass(request):
    """Fixture that returns --so-pass option value"""
    return request.config.getoption("--so-pass")
 
@pytest.fixture(scope='session')
def vim_type(request):
    """Fixture that returns --vim-type option value"""
    return request.config.getoption("--vim-type")
    
@pytest.fixture(scope='session')
def vim_host(request):
    """Fixture that returns --vim-host option value"""
    return request.config.getoption("--vim-host")
    
@pytest.fixture(scope='session')
def vim_user(request):
    """Fixture that returns --vim-user option value"""
    return request.config.getoption("--vim-user")

@pytest.fixture(scope='session')
def vim_pass(request):
    """Fixture that returns --vim-pass option value"""
    return request.config.getoption("--vim-pass")

@pytest.fixture(scope='session')
def vim_tenant(request):
    """Fixture that returns --vim-tenant option value"""
    return request.config.getoption("--vim-tenant")

@pytest.fixture(scope='session')
def package_location(request):
    """Fixture that returns --package-location option value"""
    return request.config.getoption("--package-location")
