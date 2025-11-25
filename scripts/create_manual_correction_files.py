#!/usr/bin/env python3
"""
Create manual correction CSV files for data quality issues.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
OUTPUT_DIR = BASE_DIR / "manual_corrections"

# Valid How Reported values
VALID_HOW_REPORTED = [
    '9-1-1', 'Walk-In', 'Phone', 'Self-Initiated', 'Radio', 
    'Teletype', 'Fax', 'Other - See Notes', 'eMail', 'Mail', 
    'Virtual Patrol', 'Canceled Call'
]

OUTPUT_DIR.mkdir(exist_ok=True)

print("Loading ESRI export file...")
df = pd.read_excel(ESRI_FILE)
print(f"Loaded {len(df):,} records")

# 1. How Reported Corrections
print("\nCreating How Reported corrections file...")
invalid_how = df[
    ~df['How Reported'].isin(VALID_HOW_REPORTED) & 
    df['How Reported'].notna()
].copy()
null_how = df[df['How Reported'].isna()].copy()

how_corrections = pd.DataFrame()
if len(invalid_how) > 0:
    how_corrections = invalid_how[['ReportNumberNew', 'TimeOfCall', 'How Reported', 'Incident']].copy()
    how_corrections['Corrected_Value'] = ''
    how_corrections['Notes'] = ''
    how_corrections['Issue_Type'] = 'Invalid Value'

if len(null_how) > 0:
    null_corrections = null_how[['ReportNumberNew', 'TimeOfCall', 'How Reported', 'Incident']].copy()
    null_corrections['Corrected_Value'] = ''
    null_corrections['Notes'] = ''
    null_corrections['Issue_Type'] = 'Null Value'
    
    if len(how_corrections) > 0:
        how_corrections = pd.concat([how_corrections, null_corrections], ignore_index=True)
    else:
        how_corrections = null_corrections

# Limit to first 2000 records for manual editing
how_corrections = how_corrections.head(2000)
how_corrections.to_csv(OUTPUT_DIR / "how_reported_corrections.csv", index=False)
print(f"  Created: {len(how_corrections):,} records (total issues: {len(invalid_how) + len(null_how):,})")

# 2. Disposition Corrections
print("\nCreating Disposition corrections file...")
null_disp = df[df['Disposition'].isna()].copy()
disp_corrections = null_disp[['ReportNumberNew', 'TimeOfCall', 'Incident', 'How Reported', 'Disposition']].copy()
disp_corrections['Corrected_Value'] = ''
disp_corrections['Notes'] = ''
# Limit to first 2000 records
disp_corrections = disp_corrections.head(2000)
disp_corrections.to_csv(OUTPUT_DIR / "disposition_corrections.csv", index=False)
print(f"  Created: {len(disp_corrections):,} sample records (total nulls: {len(null_disp):,})")

# 3. Case Number Corrections (from validation report)
print("\nCreating Case Number corrections file...")
case_corrections = pd.read_csv(BASE_DIR / "data" / "02_reports" / "invalid_case_numbers_20251124_000244.csv")
case_corrections['Corrected_Value'] = ''
case_corrections['Notes'] = ''
case_corrections.to_csv(OUTPUT_DIR / "case_number_corrections.csv", index=False)
print(f"  Created: {len(case_corrections):,} records")

# 4. Address Corrections (sample)
print("\nCreating Address corrections file (sample)...")
# Get addresses with issues (no street type, no number, generic text)
address_issues = df[
    (df['FullAddress2'].notna()) & 
    (
        (~df['FullAddress2'].str.contains(r'\b(STREET|AVENUE|ROAD|DRIVE|COURT|LANE|PLACE|BOULEVARD|WAY|CIRCLE)\b', case=False, na=False)) |
        (df['FullAddress2'].str.contains(r'^(home|unknown|various|rear lot|parking garage)', case=False, na=False))
    )
].head(1000).copy()

addr_corrections = address_issues[['ReportNumberNew', 'TimeOfCall', 'FullAddress2', 'Incident']].copy()
addr_corrections['Corrected_Value'] = ''
addr_corrections['Issue_Type'] = ''
addr_corrections['Notes'] = ''
addr_corrections.to_csv(OUTPUT_DIR / "address_corrections.csv", index=False)
print(f"  Created: {len(addr_corrections):,} sample records")

# 5. Hour Field Corrections (sample showing the issue)
print("\nCreating Hour field corrections reference file...")
hour_issues = df[df['Hour'].notna()].copy()
hour_issues = hour_issues[hour_issues['Hour'].astype(str).str.contains(':', na=False)].head(100).copy()
hour_corrections = hour_issues[['ReportNumberNew', 'TimeOfCall', 'Hour', 'cYear', 'cMonth']].copy()
hour_corrections['Corrected_Value'] = ''
hour_corrections['Notes'] = 'Round to HH:00 format (e.g., 00:04 -> 00:00, 14:35 -> 14:00)'
hour_corrections.to_csv(OUTPUT_DIR / "hour_field_corrections.csv", index=False)
print(f"  Created: {len(hour_corrections):,} sample records showing format issue")

# 6. Master Corrections Template
print("\nCreating Master Corrections Template...")
master_template = pd.DataFrame(columns=[
    'ReportNumberNew', 'TimeOfCall', 'Field_Name', 'Current_Value', 
    'Corrected_Value', 'Issue_Type', 'Notes', 'Status'
])
master_template.to_csv(OUTPUT_DIR / "master_corrections_template.csv", index=False)
print("  Created: Master template for any additional corrections")

print("\n" + "="*60)
print("All correction files created in: manual_corrections/")
print("="*60)
print("\nFiles created:")
print("  1. how_reported_corrections.csv")
print("  2. disposition_corrections.csv")
print("  3. case_number_corrections.csv")
print("  4. address_corrections.csv")
print("  5. hour_field_corrections.csv")
print("  6. master_corrections_template.csv")
print("\nNext steps:")
print("  1. Open each CSV file in Excel")
print("  2. Fill in the 'Corrected_Value' column")
print("  3. Add notes if needed")
print("  4. Save the files")
print("  5. Run apply_corrections.py to apply changes")

