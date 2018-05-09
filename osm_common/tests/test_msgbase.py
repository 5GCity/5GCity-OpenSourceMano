import http
import pytest

from osm_common.msgbase import MsgBase, MsgException


def exception_message(message):
    return "messaging exception " + message

@pytest.fixture
def msg_base():
    return MsgBase()

def test_constructor():
    msgbase = MsgBase()

    assert msgbase != None
    assert isinstance(msgbase, MsgBase)

def test_connect(msg_base):
    msg_base.connect(None)

def test_disconnect(msg_base):
    msg_base.disconnect()

def test_write(msg_base):
    with pytest.raises(MsgException) as excinfo:
        msg_base.write("test", "test", "test")
    assert str(excinfo.value).startswith(exception_message("Method 'write' not implemented"))
    assert excinfo.value.http_code == http.HTTPStatus.INTERNAL_SERVER_ERROR

def test_read(msg_base):
    with pytest.raises(MsgException) as excinfo:
        msg_base.read("test")
    assert str(excinfo.value).startswith(exception_message("Method 'read' not implemented"))
    assert excinfo.value.http_code == http.HTTPStatus.INTERNAL_SERVER_ERROR

def test_aiowrite(msg_base, event_loop):
    with pytest.raises(MsgException) as excinfo:
        event_loop.run_until_complete(msg_base.aiowrite("test", "test", "test", event_loop))
    assert str(excinfo.value).startswith(exception_message("Method 'aiowrite' not implemented"))
    assert excinfo.value.http_code == http.HTTPStatus.INTERNAL_SERVER_ERROR

def test_aioread(msg_base, event_loop):
    with pytest.raises(MsgException) as excinfo:
        event_loop.run_until_complete(msg_base.aioread("test", event_loop))
    assert str(excinfo.value).startswith(exception_message("Method 'aioread' not implemented"))
    assert excinfo.value.http_code == http.HTTPStatus.INTERNAL_SERVER_ERROR
