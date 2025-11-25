"""
Regenerate address_corrections.csv with representative sample from all years (2019-2025).

The original script only took the first 1000 records, which were all from 2019.
This script creates a stratified sample across all years.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
OUTPUT_CSV = BASE_DIR / "manual_corrections" / "address_corrections.csv"

print("="*80)
print("REGENERATING ADDRESS CORRECTIONS FILE")
print("="*80)
print("\nThis will create a representative sample from all years (2019-2025)\n")

# Load ESRI file
print("Loading ESRI file...")
df = pd.read_excel(ESRI_FILE, dtype=str)
print(f"  Loaded {len(df):,} records")

# Extract year from ReportNumberNew
df['Year'] = df['ReportNumberNew'].astype(str).str[:2]

# Find address issues
print("\nIdentifying address issues...")
address_issues = df[
    (df['FullAddress2'].notna()) & 
    (
        (~df['FullAddress2'].str.contains(r'\b(STREET|AVENUE|ROAD|DRIVE|COURT|LANE|PLACE|BOULEVARD|WAY|CIRCLE)\b', case=False, na=False)) |
        (df['FullAddress2'].str.contains(r'^(home|unknown|various|rear lot|parking garage)', case=False, na=False))
    )
].copy()

print(f"  Total address issues found: {len(address_issues):,}")

# Show distribution by year
print(f"\nAddress issues by year:")
year_counts = address_issues['Year'].value_counts().sort_index()
for year, count in year_counts.items():
    print(f"  {year}: {count:,} issues")

# Create stratified sample - take proportional samples from each year
# Target: 1000 records total, distributed proportionally
target_total = 1000
samples_by_year = {}

for year in sorted(address_issues['Year'].unique()):
    year_data = address_issues[address_issues['Year'] == year]
    year_total = len(year_data)
    year_proportion = year_total / len(address_issues)
    year_sample_size = max(1, int(target_total * year_proportion))
    
    # Take sample from this year
    if year_sample_size >= year_total:
        samples_by_year[year] = year_data
    else:
        samples_by_year[year] = year_data.sample(n=year_sample_size, random_state=42)

# Combine all samples
addr_corrections = pd.concat(samples_by_year.values(), ignore_index=True)

# If we have fewer than target_total, add more from years with most issues
if len(addr_corrections) < target_total:
    remaining = target_total - len(addr_corrections)
    # Get years sorted by issue count
    year_order = address_issues['Year'].value_counts().index.tolist()
    
    for year in year_order:
        if remaining <= 0:
            break
        year_data = address_issues[address_issues['Year'] == year]
        already_included = addr_corrections[addr_corrections['Year'] == year]
        available = year_data[~year_data.index.isin(already_included.index)]
        
        if len(available) > 0:
            add_count = min(remaining, len(available))
            additional = available.sample(n=add_count, random_state=42)
            addr_corrections = pd.concat([addr_corrections, additional], ignore_index=True)
            remaining -= add_count

# Prepare output
addr_corrections = addr_corrections[['ReportNumberNew', 'TimeOfCall', 'FullAddress2', 'Incident']].copy()
addr_corrections['Corrected_Value'] = ''
addr_corrections['Issue_Type'] = ''
addr_corrections['Notes'] = ''

# Remove Year column if it exists
if 'Year' in addr_corrections.columns:
    addr_corrections = addr_corrections.drop(columns=['Year'])

# Save
print(f"\nSaving address corrections file...")
addr_corrections.to_csv(OUTPUT_CSV, index=False)

print(f"\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total records in file: {len(addr_corrections):,}")
print(f"\nDistribution by year:")
final_year_counts = pd.Series([str(r)[:2] for r in addr_corrections['ReportNumberNew']]).value_counts().sort_index()
for year, count in final_year_counts.items():
    print(f"  {year}: {count:,} records")

print(f"\nSaved: {OUTPUT_CSV}")

