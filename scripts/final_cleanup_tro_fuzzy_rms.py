#!/usr/bin/env python
"""
Final Cleanup Script - TRO/FRO + Fuzzy Match + RMS Backfill
============================================================
Performs comprehensive data cleaning for CAD ESRI export:
1. RMS Backfill - Fill null Incidents from RMS data
2. TRO/FRO Corrections - Apply manual review corrections
3. Fuzzy Match - Match unmapped Incidents to call types

Author: Claude Code
Date: 2025-11-17
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from thefuzz import fuzz
import warnings
warnings.filterwarnings('ignore')

# Configuration
BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
DATA_DIR = BASE_DIR / "data"
REF_DIR = BASE_DIR / "ref"
REPORTS_DIR = DATA_DIR / "02_reports"

# Input files
CAD_FILE = DATA_DIR / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
TRO_FRO_FILE = REPORTS_DIR / "tro_fro_manual_review.csv"
RAW_CALLTYPE_FILE = REF_DIR / "RAW_CAD_CALL_TYPE_EXPORT.xlsx"
MASTER_MAPPING_FILE = REF_DIR / "call_types" / "CallType_Master_Mapping.csv"
RMS_FILE = DATA_DIR / "rms" / "2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx"

# Output files
OUTPUT_CAD_FILE = DATA_DIR / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"  # Production file
FUZZY_REVIEW_FILE = REPORTS_DIR / "fuzzy_review.csv"
FINAL_REPORT_FILE = REPORTS_DIR / "unmapped_final_report.md"

# Fuzzy match thresholds
AUTO_APPLY_THRESHOLD = 75
REVIEW_THRESHOLD = 70


class CleanupStats:
    """Track statistics for each cleanup step"""
    def __init__(self, total_records):
        self.total_records = total_records
        self.initial_unmapped = 0
        self.initial_null_incident = 0
        self.steps = []

    def add_step(self, name, before_unmapped, after_unmapped, details=None):
        improvement = before_unmapped - after_unmapped
        self.steps.append({
            'name': name,
            'before': before_unmapped,
            'after': after_unmapped,
            'improvement': improvement,
            'details': details or {}
        })

    def get_summary(self):
        return self.steps


def load_data():
    """Load all input files"""
    print("Loading input files...")

    # Load CAD data
    cad_df = pd.read_excel(CAD_FILE)
    print(f"  CAD ESRI: {len(cad_df):,} records")

    # Load TRO/FRO corrections
    tro_fro_df = pd.read_csv(TRO_FRO_FILE)
    print(f"  TRO/FRO corrections: {len(tro_fro_df):,} records")

    # Load RAW call types
    raw_calltype_df = pd.read_excel(RAW_CALLTYPE_FILE)
    print(f"  RAW call types: {len(raw_calltype_df):,} records")

    # Load master mapping
    master_mapping_df = pd.read_csv(MASTER_MAPPING_FILE)
    print(f"  Master mapping: {len(master_mapping_df):,} records")

    # Load RMS data
    rms_df = pd.read_excel(RMS_FILE)
    print(f"  RMS export: {len(rms_df):,} records")

    return cad_df, tro_fro_df, raw_calltype_df, master_mapping_df, rms_df


def count_unmapped(df):
    """Count records with blank/null Response_Type"""
    return df['Response_Type'].isna().sum() + (df['Response_Type'] == '').sum()


def count_null_incident(df):
    """Count records with blank/null Incident"""
    return df['Incident'].isna().sum() + (df['Incident'] == '').sum()


def step1_rms_backfill(cad_df, rms_df, stats):
    """
    Step 1: RMS Backfill - Fill null Incidents from RMS data
    Join CAD.ReportNumberNew = RMS.'Case Number'
    Fill from RMS.'Incident Type_1'
    """
    print("\n" + "="*60)
    print("STEP 1: RMS BACKFILL")
    print("="*60)

    before_null = count_null_incident(cad_df)
    before_unmapped = count_unmapped(cad_df)

    print(f"Before: {before_null:,} null Incidents, {before_unmapped:,} unmapped Response_Type")

    # Find records with null Incident
    null_incident_mask = cad_df['Incident'].isna() | (cad_df['Incident'] == '')
    null_incident_records = cad_df[null_incident_mask]['ReportNumberNew'].tolist()

    # Create RMS lookup dictionary
    rms_lookup = dict(zip(rms_df['Case Number'].astype(str), rms_df['Incident Type_1']))

    # Track backfills
    backfilled = 0
    backfill_details = []

    for idx in cad_df[null_incident_mask].index:
        report_num = str(cad_df.loc[idx, 'ReportNumberNew'])
        if report_num in rms_lookup:
            rms_incident = rms_lookup[report_num]
            if pd.notna(rms_incident) and str(rms_incident).strip():
                cad_df.loc[idx, 'Incident'] = rms_incident
                backfilled += 1
                backfill_details.append({
                    'ReportNumberNew': report_num,
                    'RMS_Incident': rms_incident
                })

    after_null = count_null_incident(cad_df)
    after_unmapped = count_unmapped(cad_df)

    print(f"After: {after_null:,} null Incidents, {after_unmapped:,} unmapped Response_Type")
    print(f"Backfilled: {backfilled:,} Incidents from RMS")

    stats.add_step('RMS Backfill', before_unmapped, after_unmapped, {
        'null_before': before_null,
        'null_after': after_null,
        'backfilled': backfilled
    })

    return cad_df, backfill_details


def step2_tro_fro_corrections(cad_df, tro_fro_df, stats):
    """
    Step 2: Apply TRO/FRO Corrections
    Join on ReportNumberNew
    Update Incident with Corrected Incident values
    """
    print("\n" + "="*60)
    print("STEP 2: TRO/FRO CORRECTIONS")
    print("="*60)

    # Guard: if the manual review file has not been populated with a
    # 'Corrected Incident' column yet, skip this step gracefully.
    expected_cols = {'ReportNumberNew', 'Corrected Incident'}
    missing = expected_cols.difference(tro_fro_df.columns)
    if missing:
        print(
            "TRO/FRO manual review file is missing expected columns "
            f"({', '.join(sorted(missing))}); skipping TRO/FRO corrections."
        )
        stats.add_step('TRO/FRO Corrections', count_unmapped(cad_df), count_unmapped(cad_df), {
            'corrections_applied': 0,
            'total_corrections': len(tro_fro_df)
        })
        return cad_df, []

    before_unmapped = count_unmapped(cad_df)

    # Create correction lookup
    correction_lookup = dict(zip(
        tro_fro_df['ReportNumberNew'].astype(str),
        tro_fro_df['Corrected Incident']
    ))

    # Apply corrections
    corrected = 0
    correction_details = []

    for report_num, corrected_incident in correction_lookup.items():
        mask = cad_df['ReportNumberNew'].astype(str) == report_num
        if mask.any():
            old_incident = cad_df.loc[mask, 'Incident'].values[0]
            cad_df.loc[mask, 'Incident'] = corrected_incident
            corrected += mask.sum()
            correction_details.append({
                'ReportNumberNew': report_num,
                'Old_Incident': old_incident,
                'New_Incident': corrected_incident
            })

    after_unmapped = count_unmapped(cad_df)

    print(f"Before: {before_unmapped:,} unmapped Response_Type")
    print(f"After: {after_unmapped:,} unmapped Response_Type")
    print(f"Applied: {corrected:,} TRO/FRO corrections")

    stats.add_step('TRO/FRO Corrections', before_unmapped, after_unmapped, {
        'corrections_applied': corrected,
        'total_corrections': len(tro_fro_df)
    })

    return cad_df, correction_details


def step3_fuzzy_match(cad_df, raw_calltype_df, master_mapping_df, stats):
    """
    Step 3: Fuzzy Match Unmapped Incidents
    For blank Response_Type:
    - First: fuzzy match Incident to RAW_CAD_CALL_TYPE_EXPORT.'Call Type'
    - Second: if no match, fuzzy to CallType_Master_Mapping.Incident_Norm
    - Log matches 70-75% for review, auto-apply 75+%
    """
    print("\n" + "="*60)
    print("STEP 3: FUZZY MATCHING")
    print("="*60)

    before_unmapped = count_unmapped(cad_df)
    print(f"Before: {before_unmapped:,} unmapped Response_Type")

    # Build lookup dictionaries
    # RAW call types: Call Type -> Response
    raw_lookup = dict(zip(
        raw_calltype_df['Call Type'].str.strip().str.upper(),
        raw_calltype_df['Response']
    ))
    raw_call_types = list(raw_lookup.keys())

    # Master mapping: Incident_Norm -> Response_Type
    master_lookup = dict(zip(
        master_mapping_df['Incident_Norm'].str.strip().str.upper(),
        master_mapping_df['Response_Type']
    ))
    master_incidents = list(master_lookup.keys())

    # Find unmapped records
    unmapped_mask = cad_df['Response_Type'].isna() | (cad_df['Response_Type'] == '')
    unmapped_indices = cad_df[unmapped_mask].index.tolist()

    print(f"Processing {len(unmapped_indices):,} unmapped records...")

    # Track matches
    auto_applied = 0
    review_needed = []
    no_match = []

    for i, idx in enumerate(unmapped_indices):
        if (i + 1) % 500 == 0:
            print(f"  Processed {i+1:,}/{len(unmapped_indices):,} records...")

        incident = cad_df.loc[idx, 'Incident']
        if pd.isna(incident) or str(incident).strip() == '':
            no_match.append({
                'ReportNumberNew': cad_df.loc[idx, 'ReportNumberNew'],
                'Incident': incident,
                'Reason': 'Null/blank Incident'
            })
            continue

        incident_upper = str(incident).strip().upper()
        report_num = cad_df.loc[idx, 'ReportNumberNew']

        # First: try RAW call types
        best_score = 0
        best_match = None
        best_response = None
        match_source = None

        for call_type in raw_call_types:
            score = fuzz.token_sort_ratio(incident_upper, call_type)
            if score > best_score:
                best_score = score
                best_match = call_type
                best_response = raw_lookup[call_type]
                match_source = 'RAW_CAD_CALL_TYPE'

        # Second: if no good match, try master mapping
        if best_score < REVIEW_THRESHOLD:
            for incident_norm in master_incidents:
                score = fuzz.token_sort_ratio(incident_upper, incident_norm)
                if score > best_score:
                    best_score = score
                    best_match = incident_norm
                    best_response = master_lookup[incident_norm]
                    match_source = 'Master_Mapping'

        # Apply or log match
        if best_score >= AUTO_APPLY_THRESHOLD:
            cad_df.loc[idx, 'Response_Type'] = best_response
            auto_applied += 1
        elif best_score >= REVIEW_THRESHOLD:
            review_needed.append({
                'ReportNumberNew': report_num,
                'Incident': incident,
                'Matched_To': best_match,
                'Response_Type': best_response,
                'Score': best_score,
                'Source': match_source
            })
        else:
            no_match.append({
                'ReportNumberNew': report_num,
                'Incident': incident,
                'Best_Match': best_match,
                'Best_Score': best_score,
                'Reason': f'Score {best_score}% below threshold'
            })

    after_unmapped = count_unmapped(cad_df)

    print(f"\nAfter: {after_unmapped:,} unmapped Response_Type")
    print(f"Auto-applied (>=75%): {auto_applied:,}")
    print(f"Needs review (70-75%): {len(review_needed):,}")
    print(f"No match (<70%): {len(no_match):,}")

    # Save review file
    if review_needed:
        review_df = pd.DataFrame(review_needed)
        review_df.to_csv(FUZZY_REVIEW_FILE, index=False)
        print(f"\nSaved fuzzy review file: {FUZZY_REVIEW_FILE}")

    stats.add_step('Fuzzy Matching', before_unmapped, after_unmapped, {
        'auto_applied': auto_applied,
        'review_needed': len(review_needed),
        'no_match': len(no_match)
    })

    return cad_df, review_needed, no_match


def step4_apply_fuzzy_to_rms_backfilled(cad_df, raw_calltype_df, master_mapping_df, backfill_details):
    """
    Apply fuzzy matching specifically to RMS-backfilled records
    """
    print("\n" + "="*60)
    print("STEP 4: FUZZY MATCH RMS-BACKFILLED RECORDS")
    print("="*60)

    if not backfill_details:
        print("No RMS-backfilled records to process")
        return cad_df

    # Build lookups
    raw_lookup = dict(zip(
        raw_calltype_df['Call Type'].str.strip().str.upper(),
        raw_calltype_df['Response']
    ))
    raw_call_types = list(raw_lookup.keys())

    master_lookup = dict(zip(
        master_mapping_df['Incident_Norm'].str.strip().str.upper(),
        master_mapping_df['Response_Type']
    ))
    master_incidents = list(master_lookup.keys())

    # Process backfilled records
    backfilled_report_nums = [d['ReportNumberNew'] for d in backfill_details]
    matched = 0

    for report_num in backfilled_report_nums:
        mask = cad_df['ReportNumberNew'].astype(str) == report_num
        if not mask.any():
            continue

        idx = cad_df[mask].index[0]
        incident = cad_df.loc[idx, 'Incident']
        response_type = cad_df.loc[idx, 'Response_Type']

        # Only process if Response_Type is still blank
        if pd.notna(response_type) and str(response_type).strip():
            continue

        if pd.isna(incident) or str(incident).strip() == '':
            continue

        incident_upper = str(incident).strip().upper()

        # Find best match
        best_score = 0
        best_response = None

        for call_type in raw_call_types:
            score = fuzz.token_sort_ratio(incident_upper, call_type)
            if score > best_score:
                best_score = score
                best_response = raw_lookup[call_type]

        if best_score < REVIEW_THRESHOLD:
            for incident_norm in master_incidents:
                score = fuzz.token_sort_ratio(incident_upper, incident_norm)
                if score > best_score:
                    best_score = score
                    best_response = master_lookup[incident_norm]

        if best_score >= AUTO_APPLY_THRESHOLD:
            cad_df.loc[idx, 'Response_Type'] = best_response
            matched += 1

    print(f"Matched {matched:,} of {len(backfill_details):,} RMS-backfilled records")

    return cad_df


def generate_final_report(cad_df, stats, review_needed, no_match):
    """
    Generate comprehensive final report for supervisor
    """
    print("\n" + "="*60)
    print("GENERATING FINAL REPORT")
    print("="*60)

    total_records = len(cad_df)
    final_unmapped = count_unmapped(cad_df)
    final_null_incident = count_null_incident(cad_df)

    # Coverage calculation
    mapped_count = total_records - final_unmapped
    coverage_pct = (mapped_count / total_records) * 100

    # Breakdown of unmapped
    unmapped_mask = cad_df['Response_Type'].isna() | (cad_df['Response_Type'] == '')
    unmapped_df = cad_df[unmapped_mask]

    # Count by reason
    null_incident_count = unmapped_df[
        unmapped_df['Incident'].isna() | (unmapped_df['Incident'] == '')
    ].shape[0]

    low_confidence_count = len(review_needed)
    no_match_count = len([
        x for x in no_match
        if 'Score' not in str(x.get('Reason', '')) or 'below' in str(x.get('Reason', ''))
    ])
    other_count = final_unmapped - null_incident_count - low_confidence_count

    # Build per-record category labels for unmapped rows
    # Categories: Null/Blank Incident, Low Confidence (70-75%), No Fuzzy Match (<70%), Other
    review_ids = {str(x.get('ReportNumberNew')) for x in review_needed}
    no_match_ids = {str(x.get('ReportNumberNew')) for x in no_match}

    def categorize_unmapped_row(row):
        report_num = str(row.get('ReportNumberNew'))
        incident_val = row.get('Incident')
        if pd.isna(incident_val) or str(incident_val).strip() == '':
            return "Null/Blank Incident"
        if report_num in review_ids:
            return "Low Confidence (70-75%)"
        if report_num in no_match_ids:
            return "No Fuzzy Match (<70%)"
        return "Other"

    unmapped_df = unmapped_df.copy()
    unmapped_df['Unmapped_Category'] = unmapped_df.apply(categorize_unmapped_row, axis=1)

    # Top 20 unmapped by frequency
    incident_freq = unmapped_df.groupby('Incident').agg({
        'ReportNumberNew': ['count', 'first']
    }).reset_index()
    incident_freq.columns = ['Incident', 'Count', 'Sample_ReportNumber']
    incident_freq = incident_freq.sort_values('Count', ascending=False).head(20)

    # Generate markdown report
    report = f"""# Final Cleanup Report - CAD Data Pipeline
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Records** | {total_records:,} |
| **Final Mapped** | {mapped_count:,} |
| **Final Unmapped** | {final_unmapped:,} |
| **Coverage Rate** | {coverage_pct:.2f}% |

## Unmapped Breakdown

| Category | Count | Description |
|----------|-------|-------------|
| Null/Blank Incident | {null_incident_count:,} | Records with no Incident value |
| Low Confidence (70-75%) | {low_confidence_count:,} | Fuzzy matches needing review |
| No Fuzzy Match (<70%) | {no_match_count:,} | No suitable match found |
| Other | {other_count:,} | Other unmapped reasons |

## Coverage Improvement by Step

| Step | Before | After | Improvement |
|------|--------|-------|-------------|
"""

    for step in stats.get_summary():
        improvement_pct = (step['improvement'] / step['before'] * 100) if step['before'] > 0 else 0
        report += f"| {step['name']} | {step['before']:,} | {step['after']:,} | -{step['improvement']:,} ({improvement_pct:.1f}%) |\n"

    # Overall improvement
    initial = stats.steps[0]['before'] if stats.steps else final_unmapped
    total_improvement = initial - final_unmapped
    total_pct = (total_improvement / initial * 100) if initial > 0 else 0
    report += f"| **Total** | {initial:,} | {final_unmapped:,} | **-{total_improvement:,} ({total_pct:.1f}%)** |\n"

    report += f"""
## Step Details

### Step 1: RMS Backfill
"""
    if stats.steps and stats.steps[0]['details']:
        details = stats.steps[0]['details']
        report += f"""- Null Incidents before: {details.get('null_before', 'N/A'):,}
- Null Incidents after: {details.get('null_after', 'N/A'):,}
- Incidents backfilled from RMS: {details.get('backfilled', 0):,}
"""

    report += f"""
### Step 2: TRO/FRO Corrections
"""
    if len(stats.steps) > 1 and stats.steps[1]['details']:
        details = stats.steps[1]['details']
        report += f"""- Total corrections in file: {details.get('total_corrections', 'N/A'):,}
- Corrections applied: {details.get('corrections_applied', 0):,}
"""

    report += f"""
### Step 3: Fuzzy Matching
"""
    if len(stats.steps) > 2 and stats.steps[2]['details']:
        details = stats.steps[2]['details']
        report += f"""- Auto-applied (>=75% confidence): {details.get('auto_applied', 0):,}
- Needs review (70-75% confidence): {details.get('review_needed', 0):,}
- No match found (<70%): {details.get('no_match', 0):,}

**Review file saved to:** `{FUZZY_REVIEW_FILE.name}`
"""

    report += f"""
## Top 20 Unmapped Incidents (by Frequency)

| Rank | Incident | Count | Sample Report# |
|------|----------|-------|----------------|
"""

    for i, row in enumerate(incident_freq.itertuples(), 1):
        incident_display = str(row.Incident)[:50] if row.Incident else "(blank)"
        report += f"| {i} | {incident_display} | {row.Count:,} | {row.Sample_ReportNumber} |\n"

    report += f"""
## Records Needing Manual Review

### Low Confidence Fuzzy Matches (70-75%)
Review file: `{FUZZY_REVIEW_FILE.name}`
- Total records: {len(review_needed):,}

These records have fuzzy matches between 70-75% confidence and should be manually validated before applying.

### Remaining Unmapped Records
- Total still unmapped: {final_unmapped:,}
- Records with null Incident: {null_incident_count:,}

## Output Files

1. **Updated CAD Export:** `{OUTPUT_CAD_FILE.name}`
   - Final Response_Type coverage: {coverage_pct:.2f}%

2. **Fuzzy Review File:** `{FUZZY_REVIEW_FILE.name}`
   - Contains {len(review_needed):,} records with 70-75% match scores

---
*Report generated by CAD Data Cleaning Engine*
"""

    # Save report
    with open(FINAL_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)

    # Export supplemental CSVs for manual review/backfill
    # 1) Summary by category (similar to Unmapped Breakdown table)
    summary_rows = [
        {
            'Category': 'Null/Blank Incident',
            'Count': null_incident_count,
            'Description': 'Records with no Incident value'
        },
        {
            'Category': 'Low Confidence (70-75%)',
            'Count': low_confidence_count,
            'Description': 'Fuzzy matches needing review'
        },
        {
            'Category': 'No Fuzzy Match (<70%)',
            'Count': no_match_count,
            'Description': 'No suitable match found'
        },
        {
            'Category': 'Other',
            'Count': other_count,
            'Description': 'Other unmapped reasons'
        },
    ]
    summary_df = pd.DataFrame(summary_rows)
    summary_path = FINAL_REPORT_FILE.with_name('unmapped_breakdown_summary.csv')
    summary_df.to_csv(summary_path, index=False)

    # 2) Detailed per-record CSV for manual backfill
    #    Includes all CAD fields for unmapped rows plus helper columns.
    detailed_df = unmapped_df.copy()
    detailed_df['Manual_Backfill_Incident'] = ''
    detailed_df['Manual_Backfill_Response_Type'] = ''
    detailed_df['Manual_Notes'] = ''
    detailed_path = FINAL_REPORT_FILE.with_name('unmapped_cases_for_manual_backfill.csv')
    detailed_df.to_csv(detailed_path, index=False)

    print(f"Report saved to: {FINAL_REPORT_FILE}")
    print(f"Unmapped breakdown summary CSV: {summary_path}")
    print(f"Unmapped cases for manual backfill CSV: {detailed_path}")

    return report


def main():
    """Main execution function"""
    print("="*60)
    print("CAD DATA FINAL CLEANUP")
    print("TRO/FRO + Fuzzy Match + RMS Backfill")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load data
    cad_df, tro_fro_df, raw_calltype_df, master_mapping_df, rms_df = load_data()

    # Initialize statistics
    stats = CleanupStats(len(cad_df))
    stats.initial_unmapped = count_unmapped(cad_df)
    stats.initial_null_incident = count_null_incident(cad_df)

    print(f"\nInitial state:")
    print(f"  Total records: {len(cad_df):,}")
    print(f"  Unmapped Response_Type: {stats.initial_unmapped:,}")
    print(f"  Null Incidents: {stats.initial_null_incident:,}")

    # OPTIMAL ORDER:
    # 1. RMS Backfill first - populates null Incidents
    # 2. TRO/FRO Corrections - fixes known issues
    # 3. Fuzzy Match - fills Response_Type based on corrected Incidents

    # Step 1: RMS Backfill
    cad_df, backfill_details = step1_rms_backfill(cad_df, rms_df, stats)

    # Step 2: TRO/FRO Corrections
    cad_df, correction_details = step2_tro_fro_corrections(cad_df, tro_fro_df, stats)

    # Step 3: Fuzzy Match
    cad_df, review_needed, no_match = step3_fuzzy_match(cad_df, raw_calltype_df, master_mapping_df, stats)

    # Step 4: Fuzzy match RMS-backfilled records specifically
    cad_df = step4_apply_fuzzy_to_rms_backfilled(cad_df, raw_calltype_df, master_mapping_df, backfill_details)

    # Generate final report
    report = generate_final_report(cad_df, stats, review_needed, no_match)

    # Save updated CAD file
    print("\n" + "="*60)
    print("SAVING OUTPUT")
    print("="*60)

    cad_df.to_excel(OUTPUT_CAD_FILE, index=False)
    print(f"Saved: {OUTPUT_CAD_FILE}")

    # Final summary
    final_unmapped = count_unmapped(cad_df)
    final_coverage = ((len(cad_df) - final_unmapped) / len(cad_df)) * 100

    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Total records: {len(cad_df):,}")
    print(f"Initial unmapped: {stats.initial_unmapped:,}")
    print(f"Final unmapped: {final_unmapped:,}")
    print(f"Improvement: {stats.initial_unmapped - final_unmapped:,} records")
    print(f"Final coverage: {final_coverage:.2f}%")
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
