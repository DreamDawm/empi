# EMPI 患者主索引系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的EMPI患者主索引生成系统，包括后端API、前端页面、Docker部署

**Architecture:** 采用分层架构，后端FastAPI处理业务逻辑，前端Vue3展示，MySQL存储数据，Redis缓存配置和计算结果。倒排索引加速相似患者查询，雪花算法生成唯一主索引。

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic / Vue 3 + Vite + Pinia + Element Plus / MySQL 8.0 / Redis 7.x / APScheduler / Docker

---

## 1. 项目结构创建

**Files:**
- Create: `backend/`
- Create: `backend/app/`
- Create: `backend/app/api/`
- Create: `backend/app/core/`
- Create: `backend/app/services/`
- Create: `backend/app/models/`
- Create: `backend/app/schemas/`
- Create: `backend/tests/`
- Create: `frontend/src/`
- Create: `frontend/src/views/`
- Create: `frontend/src/components/`
- Create: `frontend/src/stores/`
- Create: `frontend/src/api/`
- Create: `docs/superpowers/plans/`

- [ ] **Step 1: 创建项目目录结构**

```bash
mkdir -p backend/app/api backend/app/core backend/app/services backend/app/models backend/app/schemas backend/tests
mkdir -p frontend/src/views frontend/src/components frontend/src/stores frontend/src/api
mkdir -p docs/superpowers/plans
```

- [ ] **Step 2: 创建后端 requirements.txt**

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
pymysql==1.1.0
redis==5.0.1
pydantic==2.5.3
pydantic-settings==2.1.0
apscheduler==3.10.4
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pypinyin==0.50.0
python-multipart==0.0.6
httpx==0.26.0
pytest==7.4.4
pytest-asyncio==0.23.3
```

- [ ] **Step 3: 创建前端 package.json**

```json
{
  "name": "empi-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.15",
    "vue-router": "^4.2.5",
    "pinia": "^2.1.7",
    "element-plus": "^2.5.4",
    "axios": "^1.6.5"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.3",
    "vite": "^5.0.11"
  }
}
```

---

## 2. 数据库表结构创建

**Files:**
- Create: `backend/app/models/base.py` - SQLAlchemy基础模型
- Create: `backend/app/models/master.py` - 主索引相关模型
- Create: `backend/app/models/config.py` - 配置相关模型
- Create: `backend/app/models/log.py` - 日志相关模型
- Create: `backend/init_db.sql` - 数据库初始化SQL

- [ ] **Step 1: 创建SQLAlchemy基础模型**

```python
# backend/app/models/base.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: 创建主索引表模型**

```python
# backend/app/models/master.py
from sqlalchemy import Column, BigInteger, String, DateTime, Numeric, JSON, Index
from sqlalchemy.sql import func
from app.models.base import Base

class EmpiMaster(Base):
    __tablename__ = 'empi_master'

    id = Column(BigInteger, primary_key=True, comment='主键ID（雪花算法）')
    patient_id = Column(String(50), nullable=False, unique=True, comment='源系统患者ID')
    patient_name = Column(String(100), nullable=False, comment='患者姓名')
    master_id = Column(BigInteger, nullable=False, unique=True, comment='主索引ID（雪花算法）')
    status = Column(String(20), nullable=False, default='NORMAL', comment='状态：NORMAL/MERGED')
    merged_to_master_id = Column(BigInteger, nullable=True, comment='合并到的主索引ID')
    inverted_index = Column(JSON, nullable=True, comment='倒排索引数据')
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_master_id', 'master_id'),
    )
```

- [ ] **Step 3: 创建配置表模型**

```python
# backend/app/models/config.py
from sqlalchemy import Column, BigInteger, String, DateTime, JSON
from sqlalchemy.sql import func
from app.models.base import Base

class EmpiConfig(Base):
    __tablename__ = 'empi_config'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    config_key = Column(String(100), nullable=False, unique=True)
    config_value = Column(JSON, nullable=False)
    description = Column(String(500), nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 4: 创建日志表模型**

```python
# backend/app/models/log.py
from sqlalchemy import Column, BigInteger, String, DateTime, Numeric, JSON, Index
from sqlalchemy.sql import func
from app.models.base import Base

class EmpiMergeLog(Base):
    __tablename__ = 'empi_merge_log'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    person_id_a = Column(String(50), nullable=False)
    person_id_b = Column(String(50), nullable=False)
    master_id = Column(BigInteger, nullable=False)
    merge_type = Column(String(20), nullable=False, comment='AUTO/MANUAL')
    similarity_score = Column(Numeric(5,2), nullable=False)
    merge_time = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index('idx_ml_master_id', 'master_id'),
        Index('idx_ml_person_a', 'person_id_a'),
        Index('idx_ml_person_b', 'person_id_b'),
    )

class EmpiPendingReview(Base):
    __tablename__ = 'empi_pending_review'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    person_id_a = Column(String(50), nullable=False)
    person_id_b = Column(String(50), nullable=False)
    similarity_score = Column(Numeric(5,2), nullable=False)
    similarity_details = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default='PENDING')
    resolution_type = Column(String(20), nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index('idx_pr_status', 'status'),
        Index('idx_pr_create_time', 'create_time'),
    )

class EmpiProcessLog(Base):
    __tablename__ = 'empi_process_log'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    patient_id = Column(String(50), nullable=False)
    process_type = Column(String(20), nullable=False, comment='CLEAN/CALCULATE/MERGE/REVIEW')
    details = Column(JSON, nullable=False)
    process_time = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index('idx_pl_patient_id', 'patient_id'),
        Index('idx_pl_process_time', 'process_time'),
    )
```

- [ ] **Step 5: 创建数据库初始化SQL**

```sql
-- backend/init_db.sql
CREATE DATABASE IF NOT EXISTS empi_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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
```

- [ ] **Step 6: 创建模型模块导出**

```python
# backend/app/models/__init__.py
from app.models.base import Base, get_db, engine
from app.models.master import EmpiMaster
from app.models.config import EmpiConfig
from app.models.log import EmpiMergeLog, EmpiPendingReview, EmpiProcessLog

__all__ = [
    'Base', 'get_db', 'engine',
    'EmpiMaster', 'EmpiConfig',
    'EmpiMergeLog', 'EmpiPendingReview', 'EmpiProcessLog',
]
```

---

## 3. 核心配置模块

**Files:**
- Create: `backend/app/core/config.py` - 应用配置
- Create: `backend/app/core/snowflake.py` - 雪花算法实现

- [ ] **Step 1: 创建应用配置**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "empi_db"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # App
    APP_NAME: str = "EMPI System"
    DEBUG: bool = False

    # Snowflake
    SNOWFLAKE_WORKER_ID: int = 1

    # ETL
    ETL_BATCH_SIZE: int = 1000
    ETL_INTERVAL_MINUTES: int = 5

    # Merge threshold
    DEFAULT_MERGE_THRESHOLD: float = 85.0

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

- [ ] **Step 2: 创建雪花算法实现**

```python
# backend/app/core/snowflake.py
import time
import threading
from app.core.config import settings

class SnowflakeIdGenerator:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.worker_id = settings.SNOWFLAKE_WORKER_ID
        self.worker_id_bits = 10
        self.sequence_bits = 12
        self.worker_id_shift = self.sequence_bits
        self.timestamp_left_shift = self.worker_id_bits + self.sequence_bits
        self.sequence_mask = -1 ^ (-1 << self.sequence_bits)
        self.last_timestamp = -1
        self.sequence = 0

    def _current_millis(self) -> int:
        return int(time.time() * 1000)

    def next_id(self) -> int:
        timestamp = self._current_millis()

        if timestamp < self.last_timestamp:
            raise ValueError(f"Clock moved backwards. Refusing to generate id for {self.last_timestamp - timestamp} milliseconds")

        if timestamp == self.last_timestamp:
            self.sequence = (self.sequence + 1) & self.sequence_mask
            if self.sequence == 0:
                timestamp = self._wait_until_next_millis(timestamp)
        else:
            self.sequence = 0

        self.last_timestamp = timestamp

        return ((timestamp - 1700000000000) << self.timestamp_left_shift) | \
               (self.worker_id << self.worker_id_shift) | \
               self.sequence

    def _wait_until_next_millis(self, last_timestamp: int) -> int:
        timestamp = self._current_millis()
        while timestamp <= last_timestamp:
            timestamp = self._current_millis()
        return timestamp

def get_snowflake_generator() -> SnowflakeIdGenerator:
    return SnowflakeIdGenerator()
```

- [ ] **Step 3: 创建核心模块导出**

```python
# backend/app/core/__init__.py
from app.core.config import settings
from app.core.snowflake import get_snowflake_generator, SnowflakeIdGenerator

__all__ = ['settings', 'get_snowflake_generator', 'SnowflakeIdGenerator']
```

---

## 4. 相似度计算服务

**Files:**
- Create: `backend/app/services/cleaner.py` - 数据清洗服务
- Create: `backend/app/services/similarity.py` - 相似度计算服务
- Create: `backend/app/services/merger.py` - 合并决策服务

- [ ] **Step 1: 创建数据清洗服务**

```python
# backend/app/services/cleaner.py
import re
from typing import Optional, Dict, Any
from pypinyin import lazy_pinyin

class DataCleaner:
    @staticmethod
    def clean_name(name: str) -> str:
        """清洗姓名：去除空格、统一大小写"""
        if not name:
            return ""
        name = re.sub(r'\s+', '', name)
        return name.strip()

    @staticmethod
    def get_pinyin(name: str) -> str:
        """获取姓名拼音（小写）"""
        if not name:
            return ""
        cleaned = DataCleaner.clean_name(name)
        pinyin_list = lazy_pinyin(cleaned)
        return ''.join(p).lower()

    @staticmethod
    def clean_gender(gender: str) -> str:
        """清洗性别：统一为M/N"""
        if not gender:
            return "N"
        gender = str(gender).strip().upper()
        if gender in ['男', 'M', 'MALE']:
            return 'M'
        return 'N'

    @staticmethod
    def clean_id_card(id_card: str) -> Optional[str]:
        """清洗身份证号：去除空格，验证格式"""
        if not id_card:
            return None
        id_card = re.sub(r'\s+', '', str(id_card).strip())
        if len(id_card) < 15:
            return None
        return id_card

    @staticmethod
    def get_id_card_prefix(id_card: str) -> Optional[str]:
        """获取身份证前6位"""
        cleaned = DataCleaner.clean_id_card(id_card)
        if cleaned and len(cleaned) >= 6:
            return cleaned[:6]
        return None

    @staticmethod
    def clean_phone(phone: str) -> Optional[str]:
        """清洗电话号码：去除空格和特殊字符"""
        if not phone:
            return None
        phone = re.sub(r'[^\d]', '', str(phone).strip())
        if len(phone) < 7:
            return None
        return phone

    @staticmethod
    def get_birth_year(birthday: Any) -> Optional[int]:
        """从生日获取年份"""
        if not birthday:
            return None
        if isinstance(birthday, datetime):
            return birthday.year
        if isinstance(birthday, str) and len(birthday) >= 4:
            try:
                return int(birthday[:4])
            except ValueError:
                return None
        return None

    @staticmethod
    def build_inverted_index(patient: Dict[str, Any]) -> Dict[str, Any]:
        """构建倒排索引数据"""
        pinyin = DataCleaner.get_pinyin(patient.get('patient_name', ''))
        gender = DataCleaner.clean_gender(patient.get('gender', ''))
        birthday = patient.get('birthday')
        birth_year = DataCleaner.get_birth_year(birthday)
        id_card = patient.get('identity_card_num') or patient.get('card_id')
        id_card_prefix = DataCleaner.get_id_card_prefix(id_card)

        index = {
            'pinyin_gender': f"{pinyin}_{gender}"
        }

        if birth_year:
            index['birth_year_gender'] = f"{birth_year}_{gender}"

        if id_card_prefix:
            index['id_card_prefix'] = id_card_prefix

        return index

cleaner = DataCleaner()
```

- [ ] **Step 2: 创建相似度计算服务**

```python
# backend/app/services/similarity.py
from typing import Dict, Any, Optional
from app.core.config import settings
import redis
import json

class SimilarityCalculator:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )

    def calculate(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any], weights: Dict[str, float]) -> float:
        """计算两个患者之间的相似度"""
        cache_key = self._get_cache_key(patient_a, patient_b)
        cached = self.redis_client.get(cache_key)
        if cached:
            return float(cached)

        scores = {}
        total_weight = 0

        for field, weight in weights.items():
            if weight <= 0:
                continue
            total_weight += weight
            score = self._calculate_field_similarity(field, patient_a, patient_b)
            scores[field] = score * weight

        if total_weight == 0:
            final_score = 0
        else:
            final_score = sum(scores.values()) / total_weight

        self.redis_client.setex(cache_key, 3600, str(final_score))
        return final_score

    def _calculate_field_similarity(self, field: str, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """计算单个字段的相似度"""
        methods = {
            'identity_card': self._similarity_identity_card,
            'name': self._similarity_name,
            'birthday': self._similarity_birthday,
            'gender': self._similarity_gender,
            'phone': self._similarity_phone,
            'address': self._similarity_address,
        }
        method = methods.get(field, lambda a, b: 0.0)
        return method(patient_a, patient_b)

    def _similarity_identity_card(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """身份证相似度：完全匹配100，前6位相同30"""
        id_a = (patient_a.get('identity_card_num') or patient_a.get('card_id') or '').strip()
        id_b = (patient_b.get('identity_card_num') or patient_b.get('card_id') or '').strip()
        if not id_a or not id_b:
            return 0.0
        if id_a == id_b:
            return 100.0
        if len(id_a) >= 6 and len(id_b) >= 6 and id_a[:6] == id_b[:6]:
            return 30.0
        return 0.0

    def _similarity_name(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """姓名相似度：拼音完全匹配100，拼音编辑距离按比例"""
        from app.services.cleaner import DataCleaner
        name_a = DataCleaner.get_pinyin(patient_a.get('patient_name', ''))
        name_b = DataCleaner.get_pinyin(patient_b.get('patient_name', ''))
        if not name_a or not name_b:
            return 0.0
        if name_a == name_b:
            return 100.0
        distance = self._levenshtein_distance(name_a, name_b)
        max_len = max(len(name_a), len(name_b))
        if max_len == 0:
            return 0.0
        return max(0.0, (1 - distance / max_len) * 100)

    def _similarity_birthday(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """生日相似度：完全匹配100，年份匹配30，月日匹配各20"""
        from app.services.cleaner import DataCleaner
        birth_a = patient_a.get('birthday')
        birth_b = patient_b.get('birthday')
        year_a = DataCleaner.get_birth_year(birth_a)
        year_b = DataCleaner.get_birth_year(birth_b)

        if not year_a or not year_b:
            return 0.0

        if year_a == year_b:
            year_score = 30
        else:
            return 0.0

        month_a = self._get_month(birth_a)
        month_b = self._get_month(birth_b)
        day_a = self._get_day(birth_a)
        day_b = self._get_day(birth_b)

        month_day_score = 0
        if month_a and month_b and month_a == month_b:
            month_day_score += 20
        if day_a and day_b and day_a == day_b:
            month_day_score += 20

        return year_score + month_day_score

    def _get_month(self, birthday) -> Optional[int]:
        if not birthday:
            return None
        from datetime import datetime
        if isinstance(birthday, datetime):
            return birthday.month
        if isinstance(birthday, str) and len(birthday) >= 7:
            try:
                return int(birthday[5:7])
            except ValueError:
                return None
        return None

    def _get_day(self, birthday) -> Optional[int]:
        if not birthday:
            return None
        from datetime import datetime
        if isinstance(birthday, datetime):
            return birthday.day
        if isinstance(birthday, str) and len(birthday) >= 10:
            try:
                return int(birthday[8:10])
            except ValueError:
                return None
        return None

    def _similarity_gender(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """性别相似度：完全匹配100，不匹配0"""
        from app.services.cleaner import DataCleaner
        gender_a = DataCleaner.clean_gender(patient_a.get('gender', ''))
        gender_b = DataCleaner.clean_gender(patient_b.get('gender', ''))
        if not gender_a or not gender_b:
            return 0.0
        return 100.0 if gender_a == gender_b else 0.0

    def _similarity_phone(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """电话相似度：完全匹配100，前7位相同60"""
        from app.services.cleaner import DataCleaner
        phone_a = DataCleaner.clean_phone(patient_a.get('phone', ''))
        phone_b = DataCleaner.clean_phone(patient_b.get('phone', ''))
        if not phone_a or not phone_b:
            return 0.0
        if phone_a == phone_b:
            return 100.0
        if len(phone_a) >= 7 and len(phone_b) >= 7 and phone_a[:7] == phone_b[:7]:
            return 60.0
        return 0.0

    def _similarity_address(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
        """地址相似度：完全匹配100，JSON相似度计算"""
        addr_a = (patient_a.get('location') or '').strip()
        addr_b = (patient_b.get('location') or '').strip()
        if not addr_a or not addr_b:
            return 0.0
        if addr_a == addr_b:
            return 100.0
        len_common = self._common_prefix_length(addr_a, addr_b)
        max_len = max(len(addr_a), len(addr_b))
        if max_len == 0:
            return 0.0
        return (len_common / max_len) * 100

    def _common_prefix_length(self, s1: str, s2: str) -> int:
        i = 0
        for c1, c2 in zip(s1, s2):
            if c1 == c2:
                i += 1
            else:
                break
        return i

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def _get_cache_key(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> str:
        p1 = patient_a.get('patient_id', '')
        p2 = patient_b.get('patient_id', '')
        sorted_ids = sorted([p1, p2])
        return f"similarity:{sorted_ids[0]}:{sorted_ids[1]}"

    def get_field_details(self, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> Dict[str, float]:
        """获取各字段相似度明细"""
        fields = ['identity_card', 'name', 'birthday', 'gender', 'phone', 'address']
        details = {}
        for field in fields:
            details[field] = self._calculate_field_similarity(field, patient_a, patient_b)
        return details

similarity_calculator = SimilarityCalculator()
```

- [ ] **Step 3: 创建合并决策服务**

```python
# backend/app/services/merger.py
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import EmpiMaster, EmpiMergeLog, EmpiPendingReview, EmpiProcessLog
from app.core.snowflake import get_snowflake_generator
from app.services.similarity import similarity_calculator
from app.services.cleaner import DataCleaner
import redis
import json
from datetime import datetime

class MergeDecisionEngine:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.snowflake = get_snowflake_generator()
        self.data_cleaner = DataCleaner()

    def decide(self, db: Session, patient_a: Dict[str, Any], patient_b: Dict[str, Any],
               weights: Dict[str, float], threshold: float) -> Tuple[str, float]:
        """决策是否合并：返回 (decision, score)"""
        score = similarity_calculator.calculate(patient_a, patient_b, weights)
        field_details = similarity_calculator.get_field_details(patient_a, patient_b)

        if score >= threshold:
            return ('AUTO_MERGE', score)

        self._save_pending_review(db, patient_a, patient_b, score, field_details)
        return ('PENDING_REVIEW', score)

    def _save_pending_review(self, db: Session, patient_a: Dict[str, Any],
                            patient_b: Dict[str, Any], score: float, field_details: Dict[str, float]):
        existing = db.query(EmpiPendingReview).filter(
            ((EmpiPendingReview.person_id_a == patient_a['patient_id']) &
             (EmpiPendingReview.person_id_b == patient_b['patient_id'])) |
            ((EmpiPendingReview.person_id_a == patient_b['patient_id']) &
             (EmpiPendingReview.person_id_b == patient_a['patient_id']))
        ).first()

        if existing:
            return

        pending = EmpiPendingReview(
            person_id_a=patient_a['patient_id'],
            person_id_b=patient_b['patient_id'],
            similarity_score=score,
            similarity_details=json.dumps(field_details),
            status='PENDING'
        )
        db.add(pending)
        db.commit()

    def auto_merge(self, db: Session, patient_a: Dict[str, Any], patient_b: Dict[str, Any],
                   score: float, merge_type: str = 'AUTO') -> int:
        """执行自动合并，返回主索引ID"""
        existing_log = db.query(EmpiMergeLog).filter(
            ((EmpiMergeLog.person_id_a == patient_a['patient_id']) &
             (EmpiMergeLog.person_id_b == patient_b['patient_id'])) |
            ((EmpiMergeLog.person_id_a == patient_b['patient_id']) &
             (EmpiMergeLog.person_id_b == patient_a['patient_id']))
        ).first()

        if existing_log:
            return existing_log.master_id

        created_a = patient_a.get('created_at') or datetime.now()
        created_b = patient_b.get('created_at') or datetime.now()

        if created_a <= created_b:
            master_patient = patient_a
            slave_patient = patient_b
        else:
            master_patient = patient_b
            slave_patient = patient_a

        master_record = db.query(EmpiMaster).filter(
            EmpiMaster.patient_id == master_patient['patient_id']
        ).first()

        if master_record:
            master_id = master_record.master_id
        else:
            master_id = self.snowflake.next_id()

        slave_record = db.query(EmpiMaster).filter(
            EmpiMaster.patient_id == slave_patient['patient_id']
        ).first()

        if slave_record:
            slave_record.status = 'MERGED'
            slave_record.merged_to_master_id = master_id
            slave_record.updated_at = datetime.now()

        merge_log = EmpiMergeLog(
            person_id_a=master_patient['patient_id'],
            person_id_b=slave_patient['patient_id'],
            master_id=master_id,
            merge_type=merge_type,
            similarity_score=score,
            merge_time=datetime.now()
        )
        db.add(merge_log)
        db.commit()

        return master_id

decision_engine = MergeDecisionEngine()
```

- [ ] **Step 4: 创建服务模块导出**

```python
# backend/app/services/__init__.py
from app.services.cleaner import DataCleaner, cleaner
from app.services.similarity import SimilarityCalculator, similarity_calculator
from app.services.merger import MergeDecisionEngine, decision_engine

__all__ = [
    'DataCleaner', 'cleaner',
    'SimilarityCalculator', 'similarity_calculator',
    'MergeDecisionEngine', 'decision_engine',
]
```

---

## 5. 倒排索引服务

**Files:**
- Create: `backend/app/services/inverted_index.py` - 倒排索引管理

- [ ] **Step 1: 创建倒排索引服务**

```python
# backend/app/services/inverted_index.py
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models import EmpiMaster
from app.services.cleaner import DataCleaner
import json

class InvertedIndexService:
    def __init__(self):
        self.data_cleaner = DataCleaner()

    def build_index(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        """为患者构建倒排索引"""
        return self.data_cleaner.build_inverted_index(patient)

    def search_candidates(self, db: Session, patient: Dict[str, Any]) -> List[Dict[str, Any]]:
        """搜索候选匹配患者"""
        index = self.build_index(patient)
        candidates = []

        pinyin_gender = index.get('pinyin_gender')
        if not pinyin_gender:
            return candidates

        all_records = db.query(EmpiMaster).filter(
            EmpiMaster.status == 'NORMAL'
        ).all()

        for record in all_records:
            if not record.inverted_index:
                continue
            record_index = record.inverted_index if isinstance(record.inverted_index, dict) else json.loads(record.inverted_index)

            if record_index.get('pinyin_gender') == pinyin_gender:
                candidates.append({
                    'patient_id': record.patient_id,
                    'patient_name': record.patient_name,
                    'master_id': record.master_id,
                    'inverted_index': record_index
                })
                continue

            if pinyin_gender.split('_')[0] == record_index.get('pinyin_gender', '').split('_')[0]:
                birth_year_gender = index.get('birth_year_gender')
                record_birth_year_gender = record_index.get('birth_year_gender')
                if birth_year_gender and record_birth_year_gender and birth_year_gender == record_birth_year_gender:
                    candidates.append({
                        'patient_id': record.patient_id,
                        'patient_name': record.patient_name,
                        'master_id': record.master_id,
                        'inverted_index': record_index
                    })
                    continue

                id_card_prefix = index.get('id_card_prefix')
                record_id_card_prefix = record_index.get('id_card_prefix')
                if id_card_prefix and record_id_card_prefix and id_card_prefix == record_id_card_prefix:
                    candidates.append({
                        'patient_id': record.patient_id,
                        'patient_name': record.patient_name,
                        'master_id': record.master_id,
                        'inverted_index': record_index
                    })

        return candidates

    def update_index(self, db: Session, patient_id: str, inverted_index: Dict[str, Any]):
        """更新患者的倒排索引"""
        record = db.query(EmpiMaster).filter(EmpiMaster.patient_id == patient_id).first()
        if record:
            record.inverted_index = inverted_index
            db.commit()

inverted_index_service = InvertedIndexService()
```

---

## 6. ETL调度器和增量处理

**Files:**
- Create: `backend/app/services/etl.py` - ETL调度器

- [ ] **Step 1: 创建ETL调度器**

```python
# backend/app/services/etl.py
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import EmpiMaster, EmpiProcessLog, EmpiConfig
from app.core.snowflake import get_snowflake_generator
from app.services.cleaner import DataCleaner
from app.services.inverted_index import inverted_index_service
from app.services.similarity import similarity_calculator
from app.services.merger import decision_engine
from app.core.config import settings
import redis
import json
from datetime import datetime

class ETLScheduler:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.snowflake = get_snowflake_generator()
        self.data_cleaner = DataCleaner()

    def poll_and_process(self, db: Session, batch_size: int = None):
        """轮询并处理增量数据"""
        if batch_size is None:
            batch_size = settings.ETL_BATCH_SIZE

        last_update_time = self._get_last_update_time()
        patients = self._fetch_patients(db, last_update_time, batch_size)

        if not patients:
            return {'processed': 0, 'merged': 0, 'pending': 0}

        weights = self._get_weights(db)
        threshold = self._get_threshold(db)

        stats = {'processed': 0, 'merged': 0, 'pending': 0}

        for patient in patients:
            if self._is_processed(db, patient['patient_id']):
                continue

            self._process_patient(db, patient, weights, threshold, stats)

            self._save_process_log(db, patient['patient_id'], 'CLEAN', {})

        self._set_last_update_time(datetime.now())

        return stats

    def _get_last_update_time(self) -> Optional[datetime]:
        key = 'etl:last_update_time'
        value = self.redis_client.get(key)
        if value:
            return datetime.fromisoformat(value)
        return None

    def _set_last_update_time(self, dt: datetime):
        key = 'etl:last_update_time'
        self.redis_client.set(key, dt.isoformat())

    def _fetch_patients(self, db: Session, last_update_time: Optional[datetime],
                       batch_size: int) -> list:
        query = db.query(text("*")).select_from(text("im_patient"))
        if last_update_time:
            query = query.where(text("data_updatetime > :last_update"))
            result = db.execute(query.params(last_update=last_update_time).limit(batch_size))
        else:
            result = db.execute(query.limit(batch_size))
        return result.fetchall()

    def _is_processed(self, db: Session, patient_id: str) -> bool:
        log = db.query(EmpiProcessLog).filter(
            EmpiProcessLog.patient_id == patient_id
        ).first()
        return log is not None

    def _get_weights(self, db: Session) -> Dict[str, float]:
        cache_key = 'config:weights'
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'field_weights'
        ).first()

        if config:
            weights = config.config_value
        else:
            weights = {
                'identity_card': 30,
                'name': 30,
                'birthday': 20,
                'gender': 5,
                'phone': 10,
                'address': 5
            }

        self.redis_client.setex(cache_key, 3600, json.dumps(weights))
        return weights

    def _get_threshold(self, db: Session) -> float:
        cache_key = 'config:threshold'
        cached = self.redis_client.get(cache_key)
        if cached:
            return float(cached)

        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'merge_threshold'
        ).first()

        threshold = config.config_value.get('threshold', settings.DEFAULT_MERGE_THRESHOLD) if config else settings.DEFAULT_MERGE_THRESHOLD
        self.redis_client.setex(cache_key, 3600, str(threshold))
        return threshold

    def _process_patient(self, db: Session, patient: Dict[str, Any],
                         weights: Dict[str, float], threshold: float,
                         stats: Dict[str, int]):
        inverted_index = inverted_index_service.build_index(patient)

        patient_record = db.query(EmpiMaster).filter(
            EmpiMaster.patient_id == patient['patient_id']
        ).first()

        if not patient_record:
            master_id = self.snowflake.next_id()
            patient_record = EmpiMaster(
                id=master_id,
                patient_id=patient['patient_id'],
                patient_name=self.data_cleaner.clean_name(patient.get('person_name', '')),
                master_id=master_id,
                status='NORMAL',
                inverted_index=inverted_index
            )
            db.add(patient_record)
            db.commit()

        candidates = inverted_index_service.search_candidates(db, patient)

        for candidate in candidates:
            if candidate['patient_id'] == patient['patient_id']:
                continue

            candidate_patient = db.query(EmpiMaster).filter(
                EmpiMaster.patient_id == candidate['patient_id']
            ).first()

            if not candidate_patient:
                continue

            candidate_data = {
                'patient_id': candidate_patient.patient_id,
                'patient_name': candidate_patient.patient_name,
                'gender': candidate_patient.inverted_index.get('pinyin_gender', '').split('_')[-1] if candidate_patient.inverted_index else '',
                'birthday': candidate_patient.inverted_index.get('birth_year_gender', '').split('_')[0] if candidate_patient.inverted_index else None,
                'identity_card_num': None,
                'card_id': None,
                'phone': None,
                'location': None,
            }

            decision, score = decision_engine.decide(
                db, patient, candidate_data, weights, threshold
            )

            if decision == 'AUTO_MERGE':
                decision_engine.auto_merge(db, patient, candidate_data, score, 'AUTO')
                stats['merged'] += 1

            self._save_process_log(db, patient['patient_id'], 'CALCULATE', {
                'candidate_id': candidate['patient_id'],
                'score': score,
                'decision': decision
            })

        stats['processed'] += 1

    def _save_process_log(self, db: Session, patient_id: str, process_type: str, details: Dict):
        log = EmpiProcessLog(
            patient_id=patient_id,
            process_type=process_type,
            details=json.dumps(details),
            process_time=datetime.now()
        )
        db.add(log)
        db.commit()

etl_scheduler = ETLScheduler()
```

---

## 7. 配置服务

**Files:**
- Create: `backend/app/services/config_service.py` - 配置管理服务

- [ ] **Step 1: 创建配置服务**

```python
# backend/app/services/config_service.py
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import EmpiConfig
import redis
import json
from datetime import datetime

class ConfigService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )

    def get_weights(self, db: Session) -> Dict[str, float]:
        """获取字段权重配置"""
        cache_key = 'config:weights'
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'field_weights'
        ).first()

        if config:
            weights = config.config_value
        else:
            weights = {
                'identity_card': 30,
                'name': 30,
                'birthday': 20,
                'gender': 5,
                'phone': 10,
                'address': 5
            }

        self.redis_client.setex(cache_key, 3600, json.dumps(weights))
        return weights

    def update_weights(self, db: Session, weights: Dict[str, float]) -> Dict[str, float]:
        """更新字段权重配置"""
        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'field_weights'
        ).first()

        if config:
            config.config_value = weights
            config.updated_at = datetime.now()
        else:
            config = EmpiConfig(
                config_key='field_weights',
                config_value=weights,
                description='字段权重配置',
                updated_at=datetime.now()
            )
            db.add(config)

        db.commit()
        self.redis_client.setex('config:weights', 3600, json.dumps(weights))
        return weights

    def get_threshold(self, db: Session) -> float:
        """获取自动合并阈值"""
        cache_key = 'config:threshold'
        cached = self.redis_client.get(cache_key)
        if cached:
            return float(cached)

        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'merge_threshold'
        ).first()

        threshold = config.config_value.get('threshold', 85.0) if config else 85.0
        self.redis_client.setex(cache_key, 3600, str(threshold))
        return threshold

    def update_threshold(self, db: Session, threshold: float) -> float:
        """更新自动合并阈值"""
        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'merge_threshold'
        ).first()

        if config:
            config.config_value = {'threshold': threshold}
            config.updated_at = datetime.now()
        else:
            config = EmpiConfig(
                config_key='merge_threshold',
                config_value={'threshold': threshold},
                description='自动合并阈值',
                updated_at=datetime.now()
            )
            db.add(config)

        db.commit()
        self.redis_client.setex('config:threshold', 3600, str(threshold))
        return threshold

config_service = ConfigService()
```

---

## 8. 后端API

**Files:**
- Create: `backend/app/api/config.py` - 配置API
- Create: `backend/app/api/patients.py` - 患者API
- Create: `backend/app/api/merge.py` - 合并API
- Create: `backend/app/api/stats.py` - 统计API
- Create: `backend/app/api/deps.py` - 依赖注入

- [ ] **Step 1: 创建API依赖注入**

```python
# backend/app/api/deps.py
from app.models.base import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: 创建配置API**

```python
# backend/app/api/config.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.api.deps import get_db
from app.services.config_service import config_service

router = APIRouter(prefix="/api/config", tags=["config"])

@router.get("/weights")
def get_weights(db: Session = Depends(get_db)) -> Dict[str, float]:
    return config_service.get_weights(db)

@router.put("/weights")
def update_weights(weights: Dict[str, float], db: Session = Depends(get_db)) -> Dict[str, float]:
    return config_service.update_weights(db, weights)

@router.get("/threshold")
def get_threshold(db: Session = Depends(get_db)) -> Dict[str, float]:
    threshold = config_service.get_threshold(db)
    return {"threshold": threshold}

@router.put("/threshold")
def update_threshold(params: Dict[str, float], db: Session = Depends(get_db)) -> Dict[str, float]:
    threshold = params.get("threshold", 85.0)
    return {"threshold": config_service.update_threshold(db, threshold)}
```

- [ ] **Step 3: 创建患者API**

```python
# backend/app/api/patients.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.api.deps import get_db
from app.models import EmpiMaster, EmpiPendingReview

router = APIRouter(prefix="/api/patients", tags=["patients"])

@router.get("")
def list_patients(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)) -> Dict[str, Any]:
    offset = (page - 1) * page_size
    total = db.query(EmpiMaster).count()
    patients = db.query(EmpiMaster).offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [
            {
                "patient_id": p.patient_id,
                "patient_name": p.patient_name,
                "master_id": p.master_id,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in patients
        ]
    }

@router.get("/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)) -> Optional[Dict[str, Any]]:
    patient = db.query(EmpiMaster).filter(EmpiMaster.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return {
        "patient_id": patient.patient_id,
        "patient_name": patient.patient_name,
        "master_id": patient.master_id,
        "status": patient.status,
        "merged_to_master_id": patient.merged_to_master_id,
        "inverted_index": patient.inverted_index,
        "created_at": patient.created_at.isoformat() if patient.created_at else None,
        "updated_at": patient.updated_at.isoformat() if patient.updated_at else None
    }

@router.get("/{patient_id}/similar")
def get_similar_patients(patient_id: str, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    pending = db.query(EmpiPendingReview).filter(
        (EmpiPendingReview.person_id_a == patient_id) |
        (EmpiPendingReview.person_id_b == patient_id)
    ).filter(EmpiPendingReview.status == 'PENDING').all()

    return [
        {
            "id": p.id,
            "person_id_a": p.person_id_a,
            "person_id_b": p.person_id_b,
            "similarity_score": float(p.similarity_score),
            "similarity_details": p.similarity_details,
            "create_time": p.create_time.isoformat() if p.create_time else None
        }
        for p in pending
    ]

@router.get("/{patient_id}/master")
def get_patient_master(patient_id: str, db: Session = Depends(get_db)) -> Optional[Dict[str, Any]]:
    patient = db.query(EmpiMaster).filter(EmpiMaster.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    master_id = patient.master_id
    if patient.status == 'MERGED' and patient.merged_to_master_id:
        master_id = patient.merged_to_master_id

    master = db.query(EmpiMaster).filter(EmpiMaster.master_id == master_id).first()

    merged_patients = db.query(EmpiMaster).filter(
        EmpiMaster.merged_to_master_id == master_id
    ).all()

    return {
        "master_id": master_id,
        "primary_patient": {
            "patient_id": master.patient_id,
            "patient_name": master.patient_name
        } if master else None,
        "merged_patients": [
            {
                "patient_id": p.patient_id,
                "patient_name": p.patient_name
            }
            for p in merged_patients
        ]
    }
```

- [ ] **Step 4: 创建合并API**

```python
# backend/app/api/merge.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.api.deps import get_db
from app.models import EmpiPendingReview, EmpiMergeLog, EmpiMaster
from app.services.merger import decision_engine
import json
from datetime import datetime

router = APIRouter(prefix="/api/merge", tags=["merge"])

@router.get("/candidates")
def list_merge_candidates(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)) -> Dict[str, Any]:
    offset = (page - 1) * page_size
    total = db.query(EmpiPendingReview).filter(EmpiPendingReview.status == 'PENDING').count()
    candidates = db.query(EmpiPendingReview).filter(
        EmpiPendingReview.status == 'PENDING'
    ).offset(offset).limit(page_size).all()

    result = []
    for c in candidates:
        patient_a = db.query(EmpiMaster).filter(EmpiMaster.patient_id == c.person_id_a).first()
        patient_b = db.query(EmpiMaster).filter(EmpiMaster.patient_id == c.person_id_b).first()

        result.append({
            "id": c.id,
            "patient_a": {
                "patient_id": patient_a.patient_id if patient_a else c.person_id_a,
                "patient_name": patient_a.patient_name if patient_a else None
            },
            "patient_b": {
                "patient_id": patient_b.patient_id if patient_b else c.person_id_b,
                "patient_name": patient_b.patient_name if patient_b else None
            },
            "similarity_score": float(c.similarity_score),
            "similarity_details": c.similarity_details,
            "create_time": c.create_time.isoformat() if c.create_time else None
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": result
    }

@router.post("")
def manual_merge(params: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, Any]:
    person_id_a = params.get("person_id_a")
    person_id_b = params.get("person_id_b")

    if not person_id_a or not person_id_b:
        raise HTTPException(status_code=400, detail="person_id_a and person_id_b are required")

    patient_a = db.query(EmpiMaster).filter(EmpiMaster.patient_id == person_id_a).first()
    patient_b = db.query(EmpiMaster).filter(EmpiMaster.patient_id == person_id_b).first()

    if not patient_a or not patient_b:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_a_data = {
        "patient_id": patient_a.patient_id,
        "patient_name": patient_a.patient_name,
        "gender": patient_a.inverted_index.get("pinyin_gender", "").split("_")[-1] if patient_a.inverted_index else "",
        "created_at": patient_a.created_at
    }
    patient_b_data = {
        "patient_id": patient_b.patient_id,
        "patient_name": patient_b.patient_name,
        "gender": patient_b.inverted_index.get("pinyin_gender", "").split("_")[-1] if patient_b.inverted_index else "",
        "created_at": patient_b.created_at
    }

    master_id = decision_engine.auto_merge(db, patient_a_data, patient_b_data, 100.0, 'MANUAL')

    pending = db.query(EmpiPendingReview).filter(
        ((EmpiPendingReview.person_id_a == person_id_a) & (EmpiPendingReview.person_id_b == person_id_b)) |
        ((EmpiPendingReview.person_id_a == person_id_b) & (EmpiPendingReview.person_id_b == person_id_a))
    ).first()

    if pending:
        pending.status = 'RESOLVED'
        pending.resolution_type = 'MERGE'
        pending.resolved_at = datetime.now()
        db.commit()

    return {"master_id": master_id, "message": "Merge successful"}

@router.post("/{id}/ignore")
def ignore_candidate(id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    pending = db.query(EmpiPendingReview).filter(EmpiPendingReview.id == id).first()
    if not pending:
        raise HTTPException(status_code=404, detail="Candidate not found")

    pending.status = 'IGNORED'
    pending.resolved_at = datetime.now()
    db.commit()

    return {"message": "Ignored successfully"}

@router.get("/history")
def merge_history(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)) -> Dict[str, Any]:
    offset = (page - 1) * page_size
    total = db.query(EmpiMergeLog).count()
    logs = db.query(EmpiMergeLog).order_by(EmpiMergeLog.merge_time.desc()).offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [
            {
                "id": log.id,
                "person_id_a": log.person_id_a,
                "person_id_b": log.person_id_b,
                "master_id": log.master_id,
                "merge_type": log.merge_type,
                "similarity_score": float(log.similarity_score),
                "merge_time": log.merge_time.isoformat() if log.merge_time else None
            }
            for log in logs
        ]
    }
```

- [ ] **Step 5: 创建统计API**

```python
# backend/app/api/stats.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.deps import get_db
from app.models import EmpiMaster, EmpiMergeLog, EmpiPendingReview
from typing import Dict, Any

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("")
def get_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    total = db.query(EmpiMaster).count()
    merged = db.query(EmpiMaster).filter(EmpiMaster.status == 'MERGED').count()
    pending = db.query(EmpiPendingReview).filter(EmpiPendingReview.status == 'PENDING').count()

    return {
        "total": total,
        "merged": merged,
        "pending": pending,
        "merge_rate": round(merged / total * 100, 2) if total > 0 else 0
    }

@router.get("/trend")
def get_trend(days: int = 7, db: Session = Depends(get_db)) -> Dict[str, Any]:
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    daily_stats = []
    current = start_date
    while current <= end_date:
        next_day = current + timedelta(days=1)
        count = db.query(EmpiMergeLog).filter(
            EmpiMergeLog.merge_time >= current,
            EmpiMergeLog.merge_time < next_day
        ).count()
        daily_stats.append({
            "date": current.strftime("%Y-%m-%d"),
            "count": count
        })
        current = next_day

    return {"data": daily_stats}
```

- [ ] **Step 6: 创建API主入口**

```python
# backend/app/api/__init__.py
from fastapi import APIRouter
from app.api import config, patients, merge, stats

router = APIRouter()
router.include_router(config.router)
router.include_router(patients.router)
router.include_router(merge.router)
router.include_router(stats.router)
```

---

## 9. FastAPI应用入口

**Files:**
- Create: `backend/app/main.py` - FastAPI应用入口
- Create: `backend/app/__init__.py` - 应用初始化

- [ ] **Step 1: 创建FastAPI应用入口**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## 10. 前端页面

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.js`
- Create: `frontend/src/views/Dashboard.vue`
- Create: `frontend/src/views/Config.vue`
- Create: `frontend/src/views/Pending.vue`
- Create: `frontend/src/views/Merged.vue`
- Create: `frontend/src/views/Patients.vue`
- Create: `frontend/src/api/index.js`

- [ ] **Step 1: 创建前端入口HTML**

```html
<!-- frontend/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EMPI 患者主索引系统</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

- [ ] **Step 2: 创建前端入口JS**

```javascript
// frontend/src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')
```

- [ ] **Step 3: 创建App.vue**

```vue
<!-- frontend/src/App.vue -->
<template>
  <el-config-provider :locale="zhCn">
    <div id="app">
      <el-container>
        <el-header>
          <h1>EMPI 患者主索引系统</h1>
        <el-menu mode="horizontal" :default-active="$route.path" router>
            <el-menu-item index="/">仪表盘</el-menu-item>
            <el-menu-item index="/config">配置管理</el-menu-item>
            <el-menu-item index="/pending">待审核</el-menu-item>
            <el-menu-item index="/merged">已合并</el-menu-item>
            <el-menu-item index="/patients">患者查询</el-menu-item>
          </el-menu>
        </el-header>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </div>
  </el-config-provider>
</template>

<script setup>
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

const $route = useRoute()
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.el-header {
  display: flex;
  align-items: center;
  gap: 2rem;
  border-bottom: 1px solid #e0e0e0;
}
.el-header h1 {
  margin: 0;
  font-size: 1.25rem;
}
</style>
```

- [ ] **Step 4: 创建路由**

```javascript
// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/config', name: 'Config', component: () => import('../views/Config.vue') },
  { path: '/pending', name: 'Pending', component: () => import('../views/Pending.vue') },
  { path: '/merged', name: 'Merged', component: () => import('../views/Merged.vue') },
  { path: '/patients', name: 'Patients', component: () => import('../views/Patients.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes
})
```

- [ ] **Step 5: 创建API模块**

```javascript
// frontend/src/api/index.js
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000
})

export const configApi = {
  getWeights: () => api.get('/api/config/weights'),
  updateWeights: (weights) => api.put('/api/config/weights', weights),
  getThreshold: () => api.get('/api/config/threshold'),
  updateThreshold: (threshold) => api.put('/api/config/threshold', { threshold })
}

export const patientsApi = {
  list: (page, pageSize) => api.get('/api/patients', { params: { page, page_size: pageSize } }),
  get: (patientId) => api.get(`/api/patients/${patientId}`),
  getSimilar: (patientId) => api.get(`/api/patients/${patientId}/similar`),
  getMaster: (patientId) => api.get(`/api/patients/${patientId}/master`)
}

export const mergeApi = {
  listCandidates: (page, pageSize) => api.get('/api/merge/candidates', { params: { page, page_size: pageSize } }),
  merge: (personIdA, personIdB) => api.post('/api/merge', { person_id_a: personIdA, person_id_b: personIdB }),
  ignore: (id) => api.post(`/api/merge/${id}/ignore`),
  history: (page, pageSize) => api.get('/api/merge/history', { params: { page, page_size: pageSize } })
}

export const statsApi = {
  get: () => api.get('/api/stats'),
  getTrend: (days) => api.get('/api/stats/trend', { params: { days } })
}

export default api
```

- [ ] **Step 6: 创建仪表盘页面**

```vue
<!-- frontend/src/views/Dashboard.vue -->
<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card>
          <template #header>患者总数</template>
          <div class="stat-value">{{ stats.total || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <template #header>已合并</template>
          <div class="stat-value">{{ stats.merged || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <template #header>待审核</template>
          <div class="stat-value">{{ stats.pending || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <template #header>合并率</template>
          <div class="stat-value">{{ stats.merge_rate || 0 }}%</div>
        </el-card>
      </el-col>
    </el-row>
    <el-card style="margin-top: 20px;">
      <template #header>合并趋势（近7天）</template>
      <div v-if="trendData.length">
        <div v-for="item in trendData" :key="item.date" class="trend-item">
          <span>{{ item.date }}</span>
          <el-progress :percentage="getMaxPercentage(item.count)" :show-text="false" />
          <span>{{ item.count }}</span>
        </div>
      </div>
      <el-empty v-else description="暂无数据" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { statsApi } from '../api'
import { ElMessage } from 'element-plus'

const stats = ref({})
const trendData = ref([])
const maxCount = ref(1)

onMounted(async () => {
  try {
    const [statsRes, trendRes] = await Promise.all([
      statsApi.get(),
      statsApi.getTrend(7)
    ])
    stats.value = statsRes.data
    trendData.value = trendRes.data.data || []
    maxCount.value = Math.max(...trendData.value.map(d => d.count), 1)
  } catch (error) {
    ElMessage.error('获取统计数据失败')
  }
})

const getMaxPercentage = (count) => {
  return Math.round((count / maxCount.value) * 100)
}
</script>

<style scoped>
.stat-value {
  font-size: 2rem;
  font-weight: bold;
  text-align: center;
  padding: 1rem 0;
}
.trend-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}
.trend-item span:first-child {
  width: 100px;
}
.trend-item span:last-child {
  width: 50px;
  text-align: right;
}
</style>
```

- [ ] **Step 7: 创建配置管理页面**

```vue
<!-- frontend/src/views/Config.vue -->
<template>
  <div class="config-page">
    <el-card>
      <template #header>字段权重配置</template>
      <el-form label-width="120px">
        <el-form-item v-for="(weight, field) in weights" :key="field" :label="fieldLabels[field]">
          <el-slider v-model="weights[field]" :min="0" :max="100" show-input />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveWeights">保存权重</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="margin-top: 20px;">
      <template #header>合并阈值配置</template>
      <el-form label-width="120px">
        <el-form-item label="自动合并阈值">
          <el-input-number v-model="threshold" :min="0" :max="100" />
          <span style="margin-left: 10px;">分（≥此分数自动合并）</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveThreshold">保存阈值</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { configApi } from '../api'
import { ElMessage } from 'element-plus'

const weights = ref({
  identity_card: 30,
  name: 30,
  birthday: 20,
  gender: 5,
  phone: 10,
  address: 5
})

const threshold = ref(85)

const fieldLabels = {
  identity_card: '身份证号码',
  name: '姓名',
  birthday: '生日',
  gender: '性别',
  phone: '电话',
  address: '地址'
}

onMounted(async () => {
  try {
    const [weightsRes, thresholdRes] = await Promise.all([
      configApi.getWeights(),
      configApi.getThreshold()
    ])
    weights.value = weightsRes.data
    threshold.value = thresholdRes.data.threshold
  } catch (error) {
    ElMessage.error('获取配置失败')
  }
})

const saveWeights = async () => {
  try {
    await configApi.updateWeights(weights.value)
    ElMessage.success('权重保存成功')
  } catch (error) {
    ElMessage.error('权重保存失败')
  }
}

const saveThreshold = async () => {
  try {
    await configApi.updateThreshold(threshold.value)
    ElMessage.success('阈值保存成功')
  } catch (error) {
    ElMessage.error('阈值保存失败')
  }
}
</script>
```

- [ ] **Step 8: 创建待审核页面**

```vue
<!-- frontend/src/views/Pending.vue -->
<template>
  <div class="pending-page">
    <el-card>
      <template #header>
        <span>待审核列表</span>
        <el-button type="primary" size="small" @click="loadCandidates">刷新</el-button>
      </template>
      <el-table :data="candidates" stripe>
        <el-table-column prop="patient_a.patient_name" label="患者A" />
        <el-table-column prop="patient_b.patient_name" label="患者B" />
        <el-table-column prop="similarity_score" label="相似度">
          <template #default="{ row }">
            <el-tag :type="getScoreType(row.similarity_score)">{{ row.similarity_score }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleMerge(row)">合并</el-button>
            <el-button type="info" size="small" @click="handleIgnore(row)">忽略</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadCandidates"
        style="margin-top: 20px; justify-content: center;"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { mergeApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const candidates = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

onMounted(() => {
  loadCandidates()
})

const loadCandidates = async () => {
  try {
    const res = await mergeApi.listCandidates(page.value, pageSize.value)
    candidates.value = res.data.data || []
    total.value = res.data.total || 0
  } catch (error) {
    ElMessage.error('获取待审核列表失败')
  }
}

const getScoreType = (score) => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'info'
}

const handleMerge = async (row) => {
  try {
    await ElMessageBox.confirm('确认合并这两个患者？', '合并确认', { type: 'warning' })
    await mergeApi.merge(row.patient_a.patient_id, row.patient_b.patient_id)
    ElMessage.success('合并成功')
    loadCandidates()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('合并失败')
    }
  }
}

const handleIgnore = async (row) => {
  try {
    await ElMessageBox.confirm('确认忽略此候选对？', '忽略确认', { type: 'warning' })
    await mergeApi.ignore(row.id)
    ElMessage.success('已忽略')
    loadCandidates()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}
</script>
```

- [ ] **Step 9: 创建已合并页面**

```vue
<!-- frontend/src/views/Merged.vue -->
<template>
  <div class="merged-page">
    <el-card>
      <template #header>合并历史</template>
      <el-table :data="history" stripe>
        <el-table-column prop="person_id_a" label="患者A ID" />
        <el-table-column prop="person_id_b" label="患者B ID" />
        <el-table-column prop="master_id" label="主索引ID" />
        <el-table-column prop="merge_type" label="合并类型">
          <template #default="{ row }">
            <el-tag :type="row.merge_type === 'AUTO' ? 'success' : 'primary'">
              {{ row.merge_type === 'AUTO' ? '自动' : '人工' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="similarity_score" label="相似度" />
        <el-table-column prop="merge_time" label="合并时间" />
      </el-table>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadHistory"
        style="margin-top: 20px; justify-content: center;"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { mergeApi } from '../api'
import { ElMessage } from 'element-plus'

const history = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

onMounted(() => {
  loadHistory()
})

const loadHistory = async () => {
  try {
    const res = await mergeApi.history(page.value, pageSize.value)
    history.value = res.data.data || []
    total.value = res.data.total || 0
  } catch (error) {
    ElMessage.error('获取合并历史失败')
  }
}
</script>
```

- [ ] **Step 10: 创建患者查询页面**

```vue
<!-- frontend/src/views/Patients.vue -->
<template>
  <div class="patients-page">
    <el-card>
      <template #header>患者查询</template>
      <el-form inline>
        <el-form-item label="患者ID">
          <el-input v-model="searchId" placeholder="输入患者ID" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="searchPatient">查询</el-button>
        </el-form-item>
      </el-form>

      <div v-if="patient" style="margin-top: 20px;">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="患者ID">{{ patient.patient_id }}</el-descriptions-item>
          <el-descriptions-item label="患者姓名">{{ patient.patient_name }}</el-descriptions-item>
          <el-descriptions-item label="主索引ID">{{ patient.master_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="patient.status === 'NORMAL' ? 'success' : 'warning'">
              {{ patient.status === 'NORMAL' ? '正常' : '已合并' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="masterInfo" style="margin-top: 20px;">
          <h4>主索引信息</h4>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="主索引ID">{{ masterInfo.master_id }}</el-descriptions-item>
            <el-descriptions-item label="主患者">{{ masterInfo.primary_patient?.patient_name }}</el-descriptions-item>
          </el-descriptions>
          <div v-if="masterInfo.merged_patients?.length" style="margin-top: 10px;">
            <h4>已合并患者</h4>
            <el-tag v-for="p in masterInfo.merged_patients" :key="p.patient_id" style="margin-right: 10px;">
              {{ p.patient_name }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { patientsApi } from '../api'
import { ElMessage } from 'element-plus'

const searchId = ref('')
const patient = ref(null)
const masterInfo = ref(null)

const searchPatient = async () => {
  if (!searchId.value) {
    ElMessage.warning('请输入患者ID')
    return
  }
  try {
    patient.value = await patientsApi.get(searchId.value)
    const masterRes = await patientsApi.getMaster(searchId.value)
    masterInfo.value = masterRes.data
  } catch (error) {
    ElMessage.error('患者不存在')
    patient.value = null
    masterInfo.value = null
  }
}
</script>
```

---

## 11. Docker部署配置

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `docker-compose.yml`
- Create: `backend/.env.example`

- [ ] **Step 1: 创建后端Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 创建前端Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 3: 创建前端nginx配置**

```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **Step 4: 创建docker-compose.yml**

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_USER=root
      - MYSQL_PASSWORD=${MYSQL_PASSWORD:-empi123}
      - MYSQL_DATABASE=empi_db
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - mysql
      - redis
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_PASSWORD:-empi123}
      - MYSQL_DATABASE=empi_db
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./backend/init_db.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  mysql_data:
```

- [ ] **Step 5: 创建环境变量示例文件**

```bash
# backend/.env.example
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=empi123
MYSQL_DATABASE=empi_db
REDIS_HOST=localhost
REDIS_PORT=6379
SNOWFLAKE_WORKER_ID=1
ETL_BATCH_SIZE=1000
DEFAULT_MERGE_THRESHOLD=85.0
```

---

## 12. 单元测试

**Files:**
- Create: `backend/tests/test_cleaner.py`
- Create: `backend/tests/test_similarity.py`
- Create: `backend/tests/test_snowflake.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: 创建测试配置**

```python
# backend/tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_engine():
    return create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()
```

- [ ] **Step 2: 创建数据清洗测试**

```python
# backend/tests/test_cleaner.py
import pytest
from app.services.cleaner import DataCleaner

def test_clean_name():
    cleaner = DataCleaner()
    assert cleaner.clean_name(" 张  三 ") == "张三"
    assert cleaner.clean_name("李四") == "李四"
    assert cleaner.clean_name("") == ""

def test_get_pinyin():
    cleaner = DataCleaner()
    assert cleaner.get_pinyin("张三") == "zhangsan"
    assert cleaner.get_pinyin("李四") == "lisi"

def test_clean_gender():
    cleaner = DataCleaner()
    assert cleaner.clean_gender("男") == "M"
    assert cleaner.clean_gender("M") == "M"
    assert cleaner.clean_gender("女") == "N"
    assert cleaner.clean_gender("") == "N"

def test_clean_id_card():
    cleaner = DataCleaner()
    assert cleaner.clean_id_card("110101199001011234") == "110101199001011234"
    assert cleaner.clean_id_card("  110101199001011234  ") == "110101199001011234"
    assert cleaner.clean_id_card("123") is None

def test_get_id_card_prefix():
    cleaner = DataCleaner()
    assert cleaner.get_id_card_prefix("110101199001011234") == "110101"
    assert cleaner.get_id_card_prefix("12345") is None

def test_clean_phone():
    cleaner = DataCleaner()
    assert cleaner.clean_phone("13812345678") == "13812345678"
    assert cleaner.clean_phone(" 138-1234-5678 ") == "13812345678"
    assert cleaner.clean_phone("123") is None

def test_get_birth_year():
    cleaner = DataCleaner()
    from datetime import datetime
    assert cleaner.get_birth_year(datetime(1990, 1, 1)) == 1990
    assert cleaner.get_birth_year("1990-01-01") == 1990
    assert cleaner.get_birth_year(None) is None
```

- [ ] **Step 3: 创建雪花算法测试**

```python
# backend/tests/test_snowflake.py
import pytest
import time
from app.core.snowflake import SnowflakeIdGenerator

def test_snowflake_generates_unique_ids():
    generator = SnowflakeIdGenerator()
    ids = set()
    for _ in range(10000):
        id = generator.next_id()
        assert id not in ids
        ids.add(id)

def test_snowflake_id_length():
    generator = SnowflakeIdGenerator()
    id = generator.next_id()
    assert id > 0
    assert len(str(id)) >= 15

def test_snowflake_id_increasing():
    generator = SnowflakeIdGenerator()
    last_id = generator.next_id()
    for _ in range(100):
        new_id = generator.next_id()
        assert new_id > last_id
        last_id = new_id
```

- [ ] **Step 4: 创建相似度计算测试**

```python
# backend/tests/test_similarity.py
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

    def test_levenshtein_distance(self, calculator):
        assert calculator._levenshtein_distance('kitten', 'sitting') == 3
        assert calculator._levenshtein_distance('', 'abc') == 3
        assert calculator._levenshtein_distance('abc', 'abc') == 0
```

---

## 计划自检

1. **Spec覆盖检查:**
   - ✅ 数据库表结构：任务2覆盖
   - ✅ 雪花算法主索引：任务3覆盖（snowflake.py）
   - ✅ 倒排索引管理：任务5覆盖（inverted_index.py）
   - ✅ 数据清洗引擎：任务4覆盖（cleaner.py）
   - ✅ 相似度计算引擎：任务4覆盖（similarity.py）
   - ✅ 合并决策引擎：任务4覆盖（merger.py）
   - ✅ ETL调度器和增量处理：任务6覆盖（etl.py）
   - ✅ 配置服务：任务7覆盖（config_service.py）
   - ✅ 后端API：任务8覆盖
   - ✅ 前端页面：任务10覆盖（Dashboard、Config、Pending、Merged、Patients）
   - ✅ Docker部署：任务11覆盖
   - ✅ 单元测试：任务12覆盖

2. **占位符检查：** 无TBD、TODO占位符

3. **类型一致性：** 所有类型、方法签名在整个计划中保持一致

---

## 实施选项

**计划已完成并保存至 `docs/superpowers/plans/2026-04-30-empi-implementation.md`**

两个执行选项：

**1. 子代理驱动（推荐）** - 每个任务由新的子代理执行，任务间进行审查，快速迭代

**2. 内联执行** - 在此会话中执行任务，使用executing-plans，分批执行带检查点

您想选择哪种方式开始实施？