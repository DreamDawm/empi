import pytest
from unittest.mock import MagicMock, patch


def test_get_last_id_reads_from_redis():
    """Test that _get_last_id reads the auto-increment id cursor from Redis and converts to int"""
    from app.services.etl import ETLScheduler

    scheduler = ETLScheduler()

    with patch.object(scheduler.redis_client, 'get', return_value='42') as mock_get:
        result = scheduler._get_last_id()

    assert result == 42
    assert isinstance(result, int)
    mock_get.assert_called_once_with('etl:last_id')


def test_get_last_id_returns_none_when_empty():
    """Test that _get_last_id returns None when Redis has no cursor"""
    from app.services.etl import ETLScheduler

    scheduler = ETLScheduler()

    with patch.object(scheduler.redis_client, 'get', return_value=None):
        result = scheduler._get_last_id()

    assert result is None


def test_set_last_id_writes_to_redis():
    """Test that _set_last_id writes the auto-increment id cursor to Redis"""
    from app.services.etl import ETLScheduler

    scheduler = ETLScheduler()

    with patch.object(scheduler.redis_client, 'set') as mock_set:
        scheduler._set_last_id(100)

    mock_set.assert_called_once_with('etl:last_id', 100)


def test_fetch_patients_uses_id_cursor():
    """Test that _fetch_patients uses auto-increment id for cursor pagination"""
    from app.services.etl import ETLScheduler

    scheduler = ETLScheduler()
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.keys.return_value = ['id', 'patient_id', 'person_name']
    mock_result.fetchall.return_value = [
        (1, 'p001', 'Alice'),
        (2, 'p002', 'Bob'),
    ]
    mock_db.execute.return_value = mock_result

    # With cursor
    patients = scheduler._fetch_patients(mock_db, 5, 100)
    call_args = mock_db.execute.call_args
    bound_clause = call_args[0][0]
    sql = bound_clause.text
    assert 'id > :last_id' in sql
    assert 'ORDER BY id' in sql
    assert bound_clause.compile().params['last_id'] == 5
    assert bound_clause.compile().params['limit'] == 100

    # Without cursor (first run)
    mock_db.reset_mock()
    patients = scheduler._fetch_patients(mock_db, None, 100)
    call_args = mock_db.execute.call_args
    bound_clause = call_args[0][0]
    sql = bound_clause.text
    assert 'WHERE' not in sql
    assert 'ORDER BY id' in sql


def test_fetch_patients_returns_id_in_result():
    """Test that fetched patient dicts include the auto-increment id"""
    from app.services.etl import ETLScheduler

    scheduler = ETLScheduler()
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.keys.return_value = ['id', 'patient_id', 'person_name']
    mock_result.fetchall.return_value = [
        (10, 'p001', 'Alice'),
    ]
    mock_db.execute.return_value = mock_result

    patients = scheduler._fetch_patients(mock_db, None, 100)
    assert patients[0]['id'] == 10
    assert patients[0]['patient_id'] == 'p001'


def test_poll_and_process_updates_id_cursor():
    """Test that poll_and_process saves the last auto-increment id as cursor"""
    from app.services.etl import ETLScheduler

    scheduler = ETLScheduler()
    mock_db = MagicMock()

    patients = [
        {'id': 10, 'patient_id': 'p001', 'person_name': 'Alice', 'gender': 'M'},
        {'id': 20, 'patient_id': 'p002', 'person_name': 'Bob', 'gender': 'F'},
    ]

    with patch.object(scheduler, '_fetch_patients', return_value=patients):
        with patch.object(scheduler, '_get_last_id', return_value=None):
            with patch.object(scheduler, '_set_last_id') as mock_set:
                with patch.object(scheduler, '_is_processed', return_value=True):
                    with patch.object(scheduler, '_get_weights', return_value={}):
                        with patch.object(scheduler, '_get_threshold', return_value=85.0):
                            scheduler.poll_and_process(mock_db)

    mock_set.assert_called_once_with(20)
