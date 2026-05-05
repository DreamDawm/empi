from sqlalchemy import Column, BigInteger, String, DateTime, JSON
from sqlalchemy.sql import func
from app.models.base import Base

class EmpiConfig(Base):
    __tablename__ = 'empi_config'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    config_key = Column(String(100), nullable=False, unique=True)
    config_value = Column(JSON, nullable=False)
    description = Column(String(500), nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
