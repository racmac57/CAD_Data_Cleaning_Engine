"""
Update disposition_corrections.csv based on RMS mapping and incident type rules.

1. If ReportNumberNew maps to Case Number in RMS → set "See Report"
2. If Incident is "Assist Own Agency (Backup)" → set "Assisted"
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
DISPOSITION_CSV = BASE_DIR / "manual_corrections" / "disposition_corrections.csv"
RMS_PATH = BASE_DIR / "data" / "rms" / "2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx"

def update_disposition_corrections():
    print("="*60)
    print("UPDATE DISPOSITION CORRECTIONS")
    print("="*60)
    print(f"Started: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load disposition corrections
    print(f"Loading: {DISPOSITION_CSV.name}")
    disp_df = pd.read_csv(DISPOSITION_CSV)
    # Ensure Corrected_Value is string type to avoid dtype warnings
    disp_df['Corrected_Value'] = disp_df['Corrected_Value'].astype(str).replace('nan', '')
    print(f"  Total records: {len(disp_df):,}")
    print(f"  Records with null Disposition: {(disp_df['Disposition'].isna()).sum():,}")
    print(f"  Records with empty Corrected_Value: {(disp_df['Corrected_Value'].isna() | (disp_df['Corrected_Value'] == '')).sum():,}\n")
    
    # Load RMS export
    print(f"Loading: {RMS_PATH.name}")
    rms_df = pd.read_excel(RMS_PATH, dtype=str)
    print(f"  Total RMS records: {len(rms_df):,}")
    
    # Create lookup: Case Number -> exists in RMS
    if 'Case Number' not in rms_df.columns:
        print("ERROR: 'Case Number' column not found in RMS export")
        print(f"Available columns: {list(rms_df.columns)}")
        return
    
    rms_case_numbers = set(rms_df['Case Number'].dropna().astype(str).str.strip())
    print(f"  Unique Case Numbers in RMS: {len(rms_case_numbers):,}\n")
    
    # Track updates
    rms_matches = 0
    assist_backup_updates = 0
    already_filled = 0
    
    # Update Corrected_Value column
    for idx, row in disp_df.iterrows():
        report_num = str(row['ReportNumberNew']).strip()
        incident = str(row['Incident']).strip() if pd.notna(row['Incident']) else ''
        current_corrected = str(row['Corrected_Value']).strip() if pd.notna(row['Corrected_Value']) else ''
        
        # Skip if already has a corrected value
        if current_corrected:
            already_filled += 1
            continue
        
        # Rule 1: Check if ReportNumberNew maps to RMS Case Number
        if report_num in rms_case_numbers:
            disp_df.at[idx, 'Corrected_Value'] = 'See Report'
            rms_matches += 1
            continue
        
        # Rule 2: If Incident is "Assist Own Agency (Backup)" → "Assisted"
        if incident == 'Assist Own Agency (Backup)':
            disp_df.at[idx, 'Corrected_Value'] = 'Assisted'
            assist_backup_updates += 1
    
    # Save updated CSV
    print("="*60)
    print("UPDATES APPLIED")
    print("="*60)
    print(f"Records already had Corrected_Value: {already_filled:,}")
    print(f"Set to 'See Report' (RMS match): {rms_matches:,}")
    print(f"Set to 'Assisted' (Assist Own Agency Backup): {assist_backup_updates:,}")
    print(f"Total updated: {rms_matches + assist_backup_updates:,}")
    print(f"Remaining to fill: {(disp_df['Corrected_Value'].isna() | (disp_df['Corrected_Value'] == '')).sum():,}\n")
    
    # Save
    disp_df.to_csv(DISPOSITION_CSV, index=False)
    print(f"Saved: {DISPOSITION_CSV}")
    print(f"Completed: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    update_disposition_corrections()

