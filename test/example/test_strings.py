

def test_host(so_host):
    assert so_host == '127.0.0.1'


def test_port(so_host, so_port):
    assert so_host == '127.0.0.1'
    assert so_port == 80
