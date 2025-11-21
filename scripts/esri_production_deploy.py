#!/usr/bin/env python3
"""
ESRI Production Deployment - Final Data Cleaning Script (Optimized)
====================================================================
Uses vectorized pandas operations for speed with 700K+ records.
"""

import pandas as pd
import numpy as np
import re
import os
from datetime import datetime
from pathlib import Path

# Configuration
BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
OUTPUT_DIR = BASE_DIR / "data" / "ESRI_CADExport"
REPORTS_DIR = BASE_DIR / "data" / "02_reports"

# Input files
CAD_FILE = BASE_DIR / "ref" / "2019_2025_11_17_Updated_CAD_Export.xlsx"
DV_FILE = BASE_DIR / "ref" / "2025_11_17_DV_Offense_Report_Updated.xlsx"
RMS_FILE = BASE_DIR / "data" / "rms" / "2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx"
UNMAPPED_FILE = BASE_DIR / "ref" / "Unmapped_Response_Type.csv"
RAW_CALLTYPES_FILE = BASE_DIR / "ref" / "RAW_CAD_CALL_TYPE_EXPORT.xlsx"

# Create output directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Tracking metrics
metrics = {
    'total_records': 0,
    'response_type_mapped': 0,
    'taps_resolved': 0,
    'domestic_to_dv': 0,
    'domestic_to_dispute': 0,
    'tro_fro_split': 0,
    'tro_fro_manual_review': 0,
    'disposition_normalized': 0,
    'address_backfilled': 0,
}


def fix_mojibake(text):
    """Fix mojibake characters in text."""
    if pd.isna(text):
        return text
    text = str(text)
    text = text.replace('–', '-')
    text = text.replace('—', '-')
    text = text.replace('\x96', '-')
    return text


def load_data():
    """Load all input data files."""
    print("=" * 60)
    print("LOADING DATA FILES")
    print("=" * 60)

    # Load CAD data
    print(f"\nLoading CAD data...")
    cad_df = pd.read_excel(CAD_FILE)
    print(f"  Loaded {len(cad_df):,} CAD records")

    # Normalize column names
    column_renames = {
        'Time of Call': 'TimeOfCall',
        'Response Type': 'Response_Type',
        'HourMinuetsCalc': 'Hour'
    }
    cad_df = cad_df.rename(columns=column_renames)

    # Load DV report
    print(f"\nLoading DV report...")
    dv_df = pd.read_excel(DV_FILE)
    print(f"  Loaded {len(dv_df):,} DV records")

    # Load RMS data
    print(f"\nLoading RMS data...")
    rms_df = pd.read_excel(RMS_FILE)
    print(f"  Loaded {len(rms_df):,} RMS records")

    # Load manual mappings
    print(f"\nLoading manual mappings...")
    mappings_df = pd.read_csv(UNMAPPED_FILE, encoding='latin-1')
    print(f"  Loaded {len(mappings_df):,} mapping entries")

    # Load RAW call types
    print(f"\nLoading RAW call types...")
    raw_calltypes_df = pd.read_excel(RAW_CALLTYPES_FILE)
    print(f"  Loaded {len(raw_calltypes_df):,} raw call type entries")

    return cad_df, dv_df, rms_df, mappings_df, raw_calltypes_df


def build_response_type_mapping(mappings_df, raw_calltypes_df):
    """Build comprehensive Response_Type mapping dictionary."""
    print("\n" + "=" * 60)
    print("BUILDING RESPONSE_TYPE MAPPING")
    print("=" * 60)

    response_map = {}

    # Build from RAW call types
    if 'Call Type' in raw_calltypes_df.columns and 'Response' in raw_calltypes_df.columns:
        for _, row in raw_calltypes_df.iterrows():
            call_type = fix_mojibake(str(row['Call Type']).strip())
            response = row['Response']
            if pd.notna(response) and str(response).strip():
                response_map[call_type] = str(response).strip()
                # Also add lowercase version for case-insensitive matching
                response_map[call_type.lower()] = str(response).strip()

    print(f"  Loaded {len(response_map)} mappings from RAW call types")

    # Add manual mappings
    for _, row in mappings_df.iterrows():
        unmapped = fix_mojibake(str(row.get('Unmapped_Call_Type', '')).strip())
        raw_type = fix_mojibake(str(row.get('Raw_Call_Type', '')).strip())
        response = str(row.get('Response', '')).strip()

        if unmapped and response:
            response_map[unmapped] = response
            response_map[unmapped.lower()] = response
        if raw_type and response:
            response_map[raw_type] = response
            response_map[raw_type.lower()] = response

    print(f"  Total mapping entries: {len(response_map)}")
    return response_map


def apply_response_type_mapping(cad_df, response_map):
    """Apply Response_Type mappings using vectorized operations."""
    print("\n" + "=" * 60)
    print("APPLYING RESPONSE_TYPE MAPPINGS")
    print("=" * 60)

    # Fix mojibake in Incident column
    cad_df['Incident'] = cad_df['Incident'].apply(fix_mojibake)

    # Backup original
    cad_df['Response_Type_Original'] = cad_df['Response_Type'].copy()

    # Create lowercase incident for case-insensitive matching
    cad_df['_incident_lower'] = cad_df['Incident'].str.strip().str.lower()

    # Find records needing mapping (empty Response_Type)
    needs_mapping = cad_df['Response_Type'].isna() | (cad_df['Response_Type'].astype(str).str.strip() == '')

    # Apply mapping using map function
    mapped_values = cad_df.loc[needs_mapping, '_incident_lower'].map(response_map)

    # Update Response_Type where mapping found
    cad_df.loc[needs_mapping & mapped_values.notna(), 'Response_Type'] = mapped_values[mapped_values.notna()]

    # Count results
    metrics['response_type_mapped'] = mapped_values.notna().sum()

    # Calculate coverage
    total = len(cad_df)
    with_response = cad_df['Response_Type'].notna() & (cad_df['Response_Type'].astype(str).str.strip() != '')
    coverage = (with_response.sum() / total) * 100

    # Find unmapped
    still_unmapped = needs_mapping & cad_df['Response_Type'].isna()
    unmapped_types = cad_df.loc[still_unmapped, 'Incident'].unique()

    print(f"  Mapped {metrics['response_type_mapped']:,} records")
    print(f"  Current Response_Type coverage: {coverage:.2f}%")
    print(f"  Unmapped incident types: {len(unmapped_types)}")

    if len(unmapped_types) > 0:
        print(f"\n  Sample unmapped incidents:")
        for inc in list(unmapped_types)[:10]:
            print(f"    - {inc}")

    # Clean up temp column
    cad_df = cad_df.drop(columns=['_incident_lower'])

    return cad_df


def resolve_taps_variants(cad_df):
    """Resolve TAPS variant mappings using vectorized operations."""
    print("\n" + "=" * 60)
    print("RESOLVING TAPS VARIANTS (Blocker #8)")
    print("=" * 60)

    # TAPS base mappings
    taps_mask = cad_df['Incident'] == 'Targeted Area Patrol'
    esu_mask = cad_df['Incident'] == 'ESU - Targeted Patrol'

    # Also check lowercase variations
    taps_mask = taps_mask | (cad_df['Incident'].str.lower() == 'targeted area patrol')
    esu_mask = esu_mask | (cad_df['Incident'].str.lower() == 'esu - targeted patrol')

    address_lower = cad_df['FullAddress2'].fillna('').str.lower()

    # Default mappings
    cad_df.loc[taps_mask, 'Incident'] = 'TAPS - Other'
    cad_df.loc[esu_mask, 'Incident'] = 'TAPS - ESU - Other'

    # Specific TAPS mappings based on address keywords
    taps_keywords = {
        'business': 'TAPS - Business',
        'housing': 'TAPS - Housing',
        'medical': 'TAPS - Medical Facility',
        'hospital': 'TAPS - Medical Facility',
        'park': 'TAPS - Park',
        'garage': 'TAPS - Parking Garage',
        'church': 'TAPS - Religious Facility',
        'mosque': 'TAPS - Religious Facility',
        'synagogue': 'TAPS - Religious Facility',
        'school': 'TAPS - School'
    }

    esu_keywords = {
        'business': 'TAPS - ESU - Business',
        'medical': 'TAPS - ESU - Medical Facility',
        'hospital': 'TAPS - ESU - Medical Facility',
        'park': 'TAPS - ESU - Park',
        'garage': 'TAPS - ESU - Parking Garage',
        'church': 'TAPS - ESU - Religious Facility',
        'mosque': 'TAPS - ESU - Religious Facility',
        'synagogue': 'TAPS - ESU - Religious Facility',
        'school': 'TAPS - ESU - School'
    }

    for keyword, incident_type in taps_keywords.items():
        keyword_mask = address_lower.str.contains(keyword, na=False)
        cad_df.loc[taps_mask & keyword_mask, 'Incident'] = incident_type

    for keyword, incident_type in esu_keywords.items():
        keyword_mask = address_lower.str.contains(keyword, na=False)
        cad_df.loc[esu_mask & keyword_mask, 'Incident'] = incident_type

    # Set Response_Type to Routine for all TAPS
    all_taps = taps_mask | esu_mask
    cad_df.loc[all_taps, 'Response_Type'] = 'Routine'

    metrics['taps_resolved'] = all_taps.sum()
    print(f"  Resolved {metrics['taps_resolved']:,} TAPS variant records")

    return cad_df


def classify_domestic_disputes(cad_df, dv_df):
    """Classify Domestic Disputes using vectorized operations."""
    print("\n" + "=" * 60)
    print("CLASSIFYING DOMESTIC DISPUTES (Blocker #9)")
    print("=" * 60)

    # Get DV case numbers
    dv_cases = set()
    if 'Case_Number' in dv_df.columns:
        dv_cases = set(dv_df['Case_Number'].dropna().astype(str).str.strip())
    elif 'Case #' in dv_df.columns:
        dv_cases = set(dv_df['Case #'].dropna().astype(str).str.strip())

    print(f"  DV report contains {len(dv_cases):,} case numbers")

    # Find Domestic Dispute records
    dispute_mask = cad_df['Incident'] == 'Domestic Dispute'

    # Check if report number is in DV cases
    has_dv_report = cad_df['ReportNumberNew'].astype(str).str.strip().isin(dv_cases)

    # Classify
    dv_mask = dispute_mask & has_dv_report
    no_dv_mask = dispute_mask & ~has_dv_report

    cad_df.loc[dv_mask, 'Incident'] = 'Domestic Violence - 2C:25-21'
    cad_df.loc[dv_mask, 'Response_Type'] = 'Emergency'

    cad_df.loc[no_dv_mask, 'Incident'] = 'Dispute'
    cad_df.loc[no_dv_mask, 'Response_Type'] = 'Urgent'

    metrics['domestic_to_dv'] = dv_mask.sum()
    metrics['domestic_to_dispute'] = no_dv_mask.sum()

    print(f"  Reclassified to Domestic Violence: {metrics['domestic_to_dv']:,}")
    print(f"  Reclassified to Dispute: {metrics['domestic_to_dispute']:,}")

    return cad_df


def split_tro_fro(cad_df, rms_df):
    """Split TRO/FRO violations using vectorized operations."""
    print("\n" + "=" * 60)
    print("SPLITTING TRO/FRO VIOLATIONS (Blocker #10)")
    print("=" * 60)

    # Build RMS narrative lookup
    rms_df['_case_key'] = rms_df['Case Number'].astype(str).str.strip()
    rms_df['_narrative_lower'] = rms_df['Narrative'].fillna('').str.lower()

    # Create lookup dataframe
    rms_lookup = rms_df[['_case_key', '_narrative_lower']].drop_duplicates(subset=['_case_key'])
    rms_lookup = rms_lookup.set_index('_case_key')

    print(f"  Built RMS lookup with {len(rms_lookup):,} entries")

    # Find TRO/FRO records
    tro_fro_patterns = [
        'Violation: TRO/ FRO  2C:25-31',
        'Violation: TRO/FRO 2C:25-31',
        'Violation TRO/FRO - 2C:25-31'
    ]

    tro_fro_mask = cad_df['Incident'].isin(tro_fro_patterns)
    tro_fro_mask = tro_fro_mask | (cad_df['Incident'].str.contains('TRO', na=False) &
                                   cad_df['Incident'].str.contains('FRO', na=False) &
                                   cad_df['Incident'].str.contains('Violation', na=False))

    if tro_fro_mask.sum() == 0:
        print("  No TRO/FRO records found")
        return cad_df

    # Get narratives for TRO/FRO records
    cad_df['_report_key'] = cad_df['ReportNumberNew'].astype(str).str.strip()
    cad_df = cad_df.merge(
        rms_lookup[['_narrative_lower']],
        left_on='_report_key',
        right_index=True,
        how='left'
    )

    # Classify based on narrative
    fro_indicators = cad_df['_narrative_lower'].str.contains('fro|final', na=False, regex=True)
    tro_indicators = cad_df['_narrative_lower'].str.contains('tro|temporary', na=False, regex=True)

    fro_mask = tro_fro_mask & fro_indicators
    tro_mask = tro_fro_mask & tro_indicators & ~fro_indicators
    manual_review_mask = tro_fro_mask & ~fro_indicators & ~tro_indicators

    cad_df.loc[fro_mask, 'Incident'] = 'Violation FRO - 2C:29-9b'
    cad_df.loc[tro_mask, 'Incident'] = 'Violation TRO - 2C:29-9b'
    cad_df.loc[fro_mask | tro_mask, 'Response_Type'] = 'Routine'

    metrics['tro_fro_split'] = (fro_mask | tro_mask).sum()
    metrics['tro_fro_manual_review'] = manual_review_mask.sum()

    print(f"  Split {metrics['tro_fro_split']:,} TRO/FRO records")
    print(f"  Records for manual review: {metrics['tro_fro_manual_review']:,}")

    # Save manual review list
    if manual_review_mask.sum() > 0:
        review_df = cad_df.loc[manual_review_mask, ['ReportNumberNew', 'Incident']].copy()
        review_file = REPORTS_DIR / "tro_fro_manual_review.csv"
        review_df.to_csv(review_file, index=False)
        print(f"  Manual review list saved to: {review_file}")

    # Clean up temp columns
    cad_df = cad_df.drop(columns=['_report_key', '_narrative_lower'], errors='ignore')

    return cad_df


def normalize_disposition(cad_df):
    """Normalize Disposition values using vectorized operations."""
    print("\n" + "=" * 60)
    print("NORMALIZING DISPOSITION VALUES")
    print("=" * 60)

    # Disposition mappings
    disposition_map = {
        'ASSISTED': 'Assisted',
        'CANCELED': 'Cancelled',
        'CANCELLED': 'Cancelled',
        'CHECKED OK': 'Checked OK',
        'CHECKED O.K.': 'Checked OK',
        'UNFOUNDED': 'Unfounded',
        'REPORT TAKEN': 'Report Taken',
        'ARREST': 'Arrest',
        'CITATION': 'Citation',
        'GONE ON ARRIVAL': 'Gone on Arrival',
        'GOA': 'Gone on Arrival',
        'UNABLE TO LOCATE': 'Unable to Locate',
        'UTL': 'Unable to Locate',
        'WARNING': 'Warning',
        'REFERRED': 'Referred',
        'DUPLICATE': 'Duplicate',
        'NO ACTION REQUIRED': 'No Action Required',
        'TRANSPORTED': 'Transported'
    }

    if 'Disposition' not in cad_df.columns:
        print("  No Disposition column found")
        return cad_df

    # Backup original
    cad_df['Disposition_Original'] = cad_df['Disposition'].copy()

    # Create uppercase version for mapping
    disp_upper = cad_df['Disposition'].fillna('').astype(str).str.strip().str.upper()

    # Apply specific mappings
    mapped = disp_upper.map(disposition_map)

    # For unmapped, apply title case
    unmapped_mask = mapped.isna() & cad_df['Disposition'].notna()
    title_cased = cad_df.loc[unmapped_mask, 'Disposition'].astype(str).str.strip().str.title()

    # Combine
    cad_df['Disposition'] = mapped.fillna(title_cased)

    # Count changes
    changed = cad_df['Disposition'] != cad_df['Disposition_Original']
    metrics['disposition_normalized'] = changed.sum()

    print(f"  Normalized {metrics['disposition_normalized']:,} disposition values")

    return cad_df


def backfill_address_from_rms(cad_df, rms_df):
    """Backfill invalid FullAddress2 values from RMS data."""
    print("\n" + "=" * 60)
    print("BACKFILLING ADDRESSES FROM RMS")
    print("=" * 60)

    # Identify invalid addresses
    def is_invalid_address(s):
        if pd.isna(s):
            return True
        s = str(s).strip()
        if not s:
            return True
        # Check if has street number (digit followed by space and letters)
        if not re.search(r'\d+\s+[A-Za-z]', s):
            return True
        return False

    invalid_mask = cad_df['FullAddress2'].apply(is_invalid_address)

    # Build RMS address lookup
    rms_valid = rms_df[rms_df['FullAddress'].notna()].copy()
    rms_valid['_case_key'] = rms_valid['Case Number'].astype(str).str.strip()
    rms_valid = rms_valid[~rms_valid['FullAddress'].apply(is_invalid_address)]

    rms_address_lookup = rms_valid[['_case_key', 'FullAddress']].drop_duplicates(subset=['_case_key'])
    rms_address_lookup = rms_address_lookup.set_index('_case_key')

    print(f"  Built RMS address lookup with {len(rms_address_lookup):,} valid addresses")

    # Backup original
    cad_df['FullAddress2_Original'] = cad_df['FullAddress2'].copy()

    # Get case keys for invalid addresses
    cad_df['_report_key'] = cad_df['ReportNumberNew'].astype(str).str.strip()

    # Merge to get RMS addresses
    cad_df = cad_df.merge(
        rms_address_lookup[['FullAddress']].rename(columns={'FullAddress': '_rms_address'}),
        left_on='_report_key',
        right_index=True,
        how='left'
    )

    # Apply backfill
    backfill_mask = invalid_mask & cad_df['_rms_address'].notna()
    cad_df.loc[backfill_mask, 'FullAddress2'] = cad_df.loc[backfill_mask, '_rms_address']

    metrics['address_backfilled'] = backfill_mask.sum()

    print(f"  Backfilled {metrics['address_backfilled']:,} addresses from RMS")

    # Clean up
    cad_df = cad_df.drop(columns=['_report_key', '_rms_address'], errors='ignore')

    return cad_df


def clean_response_type_values(cad_df):
    """Clean up garbage Response_Type values from data entry errors."""
    print("\n" + "=" * 60)
    print("CLEANING RESPONSE_TYPE VALUES")
    print("=" * 60)

    # Valid response types
    valid_types = {'Routine', 'Urgent', 'Emergency'}

    # Standardize common variations
    response_type_cleanup = {
        'routine': 'Routine',
        'routine ': 'Routine',
        'routine\n': 'Routine',
        '\nroutine': 'Routine',
        'routinez': 'Routine',
        'routinede': 'Routine',
        'routinec': 'Routine',
        'routinepdsca': 'Routine',
        'routine tot mi': 'Routine',
        'urgent': 'Urgent',
        'urgent ': 'Urgent',
        'urgentz': 'Urgent',
        'urgen': 'Urgent',
        'urgent/.': 'Urgent',
        'emergency': 'Emergency',
    }

    # Track cleanup
    cleaned = 0

    # Get current values
    current_values = cad_df['Response_Type'].fillna('').astype(str).str.strip().str.lower()

    for bad_value, good_value in response_type_cleanup.items():
        mask = current_values == bad_value.lower()
        if mask.sum() > 0:
            cad_df.loc[mask, 'Response_Type'] = good_value
            cleaned += mask.sum()

    # Clear obviously invalid values (single chars, numbers, garbage)
    invalid_mask = ~cad_df['Response_Type'].fillna('').astype(str).str.strip().isin(valid_types)
    invalid_mask = invalid_mask & cad_df['Response_Type'].notna()

    # Don't clear values that look like they might be valid variations
    current = cad_df.loc[invalid_mask, 'Response_Type'].astype(str).str.strip()
    garbage_mask = (current.str.len() <= 3) | (~current.str.contains('routine|urgent|emergency', case=False, na=False))

    cad_df.loc[invalid_mask & garbage_mask, 'Response_Type'] = np.nan

    print(f"  Cleaned {cleaned} Response_Type values")
    print(f"  Cleared {(invalid_mask & garbage_mask).sum()} garbage values")

    return cad_df


def add_data_quality_flags(cad_df):
    """Add data quality flags."""
    print("\n" + "=" * 60)
    print("ADDING DATA QUALITY FLAGS")
    print("=" * 60)

    # Initialize flag
    cad_df['data_quality_flag'] = 0

    # Flag missing Response_Type
    missing_response = cad_df['Response_Type'].isna() | (cad_df['Response_Type'].astype(str).str.strip() == '')

    # Flag missing address
    missing_address = cad_df['FullAddress2'].isna() | (cad_df['FullAddress2'].astype(str).str.strip() == '')

    # Flag missing disposition
    missing_disp = cad_df['Disposition'].isna() | (cad_df['Disposition'].astype(str).str.strip() == '')

    # Set flags
    needs_review = missing_response | missing_address | missing_disp
    cad_df.loc[needs_review, 'data_quality_flag'] = 1

    print(f"  Flagged {needs_review.sum():,} records for review")

    return cad_df


def generate_esri_export(cad_df):
    """Generate the final ESRI export file."""
    print("\n" + "=" * 60)
    print("GENERATING ESRI EXPORT")
    print("=" * 60)

    # Define output columns
    esri_columns = [
        'TimeOfCall', 'cYear', 'cMonth', 'Hour', 'DayofWeek',
        'Incident', 'Response_Type', 'How Reported',
        'FullAddress2', 'Grid', 'PDZone',
        'Officer', 'Disposition', 'ReportNumberNew',
        'Latitude', 'Longitude', 'data_quality_flag'
    ]

    # Ensure all columns exist
    for col in esri_columns:
        if col not in cad_df.columns:
            cad_df[col] = np.nan

    # Select columns
    export_df = cad_df[esri_columns].copy()

    # Generate output filename
    timestamp = datetime.now().strftime('%Y%m%d')
    output_file = OUTPUT_DIR / f"CAD_ESRI_Final_{timestamp}.xlsx"

    # Save
    print(f"  Writing {len(export_df):,} records to Excel...")
    export_df.to_excel(output_file, index=False)

    print(f"  Output file: {output_file}")
    metrics['total_records'] = len(export_df)

    return output_file, export_df


def generate_validation_report(cad_df, output_file):
    """Generate validation report."""
    print("\n" + "=" * 60)
    print("GENERATING VALIDATION REPORT")
    print("=" * 60)

    total = len(cad_df)

    # Coverage calculations
    with_response = cad_df['Response_Type'].notna() & (cad_df['Response_Type'].astype(str).str.strip() != '')
    response_coverage = (with_response.sum() / total) * 100

    quality_issues = cad_df['data_quality_flag'].sum()
    quality_score = ((total - quality_issues) / total) * 100

    # Generate report
    report_content = f"""# ESRI Production Deployment - Validation Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Output File:** {output_file}

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Records | {total:,} |
| Response_Type Coverage | {response_coverage:.2f}% |
| Data Quality Score | {quality_score:.2f}% |
| Records Needing Review | {quality_issues:,} |

## Processing Results

### Response_Type Mapping
- Records mapped: {metrics['response_type_mapped']:,}

### TAPS Variant Resolution (Blocker #8)
- Records resolved: {metrics['taps_resolved']:,}

### Domestic Dispute Classification (Blocker #9)
- Reclassified to Domestic Violence: {metrics['domestic_to_dv']:,}
- Reclassified to Dispute: {metrics['domestic_to_dispute']:,}

### TRO/FRO Splitting (Blocker #10)
- Records split: {metrics['tro_fro_split']:,}
- Records for manual review: {metrics['tro_fro_manual_review']:,}

### Disposition Normalization
- Records normalized: {metrics['disposition_normalized']:,}

### Address Backfill from RMS
- Records improved: {metrics['address_backfilled']:,}

## Response_Type Distribution

"""

    # Add distribution
    response_dist = cad_df['Response_Type'].value_counts()
    report_content += "| Response Type | Count | Percentage |\n"
    report_content += "|--------------|-------|------------|\n"
    for resp_type, count in response_dist.items():
        pct = (count / total) * 100
        report_content += f"| {resp_type} | {count:,} | {pct:.2f}% |\n"

    # Quality assessment
    report_content += f"""
## Quality Assessment

| Criteria | Status |
|----------|--------|
| Response_Type Coverage >= 99% | {'PASS' if response_coverage >= 99 else 'FAIL'} ({response_coverage:.2f}%) |
| Data Quality Score >= 95% | {'PASS' if quality_score >= 95 else 'WARNING' if quality_score >= 90 else 'FAIL'} ({quality_score:.2f}%) |

### Overall Status: {'PRODUCTION READY' if response_coverage >= 99 and quality_score >= 95 else 'NEEDS REVIEW'}

---
*Report generated by ESRI Production Deployment Script*
"""

    # Save report
    report_file = REPORTS_DIR / "esri_deployment_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"  Report saved to: {report_file}")

    return report_file


def main():
    """Main execution function."""
    print("\n" + "=" * 60)
    print("ESRI PRODUCTION DEPLOYMENT - DATA CLEANING")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Load data
        cad_df, dv_df, rms_df, mappings_df, raw_calltypes_df = load_data()

        # Build mapping
        response_map = build_response_type_mapping(mappings_df, raw_calltypes_df)

        # Apply transformations
        cad_df = apply_response_type_mapping(cad_df, response_map)
        cad_df = resolve_taps_variants(cad_df)
        cad_df = classify_domestic_disputes(cad_df, dv_df)
        cad_df = split_tro_fro(cad_df, rms_df)
        cad_df = normalize_disposition(cad_df)
        cad_df = backfill_address_from_rms(cad_df, rms_df)
        cad_df = clean_response_type_values(cad_df)
        cad_df = add_data_quality_flags(cad_df)

        # Generate output
        output_file, export_df = generate_esri_export(cad_df)
        report_file = generate_validation_report(export_df, output_file)

        print("\n" + "=" * 60)
        print("DEPLOYMENT COMPLETE")
        print("=" * 60)
        print(f"Output: {output_file}")
        print(f"Report: {report_file}")
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
