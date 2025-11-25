"""
Verify that Hour field correctly extracts HH:mm from TimeOfCall without rounding.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected.xlsx"

print("="*80)
print("VERIFYING HOUR FIELD")
print("="*80)

# Load file
print("\nLoading ESRI file...")
df = pd.read_excel(ESRI_FILE, dtype=str, nrows=100)
print(f"  Loaded {len(df):,} records (sample)")

if 'TimeOfCall' not in df.columns:
    print("  ERROR: TimeOfCall column not found")
    exit(1)

if 'Hour' not in df.columns:
    print("  ERROR: Hour column not found")
    exit(1)

# Check samples
print("\nSample TimeOfCall and Hour values:")
sample = df[['TimeOfCall', 'Hour']].head(20)
for idx, row in sample.iterrows():
    timeofcall = str(row['TimeOfCall'])
    hour = str(row['Hour'])
    print(f"  TimeOfCall: {timeofcall[:30]:30} -> Hour: {hour}")

# Check for rounding issues (should not see :00 for all minutes)
print("\nChecking for rounding issues...")
hour_values = df['Hour'].dropna().astype(str)
rounded_count = hour_values.str.endswith(':00').sum()
non_rounded_count = (~hour_values.str.endswith(':00')).sum()

print(f"  Hour values ending in :00: {rounded_count}")
print(f"  Hour values with minutes: {non_rounded_count}")

if rounded_count == len(hour_values) and len(hour_values) > 0:
    print("  [WARNING] All Hour values are rounded to :00 - this may indicate rounding is still happening")
else:
    print("  [OK] Hour values include minutes (not all rounded)")

# Check for missing values
missing_hour = df['Hour'].isna().sum() + (df['Hour'].astype(str).str.strip() == '').sum()
print(f"\nMissing Hour values: {missing_hour}")

if missing_hour > 0:
    print("\nSample records with missing Hour:")
    missing = df[df['Hour'].isna() | (df['Hour'].astype(str).str.strip() == '')]
    print(missing[['TimeOfCall', 'Hour']].head(10).to_string(index=False))

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)

