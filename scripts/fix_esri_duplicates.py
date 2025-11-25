#!/usr/bin/env python3
"""
Fix duplicate corruption in ESRI file.
Deduplicate while preserving legitimate multi-record cases.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent

ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected.xlsx"
OUTPUT_DIR = BASE_DIR / "data" / "ESRI_CADExport"

print("=" * 80)
print("FIXING ESRI DUPLICATE CORRUPTION")
print("=" * 80)

# Load ESRI file
print(f"\nLoading ESRI file...")
df = pd.read_excel(ESRI_FILE)
print(f"Original records: {len(df):,}")
print(f"Unique cases: {df['ReportNumberNew'].nunique():,}")

# Identify duplicates
duplicate_mask = df.duplicated(subset=['ReportNumberNew'], keep=False)
duplicate_count = duplicate_mask.sum()
print(f"\nDuplicate records: {duplicate_count:,}")

# Strategy: For each case, keep unique combinations of key fields
# This preserves legitimate duplicates (same case, different incidents/times)
# but removes identical duplicates

print("\nDeduplicating...")
print("  Strategy: Keep unique combinations of ReportNumberNew + Incident + TimeOfCall + FullAddress2")

# Create deduplication key
df['_dedup_key'] = (
    df['ReportNumberNew'].astype(str) + '|' +
    df['Incident'].astype(str) + '|' +
    df['TimeOfCall'].astype(str) + '|' +
    df['FullAddress2'].astype(str)
)

# Count before
before_count = len(df)
unique_keys = df['_dedup_key'].nunique()

# Remove duplicates, keeping first occurrence
df_deduped = df.drop_duplicates(subset=['_dedup_key'], keep='first')

# Remove helper column
df_deduped = df_deduped.drop(columns=['_dedup_key'])

after_count = len(df_deduped)
removed = before_count - after_count

print(f"\nResults:")
print(f"  Before: {before_count:,} records")
print(f"  After: {after_count:,} records")
print(f"  Removed: {removed:,} duplicate records ({removed/before_count*100:.1f}%)")
print(f"  Unique cases: {df_deduped['ReportNumberNew'].nunique():,}")

# Check worst case again
dup_counts = df_deduped.groupby('ReportNumberNew').size()
print(f"\nDuplicate check after deduplication:")
print(f"  Max duplicates per case: {dup_counts.max()}")
print(f"  Cases with >10 duplicates: {(dup_counts > 10).sum()}")

# Create backup
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = OUTPUT_DIR / f"CAD_ESRI_Final_20251124_corrected_BACKUP_{timestamp}.xlsx"
print(f"\nCreating backup: {backup_file.name}")
df.to_excel(backup_file, index=False, engine='openpyxl')

# Save deduplicated file
output_file = OUTPUT_DIR / "CAD_ESRI_Final_20251124_corrected_DEDUPED.xlsx"
print(f"Saving deduplicated file: {output_file.name}")
df_deduped.to_excel(output_file, index=False, engine='openpyxl')

print(f"\n" + "=" * 80)
print("DEDUPLICATION COMPLETE")
print("=" * 80)
print(f"Backup: {backup_file}")
print(f"Deduplicated file: {output_file}")
print(f"Records removed: {removed:,}")

