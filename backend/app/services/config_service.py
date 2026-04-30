from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models import EmpiConfig
from app.core.config import settings
import redis
import json
from datetime import datetime

default_weights = [
    {"field_name": "identity_card", "display_name": "身份证号码", "weight": 30},
    {"field_name": "name", "display_name": "姓名", "weight": 30},
    {"field_name": "birthday", "display_name": "生日", "weight": 20},
    {"field_name": "gender", "display_name": "性别", "weight": 5},
    {"field_name": "phone", "display_name": "电话", "weight": 10},
    {"field_name": "address", "display_name": "地址", "weight": 5}
]

class ConfigService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )

    def get_weights(self, db: Session) -> List[dict]:
        """获取字段权重配置"""
        cache_key = 'config:weights'
        cached = self.redis_client.get(cache_key)
        if cached:
            weights = json.loads(cached)
            # Migrate old format if needed
            if weights and isinstance(weights, dict):
                weights = self._migrate_weights_format(weights)
            return weights

        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'field_weights'
        ).first()

        if config:
            weights = config.config_value
            # Migrate old format if needed
            if isinstance(weights, dict):
                weights = self._migrate_weights_format(weights)
        else:
            weights = default_weights

        self.redis_client.setex(cache_key, 3600, json.dumps(weights))
        return weights

    def _migrate_weights_format(self, old_weights: Dict[str, float]) -> List[dict]:
        """将旧格式dict迁移到新格式list"""
        field_mapping = {
            'identity_card': '身份证号码',
            'name': '姓名',
            'birthday': '生日',
            'gender': '性别',
            'phone': '电话',
            'address': '地址'
        }
        return [
            {"field_name": k, "display_name": field_mapping.get(k, k), "weight": v}
            for k, v in old_weights.items()
 ]

    def update_weights(self, db: Session, weights: List[dict]) -> List[dict]:
        """更新字段权重配置"""
        # Validate weight structure
        for w in weights:
            if 'field_name' not in w or 'weight' not in w:
                raise ValueError("Each weight must have 'field_name' and 'weight' fields")
            if not isinstance(w['weight'], (int, float)) or w['weight'] < 0:
                raise ValueError("Weight must be a non-negative number")
            if w['weight'] > 100:
                raise ValueError("Individual weight cannot exceed 100")

        # Validate total weight = 100
        total = sum(w['weight'] for w in weights)
        if total != 100:
            raise ValueError(f"Weight total must be 100, got {total}")

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

    def get_pending_threshold(self, db: Session) -> float:
        """获取待审核显示阈值"""
        cache_key = 'config:pending_threshold'
        cached = self.redis_client.get(cache_key)
        if cached:
            return float(cached)

        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'pending_threshold'
        ).first()

        threshold = config.config_value.get('threshold', 60.0) if config else 60.0
        self.redis_client.setex(cache_key, 3600, str(threshold))
        return threshold

    def update_pending_threshold(self, db: Session, threshold: float) -> float:
        """更新待审核显示阈值"""
        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'pending_threshold'
        ).first()

        if config:
            config.config_value = {'threshold': threshold}
            config.updated_at = datetime.now()
        else:
            config = EmpiConfig(
                config_key='pending_threshold',
                config_value={'threshold': threshold},
                description='待审核显示阈值',
                updated_at=datetime.now()
            )
            db.add(config)

        db.commit()
        self.redis_client.setex('config:pending_threshold', 3600, str(threshold))
        return threshold

    def get_poll_interval_hours(self, db: Session) -> float:
        """获取轮询间隔（小时）"""
        cache_key = 'config:poll_interval_hours'
        cached = self.redis_client.get(cache_key)
        if cached:
            return float(cached)

        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'poll_interval_hours'
        ).first()

        interval = config.config_value.get('hours', 2.0) if config else 2.0
        self.redis_client.setex(cache_key, 3600, str(interval))
        return interval

    def update_poll_interval_hours(self, db: Session, hours: float) -> float:
        """更新轮询间隔（小时）"""
        config = db.query(EmpiConfig).filter(
            EmpiConfig.config_key == 'poll_interval_hours'
        ).first()

        if config:
            config.config_value = {'hours': hours}
            config.updated_at = datetime.now()
        else:
            config = EmpiConfig(
                config_key='poll_interval_hours',
                config_value={'hours': hours},
                description='ETL轮询间隔（小时）',
                updated_at=datetime.now()
            )
            db.add(config)

        db.commit()
        self.redis_client.setex('config:poll_interval_hours', 3600, str(hours))
        return hours

config_service = ConfigService()