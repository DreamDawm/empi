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
