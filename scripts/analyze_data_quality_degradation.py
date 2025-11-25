#!/usr/bin/env python3
"""Analyze if data quality degraded during ESRI processing."""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).parent.parent

raw_file = BASE_DIR / "data" / "01_raw" / "2025_11_21_2019_2025_11_21_ALL_CAD_Data.xlsx"
esri_file = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected.xlsx"

print("=" * 80)
print("DATA QUALITY COMPARISON: RAW vs ESRI")
print("=" * 80)

# Load files
print("\nLoading files...")
raw_df = pd.read_excel(raw_file)
esri_df = pd.read_excel(esri_file)

print(f"Raw CAD: {len(raw_df):,} records, {raw_df['ReportNumberNew'].nunique():,} unique cases")
print(f"ESRI: {len(esri_df):,} records, {esri_df['ReportNumberNew'].nunique():,} unique cases")

# Check duplicates
raw_dups = raw_df[raw_df.duplicated(subset=['ReportNumberNew'], keep=False)]
esri_dups = esri_df[esri_df.duplicated(subset=['ReportNumberNew'], keep=False)]

print(f"\nDuplicate records:")
print(f"  Raw: {len(raw_dups):,} ({len(raw_dups)/len(raw_df)*100:.1f}%)")
print(f"  ESRI: {len(esri_dups):,} ({len(esri_dups)/len(esri_df)*100:.1f}%)")

# Check duplicate distribution
raw_dup_counts = raw_df.groupby('ReportNumberNew').size()
esri_dup_counts = esri_df.groupby('ReportNumberNew').size()

print(f"\nDuplicate distribution:")
print(f"  Raw - Max duplicates per case: {raw_dup_counts.max()}")
print(f"  Raw - Cases with >10 duplicates: {(raw_dup_counts > 10).sum()}")
print(f"  ESRI - Max duplicates per case: {esri_dup_counts.max()}")
print(f"  ESRI - Cases with >10 duplicates: {(esri_dup_counts > 10).sum()}")

# Check address quality in both
def is_invalid_address(addr):
    if pd.isna(addr) or str(addr).strip() == "":
        return True
    addr = str(addr).strip().upper()
    if " & ," in addr or "CANCELED CALL" in addr or addr in ["HOME", "UNKNOWN", "VARIOUS"]:
        return True
    return False

raw_invalid = raw_df['FullAddress2'].apply(is_invalid_address).sum()
esri_invalid = esri_df['FullAddress2'].apply(is_invalid_address).sum()

print(f"\nAddress Quality:")
print(f"  Raw invalid: {raw_invalid:,} ({raw_invalid/len(raw_df)*100:.1f}%)")
print(f"  ESRI invalid: {esri_invalid:,} ({esri_invalid/len(esri_df)*100:.1f}%)")

# Check if ESRI has legitimate duplicates (same case, different incidents/times)
print(f"\n" + "=" * 80)
print("ANALYZING DUPLICATE PATTERNS")
print("=" * 80)

# Sample a highly duplicated case
worst_case = esri_dup_counts.idxmax()
worst_case_records = esri_df[esri_df['ReportNumberNew'] == worst_case]

print(f"\nWorst duplicate case: {worst_case} ({len(worst_case_records):,} records)")
print(f"\nSample records:")
print(worst_case_records[['ReportNumberNew', 'Incident', 'TimeOfCall', 'FullAddress2', 'Disposition']].head(10))

# Check if they're identical or different
print(f"\nAre these records identical?")
first_record = worst_case_records.iloc[0]
identical_count = 0
for idx, row in worst_case_records.iterrows():
    if row.equals(first_record):
        identical_count += 1

print(f"  Identical to first record: {identical_count:,} / {len(worst_case_records):,}")
print(f"  Unique incidents: {worst_case_records['Incident'].nunique()}")
print(f"  Unique addresses: {worst_case_records['FullAddress2'].nunique()}")
print(f"  Unique times: {worst_case_records['TimeOfCall'].nunique()}")

# Compare to raw for same case
if worst_case in raw_df['ReportNumberNew'].values:
    raw_case_records = raw_df[raw_df['ReportNumberNew'] == worst_case]
    print(f"\nSame case in raw file: {len(raw_case_records):,} records")
    print(f"  Raw unique incidents: {raw_case_records['Incident'].nunique()}")
    print(f"  Raw unique addresses: {raw_case_records['FullAddress2'].nunique()}")

print(f"\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print(f"ESRI file has {len(esri_df) - len(raw_df):,} MORE records than raw file")
print(f"ESRI file has {esri_df['ReportNumberNew'].nunique() - raw_df['ReportNumberNew'].nunique():,} FEWER unique cases")
print(f"This suggests severe duplicate corruption during ESRI processing!")

