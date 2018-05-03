import http
import logging
import pytest

from unittest.mock import MagicMock
from osm_common.dbbase import DbException
from osm_common.dbmemory import DbMemory

__author__ = 'Eduardo Sousa <eduardosousa@av.it.pt>'

@pytest.fixture
def db_memory():
    db = DbMemory()
    return db

@pytest.fixture
def db_memory_with_data():
    db = DbMemory()

    db.create("test", {"_id": 1, "data": 1})
    db.create("test", {"_id": 2, "data": 2})
    db.create("test", {"_id": 3, "data": 3})

    return db

def empty_exception_message():
    return 'database exception '

def get_one_exception_message(filter):
    return "database exception Not found entry with filter='{}'".format(filter)

def get_one_multiple_exception_message(filter):
    return "database exception Found more than one entry with filter='{}'".format(filter)

def del_one_exception_message(filter):
    return "database exception Not found entry with filter='{}'".format(filter)

def replace_exception_message(filter):
    return "database exception Not found entry with filter='{}'".format(filter)

def test_constructor():
    db = DbMemory()

    assert db.logger == logging.getLogger('db')
    assert len(db.db) == 0

def test_constructor_with_logger():
    logger_name = 'db_local'

    db = DbMemory(logger_name=logger_name)

    assert db.logger == logging.getLogger(logger_name)
    assert len(db.db) == 0

def test_db_connect():
    logger_name = 'db_local'
    config = {'logger_name': logger_name}

    db = DbMemory()
    db.db_connect(config)

    assert db.logger == logging.getLogger(logger_name)
    assert len(db.db) == 0

@pytest.mark.parametrize("table, filter", [
    ("test", {}),
    ("test", {"_id": 1}),
    ("test", {"data": 1}),
    ("test", {"_id": 1, "data": 1})])
def test_get_list_with_empty_db(db_memory, table, filter):
    result = db_memory.get_list(table, filter)

    assert len(result) == 0

@pytest.mark.parametrize("table, filter, expected_data", [
    ("test", {}, [{"_id": 1, "data": 1}, {"_id": 2, "data": 2}, {"_id": 3, "data": 3}]),
    ("test", {"_id": 1}, [{"_id": 1, "data": 1}]),
    ("test", {"data": 1}, [{"_id": 1, "data": 1}]),
    ("test", {"_id": 1, "data": 1}, [{"_id": 1, "data": 1}]),
    ("test", {"_id": 2}, [{"_id": 2, "data": 2}]),
    ("test", {"data": 2}, [{"_id": 2, "data": 2}]),
    ("test", {"_id": 2, "data": 2}, [{"_id": 2, "data": 2}]),
    ("test", {"_id": 4}, []),
    ("test", {"data": 4}, []),
    ("test", {"_id": 4, "data": 4}, []),
    ("test_table", {}, []),
    ("test_table", {"_id": 1}, []),
    ("test_table", {"data": 1}, []),
    ("test_table", {"_id": 1, "data": 1}, [])])
def test_get_list_with_non_empty_db(db_memory_with_data, table, filter, expected_data):
    result = db_memory_with_data.get_list(table, filter)

    assert len(result) == len(expected_data)
    for data in expected_data:
        assert data in result

def test_get_list_exception(db_memory_with_data):
    table = 'test'
    filter = {}

    db_memory_with_data._find = MagicMock(side_effect=Exception())

    with pytest.raises(DbException) as excinfo:
        db_memory_with_data.get_list(table, filter)
    assert str(excinfo.value) == empty_exception_message()
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("table, filter, expected_data", [
    ("test", {"_id": 1}, {"_id": 1, "data": 1}),
    ("test", {"_id": 2}, {"_id": 2, "data": 2}),
    ("test", {"_id": 3}, {"_id": 3, "data": 3}),
    ("test", {"data": 1}, {"_id": 1, "data": 1}),
    ("test", {"data": 2}, {"_id": 2, "data": 2}),
    ("test", {"data": 3}, {"_id": 3, "data": 3}),
    ("test", {"_id": 1, "data": 1}, {"_id": 1, "data": 1}),
    ("test", {"_id": 2, "data": 2}, {"_id": 2, "data": 2}),
    ("test", {"_id": 3, "data": 3}, {"_id": 3, "data": 3})])
def test_get_one(db_memory_with_data, table, filter, expected_data):
    result = db_memory_with_data.get_one(table, filter)

    assert result == expected_data
    assert len(db_memory_with_data.db) == 1
    assert table in db_memory_with_data.db
    assert len(db_memory_with_data.db[table]) == 3
    assert result in db_memory_with_data.db[table]

@pytest.mark.parametrize("table, filter, expected_data", [
    ("test", {}, {"_id": 1, "data": 1})])
def test_get_one_with_multiple_results(db_memory_with_data, table, filter, expected_data):
    result = db_memory_with_data.get_one(table, filter, fail_on_more=False)

    assert result == expected_data
    assert len(db_memory_with_data.db) == 1
    assert table in db_memory_with_data.db
    assert len(db_memory_with_data.db[table]) == 3
    assert result in db_memory_with_data.db[table]

def test_get_one_with_multiple_results_exception(db_memory_with_data):
    table = "test"
    filter = {}

    with pytest.raises(DbException) as excinfo:
        db_memory_with_data.get_one(table, filter)

    assert str(excinfo.value) == (empty_exception_message() + get_one_multiple_exception_message(filter))
#    assert excinfo.value.http_code == http.HTTPStatus.CONFLICT

@pytest.mark.parametrize("table, filter", [
    ("test", {"_id": 4}),
    ("test", {"data": 4}),
    ("test", {"_id": 4, "data": 4}),
    ("test_table", {"_id": 4}),
    ("test_table", {"data": 4}),
    ("test_table", {"_id": 4, "data": 4})])
def test_get_one_with_non_empty_db_exception(db_memory_with_data, table, filter):
    with pytest.raises(DbException) as excinfo:
        db_memory_with_data.get_one(table, filter)
    assert str(excinfo.value) == (empty_exception_message() + get_one_exception_message(filter))
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("table, filter", [
    ("test", {"_id": 4}),
    ("test", {"data": 4}),
    ("test", {"_id": 4, "data": 4}),
    ("test_table", {"_id": 4}),
    ("test_table", {"data": 4}),
    ("test_table", {"_id": 4, "data": 4})])
def test_get_one_with_non_empty_db_none(db_memory_with_data, table, filter):
    result = db_memory_with_data.get_one(table, filter, fail_on_empty=False)
    
    assert result == None

@pytest.mark.parametrize("table, filter", [
    ("test", {"_id": 4}),
    ("test", {"data": 4}),
    ("test", {"_id": 4, "data": 4}),
    ("test_table", {"_id": 4}),
    ("test_table", {"data": 4}),
    ("test_table", {"_id": 4, "data": 4})])
def test_get_one_with_empty_db_exception(db_memory, table, filter):
    with pytest.raises(DbException) as excinfo:
        db_memory.get_one(table, filter)
    assert str(excinfo.value) == (empty_exception_message() + get_one_exception_message(filter))
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("table, filter", [
    ("test", {"_id": 4}),
    ("test", {"data": 4}),
    ("test", {"_id": 4, "data": 4}),
    ("test_table", {"_id": 4}),
    ("test_table", {"data": 4}),
    ("test_table", {"_id": 4, "data": 4})])
def test_get_one_with_empty_db_none(db_memory, table, filter):
    result = db_memory.get_one(table, filter, fail_on_empty=False)
    
    assert result == None

def test_get_one_generic_exception(db_memory_with_data):
    table = 'test'
    filter = {}

    db_memory_with_data._find = MagicMock(side_effect=Exception())

    with pytest.raises(DbException) as excinfo:
        db_memory_with_data.get_one(table, filter)
    assert str(excinfo.value) == empty_exception_message()
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("table, filter, expected_data", [
    ("test", {}, []),
    ("test", {"_id": 1}, [{"_id": 2, "data": 2}, {"_id": 3, "data": 3}]), 
    ("test", {"_id": 2}, [{"_id": 1, "data": 1}, {"_id": 3, "data": 3}]), 
    ("test", {"_id": 1, "data": 1}, [{"_id": 2, "data": 2}, {"_id": 3, "data": 3}]),
    ("test", {"_id": 2, "data": 2}, [{"_id": 1, "data": 1}, {"_id": 3, "data": 3}])])
def test_del_list_with_non_empty_db(db_memory_with_data, table, filter, expected_data):
    result = db_memory_with_data.del_list(table, filter)

    assert result["deleted"] == (3 - len(expected_data))
    assert len(db_memory_with_data.db) == 1
    assert table in db_memory_with_data.db
    assert len(db_memory_with_data.db[table]) == len(expected_data)
    for data in expected_data:
        assert data in db_memory_with_data.db[table]

@pytest.mark.parametrize("table, filter", [
    ("test", {}),
    ("test", {"_id": 1}),
    ("test", {"_id": 2}),
    ("test", {"data": 1}),
    ("test", {"data": 2}),
    ("test", {"_id": 1, "data": 1}),
    ("test", {"_id": 2, "data": 2})])
def test_del_list_with_empty_db(db_memory, table, filter):
    result = db_memory.del_list(table, filter)
    assert result['deleted'] == 0

def test_del_list_generic_exception(db_memory_with_data):
    table = 'test'
    filter = {}

    db_memory_with_data._find = MagicMock(side_effect=Exception())

    with pytest.raises(DbException) as excinfo:
        db_memory_with_data.del_list(table, filter)
    assert str(excinfo.value) == empty_exception_message()
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("table, filter, data", [
    ("test", {}, {"_id": 1, "data": 1}),
    ("test", {"_id": 1}, {"_id": 1, "data": 1}),
    ("test", {"data": 1}, {"_id": 1, "data": 1}),
    ("test", {"_id": 1, "data": 1}, {"_id": 1, "data": 1}),
    ("test", {"_id": 2}, {"_id": 2, "data": 2}),
    ("test", {"data": 2}, {"_id": 2, "data": 2}),
    ("test", {"_id": 2, "data": 2}, {"_id": 2, "data": 2})])
def test_del_one(db_memory_with_data, table, filter, data):
    result = db_memory_with_data.del_one(table, filter)

    assert result == {"deleted": 1}
    assert len(db_memory_with_data.db) == 1
    assert table in db_memory_with_data.db
    assert len(db_memory_with_data.db[table]) == 2
    assert data not in db_memory_with_data.db[table]

@pytest.mark.parametrize("table, filter", [
    ("test", {}),
    ("test", {"_id": 1}),
    ("test", {"_id": 2}),
    ("test", {"data": 1}),
    ("test", {"data": 2}),
    ("test", {"_id": 1, "data": 1}),
    ("test", {"_id": 2, "data": 2}),
    ("test_table", {}),
    ("test_table", {"_id": 1}),
    ("test_table", {"_id": 2}),
    ("test_table", {"data": 1}),
    ("test_table", {"data": 2}),
    ("test_table", {"_id": 1, "data": 1}),
    ("test_table", {"_id": 2, "data": 2})])
def test_del_one_with_empty_db_exception(db_memory, table, filter):
    with pytest.raises(DbException) as excinfo:
        db_memory.del_one(table, filter)
    assert str(excinfo.value) == (empty_exception_message() + del_one_exception_message(filter))
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("table, filter", [
    ("test", {}),
    ("test", {"_id": 1}),
    ("test", {"_id": 2}),
    ("test", {"data": 1}),
    ("test", {"data": 2}),
    ("test", {"_id": 1, "data": 1}),
    ("test", {"_id": 2, "data": 2}),
    ("test_table", {}),
    ("test_table", {"_id": 1}),
    ("test_table", {"_id": 2}),
    ("test_table", {"data": 1}),
    ("test_table", {"data": 2}),
    ("test_table", {"_id": 1, "data": 1}),
    ("test_table", {"_id": 2, "data": 2})])
def test_del_one_with_empty_db_none(db_memory, table, filter):
    result = db_memory.del_one(table, filter, fail_on_empty=False)

    assert result == None

@pytest.mark.parametrize("table, filter", [
    ("test", {"_id": 4}),
    ("test", {"_id": 5}),
    ("test", {"data": 4}),
    ("test", {"data": 5}),
    ("test", {"_id": 1, "data": 2}),
    ("test", {"_id": 2, "data": 3}),
    ("test_table", {}),
    ("test_table", {"_id": 1}),
    ("test_table", {"_id": 2}),
    ("test_table", {"data": 1}),
    ("test_table", {"data": 2}),
    ("test_table", {"_id": 1, "data": 1}),
    ("test_table", {"_id": 2, "data": 2})])
def test_del_one_with_non_empty_db_exception(db_memory_with_data, table, filter):
    with pytest.raises(DbException) as excinfo:
        db_memory_with_data.del_one(table, filter)
    assert str(excinfo.value) == (empty_exception_message() + del_one_exception_message(filter))
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("table, filter", [
    ("test", {"_id": 4}),
    ("test", {"_id": 5}),
    ("test", {"data": 4}),
    ("test", {"data": 5}),
    ("test", {"_id": 1, "data": 2}),
    ("test", {"_id": 2, "data": 3}),
    ("test_table", {}),
    ("test_table", {"_id": 1}),
    ("test_table", {"_id": 2}),
    ("test_table", {"data": 1}),
    ("test_table", {"data": 2}),
    ("test_table", {"_id": 1, "data": 1}),
    ("test_table", {"_id": 2, "data": 2})])
def test_del_one_with_non_empty_db_none(db_memory_with_data, table, filter):
    result = db_memory_with_data.del_one(table, filter, fail_on_empty=False)

    assert result == None

@pytest.mark.parametrize("fail_on_empty", [
    (True),
    (False)])
def test_del_one_generic_exception(db_memory_with_data, fail_on_empty):
    table = 'test'
    filter = {}

    db_memory_with_data._find = MagicMock(side_effect=Exception())

    with pytest.raises(DbException) as excinfo:
        db_memory_with_data.del_one(table, filter, fail_on_empty=fail_on_empty)
    assert str(excinfo.value) == empty_exception_message()
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("table, filter, indata", [
    ("test", {}, {"_id": 1, "data": 42}),
    ("test", {}, {"_id": 3, "data": 42}),
    ("test", {"_id": 1}, {"_id": 3, "data": 42}),
    ("test", {"_id": 3}, {"_id": 3, "data": 42}),
    ("test", {"data": 1}, {"_id": 3, "data": 42}),
    ("test", {"data": 3}, {"_id": 3, "data": 42}),
    ("test", {"_id": 1, "data": 1}, {"_id": 3, "data": 42}),
    ("test", {"_id": 3, "data": 3}, {"_id": 3, "data": 42})])
def test_replace(db_memory_with_data, table, filter, indata):
    result = db_memory_with_data.replace(table, filter, indata)

    assert result == {"updated": 1}
    assert len(db_memory_with_data.db) == 1
    assert table in db_memory_with_data.db
    assert len(db_memory_with_data.db[table]) == 3
    assert indata in db_memory_with_data.db[table]

@pytest.mark.parametrize("table, filter, indata", [
    ("test", {}, {'_id': 1, 'data': 1}),
    ("test", {}, {'_id': 2, 'data': 1}),
    ("test", {}, {'_id': 1, 'data': 2}),
    ("test", {'_id': 1}, {'_id': 1, 'data': 1}),
    ("test", {'_id': 1, 'data': 1}, {'_id': 1, 'data': 1}),
    ("test_table", {}, {'_id': 1, 'data': 1}),
    ("test_table", {}, {'_id': 2, 'data': 1}),
    ("test_table", {}, {'_id': 1, 'data': 2}),
    ("test_table", {'_id': 1}, {'_id': 1, 'data': 1}),
    ("test_table", {'_id': 1, 'data': 1}, {'_id': 1, 'data': 1})])
def test_replace_without_data_exception(db_memory, table, filter, indata):
    with pytest.raises(DbException) as excinfo:
        db_memory.replace(table, filter, indata, fail_on_empty=True)
    assert str(excinfo.value) == (empty_exception_message() + replace_exception_message(filter))
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("table, filter, indata", [
    ("test", {}, {'_id': 1, 'data': 1}),
    ("test", {}, {'_id': 2, 'data': 1}),
    ("test", {}, {'_id': 1, 'data': 2}),
    ("test", {'_id': 1}, {'_id': 1, 'data': 1}),
    ("test", {'_id': 1, 'data': 1}, {'_id': 1, 'data': 1}),
    ("test_table", {}, {'_id': 1, 'data': 1}),
    ("test_table", {}, {'_id': 2, 'data': 1}),
    ("test_table", {}, {'_id': 1, 'data': 2}),
    ("test_table", {'_id': 1}, {'_id': 1, 'data': 1}),
    ("test_table", {'_id': 1, 'data': 1}, {'_id': 1, 'data': 1})])
def test_replace_without_data_none(db_memory, table, filter, indata):
    result = db_memory.replace(table, filter, indata, fail_on_empty=False)
    assert result == None

@pytest.mark.parametrize("table, filter, indata", [
    ("test_table", {}, {'_id': 1, 'data': 1}),
    ("test_table", {}, {'_id': 2, 'data': 1}),
    ("test_table", {}, {'_id': 1, 'data': 2}),
    ("test_table", {'_id': 1}, {'_id': 1, 'data': 1}),
    ("test_table", {'_id': 1, 'data': 1}, {'_id': 1, 'data': 1})])
def test_replace_with_data_exception(db_memory_with_data, table, filter, indata):
    with pytest.raises(DbException) as excinfo:
        db_memory_with_data.replace(table, filter, indata, fail_on_empty=True)
    assert str(excinfo.value) == (empty_exception_message() + replace_exception_message(filter))
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("table, filter, indata", [
    ("test_table", {}, {'_id': 1, 'data': 1}),
    ("test_table", {}, {'_id': 2, 'data': 1}),
    ("test_table", {}, {'_id': 1, 'data': 2}),
    ("test_table", {'_id': 1}, {'_id': 1, 'data': 1}),
    ("test_table", {'_id': 1, 'data': 1}, {'_id': 1, 'data': 1})])
def test_replace_with_data_none(db_memory_with_data, table, filter, indata):
    result = db_memory_with_data.replace(table, filter, indata, fail_on_empty=False)
    assert result == None

@pytest.mark.parametrize("fail_on_empty", [
    (True),
    (False)])
def test_replace_generic_exception(db_memory_with_data, fail_on_empty):
    table = 'test'
    filter = {}
    indata = {'_id': 1, 'data': 1}

    db_memory_with_data._find = MagicMock(side_effect=Exception())

    with pytest.raises(DbException) as excinfo:
        db_memory_with_data.replace(table, filter, indata, fail_on_empty=fail_on_empty)
    assert str(excinfo.value) == empty_exception_message()
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("table, id, data", [
    ("test", "1", {"data": 1}),
    ("test", "1", {"data": 2}),
    ("test", "2", {"data": 1}),
    ("test", "2", {"data": 2}),
    ("test_table", "1", {"data": 1}),
    ("test_table", "1", {"data": 2}),
    ("test_table", "2", {"data": 1}),
    ("test_table", "2", {"data": 2}),
    ("test", "1", {"data_1": 1, "data_2": 2}),
    ("test", "1", {"data_1": 2, "data_2": 1}),
    ("test", "2", {"data_1": 1, "data_2": 2}),
    ("test", "2", {"data_1": 2, "data_2": 1}),
    ("test_table", "1", {"data_1": 1, "data_2": 2}),
    ("test_table", "1", {"data_1": 2, "data_2": 1}),
    ("test_table", "2", {"data_1": 1, "data_2": 2}),
    ("test_table", "2", {"data_1": 2, "data_2": 1})])
def test_create_with_empty_db_with_id(db_memory, table, id, data):
    data_to_insert = data
    data_to_insert['_id'] = id

    returned_id = db_memory.create(table, data_to_insert)

    assert returned_id == id
    assert len(db_memory.db) == 1
    assert table in db_memory.db
    assert len(db_memory.db[table]) == 1
    assert data_to_insert in db_memory.db[table]

@pytest.mark.parametrize("table, id, data", [
    ("test", "4", {"data": 1}),
    ("test", "5", {"data": 2}),
    ("test", "4", {"data": 1}),
    ("test", "5", {"data": 2}),
    ("test_table", "4", {"data": 1}),
    ("test_table", "5", {"data": 2}),
    ("test_table", "4", {"data": 1}),
    ("test_table", "5", {"data": 2}),
    ("test", "4", {"data_1": 1, "data_2": 2}),
    ("test", "5", {"data_1": 2, "data_2": 1}),
    ("test", "4", {"data_1": 1, "data_2": 2}),
    ("test", "5", {"data_1": 2, "data_2": 1}),
    ("test_table", "4", {"data_1": 1, "data_2": 2}),
    ("test_table", "5", {"data_1": 2, "data_2": 1}),
    ("test_table", "4", {"data_1": 1, "data_2": 2}),
    ("test_table", "5", {"data_1": 2, "data_2": 1})])
def test_create_with_non_empty_db_with_id(db_memory_with_data, table, id, data):
    data_to_insert = data
    data_to_insert['_id'] = id

    returned_id = db_memory_with_data.create(table, data_to_insert)

    assert returned_id == id
    assert len(db_memory_with_data.db) == (1 if table == 'test' else 2)
    assert table in db_memory_with_data.db
    assert len(db_memory_with_data.db[table]) == (4 if table == 'test' else 1)
    assert data_to_insert in db_memory_with_data.db[table]

@pytest.mark.parametrize("table, data", [
    ("test", {"data": 1}),
    ("test", {"data": 2}),
    ("test", {"data": 1}),
    ("test", {"data": 2}),
    ("test_table", {"data": 1}),
    ("test_table", {"data": 2}),
    ("test_table", {"data": 1}),
    ("test_table", {"data": 2}),
    ("test", {"data_1": 1, "data_2": 2}),
    ("test", {"data_1": 2, "data_2": 1}),
    ("test", {"data_1": 1, "data_2": 2}),
    ("test", {"data_1": 2, "data_2": 1}),
    ("test_table", {"data_1": 1, "data_2": 2}),
    ("test_table", {"data_1": 2, "data_2": 1}),
    ("test_table", {"data_1": 1, "data_2": 2}),
    ("test_table", {"data_1": 2, "data_2": 1})])
def test_create_with_empty_db_without_id(db_memory, table, data):
    returned_id = db_memory.create(table, data)

    assert len(db_memory.db) == 1
    assert table in db_memory.db
    assert len(db_memory.db[table]) == 1

    data_inserted = data
    data_inserted['_id'] = returned_id

    assert data_inserted in db_memory.db[table]

@pytest.mark.parametrize("table, data", [
    ("test", {"data": 1}),
    ("test", {"data": 2}),
    ("test", {"data": 1}),
    ("test", {"data": 2}),
    ("test_table", {"data": 1}),
    ("test_table", {"data": 2}),
    ("test_table", {"data": 1}),
    ("test_table", {"data": 2}),
    ("test", {"data_1": 1, "data_2": 2}),
    ("test", {"data_1": 2, "data_2": 1}),
    ("test", {"data_1": 1, "data_2": 2}),
    ("test", {"data_1": 2, "data_2": 1}),
    ("test_table", {"data_1": 1, "data_2": 2}),
    ("test_table", {"data_1": 2, "data_2": 1}),
    ("test_table", {"data_1": 1, "data_2": 2}),
    ("test_table", {"data_1": 2, "data_2": 1})])
def test_create_with_non_empty_db_without_id(db_memory_with_data, table, data):
    returned_id = db_memory_with_data.create(table, data)

    assert len(db_memory_with_data.db) == (1 if table == 'test' else 2)
    assert table in db_memory_with_data.db
    assert len(db_memory_with_data.db[table]) == (4 if table == 'test' else 1)
    
    data_inserted = data
    data_inserted['_id'] = returned_id

    assert data_inserted in db_memory_with_data.db[table]

def test_create_with_exception(db_memory):
    table = "test"
    data = {"_id": 1, "data": 1}

    db_memory.db = MagicMock()
    db_memory.db.__contains__.side_effect = Exception()

    with pytest.raises(DbException) as excinfo:
        db_memory.create(table, data)
    assert str(excinfo.value) == empty_exception_message()
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND
