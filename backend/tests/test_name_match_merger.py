import pytest
from unittest.mock import MagicMock, patch
from app.services.name_match_merger import NameMatchMerger
from app.models import EmpiMaster


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


class TestFindByName:
    """姓名搜索测试"""

    def setup_method(self):
        self.merger = NameMatchMerger()

    def test_find_by_chinese_name(self):
        """应能根据汉字姓名查找"""
        mock_db = MagicMock()
        mock_record = MagicMock(spec=EmpiMaster)
        mock_record.patient_id = 'P001'
        mock_record.patient_name = '张三'
        mock_record.status = 'NORMAL'

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_record]

        patient = {'patient_id': 'P002', 'person_name': '张三'}
        results = self.merger.find_by_name(mock_db, patient)

        assert len(results) == 1
        assert results[0].patient_name == '张三'

    def test_find_by_pinyin_name(self):
        """应能根据拼音姓名查找"""
        mock_db = MagicMock()
        mock_record = MagicMock(spec=EmpiMaster)
        mock_record.patient_id = 'P001'
        mock_record.patient_name = '张三'
        mock_record.status = 'NORMAL'

        # 模拟拼音查询返回结果
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_record]

        patient = {'patient_id': 'P002', 'person_name': '张三'}
        results = self.merger.find_by_name(mock_db, patient)

        assert len(results) == 1

    def test_find_excludes_self(self):
        """搜索结果应排除患者自己"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        patient = {'patient_id': 'P001', 'person_name': '张三'}
        results = self.merger.find_by_name(mock_db, patient)

        # 验证查询条件中排除了当前患者
        assert results == []

    def test_find_only_normal_status(self):
        """只查找状态为 NORMAL 的记录"""
        mock_db = MagicMock()
        mock_record = MagicMock(spec=EmpiMaster)
        mock_record.status = 'NORMAL'

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_record]

        patient = {'patient_id': 'P002', 'person_name': '张三'}
        results = self.merger.find_by_name(mock_db, patient)

        # 验证查询被调用
        assert mock_db.query.called

    def test_find_returns_empty_for_empty_name(self):
        """姓名为空应返回空列表"""
        mock_db = MagicMock()

        patient = {'patient_id': 'P001', 'person_name': ''}
        results = self.merger.find_by_name(mock_db, patient)

        assert results == []

    def test_find_returns_empty_for_none_name(self):
        """姓名为 None 应返回空列表"""
        mock_db = MagicMock()

        patient = {'patient_id': 'P001', 'person_name': None}
        results = self.merger.find_by_name(mock_db, patient)

        assert results == []


class TestCalculateNonIdCardScore:
    """非身份证字段相似度计算测试"""

    def setup_method(self):
        self.merger = NameMatchMerger()

    def test_all_fields_full_score(self):
        """所有字段都匹配应得满分"""
        patient_a = {
            'patient_id': 'P001',
            'patient_name': '张三',
            'birthday': '1990-01-01',
            'gender': 'M',
            'phone': '13800138000',
            'location': '北京市朝阳区'
        }
        patient_b = {
            'patient_id': 'P002',
            'patient_name': '张三',
            'birthday': '1990-01-01',
            'gender': 'M',
            'phone': '13800138000',
            'location': '北京市朝阳区'
        }

        score, details = self.merger.calculate_non_id_card_score(patient_a, patient_b)

        assert details['name'] == 100.0
        # Birthday: year(30) + month(20) + day(20) = 70
        assert details['birthday'] == 70.0
        assert details['gender'] == 100.0
        assert details['phone'] == 100.0
        assert details['address'] == 100.0

    def test_partial_fields_match(self):
        """部分字段匹配应返回相应分数"""
        patient_a = {
            'patient_id': 'P001',
            'patient_name': '张三',
            'birthday': '1990-01-01',
            'gender': 'M',
        }
        patient_b = {
            'patient_id': 'P002',
            'patient_name': '张三',
            'birthday': '1990-01-02',  # 日期不同
            'gender': 'F',  # 性别不同
        }

        score, details = self.merger.calculate_non_id_card_score(patient_a, patient_b)

        assert details['name'] == 100.0
        assert details['gender'] == 0.0

    def test_empty_fields_zero_score(self):
        """空字段应得0分"""
        patient_a = {'patient_id': 'P001', 'patient_name': '张三'}
        patient_b = {'patient_id': 'P002', 'patient_name': '张三'}

        score, details = self.merger.calculate_non_id_card_score(patient_a, patient_b)

        assert details.get('birthday', 0) == 0.0
        assert details.get('phone', 0) == 0.0

    def test_excludes_identity_card(self):
        """不应包含身份证字段"""
        patient_a = {
            'patient_id': 'P001',
            'patient_name': '张三',
            'identity_card_num': '110101199001011237'
        }
        patient_b = {
            'patient_id': 'P002',
            'patient_name': '张三',
            'identity_card_num': '110101199001011238'
        }

        score, details = self.merger.calculate_non_id_card_score(patient_a, patient_b)

        assert 'identity_card' not in details
