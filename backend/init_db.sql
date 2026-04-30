-- backend/init_db.sql
CREATE DATABASE IF NOT EXISTS empi_db ;

USE empi_db;

CREATE TABLE IF NOT EXISTS empi_master (
    id              BIGINT          NOT NULL COMMENT '主键ID（雪花算法）',
    patient_id      VARCHAR(50)     NOT NULL COMMENT '源系统患者ID',
    patient_name    VARCHAR(100)    NOT NULL COMMENT '患者姓名',
    master_id       BIGINT          NOT NULL COMMENT '主索引ID（雪花算法）',
    status          VARCHAR(20)     NOT NULL DEFAULT 'NORMAL' COMMENT '状态：NORMAL/MERGED',
    merged_to_master_id BIGINT      NULL COMMENT '合并到的主索引ID',
    inverted_index  JSON            NULL COMMENT '倒排索引数据',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_patient_id (patient_id),
    UNIQUE KEY uk_master_id (master_id),
    KEY idx_master_id (master_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='患者主索引表';

CREATE TABLE IF NOT EXISTS empi_merge_log (
    id              BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    person_id_a     VARCHAR(50)     NOT NULL COMMENT '患者A的patient_id',
    person_id_b     VARCHAR(50)     NOT NULL COMMENT '患者B的patient_id',
    master_id       BIGINT          NOT NULL COMMENT '合并后的主索引ID',
    merge_type      VARCHAR(20)     NOT NULL COMMENT '合并类型：AUTO/MANUAL',
    similarity_score DECIMAL(5,2)   NOT NULL COMMENT '相似度分数',
    merge_time      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    KEY idx_master_id (master_id),
    KEY idx_person_a (person_id_a),
    KEY idx_person_b (person_id_b)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='患者合并日志表';

CREATE TABLE IF NOT EXISTS empi_pending_review (
    id              BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    person_id_a     VARCHAR(50)     NOT NULL COMMENT '患者A的patient_id',
    person_id_b     VARCHAR(50)     NOT NULL COMMENT '患者B的patient_id',
    similarity_score DECIMAL(5,2)   NOT NULL COMMENT '相似度分数',
    similarity_details JSON         NOT NULL COMMENT '各字段相似度明细',
    status          VARCHAR(20)     NOT NULL DEFAULT 'PENDING' COMMENT '状态：PENDING/RESOLVED/IGNORED',
    resolution_type VARCHAR(20)     NULL COMMENT '处理方式：MERGE/IGNORE',
    resolved_by     VARCHAR(100)    NULL COMMENT '处理人',
    resolved_at     DATETIME        NULL COMMENT '处理时间',
    create_time     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_status (status),
    KEY idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='待审核队列表';

CREATE TABLE IF NOT EXISTS empi_process_log (
    id              BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    patient_id      VARCHAR(50)     NOT NULL COMMENT '患者ID',
    process_type    VARCHAR(20)     NOT NULL COMMENT '处理类型：CLEAN/CALCULATE/MERGE/REVIEW',
    details         JSON            NOT NULL COMMENT '详细日志',
    process_time    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_patient_id (patient_id),
    KEY idx_process_time (process_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='处理日志表';

CREATE TABLE IF NOT EXISTS empi_config (
    id              BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    config_key      VARCHAR(100)    NOT NULL UNIQUE COMMENT '配置键',
    config_value    JSON            NOT NULL COMMENT '配置值',
    description     VARCHAR(500)    NULL COMMENT '配置描述',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';
