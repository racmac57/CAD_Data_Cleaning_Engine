"""
Check if address corrections from address_corrections.csv were applied to the ESRI file.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
ADDR_CORR_CSV = BASE_DIR / "manual_corrections" / "address_corrections.csv"

print("="*80)
print("CHECKING IF ADDRESS CORRECTIONS WERE APPLIED")
print("="*80)

# Load files
print("\nLoading files...")
esri_df = pd.read_excel(ESRI_FILE, dtype=str).fillna('')
addr_corr = pd.read_csv(ADDR_CORR_CSV, dtype=str).fillna('')

print(f"  ESRI file: {len(esri_df):,} records")
print(f"  Address corrections CSV: {len(addr_corr):,} records")

# Get corrections that should be applied
applied_corrections = addr_corr[addr_corr['Corrected_Value'].astype(str).str.strip() != ''].copy()
print(f"\n  Corrections to apply: {len(applied_corrections):,}")

# Check a sample
print("\nChecking sample of corrections...")
sample_cases = applied_corrections['ReportNumberNew'].head(20).tolist()

matches = 0
mismatches = 0
not_found = 0

for case in sample_cases:
    esri_rows = esri_df[esri_df['ReportNumberNew'].astype(str).str.strip() == str(case).strip()]
    corr_rows = applied_corrections[applied_corrections['ReportNumberNew'].astype(str).str.strip() == str(case).strip()]
    
    if esri_rows.empty:
        not_found += 1
        continue
    
    if corr_rows.empty:
        continue
    
    corr_val = str(corr_rows['Corrected_Value'].iloc[0]).strip()
    esri_addr = str(esri_rows['FullAddress2'].iloc[0]).strip()
    
    if corr_val == esri_addr:
        matches += 1
    else:
        mismatches += 1
        if mismatches <= 5:  # Show first 5 mismatches
            print(f"  {case}: MISMATCH")
            print(f"    CSV: {corr_val[:80]}")
            print(f"    ESRI: {esri_addr[:80]}")

print(f"\nResults (sample of 20):")
print(f"  Matches: {matches}")
print(f"  Mismatches: {mismatches}")
print(f"  Not found: {not_found}")

# Check overall statistics
print("\n" + "="*80)
print("OVERALL STATISTICS")
print("="*80)

# Count how many corrections should have been applied
total_to_apply = len(applied_corrections)
print(f"\nTotal corrections in CSV: {total_to_apply:,}")

# Check how many are actually in the ESRI file
merged = esri_df.merge(
    applied_corrections[['ReportNumberNew', 'Corrected_Value']],
    on='ReportNumberNew',
    how='inner',
    suffixes=('', '_corrected')
)

if not merged.empty:
    # Check if FullAddress2 matches Corrected_Value
    merged['matches'] = merged['FullAddress2'].astype(str).str.strip() == merged['Corrected_Value'].astype(str).str.strip()
    actually_applied = merged['matches'].sum()
    
    print(f"Records in ESRI that have corrections: {len(merged):,}")
    print(f"Corrections actually applied (FullAddress2 matches Corrected_Value): {actually_applied:,}")
    print(f"Corrections NOT applied: {len(merged) - actually_applied:,}")
    
    if actually_applied < total_to_apply:
        print(f"\n[WARNING] Only {actually_applied:,} of {total_to_apply:,} corrections appear to be applied!")
        print("You may need to run: python scripts/apply_manual_corrections.py")
    else:
        print(f"\n[OK] All corrections appear to be applied!")
else:
    print("\n[WARNING] No matching ReportNumberNew values found between corrections CSV and ESRI file!")
    print("This suggests the corrections have not been applied yet.")

print("\n" + "="*80)

