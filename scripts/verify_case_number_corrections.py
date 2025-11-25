"""Verify case number corrections were applied."""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
CASE_CSV = BASE_DIR / "manual_corrections" / "case_number_corrections.csv"

print("="*80)
print("VERIFYING CASE NUMBER CORRECTIONS")
print("="*80)

# Load corrections
case_df = pd.read_csv(CASE_CSV)
case_df = case_df[case_df['Corrected_Value'].notna() & (case_df['Corrected_Value'] != '')]
case_map = dict(zip(case_df['ReportNumberNew'], case_df['Corrected_Value']))

print(f"\nCase number corrections to verify: {len(case_map)}")

# Load ESRI file
esri_df = pd.read_excel(ESRI_FILE, dtype=str)

print(f"\nChecking if old case numbers still exist in ESRI file...")
old_cases_found = []
for old_case, new_case in case_map.items():
    # Clean the old case number (remove newlines, etc.)
    old_case_clean = str(old_case).strip().replace('\n', '')
    matches = esri_df[esri_df['ReportNumberNew'] == old_case_clean]
    if len(matches) > 0:
        old_cases_found.append((old_case_clean, len(matches)))

print(f"\nChecking if new case numbers exist in ESRI file...")
new_cases_found = []
for old_case, new_case in case_map.items():
    matches = esri_df[esri_df['ReportNumberNew'] == str(new_case).strip()]
    if len(matches) > 0:
        new_cases_found.append((new_case, len(matches)))

print(f"\nResults:")
print(f"  Old case numbers still in file: {len(old_cases_found)}")
if old_cases_found:
    print(f"  [WARNING] These old case numbers should have been replaced:")
    for old_case, count in old_cases_found:
        print(f"    {old_case}: {count} records")
else:
    print(f"  [OK] No old case numbers found - all replaced")

print(f"\n  New case numbers in file: {len(new_cases_found)}")
if new_cases_found:
    print(f"  [OK] Corrected case numbers found:")
    for new_case, count in new_cases_found[:5]:  # Show first 5
        print(f"    {new_case}: {count} records")
    if len(new_cases_found) > 5:
        print(f"    ... and {len(new_cases_found) - 5} more")

if len(old_cases_found) == 0 and len(new_cases_found) == len(case_map):
    print(f"\n[SUCCESS] All case number corrections verified!")
else:
    print(f"\n[WARNING] Some corrections may not have been applied correctly")

