import re
from typing import Optional, Dict, Any
from pypinyin import lazy_pinyin
from datetime import datetime

class DataCleaner:
    @staticmethod
    def clean_name(name: str) -> str:
        """清洗姓名：去除空格、统一大小写"""
        if not name:
            return ""
        name = re.sub(r'\s+', '', name)
        return name.strip()

    @staticmethod
    def get_pinyin(name: str) -> str:
        """获取姓名拼音（小写）"""
        if not name:
            return ""
        cleaned = DataCleaner.clean_name(name)
        pinyin_list = lazy_pinyin(cleaned)
        return ''.join(pinyin_list).lower()

    @staticmethod
    def clean_gender(gender: str) -> str:
        """清洗性别：统一为M/N"""
        if not gender:
            return "N"
        gender = str(gender).strip().upper()
        if gender in ['男', 'M', 'MALE']:
            return 'M'
        return 'N'

    @staticmethod
    def clean_id_card(id_card: str) -> Optional[str]:
        """清洗身份证号：去除空格，验证格式"""
        if not id_card:
            return None
        id_card = re.sub(r'\s+', '', str(id_card).strip())
        if len(id_card) < 15:
            return None
        return id_card

    @staticmethod
    def get_id_card_prefix(id_card: str) -> Optional[str]:
        """获取身份证前6位"""
        cleaned = DataCleaner.clean_id_card(id_card)
        if cleaned and len(cleaned) >= 6:
            return cleaned[:6]
        return None

    @staticmethod
    def clean_phone(phone: str) -> Optional[str]:
        """清洗电话号码：去除空格和特殊字符"""
        if not phone:
            return None
        phone = re.sub(r'[^\d]', '', str(phone).strip())
        if len(phone) < 7:
            return None
        return phone

    @staticmethod
    def get_birth_year(birthday: Any) -> Optional[int]:
        """从生日获取年份"""
        if not birthday:
            return None
        if isinstance(birthday, datetime):
            return birthday.year
        if isinstance(birthday, str) and len(birthday) >= 4:
            try:
                return int(birthday[:4])
            except ValueError:
                return None
        return None

    @staticmethod
    def build_inverted_index(patient: Dict[str, Any]) -> Dict[str, Any]:
        """构建倒排索引数据"""
        pinyin = DataCleaner.get_pinyin(patient.get('person_name', ''))
        gender = DataCleaner.clean_gender(patient.get('gender', ''))
        birthday = patient.get('birthday')
        birth_year = DataCleaner.get_birth_year(birthday)
        id_card = patient.get('identity_card_num') or patient.get('card_id')
        id_card_prefix = DataCleaner.get_id_card_prefix(id_card)

        index = {
            'pinyin_gender': f"{pinyin}_{gender}"
        }

        if birth_year:
            index['birth_year_gender'] = f"{birth_year}_{gender}"

        if id_card_prefix:
            index['id_card_prefix'] = id_card_prefix

        return index

cleaner = DataCleaner()