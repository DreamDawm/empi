import pytest
from app.core.logger import setup_logger, get_logger
from app.core.config import settings
from app.services.logging_service import ETLLoggingService


@pytest.mark.unit
def test_log_dir_config():
    """Test log directory configuration"""
    assert settings.LOG_DIR == "logs"
    assert settings.LOG_RETENTION_DAYS == 7


@pytest.mark.unit
def test_setup_logger_returns_logger():
    """Test setup_logger returns a Logger instance"""
    logger = setup_logger("test_setup")
    assert logger is not None
    assert logger.name == "test_setup"
    assert logger.level == 20  # logging.INFO = 20


@pytest.mark.unit
def test_setup_logger_creates_handlers():
    """Test setup_logger creates file and console handlers"""
    logger = setup_logger("test_handlers")
    assert len(logger.handlers) >= 2  # file + console


@pytest.mark.unit
def test_get_logger_returns_same_instance():
    """Test get_logger returns the same instance for same name"""
    logger1 = get_logger("test_same")
    logger2 = get_logger("test_same")
    assert logger1 is logger2


@pytest.mark.unit
def test_get_logger_different_names_different_instances():
    """Test get_logger returns different instances for different names"""
    logger1 = get_logger("test_diff_1")
    logger2 = get_logger("test_diff_2")
    assert logger1 is not logger2


@pytest.mark.unit
def test_logger_can_log():
    """Test logger can actually log messages without error"""
    logger = get_logger("test_log")
    # Should not raise any exception
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")


@pytest.mark.unit
def test_logging_service_singleton():
    """Test ETLLoggingService is a singleton"""
    svc1 = ETLLoggingService()
    svc2 = ETLLoggingService()
    assert svc1 is svc2


@pytest.mark.unit
def test_logging_service_info():
    """Test ETLLoggingService info logging"""
    service = ETLLoggingService()
    service.clear_queue()
    service.info("Test info message", patient_id="P001")
    assert not service._queue.empty()


@pytest.mark.unit
def test_logging_service_error():
    """Test ETLLoggingService error logging"""
    service = ETLLoggingService()
    service.clear_queue()
    service.error("Test error message", patient_id="P002")
    entry = service._queue.get_nowait()
    assert entry['level'] == 'ERROR'
    assert entry['patient_id'] == 'P002'


@pytest.mark.unit
def test_logging_service_warning():
    """Test ETLLoggingService warning logging"""
    service = ETLLoggingService()
    service.clear_queue()
    service.warning("Test warning message", patient_id="P003")
    entry = service._queue.get_nowait()
    assert entry['level'] == 'WARNING'
    assert entry['patient_id'] == 'P003'