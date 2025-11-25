"""
Backfill incomplete addresses from RMS data and apply rule-based corrections.

This script:
1. Identifies incomplete FullAddress2 (missing street number OR incomplete intersections)
2. Matches ReportNumberNew to RMS Case Number
3. Backfills from RMS FullAddress
4. Applies rule-based corrections from updates_corrections_FullAddress2.csv
5. Does NOT use default center-point intersections
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
RMS_PATH = BASE_DIR / "data" / "rms" / "2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx"
RULES_FILE = BASE_DIR / "test" / "updates_corrections_FullAddress2.csv"
ADDRESS_CSV = BASE_DIR / "manual_corrections" / "address_corrections.csv"

# Address quality patterns
STREET_TYPES = [
    "STREET", "ST", "AVENUE", "AVE", "ROAD", "RD", "DRIVE", "DR", "LANE", "LN",
    "BOULEVARD", "BLVD", "COURT", "CT", "PLACE", "PL", "CIRCLE", "CIR",
    "TERRACE", "TER", "WAY", "PARKWAY", "PKWY", "HIGHWAY", "HWY", "PLAZA",
    "SQUARE", "SQ", "TRAIL", "TRL", "PATH", "ALLEY", "WALK", "EXPRESSWAY",
    "TURNPIKE", "TPKE", "ROUTE", "RT"
]

STREET_REGEX = r"\b(?:" + "|".join(STREET_TYPES) + r")\b"

def is_incomplete_address(address):
    """
    Check if address is incomplete:
    - Missing street number (doesn't start with a number for standard addresses)
    - Incomplete intersection (contains " & ," pattern - missing second street)
    - Generic terms (home, unknown, various, etc.)
    """
    if pd.isna(address) or str(address).strip() == "":
        return True, "blank"
    
    addr = str(address).strip()
    addr_upper = addr.upper()
    
    # Check for incomplete intersection (contains " & ," - missing second street)
    if re.search(r'&\s*,', addr_upper):
        # This is an incomplete intersection - missing the second street name
        return True, "incomplete_intersection"
    
    # Check for generic terms
    generic_terms = ["HOME", "VARIOUS", "UNKNOWN", "PARKING GARAGE", "REAR LOT", 
                     "PARKING LOT", "LOT", "GARAGE", "AREA", "LOCATION", "SCENE"]
    for term in generic_terms:
        if re.search(rf'\b{re.escape(term)}\b', addr_upper):
            return True, "generic_location"
    
    # Check for missing street number (standard address should start with number)
    # But skip if it's a complete intersection (has " & " with both streets)
    if " & " in addr_upper and not re.search(r'&\s*,', addr_upper):
        # This is a complete intersection, check if both parts are valid
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
    
    return False, "valid"

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
    generic_terms = [
        "HOME", "VARIOUS", "UNKNOWN", "PARKING GARAGE", "REAR LOT", "PARKING LOT",
        "LOT", "GARAGE", "REAR", "FRONT", "SIDE", "BEHIND", "ACROSS", "NEAR",
        "BETWEEN", "AREA", "LOCATION", "SCENE", "UNDETERMINED", "N/A", "NA",
        "NONE", "BLANK", "PARK"
    ]
    
    for term in generic_terms:
        if addr_upper.startswith(term) or f" {term} " in addr_upper:
            # Park special case with intersection
            if term == "PARK" and "&" in addr:
                parts = addr.split("&")
                if len(parts) == 2 and re.search(STREET_REGEX, parts[1], re.IGNORECASE):
                    break
            return "generic_location", f"Generic term: {term}"

    # Intersection
    if "&" in addr:
        parts = addr.split("&")
        if len(parts) == 2:
            part1 = parts[0].strip()
            part2 = parts[1].strip()

            if (
                not part2
                or part2.startswith(",")
                or re.match(r"^,?\s*(Hackensack|NJ|0760)", part2, re.IGNORECASE)
            ):
                return "incomplete_intersection", "Missing second street in intersection"

            has_type1 = bool(re.search(STREET_REGEX, part1, re.IGNORECASE))
            has_type2 = bool(re.search(STREET_REGEX, part2, re.IGNORECASE))

            if has_type1 and has_type2:
                return "valid_intersection", "Valid intersection format"
            if not has_type1 and not has_type2:
                return "missing_street_type", "Both streets missing type"
            if not has_type1:
                return "missing_street_type", f"First street missing type: {part1}"
            return "missing_street_type", f"Second street missing type: {part2}"

    # Standard address starting with a number
    if re.match(r"^\d+", addr):
        has_street = bool(re.search(STREET_REGEX, addr_upper, re.IGNORECASE))
        has_city_state_zip = bool(re.search(r"Hackensack.*NJ.*0760", addr, re.IGNORECASE))
        
        if has_street:
            if has_city_state_zip:
                return "valid_standard", "Valid standard address"
            return "incomplete", "Missing city/state/zip"
        return "missing_street_type", "No street type suffix"

    # No number, possible named location
    if re.search(STREET_REGEX, addr, re.IGNORECASE):
        return "missing_street_number", "Street name without number"

    if re.match(r"^(Hackensack|NJ|0760)", addr, re.IGNORECASE):
        return "incomplete", "City/state only"

    return "missing_street_number", "No street number"

print("="*80)
print("BACKFILLING INCOMPLETE ADDRESSES FROM RMS")
print("="*80)
print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Step 1: Load ESRI file
print("Step 1: Loading ESRI file...")
esri_df = pd.read_excel(ESRI_FILE, dtype=str)
print(f"  Loaded {len(esri_df):,} records")

# Step 2: Identify incomplete addresses
print("\nStep 2: Identifying incomplete addresses...")
incomplete_results = esri_df['FullAddress2'].apply(is_incomplete_address)
incomplete_mask = incomplete_results.apply(lambda x: x[0])
incomplete_addresses = esri_df[incomplete_mask].copy()
print(f"  Found {len(incomplete_addresses):,} records with incomplete addresses")

# Show breakdown by issue type
issue_types = incomplete_results[incomplete_mask].apply(lambda x: x[1])
print(f"\n  Breakdown by issue type:")
for issue_type, count in issue_types.value_counts().items():
    print(f"    {issue_type}: {count:,}")

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

# Step 5: Validate RMS addresses (must be complete/valid)
print("\nStep 5: Validating RMS addresses...")
rms_matches['RMS_Category'] = rms_matches['RMS_Address'].apply(lambda x: categorize_address(x)[0])
valid_cats = {"valid_standard", "valid_intersection"}
rms_matches['RMS_Is_Valid'] = rms_matches['RMS_Category'].isin(valid_cats)
valid_rms_matches = rms_matches[rms_matches['RMS_Is_Valid']].copy()
print(f"  Found {len(valid_rms_matches):,} RMS addresses that are complete/valid")
print(f"  RMS address categories: {rms_matches['RMS_Category'].value_counts().to_dict()}")

# Step 6: Load rule-based corrections
print("\nStep 6: Loading rule-based corrections...")
try:
    rules_df = pd.read_csv(RULES_FILE, dtype=str).fillna('')
    print(f"  Loaded {len(rules_df):,} rules")
except Exception as e:
    print(f"  ERROR: Could not load rule file: {e}")
    rules_df = pd.DataFrame()

# Step 7: Load existing address corrections
print("\nStep 7: Loading existing address corrections...")
if ADDRESS_CSV.exists():
    addr_corrections = pd.read_csv(ADDRESS_CSV, dtype=str).fillna('')
    print(f"  Loaded {len(addr_corrections):,} existing records")
    
    # Remove all default center-point intersections (Issue_Type == 'Default Center-Point Intersection')
    before_remove = len(addr_corrections)
    addr_corrections = addr_corrections[
        addr_corrections['Issue_Type'] != 'Default Center-Point Intersection'
    ].copy()
    removed = before_remove - len(addr_corrections)
    if removed > 0:
        print(f"  Removed {removed:,} default center-point intersections")
else:
    addr_corrections = pd.DataFrame(columns=[
        'ReportNumberNew', 'TimeOfCall', 'FullAddress2', 'Incident', 
        'Corrected_Value', 'Issue_Type', 'Notes'
    ])
    print("  Creating new file")

# Step 8: Apply RMS backfills
print("\nStep 8: Applying RMS backfills...")
rms_backfill = valid_rms_matches[[
    'ReportNumberNew', 'TimeOfCall', 'FullAddress2', 'Incident'
]].copy()
rms_backfill['Corrected_Value'] = valid_rms_matches['RMS_Address']
rms_backfill['Issue_Type'] = 'RMS Backfill'
rms_backfill['Notes'] = 'Backfilled from RMS export'

# Remove existing records that will be updated by RMS
existing_report_nums = set(addr_corrections['ReportNumberNew'].astype(str).str.strip())
rms_report_nums = set(rms_backfill['ReportNumberNew'].astype(str).str.strip())

# Keep existing records that aren't in RMS backfill
addr_corrections_keep = addr_corrections[
    ~addr_corrections['ReportNumberNew'].astype(str).str.strip().isin(rms_report_nums)
].copy()

# Step 9: Apply rule-based corrections
print("\nStep 9: Applying rule-based corrections...")
rules_applied = 0

# Create a combined dataset for rule application
combined_df = pd.concat([addr_corrections_keep, rms_backfill], ignore_index=True)

for idx, rule in rules_df.iterrows():
    incident_filter = str(rule['If Incident is']).strip()
    address_pattern = str(rule['And/Or If FullAddress2 is']).strip()
    corrected_value = str(rule['Then Change FullAddress2 to']).strip()
    
    # Skip empty rules or empty corrections
    if not address_pattern or not corrected_value:
        continue
    
    # Build match mask
    mask = combined_df['FullAddress2'].astype(str).str.strip() == address_pattern
    
    # If incident filter is specified, add it to the mask
    if incident_filter:
        mask = mask & (combined_df['Incident'].astype(str).str.strip() == incident_filter)
    
    # Apply correction
    matches = mask.sum()
    if matches > 0:
        # Override existing corrections with rule-based corrections
        combined_df.loc[mask, 'Corrected_Value'] = corrected_value
        combined_df.loc[mask, 'Issue_Type'] = 'Rule-Based Correction'
        combined_df.loc[mask, 'Notes'] = f'Applied from rule file: {incident_filter if incident_filter else "Any Incident"}'
        rules_applied += matches

print(f"  Applied {rules_applied:,} rule-based corrections")

# Step 10: Save updated file
print("\nStep 10: Saving updated address corrections...")
try:
    combined_df.to_csv(ADDRESS_CSV, index=False)
    print(f"  Saved: {ADDRESS_CSV}")
except PermissionError:
    print(f"  ERROR: Permission denied. Please close '{ADDRESS_CSV.name}' if it's open in Excel.")
    exit(1)
except Exception as e:
    print(f"  ERROR: Could not save file: {e}")
    exit(1)

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total incomplete addresses: {len(incomplete_addresses):,}")
print(f"RMS matches found: {len(rms_matches):,}")
print(f"Valid RMS addresses (complete): {len(valid_rms_matches):,}")
print(f"Rule-based corrections applied: {rules_applied:,}")
print(f"\nUpdated address_corrections.csv:")
print(f"  Total records: {len(combined_df):,}")
print(f"  RMS backfilled: {len(rms_backfill):,}")
print(f"  Rule-based corrections: {rules_applied:,}")
print(f"  Existing records kept: {len(addr_corrections_keep):,}")

print(f"\nSaved: {ADDRESS_CSV}")
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

print(f"\nNext step: Run apply_manual_corrections.py to apply these corrections to the ESRI file")

