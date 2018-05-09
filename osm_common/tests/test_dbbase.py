import http
import pytest

from osm_common.dbbase import DbBase, DbException

def exception_message(message):
    return "database exception " + message

@pytest.fixture
def db_base():
    return DbBase()

def test_constructor():
    db_base = DbBase()

    assert db_base != None
    assert isinstance(db_base, DbBase)

def test_db_connect(db_base):
    db_base.db_connect(None)

def test_db_disconnect(db_base):
    db_base.db_disconnect()

def test_get_list(db_base):
    with pytest.raises(DbException) as excinfo:
        db_base.get_list(None, None)
    assert str(excinfo.value).startswith(exception_message("Method 'get_list' not implemented"))
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

def test_get_one(db_base):
    with pytest.raises(DbException) as excinfo:
        db_base.get_one(None, None, None, None)
    assert str(excinfo.value).startswith(exception_message("Method 'get_one' not implemented"))
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

def test_create(db_base):
    with pytest.raises(DbException) as excinfo:
        db_base.create(None, None)
    assert str(excinfo.value).startswith(exception_message("Method 'create' not implemented"))
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

def test_del_list(db_base):
    with pytest.raises(DbException) as excinfo:
        db_base.del_list(None, None)
    assert str(excinfo.value).startswith(exception_message("Method 'del_list' not implemented"))
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

def test_del_one(db_base):
    with pytest.raises(DbException) as excinfo:
        db_base.del_one(None, None, None)
    assert str(excinfo.value).startswith(exception_message("Method 'del_one' not implemented"))
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND
