from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import EmpiMaster, EmpiMergeLog, EmpiPendingReview, EmpiProcessLog
from app.core.snowflake import get_snowflake_generator
from app.services.similarity import similarity_calculator
from app.services.cleaner import DataCleaner
from app.core.config import settings
import redis
import json
from datetime import datetime

class MergeDecisionEngine:
    DIRECT_MERGE_SCORE = 100.0

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.snowflake = get_snowflake_generator()
        self.data_cleaner = DataCleaner()

    def _is_direct_merge_eligible(self, patient_a: Dict[str, Any],
                                  patient_b: Dict[str, Any]) -> bool:
        """检查两个患者是否满足直接合并条件（身份证+姓名完全相同）"""
        # 获取清洗后的身份证
        id_a = self.data_cleaner.clean_id_card(
            patient_a.get('identity_card_num') or patient_a.get('card_id') or ''
        )
        id_b = self.data_cleaner.clean_id_card(
            patient_b.get('identity_card_num') or patient_b.get('card_id') or ''
        )

        # 身份证必须有效且相同
        if not id_a or not id_b or id_a != id_b:
            return False

        # 获取清洗后的姓名（转为拼音比较，因为可能大小写/空格不同）
        name_a = self.data_cleaner.get_pinyin(
            patient_a.get('patient_name') or patient_a.get('person_name') or ''
        )
        name_b = self.data_cleaner.get_pinyin(
            patient_b.get('patient_name') or patient_b.get('person_name') or ''
        )

        # 姓名拼音必须相同
        if not name_a or not name_b or name_a != name_b:
            return False

        return True

    def decide(self, db: Session, patient_a: Dict[str, Any], patient_b: Dict[str, Any],
               weights: Dict[str, float], threshold: float) -> Tuple[str, float]:
        """决策是否合并：返回 (decision, score)"""
        # 优先检查是否满足直接合并条件（身份证+姓名相同）
        if self._is_direct_merge_eligible(patient_a, patient_b):
            # 直接合并，给最高分确保通过阈值
            return ('DIRECT_MERGE', self.DIRECT_MERGE_SCORE)

        # 不满足直接合并条件，进行相似度评分
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

        # 查询两个患者的 empi_master 记录
        record_a = db.query(EmpiMaster).filter(
            EmpiMaster.patient_id == patient_a['patient_id']
        ).first()
        record_b = db.query(EmpiMaster).filter(
            EmpiMaster.patient_id == patient_b['patient_id']
        ).first()

        # 决定谁是 master，谁是 slave
        # 原则：候选者（patient_b）已经在数据库中存在，应该优先作为 master
        # 当前患者（patient_a）是新处理的，应该作为 slave

        # 特殊情况处理：
        # 1. 如果候选者已被合并，使用其 merged_to_master_id
        # 2. 如果候选者不存在（不应该发生），当前患者作为 master

        # 查询候选者的状态
        if record_b:
            if record_b.status == 'MERGED' and record_b.merged_to_master_id:
                # 候选者已被合并，使用其最终主索引
                master_id = record_b.merged_to_master_id
                # 当前患者作为 slave，合并到候选者的主索引
                master_patient = patient_b
                slave_patient = patient_a
                master_record = record_b
                slave_record = record_a
            else:
                # 候选者是 NORMAL，作为 master
                master_patient = patient_b
                slave_patient = patient_a
                master_record = record_b
                slave_record = record_a
                master_id = record_b.master_id
        else:
            # 候选者不存在（不应该发生），当前患者作为 master
            master_patient = patient_a
            slave_patient = patient_b
            master_record = record_a
            slave_record = None
            if record_a:
                master_id = record_a.master_id
            else:
                master_id = self.snowflake.next_id()

        # 如果 slave_record 存在，更新其状态

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