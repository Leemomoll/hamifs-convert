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
    # 已结束任务保留时长与总量上限，防止长期运行内存无限增长
    FINISHED_TTL_SECONDS = 6 * 3600
    MAX_TASKS = 500

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
            self._purge_locked()
            self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Optional[ConvertTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def list(self) -> list[ConvertTask]:
        with self._lock:
            self._purge_locked()
            return sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)

    def _purge_locked(self) -> None:
        """清理过期已结束任务；总量超限时淘汰最老的已结束任务。须持锁调用。"""
        now = time.time()
        finished = [t for t in self._tasks.values() if t.status in (TaskStatus.SUCCESS, TaskStatus.FAILED)]
        for t in finished:
            if now - t.created_at > self.FINISHED_TTL_SECONDS:
                self._tasks.pop(t.id, None)
        if len(self._tasks) > self.MAX_TASKS:
            finished.sort(key=lambda t: t.created_at)
            for t in finished:
                if len(self._tasks) <= self.MAX_TASKS:
                    break
                self._tasks.pop(t.id, None)


store = TaskStore()
