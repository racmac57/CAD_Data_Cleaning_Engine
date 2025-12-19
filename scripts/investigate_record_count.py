#!/usr/bin/env python3
"""Investigate the record count discrepancy."""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Files to check
raw_file = BASE_DIR / "data" / "01_raw" / "2025_11_21_2019_2025_11_21_ALL_CAD_Data.xlsx"
esri_source_file = BASE_DIR / "ref" / "2019_2025_11_17_Updated_CAD_Export.xlsx"
esri_final_file = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected_DEDUPED.xlsx"

print("=" * 80)
print("RECORD COUNT INVESTIGATION")
print("=" * 80)

# Check raw file
print(f"\n1. Raw CAD File (what you're comparing to):")
if raw_file.exists():
    raw_df = pd.read_excel(raw_file)
    print(f"   File: {raw_file.name}")
    print(f"   Records: {len(raw_df):,}")
    print(f"   Unique cases: {raw_df['ReportNumberNew'].nunique():,}")
else:
    print(f"   File not found: {raw_file}")

# Check ESRI source file (what ESRI was actually built from)
print(f"\n2. ESRI Source File (what ESRI was built from):")
if esri_source_file.exists():
    source_df = pd.read_excel(esri_source_file)
    print(f"   File: {esri_source_file.name}")
    print(f"   Records: {len(source_df):,}")
    print(f"   Unique cases: {source_df['ReportNumberNew'].nunique():,}")
else:
    print(f"   File not found: {esri_source_file}")

# Check final ESRI file
print(f"\n3. Final ESRI File (deduplicated):")
if esri_final_file.exists():
    esri_df = pd.read_excel(esri_final_file)
    print(f"   File: {esri_final_file.name}")
    print(f"   Records: {len(esri_df):,}")
    print(f"   Unique cases: {esri_df['ReportNumberNew'].nunique():,}")
else:
    print(f"   File not found: {esri_final_file}")

# Compare
if esri_source_file.exists() and esri_final_file.exists():
    print(f"\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    
    source_df = pd.read_excel(esri_source_file)
    esri_df = pd.read_excel(esri_final_file)
    
    print(f"\nESRI Source → Final:")
    print(f"   Records: {len(source_df):,} → {len(esri_df):,} (difference: {len(source_df) - len(esri_df):,})")
    print(f"   Cases: {source_df['ReportNumberNew'].nunique():,} → {esri_df['ReportNumberNew'].nunique():,}")
    
    if raw_file.exists():
        print(f"\nRaw File vs ESRI Source:")
        print(f"   Raw records: {len(raw_df):,}")
        print(f"   ESRI source records: {len(source_df):,}")
        print(f"   Difference: {len(raw_df) - len(source_df):,}")
        print(f"\n   ⚠️  These are DIFFERENT source files!")
        print(f"   The ESRI file was built from '{esri_source_file.name}',")
        print(f"   NOT from '{raw_file.name}'")

