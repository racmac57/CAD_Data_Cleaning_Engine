#!/usr/bin/env python3
"""
Apply manual corrections from CSV files to the ESRI final export.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
CORRECTIONS_DIR = BASE_DIR / "manual_corrections"
OUTPUT_DIR = BASE_DIR / "data" / "ESRI_CADExport"

def apply_how_reported_corrections(df, corrections_file):
    """Apply How Reported corrections."""
    if not corrections_file.exists():
        print(f"  Skipping: {corrections_file.name} (file not found)")
        return df, 0
    
    corrections = pd.read_csv(corrections_file)
    corrections = corrections[corrections['Corrected_Value'].notna() & (corrections['Corrected_Value'] != '')]
    
    if len(corrections) == 0:
        print(f"  No corrections to apply in {corrections_file.name}")
        return df, 0
    
    # Merge corrections
    df = df.merge(
        corrections[['ReportNumberNew', 'Corrected_Value']].rename(columns={'Corrected_Value': 'How Reported'}),
        on='ReportNumberNew',
        how='left',
        suffixes=('', '_new')
    )
    
    # Apply corrections where new value exists
    mask = df['How Reported_new'].notna()
    count = mask.sum()
    df.loc[mask, 'How Reported'] = df.loc[mask, 'How Reported_new']
    df = df.drop(columns=['How Reported_new'])
    
    return df, count

def apply_disposition_corrections(df, corrections_file):
    """Apply Disposition corrections."""
    if not corrections_file.exists():
        print(f"  Skipping: {corrections_file.name} (file not found)")
        return df, 0
    
    corrections = pd.read_csv(corrections_file)
    corrections = corrections[corrections['Corrected_Value'].notna() & (corrections['Corrected_Value'] != '')]
    
    if len(corrections) == 0:
        print(f"  No corrections to apply in {corrections_file.name}")
        return df, 0
    
    # Merge corrections
    df = df.merge(
        corrections[['ReportNumberNew', 'Corrected_Value']].rename(columns={'Corrected_Value': 'Disposition'}),
        on='ReportNumberNew',
        how='left',
        suffixes=('', '_new')
    )
    
    # Apply corrections where new value exists
    mask = df['Disposition_new'].notna()
    count = mask.sum()
    df.loc[mask, 'Disposition'] = df.loc[mask, 'Disposition_new']
    df = df.drop(columns=['Disposition_new'])
    
    return df, count

def apply_case_number_corrections(df, corrections_file):
    """Apply ReportNumberNew corrections."""
    if not corrections_file.exists():
        print(f"  Skipping: {corrections_file.name} (file not found)")
        return df, 0
    
    corrections = pd.read_csv(corrections_file)
    corrections = corrections[corrections['Corrected_Value'].notna() & (corrections['Corrected_Value'] != '')]
    
    if len(corrections) == 0:
        print(f"  No corrections to apply in {corrections_file.name}")
        return df, 0
    
    # Clean case numbers - remove newlines, whitespace, and normalize
    corrections['ReportNumberNew_clean'] = corrections['ReportNumberNew'].astype(str).str.strip().str.replace('\n', '').str.replace('\r', '')
    corrections['Corrected_Value_clean'] = corrections['Corrected_Value'].astype(str).str.strip()
    
    # Create mapping from old to new case numbers
    case_map = dict(zip(corrections['ReportNumberNew_clean'], corrections['Corrected_Value_clean']))
    
    # Clean ReportNumberNew in the dataframe for matching
    df['ReportNumberNew_clean'] = df['ReportNumberNew'].astype(str).str.strip().str.replace('\n', '').str.replace('\r', '')
    
    # Apply corrections
    mask = df['ReportNumberNew_clean'].isin(case_map.keys())
    count = mask.sum()
    df.loc[mask, 'ReportNumberNew'] = df.loc[mask, 'ReportNumberNew_clean'].map(case_map)
    
    # Drop temporary column
    df = df.drop(columns=['ReportNumberNew_clean'])
    
    return df, count

def apply_address_corrections(df, corrections_file):
    """Apply FullAddress2 corrections."""
    if not corrections_file.exists():
        print(f"  Skipping: {corrections_file.name} (file not found)")
        return df, 0
    
    corrections = pd.read_csv(corrections_file, dtype=str).fillna('')
    corrections = corrections[corrections['Corrected_Value'].astype(str).str.strip() != '']
    
    if len(corrections) == 0:
        print(f"  No corrections to apply in {corrections_file.name}")
        return df, 0
    
    # Remove duplicates from corrections - keep first occurrence per ReportNumberNew
    corrections = corrections.drop_duplicates(subset=['ReportNumberNew'], keep='first')
    print(f"  Unique corrections to apply: {len(corrections):,}")
    
    # Create a mapping dictionary for faster lookup
    correction_map = dict(zip(
        corrections['ReportNumberNew'].astype(str).str.strip(),
        corrections['Corrected_Value'].astype(str).str.strip()
    ))
    
    # Apply corrections using map (faster and avoids merge duplicates)
    df['ReportNumberNew_stripped'] = df['ReportNumberNew'].astype(str).str.strip()
    df['FullAddress2_new'] = df['ReportNumberNew_stripped'].map(correction_map)
    
    # Apply corrections where new value exists
    mask = df['FullAddress2_new'].notna() & (df['FullAddress2_new'] != '')
    count = mask.sum()
    df.loc[mask, 'FullAddress2'] = df.loc[mask, 'FullAddress2_new']
    df = df.drop(columns=['FullAddress2_new', 'ReportNumberNew_stripped'])
    
    return df, count

def fix_hour_field(df):
    """Extract HH:mm from TimeOfCall and populate Hour field without rounding."""
    print("\n  Fixing Hour field format...")
    
    if 'TimeOfCall' not in df.columns:
        print("  WARNING: TimeOfCall column not found. Skipping Hour field fix.")
        return df, 0
    
    if 'Hour' not in df.columns:
        print("  WARNING: Hour column not found. Creating Hour column.")
        df['Hour'] = ''
    
    def extract_time_from_timeofcall(timeofcall_str):
        """Extract HH:mm from TimeOfCall (format: MM/dd/YYYY HH:mm)."""
        if pd.isna(timeofcall_str):
            return ''
        
        timeofcall_str = str(timeofcall_str).strip()
        
        # Try to parse MM/dd/YYYY HH:mm format
        import re
        # Pattern: MM/dd/YYYY HH:mm or similar datetime formats
        time_match = re.search(r'(\d{1,2}):(\d{2})', timeofcall_str)
        if time_match:
            hour = time_match.group(1).zfill(2)  # Pad to 2 digits
            minute = time_match.group(2)
            return f"{hour}:{minute}"
        
        # Try parsing as datetime if it's in a different format
        try:
            from datetime import datetime
            # Try common formats
            for fmt in ['%m/%d/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%m/%d/%Y %H:%M:%S']:
                try:
                    dt = datetime.strptime(timeofcall_str, fmt)
                    return f"{dt.hour:02d}:{dt.minute:02d}"
                except:
                    continue
        except:
            pass
        
        return ''
    
    # Extract time from TimeOfCall for all records
    df['Hour'] = df['TimeOfCall'].apply(extract_time_from_timeofcall)
    
    # Count how many were populated
    count = (df['Hour'] != '').sum()
    
    return df, count

def main():
    print("="*60)
    print("APPLYING MANUAL CORRECTIONS")
    print("="*60)
    print(f"\nInput file: {ESRI_FILE}")
    print(f"Corrections directory: {CORRECTIONS_DIR}\n")
    
    # Load main file
    print("Loading ESRI export file...")
    df = pd.read_excel(ESRI_FILE)
    print(f"  Loaded {len(df):,} records\n")
    
    total_corrections = 0
    
    # Apply corrections
    print("Applying corrections...")
    
    # 1. How Reported
    print("\n1. How Reported corrections:")
    df, count = apply_how_reported_corrections(df, CORRECTIONS_DIR / "how_reported_corrections.csv")
    print(f"  Applied {count:,} corrections")
    total_corrections += count
    
    # 2. Disposition
    print("\n2. Disposition corrections:")
    df, count = apply_disposition_corrections(df, CORRECTIONS_DIR / "disposition_corrections.csv")
    print(f"  Applied {count:,} corrections")
    total_corrections += count
    
    # 3. Case Numbers
    print("\n3. Case Number corrections:")
    df, count = apply_case_number_corrections(df, CORRECTIONS_DIR / "case_number_corrections.csv")
    print(f"  Applied {count:,} corrections")
    total_corrections += count
    
    # 4. Addresses
    print("\n4. Address corrections:")
    df, count = apply_address_corrections(df, CORRECTIONS_DIR / "address_corrections.csv")
    print(f"  Applied {count:,} corrections")
    total_corrections += count
    
    # 5. Hour Field (automated fix)
    print("\n5. Hour field format fix:")
    df, count = fix_hour_field(df)
    print(f"  Fixed {count:,} records")
    total_corrections += count
    
    # Save corrected file - update the production file directly
    print(f"\nSaving corrected file...")
    print(f"  Updating production file: {ESRI_FILE.name}")
    df.to_excel(ESRI_FILE, index=False)
    print(f"  Saved to: {ESRI_FILE}")
    
    # Also save a timestamped backup
    timestamp = datetime.now().strftime('%Y%m%d')
    backup_file = OUTPUT_DIR / f"CAD_ESRI_Final_{timestamp}_corrected.xlsx"
    df.to_excel(backup_file, index=False)
    print(f"  Backup saved to: {backup_file}")
    
    print("\n" + "="*60)
    print("CORRECTIONS COMPLETE")
    print("="*60)
    print(f"Total corrections applied: {total_corrections:,}")
    print(f"Production file updated: {ESRI_FILE.name}")
    print(f"Backup file: {backup_file.name}")
    print("\nNext step: Re-run validation to verify corrections")

if __name__ == "__main__":
    main()

