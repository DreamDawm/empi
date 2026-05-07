# EMPI 患者主索引系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/vue-3.x-green.svg)](https://vuejs.org/)

企业级患者主索引（Enterprise Master Patient Index, EMPI）系统，用于管理医疗场景下的患者身份唯一性问题。

## 功能特性

- **患者主索引生成**：基于身份证、姓名等字段生成唯一主索引
- **智能合并**：计算患者相似度，自动或人工合并重复记录
- **实时清洗**：ETL流水线处理源数据，支持增量/全量清洗
- **可视化配置**：Web界面配置权重、阈值、轮询间隔
- **姓名匹配合并**：支持基于姓名匹配的特殊合并策略
- **实时日志流**：SSE实时推送清洗日志

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy + Pydantic |
| 前端 | Vue 3 + Vite + Pinia + Element Plus |
| 数据库 | MySQL 8.0 |
| 缓存 | Redis 7.x |
| 部署 | Docker + Docker Compose |

## 快速开始

### 环境要求

- Docker Desktop
- MySQL 8.0 (或使用Docker部署)
- Redis 7.x (或使用Docker部署)

### 启动服务

```bash
# 克隆项目
git clone <repository-url>
cd empi

# 启动服务（使用外部MySQL/Redis）
docker-compose up -d --build

# 访问前端
open http://localhost:3000
```

### 环境变量配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| MYSQL_HOST | host.docker.internal | MySQL地址 |
| MYSQL_PORT | 3306 | MySQL端口 |
| MYSQL_USER | root | 用户名 |
| MYSQL_PASSWORD | 123456 | 密码 |
| MYSQL_DATABASE | empi_db | 数据库名 |
| REDIS_HOST | host.docker.internal | Redis地址 |
| REDIS_PORT | 6379 | Redis端口 |

### 初始化数据

```bash
# 在MySQL中执行建表和数据初始化
mysql -h <MYSQL_HOST> -u root -p < backend/seed_data.sql
```

## 项目结构

```
empi/
├── backend/
│   ├── app/
│   │   ├── api/           # API路由
│   │   │   ├── config.py  # 配置接口
│   │   │   ├── merge.py   # 合并接口
│   │   │   ├── patients.py # 患者接口
│   │   │   └── stats.py   # 统计接口
│   │   ├── core/
│   │   │   ├── config.py  # 配置管理
│   │   │   └── snowflake.py # 雪花算法
│   │   ├── services/
│   │   │   ├── cleaner.py      # 数据清洗
│   │   │   ├── similarity.py   # 相似度计算
│   │   │   ├── merger.py       # 合并决策
│   │   │   ├── etl.py          # ETL调度
│   │   │   └── inverted_index.py # 倒排索引
│   │   └── models/        # SQLAlchemy模型
│   └── seed_data.sql      # 模拟数据
├── frontend/
│   └── src/
│       ├── views/         # 页面组件
│       │   ├── Dashboard.vue # 首页
│       │   ├── Pending.vue   # 待审核
│       │   ├── Merged.vue    # 已合并
│       │   ├── Patients.vue  # 患者列表
│       │   └── Config.vue    # 配置页
│       └── api/            # API调用
├── docs/                  # 设计文档
└── docker-compose.yml    # 容器编排
```

## API接口

基础 URL: `http://localhost:8000`

API 文档地址: http://localhost:8000/docs (Swagger UI)

### 配置接口

```
GET  /api/config/weights          # 获取字段权重
PUT  /api/config/weights          # 更新权重
GET  /api/config/threshold        # 获取自动合并阈值
PUT  /api/config/threshold        # 更新阈值
GET  /api/config/pending-threshold   # 获取待审核显示阈值
PUT  /api/config/pending-threshold   # 更新待审核阈值
GET  /api/config/poll-interval    # 获取轮询间隔
PUT  /api/config/poll-interval     # 更新轮询间隔
GET  /api/config/patient-fields   # 获取患者表字段列表
```

### 合并接口

```
GET  /api/merge/candidates       # 待审核列表 (支持min_score过滤)
POST /api/merge                  # 手动合并
POST /api/merge/{id}/ignore     # 忽略候选
GET  /api/merge/history          # 合并历史
```

### 患者接口

```
GET  /api/patients               # 患者列表
GET  /api/patients/{id}         # 患者详情
GET  /api/patients/{id}/similar # 相似患者
GET  /api/patients/{id}/master  # 患者所属主索引信息
```

### 统计接口

```
GET  /api/stats                  # 统计概览
GET  /api/stats/trend            # 合并趋势
POST /api/stats/trigger-clean   # 立刻增量清洗（同步）
POST /api/stats/trigger-clean-async # 立刻增量清洗（异步）
POST /api/stats/trigger-full-clean # 立刻全量清洗（同步）
POST /api/stats/trigger-full-clean-async # 立刻全量清洗（异步）
GET  /api/stats/logs/stream     # SSE实时日志流
POST /api/stats/admin/clear-processed-cache # 清除已处理缓存
POST /api/stats/admin/add-card-id-column # 添加card_id列
```

## 配置说明

### 字段权重

| 字段 | 默认权重 | 说明 |
|------|----------|------|
| identity_card | 30 | 身份证号码 |
| name | 30 | 姓名（拼音相似度） |
| birthday | 20 | 生日 |
| gender | 5 | 性别 |
| phone | 10 | 电话 |
| address | 5 | 地址 |

### 阈值配置

| 阈值 | 默认值 | 说明 |
|------|--------|------|
| 自动合并阈值 | 85 | ≥此分数自动合并 |
| 待审核显示阈值 | 60 | <此分数不显示 |

### ETL配置

| 配置 | 默认值 | 说明 |
|------|--------|------|
| 轮询间隔 | 2小时 | 自动清洗间隔 |

## 数据库表

| 表名 | 说明 |
|------|------|
| im_patient | 源患者数据表 |
| empi_master | 主索引表 |
| empi_pending_review | 待审核队列 |
| empi_merge_log | 合并日志 |
| empi_process_log | 处理日志 |
| empi_config | 配置表 |

## ETL清洗任务

**直接运行脚本（推荐，方便调试）：**

```bash
cd backend

# 增量清洗 - 从上次处理位置继续
python run_incremental_clean.py --batch-size 3000

# 全量清洗 - 清空所有处理后重新处理
python run_full_clean_direct.py --batch-size 3000
```

**通过API接口：**
- **轮询间隔**：默认2小时，可配置（1-24小时）
- **立刻清洗**：Dashboard页面的"立刻增量清洗"按钮
- **全量清洗**：Dashboard页面的"立刻全量清洗"按钮

## 前端页面

| 页面 | 路径 | 功能 |
|------|------|------|
| Dashboard | / | 统计概览、合并趋势、清洗操作 |
| 待审核 | /pending | 待审核列表，支持阈值过滤 |
| 已合并 | /merged | 已合并记录 |
| 患者 | /patients | 患者列表查询 |
| 配置 | /config | 权重配置、阈值配置、轮询间隔配置 |

## 开发指南

### 后端启动

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 构建镜像

```bash
docker-compose build
```

## 合并规则

- 相似度 ≥ 自动合并阈值（默认85分）：自动合并
- 相似度 < 待审核显示阈值（默认60分）：不显示在待审核列表
- 两者之间：进入待审核队列

## 倒排索引

- 必填键：姓名拼音 + 性别
- 可选键：生日年份 + 性别、身份证前6位 + 性别

## 幂等处理

- 每条记录处理前检查 empi_process_log
- 合并操作前检查 empi_merge_log
- 相似度结果缓存Redis，1小时过期

## License

MIT
