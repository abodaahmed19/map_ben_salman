import pandas as pd
from pathlib import Path

xlsx = Path(r"C:\Users\Eng Abdelatif\Downloads\الوضع الحالي للتكاليف الخاصة بالمحور تعديل 9=2-1448.xlsx")
out_path = Path(__file__).resolve().parent / "xlsx_report.txt"
xl = pd.ExcelFile(xlsx)
lines = [f"SHEETS: {xl.sheet_names}"]
for name in xl.sheet_names:
    df = pd.read_excel(xlsx, sheet_name=name, header=None)
    lines.append(f"\n=== {name} shape {df.shape} ===")
    lines.append(df.head(40).to_string())
    lines.append("--- tail ---")
    lines.append(df.tail(25).to_string())
out_path.write_text("\n".join(lines), encoding="utf-8")
print("written", out_path)
