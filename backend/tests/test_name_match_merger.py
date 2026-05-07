import pytest
from app.services.name_match_merger import NameMatchMerger


class TestNameMatchMergerInit:
    """姓名匹配合并服务初始化测试"""

    def test_init_should_create_instance(self):
        """应该能创建 NameMatchMerger 实例"""
        merger = NameMatchMerger()
        assert merger is not None

    def test_init_should_have_data_cleaner(self):
        """应该包含 DataCleaner 实例"""
        merger = NameMatchMerger()
        assert merger.data_cleaner is not None


class TestHasValidIdCard:
    """身份证有效性检查测试"""

    def setup_method(self):
        self.merger = NameMatchMerger()

    def test_valid_18_digit_id_card(self):
        """有效的18位身份证应返回 True"""
        patient = {'identity_card_num': '110101199001011237'}
        assert self.merger.has_valid_id_card(patient) is True

    def test_valid_15_digit_id_card(self):
        """有效的15位身份证应返回 True"""
        patient = {'identity_card_num': '110101900101123'}
        assert self.merger.has_valid_id_card(patient) is True

    def test_invalid_id_card(self):
        """无效身份证应返回 False"""
        patient = {'identity_card_num': 'INVALID123'}
        assert self.merger.has_valid_id_card(patient) is False

    def test_empty_id_card(self):
        """空身份证应返回 False"""
        patient = {'identity_card_num': ''}
        assert self.merger.has_valid_id_card(patient) is False

    def test_none_id_card(self):
        """身份证字段为 None 应返回 False"""
        patient = {'identity_card_num': None}
        assert self.merger.has_valid_id_card(patient) is False

    def test_missing_id_card_field(self):
        """缺少身份证字段应返回 False"""
        patient = {}
        assert self.merger.has_valid_id_card(patient) is False

    def test_card_id_field_as_fallback(self):
        """应支持 card_id 字段作为备选"""
        patient = {'card_id': '110101199001011237'}
        assert self.merger.has_valid_id_card(patient) is True
