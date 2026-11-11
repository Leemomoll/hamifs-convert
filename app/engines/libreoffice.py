"""LibreOffice headless 封装：Office 互转 / 转 PDF。

注意：
- 重操作，进程启动慢，容器内由镜像预装 soffice；
- 并发场景建议前端/队列侧限流（MAX_CONCURRENCY），避免 soffice 实例互相干扰。
"""
import subprocess
from pathlib import Path

from app.config import get_settings


def convert(src: Path, target_format: str, out_dir: Path) -> Path:
    settings = get_settings()
    cmd = [
        "soffice", "--headless", "--norestore",
        "--convert-to", target_format,
        "--outdir", str(out_dir),
        str(src),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=settings.TASK_TIMEOUT_SECONDS)
    out = out_dir / f"{src.stem}.{target_format}"
    if result.returncode != 0 or not out.exists():
        raise RuntimeError(f"LibreOffice 转换失败: {result.stderr or result.stdout or 'no output'}")
    return out
