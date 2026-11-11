"""转换任务模型与内存任务表。

P1 阶段任务记录存内存；P4 与 Java 对接后，任务持久化由 MySQL（hamifs-back）负责，
本服务只保留执行期的状态即可。
"""
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


class TaskStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class ConvertTask:
    id: str
    source_key: str
    source_name: str
    source_format: str
    target_format: str
    status: str = TaskStatus.PENDING
    progress: int = 0
    result_key: Optional[str] = None
    result_name: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0
    created_at: float = field(default_factory=time.time)


class TaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, ConvertTask] = {}
        self._lock = threading.Lock()

    def create(self, source_key: str, source_name: str, source_format: str, target_format: str) -> ConvertTask:
        task = ConvertTask(
            id=uuid.uuid4().hex[:12],
            source_key=source_key,
            source_name=source_name,
            source_format=source_format,
            target_format=target_format,
        )
        with self._lock:
            self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Optional[ConvertTask]:
        return self._tasks.get(task_id)

    def list(self) -> list[ConvertTask]:
        return sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)


store = TaskStore()
