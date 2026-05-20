"""添加复合索引优化模糊查询性能"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from app.core.config import settings


def index_exists(conn, index_name, table_name):
    result = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.statistics "
        "WHERE table_schema = DATABASE() AND table_name = :table AND index_name = :idx"
    ), {"table": table_name, "idx": index_name})
    return result.scalar() > 0


def upgrade():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        if not index_exists(conn, "idx_pinyin_birth_composite", "empi_master"):
            conn.execute(text(
                "CREATE INDEX idx_pinyin_birth_composite "
                "ON empi_master (pinyin_gender_index, birth_year_gender_index)"
            ))
            print("Created idx_pinyin_birth_composite")
        else:
            print("idx_pinyin_birth_composite already exists, skipping")

        if not index_exists(conn, "idx_status_pinyin", "empi_master"):
            conn.execute(text(
                "CREATE INDEX idx_status_pinyin "
                "ON empi_master (status, pinyin_gender_index)"
            ))
            print("Created idx_status_pinyin")
        else:
            print("idx_status_pinyin already exists, skipping")

        conn.commit()


if __name__ == '__main__':
    upgrade()
    print("Migration complete: composite indexes added")
