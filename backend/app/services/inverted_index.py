from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models import EmpiMaster
from app.services.cleaner import DataCleaner
import json

class InvertedIndexService:
    def __init__(self):
        self.data_cleaner = DataCleaner()

    def build_index(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        """为患者构建倒排索引"""
        return self.data_cleaner.build_inverted_index(patient)

    def search_candidates(self, db: Session, patient: Dict[str, Any], pinyin_gender: str) -> List[Dict[str, Any]]:
        """搜索候选匹配患者 - 使用数据库索引快速检索"""
        index = self.build_index(patient)
        candidates = []

        if not pinyin_gender:
            return candidates

        # 精确匹配：pinyin_gender 完全相同
        exact_matches = db.query(EmpiMaster).filter(
            EmpiMaster.status == 'NORMAL',
            EmpiMaster.patient_id != patient.get('patient_id'),
            EmpiMaster.pinyin_gender_index == pinyin_gender
        ).all()

        for record in exact_matches:
            candidates.append({
                'patient_id': record.patient_id,
                'patient_name': record.patient_name,
                'master_id': record.master_id,
                'inverted_index': record.inverted_index
            })

        # 获取当前患者的birth_year和id_card_prefix用于模糊匹配
        pinyin_part = pinyin_gender.split('_')[0]  # 纯拼音
        birth_year_gender = index.get('birth_year_gender', '')
        id_card_prefix = index.get('id_card_prefix', '')

        # 如果没有精确匹配，尝试模糊匹配（同拼音前缀 + 生日或身份证前6位）
        if not candidates:
            # 出生年份+性别匹配（同拼音前缀 + 出生年份 + 性别相同）
            if birth_year_gender:
                fuzzy_matches = db.query(EmpiMaster).filter(
                    EmpiMaster.status == 'NORMAL',
                    EmpiMaster.patient_id != patient.get('patient_id'),
                    EmpiMaster.pinyin_gender_index.like(f"{pinyin_part}%"),
                    EmpiMaster.birth_year_gender_index == birth_year_gender
                ).all()

                for record in fuzzy_matches:
                    candidates.append({
                        'patient_id': record.patient_id,
                        'patient_name': record.patient_name,
                        'master_id': record.master_id,
                        'inverted_index': record.inverted_index
                    })

            # 身份证前6位+性别匹配
            if not candidates and id_card_prefix:
                id_matches = db.query(EmpiMaster).filter(
                    EmpiMaster.status == 'NORMAL',
                    EmpiMaster.patient_id != patient.get('patient_id'),
                    EmpiMaster.id_card_prefix_index == id_card_prefix
                ).all()

                for record in id_matches:
                    candidates.append({
                        'patient_id': record.patient_id,
                        'patient_name': record.patient_name,
                        'master_id': record.master_id,
                        'inverted_index': record.inverted_index
                    })

        return candidates

    def update_index(self, db: Session, patient_id: str, inverted_index: Dict[str, Any]):
        """更新患者的倒排索引"""
        record = db.query(EmpiMaster).filter(EmpiMaster.patient_id == patient_id).first()
        if record:
            record.inverted_index = inverted_index
            # 同时更新预索引字段
            record.pinyin_gender_index = inverted_index.get('pinyin_gender', '')
            record.birth_year_gender_index = inverted_index.get('birth_year_gender', '')
            record.id_card_prefix_index = inverted_index.get('id_card_prefix', '')
            db.commit()

inverted_index_service = InvertedIndexService()