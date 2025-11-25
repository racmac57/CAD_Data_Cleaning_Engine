"""
Identify records in address_corrections.csv that still need manual correction.

This script:
1. Finds records with empty Corrected_Value
2. Categorizes them by issue type
3. Generates a report and filtered CSV for manual review
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ADDRESS_CSV = BASE_DIR / "manual_corrections" / "address_corrections.csv"
OUTPUT_CSV = BASE_DIR / "manual_corrections" / "address_corrections_manual_review.csv"
REPORT_FILE = BASE_DIR / "data" / "02_reports" / "address_manual_corrections_needed.md"

print("="*80)
print("IDENTIFYING RECORDS NEEDING MANUAL CORRECTION")
print("="*80)
print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Step 1: Load address corrections
print("Step 1: Loading address corrections...")
try:
    addr_corrections = pd.read_csv(ADDRESS_CSV, dtype=str).fillna('')
    print(f"  Loaded {len(addr_corrections):,} total records")
except Exception as e:
    print(f"  ERROR: Could not load file: {e}")
    exit(1)

# Step 2: Identify records needing manual correction
print("\nStep 2: Identifying records needing manual correction...")
needs_manual = addr_corrections[
    addr_corrections['Corrected_Value'].astype(str).str.strip() == ''
].copy()

print(f"  Found {len(needs_manual):,} records needing manual correction")
print(f"  Records with corrections: {len(addr_corrections) - len(needs_manual):,}")

# Step 3: Categorize by issue type
print("\nStep 3: Categorizing by issue type...")

def categorize_issue(address):
    """Categorize the type of address issue."""
    if pd.isna(address) or str(address).strip() == "":
        return "blank"
    
    addr = str(address).strip().upper()
    
    # Incomplete intersection
    if " & ," in addr or " &," in addr:
        return "incomplete_intersection"
    
    # Generic location
    generic_terms = ["HOME", "VARIOUS", "UNKNOWN", "PARKING GARAGE", "REAR LOT", 
                     "PARKING LOT", "LOT", "GARAGE", "AREA", "LOCATION", "SCENE"]
    for term in generic_terms:
        if term in addr:
            return "generic_location"
    
    # Missing street number (starts with street name, not number)
    import re
    if not re.match(r'^\d+', address):
        return "missing_street_number"
    
    # Missing street type
    street_types = ["STREET", "ST", "AVENUE", "AVE", "ROAD", "RD", "DRIVE", "DR", 
                    "LANE", "LN", "BOULEVARD", "BLVD", "COURT", "CT", "PLACE", "PL"]
    has_type = any(st in addr for st in street_types)
    if not has_type:
        return "missing_street_type"
    
    return "other"

needs_manual['Issue_Category'] = needs_manual['FullAddress2'].apply(categorize_issue)

# Show breakdown
print("\n  Breakdown by issue category:")
category_counts = needs_manual['Issue_Category'].value_counts()
for category, count in category_counts.items():
    print(f"    {category}: {count:,}")

# Step 4: Group by address pattern to identify common issues
print("\nStep 4: Identifying most common address patterns needing correction...")
pattern_counts = needs_manual.groupby('FullAddress2').size().sort_values(ascending=False)
print(f"\n  Top 20 most common incomplete addresses:")
for addr, count in pattern_counts.head(20).items():
    print(f"    {count:4,}x: {addr[:70]}")

# Step 5: Group by incident type
print("\nStep 5: Breakdown by incident type...")
if 'Incident' in needs_manual.columns:
    incident_counts = needs_manual['Incident'].value_counts()
    print(f"\n  Top 15 incident types needing correction:")
    for incident, count in incident_counts.head(15).items():
        print(f"    {count:4,}x: {incident}")

# Step 6: Create filtered CSV for manual review
print("\nStep 6: Creating filtered CSV for manual review...")
# Sort by issue category and then by address pattern (most common first)
needs_manual_sorted = needs_manual.copy()
needs_manual_sorted['Pattern_Count'] = needs_manual_sorted['FullAddress2'].map(pattern_counts)
needs_manual_sorted = needs_manual_sorted.sort_values(
    by=['Issue_Category', 'Pattern_Count', 'FullAddress2'],
    ascending=[True, False, True]
)

# Select columns for manual review
review_columns = ['ReportNumberNew', 'TimeOfCall', 'FullAddress2', 'Incident', 
                  'Issue_Category', 'Corrected_Value', 'Issue_Type', 'Notes']
review_columns = [col for col in review_columns if col in needs_manual_sorted.columns]

needs_manual_sorted[review_columns].to_csv(OUTPUT_CSV, index=False)
print(f"  Saved: {OUTPUT_CSV}")

# Step 7: Generate markdown report
print("\nStep 7: Generating markdown report...")
REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    f.write("# Address Corrections - Manual Review Needed\n\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    f.write("## Summary\n\n")
    f.write(f"- **Total records in address_corrections.csv**: {len(addr_corrections):,}\n")
    f.write(f"- **Records with corrections**: {len(addr_corrections) - len(needs_manual):,}\n")
    f.write(f"- **Records needing manual correction**: {len(needs_manual):,}\n")
    f.write(f"- **Completion rate**: {(len(addr_corrections) - len(needs_manual)) / len(addr_corrections) * 100:.1f}%\n\n")
    
    f.write("## Breakdown by Issue Category\n\n")
    f.write("| Category | Count | Percentage |\n")
    f.write("|----------|-------|------------|\n")
    for category, count in category_counts.items():
        pct = (count / len(needs_manual) * 100) if len(needs_manual) > 0 else 0
        f.write(f"| {category} | {count:,} | {pct:.1f}% |\n")
    f.write("\n")
    
    f.write("## Top 20 Most Common Incomplete Addresses\n\n")
    f.write("| Count | Address |\n")
    f.write("|-------|----------|\n")
    for addr, count in pattern_counts.head(20).items():
        f.write(f"| {count:,} | {addr} |\n")
    f.write("\n")
    
    if 'Incident' in needs_manual.columns:
        f.write("## Top 15 Incident Types Needing Correction\n\n")
        f.write("| Count | Incident Type |\n")
        f.write("|-------|---------------|\n")
        for incident, count in incident_counts.head(15).items():
            f.write(f"| {count:,} | {incident} |\n")
        f.write("\n")
    
    f.write("## Next Steps\n\n")
    f.write("1. Open `address_corrections_manual_review.csv` in Excel\n")
    f.write("2. Review records grouped by issue category\n")
    f.write("3. Fill in the `Corrected_Value` column for each record\n")
    f.write("4. Use the official street names file (`hackensack_municipal_streets_from_lawsoft_25_11_24.xlsx`) as reference\n")
    f.write("5. For incomplete intersections, use RMS data or known intersections\n")
    f.write("6. Save the CSV and run `apply_manual_corrections.py` to apply corrections\n\n")
    
    f.write("## Tips for Manual Correction\n\n")
    f.write("- **Incomplete intersections**: Add the missing cross street (e.g., 'Anderson Street & ,' → 'Anderson Street & Prospect Avenue')\n")
    f.write("- **Generic locations**: Replace with specific address if known, or use RMS data\n")
    f.write("- **Missing street numbers**: Add street number if known from RMS or other sources\n")
    f.write("- **Missing street types**: Use the official street names file to find the correct suffix\n\n")

print(f"  Saved: {REPORT_FILE}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total records: {len(addr_corrections):,}")
print(f"Records with corrections: {len(addr_corrections) - len(needs_manual):,}")
print(f"Records needing manual correction: {len(needs_manual):,}")
print(f"Completion rate: {(len(addr_corrections) - len(needs_manual)) / len(addr_corrections) * 100:.1f}%")

print(f"\nOutput files:")
print(f"  1. {OUTPUT_CSV}")
print(f"     - Filtered CSV with records needing manual correction")
print(f"     - Sorted by issue category and frequency")
print(f"     - Ready for manual review in Excel")
print(f"\n  2. {REPORT_FILE}")
print(f"     - Summary report with statistics")
print(f"     - Breakdown by issue category")
print(f"     - Top incomplete addresses")

print("\n" + "="*80)
print("NEXT STEPS")
print("="*80)
print("1. Open 'address_corrections_manual_review.csv' in Excel")
print("2. Review and fill in 'Corrected_Value' column")
print("3. Use the official street names file as reference")
print("4. Save and run 'apply_manual_corrections.py' to apply corrections")

print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

