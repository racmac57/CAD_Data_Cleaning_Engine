"""Analyze the duplicate records issue in geocoded output.

This script helps identify:
1. Where the duplicates came from
2. If they're true duplicates or merge artifacts
3. How to fix the existing geocoded file
"""
import pandas as pd
from pathlib import Path

def analyze_duplicates(polished_path: str, geocoded_path: str):
    """Analyze duplicate records between polished and geocoded files."""
    
    print("Loading files...")
    df_polished = pd.read_excel(polished_path)
    df_geocoded = pd.read_excel(geocoded_path)
    
    print(f"\n{'='*70}")
    print("RECORD COUNT ANALYSIS")
    print(f"{'='*70}")
    print(f"Polished records: {len(df_polished):,}")
    print(f"Geocoded records: {len(df_geocoded):,}")
    print(f"Difference: {len(df_geocoded) - len(df_polished):,} extra records")
    
    # Check for duplicates by ReportNumberNew
    print(f"\n{'='*70}")
    print("DUPLICATE ANALYSIS BY ReportNumberNew")
    print(f"{'='*70}")
    
    polished_unique_rn = df_polished['ReportNumberNew'].nunique()
    geocoded_unique_rn = df_geocoded['ReportNumberNew'].nunique()
    
    print(f"Polished - Unique ReportNumberNew: {polished_unique_rn:,}")
    print(f"Geocoded - Unique ReportNumberNew: {geocoded_unique_rn:,}")
    print(f"Difference: {geocoded_unique_rn - polished_unique_rn:,}")
    
    # Find duplicate ReportNumberNew values
    geocoded_dupes = df_geocoded.duplicated(subset=['ReportNumberNew'], keep=False)
    print(f"\nGeocoded - Rows with duplicate ReportNumberNew: {geocoded_dupes.sum():,}")
    
    if geocoded_dupes.sum() > 0:
        print(f"\nTop 10 most duplicated ReportNumberNew values:")
        dup_counts = df_geocoded[geocoded_dupes]['ReportNumberNew'].value_counts().head(10)
        for rn, count in dup_counts.items():
            print(f"  {rn}: {count} occurrences")
        
        # Show example
        example_rn = dup_counts.index[0]
        example_rows = df_geocoded[df_geocoded['ReportNumberNew'] == example_rn]
        print(f"\nExample: ReportNumberNew = {example_rn}")
        print(example_rows[['ReportNumberNew', 'FullAddress2', 'latitude', 'longitude']].to_string())
    
    # Check if duplicates have different addresses (merge artifact)
    print(f"\n{'='*70}")
    print("ADDRESS ANALYSIS FOR DUPLICATES")
    print(f"{'='*70}")
    
    if geocoded_dupes.sum() > 0:
        dup_rn_list = df_geocoded[geocoded_dupes]['ReportNumberNew'].unique()[:5]
        for rn in dup_rn_list:
            dup_rows = df_geocoded[df_geocoded['ReportNumberNew'] == rn]
            unique_addrs = dup_rows['FullAddress2'].nunique()
            print(f"ReportNumberNew {rn}: {len(dup_rows)} rows, {unique_addrs} unique addresses")
            if unique_addrs > 1:
                print(f"  ⚠️  Different addresses - likely merge artifact!")
                print(f"  Addresses: {dup_rows['FullAddress2'].unique().tolist()}")
    
    # Recommendation
    print(f"\n{'='*70}")
    print("RECOMMENDATION")
    print(f"{'='*70}")
    print("If duplicates exist, they're likely caused by the merge operation")
    print("creating a Cartesian product when results_df had duplicate addresses.")
    print("\nFix: Deduplicate the geocoded file by keeping first occurrence:")
    print("  df_fixed = df_geocoded.drop_duplicates(subset=['ReportNumberNew'], keep='first')")
    
    return df_polished, df_geocoded

def fix_geocoded_file(geocoded_path: str, output_path: str = None):
    """Remove duplicate records from geocoded file."""
    if output_path is None:
        geocoded_file = Path(geocoded_path)
        output_path = geocoded_file.parent / f"{geocoded_file.stem}_deduplicated{geocoded_file.suffix}"
    
    print(f"Loading geocoded file: {geocoded_path}")
    df = pd.read_excel(geocoded_path)
    
    original_count = len(df)
    print(f"Original record count: {original_count:,}")
    
    # Remove duplicates, keeping first occurrence
    df_fixed = df.drop_duplicates(subset=['ReportNumberNew'], keep='first')
    
    fixed_count = len(df_fixed)
    removed = original_count - fixed_count
    
    print(f"Fixed record count: {fixed_count:,}")
    print(f"Removed duplicates: {removed:,}")
    
    # Save fixed file
    df_fixed.to_excel(output_path, index=False)
    print(f"\n✅ Fixed file saved to: {output_path}")
    
    return df_fixed

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python analyze_geocoding_duplicates.py <polished_file> <geocoded_file>")
        print("  OR")
        print("  python analyze_geocoding_duplicates.py --fix <geocoded_file> [output_file]")
        sys.exit(1)
    
    if sys.argv[1] == '--fix':
        # Fix mode
        geocoded_file = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else None
        fix_geocoded_file(geocoded_file, output_file)
    else:
        # Analyze mode
        polished_file = sys.argv[1]
        geocoded_file = sys.argv[2]
        analyze_duplicates(polished_file, geocoded_file)

