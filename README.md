# EMPI 患者主索引系统

企业级患者主索引（Enterprise Master Patient Index, EMPI）系统，用于管理医疗场景下的患者身份唯一性问题。

## 功能特性

- **患者主索引生成**：基于身份证、姓名等字段生成唯一主索引
- **智能合并**：计算患者相似度，自动或人工合并重复记录
- **实时清洗**：ETL流水线处理源数据，支持增量/全量清洗
- **可视化配置**：Web界面配置权重、阈值、轮询间隔

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
│   │   │   └── stats.py    # 统计接口
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
```

### 统计接口

```
GET  /api/stats                  # 统计概览
GET  /api/stats/trend            # 合并趋势
POST /api/stats/trigger-clean   # 立刻增量清洗
POST /api/stats/trigger-full-clean # 立刻全量清洗
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

## 开发指南

### 后端启动

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
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

## License

MIT
