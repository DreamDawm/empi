import pytest
from app.services.cleaner import DataCleaner


class TestIdCardValidation:
    """身份证号码格式校验测试"""

    def test_valid_18_digit_id_card(self):
        """有效的18位身份证应该通过校验"""
        valid_ids = [
            '110101199001011106',  # 北京东城 (校验位6)
            '310101199001011103',  # 上海黄浦 (校验位3)
            '440301199001011103',  # 广东深圳 (校验位3)
        ]
        for id_card in valid_ids:
            result = DataCleaner.validate_id_card(id_card)
            assert result is True, f"{id_card} should be valid"

    def test_invalid_18_digit_checksum(self):
        """18位身份证校验位错误应该返回False"""
        invalid_ids = [
            '110101199001011230',  # 校验位错误
            '11010119900101123X',  # 校验位错误(X是大写但计算应为0)
        ]
        for id_card in invalid_ids:
            result = DataCleaner.validate_id_card(id_card)
            assert result is False, f"{id_card} should be invalid"

    def test_invalid_18_digit_region_code(self):
        """18位身份证地区码不合规应该返回False"""
        invalid_ids = [
            '000101199001011234',  # 地区码00不存在
            '999999199001011234',  # 地区码99不存在
        ]
        for id_card in invalid_ids:
            result = DataCleaner.validate_id_card(id_card)
            assert result is False, f"{id_card} should be invalid"

    def test_invalid_18_digit_birth_date(self):
        """18位身份证出生日期不合规应该返回False"""
        invalid_ids = [
            '110101189901011234',  # 月份00
            '110101199013011234',  # 月份13
            '110101199001321234',  # 日期32
            '110101199002291234',  # 2月30日(平年)
        ]
        for id_card in invalid_ids:
            result = DataCleaner.validate_id_card(id_card)
            assert result is False, f"{id_card} should be invalid"

    def test_leap_year_18_digit_id(self):
        """闰年2月29日应该通过"""
        # 2000年是闰年
        id_card = '11010120000229123X'  # 2000-02-29, 校验位X
        result = DataCleaner.validate_id_card(id_card)
        assert result is True

    def test_valid_15_digit_id_card(self):
        """有效的15位身份证应该通过"""
        valid_ids = [
            '110101900101123',   # 北京东城
            '310101900101123',   # 上海
        ]
        for id_card in valid_ids:
            result = DataCleaner.validate_id_card(id_card)
            assert result is True, f"{id_card} should be valid"

    def test_invalid_15_digit_obvious_duplicate(self):
        """15位身份证明显重复模式应该返回False"""
        invalid_ids = [
            '310000000000000',   # 全0
            '110111111111111',   # 连续重复
            '000000000000000',   # 全0
        ]
        for id_card in invalid_ids:
            result = DataCleaner.validate_id_card(id_card)
            assert result is False, f"{id_card} should be invalid"

    def test_15_digit_has_valid_format(self):
        """15位身份证应满足格式: 6位地区码 + 6位生日(YYMMDD) + 3位顺序码"""
        assert DataCleaner.validate_id_card('000000900101123') is False  # 无效地区码
        assert DataCleaner.validate_id_card('110101990000123') is False  # 无效日期(990000=99年00月)

    def test_validate_id_card_returns_false_for_invalid_input(self):
        """空输入和None应该返回False"""
        assert DataCleaner.validate_id_card(None) is False
        assert DataCleaner.validate_id_card('') is False
        assert DataCleaner.validate_id_card('   ') is False