"""文档文本提取：复用项目内已有的解析能力，按扩展名分发。

支持：txt/md（直接读）、pdf（pypdfium2 文本层）、docx（mammoth 原文提取）、
xlsx（openpyxl 逐行）、doc/pptx/html（pandoc 转 plain，需本机装 pandoc）。
扫描版 PDF（无文本层）返回空串并提示需要 OCR —— 二期接入。
"""
import subprocess
import tempfile
from pathlib import Path

from app.config import get_settings

TEXT_EXTS = {".txt", ".md", ".markdown"}


def extract_text(data: bytes, file_name: str) -> str:
    ext = Path(file_name).suffix.lower()

    if ext in TEXT_EXTS:
        return data.decode("utf-8", errors="ignore")

    if ext == ".pdf":
        return _pdf_text(data)

    if ext == ".docx":
        return _docx_text(data)

    if ext == ".xlsx":
        return _xlsx_text(data)

    if ext in {".doc", ".pptx", ".ppt", ".html", ".htm"}:
        return _pandoc_text(data, ext)

    raise ValueError(f"暂不支持从 {ext or '无扩展名'} 文件提取文本")


def _pdf_text(data: bytes) -> str:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    parts: list[str] = []
    for page in pdf:
        text_page = page.get_textpage()
        parts.append(text_page.get_text_bounded())
        text_page.close()
        page.close()
    pdf.close()
    return "\n".join(parts)


def _docx_text(data: bytes) -> str:
    import io

    import mammoth

    result = mammoth.extract_raw_text(io.BytesIO(data))
    return result.value


def _xlsx_text(data: bytes) -> str:
    import io

    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    lines: list[str] = []
    for ws in wb.worksheets:
        lines.append(f"[工作表: {ws.title}]")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                lines.append(" | ".join(cells))
    wb.close()
    return "\n".join(lines)


def _pandoc_text(data: bytes, ext: str) -> str:
    """doc/ppt/html 走 pandoc 转 plain text；pandoc 未安装则明确报错。"""
    s = get_settings()
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"input{ext}"
        dst = Path(tmp) / "out.txt"
        src.write_bytes(data)
        try:
            subprocess.run(
                ["pandoc", str(src), "-t", "plain", "-o", str(dst)],
                check=True, capture_output=True, timeout=s.TASK_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as e:
            raise ValueError("本机未安装 pandoc，无法提取该格式文本（容器镜像内已内置）") from e
        except subprocess.CalledProcessError as e:
            raise ValueError(f"pandoc 解析失败：{e.stderr.decode(errors='ignore')[:200]}") from e
        return dst.read_text("utf-8", errors="ignore")
