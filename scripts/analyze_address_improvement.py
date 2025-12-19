"""
Analyze the actual address improvement from corrections.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
V2_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
CORRECTED_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected.xlsx"

print("="*80)
print("ANALYZING ADDRESS IMPROVEMENT")
print("="*80)

# Load files
print("\nLoading files...")
v2_df = pd.read_excel(V2_FILE, dtype=str).fillna('')
print(f"  v2 file: {len(v2_df):,} records")

if CORRECTED_FILE.exists():
    corrected_df = pd.read_excel(CORRECTED_FILE, dtype=str).fillna('')
    print(f"  corrected file: {len(corrected_df):,} records")
    
    # Check for duplicates
    v2_unique = v2_df['ReportNumberNew'].nunique()
    corr_unique = corrected_df['ReportNumberNew'].nunique()
    print(f"\n  v2 unique ReportNumberNew: {v2_unique:,}")
    print(f"  corrected unique ReportNumberNew: {corr_unique:,}")
    print(f"  v2 duplicates: {len(v2_df) - v2_unique:,}")
    print(f"  corrected duplicates: {len(corrected_df) - corr_unique:,}")
    
    if len(corrected_df) > len(v2_df) * 1.1:
        print("\n[WARNING] Corrected file has significantly more records than v2!")
        print("This suggests duplicates were created. Using v2 for comparison.")
        use_corrected = False
    else:
        use_corrected = True
else:
    print("  corrected file: NOT FOUND")
    use_corrected = False

# Analyze address quality
def analyze_addresses(df, label):
    print(f"\n{label}:")
    total = len(df)
    
    null_addr = df['FullAddress2'].isna().sum()
    empty_addr = (df['FullAddress2'].astype(str).str.strip() == '').sum()
    incomplete_intersections = df['FullAddress2'].astype(str).str.contains(' & ,', case=False, na=False).sum()
    generic_locations = df['FullAddress2'].astype(str).str.contains(
        r'\b(home|unknown|various|parking garage|area|location|scene)\b', 
        case=False, na=False, regex=True
    ).sum()
    
    invalid = null_addr + empty_addr + incomplete_intersections + generic_locations
    valid = total - invalid
    
    print(f"  Total records: {total:,}")
    print(f"  Null addresses: {null_addr:,}")
    print(f"  Empty addresses: {empty_addr:,}")
    print(f"  Incomplete intersections: {incomplete_intersections:,}")
    print(f"  Generic locations: {generic_locations:,}")
    print(f"  Total invalid: {invalid:,} ({invalid/total*100:.1f}%)")
    print(f"  Valid addresses: {valid:,} ({valid/total*100:.1f}%)")
    
    return invalid, valid

# Analyze v2
v2_invalid, v2_valid = analyze_addresses(v2_df, "V2 FILE (BEFORE CORRECTIONS)")

# Analyze corrected if available
if use_corrected:
    corr_invalid, corr_valid = analyze_addresses(corrected_df, "CORRECTED FILE (AFTER CORRECTIONS)")
    
    # Calculate improvement
    print("\n" + "="*80)
    print("IMPROVEMENT ANALYSIS")
    print("="*80)
    
    invalid_reduction = v2_invalid - corr_invalid
    invalid_reduction_pct = (invalid_reduction / v2_invalid * 100) if v2_invalid > 0 else 0
    
    valid_increase = corr_valid - v2_valid
    valid_increase_pct = (valid_increase / v2_valid * 100) if v2_valid > 0 else 0
    
    print(f"\nInvalid Address Reduction:")
    print(f"  Before: {v2_invalid:,}")
    print(f"  After: {corr_invalid:,}")
    print(f"  Reduction: {invalid_reduction:,} ({invalid_reduction_pct:.1f}%)")
    
    print(f"\nValid Address Increase:")
    print(f"  Before: {v2_valid:,}")
    print(f"  After: {corr_valid:,}")
    print(f"  Increase: {valid_increase:,} ({valid_increase_pct:.1f}%)")
    
    # Check specific corrections
    print("\n" + "="*80)
    print("CHECKING SPECIFIC CORRECTIONS")
    print("="*80)
    
    # Load address corrections
    addr_corr = pd.read_csv(BASE_DIR / "manual_corrections" / "address_corrections.csv", dtype=str).fillna('')
    applied_corrections = addr_corr[addr_corr['Corrected_Value'].astype(str).str.strip() != '']
    print(f"\nTotal corrections in CSV: {len(applied_corrections):,}")
    
    # Sample some corrections
    sample_cases = applied_corrections['ReportNumberNew'].head(10).tolist()
    matches = 0
    for case in sample_cases:
        v2_rows = v2_df[v2_df['ReportNumberNew'].astype(str).str.strip() == str(case).strip()]
        corr_rows = corrected_df[corrected_df['ReportNumberNew'].astype(str).str.strip() == str(case).strip()]
        corr_val = applied_corrections[applied_corrections['ReportNumberNew'].astype(str).str.strip() == str(case).strip()]
        
        if not v2_rows.empty and not corr_rows.empty and not corr_val.empty:
            v2_addr = str(v2_rows['FullAddress2'].iloc[0]).strip()
            corr_addr = str(corr_rows['FullAddress2'].iloc[0]).strip()
            expected = str(corr_val['Corrected_Value'].iloc[0]).strip()
            
            if corr_addr == expected:
                matches += 1
    
    print(f"Sample corrections verified: {matches}/10 match expected values")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)

