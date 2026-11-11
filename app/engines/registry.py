"""转换方向注册表：(源格式, 目标格式) -> 引擎名。"""
from typing import Callable, Optional
from pathlib import Path

from app.engines import libreoffice, mammoth_engine, openpyxl_engine, pandoc_engine, pdf2docx_engine, pdfium_engine

CONVERSION_MATRIX: dict[tuple[str, str], str] = {
    # LibreOffice：Office 互转 / 转 PDF（还原度最高的主力方案）
    ("docx", "pdf"): "libreoffice",
    ("doc", "pdf"): "libreoffice",
    ("xlsx", "pdf"): "libreoffice",
    ("pptx", "pdf"): "libreoffice",
    # mammoth：docx -> html/md（轻量、语义好，便于进入 RAG 流程）
    ("docx", "html"): "mammoth",
    ("docx", "md"): "mammoth",
    # pdf2docx：PDF -> Word
    ("pdf", "docx"): "pdf2docx",
    # pypdfium2：PDF -> 图片
    ("pdf", "png"): "pdfium",
    # openpyxl：xlsx -> csv
    ("xlsx", "csv"): "openpyxl",
}

# pandoc 兜底：Markdown/HTML/txt 相关的通用互转
_PANDOC_PAIRS = [
    ("md", "docx"), ("md", "html"), ("md", "pdf"),
    ("html", "md"), ("html", "docx"), ("html", "pdf"),
    ("docx", "txt"), ("pdf", "txt"), ("md", "txt"),
    ("txt", "docx"), ("txt", "pdf"), ("txt", "html"),
]
for s, t in _PANDOC_PAIRS:
    CONVERSION_MATRIX[(s, t)] = "pandoc"

_ENGINES: dict[str, Callable[[Path, str, Path], Path]] = {
    "libreoffice": libreoffice.convert,
    "pandoc": pandoc_engine.convert,
    "pdf2docx": pdf2docx_engine.convert,
    "pdfium": pdfium_engine.convert,
    "openpyxl": openpyxl_engine.convert,
    "mammoth": mammoth_engine.convert,
}


def resolve_engine(source_format: str, target_format: str) -> Optional[Callable[[Path, str, Path], Path]]:
    """返回 (源路径, 目标格式, 输出目录) -> 输出文件路径 的转换函数；不支持则返回 None。"""
    engine_name = CONVERSION_MATRIX.get((source_format.lower(), target_format.lower()))
    if engine_name is None:
        return None
    return _ENGINES[engine_name]


def supported_targets(source_format: str) -> list[str]:
    return sorted(t for s, t in CONVERSION_MATRIX if s == source_format.lower())
