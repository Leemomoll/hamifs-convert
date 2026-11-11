"""Celery 任务入口（配置了 broker 时由 routes.py 派发）。"""
from app.tasks.celery_app import celery
from app.tasks.runner import run_task


@celery.task(name="app.tasks.convert_tasks.convert", bind=True, max_retries=0)
def convert(self, task_id: str):
    run_task(task_id)
