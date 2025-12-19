#!/usr/bin/env python3
"""Verify the final ESRI file is ready for submission."""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

FINAL_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected_DEDUPED.xlsx"

print("=" * 80)
print("FINAL ESRI FILE VERIFICATION")
print("=" * 80)

# Required columns for ESRI
REQUIRED_COLUMNS = [
    'TimeOfCall', 'cYear', 'cMonth', 'Hour', 'DayofWeek',
    'Incident', 'Response_Type', 'How Reported',
    'FullAddress2', 'Grid', 'PDZone',
    'Officer', 'Disposition', 'ReportNumberNew',
    'Latitude', 'Longitude', 'data_quality_flag'
]

# Load file
print(f"\nLoading: {FINAL_FILE.name}")
df = pd.read_excel(FINAL_FILE)

print(f"\nFile Statistics:")
print(f"  Total records: {len(df):,}")
print(f"  Unique cases: {df['ReportNumberNew'].nunique():,}")
print(f"  Duplicate cases: {len(df) - df['ReportNumberNew'].nunique():,}")

# Check columns
print(f"\nColumn Verification:")
missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
if missing_cols:
    print(f"  ❌ Missing columns: {missing_cols}")
else:
    print(f"  ✅ All required columns present")

extra_cols = [col for col in df.columns if col not in REQUIRED_COLUMNS]
if extra_cols:
    print(f"  ⚠️  Extra columns (will be ignored): {extra_cols}")

# Check data quality
print(f"\nData Quality Checks:")

# Check for duplicates
dup_mask = df.duplicated(subset=['ReportNumberNew'], keep=False)
dup_count = dup_mask.sum()
max_dups = df.groupby('ReportNumberNew').size().max()
print(f"  Duplicate records: {dup_count:,} (max {max_dups} per case)")

# Check field coverage
incident_coverage = (df['Incident'].notna().sum() / len(df) * 100)
response_coverage = (df['Response_Type'].notna().sum() / len(df) * 100)
disposition_coverage = (df['Disposition'].notna().sum() / len(df) * 100)

print(f"  Incident coverage: {incident_coverage:.2f}%")
print(f"  Response_Type coverage: {response_coverage:.2f}%")
print(f"  Disposition coverage: {disposition_coverage:.2f}%")

# Check address quality
def is_invalid(addr):
    if pd.isna(addr) or str(addr).strip() == "":
        return True
    addr = str(addr).strip().upper()
    if " & ," in addr or "CANCELED CALL" in addr:
        return True
    return False

invalid_addrs = df['FullAddress2'].apply(is_invalid).sum()
valid_pct = ((len(df) - invalid_addrs) / len(df) * 100)
print(f"  Address validity: {valid_pct:.1f}% ({invalid_addrs:,} invalid)")

# Final assessment
print(f"\n" + "=" * 80)
print("FINAL ASSESSMENT")
print("=" * 80)

issues = []
if missing_cols:
    issues.append(f"Missing required columns: {missing_cols}")
if max_dups > 25:
    issues.append(f"Excessive duplicates: max {max_dups} per case")
if response_coverage < 99:
    issues.append(f"Response_Type coverage below 99%: {response_coverage:.2f}%")
if valid_pct < 95:
    issues.append(f"Address validity below 95%: {valid_pct:.1f}%")

if issues:
    print("  ⚠️  ISSUES FOUND:")
    for issue in issues:
        print(f"    - {issue}")
    print("\n  Status: NEEDS REVIEW")
else:
    print("  ✅ ALL CHECKS PASSED")
    print("\n  Status: READY FOR ESRI SUBMISSION")

print(f"\nFile: {FINAL_FILE}")
print(f"Size: {FINAL_FILE.stat().st_size / (1024*1024):.1f} MB")

