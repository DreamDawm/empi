from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import EmpiMaster
from app.services.cleaner import DataCleaner
from app.services.similarity import similarity_calculator


class NameMatchMerger:
    """处理无身份证患者的姓名匹配合并"""

    def __init__(self):
        self.data_cleaner = DataCleaner()

    def has_valid_id_card(self, patient: Dict[str, Any]) -> bool:
        """检查患者是否有有效身份证"""
        id_card = patient.get('identity_card_num') or patient.get('card_id')
        if not id_card:
            return False
        cleaned = self.data_cleaner.clean_id_card(id_card)
        return cleaned is not None

    def find_by_name(self, db: Session, patient: Dict[str, Any]) -> List[EmpiMaster]:
        """根据姓名（汉字和拼音）在 empi_master 中查找匹配记录

        搜索策略：
        1. 先按汉字姓名精确匹配
        2. 再按拼音姓名匹配
        3. 合并去重后返回

        Args:
            db: 数据库会话
            patient: 患者信息字典

        Returns:
            匹配的 EmpiMaster 记录列表（排除自己，只包含 NORMAL 状态）
        """
        name = patient.get('person_name') or patient.get('patient_name')
        if not name:
            return []

        cleaned_name = self.data_cleaner.clean_name(name)
        pinyin_name = self.data_cleaner.get_pinyin(name)
        patient_id = patient.get('patient_id')

        results = []
        seen_ids = set()

        # 1. 按汉字姓名精确匹配
        chinese_matches = db.query(EmpiMaster).filter(
            EmpiMaster.status == 'NORMAL',
            EmpiMaster.patient_id != patient_id,
            EmpiMaster.patient_name == cleaned_name
        ).all()

        for record in chinese_matches:
            if record.patient_id not in seen_ids:
                seen_ids.add(record.patient_id)
                results.append(record)

        # 2. 按拼音姓名匹配（通过 inverted_index 的 pinyin_gender 字段）
        if pinyin_name:
            # 从 pinyin_gender_index 中提取拼音前缀
            pinyin_matches = db.query(EmpiMaster).filter(
                EmpiMaster.status == 'NORMAL',
                EmpiMaster.patient_id != patient_id,
                EmpiMaster.pinyin_gender_index.like(f"{pinyin_name}_%")
            ).all()

            for record in pinyin_matches:
                if record.patient_id not in seen_ids:
                    seen_ids.add(record.patient_id)
                    results.append(record)

        return results

    def calculate_non_id_card_score(self, patient_a: Dict[str, Any],
                                     patient_b: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """计算除身份证外的字段相似度

        计算字段：name, birthday, gender, phone, address
        排除字段：identity_card, card_id

        Returns:
            Tuple[float, Dict[str, float]]: (平均分, 各字段分数详情)
        """
        # 定义非身份证字段
        non_id_fields = ['name', 'birthday', 'gender', 'phone', 'address']

        details = {}
        total_score = 0.0
        valid_field_count = 0

        for field in non_id_fields:
            score = similarity_calculator._calculate_field_similarity(field, patient_a, patient_b)
            details[field] = score

            # 只计算有值的字段
            if score > 0 or (patient_a.get(field) and patient_b.get(field)):
                total_score += score
                valid_field_count += 1

        # 计算平均分（只考虑有值的字段）
        avg_score = total_score / valid_field_count if valid_field_count > 0 else 0.0

        return avg_score, details

    def is_majority_full_score(self, field_scores: Dict[str, float]) -> bool:
        """判断是否超过一半字段得满分（100分）

        Args:
            field_scores: 各字段分数字典

        Returns:
            bool: 是否超过一半字段得满分
        """
        if not field_scores:
            return False

        total_fields = len(field_scores)
        full_score_count = sum(1 for score in field_scores.values() if score >= 100.0)

        # 必须严格超过一半（> 50%）
        return full_score_count > total_fields / 2

    def _get_patient_data(self, db: Session, patient_id: str) -> Optional[Dict[str, Any]]:
        """从 im_patient 表获取患者完整数据

        Args:
            db: 数据库会话
            patient_id: 患者ID

        Returns:
            患者数据字典，如果不存在返回 None
        """
        query = text("SELECT * FROM im_patient WHERE patient_id = :patient_id LIMIT 1")
        result = db.execute(query.params(patient_id=patient_id))
        row = result.fetchone()
        if row:
            columns = result.keys()
            return dict(zip(columns, row))
        return None

    def decide_merge(self, db: Session, patient: Dict[str, Any],
                     threshold: float) -> Tuple[str, Optional[int], float]:
        """决策是否可以基于姓名匹配合并

        流程：
        1. 在 empi_master 中查找姓名相同的记录
        2. 对每个匹配记录计算非身份证字段相似度
        3. 如果超过一半字段满分，则认为可以合并

        Args:
            db: 数据库会话
            patient: 待处理患者数据
            threshold: 合并阈值（此场景下不直接使用，但保留参数）

        Returns:
            Tuple[str, Optional[int], float]:
                - 决策类型: 'NAME_MATCH_MERGE' 或 'NO_MATCH'
                - 主索引ID: 可合并时返回，否则 None
                - 相似度分数
        """
        # 查找姓名匹配的记录
        matches = self.find_by_name(db, patient)

        if not matches:
            return ('NO_MATCH', None, 0.0)

        best_match = None
        best_score = 0.0
        best_master_id = None

        for match_record in matches:
            # 从 im_patient 表获取完整患者数据
            candidate_data = self._get_patient_data(db, match_record.patient_id)

            if not candidate_data:
                continue

            # 计算非身份证字段相似度
            avg_score, field_scores = self.calculate_non_id_card_score(patient, candidate_data)

            # 检查是否超过一半字段满分
            if self.is_majority_full_score(field_scores):
                if avg_score > best_score:
                    best_score = avg_score
                    best_match = match_record
                    best_master_id = match_record.master_id

        if best_match:
            return ('NAME_MATCH_MERGE', best_master_id, best_score)

        return ('NO_MATCH', None, 0.0)


name_match_merger = NameMatchMerger()
