import pytest
from app.services.cleaner import DataCleaner
from datetime import datetime

def test_clean_name():
    cleaner = DataCleaner()
    assert cleaner.clean_name(" 张  三 ") == "张三"
    assert cleaner.clean_name("李四") == "李四"
    assert cleaner.clean_name("") == ""

def test_get_pinyin():
    cleaner = DataCleaner()
    assert cleaner.get_pinyin("张三") == "zhangsan"
    assert cleaner.get_pinyin("李四") == "lisi"

def test_clean_gender():
    cleaner = DataCleaner()
    assert cleaner.clean_gender("男") == "M"
    assert cleaner.clean_gender("M") == "M"
    assert cleaner.clean_gender("女") == "N"
    assert cleaner.clean_gender("") == "N"

def test_clean_id_card():
    cleaner = DataCleaner()
    assert cleaner.clean_id_card("110101199001011234") == "110101199001011234"
    assert cleaner.clean_id_card("  110101199001011234  ") == "110101199001011234"
    assert cleaner.clean_id_card("123") is None

def test_get_id_card_prefix():
    cleaner = DataCleaner()
    assert cleaner.get_id_card_prefix("110101199001011234") == "110101"
    assert cleaner.get_id_card_prefix("12345") is None

def test_clean_phone():
    cleaner = DataCleaner()
    assert cleaner.clean_phone("13812345678") == "13812345678"
    assert cleaner.clean_phone(" 138-1234-5678 ") == "13812345678"
    assert cleaner.clean_phone("123") is None

def test_get_birth_year():
    cleaner = DataCleaner()
    assert cleaner.get_birth_year(datetime(1990, 1, 1)) == 1990
    assert cleaner.get_birth_year("1990-01-01") == 1990
    assert cleaner.get_birth_year(None) is None

def test_build_inverted_index():
    cleaner = DataCleaner()
    patient = {
        'patient_name': '张三',
        'gender': '男',
        'birthday': '1990-01-01',
        'identity_card_num': '110101199001011234'
    }
    index = cleaner.build_inverted_index(patient)
    assert index['pinyin_gender'] == 'zhangsan_M'
    assert 'birth_year_gender' in index
    assert 'id_card_prefix' in index