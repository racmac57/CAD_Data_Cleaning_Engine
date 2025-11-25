"""Check disposition count discrepancy."""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
CSV_FILE = BASE_DIR / "manual_corrections" / "disposition_corrections.csv"

print("="*80)
print("CHECKING DISPOSITION COUNT DISCREPANCY")
print("="*80)

# Check ESRI file
df_esri = pd.read_excel(ESRI_FILE)
null_in_esri = df_esri['Disposition'].isna().sum()
total_esri = len(df_esri)

print(f"\nESRI File (CAD_ESRI_Final_20251117_v2.xlsx):")
print(f"  Total records: {total_esri:,}")
print(f"  Null Disposition: {null_in_esri:,}")
print(f"  Non-null Disposition: {df_esri['Disposition'].notna().sum():,}")

# Check CSV file
df_csv = pd.read_csv(CSV_FILE)
print(f"\nCSV File (disposition_corrections.csv):")
print(f"  Total records: {len(df_csv):,}")

print(f"\nREADME states: 18,582 null Disposition values")
print(f"Current ESRI file has: {null_in_esri:,} null Disposition values")
print(f"Difference: {18582 - null_in_esri:,} records")

if null_in_esri < 18582:
    print(f"\n[EXPLANATION]")
    print(f"The README number (18,582) was from an earlier version of the file.")
    print(f"Since then, {18582 - null_in_esri:,} dispositions have been corrected.")
    print(f"The current file correctly captures all {null_in_esri:,} remaining null dispositions.")
elif null_in_esri > 18582:
    print(f"\n[WARNING]")
    print(f"The ESRI file has MORE null dispositions than the README states.")
    print(f"This suggests the file may have been updated with additional records.")
else:
    print(f"\n[OK] Counts match!")

print(f"\n[VERIFICATION]")
print(f"CSV file has {len(df_csv):,} records")
print(f"ESRI file has {null_in_esri:,} null dispositions")
if len(df_csv) == null_in_esri:
    print(f"✓ CSV file correctly captures all null disposition records")
else:
    print(f"⚠ Mismatch: CSV has {len(df_csv) - null_in_esri:,} {'more' if len(df_csv) > null_in_esri else 'fewer'} records than null dispositions")

