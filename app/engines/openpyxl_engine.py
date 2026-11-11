"""openpyxl 封装：xlsx -> csv（默认导出第一个工作表）。"""
import csv
from pathlib import Path

from openpyxl import load_workbook


def convert(src: Path, target_format: str, out_dir: Path) -> Path:
    wb = load_workbook(str(src), read_only=True, data_only=True)
    try:
        ws = wb.worksheets[0]
        out = out_dir / f"{src.stem}.csv"
        with open(out, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            for row in ws.iter_rows(values_only=True):
                writer.writerow(["" if v is None else v for v in row])
    finally:
        wb.close()
    return out
