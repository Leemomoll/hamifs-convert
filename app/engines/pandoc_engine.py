"""Pandoc 封装：Markdown/HTML/txt/Word 通用互转（GPL-2.0+，独立子进程调用，不传染自有代码）。"""
import shutil
import subprocess
from pathlib import Path

from app.config import get_settings

# md -> pdf 依赖 latex 引擎，容器内未装时给出清晰报错
_PDF_NOTE = "pandoc 生成 PDF 需要 LaTeX（或改用 md -> html -> pdf 链路）"


def convert(src: Path, target_format: str, out_dir: Path) -> Path:
    if shutil.which("pandoc") is None:
        raise RuntimeError("未找到 pandoc 可执行文件，请安装（Docker 镜像内已内置）")
    settings = get_settings()
    out = out_dir / f"{src.stem}.{target_format}"
    cmd = ["pandoc", str(src), "-o", str(out)]
    if target_format == "pdf":
        # 优先用 wkhtmltopdf（若镜像内存在），否则交给 pandoc 默认 latex
        if shutil.which("wkhtmltopdf"):
            cmd += ["--pdf-engine", "wkhtmltopdf"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=settings.TASK_TIMEOUT_SECONDS)
    except FileNotFoundError:
        raise RuntimeError("pandoc 执行失败：可执行文件不可用")
    if result.returncode != 0 or not out.exists():
        msg = result.stderr or result.stdout or "no output"
        if target_format == "pdf":
            msg += f"（提示：{_PDF_NOTE}）"
        raise RuntimeError(f"Pandoc 转换失败: {msg}")
    return out
