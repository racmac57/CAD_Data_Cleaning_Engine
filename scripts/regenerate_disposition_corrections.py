"""
Regenerate disposition_corrections.csv with all records and RMS backfill.

This recreates the file that was lost when saving Excel as CSV.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
CAD_FILE = BASE_DIR / "ref" / "2019_2025_11_17_Updated_CAD_Export.xlsx"  # Original CAD file with CADNotes
RMS_PATH = BASE_DIR / "data" / "rms" / "2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx"
OUTPUT_CSV = BASE_DIR / "manual_corrections" / "disposition_corrections.csv"
BACKUP_CSV = BASE_DIR / "manual_corrections" / "disposition_corrections_backup_243_records.csv"

print("="*80)
print("REGENERATING DISPOSITION CORRECTIONS FILE")
print("="*80)
print("\nThis will recreate the file with all null disposition records")
print("and automatically backfill RMS matches and Assist Own Agency (Backup)\n")

# Step 1: Get all records with null Disposition from ESRI file
print("Step 1: Loading ESRI file and finding null Disposition records...")
df = pd.read_excel(ESRI_FILE)
print(f"  Total ESRI records: {len(df):,}")

null_disp = df[df['Disposition'].isna()].copy()
print(f"  Records with null Disposition: {len(null_disp):,}")

# Note: We keep ALL records, even if ReportNumberNew is duplicated
# Each row represents a separate CAD entry that needs a disposition
if null_disp['ReportNumberNew'].duplicated().sum() > 0:
    print(f"  Note: {null_disp['ReportNumberNew'].duplicated().sum():,} records have duplicate ReportNumberNew")
    print(f"  (This is expected - same case can have multiple CAD entries)")

# Create the corrections DataFrame
base_columns = ['ReportNumberNew', 'TimeOfCall', 'Incident', 'How Reported', 'Disposition']
disp_corrections = null_disp[base_columns].copy()

# Try to get CAD Notes from original CAD file
print("\nStep 2a: Loading CAD Notes from original CAD export...")
try:
    if CAD_FILE.exists():
        cad_df = pd.read_excel(CAD_FILE, usecols=['ReportNumberNew', 'CADNotes'], dtype=str)
        print(f"  Loaded {len(cad_df):,} records from CAD file")
        
        # For CAD Notes, we need to merge on ReportNumberNew + TimeOfCall if possible
        # But since we're merging on ReportNumberNew only, we'll get the first match
        # This is okay - CAD Notes are typically the same for all entries of the same case
        print(f"  Note: Merging CAD Notes - if multiple entries per ReportNumberNew, first match will be used")
        
        # Merge CAD Notes (will match first occurrence per ReportNumberNew)
        disp_corrections = disp_corrections.merge(
            cad_df[['ReportNumberNew', 'CADNotes']].drop_duplicates(subset=['ReportNumberNew'], keep='first'),
            on='ReportNumberNew',
            how='left'
        )
        print(f"  Merged CAD Notes: {disp_corrections['CADNotes'].notna().sum():,} records have CAD Notes")
    else:
        print(f"  [WARNING] CAD file not found: {CAD_FILE.name}")
        print(f"  CAD Notes column will not be included")
        disp_corrections['CADNotes'] = ''
except Exception as e:
    print(f"  [WARNING] Could not load CAD Notes: {e}")
    disp_corrections['CADNotes'] = ''

disp_corrections['Corrected_Value'] = ''
disp_corrections['Notes'] = ''  # This is for manual notes, not CAD Notes

print(f"\nStep 2: Created corrections file with {len(disp_corrections):,} records")

# Step 3: Load RMS and backfill
print("\nStep 3: Loading RMS export and backfilling matches...")
rms_df = pd.read_excel(RMS_PATH, dtype=str)
rms_case_numbers = set(rms_df['Case Number'].dropna().astype(str).str.strip())
print(f"  RMS Case Numbers: {len(rms_case_numbers):,}")

# Track updates
rms_matches = 0
assist_backup_updates = 0

# Backfill Corrected_Value
for idx, row in disp_corrections.iterrows():
    report_num = str(row['ReportNumberNew']).strip()
    incident = str(row['Incident']).strip() if pd.notna(row['Incident']) else ''
    
    # Rule 1: Check if ReportNumberNew maps to RMS Case Number
    if report_num in rms_case_numbers:
        disp_corrections.at[idx, 'Corrected_Value'] = 'See Report'
        rms_matches += 1
        continue
    
    # Rule 2: If Incident is "Assist Own Agency (Backup)" → "Assisted"
    if incident == 'Assist Own Agency (Backup)':
        disp_corrections.at[idx, 'Corrected_Value'] = 'Assisted'
        assist_backup_updates += 1

# Save
print("\n" + "="*80)
print("BACKFILL SUMMARY")
print("="*80)
print(f"Total records: {len(disp_corrections):,}")
print(f"Set to 'See Report' (RMS match): {rms_matches:,}")
print(f"Set to 'Assisted' (Assist Own Agency Backup): {assist_backup_updates:,}")
print(f"Total auto-filled: {rms_matches + assist_backup_updates:,}")
print(f"Remaining to fill manually: {(disp_corrections['Corrected_Value'] == '').sum():,}")

# Backup current file if it exists
if OUTPUT_CSV.exists():
    try:
        import shutil
        shutil.copy(OUTPUT_CSV, BACKUP_CSV)
        print(f"\nBacked up current file (243 records) to: {BACKUP_CSV.name}")
    except Exception as e:
        print(f"\n[WARNING] Could not backup current file: {e}")

print(f"\nSaving to: {OUTPUT_CSV}")
try:
    disp_corrections.to_csv(OUTPUT_CSV, index=False)
except PermissionError:
    print("\n[ERROR] File is open in Excel or another program!")
    print("Please close the file and run this script again.")
    print(f"\nAlternatively, the data is ready - you can manually save it.")
    print(f"Total records to save: {len(disp_corrections):,}")
    exit(1)

print("\n" + "="*80)
print("[SUCCESS] File regenerated!")
print("="*80)
print(f"\nThe file now has {len(disp_corrections):,} records (restored from {len(null_disp):,} null dispositions)")
print(f"  - {rms_matches:,} records auto-filled with 'See Report' (RMS matches)")
print(f"  - {assist_backup_updates:,} records auto-filled with 'Assisted' (Assist Own Agency Backup)")
print(f"  - {(disp_corrections['Corrected_Value'] == '').sum():,} records still need manual correction")
print("\nYou can now add your manual corrections to the remaining empty Corrected_Value fields.")

