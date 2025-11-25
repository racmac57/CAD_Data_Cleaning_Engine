#!/usr/bin/env python3
"""Check why ESRI file has more records than raw CAD file."""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

raw_file = BASE_DIR / "data" / "01_raw" / "2025_11_21_2019_2025_11_21_ALL_CAD_Data.xlsx"
esri_file = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected.xlsx"

print("=" * 80)
print("RECORD COUNT DISCREPANCY ANALYSIS")
print("=" * 80)

# Load raw file
print(f"\nLoading raw CAD file...")
raw_df = pd.read_excel(raw_file)
print(f"Raw CAD file: {len(raw_df):,} records")
print(f"Unique ReportNumberNew in raw: {raw_df['ReportNumberNew'].nunique():,}")

# Load ESRI file
print(f"\nLoading ESRI file...")
esri_df = pd.read_excel(esri_file)
print(f"ESRI file: {len(esri_df):,} records")
print(f"Unique ReportNumberNew in ESRI: {esri_df['ReportNumberNew'].nunique():,}")

# Check for duplicates
print(f"\nDuplicate analysis:")
duplicate_cases = esri_df[esri_df.duplicated(subset=['ReportNumberNew'], keep=False)]
print(f"Records with duplicate ReportNumberNew: {len(duplicate_cases):,}")

if len(duplicate_cases) > 0:
    print(f"\nSample duplicate cases:")
    sample_dups = duplicate_cases.groupby('ReportNumberNew').size().sort_values(ascending=False).head(10)
    print(sample_dups)
    
    print(f"\nExample of duplicate case:")
    example_case = sample_dups.index[0]
    example_records = esri_df[esri_df['ReportNumberNew'] == example_case]
    print(f"\nCase {example_case} appears {len(example_records)} times:")
    print(example_records[['ReportNumberNew', 'Incident', 'TimeOfCall', 'FullAddress2']].head())

# Calculate difference
difference = len(esri_df) - len(raw_df)
print(f"\n" + "=" * 80)
print(f"SUMMARY")
print("=" * 80)
print(f"Raw CAD records: {len(raw_df):,}")
print(f"ESRI records: {len(esri_df):,}")
print(f"Difference: {difference:,} records")
print(f"Unique cases in raw: {raw_df['ReportNumberNew'].nunique():,}")
print(f"Unique cases in ESRI: {esri_df['ReportNumberNew'].nunique():,}")
print(f"Case count difference: {esri_df['ReportNumberNew'].nunique() - raw_df['ReportNumberNew'].nunique():,}")

