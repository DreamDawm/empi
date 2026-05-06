import pytest
from unittest.mock import MagicMock, patch
from app.services.merger import MergeDecisionEngine
from app.services.cleaner import DataCleaner


class TestDirectMergeDecision:
    """身份证+姓名相同直接合并测试"""

    def setup_method(self):
        self.engine = MergeDecisionEngine()

    def test_same_id_and_name_pinyin_should_direct_merge(self):
        """身份证和姓名拼音都相同应该直接合并"""
        patient_a = {
            'patient_id': 'P001',
            'patient_name': '张三',
            'identity_card_num': '110101199001011234',
            'gender': 'M',
        }
        patient_b = {
            'patient_id': 'P002',
            'patient_name': '张三',  # 同名
            'identity_card_num': '110101199001011234',  # 同身份证
            'gender': 'F',  # 性别不同不影响直接合并
        }

        result = self.engine._is_direct_merge_eligible(patient_a, patient_b)
        assert result is True

    def test_different_id_same_name_should_not_direct_merge(self):
        """身份证不同但姓名相同不应该直接合并"""
        patient_a = {
            'patient_id': 'P001',
            'patient_name': '张三',
            'identity_card_num': '110101199001011234',
        }
        patient_b = {
            'patient_id': 'P002',
            'patient_name': '张三',
            'identity_card_num': '110101199001011235',  # 最后一位不同
        }

        result = self.engine._is_direct_merge_eligible(patient_a, patient_b)
        assert result is False

    def test_same_id_different_name_should_not_direct_merge(self):
        """身份证相同但姓名不同不应该直接合并"""
        patient_a = {
            'patient_id': 'P001',
            'patient_name': '张三',
            'identity_card_num': '110101199001011234',
        }
        patient_b = {
            'patient_id': 'P002',
            'patient_name': '李四',  # 不同名
            'identity_card_num': '110101199001011234',  # 身份证相同
        }

        result = self.engine._is_direct_merge_eligible(patient_a, patient_b)
        assert result is False

    def test_invalid_id_card_should_not_direct_merge(self):
        """无效身份证不应该触发直接合并"""
        patient_a = {
            'patient_id': 'P001',
            'patient_name': '张三',
            'identity_card_num': 'INVALID123',
        }
        patient_b = {
            'patient_id': 'P002',
            'patient_name': '张三',
            'identity_card_num': 'INVALID123',
        }

        result = self.engine._is_direct_merge_eligible(patient_a, patient_b)
        assert result is False

    def test_decide_returns_direct_merge_for_same_id_and_name(self):
        """decide()方法对同名同身份证应返回DIRECT_MERGE"""
        patient_a = {
            'patient_id': 'P001',
            'patient_name': '张三',
            'identity_card_num': '110101199001011234',
            'gender': 'M',
        }
        patient_b = {
            'patient_id': 'P002',
            'patient_name': '张三',
            'identity_card_num': '110101199001011234',
            'gender': 'F',
        }

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch.object(self.engine, 'redis_client') as mock_redis:
            mock_redis.get.return_value = None

            decision, score = self.engine.decide(mock_db, patient_a, patient_b, {}, 85.0)

        assert decision == 'DIRECT_MERGE'
        assert score == 100.0

    def test_name_with_whitespace_and_case_should_still_match(self):
        """姓名有空格或大小写不同但拼音相同时应能直接合并"""
        patient_a = {
            'patient_id': 'P001',
            'patient_name': '张  三',  # 有空格
            'identity_card_num': '110101199001011234',
        }
        patient_b = {
            'patient_id': 'P002',
            'patient_name': '张三',  # 无空格
            'identity_card_num': '110101199001011234',
        }

        result = self.engine._is_direct_merge_eligible(patient_a, patient_b)
        assert result is True  # 清洗后拼音都是zhangsan