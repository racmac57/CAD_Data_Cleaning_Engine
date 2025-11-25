"""
Apply rule-based address corrections from updates_corrections_FullAddress2.csv to address_corrections.csv.

This script:
1. Loads the rule-based mapping file
2. Applies rules to address_corrections.csv
3. Handles incomplete intersections by suggesting center-point intersections
"""

import pandas as pd
from pathlib import Path
import re

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
RULES_FILE = BASE_DIR / "test" / "updates_corrections_FullAddress2.csv"
ADDRESS_CSV = BASE_DIR / "manual_corrections" / "address_corrections.csv"

# Default center-point intersections for long streets
# These are suggested defaults when a street has "& ," (incomplete intersection)
# Based on user knowledge: Anderson Street runs East-West from Teaneck to Maywood
DEFAULT_INTERSECTIONS = {
    "Anderson Street": "Anderson Street & Prospect Avenue",
    "Essex Street": "Essex Street & Main Street",
    "Main Street": "Main Street & State Street",
    "Maple Avenue": "Maple Avenue & Park Avenue",
    "Park Street": "Park Street & Main Street",
    "South State Street": "South State Street & Main Street",
    "Union Street": "Union Street & Main Street",
    "Hackensack Avenue": "Hackensack Avenue & Main Street",
    "Euclid Avenue": "Euclid Avenue & Park Avenue",
    "Broadway": "Broadway & Main Street",
    "The Esplanade": "The Esplanade & Main Street",
    "Route 17 South": "Route 17 South & Main Street",
    "Route 80 East": "Route 80 East & Main Street",
    "Route 80 West": "Route 80 West & Main Street",
    "Route 4 East": "Route 4 East & Main Street",
    "Route 4 West": "Route 4 West & Main Street",
    # For generic "Area" or other non-street locations, use a central location
    "Area": "225 State Street, Hackensack, NJ, 07601",  # Central location for generic areas
    "Home": "225 State Street, Hackensack, NJ, 07601",  # Already in rules, but as fallback
}

print("="*80)
print("APPLYING RULE-BASED ADDRESS CORRECTIONS")
print("="*80)

# Step 1: Load rule file
print("\nStep 1: Loading rule file...")
try:
    rules_df = pd.read_csv(RULES_FILE, dtype=str).fillna('')
    print(f"  Loaded {len(rules_df):,} rules")
except Exception as e:
    print(f"  ERROR: Could not load rule file: {e}")
    exit(1)

# Step 2: Load address corrections
print("\nStep 2: Loading address corrections...")
try:
    addr_corrections = pd.read_csv(ADDRESS_CSV, dtype=str).fillna('')
    print(f"  Loaded {len(addr_corrections):,} records")
except Exception as e:
    print(f"  ERROR: Could not load address corrections: {e}")
    exit(1)

# Step 3: Apply rules
print("\nStep 3: Applying rule-based corrections...")

# Create a copy to track changes
addr_corrections['Original_Corrected_Value'] = addr_corrections['Corrected_Value'].copy()
rules_applied = 0
default_intersections_applied = 0

# First, identify all incomplete intersections that need default center-point intersections
print("\n  Identifying incomplete intersections...")
incomplete_mask = (
    addr_corrections['FullAddress2'].astype(str).str.contains(' & ,', case=False, na=False) &
    (addr_corrections['Corrected_Value'].astype(str).str.strip() == '')
)
incomplete_count = incomplete_mask.sum()
print(f"  Found {incomplete_count:,} incomplete intersections without corrections")

for idx, rule in rules_df.iterrows():
    incident_filter = str(rule['If Incident is']).strip()
    address_pattern = str(rule['And/Or If FullAddress2 is']).strip()
    corrected_value = str(rule['Then Change FullAddress2 to']).strip()
    
    # Skip empty rules
    if not address_pattern:
        continue
    
    # Build match mask
    mask = addr_corrections['FullAddress2'].astype(str).str.strip() == address_pattern
    
    # If incident filter is specified, add it to the mask
    if incident_filter:
        mask = mask & (addr_corrections['Incident'].astype(str).str.strip() == incident_filter)
    
    # Apply correction if we have a corrected value
    if corrected_value:
        matches = mask.sum()
        if matches > 0:
            # Only apply if Corrected_Value is currently empty
            apply_mask = mask & (addr_corrections['Corrected_Value'].astype(str).str.strip() == '')
            addr_corrections.loc[apply_mask, 'Corrected_Value'] = corrected_value
            addr_corrections.loc[apply_mask, 'Issue_Type'] = 'Rule-Based Correction'
            addr_corrections.loc[apply_mask, 'Notes'] = f'Applied from rule file: {incident_filter if incident_filter else "Any Incident"}'
            rules_applied += apply_mask.sum()
            print(f"  Applied rule: '{address_pattern[:50]}...' -> '{corrected_value[:50]}...' ({apply_mask.sum()} records)")
    
    # Handle incomplete intersections (empty corrected value but pattern matches)
    elif corrected_value == '' and ' & ,' in address_pattern:
        matches = mask.sum()
        if matches > 0:
            # Extract street name (before " & ,")
            street_match = re.match(r'^(.+?)\s*&\s*,', address_pattern)
            if street_match:
                street_name = street_match.group(1).strip()
                
                # Check if we have a default intersection for this street
                default_intersection = None
                for default_street, default_addr in DEFAULT_INTERSECTIONS.items():
                    if street_name.upper() == default_street.upper() or default_street.upper() in street_name.upper():
                        default_intersection = default_addr + ", Hackensack, NJ, 07601"
                        break
                
                # If no default found, try to construct one
                if not default_intersection:
                    # Try to find a common intersection pattern
                    # For now, use the street name with a generic intersection
                    default_intersection = f"{street_name} & Main Street, Hackensack, NJ, 07601"
                
                # Only apply if Corrected_Value is currently empty
                apply_mask = mask & (addr_corrections['Corrected_Value'].astype(str).str.strip() == '')
                if apply_mask.sum() > 0:
                    addr_corrections.loc[apply_mask, 'Corrected_Value'] = default_intersection
                    addr_corrections.loc[apply_mask, 'Issue_Type'] = 'Default Center-Point Intersection'
                    addr_corrections.loc[apply_mask, 'Notes'] = f'Applied default center-point intersection for incomplete intersection: {street_name}'
                    default_intersections_applied += apply_mask.sum()
                    print(f"  Applied default intersection: '{street_name}' -> '{default_intersection[:60]}...' ({apply_mask.sum()} records)")

# Step 3b: Apply default center-point intersections for any remaining incomplete intersections
print("\nStep 3b: Applying default center-point intersections to remaining incomplete intersections...")
remaining_incomplete = (
    addr_corrections['FullAddress2'].astype(str).str.contains(' & ,', case=False, na=False) &
    (addr_corrections['Corrected_Value'].astype(str).str.strip() == '')
)

if remaining_incomplete.sum() > 0:
    for idx in addr_corrections[remaining_incomplete].index:
        addr = str(addr_corrections.loc[idx, 'FullAddress2']).strip()
        # Extract street name (before " & ,")
        street_match = re.match(r'^(.+?)\s*&\s*,', addr)
        if street_match:
            street_name = street_match.group(1).strip()
            
            # Check if we have a default intersection for this street
            default_intersection = None
            
            # Special handling for "Area", "Home", etc.
            if street_name.upper().startswith("AREA"):
                default_intersection = DEFAULT_INTERSECTIONS.get("Area", "225 State Street, Hackensack, NJ, 07601")
            elif street_name.upper() in ["HOME", "HOME "]:
                default_intersection = DEFAULT_INTERSECTIONS.get("Home", "225 State Street, Hackensack, NJ, 07601")
            else:
                # Check for exact or partial match in DEFAULT_INTERSECTIONS
                for default_street, default_addr in DEFAULT_INTERSECTIONS.items():
                    if default_street in ["Area", "Home"]:
                        continue  # Skip these, already handled
                    if street_name.upper() == default_street.upper() or default_street.upper() in street_name.upper():
                        # If default_addr already includes city/state/zip, use as-is
                        if ", Hackensack" in default_addr or ", NJ" in default_addr:
                            default_intersection = default_addr
                        else:
                            default_intersection = default_addr + ", Hackensack, NJ, 07601"
                        break
            
            # If no default found, try to construct one
            if not default_intersection:
                # Use the street name with a generic intersection
                default_intersection = f"{street_name} & Main Street, Hackensack, NJ, 07601"
            
            addr_corrections.loc[idx, 'Corrected_Value'] = default_intersection
            addr_corrections.loc[idx, 'Issue_Type'] = 'Default Center-Point Intersection'
            addr_corrections.loc[idx, 'Notes'] = f'Applied default center-point intersection for incomplete intersection: {street_name}'
            default_intersections_applied += 1
    
    print(f"  Applied {default_intersections_applied:,} default center-point intersections")

# Step 4: Save updated file
print("\nStep 4: Saving updated address corrections...")
try:
    # Remove the temporary column
    addr_corrections = addr_corrections.drop(columns=['Original_Corrected_Value'])
    addr_corrections.to_csv(ADDRESS_CSV, index=False)
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
print(f"Total records in address_corrections.csv: {len(addr_corrections):,}")
print(f"Rule-based corrections applied: {rules_applied:,}")
print(f"Default center-point intersections applied: {default_intersections_applied:,}")
print(f"Total corrections now in file: {(addr_corrections['Corrected_Value'].astype(str).str.strip() != '').sum():,}")

# Show sample of default intersections applied
if default_intersections_applied > 0:
    print("\nSample of default center-point intersections applied:")
    default_samples = addr_corrections[
        (addr_corrections['Issue_Type'] == 'Default Center-Point Intersection') &
        (addr_corrections['Corrected_Value'].astype(str).str.strip() != '')
    ][['FullAddress2', 'Corrected_Value']].head(10)
    for _, row in default_samples.iterrows():
        print(f"  {row['FullAddress2'][:50]:50} -> {row['Corrected_Value'][:60]}")

print("\n" + "="*80)
print("COMPLETE")
print("="*80)

