"""
Update address_corrections.csv with RMS backfills for all incomplete addresses.

This script:
1. Checks all 700K+ records for incomplete FullAddress2
2. Matches ReportNumberNew to RMS Case Number
3. Updates address_corrections.csv with RMS addresses where available
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
RMS_PATH = BASE_DIR / "data" / "rms" / "2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx"
ADDRESS_CSV = BASE_DIR / "manual_corrections" / "address_corrections.csv"

# Address quality patterns
STREET_TYPES = [
    "STREET", "ST", "AVENUE", "AVE", "ROAD", "RD", "DRIVE", "DR", "LANE", "LN",
    "BOULEVARD", "BLVD", "COURT", "CT", "PLACE", "PL", "CIRCLE", "CIR",
    "TERRACE", "TER", "WAY", "PARKWAY", "PKWY", "HIGHWAY", "HWY", "PLAZA",
    "SQUARE", "SQ", "TRAIL", "TRL", "PATH", "ALLEY", "WALK", "EXPRESSWAY",
    "TURNPIKE", "TPKE", "ROUTE", "RT"
]

GENERIC_TERMS = [
    "HOME", "VARIOUS", "UNKNOWN", "PARKING GARAGE", "REAR LOT", "PARKING LOT",
    "LOT", "GARAGE", "REAR", "FRONT", "SIDE", "BEHIND", "ACROSS", "NEAR",
    "BETWEEN", "AREA", "LOCATION", "SCENE", "UNDETERMINED", "N/A", "NA",
    "NONE", "BLANK", "PARK", " & "
]

STREET_REGEX = r"\b(?:" + "|".join(STREET_TYPES) + r")\b"
CITY_STATE_ZIP_REGEX = r"Hackensack.*NJ.*0760"

def categorize_address(address):
    """
    Categorize an address into quality buckets (same logic as backfill_address_from_rms.py).
    Returns: (category, reason)
    """
    if pd.isna(address) or str(address).strip() == "":
        return "blank", "Null or empty address"

    addr = str(address).strip()
    addr_upper = addr.upper()

    # PO Box
    if re.search(r"P\.?O\.?\s*BOX", addr_upper):
        return "po_box", "PO Box address"

    # Generic location terms
    for term in GENERIC_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", addr_upper):
            return "generic_location", f"Contains generic term: {term}"

    # Check for street type
    has_street = bool(re.search(STREET_REGEX, addr_upper, re.IGNORECASE))
    
    # Check for city/state/zip
    has_city_state_zip = bool(re.search(CITY_STATE_ZIP_REGEX, addr, re.IGNORECASE))
    
    # Intersection pattern (Street & Street)
    if " & " in addr_upper:
        if has_street and has_city_state_zip:
            return "valid_intersection", "Valid intersection address"
        else:
            return "incomplete_intersection", "Incomplete intersection"

    # Standard address
    if has_street and has_city_state_zip:
        return "valid_standard", "Valid standard address"
    
    if not has_street:
        return "missing_street_type", "Missing street type"
    
    if not has_city_state_zip:
        return "missing_city_state_zip", "Missing city/state/zip"
    
    return "incomplete", "Incomplete address"

def is_incomplete_address(address):
    """Check if address is incomplete (missing street type, generic, etc.)."""
    category, _ = categorize_address(address)
    valid_cats = {"valid_standard", "valid_intersection"}
    return category not in valid_cats, category

print("="*80)
print("UPDATING ADDRESS CORRECTIONS WITH RMS BACKFILL")
print("="*80)
print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Step 1: Load ESRI file
print("Step 1: Loading ESRI file...")
esri_df = pd.read_excel(ESRI_FILE, dtype=str)
print(f"  Loaded {len(esri_df):,} records")

# Step 2: Identify incomplete addresses
print("\nStep 2: Identifying incomplete addresses...")
incomplete_mask = esri_df['FullAddress2'].apply(lambda x: is_incomplete_address(x)[0])
incomplete_addresses = esri_df[incomplete_mask].copy()
print(f"  Found {len(incomplete_addresses):,} records with incomplete addresses")

# Step 3: Load RMS export
print("\nStep 3: Loading RMS export...")
rms_df = pd.read_excel(RMS_PATH, dtype=str)
print(f"  Loaded {len(rms_df):,} RMS records")

# Find address column in RMS
rms_address_col = None
for col in rms_df.columns:
    if 'address' in col.lower() or 'location' in col.lower():
        rms_address_col = col
        break

if not rms_address_col:
    print("  [WARNING] Could not find address column in RMS. Trying common names...")
    for col in ['FullAddress', 'Address', 'Location', 'Incident Location']:
        if col in rms_df.columns:
            rms_address_col = col
            break

if not rms_address_col:
    print(f"  Available RMS columns: {list(rms_df.columns)[:10]}...")
    raise ValueError("Could not identify RMS address column")

print(f"  Using RMS column: {rms_address_col}")

# Create RMS lookup: Case Number -> Address
rms_lookup = rms_df.set_index('Case Number')[rms_address_col].to_dict()
print(f"  Created lookup for {len(rms_lookup):,} RMS case numbers")

# Step 4: Match incomplete addresses to RMS
print("\nStep 4: Matching incomplete addresses to RMS...")
incomplete_addresses['RMS_Address'] = incomplete_addresses['ReportNumberNew'].astype(str).str.strip().map(rms_lookup)
rms_matches = incomplete_addresses[incomplete_addresses['RMS_Address'].notna()].copy()
print(f"  Found {len(rms_matches):,} incomplete addresses that match RMS Case Number")

# Step 5: Check if RMS address is better (complete)
print("\nStep 5: Validating RMS addresses...")
rms_matches['RMS_Category'] = rms_matches['RMS_Address'].apply(lambda x: categorize_address(x)[0])
valid_cats = {"valid_standard", "valid_intersection"}
rms_matches['RMS_Is_Complete'] = rms_matches['RMS_Category'].isin(valid_cats)
valid_rms_matches = rms_matches[rms_matches['RMS_Is_Complete']].copy()
print(f"  Found {len(valid_rms_matches):,} RMS addresses that are complete/valid")
print(f"  RMS address categories: {rms_matches['RMS_Category'].value_counts().to_dict()}")

# Step 6: Update address_corrections.csv
print("\nStep 6: Updating address_corrections.csv...")

# Load existing address corrections
if ADDRESS_CSV.exists():
    addr_corrections = pd.read_csv(ADDRESS_CSV)
    print(f"  Loaded existing file with {len(addr_corrections):,} records")
else:
    # Create new file structure
    addr_corrections = pd.DataFrame(columns=[
        'ReportNumberNew', 'TimeOfCall', 'FullAddress2', 'Incident', 
        'Corrected_Value', 'Issue_Type', 'Notes'
    ])
    print(f"  Creating new file")

# Prepare RMS backfill records
rms_backfill = valid_rms_matches[[
    'ReportNumberNew', 'TimeOfCall', 'FullAddress2', 'Incident'
]].copy()
rms_backfill['Corrected_Value'] = valid_rms_matches['RMS_Address']
rms_backfill['Issue_Type'] = 'RMS Backfill'
rms_backfill['Notes'] = 'Backfilled from RMS export'

# Merge with existing corrections
# Remove existing records that will be updated by RMS
existing_report_nums = set(addr_corrections['ReportNumberNew'].astype(str))
rms_report_nums = set(rms_backfill['ReportNumberNew'].astype(str))

# Keep existing records that aren't in RMS backfill
addr_corrections_keep = addr_corrections[
    ~addr_corrections['ReportNumberNew'].astype(str).isin(rms_report_nums)
].copy()

# Combine: existing (non-RMS) + RMS backfills
addr_corrections_updated = pd.concat([addr_corrections_keep, rms_backfill], ignore_index=True)

# Remove duplicates (keep RMS backfill if duplicate)
addr_corrections_updated = addr_corrections_updated.drop_duplicates(
    subset=['ReportNumberNew'], 
    keep='last'  # Keep RMS backfill if duplicate
)

# Save
addr_corrections_updated.to_csv(ADDRESS_CSV, index=False)

print(f"\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total incomplete addresses: {len(incomplete_addresses):,}")
print(f"RMS matches found: {len(rms_matches):,}")
print(f"Valid RMS addresses (complete): {len(valid_rms_matches):,}")
print(f"\nUpdated address_corrections.csv:")
print(f"  Total records: {len(addr_corrections_updated):,}")
print(f"  RMS backfilled: {len(rms_backfill):,}")
print(f"  Existing records kept: {len(addr_corrections_keep):,}")

print(f"\nSaved: {ADDRESS_CSV}")
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

print(f"\nNext step: Run apply_manual_corrections.py to apply these corrections to the ESRI file")

