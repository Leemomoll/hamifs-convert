"""pdf2docx 封装：PDF -> Word（AGPL-3.0，开源无碍，闭源商用需商业授权）。

只能提取文本层；扫描版（图片型）PDF 需 OCR，为二期扩展。
"""
from pathlib import Path


def convert(src: Path, target_format: str, out_dir: Path) -> Path:
    from pdf2docx import Converter

    out = out_dir / f"{src.stem}.docx"
    cv = Converter(str(src))
    try:
        cv.convert(str(out))
    finally:
        cv.close()
    if not out.exists():
        raise RuntimeError("pdf2docx 转换失败：未生成输出文件（若为扫描版 PDF，请先 OCR）")
    return out
