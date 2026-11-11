"""mammoth 封装：docx -> html / md（语义化转换，适合进入 RAG 文本流程）。"""
from pathlib import Path

import mammoth


def convert(src: Path, target_format: str, out_dir: Path) -> Path:
    out = out_dir / f"{src.stem}.{target_format}"
    with open(src, "rb") as fin:
        if target_format == "md":
            result = mammoth.convert_to_markdown(fin)
        else:
            result = mammoth.convert_to_html(fin)
    out.write_text(result.value, encoding="utf-8")
    return out
