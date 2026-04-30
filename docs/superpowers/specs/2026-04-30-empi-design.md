# 医疗患者主索引生成系统 (EMPI) 设计文档

## 1. 项目概述

**项目名称**: 医疗患者主索引生成系统 (EMPI - Enterprise Master Patient Index)

**核心功能**: 通过身份证号码、姓名等字段生成患者唯一主索引，对相似患者进行自动或人工合并，保证患者数据准确性和唯一性。

**目标用户**: 数据治理团队

## 2. 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy + Pydantic |
| 前端 | Vue 3 + Vite + Pinia + Element Plus |
| 数据库 | MySQL 8.0 |
| 缓存 | Redis 7.x |
| 任务调度 | APScheduler |
| 部署 | Docker + Docker Compose |

## 3. 系统架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   MySQL 患者表   │────▶│  FastAPI 后端   │────▶│   Vue 3 前端    │
│   (千万级)      │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐
            │   Redis   │ │ 处理日志表 │ │ 倒排索引  │
            │ (配置+缓存)│ │           │ │  (索引)   │
            └───────────┘ └───────────┘ └───────────┘
```

### 核心模块

| 模块 | 职责 |
|------|------|
| **ETL调度器** | 定时轮询 `data_updatetime`，拉取增量数据，触发清洗流程 |
| **数据清洗引擎** | 初始化清洗 + 增量清洗，生成标准化数据（拼音转换、大小写统一等） |
| **相似度计算引擎** | 基于配置的权重字段，计算多维度相似度 |
| **合并决策引擎** | ≥阈值自动合并，<阈值写入待审核队列 |
| **倒排索引管理** | 维护拼音+性别+生日+身份证前6位的倒排索引 |
| **主索引服务** | 管理主索引分配（雪花算法）、合并关系、双向指针 |
| **配置服务** | 管理权重配置、字段配置、阈值配置，Redis缓存 |
| **待审核队列** | 存储待人工审核的候选对，前端展示和操作 |

## 4. 数据模型

### 4.1 源数据表 (im_patient)

已有表结构，核心字段：
- `patient_id`: 源系统患者ID (主键)
- `person_name`: 患者姓名
- `card_id` / `identity_card_num`: 身份证号码
- `birthday`: 出生日期
- `gender`: 性别
- `phone`: 电话
- `location`: 住址
- `data_updatetime`: 数据更新时间（增量轮询字段）

### 4.2 主索引表 (empi_master)

```sql
create table empi_master
(
    id              bigint          not null comment '主键ID（雪花算法）' primary key,
    patient_id      varchar(50)     not null comment '源系统患者ID',
    patient_name    varchar(100)    not null comment '患者姓名',
    master_id       bigint          not null comment '主索引ID（雪花算法）',
    status          varchar(20)     not null comment '状态：NORMAL/MERGED',
    merged_to_master_id bigint      null comment '合并到的主索引ID',
    inverted_index  json            null comment '倒排索引数据',
    created_at      datetime        not null comment '创建时间',
    updated_at      datetime        not null comment '更新时间',
    unique key uk_patient_id (patient_id),
    unique key uk_master_id (master_id),
    key idx_master_id (master_id)
) comment '患者主索引表';
```

### 4.3 合并关系表 (empi_merge_log)

```sql
create table empi_merge_log
(
    id              bigint          not null auto_increment primary key,
    person_id_a     varchar(50)     not null comment '患者A的patient_id',
    person_id_b     varchar(50)     not null comment '患者B的patient_id',
    master_id       bigint          not null comment '合并后的主索引ID',
    merge_type      varchar(20)     not null comment '合并类型：AUTO/MANUAL',
    similarity_score decimal(5,2)   not null comment '相似度分数',
    merge_time      datetime        not null comment '合并时间',
    created_at      datetime        default CURRENT_TIMESTAMP,
    key idx_master_id (master_id),
    key idx_person_a (person_id_a),
    key idx_person_b (person_id_b)
) comment '患者合并日志表';
```

### 4.4 待审核队列表 (empi_pending_review)

```sql
create table empi_pending_review
(
    id              bigint          not null auto_increment primary key,
    person_id_a     varchar(50)     not null comment '患者A的patient_id',
    person_id_b     varchar(50)     not null comment '患者B的patient_id',
    similarity_score decimal(5,2)   not null comment '相似度分数',
    similarity_details json         not null comment '各字段相似度明细',
    status          varchar(20)     not null default 'PENDING' comment '状态：PENDING/RESOLVED/IGNORED',
    resolution_type varchar(20)     null comment '处理方式：MERGE/IGNORE',
    resolved_by     varchar(100)    null comment '处理人',
    resolved_at     datetime        null comment '处理时间',
    create_time     datetime        not null comment '创建时间',
    key idx_status (status),
    key idx_create_time (create_time)
) comment '待审核队列表';
```

### 4.5 处理日志表 (empi_process_log)

```sql
create table empi_process_log
(
    id              bigint          not null auto_increment primary key,
    patient_id      varchar(50)     not null comment '患者ID',
    process_type    varchar(20)     not null comment '处理类型：CLEAN/CALCULATE/MERGE/REVIEW',
    details         json            not null comment '详细日志',
    process_time    datetime        not null comment '处理时间',
    key idx_patient_id (patient_id),
    key idx_process_time (process_time)
) comment '处理日志表';
```

### 4.6 配置表 (empi_config)

```sql
create table empi_config
(
    id              bigint          not null auto_increment primary key,
    config_key      varchar(100)    not null unique comment '配置键',
    config_value    json            not null comment '配置值',
    description     varchar(500)    null comment '配置描述',
    updated_at      datetime        not null comment '更新时间'
) comment '系统配置表';
```

## 5. 相似度计算规则

### 5.1 可配置字段

| 字段 | 权重 | 评分规则 |
|------|------|----------|
| 身份证号码 | 可配置 | 完全匹配100分，前6位相同加30分 |
| 姓名 | 可配置 | 拼音完全匹配100分，拼音相似度（编辑距离）按比例计算 |
| 生日 | 可配置 | 完全匹配100分，年份匹配30分，月日匹配各20分 |
| 性别 | 可配置 | 完全匹配100分，不匹配0分 |
| 电话 | 可配置 | 完全匹配100分，前7位相同60分 |
| 地址 | 可配置 | 完全匹配100分，JSON相似度计算 |

### 5.2 评分计算

总分 = Σ(字段权重 × 字段得分) / Σ权重

### 5.3 决策规则

- **≥自动合并阈值**：自动合并（阈值可配置，默认为85）
- **<阈值**：进入待审核队列

## 6. 倒排索引设计

### 6.1 索引结构

```json
{
  "pinyin_gender": {
    "zhangsan_N": ["patient_001", "patient_002"],
    "lisi_M": ["patient_003"]
  },
  "birth_year_gender": {
    "1990_N": ["patient_001"],
    "1985_M": ["patient_003"]
  },
  "id_card_prefix": {
    "110101": ["patient_001", "patient_002"]
  }
}
```

### 6.2 索引键生成规则

- `pinyin_gender`: 姓名拼音（小写）+ "_" + 性别（M/N），必填
- `birth_year_gender`: 出生年份 + "_" + 性别，可空
- `id_card_prefix`: 身份证前6位，可空

## 7. 主索引服务

### 7.1 主索引分配流程

```
新增患者 → 查询empi_master是否存在该patient_id记录
         → 存在：直接返回已有master_id
         → 不存在：生成雪花ID，创建master记录
```

### 7.2 合并时的主索引分配

```
两个患者A、B需要合并 → 选取创建时间更早的作为主索引
                   → 更新A的master_id，B的merged_to_master_id指向A的master_id
                   → 记录合并日志
```

### 7.3 雪花ID配置

- 时间戳位数：41位（毫秒级，可使用69年）
- 机器ID位数：10位（支持1024个节点）
- 序列号位数：12位（每节点每毫秒支持4096个ID）

## 8. 增量处理流程

### 8.1 轮询机制

- 定时任务每5分钟执行一次
- 查询 `data_updatetime` > 上次处理时间的记录
- 每次处理记录数可配置（默认1000条/批）

### 8.2 处理流程（幂等设计）

```
增量轮询 → 检查empi_process_log是否已处理 → 已处理跳过
                                          → 未处理：
            ↓
数据清洗 → 标准化（拼音转换、大小写统一、去除空格）
            ↓
倒排索引查询 → 查找候选匹配记录
            ↓
相似度计算 → 计算各字段相似度 → 汇总分数
            ↓
决策判断 → ≥阈值：自动合并 → 更新empi_master → 记录empi_merge_log
         → <阈值：进入待审核队列 → 记录empi_pending_review
            ↓
记录日志 → 写入empi_process_log
```

### 8.3 幂等保证

- 每条记录处理前检查 `empi_process_log`，已处理则跳过
- 合并操作前检查 `empi_merge_log`，已存在则跳过
- 相似度结果缓存Redis，设置过期时间（1小时），重复计算直接返回

## 9. API 设计

### 9.1 配置管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/config/weights` | GET | 获取字段权重配置 |
| `/api/config/weights` | PUT | 更新字段权重配置（同步到Redis） |
| `/api/config/threshold` | GET | 获取自动合并阈值 |
| `/api/config/threshold` | PUT | 更新自动合并阈值 |

### 9.2 患者管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/patients` | GET | 分页查询患者列表 |
| `/api/patients/{id}` | GET | 获取患者详情 |
| `/api/patients/{id}/similar` | GET | 获取该患者的所有相似候选 |
| `/api/patients/{id}/master` | GET | 获取患者的主索引信息 |

### 9.3 合并管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/merge-candidates` | GET | 分页获取待审核候选列表 |
| `/api/merge` | POST | 人工合并两个患者 |
| `/api/merge/batch` | POST | 批量确认合并（前端勾选） |
| `/api/merge/{id}/ignore` | POST | 忽略该候选对 |
| `/api/merge/history` | GET | 查看合并历史 |

### 9.4 统计

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/stats` | GET | 获取统计信息（总数、已合并、待审核） |
| `/api/stats/trend` | GET | 获取趋势数据 |

## 10. 前端页面设计

### 10.1 页面列表

| 页面 | 路径 | 描述 |
|------|------|------|
| 仪表盘 | `/` | 概览统计、合并率、待审核数量 |
| 配置管理 | `/config` | 权重配置、字段选择、阈值设置 |
| 待审核列表 | `/pending` | 相似患者对列表，可合并/忽略 |
| 已合并管理 | `/merged` | 查看已合并记录、合并历史、可撤销 |
| 患者查询 | `/patients` | 输入患者信息，查看主索引和相似记录 |

### 10.2 核心交互

**待审核列表页面**:
- 显示所有待审核的相似患者对
- 每对显示：患者A信息、患者B信息、相似度分数、各字段相似度明细
- 操作按钮：合并、忽略
- 支持批量勾选后批量合并

**配置管理页面**:
- 权重配置表格：字段名、权重值（滑块）、是否参与计算（开关）
- 阈值配置：自动合并阈值输入框
- 保存后同步到Redis

## 11. 部署架构

### 11.1 Docker Compose 配置

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - MYSQL_HOST=mysql
      - REDIS_HOST=redis
    depends_on:
      - mysql
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=xxx

  redis:
    image: redis:7-alpine
```

### 11.2 环境变量

**后端环境变量**:
- `MYSQL_HOST`: MySQL地址
- `MYSQL_PORT`: MySQL端口
- `MYSQL_USER`: 用户名
- `MYSQL_PASSWORD`: 密码
- `MYSQL_DATABASE`: 数据库名
- `REDIS_HOST`: Redis地址
- `REDIS_PORT`: Redis端口

## 12. 性能优化策略

### 12.1 千万级数据优化

- 倒排索引分片存储，按拼音首字母分桶
- 批量处理，每批1000条，减少数据库IO
- Redis缓存高频访问的配置和计算结果
- 增量处理避开业务高峰期（凌晨2-6点）

### 12.2 相似度计算优化

- 必填字段不匹配则直接跳过（身份证+姓名联合索引）
- 只对倒排索引命中的候选进行细粒度计算
- 使用多进程/多线程并行计算

## 13. 数据安全

- 处理日志完整记录，支持追溯
- 合并操作需记录操作人和时间
- 支持撤销最近 N 次合并（配置可查时间范围）
- 敏感信息（身份证号）脱敏显示