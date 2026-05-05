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

    # Logging
    LOG_DIR: str = "logs"
    LOG_RETENTION_DAYS: int = 7

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()