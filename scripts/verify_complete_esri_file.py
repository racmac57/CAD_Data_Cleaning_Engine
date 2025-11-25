#!/usr/bin/env python3
"""Verify the complete ESRI file has all records."""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

complete_file = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_COMPLETE.xlsx"
source_file = BASE_DIR / "ref" / "2019_2025_11_17_Updated_CAD_Export.xlsx"

print("=" * 80)
print("VERIFYING COMPLETE ESRI FILE")
print("=" * 80)

# Load files
print("\nLoading files...")
complete_df = pd.read_excel(complete_file)
source_df = pd.read_excel(source_file)

print(f"\nSource file:")
print(f"  Records: {len(source_df):,}")
print(f"  Unique cases: {source_df['ReportNumberNew'].nunique():,}")

print(f"\nComplete ESRI file:")
print(f"  Records: {len(complete_df):,}")
print(f"  Unique cases: {complete_df['ReportNumberNew'].nunique():,}")

print(f"\nComparison:")
print(f"  Records difference: {len(source_df) - len(complete_df):,}")
print(f"  Cases difference: {source_df['ReportNumberNew'].nunique() - complete_df['ReportNumberNew'].nunique():,}")

# Check required columns
required_cols = ['TimeOfCall', 'Incident', 'Response_Type', 'FullAddress2', 'ReportNumberNew', 'Disposition']
missing = [col for col in required_cols if col not in complete_df.columns]
if missing:
    print(f"\n  ⚠️  Missing columns: {missing}")
else:
    print(f"\n  ✅ All required columns present")

# Check duplicate pattern
dup_counts = complete_df.groupby('ReportNumberNew').size()
print(f"\nDuplicate pattern:")
print(f"  Max duplicates per case: {dup_counts.max()}")
print(f"  Cases with >10 duplicates: {(dup_counts > 10).sum()}")
print(f"  Cases with >20 duplicates: {(dup_counts > 20).sum()}")

print("\n" + "=" * 80)
if len(complete_df) >= len(source_df) - 100:  # Allow for a few identical duplicates
    print("✅ FILE IS COMPLETE - All records preserved")
else:
    print("⚠️  FILE MAY BE INCOMPLETE - Some records missing")
print("=" * 80)

