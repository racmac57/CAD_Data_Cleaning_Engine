#!/usr/bin/env python3
"""
Comprehensive quality check for ESRI export file.
Compares current state to raw data baseline.
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

BASE_DIR = Path(__file__).parent.parent

# File paths
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected.xlsx"
RAW_CAD_FILE = BASE_DIR / "data" / "01_raw" / "2025_11_21_2019_2025_11_21_ALL_CAD_Data.xlsx"
OUTPUT_DIR = BASE_DIR / "data" / "02_reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Street types for validation
STREET_TYPES = [
    "STREET", "ST", "AVENUE", "AVE", "ROAD", "RD", "DRIVE", "DR", "LANE", "LN",
    "BOULEVARD", "BLVD", "COURT", "CT", "PLACE", "PL", "CIRCLE", "CIR",
    "TERRACE", "TER", "WAY", "PARKWAY", "PKWY", "HIGHWAY", "HWY", "PLAZA",
    "SQUARE", "SQ", "TRAIL", "TRL", "PATH", "ALLEY", "WALK", "EXPRESSWAY",
    "TURNPIKE", "TPKE", "ROUTE", "RT"
]

STREET_REGEX = r"\b(?:" + "|".join(STREET_TYPES) + r")\b"

def is_invalid_address(address):
    """Check if address is invalid/incomplete."""
    if pd.isna(address) or str(address).strip() == "":
        return True, "blank"
    
    addr = str(address).strip()
    addr_upper = addr.upper()
    
    # Check for incomplete intersection (contains " & ," - missing second street)
    if re.search(r'&\s*,', addr_upper):
        return True, "incomplete_intersection"
    
    # Check for generic terms
    generic_terms = ["HOME", "VARIOUS", "UNKNOWN", "PARKING GARAGE", "REAR LOT", 
                     "PARKING LOT", "LOT", "GARAGE", "AREA", "LOCATION", "SCENE",
                     "N/A", "NA", "TBD", "TO BE DETERMINED", "CANCELED CALL"]
    for term in generic_terms:
        if re.search(rf'\b{re.escape(term)}\b', addr_upper):
            return True, "generic_location"
    
    # Check for complete intersection (has " & " with both streets)
    if " & " in addr_upper and not re.search(r'&\s*,', addr_upper):
        parts = addr_upper.split("&")
        if len(parts) == 2:
            part1 = parts[0].strip()
            part2 = parts[1].strip()
            # If both parts have street types, it's likely valid
            if re.search(STREET_REGEX, part1, re.IGNORECASE) and re.search(STREET_REGEX, part2, re.IGNORECASE):
                return False, "valid"
    
    # For standard addresses (not intersections), check if it starts with a number
    if " & " not in addr_upper:
        # Standard address should start with a number
        if not re.match(r'^\d+', addr):
            # Check if it has a street type (might be a named location like "Park")
            if not re.search(STREET_REGEX, addr_upper, re.IGNORECASE):
                return True, "missing_street_number"
    
    # Check for missing street type (has number but no street type)
    if re.match(r'^\d+', addr):
        if not re.search(STREET_REGEX, addr_upper, re.IGNORECASE):
            return True, "missing_street_type"
    
    return False, "valid"

def analyze_address_quality(df):
    """Analyze address quality."""
    print("\nAnalyzing address quality...")
    
    issue_counter = Counter()
    invalid_count = 0
    valid_count = 0
    
    for addr in df['FullAddress2']:
        is_invalid, issue_type = is_invalid_address(addr)
        if is_invalid:
            invalid_count += 1
            issue_counter[issue_type] += 1
        else:
            valid_count += 1
    
    total = len(df)
    valid_pct = (valid_count / total * 100) if total > 0 else 0
    invalid_pct = (invalid_count / total * 100) if total > 0 else 0
    
    return {
        'total': total,
        'valid': valid_count,
        'valid_pct': valid_pct,
        'invalid': invalid_count,
        'invalid_pct': invalid_pct,
        'issues': dict(issue_counter)
    }

def analyze_field_coverage(df, field_name):
    """Analyze field coverage."""
    if field_name not in df.columns:
        return {'total': len(df), 'null': len(df), 'null_pct': 100.0, 'coverage': 0.0}
    
    null_count = df[field_name].isna().sum()
    empty_count = (df[field_name].astype(str).str.strip() == '').sum()
    total_null = null_count + empty_count
    total = len(df)
    coverage = ((total - total_null) / total * 100) if total > 0 else 0
    
    return {
        'total': total,
        'null': total_null,
        'null_pct': (total_null / total * 100) if total > 0 else 0,
        'coverage': coverage
    }

def analyze_how_reported(df):
    """Analyze How Reported field."""
    if 'How Reported' not in df.columns:
        return {'total': len(df), 'standard': 0, 'needs_fix': len(df)}
    
    standard_values = {'9-1-1', 'Phone', 'Radio', 'Self-Initiated', 'Walk-In', 'Other'}
    
    df['_how_reported_upper'] = df['How Reported'].astype(str).str.strip().str.upper()
    standard_mask = df['_how_reported_upper'].isin([v.upper() for v in standard_values])
    
    needs_fix = (~standard_mask & df['How Reported'].notna()).sum()
    standard = standard_mask.sum()
    total = len(df)
    
    return {
        'total': total,
        'standard': standard,
        'standard_pct': (standard / total * 100) if total > 0 else 0,
        'needs_fix': needs_fix,
        'needs_fix_pct': (needs_fix / total * 100) if total > 0 else 0
    }

def main():
    """Main execution."""
    print("=" * 80)
    print("COMPREHENSIVE ESRI DATA QUALITY CHECK")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load ESRI file
    print(f"\nLoading ESRI file: {ESRI_FILE.name}")
    try:
        esri_df = pd.read_excel(ESRI_FILE, dtype=str)
        print(f"Loaded {len(esri_df):,} records")
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Try to load raw file for comparison
    raw_df = None
    if RAW_CAD_FILE.exists():
        try:
            print(f"\nLoading raw CAD file for comparison: {RAW_CAD_FILE.name}")
            raw_df = pd.read_excel(RAW_CAD_FILE, dtype=str, nrows=100000)  # Sample for speed
            print(f"Loaded {len(raw_df):,} sample records from raw file")
        except Exception as e:
            print(f"Could not load raw file: {e}")
    
    # Analyze current ESRI file
    print("\n" + "=" * 80)
    print("CURRENT ESRI FILE ANALYSIS")
    print("=" * 80)
    
    # Address quality
    address_quality = analyze_address_quality(esri_df)
    print(f"\nAddress Quality:")
    print(f"  Total records: {address_quality['total']:,}")
    print(f"  Valid addresses: {address_quality['valid']:,} ({address_quality['valid_pct']:.1f}%)")
    print(f"  Invalid addresses: {address_quality['invalid']:,} ({address_quality['invalid_pct']:.1f}%)")
    print(f"\n  Invalid address breakdown:")
    for issue_type, count in sorted(address_quality['issues'].items(), key=lambda x: x[1], reverse=True):
        print(f"    {issue_type}: {count:,}")
    
    # Field coverage
    print(f"\nField Coverage:")
    incident_coverage = analyze_field_coverage(esri_df, 'Incident')
    print(f"  Incident: {incident_coverage['coverage']:.2f}% ({incident_coverage['null']:,} null)")
    
    response_type_coverage = analyze_field_coverage(esri_df, 'Response_Type')
    print(f"  Response_Type: {response_type_coverage['coverage']:.2f}% ({response_type_coverage['null']:,} null)")
    
    disposition_coverage = analyze_field_coverage(esri_df, 'Disposition')
    print(f"  Disposition: {disposition_coverage['coverage']:.2f}% ({disposition_coverage['null']:,} null)")
    
    # How Reported
    how_reported = analyze_how_reported(esri_df)
    print(f"\nHow Reported:")
    print(f"  Standard values: {how_reported['standard']:,} ({how_reported['standard_pct']:.1f}%)")
    print(f"  Needs standardization: {how_reported['needs_fix']:,} ({how_reported['needs_fix_pct']:.1f}%)")
    
    # Hour field
    if 'Hour' in esri_df.columns:
        hour_filled = esri_df['Hour'].notna().sum()
        hour_pct = (hour_filled / len(esri_df) * 100) if len(esri_df) > 0 else 0
        print(f"\nHour Field:")
        print(f"  Filled: {hour_filled:,} ({hour_pct:.1f}%)")
    
    # Compare to raw if available
    if raw_df is not None and 'FullAddress2' in raw_df.columns:
        print("\n" + "=" * 80)
        print("COMPARISON TO RAW DATA (Sample)")
        print("=" * 80)
        
        raw_address_quality = analyze_address_quality(raw_df)
        print(f"\nRaw Data Address Quality (sample):")
        print(f"  Valid: {raw_address_quality['valid']:,} ({raw_address_quality['valid_pct']:.1f}%)")
        print(f"  Invalid: {raw_address_quality['invalid']:,} ({raw_address_quality['invalid_pct']:.1f}%)")
        
        print(f"\nImprovement:")
        improvement = raw_address_quality['invalid_pct'] - address_quality['invalid_pct']
        print(f"  Invalid address reduction: {improvement:.1f} percentage points")
        print(f"  From {raw_address_quality['invalid_pct']:.1f}% to {address_quality['invalid_pct']:.1f}%")
    
    # Generate report
    report_file = OUTPUT_DIR / f"ESRI_Data_Quality_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# ESRI Data Quality Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Source File:** {ESRI_FILE.name}\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write(f"- Total records: {address_quality['total']:,}\n")
        f.write(f"- Valid addresses: {address_quality['valid']:,} ({address_quality['valid_pct']:.1f}%)\n")
        f.write(f"- Invalid addresses: {address_quality['invalid']:,} ({address_quality['invalid_pct']:.1f}%)\n")
        f.write(f"- Response Type coverage: {response_type_coverage['coverage']:.2f}%\n")
        f.write(f"- Disposition coverage: {disposition_coverage['coverage']:.2f}%\n\n")
        
        f.write("## Address Quality Breakdown\n\n")
        for issue_type, count in sorted(address_quality['issues'].items(), key=lambda x: x[1], reverse=True):
            f.write(f"- **{issue_type}**: {count:,} records\n")
        
        f.write("\n## Field Coverage\n\n")
        f.write(f"- **Incident**: {incident_coverage['coverage']:.2f}% ({incident_coverage['null']:,} null)\n")
        f.write(f"- **Response_Type**: {response_type_coverage['coverage']:.2f}% ({response_type_coverage['null']:,} null)\n")
        f.write(f"- **Disposition**: {disposition_coverage['coverage']:.2f}% ({disposition_coverage['null']:,} null)\n")
        f.write(f"- **How Reported**: {how_reported['standard_pct']:.1f}% standardized ({how_reported['needs_fix']:,} need fixes)\n")
        
        if raw_df is not None:
            f.write("\n## Comparison to Raw Data\n\n")
            f.write(f"- Raw invalid addresses: {raw_address_quality['invalid_pct']:.1f}%\n")
            f.write(f"- Current invalid addresses: {address_quality['invalid_pct']:.1f}%\n")
            f.write(f"- **Improvement: {improvement:.1f} percentage points**\n")
    
    print(f"\n\nReport saved to: {report_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()

