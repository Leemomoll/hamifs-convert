"""Celery 应用（可选）。配置了 CELERY_BROKER_URL 时启用，用于削峰与多 worker 扩展。"""
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery = Celery(
    "hamifs-convert",
    broker=settings.CELERY_BROKER_URL or "redis://localhost:6379/0",
    backend=settings.CELERY_RESULT_BACKEND or "redis://localhost:6379/1",
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_time_limit=settings.TASK_TIMEOUT_SECONDS * 2,
    task_soft_time_limit=settings.TASK_TIMEOUT_SECONDS,
    worker_concurrency=2,
)

celery.autodiscover_tasks(["app.tasks"])
