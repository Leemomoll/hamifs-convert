"""Pandoc 封装：Markdown/HTML/txt/Word 通用互转（GPL-2.0+，独立子进程调用，不传染自有代码）。"""
import shutil
import subprocess
from pathlib import Path

from app.config import get_settings
from app.engines import libreoffice


def convert(src: Path, target_format: str, out_dir: Path) -> Path:
    if shutil.which("pandoc") is None:
        raise RuntimeError("未找到 pandoc 可执行文件，请安装（Docker 镜像内已内置）")
    settings = get_settings()

    # Markdown/HTML/txt -> pdf：不依赖 1GB 级的 LaTeX，走两段链路
    # pandoc 先转 docx（保留样式），LibreOffice 再 docx -> pdf（noto-cjk 字体保证中文正常）
    if target_format == "pdf":
        return _pdf_via_docx(src, out_dir, settings)

    out = out_dir / f"{src.stem}.{target_format}"
    cmd = ["pandoc", str(src), "-o", str(out)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=settings.TASK_TIMEOUT_SECONDS)
    except FileNotFoundError:
        raise RuntimeError("pandoc 执行失败：可执行文件不可用")
    if result.returncode != 0 or not out.exists():
        msg = result.stderr or result.stdout or "no output"
        raise RuntimeError(f"Pandoc 转换失败: {msg}")
    return out


def _pdf_via_docx(src: Path, out_dir: Path, settings) -> Path:
    tmp_docx = out_dir / f"{src.stem}.docx"
    try:
        result = subprocess.run(
            ["pandoc", str(src), "-o", str(tmp_docx)],
            capture_output=True, text=True, timeout=settings.TASK_TIMEOUT_SECONDS,
        )
        if result.returncode != 0 or not tmp_docx.exists():
            msg = result.stderr or result.stdout or "no output"
            raise RuntimeError(f"Pandoc 转换失败: {msg}")
        return libreoffice.convert(tmp_docx, "pdf", out_dir)
    finally:
        # 中间产物清理，避免与正式结果混淆
        tmp_docx.unlink(missing_ok=True)
