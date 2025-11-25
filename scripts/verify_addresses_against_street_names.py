"""
Verify addresses against official street names and mark correct addresses.

This script:
1. Loads official street names
2. Checks if addresses in address_corrections.csv are already correct
3. Removes or marks correct addresses so they don't need correction
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
STREET_NAMES_FILE = BASE_DIR / "ref" / "hackensack_municipal_streets_from_lawsoft_25_11_24.xlsx"
ADDRESS_CSV = BASE_DIR / "manual_corrections" / "address_corrections.csv"

print("="*80)
print("VERIFYING ADDRESSES AGAINST OFFICIAL STREET NAMES")
print("="*80)
print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Step 1: Load official street names
print("Step 1: Loading official street names...")
try:
    streets_df = pd.read_excel(STREET_NAMES_FILE, dtype=str)
    print(f"  Loaded {len(streets_df):,} street names")
    
    # Create set of all official street names (case-insensitive)
    official_streets = set(streets_df['Street'].astype(str).str.strip().str.upper())
    print(f"  Created lookup for {len(official_streets):,} official street names")
except Exception as e:
    print(f"  ERROR: Could not load street names file: {e}")
    exit(1)

# Step 2: Load address corrections
print("\nStep 2: Loading address corrections...")
try:
    addr_corrections = pd.read_csv(ADDRESS_CSV, dtype=str).fillna('')
    print(f"  Loaded {len(addr_corrections):,} records")
except Exception as e:
    print(f"  ERROR: Could not load file: {e}")
    exit(1)

# Step 3: Function to extract street name from address
def extract_street_from_address(address):
    """Extract the street name part from a full address."""
    if pd.isna(address) or str(address).strip() == "":
        return None
    
    addr = str(address).strip()
    
    # Remove city/state/zip
    addr = re.sub(r',\s*Hackensack.*$', '', addr, flags=re.IGNORECASE)
    
    # Extract street name (after house number, before comma or intersection)
    # Pattern: "123 Street Name" or "Street Name & Other Street"
    match = re.match(r'^\d+\s+(.+?)(?:\s*&\s*|,|$)', addr)
    if match:
        street_part = match.group(1).strip().rstrip(',')
        return street_part
    
    # Try without number (for intersections or named locations)
    match = re.match(r'^(.+?)(?:\s*&\s*|,|$)', addr)
    if match:
        street_part = match.group(1).strip().rstrip(',')
        return street_part
    
    return None

# Step 4: Check which addresses are already correct
print("\nStep 3: Checking which addresses are already correct...")
correct_addresses = []
needs_correction = []

for idx, row in addr_corrections.iterrows():
    addr = str(row['FullAddress2']).strip()
    corrected = str(row.get('Corrected_Value', '')).strip()
    
    # Skip if already has correction
    if corrected and corrected != '':
        needs_correction.append(idx)
        continue
    
    # Extract street name
    street_name = extract_street_from_address(addr)
    if not street_name:
        needs_correction.append(idx)
        continue
    
    # Check if street name matches an official street name
    street_upper = street_name.upper()
    
    # Check exact match
    if street_upper in official_streets:
        # Address is already correct - mark it as such
        addr_corrections.loc[idx, 'Corrected_Value'] = addr  # Keep original (it's correct)
        addr_corrections.loc[idx, 'Issue_Type'] = 'Verified Correct'
        addr_corrections.loc[idx, 'Notes'] = f'Verified against official street names: {street_name} is correct'
        correct_addresses.append(idx)
        continue
    
    # Check if any official street contains this street name (for partial matches)
    # e.g., "Cambridge Terrace" should match "Cambridge Terrace" in official list
    matched = False
    for official_street in official_streets:
        if street_upper == official_street or street_upper in official_street or official_street in street_upper:
            # Found a match - address is correct
            addr_corrections.loc[idx, 'Corrected_Value'] = addr
            addr_corrections.loc[idx, 'Issue_Type'] = 'Verified Correct'
            addr_corrections.loc[idx, 'Notes'] = f'Verified against official street names: {street_name} matches {official_street}'
            correct_addresses.append(idx)
            matched = True
            break
    
    if not matched:
        needs_correction.append(idx)

print(f"  Found {len(correct_addresses):,} addresses that are already correct")
print(f"  Found {len(needs_correction):,} addresses that still need correction")

# Show examples of correct addresses
if correct_addresses:
    print("\n  Sample of verified correct addresses:")
    sample = addr_corrections.loc[correct_addresses[:10], ['FullAddress2', 'Corrected_Value', 'Issue_Type']]
    for _, row in sample.iterrows():
        print(f"    {row['FullAddress2'][:60]:60} -> Verified Correct")

# Step 5: Save updated file
print("\nStep 4: Saving updated address corrections...")
try:
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
print(f"Total records: {len(addr_corrections):,}")
print(f"Addresses verified as correct: {len(correct_addresses):,}")
print(f"Addresses still needing correction: {len(needs_correction):,}")
print(f"Records with corrections: {(addr_corrections['Corrected_Value'].astype(str).str.strip() != '').sum():,}")

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

print("\nNote: Addresses verified as correct have been marked with 'Verified Correct' in Issue_Type")
print("They will be included when applying corrections but won't change the original address.")

