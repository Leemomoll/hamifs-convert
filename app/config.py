from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 服务
    APP_NAME: str = "hamifs-convert"
    HOST: str = "0.0.0.0"
    PORT: int = 8100

    # 任务限制（对齐技术方案：单任务超时 120s，上传 <=100MB）
    TASK_TIMEOUT_SECONDS: int = 120
    MAX_UPLOAD_MB: int = 100
    MAX_CONCURRENCY: int = 4

    # 存储后端：local（开发期默认） | s3（MinIO / 云 OSS）
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_DIR: str = "./data"
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "hamifs-convert"
    PRESIGN_EXPIRES_SECONDS: int = 3600

    # Celery（可选：不配置则用进程内后台线程执行）
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
