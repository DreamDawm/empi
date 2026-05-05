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