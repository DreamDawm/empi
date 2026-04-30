from sqlalchemy import Column, BigInteger, String, DateTime, Numeric, JSON, Index
from sqlalchemy.sql import func
from app.models.base import Base

class EmpiMaster(Base):
    __tablename__ = 'empi_master'

    id = Column(BigInteger, primary_key=True, comment='主键ID（雪花算法）')
    patient_id = Column(String(50), nullable=False, unique=True, comment='源系统患者ID')
    patient_name = Column(String(100), nullable=False, comment='患者姓名')
    master_id = Column(BigInteger, nullable=False, unique=True, comment='主索引ID（雪花算法）')
    status = Column(String(20), nullable=False, default='NORMAL', comment='状态：NORMAL/MERGED')
    merged_to_master_id = Column(BigInteger, nullable=True, comment='合并到的主索引ID')
    inverted_index = Column(JSON, nullable=True, comment='倒排索引数据')
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_master_id', 'master_id'),
    )
