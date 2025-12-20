"""Investigate record count discrepancy between polished and geocoded files."""
import pandas as pd
from pathlib import Path

# File paths
polished_path = Path(r'data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx')
geocoded_path = Path(r'data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114_geocoded.xlsx')

print("Loading files...")
df_polished = pd.read_excel(polished_path)
df_geocoded = pd.read_excel(geocoded_path)

print(f"\n{'='*60}")
print("RECORD COUNT ANALYSIS")
print(f"{'='*60}")
print(f"Polished records: {len(df_polished):,}")
print(f"Geocoded records: {len(df_geocoded):,}")
print(f"Difference: {len(df_geocoded) - len(df_polished):,}")

# Check for duplicates by ReportNumberNew
print(f"\n{'='*60}")
print("DUPLICATE ANALYSIS")
print(f"{'='*60}")

# Check polished file
polished_dupes = df_polished.duplicated(subset=['ReportNumberNew'], keep=False)
print(f"Polished - Duplicate ReportNumberNew: {polished_dupes.sum():,}")

# Check geocoded file
geocoded_dupes = df_geocoded.duplicated(subset=['ReportNumberNew'], keep=False)
print(f"Geocoded - Duplicate ReportNumberNew: {geocoded_dupes.sum():,}")

if geocoded_dupes.sum() > 0:
    print(f"\nSample duplicate ReportNumberNew values in geocoded file:")
    dup_counts = df_geocoded[geocoded_dupes]['ReportNumberNew'].value_counts().head(10)
    print(dup_counts)
    
    # Show an example of duplicates
    print(f"\nExample duplicate rows (first ReportNumberNew with duplicates):")
    example_rn = dup_counts.index[0]
    example_rows = df_geocoded[df_geocoded['ReportNumberNew'] == example_rn]
    print(example_rows[['ReportNumberNew', 'FullAddress2', 'latitude', 'longitude']].head())

# Check for duplicate addresses that might cause merge issues
print(f"\n{'='*60}")
print("ADDRESS DUPLICATE ANALYSIS")
print(f"{'='*60}")

polished_addr_dupes = df_polished.duplicated(subset=['FullAddress2'], keep=False)
geocoded_addr_dupes = df_geocoded.duplicated(subset=['FullAddress2'], keep=False)

print(f"Polished - Duplicate addresses: {polished_addr_dupes.sum():,}")
print(f"Geocoded - Duplicate addresses: {geocoded_addr_dupes.sum():,}")

# Check if merge created duplicates by comparing unique ReportNumberNew counts
print(f"\n{'='*60}")
print("UNIQUE RECORD ANALYSIS")
print(f"{'='*60}")

polished_unique_rn = df_polished['ReportNumberNew'].nunique()
geocoded_unique_rn = df_geocoded['ReportNumberNew'].nunique()

print(f"Polished - Unique ReportNumberNew: {polished_unique_rn:,}")
print(f"Geocoded - Unique ReportNumberNew: {geocoded_unique_rn:,}")
print(f"Difference in unique records: {geocoded_unique_rn - polished_unique_rn:,}")

# Check if there are new ReportNumberNew values in geocoded that weren't in polished
polished_rn_set = set(df_polished['ReportNumberNew'].dropna().astype(str))
geocoded_rn_set = set(df_geocoded['ReportNumberNew'].dropna().astype(str))

new_rn = geocoded_rn_set - polished_rn_set
missing_rn = polished_rn_set - geocoded_rn_set

print(f"\nNew ReportNumberNew in geocoded (not in polished): {len(new_rn):,}")
if len(new_rn) > 0:
    print(f"Sample new ReportNumberNew values: {list(new_rn)[:10]}")
    
print(f"Missing ReportNumberNew in geocoded (was in polished): {len(missing_rn):,}")
if len(missing_rn) > 0:
    print(f"Sample missing ReportNumberNew values: {list(missing_rn)[:10]}")

print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
if len(df_geocoded) > len(df_polished):
    print(f"⚠️  WARNING: Geocoded file has {len(df_geocoded) - len(df_polished):,} MORE records than polished file!")
    print("This suggests the merge operation may have created duplicate rows.")
    print("Recommendation: Check the merge logic in geocode_nj_geocoder.py")
else:
    print("✅ Record counts match or geocoded has fewer records (expected).")
