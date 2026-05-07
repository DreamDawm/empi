from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
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
        """计算除身份证外的字段相似度"""
        pass

    def is_majority_full_score(self, field_scores: Dict[str, float]) -> bool:
        """判断是否超过一半字段得满分"""
        pass

    def decide_merge(self, db: Session, patient: Dict[str, Any],
                     threshold: float) -> Tuple[str, Optional[int], float]:
        """决策是否可以基于姓名匹配合并"""
        pass


name_match_merger = NameMatchMerger()
