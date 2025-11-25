"""Verify that disposition_corrections.csv was checked against RMS and "See Report" was added."""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
DISPOSITION_CSV = BASE_DIR / "manual_corrections" / "disposition_corrections.csv"
RMS_PATH = BASE_DIR / "data" / "rms" / "2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx"

print("="*80)
print("VERIFYING RMS MAPPING IN DISPOSITION CORRECTIONS CSV")
print("="*80)

# Load files
print("\nLoading files...")
disp_df = pd.read_csv(DISPOSITION_CSV)
rms_df = pd.read_excel(RMS_PATH, dtype=str)

# Get RMS case numbers
rms_case_numbers = set(rms_df['Case Number'].dropna().astype(str).str.strip())
print(f"RMS Case Numbers: {len(rms_case_numbers):,}")

# Check CSV
print(f"\nCSV Status:")
print(f"  Total records: {len(disp_df):,}")

# Get records with "See Report"
see_report = disp_df[disp_df['Corrected_Value'] == 'See Report']
print(f"  Records with Corrected_Value='See Report': {len(see_report):,}")

# Verify these are actually in RMS
disp_df['ReportNumberNew_str'] = disp_df['ReportNumberNew'].astype(str).str.strip()
disp_df['In_RMS'] = disp_df['ReportNumberNew_str'].isin(rms_case_numbers)

# Re-filter see_report after adding In_RMS column
see_report = disp_df[disp_df['Corrected_Value'] == 'See Report']
see_report_in_rms = see_report[see_report['In_RMS'] == True]
see_report_not_in_rms = see_report[see_report['In_RMS'] == False]

print(f"\nVerification:")
print(f"  'See Report' records that ARE in RMS: {len(see_report_in_rms):,}")
print(f"  'See Report' records that are NOT in RMS: {len(see_report_not_in_rms):,}")

# Check records in RMS that should have "See Report"
in_rms_total = disp_df[disp_df['In_RMS'] == True]
in_rms_with_see_report = in_rms_total[in_rms_total['Corrected_Value'] == 'See Report']
in_rms_without_see_report = in_rms_total[
    (in_rms_total['Corrected_Value'] != 'See Report') & 
    (in_rms_total['Corrected_Value'].notna()) & 
    (in_rms_total['Corrected_Value'] != '')
]

print(f"\nRMS Match Analysis:")
print(f"  Total CSV records that match RMS Case Number: {len(in_rms_total):,}")
print(f"  Of those, have 'See Report': {len(in_rms_with_see_report):,}")
print(f"  Of those, have other values: {len(in_rms_without_see_report):,}")

# Show samples
print(f"\nSample of 'See Report' records that ARE in RMS:")
print(see_report_in_rms[['ReportNumberNew', 'Incident', 'Corrected_Value']].head(10).to_string(index=False))

if len(see_report_not_in_rms) > 0:
    print(f"\nSample of 'See Report' records that are NOT in RMS (should be reviewed):")
    print(see_report_not_in_rms[['ReportNumberNew', 'Incident', 'Corrected_Value']].head(5).to_string(index=False))

print("\n" + "="*80)
if len(see_report_in_rms) > 0:
    print("[CONFIRMED] CSV was checked against RMS export")
    print(f"[CONFIRMED] {len(see_report_in_rms):,} records with 'See Report' are verified in RMS")
else:
    print("[WARNING] No 'See Report' records found that match RMS")

