"""Quick verification of disposition corrections updates."""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
DISPOSITION_CSV = BASE_DIR / "manual_corrections" / "disposition_corrections.csv"

df = pd.read_csv(DISPOSITION_CSV)

print("="*60)
print("DISPOSITION CORRECTIONS SUMMARY")
print("="*60)
print(f"Total records: {len(df):,}")
print(f"'See Report' (RMS match): {(df['Corrected_Value'] == 'See Report').sum():,}")
print(f"'Assisted' (Assist Own Agency Backup): {(df['Corrected_Value'] == 'Assisted').sum():,}")
print(f"Still empty: {(df['Corrected_Value'].isna() | (df['Corrected_Value'] == '')).sum():,}")
print(f"\nSample of 'See Report' records:")
print(df[df['Corrected_Value'] == 'See Report'][['ReportNumberNew', 'Incident', 'Corrected_Value']].head(5).to_string(index=False))
print(f"\nSample of 'Assisted' records:")
print(df[df['Corrected_Value'] == 'Assisted'][['ReportNumberNew', 'Incident', 'Corrected_Value']].head(5).to_string(index=False))

