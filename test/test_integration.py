import django.db


def test_request_triggers_validate_connection(mocker, db, client):
    mock_validate_connection = mocker.patch.object(
        django.db.connection, "validate_connection", autospec=True
    )
    client.get("")
    assert mock_validate_connection.called is True
