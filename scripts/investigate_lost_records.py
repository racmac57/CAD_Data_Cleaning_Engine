#!/usr/bin/env python3
"""Investigate what records were lost during deduplication."""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Files
esri_source = BASE_DIR / "ref" / "2019_2025_11_17_Updated_CAD_Export.xlsx"
esri_deduped = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected_DEDUPED.xlsx"
esri_corrupted = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected.xlsx"

print("=" * 80)
print("INVESTIGATING LOST RECORDS")
print("=" * 80)

# Load files
print("\nLoading files...")
source_df = pd.read_excel(esri_source)
deduped_df = pd.read_excel(esri_deduped)

print(f"Source file: {len(source_df):,} records, {source_df['ReportNumberNew'].nunique():,} unique cases")
print(f"Deduplicated file: {len(deduped_df):,} records, {deduped_df['ReportNumberNew'].nunique():,} unique cases")
print(f"Lost: {len(source_df) - len(deduped_df):,} records")

# Check what the deduplication key was
print("\n" + "=" * 80)
print("UNDERSTANDING DEDUPLICATION LOGIC")
print("=" * 80)

# The deduplication used: ReportNumberNew + Incident + TimeOfCall + FullAddress2
# This is TOO STRICT - CAD data legitimately has:
# - Same case, same incident, same time, same address BUT different units (backup)
# - Same case, different incidents (multiple calls for same case)
# - Same case, same incident, different times (follow-ups)

print("\nCAD data can legitimately have multiple records per case:")
print("  - Multiple units responding (backup, assist)")
print("  - Multiple incidents for same case number")
print("  - Follow-up calls")
print("  - Different dispositions")

# Check if we should only remove IDENTICAL records
print("\n" + "=" * 80)
print("CHECKING FOR TRULY IDENTICAL DUPLICATES")
print("=" * 80)

# Find records that are completely identical (all columns match)
print("\nFinding completely identical records...")
identical_dups = source_df[source_df.duplicated(keep=False)]

if len(identical_dups) > 0:
    print(f"Found {len(identical_dups):,} records that are completely identical")
    
    # Group by all columns to find identical sets
    identical_groups = identical_dups.groupby(list(source_df.columns)).size()
    print(f"Number of unique identical record sets: {len(identical_groups)}")
    
    # Show example
    print("\nExample of identical duplicates:")
    example_case = identical_dups.iloc[0]['ReportNumberNew']
    example_records = source_df[source_df['ReportNumberNew'] == example_case]
    if len(example_records) > 1:
        # Check if they're truly identical
        first = example_records.iloc[0]
        identical_to_first = (example_records == first).all(axis=1)
        if identical_to_first.sum() > 1:
            print(f"Case {example_case} has {identical_to_first.sum()} identical records")
            print(example_records[identical_to_first].head(3))
else:
    print("No completely identical records found")

# Check what the corrupted file had
if esri_corrupted.exists():
    print("\n" + "=" * 80)
    print("CHECKING CORRUPTED FILE")
    print("=" * 80)
    corrupted_df = pd.read_excel(esri_corrupted)
    print(f"Corrupted file: {len(corrupted_df):,} records")
    
    # Check the worst case
    worst_case = corrupted_df.groupby('ReportNumberNew').size().idxmax()
    worst_case_records = corrupted_df[corrupted_df['ReportNumberNew'] == worst_case]
    print(f"\nWorst duplicate case in corrupted file: {worst_case}")
    print(f"  Appears {len(worst_case_records):,} times")
    print(f"  Same case in source: {len(source_df[source_df['ReportNumberNew'] == worst_case]):,} times")
    print(f"  Same case in deduped: {len(deduped_df[deduped_df['ReportNumberNew'] == worst_case]):,} times")

print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print("The deduplication was too aggressive.")
print("We should ONLY remove completely identical records (all columns match).")
print("CAD data legitimately has multiple records per case number.")
print("\nNeed to rebuild the ESRI file from the source, removing only TRUE duplicates.")

