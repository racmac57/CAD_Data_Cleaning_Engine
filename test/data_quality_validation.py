"""
CAD Data Quality Validation Script
Two-part validation:
1. Incident Field Validation against manual call type mapping
2. FullAddress2 Quality Audit

Author: Claude Code
Date: 2025-11-22
"""

import pandas as pd
import re
from collections import Counter
import numpy as np

# ============================================================================
# CONFIGURATION
# ============================================================================

# Input files (Note: Using available file from test directory)
CAD_FILE = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\test\2025_11_17_CAD_With_RMS.csv"
MANUAL_CALL_TYPE_FILE = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\ref\manual_call_type.csv"

# Output files
INCIDENT_REPORT = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\test\Incident_Validation_Report.csv"
ADDRESS_REPORT = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\test\Address_Quality_Report.csv"

# ============================================================================
# PART 1: INCIDENT FIELD VALIDATION
# ============================================================================

def normalize_incident(incident):
    """Normalize incident text for comparison"""
    if pd.isna(incident) or incident == '':
        return None
    return str(incident).strip()

def load_call_type_mapping():
    """Load and process the manual call type mapping"""
    df = pd.read_csv(MANUAL_CALL_TYPE_FILE, encoding='utf-8-sig')

    # The file has columns where index 3 is "Incident" and index 4 is "Change to"
    # Build a dictionary of valid incident types
    valid_incidents = set()
    variant_to_correct = {}

    for _, row in df.iterrows():
        incident = row.iloc[3] if len(row) > 3 else None
        change_to = row.iloc[4] if len(row) > 4 else None

        if pd.notna(incident) and incident != '' and incident != 'Incident':
            normalized_incident = normalize_incident(incident)
            if normalized_incident:
                if pd.notna(change_to) and change_to != '':
                    # This is a variant that should be changed
                    variant_to_correct[normalized_incident] = normalize_incident(change_to)
                    # Also add the correct version to valid set
                    valid_incidents.add(normalize_incident(change_to))
                else:
                    # This is a valid incident type
                    valid_incidents.add(normalized_incident)

    return valid_incidents, variant_to_correct

def validate_incidents(cad_df, valid_incidents, variant_to_correct):
    """Validate incident fields against mapping"""
    results = []

    for idx, row in cad_df.iterrows():
        report_num = row['ReportNumberNew']
        incident = row['Incident']
        normalized_incident = normalize_incident(incident)

        # Determine match status
        if normalized_incident is None:
            match_status = 'NULL/EMPTY'
            suggested_correction = 'MANUAL REVIEW NEEDED'
        elif normalized_incident in valid_incidents:
            match_status = 'VALID'
            suggested_correction = None
        elif normalized_incident in variant_to_correct:
            match_status = 'VARIANT - NEEDS CORRECTION'
            suggested_correction = variant_to_correct[normalized_incident]
        else:
            match_status = 'UNMAPPED'
            suggested_correction = 'NOT IN MAPPING FILE'

        results.append({
            'ReportNumberNew': report_num,
            'Incident': incident,
            'Match_Status': match_status,
            'Suggested_Correction': suggested_correction
        })

    return pd.DataFrame(results)

# ============================================================================
# PART 2: FULLADDRESS2 QUALITY AUDIT
# ============================================================================

# Common street types for validation
STREET_TYPES = [
    'Street', 'St', 'Avenue', 'Ave', 'Road', 'Rd', 'Boulevard', 'Blvd',
    'Lane', 'Ln', 'Drive', 'Dr', 'Court', 'Ct', 'Place', 'Pl', 'Circle', 'Cir',
    'Way', 'Terrace', 'Ter', 'Parkway', 'Pkwy', 'Highway', 'Hwy'
]

# Generic placeholders to flag
GENERIC_PLACEHOLDERS = [
    'Home', 'Park', 'School', 'PO Box', 'P.O. Box', 'Unknown',
    'Not Available', 'N/A', 'NA', 'TBD', 'To Be Determined'
]

def has_street_number(address):
    """Check if address starts with a number"""
    if pd.isna(address) or address == '':
        return False
    # Check if address starts with digits
    match = re.match(r'^\d+', str(address).strip())
    return match is not None

def has_street_type(address):
    """Check if address contains a valid street type"""
    if pd.isna(address) or address == '':
        return False
    address_str = str(address)
    for street_type in STREET_TYPES:
        if re.search(rf'\b{street_type}\b', address_str, re.IGNORECASE):
            return True
    return False

def is_intersection(address):
    """Check if address appears to be an intersection (contains &)"""
    if pd.isna(address) or address == '':
        return False
    return '&' in str(address)

def has_valid_intersection(address):
    """Check if intersection has two street names (not just '& ,')"""
    if pd.isna(address) or address == '':
        return False

    address_str = str(address).strip()

    # Check for invalid patterns like "& ,", "& Hackensack", etc.
    if re.search(r'&\s*,', address_str):
        return False

    # Split by & and check both sides have meaningful content
    parts = address_str.split('&')
    if len(parts) != 2:
        return False

    left = parts[0].strip()
    right = parts[1].split(',')[0].strip()  # Get part before comma

    # Both sides should have at least a street name (not just city/state)
    if len(left) < 3 or len(right) < 3:
        return False

    return True

def is_generic_placeholder(address):
    """Check if address is a generic placeholder"""
    if pd.isna(address) or address == '':
        return True

    address_str = str(address).strip().lower()

    for placeholder in GENERIC_PLACEHOLDERS:
        if placeholder.lower() in address_str:
            return True

    return False

def is_po_box(address):
    """Check if address is a PO Box"""
    if pd.isna(address) or address == '':
        return False
    return bool(re.search(r'\bP\.?\s*O\.?\s*Box\b', str(address), re.IGNORECASE))

def audit_address_quality(cad_df):
    """Audit FullAddress2 field quality"""
    results = []

    for idx, row in cad_df.iterrows():
        report_num = row['ReportNumberNew']
        address = row['FullAddress2']

        issues = []
        severity = 'OK'
        suggested_fix = None

        # Check for null/empty
        if pd.isna(address) or str(address).strip() == '':
            issues.append('NULL/EMPTY')
            severity = 'CRITICAL'
            suggested_fix = 'MANUAL REVIEW - NO ADDRESS PROVIDED'

        # Check for generic placeholders
        elif is_generic_placeholder(address):
            issues.append('GENERIC_PLACEHOLDER')
            severity = 'CRITICAL'
            suggested_fix = 'REPLACE WITH ACTUAL ADDRESS'

        # Check for PO Box
        elif is_po_box(address):
            issues.append('PO_BOX')
            severity = 'WARNING'
            suggested_fix = 'VERIFY PHYSICAL ADDRESS NEEDED'

        # Check intersections
        elif is_intersection(address):
            if not has_valid_intersection(address):
                issues.append('INCOMPLETE_INTERSECTION')
                severity = 'HIGH'
                suggested_fix = 'MISSING CROSS STREET - NEEDS BOTH STREET NAMES'

        # Check standard addresses
        else:
            # Must have street number
            if not has_street_number(address):
                issues.append('MISSING_STREET_NUMBER')
                severity = 'HIGH'
                suggested_fix = 'ADD STREET NUMBER'

            # Should have street type
            if not has_street_type(address):
                issues.append('MISSING_STREET_TYPE')
                severity = 'MEDIUM'
                suggested_fix = 'VERIFY STREET TYPE (St, Ave, Rd, etc.)'

        # Only add to results if there are issues
        if issues:
            results.append({
                'ReportNumberNew': report_num,
                'FullAddress2': address,
                'Issue_Type': '; '.join(issues),
                'Severity': severity,
                'Suggested_Fix': suggested_fix
            })

    return pd.DataFrame(results)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("=" * 80)
    print("CAD DATA QUALITY VALIDATION")
    print("=" * 80)
    print()

    # Load CAD data
    print(f"Loading CAD data from: {CAD_FILE}")
    cad_df = pd.read_csv(CAD_FILE, encoding='utf-8-sig')
    total_records = len(cad_df)
    print(f"  [OK] Loaded {total_records:,} records")
    print()

    # ========================================================================
    # PART 1: INCIDENT VALIDATION
    # ========================================================================
    print("-" * 80)
    print("PART 1: INCIDENT FIELD VALIDATION")
    print("-" * 80)

    print("Loading manual call type mapping...")
    valid_incidents, variant_to_correct = load_call_type_mapping()
    print(f"  [OK] Loaded {len(valid_incidents):,} valid incident types")
    print(f"  [OK] Loaded {len(variant_to_correct):,} known variants")
    print()

    print("Validating incident fields...")
    incident_report = validate_incidents(cad_df, valid_incidents, variant_to_correct)

    # Save full report
    incident_report.to_csv(INCIDENT_REPORT, index=False, encoding='utf-8-sig')
    print(f"  [OK] Saved report to: {INCIDENT_REPORT}")
    print()

    # Summary statistics
    status_counts = incident_report['Match_Status'].value_counts()
    print("Incident Validation Summary:")
    print(f"  Total Records: {len(incident_report):,}")
    for status, count in status_counts.items():
        pct = (count / len(incident_report)) * 100
        print(f"    {status}: {count:,} ({pct:.1f}%)")
    print()

    # Top unmapped incidents
    unmapped = incident_report[incident_report['Match_Status'] == 'UNMAPPED']
    if len(unmapped) > 0:
        print("Top 10 Unmapped Incident Types:")
        unmapped_counts = unmapped['Incident'].value_counts().head(10)
        for incident, count in unmapped_counts.items():
            print(f"    {incident}: {count:,} occurrences")
    print()

    # ========================================================================
    # PART 2: ADDRESS QUALITY AUDIT
    # ========================================================================
    print("-" * 80)
    print("PART 2: FULLADDRESS2 QUALITY AUDIT")
    print("-" * 80)

    print("Auditing address quality...")
    address_report = audit_address_quality(cad_df)

    # Save full report
    address_report.to_csv(ADDRESS_REPORT, index=False, encoding='utf-8-sig')
    print(f"  [OK] Saved report to: {ADDRESS_REPORT}")
    print()

    # Summary statistics
    total_address_issues = len(address_report)
    pct_with_issues = (total_address_issues / total_records) * 100

    print("Address Quality Summary:")
    print(f"  Total Records: {total_records:,}")
    print(f"  Records with Issues: {total_address_issues:,} ({pct_with_issues:.1f}%)")
    print(f"  Records OK: {total_records - total_address_issues:,} ({100 - pct_with_issues:.1f}%)")
    print()

    # Breakdown by severity
    if len(address_report) > 0:
        severity_counts = address_report['Severity'].value_counts()
        print("Issues by Severity:")
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'WARNING']:
            count = severity_counts.get(severity, 0)
            if count > 0:
                pct = (count / total_address_issues) * 100
                print(f"    {severity}: {count:,} ({pct:.1f}%)")
        print()

        # Top 10 issue types
        print("Top 10 Invalid Address Patterns:")
        issue_counts = address_report['Issue_Type'].value_counts().head(10)
        for issue, count in issue_counts.items():
            print(f"    {issue}: {count:,} occurrences")
        print()

    # ========================================================================
    # OVERALL SUMMARY
    # ========================================================================
    print("=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print(f"Total Records Reviewed: {total_records:,}")
    print()
    print("Incident Validation:")
    print(f"  Unmapped Incidents: {len(unmapped):,}")
    print(f"  Null/Empty Incidents: {status_counts.get('NULL/EMPTY', 0):,}")
    print(f"  Variants Needing Correction: {status_counts.get('VARIANT - NEEDS CORRECTION', 0):,}")
    print()
    print("Address Quality:")
    print(f"  Incomplete Address Records: {total_address_issues:,}")
    if len(address_report) > 0:
        critical_addresses = len(address_report[address_report['Severity'] == 'CRITICAL'])
        high_addresses = len(address_report[address_report['Severity'] == 'HIGH'])
        print(f"    Critical Issues: {critical_addresses:,}")
        print(f"    High Priority Issues: {high_addresses:,}")
    print()
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
