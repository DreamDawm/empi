from typing import Dict, Any, Optional
import redis
import json
from app.core.config import settings

class SimilarityCalculator:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )

    def calculate(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any], weights: Any) -> float:
        """计算两个患者之间的相似度"""
        cache_key = self._get_cache_key(patient_a, patient_b)
        cached = self.redis_client.get(cache_key)
        if cached:
            return float(cached)

        scores = {}
        total_weight = 0

        # Handle both old dict format {'field': weight} and new list format [{'field_name': 'x', 'weight': y}]
        if isinstance(weights, dict):
            for field, weight in weights.items():
                if weight <= 0:
                    continue
                total_weight += weight
                score = self._calculate_field_similarity(field, patient_a, patient_b)
                scores[field] = score * weight
        elif isinstance(weights, list):
            for item in weights:
                field_name = item.get('field_name', '')
                weight = item.get('weight', 0)
                if weight <= 0:
                    continue
                total_weight += weight
                score = self._calculate_field_similarity(item, patient_a, patient_b)
                scores[field_name] = score * weight

        if total_weight == 0:
            final_score = 0
        else:
            final_score = sum(scores.values()) / total_weight

        self.redis_client.setex(cache_key, 3600, str(final_score))
        return final_score

    def _calculate_field_similarity(self, field: Any, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """计算单个字段的相似度"""
        # Handle both string field names and dict with field_name key
        if isinstance(field, dict):
            field_name = field.get('field_name', '')
        else:
            field_name = field

        methods = {
            'identity_card': self._similarity_identity_card,
            'identity_card_num': self._similarity_identity_card,
            'name': self._similarity_name,
            'person_name': self._similarity_name,
            'birthday': self._similarity_birthday,
            'gender': self._similarity_gender,
            'phone': self._similarity_phone,
            'address': self._similarity_address,
            'location': self._similarity_address,
        }

        if not field_name or field_name not in methods:
            return 0.0
        method = methods[field_name]
        if method is None:
            return 0.0
        return method(patient_a, patient_b)

    def _similarity_identity_card(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """身份证相似度：完全匹配100，前6位相同30"""
        id_a = (patient_a.get('identity_card_num') or patient_a.get('card_id') or '').strip()
        id_b = (patient_b.get('identity_card_num') or patient_b.get('card_id') or '').strip()
        if not id_a or not id_b:
            return 0.0
        if id_a == id_b:
            return 100.0
        if len(id_a) >= 6 and len(id_b) >= 6 and id_a[:6] == id_b[:6]:
            return 30.0
        return 0.0

    def _similarity_name(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """姓名相似度：拼音完全匹配100，拼音编辑距离按比例"""
        from app.services.cleaner import DataCleaner
        name_a = DataCleaner.get_pinyin(patient_a.get('patient_name', ''))
        name_b = DataCleaner.get_pinyin(patient_b.get('patient_name', ''))
        if not name_a or not name_b:
            return 0.0
        if name_a == name_b:
            return 100.0
        distance = self._levenshtein_distance(name_a, name_b)
        max_len = max(len(name_a), len(name_b))
        if max_len == 0:
            return 0.0
        return max(0.0, (1 - distance / max_len) * 100)

    def _similarity_birthday(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """生日相似度：完全匹配100，年份匹配30，月日匹配各20"""
        from app.services.cleaner import DataCleaner
        birth_a = patient_a.get('birthday')
        birth_b = patient_b.get('birthday')
        year_a = DataCleaner.get_birth_year(birth_a)
        year_b = DataCleaner.get_birth_year(birth_b)

        if not year_a or not year_b:
            return 0.0

        if year_a == year_b:
            year_score = 30
        else:
            return 0.0

        month_a = self._get_month(birth_a)
        month_b = self._get_month(birth_b)
        day_a = self._get_day(birth_a)
        day_b = self._get_day(birth_b)

        month_day_score = 0
        if month_a and month_b and month_a == month_b:
            month_day_score += 20
        if day_a and day_b and day_a == day_b:
            month_day_score += 20

        return year_score + month_day_score

    def _get_month(self, birthday) -> Optional[int]:
        if not birthday:
            return None
        from datetime import datetime
        if isinstance(birthday, datetime):
            return birthday.month
        if isinstance(birthday, str) and len(birthday) >= 7:
            try:
                return int(birthday[5:7])
            except ValueError:
                return None
        return None

    def _get_day(self, birthday) -> Optional[int]:
        if not birthday:
            return None
        from datetime import datetime
        if isinstance(birthday, datetime):
            return birthday.day
        if isinstance(birthday, str) and len(birthday) >= 10:
            try:
                return int(birthday[8:10])
            except ValueError:
                return None
        return None

    def _similarity_gender(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """性别相似度：完全匹配100，不匹配0"""
        from app.services.cleaner import DataCleaner
        gender_a = DataCleaner.clean_gender(patient_a.get('gender', ''))
        gender_b = DataCleaner.clean_gender(patient_b.get('gender', ''))
        if not gender_a or not gender_b:
            return 0.0
        return 100.0 if gender_a == gender_b else 0.0

    def _similarity_phone(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """电话相似度：完全匹配100，前7位相同60"""
        from app.services.cleaner import DataCleaner
        phone_a = DataCleaner.clean_phone(patient_a.get('phone', ''))
        phone_b = DataCleaner.clean_phone(patient_b.get('phone', ''))
        if not phone_a or not phone_b:
            return 0.0
        if phone_a == phone_b:
            return 100.0
        if len(phone_a) >= 7 and len(phone_b) >= 7 and phone_a[:7] == phone_b[:7]:
            return 60.0
        return 0.0

    def _similarity_address(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """地址相似度：完全匹配100，JSON相似度计算"""
        addr_a = (patient_a.get('location') or '').strip()
        addr_b = (patient_b.get('location') or '').strip()
        if not addr_a or not addr_b:
            return 0.0
        if addr_a == addr_b:
            return 100.0
        len_common = self._common_prefix_length(addr_a, addr_b)
        max_len = max(len(addr_a), len(addr_b))
        if max_len == 0:
            return 0.0
        return (len_common / max_len) * 100

    def _common_prefix_length(self, s1: str, s2: str) -> int:
        i = 0
        for c1, c2 in zip(s1, s2):
            if c1 == c2:
                i += 1
            else:
                break
        return i

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def _get_cache_key(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> str:
        p1 = patient_a.get('patient_id', '')
        p2 = patient_b.get('patient_id', '')
        sorted_ids = sorted([p1, p2])
        return f"similarity:{sorted_ids[0]}:{sorted_ids[1]}"

    def get_field_details(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> Dict[str, float]:
        """获取各字段相似度明细"""
        fields = ['identity_card', 'name', 'birthday', 'gender', 'phone', 'address']
        details = {}
        for field in fields:
            details[field] = self._calculate_field_similarity(field, patient_a, patient_b)
        return details

similarity_calculator = SimilarityCalculator()