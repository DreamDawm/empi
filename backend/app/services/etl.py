from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import EmpiMaster, EmpiProcessLog, EmpiConfig
from app.core.snowflake import get_snowflake_generator
from app.services.cleaner import DataCleaner
from app.services.inverted_index import inverted_index_service
from app.services.similarity import similarity_calculator
from app.services.merger import decision_engine
from app.services.logging_service import logging_service
from app.core.config import settings
import redis
import json
from datetime import datetime

class ETLScheduler:
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
        self._processed_patients_key = 'etl:processed_patients'

    def poll_and_process(self, db: Session, batch_size: int = None):
        """轮询并处理增量数据"""
        if batch_size is None:
            batch_size = settings.ETL_BATCH_SIZE

        logging_service.info(f"开始轮询处理，batch_size={batch_size}")

        last_patient_id = self._get_last_patient_id()
        patients = self._fetch_patients(db, last_patient_id, batch_size)

        logging_service.info(f"获取到 {len(patients)} 条待处理记录")

        if not patients:
            return {'processed': 0, 'merged': 0, 'pending': 0}

        weights = self._get_weights(db)
        threshold = self._get_threshold(db)

        stats = {'processed': 0, 'merged': 0, 'pending': 0}

        for patient in patients:
            # Idempotency check: skip patients already processed in previous batches
            # Note: This checks EmpiProcessLog (tracking processed patients), not EmpiMaster.
            # New EmpiMaster records created in this batch are committed per-patient inside
            # _process_patient(), making them visible to subsequent search_candidates() calls.
            if self._is_processed(db, patient['patient_id']):
                continue

            self._process_patient(db, patient, weights, threshold, stats)

        # 使用 patient_id 作为游标，避免同一时刻多条记录被遗漏
        last_processed_id = patients[-1]['patient_id']
        self._set_last_patient_id(last_processed_id)

        logging_service.info(f"本轮处理完成: {stats}")

        return stats

    def _get_last_patient_id(self) -> Optional[str]:
        """获取上一次处理的最大 patient_id"""
        key = 'etl:last_patient_id'
        return self.redis_client.get(key)

    def _set_last_patient_id(self, patient_id: str):
        """保存上一次处理的最大 patient_id"""
        key = 'etl:last_patient_id'
        self.redis_client.set(key, patient_id)

    def _fetch_patients(self, db: Session, last_patient_id: Optional[str],
                       batch_size: int) -> List[Dict[str, Any]]:
        """从im_patient表获取增量数据，使用 patient_id 作为游标"""
        if last_patient_id:
            # 使用 > 而不是 >= 确保不会重复处理同一批
            query = text("SELECT * FROM im_patient WHERE patient_id > :last_id ORDER BY patient_id LIMIT :limit")
            result = db.execute(query.params(last_id=last_patient_id, limit=batch_size))
        else:
            # 首次运行，按 patient_id 顺序获取
            query = text("SELECT * FROM im_patient ORDER BY patient_id LIMIT :limit")
            result = db.execute(query.params(limit=batch_size))

        columns = result.keys()
        patients = []
        for row in result.fetchall():
            patient = dict(zip(columns, row))
            patients.append(patient)
        return patients

    def _is_processed(self, db: Session, patient_id: str) -> bool:
        """Check if patient was already processed using Redis cache"""
        try:
            if self.redis_client.sismember(self._processed_patients_key, patient_id):
                return True
        except redis.RedisError:
            logging_service.warning("Redis unavailable, falling back to database")
        return self._is_processed_db(db, patient_id)

    def _is_processed_db(self, db: Session, patient_id: str) -> bool:
        """Database fallback for processed check"""
        log = db.query(EmpiProcessLog).filter(
            EmpiProcessLog.patient_id == patient_id
        ).first()
        return log is not None

    def _get_weights(self, db: Session) -> Dict[str, float]:
        """获取字段权重配置"""
        cache_key = 'config:weights'
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'field_weights'
        ).first()

        if config:
            weights = config.config_value
        else:
            weights = {
                'identity_card': 30,
                'name': 30,
                'birthday': 20,
                'gender': 5,
                'phone': 10,
                'address': 5
            }

        self.redis_client.setex(cache_key, 3600, json.dumps(weights))
        return weights

    def _get_threshold(self, db: Session) -> float:
        """获取自动合并阈值"""
        cache_key = 'config:threshold'
        cached = self.redis_client.get(cache_key)
        if cached:
            return float(cached)

        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'merge_threshold'
        ).first()

        if config:
            threshold = config.config_value.get('threshold', settings.DEFAULT_MERGE_THRESHOLD)
        else:
            threshold = settings.DEFAULT_MERGE_THRESHOLD

        self.redis_client.setex(cache_key, 3600, str(threshold))
        return threshold

    def _process_patient(self, db: Session, patient: Dict[str, Any],
                         weights: Dict[str, float], threshold: float,
                         stats: Dict[str, int]):
        """处理单个患者"""
        logging_service.info(f"处理患者: {patient['patient_id']}")

        inverted_index = inverted_index_service.build_index(patient)

        # 提取索引字段值
        pinyin_gender = inverted_index.get('pinyin_gender', '')
        birth_year_gender = inverted_index.get('birth_year_gender', '')
        id_card_prefix = inverted_index.get('id_card_prefix', '')

        patient_record = db.query(EmpiMaster).filter(
            EmpiMaster.patient_id == patient['patient_id']
        ).first()

        if not patient_record:
            master_id = self.snowflake.next_id()
            patient_record = EmpiMaster(
                id=master_id,
                patient_id=patient['patient_id'],
                patient_name=self.data_cleaner.clean_name(patient.get('person_name', '')),
                master_id=master_id,
                status='NORMAL',
                inverted_index=inverted_index,
                pinyin_gender_index=pinyin_gender,
                birth_year_gender_index=birth_year_gender,
                id_card_prefix_index=id_card_prefix
            )
            db.add(patient_record)
            db.commit()

        candidates = inverted_index_service.search_candidates(db, patient, pinyin_gender)

        for candidate in candidates:
            if candidate['patient_id'] == patient['patient_id']:
                continue

            candidate_patient = db.query(EmpiMaster).filter(
                EmpiMaster.patient_id == candidate['patient_id']
            ).first()

            if not candidate_patient:
                continue

            candidate_data = {
                'patient_id': candidate_patient.patient_id,
                'patient_name': candidate_patient.patient_name,
                'gender': candidate_patient.inverted_index.get('pinyin_gender', '').split('_')[-1] if candidate_patient.inverted_index else '',
                'birthday': candidate_patient.inverted_index.get('birth_year_gender', '').split('_')[0] if candidate_patient.inverted_index else None,
                'identity_card_num': None,
                'card_id': None,
                'phone': None,
                'location': None,
            }

            decision, score = decision_engine.decide(
                db, patient, candidate_data, weights, threshold
            )

            if decision == 'AUTO_MERGE':
                decision_engine.auto_merge(db, patient, candidate_data, score, 'AUTO')
                stats['merged'] += 1

            self._save_process_log(db, patient['patient_id'], 'CALCULATE', {
                'candidate_id': candidate['patient_id'],
                'score': score,
                'decision': decision
            })

        stats['processed'] += 1

        logging_service.info(f"患者 {patient['patient_id']} 处理完成，结果: {stats}")

    def _save_process_log(self, db: Session, patient_id: str, process_type: str, details: Dict):
        """保存处理日志并添加到Redis缓存"""
        # Add to Redis set immediately for fast idempotency checks
        self.redis_client.sadd(self._processed_patients_key, patient_id)
        # Also save to database as persistent log
        self._save_process_log_db(db, patient_id, process_type, details)

    def _save_process_log_db(self, db: Session, patient_id: str, process_type: str, details: Dict):
        """数据库持久化处理日志"""
        log = EmpiProcessLog(
            patient_id=patient_id,
            process_type=process_type,
            details=json.dumps(details),
            process_time=datetime.now()
        )
        db.add(log)
        db.commit()

etl_scheduler = ETLScheduler()
