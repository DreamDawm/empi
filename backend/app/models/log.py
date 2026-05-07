from sqlalchemy import Column, BigInteger, String, DateTime, Numeric, JSON, Index
from sqlalchemy.sql import func
from app.models.base import Base

class EmpiMergeLog(Base):
    __tablename__ = 'empi_merge_log'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    person_id_a = Column(String(50), nullable=False)
    person_id_b = Column(String(50), nullable=False)
    master_id = Column(BigInteger, nullable=False)
    merge_type = Column(String(20), nullable=False, comment='AUTO/MANUAL/DIRECT/NAME_MATCH')
    similarity_score = Column(Numeric(5,2), nullable=False)
    merge_time = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index('idx_ml_master_id', 'master_id'),
        Index('idx_ml_person_a', 'person_id_a'),
        Index('idx_ml_person_b', 'person_id_b'),
    )

class EmpiPendingReview(Base):
    __tablename__ = 'empi_pending_review'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    person_id_a = Column(String(50), nullable=False)
    person_id_b = Column(String(50), nullable=False)
    similarity_score = Column(Numeric(5,2), nullable=False)
    similarity_details = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default='PENDING')
    resolution_type = Column(String(20), nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index('idx_pr_status', 'status'),
        Index('idx_pr_create_time', 'create_time'),
    )

class EmpiProcessLog(Base):
    __tablename__ = 'empi_process_log'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    patient_id = Column(String(50), nullable=False)
    process_type = Column(String(20), nullable=False, comment='CLEAN/CALCULATE/MERGE/REVIEW')
    details = Column(JSON, nullable=False)
    process_time = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index('idx_pl_patient_id', 'patient_id'),
        Index('idx_pl_process_time', 'process_time'),
    )
