# EMPI 患者主索引系统

## 项目概述

医疗患者主索引生成系统，通过身份证号码、姓名等字段生成患者唯一主索引，对相似患者进行自动或人工合并。

## 技术栈

- 后端: FastAPI + SQLAlchemy + Pydantic
- 前端: Vue 3 + Vite + Pinia + Element Plus
- 数据库: MySQL 8.0
- 缓存: Redis 7.x
- 任务调度: APScheduler
- 部署: Docker + Docker Compose

## 项目结构

```
empi/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── core/         # 核心模块（雪花算法、配置服务）
│   │   ├── services/     # 业务服务（清洗、相似度、合并）
│   │   ├── models/       # 数据模型
│   │   └── schemas/      # Pydantic schemas
│   ├── tests/
│   └── Dockerfile
├── frontend/             # Vue 3 前端
│   ├── src/
│   │   ├── views/        # 页面
│   │   ├── components/   # 组件
│   │   ├── stores/       # Pinia stores
│   │   └── api/          # API 调用
│   └── Dockerfile
├── docs/                 # 文档
│   └── superpowers/
│       └── specs/        # 设计文档
└── docker-compose.yml    # 部署配置
```

## 设计文档

- [设计文档](./docs/superpowers/specs/2026-04-30-empi-design.md)

## 关键规则

### 合并规则
- 相似度 ≥ 阈值（默认85分）：自动合并
- 相似度 < 阈值：进入待审核队列

### 倒排索引
- 必填键：姓名拼音 + 性别
- 可选键：生日年份 + 性别、身份证前6位 + 性别

### 幂等处理
- 每条记录处理前检查 empi_process_log
- 合并操作前检查 empi_merge_log
- 相似度结果缓存Redis，1小时过期