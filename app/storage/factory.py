from app.config import get_settings
from app.storage.base import LocalStorage, S3Storage

_cache: list = []


def get_storage():
    """按配置返回存储后端（进程内单例）。"""
    if _cache:
        return _cache[0]
    settings = get_settings()
    if settings.STORAGE_BACKEND == "s3":
        storage = S3Storage(
            endpoint=settings.S3_ENDPOINT,
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            bucket=settings.S3_BUCKET,
        )
    else:
        storage = LocalStorage(settings.LOCAL_STORAGE_DIR)
    _cache.append(storage)
    return storage
