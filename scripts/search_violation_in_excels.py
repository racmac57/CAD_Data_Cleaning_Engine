import os
from pathlib import Path

import pandas as pd

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
SEARCH_ROOT = BASE_DIR  # or BASE_DIR / "data" / "01_raw", etc.
TARGETS = [
    "Violation FRO - 2C:29-9b",
    "Violation TRO - 2C:29-9b",
]

def scan_file(path: Path):
    print(f"\nScanning: {path}")
    try:
        # Try all sheets
        xls = pd.ExcelFile(path)
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name, dtype=str)
            df = df.fillna("")
            for target in TARGETS:
                mask = df.apply(lambda col: col.str.contains(target, case=False, na=False))
                hits = mask.any(axis=1)
                if hits.any():
                    print(f"  Found '{target}' in sheet '{sheet_name}' at rows: "
                          f"{', '.join(str(i+1) for i in df.index[hits])}")
    except Exception as e:
        print(f"  Error reading {path}: {e}")

def main():
    for root, _, files in os.walk(SEARCH_ROOT):
        for name in files:
            if name.lower().endswith((".xlsx", ".xls")):
                scan_file(Path(root) / name)

if __name__ == "__main__":
    main()