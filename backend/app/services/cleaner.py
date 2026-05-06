import re
from typing import Optional, Dict, Any
from pypinyin import lazy_pinyin
from datetime import datetime

# 中国省份/直辖市/自治区代码前两位映射
REGION_PREFIXES = {
    '11': '北京市', '12': '天津市', '13': '河北省', '14': '山西省',
    '15': '内蒙古', '21': '辽宁省', '22': '吉林省', '23': '黑龙江省',
    '31': '上海市', '32': '江苏省', '33': '浙江省', '34': '安徽省',
    '35': '福建省', '36': '江西省', '37': '山东省', '41': '河南省',
    '42': '湖北省', '43': '湖南省', '44': '广东省', '45': '广西壮族自治区',
    '46': '海南省', '50': '重庆市', '51': '四川省', '52': '贵州省',
    '53': '云南省', '54': '西藏自治区', '61': '陕西省', '62': '甘肃省',
    '63': '青海省', '64': '宁夏回族自治区', '65': '新疆维吾尔自治区',
    '71': '台湾省', '81': '香港特别行政区', '82': '澳门特别行政区',
}

WEIGHT_FACTORS = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]  # 18位校验码权重
CHECK_CODE = ('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2')  # 校验码映射
DAYS_IN_MONTH_COMMON = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MIN_BIRTH_YEAR = 1900
MAX_BIRTH_YEAR = 2099
MAX_CHAR_SET_THRESHOLD = 3


def validate_id_card(id_card: str) -> bool:
    """校验身份证号码格式是否合法"""
    if not id_card:
        return False
    id_card = str(id_card).strip().upper()

    if len(id_card) == 18:
        return _validate_18_digit_id_card(id_card)
    elif len(id_card) == 15:
        return _validate_15_digit_id_card(id_card)
    return False


def _validate_18_digit_id_card(id_card: str) -> bool:
    """校验18位身份证格式"""
    if not re.match(r'^\d{17}[\dX]$', id_card):
        return False

    # 1. 地区码校验 (前2位)
    region_code = id_card[:2]
    if region_code not in REGION_PREFIXES:
        return False

    # 2. 出生日期校验 (第7-14位，格式: YYYYMMDD)
    birth_date_str = id_card[6:14]
    if not _validate_birth_date(birth_date_str):
        return False

    # 3. 校验码校验 (最后一位)
    calculated_check = _calculate_18_digit_check(id_card[:17])
    if calculated_check != id_card[17]:
        return False

    return True


def _validate_15_digit_id_card(id_card: str) -> bool:
    """校验15位身份证格式"""
    if not re.match(r'^\d{15}$', id_card):
        return False

    # 1. 地区码校验 (前2位)
    region_code = id_card[:2]
    if region_code not in REGION_PREFIXES:
        return False

    # 2. 出生日期校验 (第7-12位，格式: YYMMDD，世纪码0=19xx)
    birth_date_str = '19' + id_card[6:12]
    if not _validate_birth_date(birth_date_str):
        return False

    # 3. 明显重复模式检测
    if _has_obvious_duplicate_pattern(id_card):
        return False

    return True


def _validate_birth_date(date_str: str) -> bool:
    """校验日期是否合法"""
    if not re.match(r'^\d{8}$', date_str):
        return False

    year = int(date_str[:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])

    if year < MIN_BIRTH_YEAR or year > MAX_BIRTH_YEAR:
        return False
    if month < 1 or month > 12:
        return False

    days_in_month = DAYS_IN_MONTH_COMMON[:]
    # 闰年2月
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        days_in_month[1] = 29

    if day < 1 or day > days_in_month[month - 1]:
        return False

    return True


def _calculate_18_digit_check(first_17: str) -> str:
    """计算18位身份证校验码"""
    total = sum(int(first_17[i]) * WEIGHT_FACTORS[i] for i in range(17))
    return CHECK_CODE[total % 11]


def _has_obvious_duplicate_pattern(id_card: str) -> bool:
    """检测15位身份证是否有明显的重复模式"""
    if id_card == '0' * 15:
        return True
    if len(set(id_card)) == 1:
        return True
    # 检测纯重复模式 (如 121212121212121)
    for pattern_len in [1, 2, 3, 4, 5]:
        if len(id_card) % pattern_len == 0:
            pattern = id_card[:pattern_len]
            repeated = pattern * (len(id_card) // pattern_len)
            if id_card == repeated:
                return True
    # 检测极低信息熵模式 (如 110111111111111, 只有0和1且严重偏向一个数字)
    if len(set(id_card)) <= 2:
        char_counts = {}
        for c in id_card:
            char_counts[c] = char_counts.get(c, 0) + 1
        max_count = max(char_counts.values())
        # 如果某个字符出现超过阈值，认为是重复模式
        if max_count >= MAX_CHAR_SET_THRESHOLD * 4 + 1:
            return True
    return False


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
    def validate_id_card(id_card: str) -> bool:
        """校验身份证号码格式是否合法（18位和15位）"""
        return validate_id_card(id_card)

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