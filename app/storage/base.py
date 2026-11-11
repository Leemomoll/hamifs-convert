"""存储后端抽象：本地目录（开发期）或 S3 协议（MinIO / 云 OSS）。"""
import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from fastapi import UploadFile


class Storage(ABC):
    @abstractmethod
    def save_upload(self, file: UploadFile, key: str) -> str:
        """保存上传文件，返回存储 key。"""

    @abstractmethod
    def fetch(self, key: str, dest_dir: Path) -> Path:
        """把文件取到本地临时目录，返回本地路径（引擎只认本地文件）。"""

    @abstractmethod
    def save_result(self, local_path: Path, key: str) -> str:
        """保存转换结果，返回存储 key。"""

    @abstractmethod
    def presign_download(self, key: str, filename: str) -> Optional[str]:
        """生成下载 URL；本地后端返回 None（由 API 直接回文件流）。"""

    @abstractmethod
    def local_path(self, key: str) -> Path:
        """本地后端：返回文件路径；s3 后端不支持（下载走预签名）。"""


class LocalStorage(Storage):
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError(f"非法存储 key: {key}")
        return path

    def save_upload(self, file: UploadFile, key: str) -> str:
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return key

    def fetch(self, key: str, dest_dir: Path) -> Path:
        src = self._resolve(key)
        dest = dest_dir / Path(key).name
        shutil.copy2(src, dest)
        return dest

    def save_result(self, local_path: Path, key: str) -> str:
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest)
        return key

    def presign_download(self, key: str, filename: str) -> Optional[str]:
        return None

    def local_path(self, key: str) -> Path:
        return self._resolve(key)


class S3Storage(Storage):
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str) -> None:
        import boto3

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        # bucket 不存在则自动创建（MinIO 本地开发场景）
        from botocore.exceptions import ClientError

        try:
            self.client.head_bucket(Bucket=bucket)
        except ClientError:
            self.client.create_bucket(Bucket=bucket)

    def save_upload(self, file: UploadFile, key: str) -> str:
        self.client.upload_fileobj(file.file, self.bucket, key)
        return key

    def fetch(self, key: str, dest_dir: Path) -> Path:
        dest = dest_dir / Path(key).name
        self.client.download_file(self.bucket, key, str(dest))
        return dest

    def save_result(self, local_path: Path, key: str) -> str:
        self.client.upload_file(str(local_path), self.bucket, key)
        return key

    def presign_download(self, key: str, filename: str) -> Optional[str]:
        from app.config import get_settings

        url = self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=get_settings().PRESIGN_EXPIRES_SECONDS,
        )
        return url

    def local_path(self, key: str) -> Path:
        raise RuntimeError("s3 后端请使用预签名 URL 下载")


def new_task_id() -> str:
    return uuid.uuid4().hex[:12]
