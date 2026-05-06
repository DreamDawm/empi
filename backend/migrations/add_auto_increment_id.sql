-- 为 im_patient 表添加自增主键 id
-- 原 patient_id 改为普通唯一索引
-- 目的：将增量检测的游标从 patient_id（业务ID）改为自增 id，避免业务ID不连续导致漏检

-- Step 1: 添加自增 id 列（已有 PRIMARY KEY on patient_id，AUTO_INCREMENT 可正常工作）
ALTER TABLE im_patient ADD COLUMN id BIGINT NOT NULL AUTO_INCREMENT FIRST;

-- Step 2: 替换主键 — 删除旧主键(patient_id)，添加新主键(id)（必须同一条语句，否则报错）
ALTER TABLE im_patient DROP PRIMARY KEY, ADD PRIMARY KEY (id);

-- Step 3: 为原 patient_id 添加唯一索引（保证业务唯一性）
CREATE UNIQUE INDEX uk_patient_id ON im_patient(patient_id);
