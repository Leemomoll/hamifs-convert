"""任务执行器：取源文件 -> 选引擎 -> 转换 -> 结果入库 -> 更新状态。

状态机：PENDING -> RUNNING(10/50/90) -> SUCCESS(100) / FAILED
失败自动重试 1 次（对齐技术方案）。
"""
import tempfile
import traceback
from pathlib import Path

from app.config import get_settings
from app.engines.registry import resolve_engine
from app.models import TaskStatus, store
from app.storage.factory import get_storage

MAX_ATTEMPTS = 2  # 首次 + 重试 1 次


def run_task(task_id: str) -> None:
    task = store.get(task_id)
    if task is None or task.status in (TaskStatus.RUNNING, TaskStatus.SUCCESS):
        return

    task.status = TaskStatus.RUNNING
    task.attempts += 1
    task.progress = 10
    settings = get_settings()
    storage = get_storage()

    try:
        engine = resolve_engine(task.source_format, task.target_format)
        if engine is None:
            raise RuntimeError(f"不支持的转换方向: {task.source_format} -> {task.target_format}")

        with tempfile.TemporaryDirectory(prefix=f"convert-{task_id}-") as tmp:
            tmp_dir = Path(tmp)
            task.progress = 30

            src_path = storage.fetch(task.source_key, tmp_dir)
            task.progress = 50

            out_path = engine(src_path, task.target_format, tmp_dir)
            task.progress = 90

            result_key = f"results/{task_id}/{out_path.name}"
            saved_key = storage.save_result(out_path, result_key)

        task.result_key = saved_key
        task.result_name = out_path.name
        task.status = TaskStatus.SUCCESS
        task.progress = 100
        task.error = None
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        if task.attempts < MAX_ATTEMPTS:
            # 失败自动重试 1 次
            task.status = TaskStatus.PENDING
            run_task(task_id)
            return
        task.status = TaskStatus.FAILED
        task.error = str(e)[:500] or e.__class__.__name__
