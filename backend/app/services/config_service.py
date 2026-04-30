from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models import EmpiConfig
from app.core.config import settings
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