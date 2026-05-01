-- Migration: Add inverted index columns to empi_master
-- This is for existing databases that need the new index columns

ALTER TABLE empi_master
    ADD COLUMN pinyin_gender_index VARCHAR(100) NULL COMMENT '姓名拼音+性别预索引' AFTER inverted_index,
    ADD COLUMN birth_year_gender_index VARCHAR(50) NULL COMMENT '出生年份+性别预索引' AFTER pinyin_gender_index,
    ADD COLUMN id_card_prefix_index VARCHAR(20) NULL COMMENT '身份证前6位预索引' AFTER birth_year_gender_index,
    ADD INDEX idx_pinyin_gender (pinyin_gender_index),
    ADD INDEX idx_birth_year_gender (birth_year_gender_index),
    ADD INDEX idx_id_card_prefix (id_card_prefix_index);