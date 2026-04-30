from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models import EmpiMaster
from app.services.cleaner import DataCleaner
import json

class InvertedIndexService:
    def __init__(self):
        self.data_cleaner = DataCleaner()

    def build_index(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        """为患者构建倒排索引"""
        return self.data_cleaner.build_inverted_index(patient)

    def search_candidates(self, db: Session, patient: Dict[str, Any]) -> List[Dict[str, Any]]:
        """搜索候选匹配患者"""
        index = self.build_index(patient)
        candidates = []

        pinyin_gender = index.get('pinyin_gender')
        if not pinyin_gender:
            return candidates

        all_records = db.query(EmpiMaster).filter(
            EmpiMaster.status == 'NORMAL'
        ).all()

        for record in all_records:
            if not record.inverted_index:
                continue
            record_index = record.inverted_index if isinstance(record.inverted_index, dict) else json.loads(record.inverted_index)

            if record_index.get('pinyin_gender') == pinyin_gender:
                candidates.append({
                    'patient_id': record.patient_id,
                    'patient_name': record.patient_name,
                    'master_id': record.master_id,
                    'inverted_index': record_index
                })
                continue

            if pinyin_gender.split('_')[0] == record_index.get('pinyin_gender', '').split('_')[0]:
                birth_year_gender = index.get('birth_year_gender')
                record_birth_year_gender = record_index.get('birth_year_gender')
                if birth_year_gender and record_birth_year_gender and birth_year_gender == record_birth_year_gender:
                    candidates.append({
                        'patient_id': record.patient_id,
                        'patient_name': record.patient_name,
                        'master_id': record.master_id,
                        'inverted_index': record_index
                    })
                    continue

                id_card_prefix = index.get('id_card_prefix')
                record_id_card_prefix = record_index.get('id_card_prefix')
                if id_card_prefix and record_id_card_prefix and id_card_prefix == record_id_card_prefix:
                    candidates.append({
                        'patient_id': record.patient_id,
                        'patient_name': record.patient_name,
                        'master_id': record.master_id,
                        'inverted_index': record_index
                    })

        return candidates

    def update_index(self, db: Session, patient_id: str, inverted_index: Dict[str, Any]):
        """更新患者的倒排索引"""
        record = db.query(EmpiMaster).filter(EmpiMaster.patient_id == patient_id).first()
        if record:
            record.inverted_index = inverted_index
            db.commit()

inverted_index_service = InvertedIndexService()