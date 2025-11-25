"""
Merge updates from address_corrections_manual_review.csv back into address_corrections.csv.

This script:
1. Loads the manual review CSV with user updates
2. Merges corrections back into the main address_corrections.csv
3. Ensures all updates are preserved
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
MANUAL_REVIEW_CSV = BASE_DIR / "manual_corrections" / "address_corrections_manual_review.csv"
ADDRESS_CSV = BASE_DIR / "manual_corrections" / "address_corrections.csv"

print("="*80)
print("MERGING MANUAL REVIEW UPDATES")
print("="*80)
print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Step 1: Load manual review CSV
print("Step 1: Loading manual review CSV...")
try:
    manual_review = pd.read_csv(MANUAL_REVIEW_CSV, dtype=str).fillna('')
    print(f"  Loaded {len(manual_review):,} records from manual review")
except Exception as e:
    print(f"  ERROR: Could not load manual review file: {e}")
    exit(1)

# Step 2: Load main address corrections
print("\nStep 2: Loading main address corrections...")
try:
    addr_corrections = pd.read_csv(ADDRESS_CSV, dtype=str).fillna('')
    print(f"  Loaded {len(addr_corrections):,} records from main file")
except Exception as e:
    print(f"  ERROR: Could not load main file: {e}")
    exit(1)

# Step 3: Get records with corrections from manual review
print("\nStep 3: Identifying updates from manual review...")
manual_updates = manual_review[
    manual_review['Corrected_Value'].astype(str).str.strip() != ''
].copy()

print(f"  Found {len(manual_updates):,} records with corrections in manual review")

# Step 4: Update main file with manual review corrections
print("\nStep 4: Merging updates into main file...")
updates_applied = 0

# Create a lookup from ReportNumberNew to corrected value
update_lookup = dict(zip(
    manual_updates['ReportNumberNew'].astype(str).str.strip(),
    manual_updates['Corrected_Value'].astype(str).str.strip()
))

# Update main file
for idx, row in addr_corrections.iterrows():
    report_num = str(row['ReportNumberNew']).strip()
    if report_num in update_lookup:
        new_corrected = update_lookup[report_num]
        old_corrected = str(row.get('Corrected_Value', '')).strip()
        
        if new_corrected != old_corrected:
            addr_corrections.loc[idx, 'Corrected_Value'] = new_corrected
            # Update Issue_Type and Notes if they exist in manual review
            if 'Issue_Type' in manual_updates.columns:
                manual_row = manual_updates[manual_updates['ReportNumberNew'].astype(str).str.strip() == report_num]
                if not manual_row.empty:
                    new_issue_type = str(manual_row.iloc[0].get('Issue_Type', '')).strip()
                    new_notes = str(manual_row.iloc[0].get('Notes', '')).strip()
                    if new_issue_type:
                        addr_corrections.loc[idx, 'Issue_Type'] = new_issue_type
                    if new_notes:
                        addr_corrections.loc[idx, 'Notes'] = new_notes
                    else:
                        addr_corrections.loc[idx, 'Notes'] = 'Updated from manual review'
            else:
                addr_corrections.loc[idx, 'Notes'] = 'Updated from manual review'
            updates_applied += 1

print(f"  Applied {updates_applied:,} updates from manual review")

# Step 5: Save updated file
print("\nStep 5: Saving updated address corrections...")
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
print(f"Total records in main file: {len(addr_corrections):,}")
print(f"Updates applied from manual review: {updates_applied:,}")
print(f"Total corrections with values: {(addr_corrections['Corrected_Value'].astype(str).str.strip() != '').sum():,}")

# Count remaining blank corrections
remaining_blank = (addr_corrections['Corrected_Value'].astype(str).str.strip() == '').sum()
print(f"Records still without corrections: {remaining_blank:,}")

if remaining_blank > 0:
    print("\nRecords still needing correction:")
    blank_records = addr_corrections[addr_corrections['Corrected_Value'].astype(str).str.strip() == '']
    print(blank_records[['ReportNumberNew', 'FullAddress2', 'Incident']].head(10).to_string(index=False))

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

