import pytest
from unittest.mock import MagicMock, patch


def test_warm_cache_loads_existing_patients():
    """Test that warm_cache loads existing processed patients from DB using atomic rename"""
    from app.services.etl import ETLScheduler

    scheduler = ETLScheduler()
    mock_db = MagicMock()
    mock_db.query.return_value.distinct.return_value.all.return_value = [
        MagicMock(patient_id='p1'),
        MagicMock(patient_id='p2'),
    ]

    mock_pipe = MagicMock()
    with patch.object(scheduler.redis_client, 'pipeline', return_value=mock_pipe) as mock_pipeline:
        scheduler.warm_processed_cache(mock_db)

    # Verify pipeline is used with atomic rename pattern
    mock_pipeline.assert_called_once()
    assert mock_pipe.delete.called
    assert mock_pipe.sadd.called
    assert mock_pipe.rename.called
    # Verify rename was called with new_key -> processed_patients_key
    rename_call = mock_pipe.rename.call_args
    assert rename_call[0][0] == f'{scheduler._processed_patients_key}:new'
    assert rename_call[0][1] == scheduler._processed_patients_key


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