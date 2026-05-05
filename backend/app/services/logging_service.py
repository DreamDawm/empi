import asyncio
import json
import queue
import threading
from datetime import datetime
from typing import Optional, AsyncGenerator
from app.core.logger import get_logger

logger = get_logger("empi.etl")

class ETLLoggingService:
    _instance: Optional['ETLLoggingService'] = None
    _queue: queue.Queue = queue.Queue()
    _subscribers: list = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._running = False
            cls._instance._thread: Optional[threading.Thread] = None
        return cls._instance

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._process_logs, daemon=True)
            self._thread.start()
            logger.info("ETL logging service started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        logger.info("ETL logging service stopped")

    def log(self, level: str, message: str, patient_id: Optional[str] = None):
        """记录日志"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'patient_id': patient_id
        }
        self._queue.put(entry)
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[{patient_id}] {message}" if patient_id else message)

    def info(self, message: str, patient_id: Optional[str] = None):
        self.log('INFO', message, patient_id)

    def error(self, message: str, patient_id: Optional[str] = None):
        self.log('ERROR', message, patient_id)

    def warning(self, message: str, patient_id: Optional[str] = None):
        self.log('WARNING', message, patient_id)

    def clear_queue(self):
        """Clear the log queue (for testing)"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    async def stream_logs(self) -> AsyncGenerator[str, None]:
        """SSE流式日志"""
        q: asyncio.Queue = asyncio.Queue()

        async def put_log():
            while True:
                entry = await asyncio.get_event_loop().run_in_executor(None, self._queue.get)
                await q.put(f"data: {json.dumps(entry)}\n\n")

        task = asyncio.create_task(put_log())
        try:
            while True:
                data = await asyncio.wait_for(q.get(), timeout=30)
                yield data
        except asyncio.TimeoutError:
            yield f"data: {{'event': 'heartbeat', 'timestamp': '{datetime.now().isoformat()}'}}\n\n"
        finally:
            task.cancel()

    def _process_logs(self):
        while self._running:
            try:
                entry = self._queue.get(timeout=0.1)
                for subscriber in self._subscribers:
                    subscriber.put(entry)
            except queue.Empty:
                continue

logging_service = ETLLoggingService()