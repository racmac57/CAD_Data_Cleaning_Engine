"""Verify the regenerated disposition_corrections.csv file."""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
CSV_FILE = BASE_DIR / "manual_corrections" / "disposition_corrections.csv"

df = pd.read_csv(CSV_FILE)

print("="*80)
print("DISPOSITION CORRECTIONS FILE VERIFICATION")
print("="*80)
print(f"\nTotal records: {len(df):,}")
print(f"Unique ReportNumberNew: {df['ReportNumberNew'].nunique():,}")
print(f"Duplicate ReportNumberNew: {df['ReportNumberNew'].duplicated().sum():,}")

print(f"\nColumns: {list(df.columns)}")
print(f"\nCAD Notes:")
print(f"  Records with CADNotes: {df['CADNotes'].notna().sum():,}")
print(f"  Records without CADNotes: {df['CADNotes'].isna().sum():,}")

print(f"\nCorrected_Value:")
print(f"  Records with Corrected_Value: {(df['Corrected_Value'].notna() & (df['Corrected_Value'] != '')).sum():,}")
print(f"  'See Report': {(df['Corrected_Value'] == 'See Report').sum():,}")
print(f"  'Assisted': {(df['Corrected_Value'] == 'Assisted').sum():,}")
print(f"  Empty: {(df['Corrected_Value'].isna() | (df['Corrected_Value'] == '')).sum():,}")

if df['ReportNumberNew'].duplicated().sum() > 0:
    print(f"\n[WARNING] Found {df['ReportNumberNew'].duplicated().sum():,} duplicate ReportNumberNew values")
    print("Sample duplicates:")
    dup_sample = df[df['ReportNumberNew'].duplicated(keep=False)][['ReportNumberNew', 'Incident', 'CADNotes']].head(10)
    print(dup_sample.to_string(index=False))

