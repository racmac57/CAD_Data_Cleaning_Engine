"""
Apply default center-point intersection for Anderson Street and other long streets.

This script specifically handles "Anderson Street & ," entries by applying
"Anderson Street & Prospect Avenue" as the default center-point intersection,
as suggested by the user (Anderson Street runs East-West from Teaneck to Maywood).
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
ADDRESS_CSV = BASE_DIR / "manual_corrections" / "address_corrections.csv"

# Default center-point intersections for long streets
# Based on user knowledge of street geography
LONG_STREET_DEFAULTS = {
    "Anderson Street & ,": "Anderson Street & Prospect Avenue, Hackensack, NJ, 07601",
    "Essex Street & ,": "Essex Street & Main Street, Hackensack, NJ, 07601",
    "Main Street & ,": "Main Street & State Street, Hackensack, NJ, 07601",
    "Maple Avenue & ,": "Maple Avenue & Park Avenue, Hackensack, NJ, 07601",
    "Park Street & ,": "Park Street & Main Street, Hackensack, NJ, 07601",
    "South State Street & ,": "South State Street & Main Street, Hackensack, NJ, 07601",
    "Union Street & ,": "Union Street & Main Street, Hackensack, NJ, 07601",
    "Hackensack Avenue & ,": "Hackensack Avenue & Main Street, Hackensack, NJ, 07601",
    "Euclid Avenue & ,": "Euclid Avenue & Park Avenue, Hackensack, NJ, 07601",
    "Broadway & ,": "Broadway & Main Street, Hackensack, NJ, 07601",
    "The Esplanade & ,": "The Esplanade & Main Street, Hackensack, NJ, 07601",
}

print("="*80)
print("APPLYING DEFAULT CENTER-POINT INTERSECTIONS FOR LONG STREETS")
print("="*80)

# Step 1: Load ESRI file to find all incomplete intersections
print("\nStep 1: Loading ESRI file to identify incomplete intersections...")
esri_df = pd.read_excel(ESRI_FILE, dtype=str)
print(f"  Loaded {len(esri_df):,} records")

# Find incomplete intersections
incomplete_mask = esri_df['FullAddress2'].astype(str).str.contains(' & ,', case=False, na=False)
incomplete_addresses = esri_df[incomplete_mask].copy()
print(f"  Found {len(incomplete_addresses):,} records with incomplete intersections")

# Step 2: Check which ones are already in address_corrections.csv
print("\nStep 2: Checking address_corrections.csv...")
if ADDRESS_CSV.exists():
    addr_corrections = pd.read_csv(ADDRESS_CSV, dtype=str).fillna('')
    print(f"  Loaded {len(addr_corrections):,} existing corrections")
    
    # Get ReportNumberNew that already have corrections
    corrected_report_nums = set(addr_corrections[
        addr_corrections['Corrected_Value'].astype(str).str.strip() != ''
    ]['ReportNumberNew'].astype(str).str.strip())
    print(f"  Found {len(corrected_report_nums):,} ReportNumberNew with existing corrections")
else:
    addr_corrections = pd.DataFrame(columns=[
        'ReportNumberNew', 'TimeOfCall', 'FullAddress2', 'Incident', 
        'Corrected_Value', 'Issue_Type', 'Notes'
    ])
    corrected_report_nums = set()
    print("  Creating new address_corrections.csv")

# Step 3: Identify incomplete intersections that need default center-point intersections
print("\nStep 3: Identifying records needing default center-point intersections...")
needs_default = incomplete_addresses[
    ~incomplete_addresses['ReportNumberNew'].astype(str).str.strip().isin(corrected_report_nums)
].copy()

print(f"  Found {len(needs_default):,} records needing default center-point intersections")

# Step 4: Apply defaults
print("\nStep 4: Applying default center-point intersections...")
new_corrections = []

for idx, row in needs_default.iterrows():
    addr = str(row['FullAddress2']).strip()
    
    # Check if we have a default for this address pattern
    default_correction = None
    for pattern, default_addr in LONG_STREET_DEFAULTS.items():
        if pattern in addr:
            default_correction = default_addr
            break
    
    # If no specific default, use generic pattern
    if not default_correction:
        # Extract street name before " & ,"
        import re
        match = re.match(r'^(.+?)\s*&\s*,', addr)
        if match:
            street_name = match.group(1).strip()
            default_correction = f"{street_name} & Main Street, Hackensack, NJ, 07601"
        else:
            continue  # Skip if we can't parse
    
    new_corrections.append({
        'ReportNumberNew': str(row['ReportNumberNew']).strip(),
        'TimeOfCall': str(row.get('TimeOfCall', '')),
        'FullAddress2': addr,
        'Incident': str(row.get('Incident', '')),
        'Corrected_Value': default_correction,
        'Issue_Type': 'Default Center-Point Intersection',
        'Notes': f'Applied default center-point intersection for long street: {addr[:50]}'
    })

print(f"  Created {len(new_corrections):,} new corrections")

# Step 5: Add to address_corrections.csv
if new_corrections:
    new_df = pd.DataFrame(new_corrections)
    
    # Remove duplicates (in case some already exist)
    if not addr_corrections.empty:
        existing_report_nums = set(addr_corrections['ReportNumberNew'].astype(str).str.strip())
        new_df = new_df[~new_df['ReportNumberNew'].astype(str).str.strip().isin(existing_report_nums)]
        print(f"  After removing duplicates: {len(new_df):,} new corrections to add")
    
    # Combine
    addr_corrections = pd.concat([addr_corrections, new_df], ignore_index=True)
    
    # Save
    print("\nStep 5: Saving updated address_corrections.csv...")
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
print(f"New default center-point intersections added: {len(new_corrections):,}")

# Show breakdown by street
if new_corrections:
    street_counts = {}
    for corr in new_corrections:
        addr = corr['FullAddress2']
        for pattern in LONG_STREET_DEFAULTS.keys():
            if pattern in addr:
                street_counts[pattern] = street_counts.get(pattern, 0) + 1
                break
    
    if street_counts:
        print("\nBreakdown by street pattern:")
        for pattern, count in sorted(street_counts.items(), key=lambda x: -x[1]):
            print(f"  {pattern}: {count:,}")

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
print("\nNext step: Run apply_manual_corrections.py to apply these corrections to the ESRI file")

