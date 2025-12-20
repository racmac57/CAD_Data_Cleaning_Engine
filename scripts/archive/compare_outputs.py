#!/usr/bin/env python
"""
Compare New Outputs with Old Version and Reference
===================================================
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
POLISHED = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_POLISHED_20251219_131114.xlsx"
DRAFT = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_DRAFT_20251219_131114.xlsx"
OLD_VERSION = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v3.xlsx"
REFERENCE = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\InBox\2025_06_24_SCRPA\dashboard_data_export\ESRI_CADExport.xlsx")

print("="*80)
print("OUTPUT COMPARISON REPORT")
print("="*80)

# Polished output
polished_df = pd.read_excel(POLISHED, nrows=0)
print(f"\nPOLISHED OUTPUT:")
print(f"  File: {POLISHED.name}")
print(f"  Columns: {len(polished_df.columns)}")
print(f"  Column order: {list(polished_df.columns)}")

# Draft output
draft_df = pd.read_excel(DRAFT, nrows=0)
print(f"\nDRAFT OUTPUT:")
print(f"  File: {DRAFT.name}")
print(f"  Columns: {len(draft_df.columns)}")
print(f"  ESRI columns: {[c for c in draft_df.columns if c in polished_df.columns]}")
print(f"  Additional columns: {[c for c in draft_df.columns if c not in polished_df.columns]}")

# Old version
try:
    old_df = pd.read_excel(OLD_VERSION, nrows=0)
    print(f"\nOLD VERSION:")
    print(f"  File: {OLD_VERSION.name}")
    print(f"  Columns: {len(old_df.columns)}")
    print(f"  ESRI columns: {[c for c in old_df.columns if c in ['ReportNumberNew', 'Incident', 'How Reported', 'FullAddress2', 'Grid', 'TimeOfCall', 'cYear', 'cMonth', 'Hour', 'DayofWeek', 'Officer', 'Disposition', 'Latitude', 'Longitude']]}")
except Exception as e:
    print(f"\nOLD VERSION: Could not read ({e})")

# Reference
try:
    ref_df = pd.read_excel(REFERENCE, nrows=0)
    print(f"\nREFERENCE STRUCTURE:")
    print(f"  File: {REFERENCE.name}")
    print(f"  Columns: {len(ref_df.columns)}")
    print(f"  Column order: {list(ref_df.columns)}")
    
    # Compare
    polished_cols = list(polished_df.columns)
    ref_cols = list(ref_df.columns)
    match = polished_cols == ref_cols
    print(f"\nSTRUCTURE MATCH:")
    print(f"  Polished matches reference: {match}")
    if not match:
        missing = set(ref_cols) - set(polished_cols)
        extra = set(polished_cols) - set(ref_cols)
        if missing:
            print(f"  Missing in polished: {missing}")
        if extra:
            print(f"  Extra in polished: {extra}")
except Exception as e:
    print(f"\nREFERENCE: Could not read ({e})")

print("\n" + "="*80)

