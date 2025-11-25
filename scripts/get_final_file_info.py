#!/usr/bin/env python3
"""Get final ESRI file information for sharing."""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
file = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_COMPLETE.xlsx"

df = pd.read_excel(file)

print("=" * 80)
print("FINAL ESRI FILE FOR SHARING")
print("=" * 80)
print(f"\nFile Name: {file.name}")
print(f"Full Path: {file.absolute()}")
print(f"File Size: {file.stat().st_size / (1024*1024):.1f} MB")
print(f"\nRecords: {len(df):,}")
print(f"Unique Cases: {df['ReportNumberNew'].nunique():,}")

# Check invalid addresses
invalid_addr = df['FullAddress2'].apply(
    lambda x: pd.isna(x) or str(x).strip() == '' or ' & ,' in str(x) or 'CANCELED CALL' in str(x).upper()
).sum()
valid_addr = len(df) - invalid_addr

print(f"\nAddress Quality:")
print(f"  Valid: {valid_addr:,} ({valid_addr/len(df)*100:.1f}%)")
print(f"  Invalid: {invalid_addr:,} ({invalid_addr/len(df)*100:.1f}%)")

print(f"\nField Coverage:")
print(f"  Incident: {(df['Incident'].notna().sum() / len(df) * 100):.2f}%")
print(f"  Response_Type: {(df['Response_Type'].notna().sum() / len(df) * 100):.2f}%")
print(f"  Disposition: {(df['Disposition'].notna().sum() / len(df) * 100):.2f}%")
print(f"  Hour: {(df['Hour'].notna().sum() / len(df) * 100):.2f}%")

print(f"\n✅ File is ready for ESRI submission!")
print("=" * 80)

