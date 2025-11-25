"""
Convert test working files from XLSX to CSV format.

This script converts the identified CAD and RMS Excel files to CSV format
for the /test working directory.
"""

import pandas as pd
import os
from pathlib import Path

def convert_to_csv(source_path, dest_path, description):
    """Convert Excel file to CSV."""
    print(f"\n{'='*60}")
    print(f"Converting: {description}")
    print(f"Source: {source_path}")
    print(f"Destination: {dest_path}")
    print(f"{'='*60}")

    if not os.path.exists(source_path):
        print(f"ERROR: Source file not found: {source_path}")
        return False

    try:
        # Read Excel file
        print("Reading Excel file...")
        df = pd.read_excel(source_path, engine='openpyxl')

        print(f"  Records loaded: {len(df):,}")
        print(f"  Columns: {len(df.columns)}")

        # Write to CSV
        print("Writing CSV file...")
        df.to_csv(dest_path, index=False, encoding='utf-8')

        # Verify output
        file_size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        print(f"  CSV created: {file_size_mb:.2f} MB")
        print(f"[OK] SUCCESS: {description}")
        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def main():
    """Convert all test files."""

    # Ensure test directory exists
    test_dir = Path("test")
    test_dir.mkdir(exist_ok=True)

    # Define conversions
    conversions = [
        {
            "source": "ref/2019_2025_11_17_Updated_CAD_Export.xlsx",
            "dest": "test/2025_11_17_CAD_Cleanup_PreManual.csv",
            "description": "Pre-manual CAD cleanup file (needs manual fixes for Incident, How Reported, FullAddress2)"
        },
        {
            "source": "Merged_Output_optimized.xlsx",
            "dest": "test/2025_11_17_CAD_With_RMS.csv",
            "description": "CAD with RMS incident backfill"
        },
        {
            "source": "data/rms/2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx",
            "dest": "test/2025_11_16_RMS_Export.csv",
            "description": "Full RMS export"
        }
    ]

    # Track results
    results = []

    print("\n" + "="*60)
    print("CAD/RMS Test File Conversion Utility")
    print("="*60)
    print("\nThis will convert 3 Excel files to CSV format for /test working directory")
    print("\nWARNING: These files contain 700K+ rows and may take several minutes to process.")
    print("="*60)

    # Process each conversion
    for i, conversion in enumerate(conversions, 1):
        print(f"\n\n[{i}/3] Processing conversion {i} of 3...")
        success = convert_to_csv(
            conversion["source"],
            conversion["dest"],
            conversion["description"]
        )
        results.append({
            "description": conversion["description"],
            "success": success
        })

    # Summary
    print("\n\n" + "="*60)
    print("CONVERSION SUMMARY")
    print("="*60)

    for i, result in enumerate(results, 1):
        status = "[OK] SUCCESS" if result["success"] else "[ERROR] FAILED"
        print(f"{i}. {status}: {result['description']}")

    success_count = sum(1 for r in results if r["success"])
    print(f"\n{success_count}/3 conversions completed successfully")

    if success_count == 3:
        print("\n[OK] All test files are ready in /test directory")
    else:
        print("\n[WARNING] Some conversions failed - please review errors above")

if __name__ == "__main__":
    main()
