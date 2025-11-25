"""
Apply ONLY case number corrections to the ESRI production file.
This script applies case number corrections without re-applying other corrections.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
CASE_CSV = BASE_DIR / "manual_corrections" / "case_number_corrections.csv"
OUTPUT_DIR = BASE_DIR / "data" / "ESRI_CADExport"

print("="*80)
print("APPLYING CASE NUMBER CORRECTIONS ONLY")
print("="*80)
print(f"\nInput file: {ESRI_FILE.name}")
print(f"Corrections file: {CASE_CSV.name}\n")

# Load ESRI file
print("Loading ESRI file...")
df = pd.read_excel(ESRI_FILE, dtype=str)
print(f"  Loaded {len(df):,} records")

# Load case number corrections
print(f"\nLoading case number corrections...")
corrections = pd.read_csv(CASE_CSV)
corrections = corrections[corrections['Corrected_Value'].notna() & (corrections['Corrected_Value'] != '')]
print(f"  Found {len(corrections):,} corrections to apply")

# Clean case numbers - remove newlines, whitespace
corrections['ReportNumberNew_clean'] = corrections['ReportNumberNew'].astype(str).str.strip().str.replace('\n', '').str.replace('\r', '').str.replace('"', '')
corrections['Corrected_Value_clean'] = corrections['Corrected_Value'].astype(str).str.strip()

# Create mapping
case_map = dict(zip(corrections['ReportNumberNew_clean'], corrections['Corrected_Value_clean']))

print(f"\nCase number mapping:")
for old, new in case_map.items():
    print(f"  {old} -> {new}")

# Clean ReportNumberNew in dataframe for matching
df['ReportNumberNew_clean'] = df['ReportNumberNew'].astype(str).str.strip()

# Apply corrections
print(f"\nApplying corrections...")
mask = df['ReportNumberNew_clean'].isin(case_map.keys())
count = mask.sum()
print(f"  Found {count:,} records to update")

if count > 0:
    df.loc[mask, 'ReportNumberNew'] = df.loc[mask, 'ReportNumberNew_clean'].map(case_map)
    print(f"  Updated {count:,} ReportNumberNew values")
    
    # Show sample of changes
    changed = df[mask][['ReportNumberNew', 'TimeOfCall', 'Incident']].head(5)
    print(f"\n  Sample of changes:")
    for idx, row in changed.iterrows():
        old_val = corrections[corrections['Corrected_Value_clean'] == row['ReportNumberNew']]['ReportNumberNew_clean'].iloc[0] if len(corrections[corrections['Corrected_Value_clean'] == row['ReportNumberNew']]) > 0 else 'N/A'
        print(f"    {old_val} -> {row['ReportNumberNew']}")
else:
    print(f"  [WARNING] No matching records found!")

# Drop temporary column
df = df.drop(columns=['ReportNumberNew_clean'])

# Save
print(f"\nSaving updated file...")
df.to_excel(ESRI_FILE, index=False)
print(f"  Saved: {ESRI_FILE}")

print("\n" + "="*80)
print("[SUCCESS] Case number corrections applied!")
print("="*80)
print(f"Total records: {len(df):,}")
print(f"Case numbers corrected: {count:,}")

