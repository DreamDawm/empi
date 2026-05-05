import pytest
from unittest.mock import MagicMock, patch


def test_warm_cache_loads_existing_patients():
    """Test that warm_cache loads existing processed patients from DB"""
    from app.services.etl import ETLScheduler

    scheduler = ETLScheduler()
    mock_db = MagicMock()
    mock_db.query.return_value.distinct.return_value.all.return_value = [
        MagicMock(patient_id='p1'),
        MagicMock(patient_id='p2'),
    ]

    with patch.object(scheduler.redis_client, 'delete') as mock_delete:
        with patch.object(scheduler.redis_client, 'sadd') as mock_sadd:
            scheduler.warm_processed_cache(mock_db)

    assert mock_delete.called  # Should clear existing key first
    # sadd is called once with all patient IDs (variadic)
    mock_sadd.assert_called_once()
    call_args = mock_sadd.call_args[0]
    assert call_args[0] == scheduler._processed_patients_key
    assert set(call_args[1:]) == {'p1', 'p2'}  # All patient IDs passed


def test_warm_cache_does_nothing_when_no_patients():
    """Test that warm_cache does nothing when no processed patients exist"""
    from app.services.etl import ETLScheduler

    scheduler = ETLScheduler()
    mock_db = MagicMock()
    mock_db.query.return_value.distinct.return_value.all.return_value = []

    with patch.object(scheduler.redis_client, 'delete') as mock_delete:
        with patch.object(scheduler.redis_client, 'sadd') as mock_sadd:
            scheduler.warm_processed_cache(mock_db)

    assert not mock_delete.called
    assert not mock_sadd.called