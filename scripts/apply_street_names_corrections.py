"""
Apply street name corrections using the official Hackensack street names file.

This script:
1. Loads the official street names from hackensack_municipal_streets_from_lawsoft_25_11_24.xlsx
2. Identifies addresses that are missing street type suffixes (e.g., "University Plaza" -> "University Plaza Drive")
3. Applies corrections to address_corrections.csv
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
STREET_NAMES_FILE = BASE_DIR / "ref" / "hackensack_municipal_streets_from_lawsoft_25_11_24.xlsx"
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
ADDRESS_CSV = BASE_DIR / "manual_corrections" / "address_corrections.csv"

print("="*80)
print("APPLYING STREET NAMES CORRECTIONS")
print("="*80)
print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Step 1: Load official street names
print("Step 1: Loading official street names...")
try:
    streets_df = pd.read_excel(STREET_NAMES_FILE, dtype=str)
    print(f"  Loaded {len(streets_df):,} street names")
    print(f"  Columns: {list(streets_df.columns)}")
except Exception as e:
    print(f"  ERROR: Could not load street names file: {e}")
    exit(1)

# Create a lookup: street name without suffix -> full street name with suffix
# Example: "University Plaza" -> "University Plaza Drive"
street_lookup = {}
for _, row in streets_df.iterrows():
    street_name = str(row['Street']).strip()
    if street_name:
        # Extract base name (without suffix)
        # For "University Plaza Drive", base would be "University Plaza"
        base_match = re.match(r'^(.+?)\s+(Drive|Street|Avenue|Road|Place|Court|Lane|Boulevard|Way|Circle|Terrace|Parkway|Highway|Plaza|Square|Trail|Path|Alley|Walk|Expressway|Turnpike|Route)$', street_name, re.IGNORECASE)
        if base_match:
            base_name = base_match.group(1).strip()
            # Store mapping: base name -> full name
            if base_name not in street_lookup:
                street_lookup[base_name.upper()] = street_name
            # Also store the full name itself
            street_lookup[street_name.upper()] = street_name

print(f"  Created lookup for {len(street_lookup):,} street name variations")

# Step 2: Load ESRI file to find addresses needing correction
print("\nStep 2: Loading ESRI file...")
esri_df = pd.read_excel(ESRI_FILE, dtype=str)
print(f"  Loaded {len(esri_df):,} records")

# Step 3: Load existing address corrections
print("\nStep 3: Loading existing address corrections...")
if ADDRESS_CSV.exists():
    addr_corrections = pd.read_csv(ADDRESS_CSV, dtype=str).fillna('')
    print(f"  Loaded {len(addr_corrections):,} existing records")
else:
    addr_corrections = pd.DataFrame(columns=[
        'ReportNumberNew', 'TimeOfCall', 'FullAddress2', 'Incident', 
        'Corrected_Value', 'Issue_Type', 'Notes'
    ])
    print("  Creating new file")

# Step 4: Find addresses in ESRI that need street name corrections
print("\nStep 4: Identifying addresses needing street name corrections...")

# Get addresses that are not yet in corrections or don't have corrections
esri_addresses = esri_df[['ReportNumberNew', 'TimeOfCall', 'FullAddress2', 'Incident']].copy()
existing_report_nums = set(addr_corrections['ReportNumberNew'].astype(str).str.strip())
esri_addresses = esri_addresses[
    ~esri_addresses['ReportNumberNew'].astype(str).str.strip().isin(existing_report_nums)
].copy()

print(f"  Checking {len(esri_addresses):,} addresses not yet in corrections")

# Function to extract street name from address
def extract_street_name(address):
    """Extract street name from address for matching."""
    if pd.isna(address) or str(address).strip() == "":
        return None
    
    addr = str(address).strip()
    
    # Remove city/state/zip
    addr = re.sub(r',\s*Hackensack.*$', '', addr, flags=re.IGNORECASE)
    
    # Extract street name (before comma or end)
    # Pattern: "123 Street Name" or "Street Name & Other Street"
    match = re.match(r'^\d+\s+(.+?)(?:\s*&\s*|,|$)', addr)
    if match:
        street_part = match.group(1).strip()
        # Remove trailing comma if present
        street_part = street_part.rstrip(',')
        return street_part
    
    # Try without number (for intersections or named locations)
    match = re.match(r'^(.+?)(?:\s*&\s*|,|$)', addr)
    if match:
        street_part = match.group(1).strip()
        # Remove trailing comma if present
        street_part = street_part.rstrip(',')
        return street_part
    
    return None

# Find addresses that need corrections
new_corrections = []
corrections_applied = 0

for idx, row in esri_addresses.iterrows():
    addr = str(row['FullAddress2']).strip()
    if not addr:
        continue
    
    # Extract street name
    street_name = extract_street_name(addr)
    if not street_name:
        continue
    
    # Check if street name (without suffix) is in lookup
    street_upper = street_name.upper()
    if street_upper in street_lookup:
        full_street_name = street_lookup[street_upper]
        
        # Only correct if the address doesn't already have the full street name
        if full_street_name.upper() not in addr.upper():
            # Build corrected address
            # Replace the street name part with the full street name
            corrected_addr = re.sub(
                rf'\b{re.escape(street_name)}\b',
                full_street_name,
                addr,
                count=1,
                flags=re.IGNORECASE
            )
            
            # Only add if correction is different
            if corrected_addr != addr:
                new_corrections.append({
                    'ReportNumberNew': str(row['ReportNumberNew']).strip(),
                    'TimeOfCall': str(row.get('TimeOfCall', '')),
                    'FullAddress2': addr,
                    'Incident': str(row.get('Incident', '')),
                    'Corrected_Value': corrected_addr,
                    'Issue_Type': 'Street Name Correction',
                    'Notes': f'Applied official street name: {street_name} -> {full_street_name}'
                })
                corrections_applied += 1

print(f"  Found {corrections_applied:,} addresses needing street name corrections")

# Step 5: Also check existing corrections that might need updates
print("\nStep 5: Checking existing corrections for street name updates...")
existing_updates = 0

for idx, row in addr_corrections.iterrows():
    addr = str(row['FullAddress2']).strip()
    corrected = str(row.get('Corrected_Value', '')).strip()
    
    # Skip if already corrected or empty
    if not corrected or corrected == '':
        continue
    
    # Extract street name from original address
    street_name = extract_street_name(addr)
    if not street_name:
        continue
    
    # Check if street name needs correction
    street_upper = street_name.upper()
    if street_upper in street_lookup:
        full_street_name = street_lookup[street_upper]
        
        # Check if corrected address also needs the street name fix
        if full_street_name.upper() not in corrected.upper():
            # Update the corrected value
            updated_corrected = re.sub(
                rf'\b{re.escape(street_name)}\b',
                full_street_name,
                corrected,
                count=1,
                flags=re.IGNORECASE
            )
            
            if updated_corrected != corrected:
                addr_corrections.loc[idx, 'Corrected_Value'] = updated_corrected
                if addr_corrections.loc[idx, 'Issue_Type'] == '':
                    addr_corrections.loc[idx, 'Issue_Type'] = 'Street Name Correction'
                existing_updates += 1

print(f"  Updated {existing_updates:,} existing corrections")

# Step 6: Add new corrections
if new_corrections:
    new_df = pd.DataFrame(new_corrections)
    addr_corrections = pd.concat([addr_corrections, new_df], ignore_index=True)
    print(f"\n  Added {len(new_corrections):,} new corrections")

# Step 7: Save updated file
print("\nStep 7: Saving updated address corrections...")
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
print(f"Total records in address_corrections.csv: {len(addr_corrections):,}")
print(f"New street name corrections added: {len(new_corrections):,}")
print(f"Existing corrections updated: {existing_updates:,}")
print(f"Total corrections with values: {(addr_corrections['Corrected_Value'].astype(str).str.strip() != '').sum():,}")

# Show sample corrections
if new_corrections:
    print("\nSample of street name corrections:")
    for i, corr in enumerate(new_corrections[:10]):
        print(f"  {corr['FullAddress2'][:50]:50} -> {corr['Corrected_Value'][:60]}")

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

