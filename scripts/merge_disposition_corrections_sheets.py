"""
Merge two sheets from disposition_corrections Excel file into a single CSV.

This script:
1. Reads both sheets from the Excel file
2. Combines them into a single DataFrame
3. Removes duplicates (if any)
4. Saves as a single CSV file
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
CORRECTIONS_DIR = BASE_DIR / "manual_corrections"

# Try to find the Excel file
excel_files = list(CORRECTIONS_DIR.glob("*disposition*.xlsx"))
csv_file = CORRECTIONS_DIR / "disposition_corrections.csv"

# Also check Downloads folder in case user saved it there
downloads_dir = Path.home() / "Downloads"
downloads_excel = list(downloads_dir.glob("*disposition*.xlsx"))

if not excel_files and not downloads_excel:
    print("="*80)
    print("ERROR: No Excel file found with 'disposition' in the name")
    print(f"Looking in: {CORRECTIONS_DIR}")
    print(f"Also checked: {downloads_dir}")
    print("\nPlease either:")
    print("  1. Save your Excel file as 'disposition_corrections.xlsx' in the manual_corrections folder, OR")
    print("  2. Provide the full path to your Excel file")
    print("\nAlternatively, you can merge manually in Excel:")
    print("  - Copy all data from 'remaining_records' sheet")
    print("  - Paste into the first sheet below existing data")
    print("  - Use Data → Remove Duplicates (on ReportNumberNew column)")
    print("  - Save as CSV")
    exit(1)

excel_file = excel_files[0] if excel_files else downloads_excel[0]

print("="*80)
print("MERGING DISPOSITION CORRECTIONS SHEETS")
print("="*80)
print(f"\nInput file: {excel_file.name}")
print(f"Output file: {csv_file.name}\n")

# Read both sheets
print("Reading sheets...")
try:
    # Read first sheet (usually Sheet1 or the first sheet)
    df1 = pd.read_excel(excel_file, sheet_name=0)
    print(f"  Sheet 1: {len(df1):,} records")
    print(f"    Columns: {list(df1.columns)}")
    
    # Read second sheet (remaining_records)
    df2 = pd.read_excel(excel_file, sheet_name=1)
    print(f"  Sheet 2: {len(df2):,} records")
    print(f"    Columns: {list(df2.columns)}")
except Exception as e:
    print(f"ERROR reading sheets: {e}")
    print("\nTrying to list all available sheets...")
    xl_file = pd.ExcelFile(excel_file)
    print(f"Available sheets: {xl_file.sheet_names}")
    exit(1)

# Check if columns match
if list(df1.columns) != list(df2.columns):
    print("\n[WARNING] Column names don't match between sheets!")
    print(f"Sheet 1 columns: {list(df1.columns)}")
    print(f"Sheet 2 columns: {list(df2.columns)}")
    print("\nAttempting to align columns...")
    
    # Try to align by common columns
    common_cols = set(df1.columns) & set(df2.columns)
    if common_cols:
        print(f"Common columns found: {list(common_cols)}")
        df1 = df1[list(common_cols)]
        df2 = df2[list(common_cols)]
    else:
        print("ERROR: No common columns found!")
        exit(1)

# Combine the DataFrames
print("\nCombining sheets...")
combined_df = pd.concat([df1, df2], ignore_index=True)
print(f"  Combined total: {len(combined_df):,} records")

# Check for duplicates based on ReportNumberNew
print("\nChecking for duplicates...")
initial_count = len(combined_df)
duplicates = combined_df.duplicated(subset=['ReportNumberNew'], keep='first')
duplicate_count = duplicates.sum()

if duplicate_count > 0:
    print(f"  Found {duplicate_count:,} duplicate ReportNumberNew values")
    print("\n  Sample duplicates:")
    dup_rows = combined_df[duplicates][['ReportNumberNew', 'Corrected_Value']].head(10)
    print(dup_rows.to_string(index=False))
    
    # Remove duplicates, keeping first occurrence
    combined_df = combined_df.drop_duplicates(subset=['ReportNumberNew'], keep='first')
    print(f"\n  Removed duplicates: {initial_count - len(combined_df):,} records")
    print(f"  Final count: {len(combined_df):,} records")
else:
    print("  No duplicates found - all ReportNumberNew values are unique")

# Check for records with Corrected_Value
print("\nFinal Statistics:")
print(f"  Total records: {len(combined_df):,}")
print(f"  Records with Corrected_Value: {(combined_df['Corrected_Value'].notna() & (combined_df['Corrected_Value'] != '')).sum():,}")
print(f"  Records still empty: {(combined_df['Corrected_Value'].isna() | (combined_df['Corrected_Value'] == '')).sum():,}")

# Save to CSV
print(f"\nSaving merged file...")
combined_df.to_csv(csv_file, index=False)
print(f"  Saved: {csv_file}")

print("\n" + "="*80)
print("[SUCCESS] Sheets merged successfully!")
print("="*80)
print(f"\nThe merged CSV file is ready to use.")
print(f"You can now delete or archive the Excel file if desired.")

