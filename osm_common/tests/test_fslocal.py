import io
import logging
import http
import os
import pytest
import tarfile
import tempfile
import uuid
import shutil

from osm_common.fsbase import FsException
from osm_common.fslocal import FsLocal

__author__ = "Eduardo Sousa <eduardosousa@av.it.pt>"

def valid_path():
    return tempfile.gettempdir() + '/'

def invalid_path():
    return '/#tweeter/'

@pytest.fixture
def fs_local():
    fs = FsLocal()
    fs.fs_connect({'path': valid_path()})

    return fs

def fs_connect_exception_message(path):
    return "storage exception Invalid configuration param at '[storage]': path '{}' does not exist".format(path)

def file_open_file_not_found_exception(storage):
    f = storage if isinstance(storage, str) else '/'.join(storage)
    return "storage exception File {} does not exist".format(f)

def file_open_io_exception(storage):
    f = storage if isinstance(storage, str) else '/'.join(storage)
    return "storage exception File {} cannot be opened".format(f)

def dir_ls_not_a_directory_exception(storage):
    f = storage if isinstance(storage, str) else '/'.join(storage)
    return "storage exception File {} does not exist".format(f)

def dir_ls_io_exception(storage):
    f = storage if isinstance(storage, str) else '/'.join(storage)
    return "storage exception File {} cannot be opened".format(f)

def file_delete_exception_message(storage):
    return "storage exception File {} does not exist".format(storage)

def test_constructor_without_logger():
    fs = FsLocal()

    assert fs.logger == logging.getLogger('fs')
    assert fs.path is None

def test_constructor_with_logger():
    logger_name = 'fs_local'

    fs = FsLocal(logger_name=logger_name)

    assert fs.logger == logging.getLogger(logger_name)
    assert fs.path is None

@pytest.mark.parametrize("config, exp_logger, exp_path", [
    ({'logger_name': 'fs_local', 'path': valid_path()}, 'fs_local', valid_path()),
    ({'logger_name': 'fs_local', 'path': valid_path()[:-1]}, 'fs_local', valid_path()),
    ({'path': valid_path()}, 'fs', valid_path()),
    ({'path': valid_path()[:-1]}, 'fs', valid_path())])
def test_fs_connect_with_valid_config(config, exp_logger, exp_path):
    fs = FsLocal()
    fs.fs_connect(config)

    assert fs.logger == logging.getLogger(exp_logger)
    assert fs.path == exp_path

@pytest.mark.parametrize("config, exp_exception_message", [
    ({'logger_name': 'fs_local', 'path': invalid_path()}, fs_connect_exception_message(invalid_path())),
    ({'logger_name': 'fs_local', 'path': invalid_path()[:-1]}, fs_connect_exception_message(invalid_path()[:-1])),
    ({'path': invalid_path()}, fs_connect_exception_message(invalid_path())),
    ({'path': invalid_path()[:-1]}, fs_connect_exception_message(invalid_path()[:-1]))])
def test_fs_connect_with_invalid_path(config, exp_exception_message):
    fs = FsLocal()
    
    with pytest.raises(FsException) as excinfo:
        fs.fs_connect(config)
    assert str(excinfo.value) == exp_exception_message

def test_mkdir_with_valid_path(fs_local):
    folder_name = str(uuid.uuid4())
    folder_path = valid_path() + folder_name

    fs_local.mkdir(folder_name)

    assert os.path.exists(folder_path)

    os.rmdir(folder_path)

def test_mkdir_with_exception(fs_local):
    folder_name = str(uuid.uuid4())
    folder_path = valid_path() + folder_name
    os.mkdir(folder_path)

    with pytest.raises(FsException) as excinfo:
        fs_local.mkdir(folder_name)
    assert excinfo.value.http_code == http.HTTPStatus.INTERNAL_SERVER_ERROR

    os.rmdir(folder_path)

@pytest.mark.parametrize("storage, mode, expected", [
    (str(uuid.uuid4()), 'file', False),
    ([str(uuid.uuid4())], 'file', False),
    (str(uuid.uuid4()), 'dir', False),
    ([str(uuid.uuid4())], 'dir', False)])
def test_file_exists_returns_false(fs_local, storage, mode, expected):
    assert fs_local.file_exists(storage, mode) == expected

@pytest.mark.parametrize("storage, mode, expected", [
    (str(uuid.uuid4()), 'file', True),
    ([str(uuid.uuid4())], 'file', True),
    (str(uuid.uuid4()), 'dir', True),
    ([str(uuid.uuid4())], 'dir', True)])
def test_file_exists_returns_true(fs_local, storage, mode, expected):
    path = valid_path() + storage if isinstance(storage, str) else valid_path() + storage[0]

    if mode == 'file':
        os.mknod(path)
    elif mode == 'dir':
        os.mkdir(path)

    assert fs_local.file_exists(storage, mode) == expected

    if mode == 'file':
        os.remove(path)
    elif mode == 'dir':
        os.rmdir(path)

@pytest.mark.parametrize("storage, mode", [
    (str(uuid.uuid4()), 'file'),
    ([str(uuid.uuid4())], 'file'),
    (str(uuid.uuid4()), 'dir'),
    ([str(uuid.uuid4())], 'dir')])
def test_file_size(fs_local, storage, mode):
    path = valid_path() + storage if isinstance(storage, str) else valid_path() + storage[0]

    if mode == 'file':
        os.mknod(path)
    elif mode == 'dir':
        os.mkdir(path)

    size = os.path.getsize(path)

    assert fs_local.file_size(storage) == size

    if mode == 'file':
        os.remove(path)
    elif mode == 'dir':
        os.rmdir(path)

@pytest.mark.parametrize("files, path", [
    (['foo', 'bar', 'foobar'], str(uuid.uuid4())),
    (['foo', 'bar', 'foobar'], [str(uuid.uuid4())])])
def test_file_extract(fs_local, files, path):
    for f in files:
        os.mknod(valid_path() + f)
    
    tar_path = valid_path() + str(uuid.uuid4()) + '.tar'
    with tarfile.open(tar_path, 'w') as tar:
        for f in files:
            tar.add(valid_path() + f, arcname=f)
    
    with tarfile.open(tar_path, 'r') as tar:
        fs_local.file_extract(tar, path)
    
    extracted_path = valid_path() + (path if isinstance(path, str) else '/'.join(path))
    ls_dir = os.listdir(extracted_path)

    assert len(ls_dir) == len(files)
    for f in files:
        assert f in ls_dir
    
    os.remove(tar_path)

    for f in files:
        os.remove(valid_path() + f)

    shutil.rmtree(extracted_path)

@pytest.mark.parametrize("storage, mode", [
    (str(uuid.uuid4()), 'r'),
    (str(uuid.uuid4()), 'w'),
    (str(uuid.uuid4()), 'a'),
    (str(uuid.uuid4()), 'rb'),
    (str(uuid.uuid4()), 'wb'),
    (str(uuid.uuid4()), 'ab'),
    ([str(uuid.uuid4())], 'r'),
    ([str(uuid.uuid4())], 'w'),
    ([str(uuid.uuid4())], 'a'),
    ([str(uuid.uuid4())], 'rb'),
    ([str(uuid.uuid4())], 'wb'),
    ([str(uuid.uuid4())], 'ab')])
def test_file_open(fs_local, storage, mode):
    path = valid_path() + storage if isinstance(storage, str) else valid_path() + storage[0]

    os.mknod(path)

    file_obj = fs_local.file_open(storage, mode)

    assert isinstance(file_obj, io.IOBase)
    assert file_obj.closed == False

    os.remove(path)

@pytest.mark.parametrize("storage, mode", [
    (str(uuid.uuid4()), 'r'),
    (str(uuid.uuid4()), 'rb'),
    ([str(uuid.uuid4())], 'r'),
    ([str(uuid.uuid4())], 'rb')])
def test_file_open_file_not_found_exception(fs_local, storage, mode):
    with pytest.raises(FsException) as excinfo:
        fs_local.file_open(storage, mode)
    assert str(excinfo.value) == file_open_file_not_found_exception(storage)
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("storage, mode", [
    (str(uuid.uuid4()), 'r'),
    (str(uuid.uuid4()), 'w'),
    (str(uuid.uuid4()), 'a'),
    (str(uuid.uuid4()), 'rb'),
    (str(uuid.uuid4()), 'wb'),
    (str(uuid.uuid4()), 'ab'),
    ([str(uuid.uuid4())], 'r'),
    ([str(uuid.uuid4())], 'w'),
    ([str(uuid.uuid4())], 'a'),
    ([str(uuid.uuid4())], 'rb'),
    ([str(uuid.uuid4())], 'wb'),
    ([str(uuid.uuid4())], 'ab')])
def test_file_open_io_error(fs_local, storage, mode):
    path = valid_path() + storage if isinstance(storage, str) else valid_path() + storage[0]

    os.mknod(path)
    os.chmod(path, 0)

    with pytest.raises(FsException) as excinfo:
        fs_local.file_open(storage, mode)
    assert str(excinfo.value) == file_open_io_exception(storage)
    assert excinfo.value.http_code == http.HTTPStatus.BAD_REQUEST

    os.remove(path)

@pytest.mark.parametrize("storage, with_files", [
    (str(uuid.uuid4()), True),
    (str(uuid.uuid4()), False),
    ([str(uuid.uuid4())], True),
    ([str(uuid.uuid4())], False)])
def test_dir_ls(fs_local, storage, with_files):
    path = valid_path() + storage if isinstance(storage, str) else valid_path() + storage[0]

    os.mkdir(path)

    if with_files == True:
        file_name = str(uuid.uuid4())
        file_path = path + '/' + file_name
        os.mknod(file_path)
    
    result = fs_local.dir_ls(storage)

    if with_files == True:
        assert len(result) == 1
        assert result[0] == file_name
    else:
        assert len(result) == 0
    
    shutil.rmtree(path)

@pytest.mark.parametrize("storage", [
    (str(uuid.uuid4())),
    ([str(uuid.uuid4())])])
def test_dir_ls_with_not_a_directory_error(fs_local, storage):
    path = valid_path() + storage if isinstance(storage, str) else valid_path() + storage[0]

    os.mknod(path)

    with pytest.raises(FsException) as excinfo:
        fs_local.dir_ls(storage)
    assert str(excinfo.value) == dir_ls_not_a_directory_exception(storage)
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

    os.remove(path)

@pytest.mark.parametrize("storage", [
    (str(uuid.uuid4())),
    ([str(uuid.uuid4())])])
def test_dir_ls_with_io_error(fs_local, storage):
    path = valid_path() + storage if isinstance(storage, str) else valid_path() + storage[0]

    os.mkdir(path)
    os.chmod(path, 0)

    with pytest.raises(FsException) as excinfo:
        fs_local.dir_ls(storage)
    assert str(excinfo.value) == dir_ls_io_exception(storage)
    assert excinfo.value.http_code == http.HTTPStatus.BAD_REQUEST

    os.rmdir(path)

@pytest.mark.parametrize("storage, with_files, ignore_non_exist", [
    (str(uuid.uuid4()), True, True),
    (str(uuid.uuid4()), False, True),
    (str(uuid.uuid4()), True, False),
    (str(uuid.uuid4()), False, False),
    ([str(uuid.uuid4())], True, True),
    ([str(uuid.uuid4())], False, True),
    ([str(uuid.uuid4())], True, False),
    ([str(uuid.uuid4())], False, False)])
def test_file_delete_with_dir(fs_local, storage, with_files, ignore_non_exist):
    path = valid_path() + storage if isinstance(storage, str) else valid_path() + storage[0]

    os.mkdir(path)

    if with_files == True:
        file_path = path + '/' + str(uuid.uuid4())
        os.mknod(file_path)

    fs_local.file_delete(storage, ignore_non_exist)

    assert os.path.exists(path) == False

@pytest.mark.parametrize("storage", [
    (str(uuid.uuid4())),
    ([str(uuid.uuid4())])])
def test_file_delete_expect_exception(fs_local, storage):
    with pytest.raises(FsException) as excinfo:
        fs_local.file_delete(storage)
    assert str(excinfo.value) == file_delete_exception_message(storage)
    assert excinfo.value.http_code == http.HTTPStatus.NOT_FOUND

@pytest.mark.parametrize("storage", [
    (str(uuid.uuid4())),
    ([str(uuid.uuid4())])])
def test_file_delete_no_exception(fs_local, storage):
    path = valid_path() + storage if isinstance(storage, str) else valid_path() + storage[0]

    fs_local.file_delete(storage, ignore_non_exist=True)

    assert os.path.exists(path) == False
