#!/usr/bin/env python
"""
Convert large Excel file to CSV for faster loading.
This is a one-time conversion utility to speed up pipeline runs.

Usage:
    python scripts/convert_excel_to_csv.py --input "data/01_raw/19_to_25_12_18_CAD_Data.xlsx"
"""

import pandas as pd
import argparse
from pathlib import Path
import sys
from datetime import datetime

def convert_excel_to_csv(input_file: Path, output_file: Path = None, chunk_size: int = 100000):
    """
    Convert Excel file to CSV, optionally in chunks for very large files.
    
    Args:
        input_file: Path to input Excel file
        output_file: Path to output CSV file (default: same name with .csv extension)
        chunk_size: Number of rows to process at a time (for memory efficiency)
    """
    input_file = Path(input_file)
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return 1
    
    if output_file is None:
        output_file = input_file.with_suffix('.csv')
    else:
        output_file = Path(output_file)
    
    print(f"Converting {input_file.name} to CSV...")
    print(f"Output: {output_file}")
    print("This may take a few minutes for large files...")
    
    start_time = datetime.now()
    
    try:
        # Read Excel file
        print("Reading Excel file...")
        df = pd.read_excel(input_file, engine='openpyxl', sheet_name=0)
        
        total_rows = len(df)
        print(f"Loaded {total_rows:,} rows with {len(df.columns)} columns")
        
        # Write to CSV
        print(f"Writing to CSV...")
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        elapsed = (datetime.now() - start_time).total_seconds()
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        
        print(f"\n[SUCCESS] Conversion complete!")
        print(f"  Time: {elapsed:.1f} seconds")
        print(f"  Output file size: {file_size_mb:.1f} MB")
        print(f"  Output: {output_file}")
        print(f"\nYou can now use the CSV file for faster pipeline runs:")
        print(f"  python scripts\\master_pipeline.py --input \"{output_file}\" --format excel")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Convert Excel file to CSV for faster loading'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input Excel file path'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output CSV file path (default: same name with .csv extension)'
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None
    
    return convert_excel_to_csv(input_path, output_path)


if __name__ == "__main__":
    sys.exit(main())

