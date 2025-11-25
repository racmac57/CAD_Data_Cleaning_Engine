"""Check which disposition corrections are still missing."""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
DISP_CSV = BASE_DIR / "manual_corrections" / "disposition_corrections.csv"

disp_df = pd.read_csv(DISP_CSV)

# Find records with empty Corrected_Value
empty = disp_df[(disp_df['Corrected_Value'].isna()) | (disp_df['Corrected_Value'] == '')]

print("="*80)
print("REMAINING DISPOSITION CORRECTIONS")
print("="*80)
print(f"\nTotal records in CSV: {len(disp_df):,}")
print(f"Records with Corrected_Value: {(disp_df['Corrected_Value'].notna() & (disp_df['Corrected_Value'] != '')).sum():,}")
print(f"Records still missing Corrected_Value: {len(empty):,}")

if len(empty) > 0:
    print(f"\nMissing records:")
    print(empty[['ReportNumberNew', 'TimeOfCall', 'Incident', 'How Reported', 'CADNotes']].to_string(index=False))
    print(f"\nThese {len(empty)} records still need manual correction.")
else:
    print("\n[SUCCESS] All records have Corrected_Value filled!")

