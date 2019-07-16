from unittest.mock import Mock, call

import pyodbc
import pytest

from django_informixdb.base import DatabaseWrapper


CONNECTION_FAILED_ERROR = pyodbc.Error(
    "08004", "Attempt to connect to database server (<dbname>) failed. (-908) (SQLDriverConnect)"
)
READ_ERROR = pyodbc.Error(
    "HY000", "Read error occurred during connection attempt. (-27001) (SQLDriverConnect)"
)
AUTHENTICATION_ERROR = pyodbc.Error(
    "28000",
    "Incorrect password or user is not known on the database server (-951) (SQLDriverConnect)"
)


@pytest.fixture
def mock_autocommit_methods(mocker):
    mocker.patch.object(DatabaseWrapper, "get_autocommit", return_value=True, autospec=True)
    mocker.patch.object(DatabaseWrapper, "set_autocommit", autospec=True)


@pytest.fixture
def mock_is_usable(mocker):
    yield mocker.patch.object(DatabaseWrapper, "is_usable", return_value=False, autospec=True)


def test_DatabaseWrapper_get_new_connection_successfully_connects(mock_autocommit_methods):
    db = DatabaseWrapper({
        "ENGINE": "django_informixdb",
        "SERVER": "informix",
        "NAME": "sysmaster",
        "USER": "informix",
        "PASSWORD": "in4mix",
        "OPTIONS": {},
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": None,
        "TIME_ZONE": None,
    })
    assert db.connection is None
    db.connect()
    assert db.connection is not None
    assert db.is_usable() is True


def test_DatabaseWrapper_validate_connection_closes_connections_that_are_not_usable(
    mock_autocommit_methods, mock_is_usable
):
    mock_is_usable.return_value = False
    db = DatabaseWrapper({
        "ENGINE": "django_informixdb",
        "SERVER": "informix",
        "NAME": "sysmaster",
        "USER": "informix",
        "PASSWORD": "in4mix",
        "OPTIONS": {"VALIDATE_CONNECTION": True},
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": None,
        "TIME_ZONE": None,
    })
    db.connect()
    db.validate_connection()
    assert db.connection is None


def test_DatabaseWrapper_validate_connection_does_not_close_connection_if_not_enabled(
    mock_autocommit_methods, mock_is_usable
):
    mock_is_usable.return_value = False
    db = DatabaseWrapper({
        "ENGINE": "django_informixdb",
        "SERVER": "informix",
        "NAME": "sysmaster",
        "USER": "informix",
        "PASSWORD": "in4mix",
        "OPTIONS": {"VALIDATE_CONNECTION": False},
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": None,
        "TIME_ZONE": None,
    })
    db.connect()
    db.validate_connection()
    assert db.connection is not None


def test_DatabaseWrapper_validate_connection_handles_closed_connections(mock_autocommit_methods):
    db = DatabaseWrapper({
        "ENGINE": "django_informixdb",
        "SERVER": "informix",
        "NAME": "sysmaster",
        "USER": "informix",
        "PASSWORD": "in4mix",
        "OPTIONS": {"VALIDATE_CONNECTION": True},
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,  # this will make close_if_unusable_or_obsolete close the connection
        "TIME_ZONE": None,
    })
    db.connect()
    db.validate_connection()
    assert db.connection is None


def test_DatabaseWrapper_get_new_connection_calls_pyodbc_connect(mocker):
    mock_connect = mocker.patch("pyodbc.connect", autospec=True)
    db = DatabaseWrapper({
        "SERVER": "server1", "NAME": "db1", "USER": "user1", "PASSWORD": "password1",
        "OPTIONS": {"CONN_TIMEOUT": 120}
    })
    db.get_new_connection(db.get_connection_params())
    assert mock_connect.called is True
    connection_string = mock_connect.call_args[0][0]
    parts = connection_string.split(";")
    assert "Server=server1" in parts
    assert "Database=db1" in parts
    assert "Uid=user1" in parts
    assert "Pwd=password1" in parts
    assert mock_connect.call_args[1]['timeout'] == 120


def test_get_new_connection_doesnt_retry_by_default(mocker):
    mock_connect = mocker.patch("pyodbc.connect", autospec=True, side_effect=READ_ERROR)
    db = DatabaseWrapper({
        "SERVER": "server1", "NAME": "db1", "USER": "user1", "PASSWORD": "password1"
    })
    with pytest.raises(pyodbc.Error):
        db.get_new_connection(db.get_connection_params())
    assert mock_connect.call_count == 1


def test_get_new_connection_retries_up_to_MAX_ATTEMPTS(mocker):
    mock_sleep = mocker.patch("time.sleep", autospec=True)
    mock_connect = mocker.patch("pyodbc.connect", autospec=True, side_effect=READ_ERROR)
    db = DatabaseWrapper({
        "SERVER": "server1",
        "NAME": "db1",
        "USER": "user1",
        "PASSWORD": "password1",
        "CONNECTION_RETRY": {
            "MAX_ATTEMPTS": 3,
        },
    })
    with pytest.raises(pyodbc.Error):
        db.get_new_connection(db.get_connection_params())
    assert mock_connect.call_count == 3
    assert mock_sleep.call_count == 2


@pytest.mark.parametrize("error, expected_retries", [
    (CONNECTION_FAILED_ERROR, 1),
    (READ_ERROR, 1),
    (AUTHENTICATION_ERROR, 0),
    (pyodbc.Error("", "-27001"), 0),  # the error code must be surrounded by round brackets
])
def test_only_retries_certain_errors(mocker, error, expected_retries):
    mocker.patch("time.sleep", autospec=True)
    mock_connect = mocker.patch("pyodbc.connect", autospec=True, side_effect=error)
    db = DatabaseWrapper({
        "SERVER": "server1",
        "NAME": "db1",
        "USER": "user1",
        "PASSWORD": "password1",
        "CONNECTION_RETRY": {
            "MAX_ATTEMPTS": 2,
        },
    })
    with pytest.raises(pyodbc.Error):
        db.get_new_connection(db.get_connection_params())
    assert mock_connect.call_count == 1 + expected_retries  # attempts = 1 + retries


@pytest.mark.parametrize("error, expected_retries", [
    (CONNECTION_FAILED_ERROR, 0),
    (pyodbc.Error("", "(-12345)"), 1),
])
def test_errors_to_retry_can_be_overridden(mocker, error, expected_retries):
    mocker.patch("time.sleep", autospec=True)
    mock_connect = mocker.patch("pyodbc.connect", autospec=True, side_effect=error)
    db = DatabaseWrapper({
        "SERVER": "server1",
        "NAME": "db1",
        "USER": "user1",
        "PASSWORD": "password1",
        "CONNECTION_RETRY": {
            "MAX_ATTEMPTS": 2,
            "ERRORS": ["-12345"],
        },
    })
    with pytest.raises(pyodbc.Error):
        db.get_new_connection(db.get_connection_params())
    assert mock_connect.call_count == 1 + expected_retries


def test_get_new_connection_breaks_early_if_connection_succeeds(mocker):
    mock_sleep = mocker.patch("time.sleep", autospec=True)
    mock_connect = mocker.patch(
        "pyodbc.connect",
        autospec=True,
        side_effect=[READ_ERROR, Mock()],
    )
    db = DatabaseWrapper({
        "SERVER": "server1",
        "NAME": "db1",
        "USER": "user1",
        "PASSWORD": "password1",
        "CONNECTION_RETRY": {
            "MAX_ATTEMPTS": 3,
        },
    })
    db.get_new_connection(db.get_connection_params())
    assert mock_connect.call_count == 2
    assert mock_sleep.call_count == 1


def test_sleeps_between_connection_attempts(mocker):
    mock_uniform = mocker.patch(
        "random.uniform",
        autospec=True,
        side_effect=[1000, 2000, 3000, 4000, 5000],
    )
    mock_sleep = mocker.patch("time.sleep", autospec=True)
    mocker.patch("pyodbc.connect", autospec=True, side_effect=READ_ERROR)
    db = DatabaseWrapper({
        "SERVER": "server1",
        "NAME": "db1",
        "USER": "user1",
        "PASSWORD": "password1",
        "CONNECTION_RETRY": {
            "MAX_ATTEMPTS": 6,
            "WAIT_MIN": 15,
            "WAIT_MAX": 100,
            "WAIT_MULTIPLIER": 10,
            "WAIT_EXP_BASE": 2,
        },
    })
    with pytest.raises(pyodbc.Error):
        db.get_new_connection(db.get_connection_params())
    assert mock_uniform.call_args_list == [
        call(15, 15),
        call(15, 20),
        call(15, 40),
        call(15, 80),
        call(15, 100),
    ]
    assert mock_sleep.call_args_list == [call(1), call(2), call(3), call(4), call(5)]
