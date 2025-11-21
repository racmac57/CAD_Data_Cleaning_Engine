#!/usr/bin/env python
"""
Address Quality Analysis for ESRI Geocoding Standards
======================================================
Analyzes FullAddress2 column for geocoding readiness

Author: Claude Code
Date: 2025-11-18
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Configuration
BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = DATA_DIR / "02_reports"

# Input/Output
INPUT_FILE = DATA_DIR / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
OUTPUT_REPORT = REPORTS_DIR / "address_quality_report.md"

# Street types for validation
STREET_TYPES = [
    'STREET', 'ST', 'AVENUE', 'AVE', 'ROAD', 'RD', 'DRIVE', 'DR', 'LANE', 'LN',
    'BOULEVARD', 'BLVD', 'COURT', 'CT', 'PLACE', 'PL', 'CIRCLE', 'CIR',
    'TERRACE', 'TER', 'WAY', 'PARKWAY', 'PKWY', 'HIGHWAY', 'HWY', 'PLAZA',
    'SQUARE', 'SQ', 'TRAIL', 'TRL', 'PATH', 'ALLEY', 'WALK', 'EXPRESSWAY',
    'TURNPIKE', 'TPKE', 'ROUTE', 'RT'
]

# Generic location terms
GENERIC_TERMS = [
    'HOME', 'VARIOUS', 'UNKNOWN', 'PARKING GARAGE', 'REAR LOT', 'PARKING LOT',
    'LOT', 'GARAGE', 'REAR', 'FRONT', 'SIDE', 'BEHIND', 'ACROSS', 'NEAR',
    'BETWEEN', 'AREA', 'LOCATION', 'SCENE', 'UNDETERMINED', 'N/A', 'NA',
    'NONE', 'BLANK', 'PARK'
]


def categorize_address(address):
    """
    Categorize an address into quality categories
    Returns: (category, reason)
    """
    if pd.isna(address) or str(address).strip() == '':
        return 'blank', 'Null or empty address'

    addr = str(address).strip()
    addr_upper = addr.upper()

    # Check for PO BOX
    if re.search(r'P\.?O\.?\s*BOX', addr_upper):
        return 'po_box', 'PO Box address'

    # Check for generic location terms at start
    for term in GENERIC_TERMS:
        if addr_upper.startswith(term) or f' {term} ' in addr_upper:
            # Special case: if it's a park name with a valid street (like "Columbus Park & Main Street")
            if term == 'PARK' and '&' in addr:
                parts = addr.split('&')
                if len(parts) == 2 and has_street_type(parts[1]):
                    continue
            return 'generic_location', f'Generic term: {term}'

    # Check if it's an intersection (has &)
    if '&' in addr:
        parts = addr.split('&')
        if len(parts) == 2:
            part1 = parts[0].strip()
            part2 = parts[1].strip()

            # Check for incomplete intersection (empty second part or just city/state)
            if not part2 or part2.startswith(',') or re.match(r'^,?\s*(Hackensack|NJ|07601)', part2, re.IGNORECASE):
                return 'incomplete_intersection', 'Missing second street in intersection'

            # Valid intersection should have street types in both parts
            has_type1 = has_street_type(part1)
            has_type2 = has_street_type(part2)

            if has_type1 and has_type2:
                return 'valid_intersection', 'Valid intersection format'
            elif not has_type1 and not has_type2:
                return 'missing_street_type', 'Both streets missing type'
            elif not has_type1:
                return 'missing_street_type', f'First street missing type: {part1}'
            else:
                return 'missing_street_type', f'Second street missing type: {part2}'

    # Standard address - should start with number
    if re.match(r'^\d+', addr):
        # Has street number, check for street type
        if has_street_type(addr):
            # Check for city/state/zip
            if has_city_state_zip(addr):
                return 'valid_standard', 'Valid standard address'
            else:
                return 'incomplete', 'Missing city/state/zip'
        else:
            return 'missing_street_type', 'No street type suffix'
    else:
        # No street number - check if it might be a valid named location
        if has_street_type(addr):
            return 'missing_street_number', 'Street name without number'
        else:
            # Could be city only or incomplete
            if re.match(r'^(Hackensack|NJ|07601)', addr, re.IGNORECASE):
                return 'incomplete', 'City/state only'
            return 'missing_street_number', 'No street number'


def has_street_type(text):
    """Check if text contains a valid street type"""
    text_upper = text.upper()
    for st_type in STREET_TYPES:
        # Match street type as whole word
        if re.search(rf'\b{st_type}\b', text_upper):
            return True
    return False


def has_city_state_zip(text):
    """Check if address has city, state, and zip"""
    # Look for pattern: City, State, Zip or City, State Zip
    return bool(re.search(r'Hackensack.*NJ.*07601', text, re.IGNORECASE))


def analyze_addresses(df):
    """Analyze all addresses and categorize them"""
    results = defaultdict(list)
    category_counts = defaultdict(int)

    print(f"Analyzing {len(df):,} addresses...")

    for idx, row in df.iterrows():
        address = row['FullAddress2']
        report_num = row['ReportNumberNew']

        category, reason = categorize_address(address)
        category_counts[category] += 1

        # Store samples (up to 100 per category for sampling)
        if len(results[category]) < 100:
            results[category].append({
                'ReportNumberNew': report_num,
                'FullAddress2': address,
                'Reason': reason
            })

        if (idx + 1) % 100000 == 0:
            print(f"  Processed {idx + 1:,} records...")

    return category_counts, results


def generate_report(df, category_counts, samples):
    """Generate markdown report"""
    total = len(df)

    # Calculate valid vs invalid
    valid_categories = ['valid_standard', 'valid_intersection']
    valid_count = sum(category_counts.get(cat, 0) for cat in valid_categories)
    invalid_count = total - valid_count

    valid_pct = (valid_count / total) * 100
    invalid_pct = (invalid_count / total) * 100

    # Category order and descriptions
    category_info = {
        'valid_standard': ('Valid Standard', 'Complete address with number, street type, city/state/zip'),
        'valid_intersection': ('Valid Intersection', 'Two streets with & separator'),
        'missing_street_number': ('Missing Street Number', 'Street name without house/building number'),
        'missing_street_type': ('Missing Street Type', 'No STREET/AVENUE/ROAD etc suffix'),
        'generic_location': ('Generic Location', 'HOME, VARIOUS, UNKNOWN, PARK, etc'),
        'incomplete_intersection': ('Incomplete Intersection', 'Has & but missing second street'),
        'incomplete': ('Incomplete Address', 'City/state only or missing components'),
        'po_box': ('PO Box', 'Post office box - not geocodable'),
        'blank': ('Blank/Null', 'Empty address field')
    }

    report = f"""# Address Quality Report for ESRI Geocoding
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total Records** | {total:,} | 100.00% |
| **Valid Addresses** | {valid_count:,} | {valid_pct:.2f}% |
| **Invalid Addresses** | {invalid_count:,} | {invalid_pct:.2f}% |

### Geocoding Readiness

**Estimated Geocoding Success Rate: {valid_pct:.1f}%**

- Addresses ready for geocoding: {valid_count:,}
- Addresses needing cleanup: {invalid_count:,}

## Category Breakdown

| Category | Count | % of Total | Geocodable |
|----------|-------|------------|------------|
"""

    # Sort categories by count (descending)
    sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

    for cat, count in sorted_cats:
        pct = (count / total) * 100
        cat_name = category_info.get(cat, (cat, ''))[0]
        geocodable = 'Yes' if cat in valid_categories else 'No'
        report += f"| {cat_name} | {count:,} | {pct:.2f}% | {geocodable} |\n"

    # Invalid breakdown
    report += f"""
## Invalid Address Details

### Issue Types Requiring Attention

"""

    invalid_cats = [cat for cat in sorted_cats if cat[0] not in valid_categories]

    for cat, count in invalid_cats:
        if count == 0:
            continue
        cat_name, description = category_info.get(cat, (cat, ''))
        pct = (count / total) * 100

        report += f"""#### {cat_name}
- **Count:** {count:,} ({pct:.2f}%)
- **Description:** {description}

**Sample Records (up to 5):**

| ReportNumberNew | FullAddress2 | Issue |
|-----------------|--------------|-------|
"""

        # Add samples
        cat_samples = samples.get(cat, [])[:5]
        for sample in cat_samples:
            addr = str(sample['FullAddress2'])[:60] if sample['FullAddress2'] else '(blank)'
            reason = sample['Reason'][:40]
            report += f"| {sample['ReportNumberNew']} | {addr} | {reason} |\n"

        report += "\n"

    # Recommendations
    report += f"""## Recommendations for Cleanup

### High Priority (Most Impact)

1. **Incomplete Intersections** ({category_counts.get('incomplete_intersection', 0):,} records)
   - Pattern: "Street Name & , Hackensack, NJ, 07601"
   - Action: Review CAD system to capture second street name
   - Many appear to be intersections where cross street wasn't recorded

2. **Missing Street Numbers** ({category_counts.get('missing_street_number', 0):,} records)
   - Pattern: "Main Street, Hackensack, NJ, 07601"
   - Action: Cross-reference with original CAD records or parcel data
   - Some may be valid intersections that need reformatting

3. **Generic Locations** ({category_counts.get('generic_location', 0):,} records)
   - Pattern: "Home & , Hackensack, NJ, 07601"
   - Action: These cannot be geocoded; consider flagging for manual review
   - May need to be excluded from spatial analysis

### Medium Priority

4. **Missing Street Types** ({category_counts.get('missing_street_type', 0):,} records)
   - Action: Standardize street names using USPS or county address database
   - Example: "Main" -> "Main Street"

5. **Incomplete Addresses** ({category_counts.get('incomplete', 0):,} records)
   - Action: Enrich with missing city/state/zip from default values

### Low Priority

6. **PO Boxes** ({category_counts.get('po_box', 0):,} records)
   - Cannot be geocoded to street location
   - Consider using alternate address if available

## Geocoding Strategy

### Recommended Approach

1. **Phase 1: Geocode Valid Addresses**
   - Process {valid_count:,} valid addresses first
   - Expected success rate: ~95-98%

2. **Phase 2: Address Standardization**
   - Use ESRI address locator with relaxed matching
   - May recover additional {category_counts.get('missing_street_type', 0) + category_counts.get('incomplete', 0):,} addresses

3. **Phase 3: Manual Review**
   - Flag remaining {category_counts.get('generic_location', 0) + category_counts.get('incomplete_intersection', 0):,} addresses
   - Consider centroid fallback for statistical analysis

### Quality Metrics

| Quality Level | Definition | Count | Percentage |
|---------------|------------|-------|------------|
| High | Valid standard/intersection | {valid_count:,} | {valid_pct:.2f}% |
| Medium | Fixable with standardization | {category_counts.get('missing_street_type', 0) + category_counts.get('incomplete', 0):,} | {((category_counts.get('missing_street_type', 0) + category_counts.get('incomplete', 0)) / total * 100):.2f}% |
| Low | Requires manual review | {category_counts.get('missing_street_number', 0) + category_counts.get('incomplete_intersection', 0):,} | {((category_counts.get('missing_street_number', 0) + category_counts.get('incomplete_intersection', 0)) / total * 100):.2f}% |
| Ungeocoadable | Generic/blank | {category_counts.get('generic_location', 0) + category_counts.get('blank', 0) + category_counts.get('po_box', 0):,} | {((category_counts.get('generic_location', 0) + category_counts.get('blank', 0) + category_counts.get('po_box', 0)) / total * 100):.2f}% |

---
*Report generated by CAD Data Cleaning Engine*
"""

    return report


def main():
    print("="*60)
    print("ADDRESS QUALITY ANALYSIS")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load data
    print(f"\nLoading: {INPUT_FILE}")
    df = pd.read_excel(INPUT_FILE)
    print(f"Records: {len(df):,}")

    # Analyze addresses
    print("\nAnalyzing addresses...")
    category_counts, samples = analyze_addresses(df)

    # Generate report
    print("\nGenerating report...")
    report = generate_report(df, category_counts, samples)

    # Save report
    with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\nReport saved: {OUTPUT_REPORT}")

    # Print summary
    total = len(df)
    valid_count = category_counts.get('valid_standard', 0) + category_counts.get('valid_intersection', 0)

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total records: {total:,}")
    print(f"Valid addresses: {valid_count:,} ({valid_count/total*100:.2f}%)")
    print(f"Invalid addresses: {total - valid_count:,} ({(total-valid_count)/total*100:.2f}%)")
    print(f"\nTop issues:")

    sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    for cat, count in sorted_cats[:5]:
        print(f"  {cat}: {count:,} ({count/total*100:.2f}%)")

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
