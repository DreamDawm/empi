# EMPI 患者主索引系统

## 项目概述

医疗患者主索引生成系统，通过身份证号码、姓名等字段生成患者唯一主索引，对相似患者进行自动或人工合并。

## 技术栈

- 后端: FastAPI + SQLAlchemy + Pydantic
- 前端: Vue 3 + Vite + Pinia + Element Plus
- 数据库: MySQL 8.0
- 缓存: Redis 7.x
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
│   ├── seed_data.sql     # 模拟数据
│   └── Dockerfile
├── frontend/             # Vue 3 前端
│   ├── src/
│   │   ├── views/        # 页面
│   │   ├── components/   # 组件
│   │   ├── stores/       # Pinia stores
│   │   └── api/          # API 调用
│   └── Dockerfile
├── docs/                 # 文档
└── docker-compose.yml    # 部署配置
```

## 设计文档

- [设计文档](./docs/superpowers/specs/2026-04-30-empi-design.md)

## 关键规则

### 测试规则
- 调试浏览器功能时，优先使用 `playwright-cli` skill
- 其次使用插件中的 `playwright`
- 不使用 `python -m playwright install chromium` 命令

### 合并规则
- 相似度 ≥ 自动合并阈值（默认85分）：自动合并
- 相似度 < 待审核显示阈值（默认60分）：不显示在待审核列表
- 两者之间：进入待审核队列

### 倒排索引
- 必填键：姓名拼音 + 性别
- 可选键：生日年份 + 性别、身份证前6位 + 性别

### 幂等处理
- 每条记录处理前检查 empi_process_log
- 合并操作前检查 empi_merge_log
- 相似度结果缓存Redis，1小时过期

## ETL配置

- **轮询间隔**：默认2小时，可配置（1-24小时）
- **立刻清洗**：Dashboard页面的"立刻增量清洗"按钮
- **全量清洗**：Dashboard页面的"立刻全量清洗"按钮（清除处理日志后重新处理）

## 前端页面

| 页面 | 路径 | 功能 |
|------|------|------|
| Dashboard | / | 统计概览、合并趋势、清洗操作 |
| 待审核 | /pending | 待审核列表，支持阈值过滤 |
| 已合并 | /merged | 已合并记录 |
| 患者 | /patients | 患者列表查询 |
| 配置 | /config | 权重配置、阈值配置、轮询间隔配置 |

## 数据库表

| 表名 | 说明 |
|------|------|
| im_patient | 源患者数据表 |
| empi_master | 主索引表 |
| empi_pending_review | 待审核队列 |
| empi_merge_log | 合并日志 |
| empi_process_log | 处理日志 |
| empi_config | 配置表 |
