#!/usr/bin/env python3
"""
Rebuild ESRI file from source, preserving ALL legitimate records.
Only removes completely identical duplicates (all columns match).
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent

# Source file (the one ESRI was built from)
SOURCE_FILE = BASE_DIR / "ref" / "2019_2025_11_17_Updated_CAD_Export.xlsx"

# Current corrupted ESRI file (to apply corrections from)
CORRUPTED_ESRI = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected.xlsx"

# Output
OUTPUT_DIR = BASE_DIR / "data" / "ESRI_CADExport"
OUTPUT_FILE = OUTPUT_DIR / "CAD_ESRI_Final_20251124_COMPLETE.xlsx"

print("=" * 80)
print("REBUILDING ESRI FILE WITH ALL RECORDS")
print("=" * 80)

# Load source file
print(f"\nLoading source file: {SOURCE_FILE.name}")
source_df = pd.read_excel(SOURCE_FILE)
print(f"  Loaded {len(source_df):,} records")
print(f"  Unique cases: {source_df['ReportNumberNew'].nunique():,}")

# Check for completely identical duplicates (all columns match)
print("\nChecking for completely identical duplicates...")
before_dedup = len(source_df)

# Remove only completely identical records (all columns match)
df_cleaned = source_df.copy()
df_cleaned = df_cleaned.drop_duplicates(keep='first')

after_dedup = len(df_cleaned)
identical_removed = before_dedup - after_dedup

print(f"  Before: {before_dedup:,} records")
print(f"  After removing identical: {after_dedup:,} records")
print(f"  Removed: {identical_removed:,} completely identical duplicates")

# Verify we have all unique cases
print(f"\nUnique cases preserved: {df_cleaned['ReportNumberNew'].nunique():,}")

# Check if we need to apply corrections from the corrupted file
# (The corrupted file has address corrections applied)
if CORRUPTED_ESRI.exists():
    print(f"\nChecking if corrections need to be applied from: {CORRUPTED_ESRI.name}")
    corrupted_df = pd.read_excel(CORRUPTED_ESRI)
    
    # The corrupted file has corrections but also has duplicates
    # We'll use it as a reference for corrected addresses, but rebuild from source
    
    # Create a lookup of corrected addresses (one per case, take first occurrence)
    corrupted_lookup = corrupted_df.groupby('ReportNumberNew').first()
    address_corrections = corrupted_lookup['FullAddress2'].to_dict()
    
    # Apply address corrections where they differ
    df_cleaned = df_cleaned.copy()  # Avoid SettingWithCopyWarning
    df_cleaned['FullAddress2_Original'] = df_cleaned['FullAddress2'].copy()
    df_cleaned['_corrected_address'] = df_cleaned['ReportNumberNew'].map(address_corrections)
    
    # Only update if correction exists and is different
    mask = df_cleaned['_corrected_address'].notna() & (df_cleaned['FullAddress2'] != df_cleaned['_corrected_address'])
    corrections_applied = mask.sum()
    
    if corrections_applied > 0:
        df_cleaned.loc[mask, 'FullAddress2'] = df_cleaned.loc[mask, '_corrected_address']
        print(f"  Applied {corrections_applied:,} address corrections")
    
    df_cleaned = df_cleaned.drop(columns=['FullAddress2_Original', '_corrected_address'], errors='ignore')

# Ensure ESRI columns are present
esri_columns = [
    'TimeOfCall', 'cYear', 'cMonth', 'Hour', 'DayofWeek',
    'Incident', 'Response_Type', 'How Reported',
    'FullAddress2', 'Grid', 'PDZone',
    'Officer', 'Disposition', 'ReportNumberNew',
    'Latitude', 'Longitude', 'data_quality_flag'
]

# Rename columns if needed
column_map = {
    'Time of Call': 'TimeOfCall',
    'Response Type': 'Response_Type',
    'HourMinuetsCalc': 'Hour'
}

df_cleaned = df_cleaned.rename(columns=column_map)

# Ensure all ESRI columns exist
for col in esri_columns:
    if col not in df_cleaned.columns:
        df_cleaned[col] = None

# Select only ESRI columns
df_final = df_cleaned[esri_columns].copy()

# Create backup
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = OUTPUT_DIR / f"CAD_ESRI_Final_20251124_COMPLETE_BACKUP_{timestamp}.xlsx"
print(f"\nCreating backup: {backup_file.name}")
df_final.to_excel(backup_file, index=False, engine='openpyxl')

# Save final file
print(f"Saving complete ESRI file: {OUTPUT_FILE.name}")
df_final.to_excel(OUTPUT_FILE, index=False, engine='openpyxl')

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Source records: {len(source_df):,}")
print(f"Final records: {len(df_final):,}")
print(f"Identical duplicates removed: {identical_removed:,}")
print(f"Unique cases: {df_final['ReportNumberNew'].nunique():,}")
print(f"\nFile saved: {OUTPUT_FILE}")
print("=" * 80)

