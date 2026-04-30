from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import EmpiMaster, EmpiMergeLog, EmpiPendingReview, EmpiProcessLog
from app.core.snowflake import get_snowflake_generator
from app.services.similarity import similarity_calculator
from app.services.cleaner import DataCleaner
import redis
import json
from datetime import datetime

class MergeDecisionEngine:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        self.snowflake = get_snowflake_generator()
        self.data_cleaner = DataCleaner()

    def decide(self, db: Session, patient_a: Dict[str, Any], patient_b: Dict[str, Any],
               weights: Dict[str, float], threshold: float) -> Tuple[str, float]:
        """决策是否合并：返回 (decision, score)"""
        score = similarity_calculator.calculate(patient_a, patient_b, weights)
        field_details = similarity_calculator.get_field_details(patient_a, patient_b)

        if score >= threshold:
            return ('AUTO_MERGE', score)

        self._save_pending_review(db, patient_a, patient_b, score, field_details)
        return ('PENDING_REVIEW', score)

    def _save_pending_review(self, db: Session, patient_a: Dict[str, Any],
                            patient_b: Dict[str, Any], score: float, field_details: Dict[str, float]):
        existing = db.query(EmpiPendingReview).filter(
            ((EmpiPendingReview.person_id_a == patient_a['patient_id']) &
             (EmpiPendingReview.person_id_b == patient_b['patient_id'])) |
            ((EmpiPendingReview.person_id_a == patient_b['patient_id']) &
             (EmpiPendingReview.person_id_b == patient_a['patient_id']))
        ).first()

        if existing:
            return

        pending = EmpiPendingReview(
            person_id_a=patient_a['patient_id'],
            person_id_b=patient_b['patient_id'],
            similarity_score=score,
            similarity_details=json.dumps(field_details),
            status='PENDING'
        )
        db.add(pending)
        db.commit()

    def auto_merge(self, db: Session, patient_a: Dict[str, Any], patient_b: Dict[str, Any],
                   score: float, merge_type: str = 'AUTO') -> int:
        """执行自动合并，返回主索引ID"""
        existing_log = db.query(EmpiMergeLog).filter(
            ((EmpiMergeLog.person_id_a == patient_a['patient_id']) &
             (EmpiMergeLog.person_id_b == patient_b['patient_id'])) |
            ((EmpiMergeLog.person_id_a == patient_b['patient_id']) &
             (EmpiMergeLog.person_id_b == patient_a['patient_id']))
        ).first()

        if existing_log:
            return existing_log.master_id

        created_a = patient_a.get('created_at') or datetime.now()
        created_b = patient_b.get('created_at') or datetime.now()

        if created_a <= created_b:
            master_patient = patient_a
            slave_patient = patient_b
        else:
            master_patient = patient_b
            slave_patient = patient_a

        master_record = db.query(EmpiMaster).filter(
            EmpiMaster.patient_id == master_patient['patient_id']
        ).first()

        if master_record:
            master_id = master_record.master_id
        else:
            master_id = self.snowflake.next_id()

        slave_record = db.query(EmpiMaster).filter(
            EmpiMaster.patient_id == slave_patient['patient_id']
        ).first()

        if slave_record:
            slave_record.status = 'MERGED'
            slave_record.merged_to_master_id = master_id
            slave_record.updated_at = datetime.now()

        merge_log = EmpiMergeLog(
            person_id_a=master_patient['patient_id'],
            person_id_b=slave_patient['patient_id'],
            master_id=master_id,
            merge_type=merge_type,
            similarity_score=score,
            merge_time=datetime.now()
        )
        db.add(merge_log)
        db.commit()

        return master_id

decision_engine = MergeDecisionEngine()