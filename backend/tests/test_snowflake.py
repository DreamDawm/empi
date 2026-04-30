import pytest
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

def test_snowflake_singleton():
    generator1 = SnowflakeIdGenerator()
    generator2 = SnowflakeIdGenerator()
    assert generator1 is generator2