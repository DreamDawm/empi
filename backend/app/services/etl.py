from typing import Dict, Any, Optional, List
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import EmpiMaster, EmpiProcessLog, EmpiConfig
from app.models.base import SessionLocal
from app.core.snowflake import get_snowflake_generator
from app.services.cleaner import DataCleaner
from app.services.inverted_index import inverted_index_service
from app.services.similarity import similarity_calculator
from app.services.merger import decision_engine
from app.services.name_match_merger import name_match_merger
from app.services.logging_service import logging_service
from app.core.config import settings
import redis
import json
from datetime import datetime

BATCH_COMMIT_SIZE = 100

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

        # Warm cache on first call if empty
        if not self.redis_client.exists(self._processed_patients_key):
            self.warm_processed_cache(db)

        last_id = self._get_last_id()
        patients = self._fetch_patients(db, last_id, batch_size)

        logging_service.info(f"获取到 {len(patients)} 条待处理记录")

        if not patients:
            return {'processed': 0, 'merged': 0, 'pending': 0}

        weights = self._get_weights(db)
        threshold = self._get_threshold(db)

        logging_service.info(f"[批次开始] 获取到 {len(patients)} 条待处理记录, 权重={weights}, 阈值={threshold}")

        stats = {'processed': 0, 'merged': 0, 'pending': 0}

        groups = self._group_patients_by_pinyin(patients)
        max_workers = min(8, len(groups))

        logging_service.info(f"分为 {len(groups)} 组，使用 {max_workers} 个工作线程")

        if max_workers <= 1:
            # 只有一组或空，退化为串行处理
            for patient in patients:
                if self._is_processed(db, patient['patient_id']):
                    continue
                self._process_patient(db, patient, weights, threshold, stats)
            db.commit()
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._process_group, group, weights, threshold): key
                    for key, group in groups.items()
                }
                for future in as_completed(futures):
                    group_key = futures[future]
                    try:
                        group_stats = future.result()
                        stats['processed'] += group_stats['processed']
                        stats['merged'] += group_stats['merged']
                        stats['pending'] += group_stats['pending']
                    except Exception as e:
                        logging_service.error(f"分组 {group_key} 处理异常: {e}")

        # Commit any remaining records at the end
        logging_service.info(f"[批次完成] 处理={stats['processed']}, 合并={stats['merged']}, 待审核={stats['pending']}")

        # 使用自增 id 作为游标，确保不遗漏任何数据
        self._set_last_id(patients[-1]['id'])

        logging_service.info(f"本轮处理完成: {stats}")

        return stats

    def _group_patients_by_pinyin(self, patients: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按 pinyin_gender 分组，同组内串行处理避免冲突"""
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for patient in patients:
            index = inverted_index_service.build_index(patient)
            key = index.get('pinyin_gender', '') or 'unknown'
            patient['_prebuilt_index'] = index
            groups[key].append(patient)
        return dict(groups)

    def _process_group(self, group_patients: List[Dict[str, Any]], weights: Dict[str, float], threshold: float) -> Dict[str, int]:
        """在独立 Session 中处理一组患者"""
        db = SessionLocal()
        stats = {'processed': 0, 'merged': 0, 'pending': 0}
        try:
            for patient in group_patients:
                if self._is_processed(db, patient['patient_id']):
                    continue
                self._process_patient(db, patient, weights, threshold, stats)
            db.commit()
        except Exception as e:
            db.rollback()
            logging_service.error(f"分组处理失败: {e}")
        finally:
            db.close()
        return stats

    def _get_last_id(self) -> Optional[int]:
        """获取上一次处理的最大自增 id"""
        key = 'etl:last_id'
        val = self.redis_client.get(key)
        return int(val) if val is not None else None

    def _set_last_id(self, last_id: int):
        """保存上一次处理的最大自增 id"""
        key = 'etl:last_id'
        self.redis_client.set(key, last_id)

    def warm_processed_cache(self, db: Session):
        """从数据库加载已处理的患者ID到Redis缓存"""
        logging_service.info("开始加载已处理患者到缓存...")
        processed = db.query(EmpiProcessLog.patient_id).distinct().all()
        patient_ids = [p.patient_id for p in processed]

        if not patient_ids:
            logging_service.info("没有已处理记录，跳过缓存预热")
            return

        # Use atomic key rename pattern to avoid race condition
        new_key = f"{self._processed_patients_key}:new"
        pipe = self.redis_client.pipeline()
        pipe.delete(new_key)
        pipe.sadd(new_key, *patient_ids)
        pipe.rename(new_key, self._processed_patients_key)  # Atomic operation
        pipe.execute()

        logging_service.info(f"已加载 {len(patient_ids)} 条已处理记录到缓存")

    def _fetch_patients(self, db: Session, last_id: Optional[int],
                       batch_size: int) -> List[Dict[str, Any]]:
        """从im_patient表获取增量数据，使用自增 id 作为游标"""
        if last_id:
            query = text("SELECT * FROM im_patient WHERE id > :last_id ORDER BY id LIMIT :limit")
            result = db.execute(query.params(last_id=last_id, limit=batch_size))
        else:
            query = text("SELECT * FROM im_patient ORDER BY id LIMIT :limit")
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
        # Also check if patient already exists in empi_master (handles interrupted ETL)
        existing_master = db.query(EmpiMaster).filter(
            EmpiMaster.patient_id == patient_id
        ).first()
        if existing_master:
            return True
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
        current_patient_id = patient['patient_id']
        current_patient_name = patient.get('person_name', '')
        current_patient_gender = patient.get('gender', '')
        logging_service.debug(f"[patient_id={current_patient_id}] 开始处理: 姓名={current_patient_name}, 性别={current_patient_gender}")

        inverted_index = patient.get('_prebuilt_index') or inverted_index_service.build_index(patient)

        # 提取索引字段值
        pinyin_gender = inverted_index.get('pinyin_gender', '')
        birth_year_gender = inverted_index.get('birth_year_gender', '')
        id_card_prefix = inverted_index.get('id_card_prefix', '')

        logging_service.debug(f"[patient_id={current_patient_id}] 索引字段: pinyin_gender={pinyin_gender}, birth_year_gender={birth_year_gender}, id_card_prefix={id_card_prefix}")

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
                merged_to_master_id=master_id,  # Master points to itself
                card_id=patient.get('card_id') or patient.get('identity_card_num'),
                inverted_index=inverted_index,
                pinyin_gender_index=pinyin_gender,
                birth_year_gender_index=birth_year_gender,
                id_card_prefix_index=id_card_prefix
            )
            db.add(patient_record)
            db.flush()  # Flush to make the new record visible to subsequent queries

        # Check if patient has valid ID card
        has_valid_id = name_match_merger.has_valid_id_card(patient)

        if not has_valid_id:
            # Patient without valid ID card - use name match merging
            logging_service.debug(f"[patient_id={current_patient_id}] 无有效身份证，尝试姓名匹配合并")

            decision, master_id, score = name_match_merger.decide_merge(db, patient, threshold)

            if decision == 'NAME_MATCH_MERGE':
                # Perform name match merge
                logging_service.debug(f"[patient_id={current_patient_id}] 姓名匹配合并成功! master_id={master_id}, 相似度={score:.2f}")

                # Update patient record to merged status
                patient_record.merged_to_master_id = master_id
                patient_record.status = 'MERGED'

                # Create merge log
                self._save_merge_log(db, patient['patient_id'], master_id, score, 'NAME_MATCH')

                stats['merged'] += 1

                # Save process log and return early
                self._save_process_log(db, patient['patient_id'], 'PROCESS', {
                    'candidates_checked': 0,
                    'merges': 1,
                    'merge_type': 'NAME_MATCH'
                })
                stats['processed'] += 1
                logging_service.debug(f"[patient_id={current_patient_id}] 处理完成（姓名匹配）: 已处理={stats['processed']}, 已合并={stats['merged']}")
                return

        # Regular processing for patients with valid ID card
        candidates = inverted_index_service.search_candidates(db, patient, pinyin_gender, prebuilt_index=inverted_index)
        logging_service.debug(f"[patient_id={current_patient_id}] 找到 {len(candidates)} 个候选匹配")

        for candidate in candidates:
            if candidate['patient_id'] == patient['patient_id']:
                continue

            candidate_data = {
                'patient_id': candidate['patient_id'],
                'person_name': candidate['patient_name'],
                'gender': candidate['inverted_index'].get('pinyin_gender', '').split('_')[-1] if candidate.get('inverted_index') else '',
                'birthday': candidate['inverted_index'].get('birth_year_gender', '').split('_')[0] if candidate.get('inverted_index') else None,
                'card_id': candidate.get('card_id'),
                'identity_card_num': candidate.get('card_id'),
                'phone': None,
                'location': None,
            }

            decision, score = decision_engine.decide(
                db, patient, candidate_data, weights, threshold
            )

            logging_service.debug(f"[patient_id={current_patient_id}] vs [candidate_id={candidate['patient_id']}] 相似度评分: {score:.2f}, 决策: {decision}")

            if decision == 'DIRECT_MERGE':
                # 直接合并（身份证+姓名相同）
                master_id = decision_engine.auto_merge(db, patient, candidate_data, score, 'DIRECT')
                stats['merged'] += 1
                logging_service.debug(f"[patient_id={current_patient_id}] 直接合并成功（身份证+姓名相同）! master_id={master_id}, 累计合并数: {stats['merged']}")
            elif decision == 'AUTO_MERGE':
                master_id = decision_engine.auto_merge(db, patient, candidate_data, score, 'AUTO')
                stats['merged'] += 1
                logging_service.debug(f"[patient_id={current_patient_id}] 自动合并成功! master_id={master_id}, 累计合并数: {stats['merged']}")
            else:
                stats['pending'] += 1
                logging_service.debug(f"[patient_id={current_patient_id}] 进入待审核, 累计待审核数: {stats['pending']}")

        # Save process log once per patient (not per candidate) for idempotency tracking
        self._save_process_log(db, patient['patient_id'], 'PROCESS', {
            'candidates_checked': len(candidates),
            'merges': stats['merged']
        })

        stats['processed'] += 1

        logging_service.debug(f"[patient_id={current_patient_id}] 处理完成: 已处理={stats['processed']}, 已合并={stats['merged']}, 待审核={stats['pending']}")

    def _save_merge_log(self, db: Session, patient_id: str, master_id: int,
                        score: float, merge_type: str):
        """保存合并日志

        For NAME_MATCH merge, person_id_b uses master_id as placeholder since
        there's no specific second patient in this merge scenario.
        """
        from app.models import EmpiMergeLog

        log = EmpiMergeLog(
            person_id_a=patient_id,
            person_id_b=str(master_id),  # Use master_id as placeholder for NAME_MATCH
            master_id=master_id,
            similarity_score=score,
            merge_type=merge_type,
            merge_time=datetime.now()
        )
        db.add(log)
        db.flush()

    def _save_process_log(self, db: Session, patient_id: str, process_type: str, details: Dict):
        """保存处理日志并添加到Redis缓存"""
        # Add to Redis set immediately for fast idempotency checks
        try:
            self.redis_client.sadd(self._processed_patients_key, patient_id)
        except redis.RedisError:
            logging_service.warning(f"Redis unavailable, skipping cache for patient {patient_id}")
        # Always save to database as persistent log
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
        db.flush()

etl_scheduler = ETLScheduler()
