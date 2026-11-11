"""转换任务接口。

POST   /convert/tasks          提交转换任务（multipart: file + targetFormat），返回 taskId
GET    /convert/tasks          任务列表
GET    /convert/tasks/{id}     单个任务状态与进度（前端轮询）
GET    /convert/download/{id}  下载转换结果（s3 时 302 到预签名 URL）
"""
import posixpath

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse

from app.config import get_settings
from app.engines.registry import resolve_engine, supported_targets
from app.models import TaskStatus, store
from app.api.schemas import TaskDetailOut, TaskOut
from app.storage.factory import get_storage
from app.tasks.runner import run_task

router = APIRouter(prefix="/convert")


def _to_out(task) -> TaskOut:
    return TaskOut(
        taskId=task.id,
        sourceName=task.source_name,
        sourceFormat=task.source_format,
        targetFormat=task.target_format,
        status=task.status,
        progress=task.progress,
        error=task.error,
        createdAt=task.created_at,
    )


@router.post("/tasks")
async def create_task(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    targetFormat: str = Form(...),
):
    settings = get_settings()
    target = targetFormat.lower().lstrip(".")

    source_name = posixpath.basename(file.filename or "file")
    source_format = source_name.rsplit(".", 1)[-1].lower() if "." in source_name else ""

    if not source_format:
        raise HTTPException(400, "无法识别源文件扩展名")
    if resolve_engine(source_format, target) is None:
        raise HTTPException(400, f"不支持的转换方向: {source_format} -> {target}，支持: {sorted(supported_targets(source_format))}")

    storage = get_storage()
    source_key = storage.save_upload(file, f"uploads/{source_name}")

    task = store.create(
        source_key=source_key,
        source_name=source_name,
        source_format=source_format,
        target_format=target,
    )

    if settings.CELERY_BROKER_URL:
        from app.tasks.celery_app import celery
        celery.send_task("app.tasks.convert_tasks.convert", args=[task.id])
    else:
        # 开发期：进程内后台线程执行，无需 Redis
        background.add_task(run_task, task.id)

    return {"taskId": task.id}


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks():
    return [_to_out(t) for t in store.list()]


@router.get("/tasks/{task_id}", response_model=TaskDetailOut)
def get_task(task_id: str):
    task = store.get(task_id)
    if task is None:
        raise HTTPException(404, "任务不存在")
    return TaskDetailOut(
        **_to_out(task).model_dump(),
        resultKey=task.result_key,
        resultName=task.result_name,
    )


@router.get("/download/{task_id}")
def download_result(task_id: str):
    task = store.get(task_id)
    if task is None:
        raise HTTPException(404, "任务不存在")
    if task.status != TaskStatus.SUCCESS or not task.result_key:
        raise HTTPException(409, "任务尚未完成或已失败")

    storage = get_storage()
    url = storage.presign_download(task.result_key, task.result_name or "result")
    if url:  # s3 后端：302 到预签名 URL，文件流不经过本服务
        return RedirectResponse(url)
    path = storage.local_path(task.result_key)
    return FileResponse(path, filename=task.result_name or "result")
