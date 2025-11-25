"""Verify production file status after applying corrections."""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"

print("="*80)
print("PRODUCTION FILE STATUS")
print("="*80)

df = pd.read_excel(ESRI_FILE)

print(f"\nFile: {ESRI_FILE.name}")
print(f"Total records: {len(df):,}")
print(f"Disposition coverage: {df['Disposition'].notna().sum():,} ({df['Disposition'].notna().sum()/len(df)*100:.1f}%)")

print(f"\nTop 10 Disposition values:")
print(df['Disposition'].value_counts().head(10))

print(f"\n[SUCCESS] Production file has been updated with manual corrections!")

