from unittest.mock import Mock, call
from datetime import timedelta

import pyodbc
import pytest
from freezegun import freeze_time

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
def db_config():
    return {
        "ENGINE": "django_informixdb",
        "SERVER": "informix",
        "NAME": "sysmaster",
        "USER": "informix",
        "PASSWORD": "in4mix",
        "OPTIONS": {},
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": None,
        "TIME_ZONE": None,
    }


@pytest.fixture
def mock_autocommit_methods(mocker):
    mocker.patch.object(DatabaseWrapper, "get_autocommit", return_value=True, autospec=True)
    mocker.patch.object(DatabaseWrapper, "set_autocommit", autospec=True)


@pytest.fixture
def mock_is_usable(mocker):
    yield mocker.patch.object(DatabaseWrapper, "is_usable", return_value=True, autospec=True)


@pytest.fixture
def mock_connect(mocker):
    yield mocker.patch("pyodbc.connect", autospec=True)


@pytest.fixture
def mock_connection(mock_connect):
    yield mock_connect.return_value


@pytest.fixture
def mock_sleep(mocker):
    yield mocker.patch("time.sleep", autospec=True)


def test_DatabaseWrapper_connect_successfully_connects(mock_autocommit_methods, db_config):
    db = DatabaseWrapper(db_config)
    assert db.connection is None
    db.connect()
    assert db.connection is not None
    assert db.is_usable() is True


def test_DatabaseWrapper_validate_connection_closes_connections_that_are_not_usable(
    mock_autocommit_methods, mock_is_usable, db_config
):
    mock_is_usable.return_value = False
    db = DatabaseWrapper({
        **db_config,
        "OPTIONS": {"VALIDATE_CONNECTION": True, "VALIDATION_INTERVAL": 0},
    })
    db.connect()
    db.validate_connection()
    assert db.connection is None


def test_DatabaseWrapper_validate_connection_does_not_close_connection_if_not_enabled(
    mock_autocommit_methods, mock_is_usable, db_config
):
    mock_is_usable.return_value = False
    db = DatabaseWrapper({
        **db_config,
        "OPTIONS": {"VALIDATE_CONNECTION": False, "VALIDATION_INTERVAL": 0},
    })
    db.connect()
    db.validate_connection()
    assert db.connection is not None


def test_DatabaseWrapper_validate_connection_handles_closed_connections(
    mock_autocommit_methods, db_config
):
    db = DatabaseWrapper({
        **db_config,
        "OPTIONS": {"VALIDATE_CONNECTION": True, "VALIDATION_INTERVAL": 0},
        "CONN_MAX_AGE": 0,  # this will make close_if_unusable_or_obsolete close the connection
    })
    db.connect()
    db.validate_connection()
    assert db.connection is None


def test_connection_is_not_revalidated_within_validation_interval(
    mock_is_usable, mock_autocommit_methods, db_config
):
    with freeze_time() as frozen_time:
        db = DatabaseWrapper({
            **db_config,
            "OPTIONS": {
                "VALIDATE_CONNECTION": True,
                "VALIDATION_INTERVAL": 10,
            },
        })
        db.connect()

        frozen_time.tick(delta=timedelta(seconds=10))
        db.validate_connection()
        assert mock_is_usable.called is True

        mock_is_usable.reset_mock()

        frozen_time.tick(delta=timedelta(seconds=5))
        db.validate_connection()
        assert mock_is_usable.called is False

        frozen_time.tick(delta=timedelta(seconds=5))
        db.validate_connection()
        assert mock_is_usable.called is True


def test_DatabaseWrapper_is_usable(mocker, mock_autocommit_methods, db_config):
    mocker.patch("pyodbc.connect", autospec=True)
    db = DatabaseWrapper(db_config)
    db.connect()
    assert db.is_usable() is True


def test_DatabaseWrapper_is_usable_returns_false_if_creating_cursor_fails(
    caplog, mocker, mock_connection, mock_autocommit_methods, db_config
):
    mock_connection.cursor.side_effect = pyodbc.Error("", "error message 1")
    db = DatabaseWrapper(db_config)
    db.connect()
    assert db.is_usable() is False
    assert "error message 1" in caplog.text


def test_DatabaseWrapper_is_usable_returns_false_if_execute_raises_error(
    caplog, mocker, mock_connection, mock_autocommit_methods, db_config
):
    mock_connection.cursor.return_value.execute.side_effect = pyodbc.Error("", "error message 1")
    db = DatabaseWrapper(db_config)
    db.connect()
    assert db.is_usable() is False
    assert "error message 1" in caplog.text


def test_DatabaseWrapper_is_usable_returns_false_if_closing_cursor_raises_error(
    caplog, mocker, mock_connection, mock_autocommit_methods, db_config
):
    mock_connection.cursor.return_value.close.side_effect = pyodbc.Error("", "error message 1")
    db = DatabaseWrapper(db_config)
    db.connect()
    assert db.is_usable() is False
    assert "error message 1" in caplog.text


def test_DatabaseWrapper_get_new_connection_calls_pyodbc_connect(mock_connect, db_config):
    db = DatabaseWrapper({
        "SERVER": "server1",
        "NAME": "db1",
        "USER": "user1",
        "PASSWORD": "password1",
        "OPTIONS": {"CONN_TIMEOUT": 120},
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


def test_get_new_connection_doesnt_retry_by_default(mock_connect, db_config):
    mock_connect.side_effect = READ_ERROR
    db = DatabaseWrapper(db_config)
    with pytest.raises(pyodbc.Error):
        db.get_new_connection(db.get_connection_params())
    assert mock_connect.call_count == 1


def test_get_new_connection_retries_up_to_MAX_ATTEMPTS(mock_sleep, mock_connect, db_config):
    mock_connect.side_effect = READ_ERROR
    db = DatabaseWrapper({**db_config, "CONNECTION_RETRY": {"MAX_ATTEMPTS": 3}})
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
def test_only_retries_certain_errors(mock_sleep, mock_connect, db_config, error, expected_retries):
    mock_connect.side_effect = error
    db = DatabaseWrapper({**db_config, "CONNECTION_RETRY": {"MAX_ATTEMPTS": 2}})
    with pytest.raises(pyodbc.Error):
        db.get_new_connection(db.get_connection_params())
    assert mock_connect.call_count == 1 + expected_retries  # attempts = 1 + retries


@pytest.mark.parametrize("error, expected_retries", [
    (CONNECTION_FAILED_ERROR, 0),
    (pyodbc.Error("", "(-12345)"), 1),
])
def test_errors_to_retry_can_be_overridden(mock_sleep, mock_connect, db_config, error, expected_retries):
    mock_connect.side_effect = error
    db = DatabaseWrapper({
        **db_config,
        "CONNECTION_RETRY": {
            "MAX_ATTEMPTS": 2,
            "ERRORS": ["-12345"],
        },
    })
    with pytest.raises(pyodbc.Error):
        db.get_new_connection(db.get_connection_params())
    assert mock_connect.call_count == 1 + expected_retries


def test_get_new_connection_breaks_early_if_connection_succeeds(
    mock_sleep, mock_connect, db_config
):
    mock_connect.side_effect = [READ_ERROR, Mock()]
    db = DatabaseWrapper({**db_config, "CONNECTION_RETRY": {"MAX_ATTEMPTS": 3}})
    db.get_new_connection(db.get_connection_params())
    assert mock_connect.call_count == 2
    assert mock_sleep.call_count == 1


def test_sleeps_between_connection_attempts(mocker, mock_sleep, mock_connect, db_config):
    mock_uniform = mocker.patch(
        "random.uniform",
        autospec=True,
        side_effect=[1000, 2000, 3000, 4000, 5000],
    )
    mock_connect.side_effect = READ_ERROR
    db = DatabaseWrapper({
        **db_config,
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
