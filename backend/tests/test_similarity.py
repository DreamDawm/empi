import pytest
from unittest.mock import MagicMock, patch

class TestSimilarityCalculator:
    @pytest.fixture
    def calculator(self):
        with patch('app.services.similarity.redis.Redis'):
            from app.services.similarity import SimilarityCalculator
            return SimilarityCalculator()

    def test_identity_card_exact_match(self, calculator):
        patient_a = {'identity_card_num': '110101199001011234'}
        patient_b = {'identity_card_num': '110101199001011234'}
        score = calculator._similarity_identity_card(patient_a, patient_b)
        assert score == 100.0

    def test_identity_card_prefix_match(self, calculator):
        patient_a = {'identity_card_num': '110101199001011234'}
        patient_b = {'identity_card_num': '110101199009091234'}
        score = calculator._similarity_identity_card(patient_a, patient_b)
        assert score == 30.0

    def test_identity_card_no_match(self, calculator):
        patient_a = {'identity_card_num': '110101199001011234'}
        patient_b = {'identity_card_num': '210101199001011234'}
        score = calculator._similarity_identity_card(patient_a, patient_b)
        assert score == 0.0

    def test_gender_exact_match(self, calculator):
        patient_a = {'gender': 'M'}
        patient_b = {'gender': 'M'}
        score = calculator._similarity_gender(patient_a, patient_b)
        assert score == 100.0

    def test_gender_no_match(self, calculator):
        patient_a = {'gender': 'M'}
        patient_b = {'gender': 'N'}
        score = calculator._similarity_gender(patient_a, patient_b)
        assert score == 0.0

    def test_phone_exact_match(self, calculator):
        patient_a = {'phone': '13812345678'}
        patient_b = {'phone': '13812345678'}
        score = calculator._similarity_phone(patient_a, patient_b)
        assert score == 100.0

    def test_phone_prefix_match(self, calculator):
        patient_a = {'phone': '13812345678'}
        patient_b = {'phone': '13812340000'}
        score = calculator._similarity_phone(patient_a, patient_b)
        assert score == 60.0

    def test_address_exact_match(self, calculator):
        patient_a = {'location': '北京市朝阳区'}
        patient_b = {'location': '北京市朝阳区'}
        score = calculator._similarity_address(patient_a, patient_b)
        assert score == 100.0

    def test_address_no_match(self, calculator):
        patient_a = {'location': '北京市朝阳区'}
        patient_b = {'location': '上海市浦东新区'}
        score = calculator._similarity_address(patient_a, patient_b)
        assert score == 0.0

    def test_levenshtein_distance(self, calculator):
        assert calculator._levenshtein_distance('kitten', 'sitting') == 3
        assert calculator._levenshtein_distance('', 'abc') == 3
        assert calculator._levenshtein_distance('abc', 'abc') == 0
        assert calculator._levenshtein_distance('abc', 'def') == 3

    def test_common_prefix_length(self, calculator):
        assert calculator._common_prefix_length('abc', 'abc') == 3
        assert calculator._common_prefix_length('abc', 'abd') == 2
        assert calculator._common_prefix_length('abc', 'def') == 0