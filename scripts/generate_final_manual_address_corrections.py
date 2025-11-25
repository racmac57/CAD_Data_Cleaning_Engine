#!/usr/bin/env python3
"""
Generate final list of addresses needing manual correction after RMS backfill.

This script:
1. Loads the current ESRI export file
2. Identifies invalid/incomplete addresses
3. Attempts to backfill from RMS data
4. Generates CSV with remaining records needing manual correction
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
from datetime import datetime
import sys

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# File paths
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected.xlsx"
RAW_CAD_FILE = BASE_DIR / "data" / "01_raw" / "2025_11_21_2019_2025_11_21_ALL_CAD_Data.xlsx"
RMS_FILE = BASE_DIR / "data" / "rms" / "2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx"
OUTPUT_DIR = BASE_DIR / "data" / "02_reports"
OUTPUT_CSV = OUTPUT_DIR / f"final_address_manual_corrections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Address quality patterns
STREET_TYPES = [
    "STREET", "ST", "AVENUE", "AVE", "ROAD", "RD", "DRIVE", "DR", "LANE", "LN",
    "BOULEVARD", "BLVD", "COURT", "CT", "PLACE", "PL", "CIRCLE", "CIR",
    "TERRACE", "TER", "WAY", "PARKWAY", "PKWY", "HIGHWAY", "HWY", "PLAZA",
    "SQUARE", "SQ", "TRAIL", "TRL", "PATH", "ALLEY", "WALK", "EXPRESSWAY",
    "TURNPIKE", "TPKE", "ROUTE", "RT"
]

STREET_REGEX = r"\b(?:" + "|".join(STREET_TYPES) + r")\b"

def is_invalid_address(address):
    """
    Check if address is invalid/incomplete:
    - Missing street number (doesn't start with a number for standard addresses)
    - Incomplete intersection (contains " & ," pattern - missing second street)
    - Generic terms (home, unknown, various, etc.)
    - Missing street type
    """
    if pd.isna(address) or str(address).strip() == "":
        return True, "blank"
    
    addr = str(address).strip()
    addr_upper = addr.upper()
    
    # Check for incomplete intersection (contains " & ," - missing second street)
    if re.search(r'&\s*,', addr_upper):
        return True, "incomplete_intersection"
    
    # Check for generic terms
    generic_terms = ["HOME", "VARIOUS", "UNKNOWN", "PARKING GARAGE", "REAR LOT", 
                     "PARKING LOT", "LOT", "GARAGE", "AREA", "LOCATION", "SCENE",
                     "N/A", "NA", "TBD", "TO BE DETERMINED"]
    for term in generic_terms:
        if re.search(rf'\b{re.escape(term)}\b', addr_upper):
            return True, "generic_location"
    
    # Check for complete intersection (has " & " with both streets)
    if " & " in addr_upper and not re.search(r'&\s*,', addr_upper):
        parts = addr_upper.split("&")
        if len(parts) == 2:
            part1 = parts[0].strip()
            part2 = parts[1].strip()
            # If both parts have street types, it's likely valid
            if re.search(STREET_REGEX, part1, re.IGNORECASE) and re.search(STREET_REGEX, part2, re.IGNORECASE):
                return False, "valid"
    
    # For standard addresses (not intersections), check if it starts with a number
    if " & " not in addr_upper:
        # Standard address should start with a number
        if not re.match(r'^\d+', addr):
            # Check if it has a street type (might be a named location like "Park")
            if not re.search(STREET_REGEX, addr_upper, re.IGNORECASE):
                return True, "missing_street_number"
    
    # Check for missing street type (has number but no street type)
    if re.match(r'^\d+', addr):
        if not re.search(STREET_REGEX, addr_upper, re.IGNORECASE):
            return True, "missing_street_type"
    
    return False, "valid"

def validate_rms_address(address):
    """Validate that RMS address is better than CAD address."""
    if pd.isna(address) or str(address).strip() == "":
        return False
    
    addr = str(address).strip()
    addr_upper = addr.upper()
    
    # Check for generic terms
    generic_terms = ["HOME", "VARIOUS", "UNKNOWN", "PARKING GARAGE", "REAR LOT", 
                     "PARKING LOT", "LOT", "GARAGE", "AREA", "LOCATION", "SCENE"]
    for term in generic_terms:
        if re.search(rf'\b{re.escape(term)}\b', addr_upper):
            return False
    
    # Check for incomplete intersection
    if re.search(r'&\s*,', addr_upper):
        return False
    
    # Check if it has street number or is complete intersection
    if re.match(r'^\d+', addr) or (" & " in addr_upper and not re.search(r'&\s*,', addr_upper)):
        return True
    
    return False

def main():
    """Main execution function."""
    print("=" * 80)
    print("Final Address Manual Corrections Generator")
    print("=" * 80)
    
    # Load ESRI file
    print(f"\nLoading ESRI file: {ESRI_FILE.name}")
    try:
        cad_df = pd.read_excel(ESRI_FILE, dtype=str)
        print(f"Loaded {len(cad_df):,} records")
    except Exception as e:
        print(f"Error loading ESRI file: {e}")
        return
    
    # Try to load CADNotes from raw file
    print(f"\nAttempting to load CADNotes from raw CAD file...")
    cad_notes_map = {}
    if RAW_CAD_FILE.exists():
        try:
            raw_df = pd.read_excel(RAW_CAD_FILE, dtype=str, nrows=1000)  # Check first 1000 rows for column name
            cad_notes_col = None
            for col in raw_df.columns:
                if 'CAD' in col.upper() and ('NOTE' in col.upper() or 'NARRATIVE' in col.upper()):
                    cad_notes_col = col
                    break
            
            if cad_notes_col:
                print(f"Found CADNotes column: {cad_notes_col}")
                print("Loading full raw CAD file for CADNotes...")
                raw_df_full = pd.read_excel(RAW_CAD_FILE, dtype=str, usecols=['ReportNumberNew', cad_notes_col])
                raw_df_full['_key'] = raw_df_full['ReportNumberNew'].astype(str).str.strip()
                cad_notes_map = dict(zip(raw_df_full['_key'], raw_df_full[cad_notes_col].fillna('')))
                print(f"Loaded {len(cad_notes_map):,} CADNotes entries")
            else:
                print("CADNotes column not found in raw file")
        except Exception as e:
            print(f"Could not load CADNotes from raw file: {e}")
    else:
        print("Raw CAD file not found")
    
    # Identify invalid addresses
    print("\nIdentifying invalid addresses...")
    cad_df['_is_invalid'] = cad_df['FullAddress2'].apply(lambda x: is_invalid_address(x)[0])
    cad_df['_issue_type'] = cad_df['FullAddress2'].apply(lambda x: is_invalid_address(x)[1])
    
    invalid_count = cad_df['_is_invalid'].sum()
    print(f"Found {invalid_count:,} records with invalid addresses")
    
    # Load RMS data
    print(f"\nLoading RMS file: {RMS_FILE.name}")
    try:
        rms_df = pd.read_excel(RMS_FILE, dtype=str)
        print(f"Loaded {len(rms_df):,} RMS records")
    except Exception as e:
        print(f"Error loading RMS file: {e}")
        return
    
    # Prepare RMS lookup
    print("\nPreparing RMS address lookup...")
    rms_df['_case_key'] = rms_df['Case Number'].astype(str).str.strip()
    rms_df = rms_df[rms_df['FullAddress'].notna()]
    
    # Validate RMS addresses
    rms_df['_rms_valid'] = rms_df['FullAddress'].apply(validate_rms_address)
    rms_valid = rms_df[rms_df['_rms_valid']].copy()
    
    # Create lookup dictionary (keep first occurrence per case)
    rms_lookup = rms_valid[['_case_key', 'FullAddress']].drop_duplicates(subset=['_case_key'], keep='first')
    rms_address_map = dict(zip(rms_lookup['_case_key'], rms_lookup['FullAddress']))
    
    print(f"Created RMS lookup with {len(rms_address_map):,} valid addresses")
    
    # Attempt backfill from RMS
    print("\nAttempting RMS backfill...")
    cad_df['_report_key'] = cad_df['ReportNumberNew'].astype(str).str.strip()
    cad_df['_rms_address'] = cad_df['_report_key'].map(rms_address_map)
    
    # Backfill where RMS address is available and valid
    backfill_mask = cad_df['_is_invalid'] & cad_df['_rms_address'].notna()
    backfilled_count = backfill_mask.sum()
    
    if backfilled_count > 0:
        print(f"Backfilling {backfilled_count:,} addresses from RMS...")
        cad_df.loc[backfill_mask, 'FullAddress2'] = cad_df.loc[backfill_mask, '_rms_address']
        cad_df.loc[backfill_mask, '_is_invalid'] = False
        cad_df.loc[backfill_mask, '_issue_type'] = 'backfilled_from_rms'
    
    # Re-identify remaining invalid addresses
    print("\nRe-identifying remaining invalid addresses...")
    cad_df['_is_invalid'] = cad_df['FullAddress2'].apply(lambda x: is_invalid_address(x)[0])
    cad_df['_issue_type'] = cad_df['FullAddress2'].apply(lambda x: is_invalid_address(x)[1])
    
    remaining_invalid = cad_df['_is_invalid'].sum()
    print(f"Remaining invalid addresses: {remaining_invalid:,}")
    print(f"Backfilled from RMS: {backfilled_count:,}")
    
    # Get records needing manual correction
    manual_corrections = cad_df[cad_df['_is_invalid']].copy()
    
    # Prepare output columns
    output_columns = {
        'ReportNumberNew': 'ReportNumberNew',
        'ReportDate': 'TimeOfCall',  # Will format this
        'IncidentType': 'Incident',
        'CADNotes': 'CADNotes' if 'CADNotes' in manual_corrections.columns else None,
        'CurrentAddress': 'FullAddress2',
        'IssueType': '_issue_type'
    }
    
    # Build output dataframe
    output_df = pd.DataFrame()
    output_df['ReportNumberNew'] = manual_corrections['ReportNumberNew']
    
    # Format date/time
    if 'TimeOfCall' in manual_corrections.columns:
        try:
            output_df['ReportDate'] = pd.to_datetime(manual_corrections['TimeOfCall'], errors='coerce')
            output_df['ReportDate'] = output_df['ReportDate'].dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            output_df['ReportDate'] = manual_corrections['TimeOfCall']
    else:
        output_df['ReportDate'] = ''
    
    output_df['IncidentType'] = manual_corrections.get('Incident', '')
    
    # Get CADNotes from map if available
    if cad_notes_map:
        output_df['CADNotes'] = output_df['ReportNumberNew'].astype(str).str.strip().map(cad_notes_map).fillna('')
    else:
        output_df['CADNotes'] = manual_corrections.get('CADNotes', '')
    output_df['CurrentAddress'] = manual_corrections['FullAddress2']
    output_df['IssueType'] = manual_corrections['_issue_type']
    
    # Add RMS address if available (for reference)
    output_df['RMSAddress'] = manual_corrections['_rms_address'].fillna('')
    
    # Sort by issue type and date
    issue_priority = {
        'incomplete_intersection': 1,
        'generic_location': 2,
        'missing_street_number': 3,
        'missing_street_type': 4,
        'blank': 5
    }
    output_df['_priority'] = output_df['IssueType'].map(issue_priority).fillna(99)
    output_df = output_df.sort_values(['_priority', 'ReportDate'], ascending=[True, True])
    output_df = output_df.drop('_priority', axis=1)
    
    # Remove duplicates (keep first occurrence per ReportNumberNew)
    print(f"\nRemoving duplicates (keeping first occurrence per case)...")
    before_dedup = len(output_df)
    output_df = output_df.drop_duplicates(subset=['ReportNumberNew'], keep='first')
    after_dedup = len(output_df)
    print(f"Reduced from {before_dedup:,} to {after_dedup:,} unique cases")
    
    # Save to CSV
    print(f"\nSaving to: {OUTPUT_CSV}")
    output_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    # Generate summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total invalid addresses found: {invalid_count:,}")
    print(f"Backfilled from RMS: {backfilled_count:,}")
    print(f"Remaining needing manual correction: {remaining_invalid:,}")
    print(f"Unique cases needing correction: {len(output_df):,}")
    
    print("\nBreakdown by issue type:")
    issue_counts = output_df['IssueType'].value_counts()
    for issue, count in issue_counts.items():
        print(f"  {issue}: {count:,}")
    
    print(f"\nOutput file: {OUTPUT_CSV}")
    print("=" * 80)

if __name__ == "__main__":
    main()

