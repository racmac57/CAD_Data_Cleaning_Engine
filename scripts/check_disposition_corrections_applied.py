"""Check if disposition corrections from CSV were applied to ESRI file."""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
DISP_CSV = BASE_DIR / "manual_corrections" / "disposition_corrections.csv"

print("="*80)
print("CHECKING IF DISPOSITION CORRECTIONS WERE APPLIED")
print("="*80)

# Load files
print("\nLoading files...")
esri_df = pd.read_excel(ESRI_FILE)
disp_df = pd.read_csv(DISP_CSV)

# Get corrected values from CSV
corrected = disp_df[disp_df['Corrected_Value'].notna() & (disp_df['Corrected_Value'] != '')]
print(f"\nCSV Status:")
print(f"  Total records: {len(disp_df):,}")
print(f"  Records with Corrected_Value: {len(corrected):,}")

# Check a sample of cases
print(f"\nChecking sample cases...")
sample_cases = corrected['ReportNumberNew'].head(10).tolist()

matches = 0
mismatches = 0
not_found = 0

for case in sample_cases:
    csv_val = corrected[corrected['ReportNumberNew'] == case]['Corrected_Value'].iloc[0]
    esri_rows = esri_df[esri_df['ReportNumberNew'] == case]
    
    if esri_rows.empty:
        not_found += 1
        print(f"  {case}: NOT FOUND in ESRI file")
    else:
        esri_val = esri_rows['Disposition'].iloc[0] if 'Disposition' in esri_rows.columns else None
        if pd.isna(esri_val):
            esri_val = "NULL"
        
        if str(esri_val).strip() == str(csv_val).strip():
            matches += 1
            print(f"  {case}: MATCH - CSV={csv_val}, ESRI={esri_val}")
        else:
            mismatches += 1
            print(f"  {case}: MISMATCH - CSV={csv_val}, ESRI={esri_val}")

print(f"\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Matches: {matches}")
print(f"Mismatches: {mismatches}")
print(f"Not found: {not_found}")

if mismatches > 0 or not_found > 0:
    print(f"\n[ACTION NEEDED] Corrections have NOT been applied to the ESRI file.")
    print(f"Run: python scripts/apply_manual_corrections.py")
else:
    print(f"\n[OK] Corrections appear to be applied (based on sample check)")

