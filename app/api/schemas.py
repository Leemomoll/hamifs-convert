"""请求/响应模型，字段形状对齐前端 api/convert.js 的 mock。"""
from typing import Optional

from pydantic import BaseModel


class TaskOut(BaseModel):
    taskId: str
    sourceName: str
    sourceFormat: str
    targetFormat: str
    status: str
    progress: int
    error: Optional[str] = None
    createdAt: float


class TaskDetailOut(TaskOut):
    resultKey: Optional[str] = None
    resultName: Optional[str] = None
