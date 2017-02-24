import yaml


config = None
with open('config.yaml') as f:
    config = yaml.load(f)


def pytest_addoption(parser):
    for param in config:
        parser.addoption("--{}".format(param),
                         action="store",
                         type="{}".format(config[param]["type"]),
                         default="{}".format(config[param]["default"]),
                         help="{}".format(config[param]["description"])
                         )


def pytest_generate_tests(metafunc):
    for param in config:
        if param in metafunc.fixturenames:
            metafunc.parametrize(param, [metafunc.config.getoption(param)])
