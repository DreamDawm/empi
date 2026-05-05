import pytest
from unittest.mock import MagicMock, patch


def test_is_processed_uses_redis_cache():
    """Test that _is_processed checks Redis cache before database"""
    from app.services.etl import ETLScheduler

    scheduler = ETLScheduler()

    # Mock Redis to return cached patient ID
    with patch.object(scheduler.redis_client, 'sismember', return_value=True) as mock_sismember:
        with patch.object(scheduler, '_is_processed_db') as mock_db:
            result = scheduler._is_processed(None, 'patient_123')

    assert result is True
    assert mock_sismember.called
    assert not mock_db.called  # Should NOT hit database


def test_is_processed_falls_back_to_db():
    """Test that _is_processed falls back to database on cache miss"""
    from app.services.etl import ETLScheduler

    scheduler = ETLScheduler()

    with patch.object(scheduler.redis_client, 'sismember', return_value=False):
        with patch.object(scheduler, '_is_processed_db', return_value=True) as mock_db:
            result = scheduler._is_processed(None, 'patient_123')

    assert result is True
    assert mock_db.called