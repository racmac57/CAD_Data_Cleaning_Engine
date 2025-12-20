"""Fix duplicate records in existing geocoded file.

The geocoding merge operation can create duplicate rows if results_df has duplicate addresses.
This script removes duplicates from the geocoded file, keeping the first occurrence.
"""
import pandas as pd
from pathlib import Path
import sys

def fix_geocoded_duplicates(input_path: str, output_path: str = None):
    """Remove duplicate records from geocoded file based on ReportNumberNew.
    
    Args:
        input_path: Path to the geocoded Excel file with duplicates
        output_path: Optional output path. If None, creates a new file with '_deduplicated' suffix.
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        print(f"❌ Error: File not found: {input_path}")
        return None
    
    if output_path is None:
        output_path = input_file.parent / f"{input_file.stem}_deduplicated{input_file.suffix}"
    else:
        output_path = Path(output_path)
    
    print(f"Loading geocoded file: {input_path}")
    print(f"File size: {input_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    df = pd.read_excel(input_path)
    original_count = len(df)
    print(f"\nOriginal record count: {original_count:,}")
    
    # Check for duplicates
    duplicates = df.duplicated(subset=['ReportNumberNew'], keep=False)
    duplicate_count = duplicates.sum()
    
    if duplicate_count == 0:
        print("✅ No duplicates found! File is already clean.")
        return df
    
    print(f"Found {duplicate_count:,} rows with duplicate ReportNumberNew values")
    
    # Show some examples
    dup_rn_counts = df[duplicates]['ReportNumberNew'].value_counts().head(5)
    print(f"\nTop 5 most duplicated ReportNumberNew values:")
    for rn, count in dup_rn_counts.items():
        print(f"  {rn}: {count} occurrences")
    
    # Remove duplicates, keeping first occurrence
    print(f"\nRemoving duplicates (keeping first occurrence)...")
    df_fixed = df.drop_duplicates(subset=['ReportNumberNew'], keep='first')
    
    fixed_count = len(df_fixed)
    removed = original_count - fixed_count
    
    print(f"Fixed record count: {fixed_count:,}")
    print(f"Removed duplicates: {removed:,} ({removed/original_count*100:.2f}%)")
    
    # Verify no duplicates remain
    remaining_dupes = df_fixed.duplicated(subset=['ReportNumberNew'], keep=False).sum()
    if remaining_dupes > 0:
        print(f"⚠️  Warning: {remaining_dupes} duplicates still remain!")
    else:
        print("✅ All duplicates removed successfully!")
    
    # Save fixed file
    print(f"\nSaving fixed file to: {output_path}")
    df_fixed.to_excel(output_path, index=False)
    
    output_size = output_path.stat().st_size / 1024 / 1024
    print(f"✅ Fixed file saved! Size: {output_size:.2f} MB")
    
    return df_fixed

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python fix_existing_geocoded_file.py <geocoded_file> [output_file]")
        print("\nExample:")
        print("  python fix_existing_geocoded_file.py data/ESRI_CADExport/CAD_ESRI_POLISHED_20251219_131114_geocoded.xlsx")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    fix_geocoded_duplicates(input_file, output_file)

