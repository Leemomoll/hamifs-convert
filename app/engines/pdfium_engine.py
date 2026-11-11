"""pypdfium2 封装：PDF -> PNG（Apache-2.0/BSD，可放心商用）。

多页 PDF 输出 zip；单页直接输出 png。
"""
import zipfile
from pathlib import Path

import pypdfium2 as pdfium

SCALE = 2.0  # 约 144 DPI


def convert(src: Path, target_format: str, out_dir: Path) -> Path:
    pdf = pdfium.PdfDocument(str(src))
    try:
        paths: list[Path] = []
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=SCALE)
            pil_image = bitmap.to_pil()
            p = out_dir / f"{src.stem}-{i + 1}.png"
            pil_image.save(p)
            paths.append(p)
    finally:
        pdf.close()

    if not paths:
        raise RuntimeError("PDF 无可渲染页面")

    if len(paths) == 1:
        out = out_dir / f"{src.stem}.png"
        paths[0].rename(out)
        return out

    out = out_dir / f"{src.stem}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            zf.write(p, arcname=p.name)
    return out
