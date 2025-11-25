"""
Apply FullAddress2 Corrections to CAD Data
Applies rule-based corrections from a correction file to CAD data.

Author: Claude Code
Date: 2025-11-22
"""

import pandas as pd
import numpy as np
from collections import Counter

# ============================================================================
# CONFIGURATION
# ============================================================================

# Input files
CAD_FILE = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\test\2025_11_17_CAD_With_RMS.csv"
CORRECTIONS_FILE = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\test\updates_corrections_FullAddress2.csv"

# Output files
OUTPUT_FILE = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\test\2025_11_17_CAD_FullAddress2_AutoFixed.csv"
LOG_FILE = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\test\FullAddress2_AutoFix_Log.csv"

# ============================================================================
# LOAD AND PROCESS CORRECTION RULES
# ============================================================================

def load_correction_rules():
    """Load and process correction rules from CSV"""
    df = pd.read_csv(CORRECTIONS_FILE, encoding='utf-8-sig')

    # Column names
    incident_col = df.columns[0]  # "If Incident is"
    address_col = df.columns[1]   # "And/Or If FullAddress2 is"
    correction_col = df.columns[2]  # "Then Change FullAddress2 to"

    rules = []
    contextual_required = set()

    for idx, row in df.iterrows():
        # Skip header row if present
        if row[address_col] == 'And/Or If FullAddress2 is':
            continue

        incident_condition = row[incident_col] if pd.notna(row[incident_col]) else None
        original_address = row[address_col]
        corrected_address = row[correction_col] if pd.notna(row[correction_col]) else None

        # Skip rows with no address to match
        if pd.isna(original_address) or str(original_address).strip() == '':
            continue

        # Normalize addresses for matching
        original_address = str(original_address).strip()

        # Check if this is a contextual fix (empty correction)
        if corrected_address is None or str(corrected_address).strip() == '':
            contextual_required.add(original_address)
            continue

        corrected_address = str(corrected_address).strip()

        rules.append({
            'incident_condition': incident_condition.strip() if incident_condition else None,
            'original_address': original_address,
            'corrected_address': corrected_address
        })

    return rules, contextual_required

def find_matching_rule(incident, address, rules):
    """Find matching correction rule for given incident and address"""
    # Try to find exact match with incident condition first
    for rule in rules:
        if rule['original_address'] == address:
            if rule['incident_condition'] is None:
                # Rule applies to all incidents
                return rule['corrected_address']
            elif rule['incident_condition'] == incident:
                # Rule matches both incident and address
                return rule['corrected_address']

    # No match found
    return None

# ============================================================================
# APPLY CORRECTIONS
# ============================================================================

def apply_corrections(cad_df, rules, contextual_required):
    """Apply corrections to CAD data and generate log"""

    log_entries = []
    fix_counts = {'FIXED': 0, 'NO_MATCH': 0, 'UNFIXED_CONTEXTUAL_REQUIRED': 0}

    # Create a copy for modifications
    output_df = cad_df.copy()

    for idx, row in output_df.iterrows():
        report_num = row['ReportNumberNew']
        incident = row['Incident'] if pd.notna(row['Incident']) else ''
        original_address = row['FullAddress2'] if pd.notna(row['FullAddress2']) else ''

        # Normalize address for matching
        address_normalized = str(original_address).strip()

        # Check if this address requires contextual information
        if address_normalized in contextual_required:
            log_entries.append({
                'ReportNumberNew': report_num,
                'Original_Address': original_address,
                'New_Address': original_address,  # Keep unchanged
                'Fix_Applied': 'UNFIXED_CONTEXTUAL_REQUIRED',
                'Issue_Type': 'Incomplete intersection - no valid cross street known'
            })
            fix_counts['UNFIXED_CONTEXTUAL_REQUIRED'] += 1
            continue

        # Try to find matching correction rule
        corrected_address = find_matching_rule(incident, address_normalized, rules)

        if corrected_address:
            # Apply correction
            output_df.at[idx, 'FullAddress2'] = corrected_address
            log_entries.append({
                'ReportNumberNew': report_num,
                'Original_Address': original_address,
                'New_Address': corrected_address,
                'Fix_Applied': 'FIXED',
                'Issue_Type': 'Auto-corrected from rules file'
            })
            fix_counts['FIXED'] += 1
        else:
            # No match found
            log_entries.append({
                'ReportNumberNew': report_num,
                'Original_Address': original_address,
                'New_Address': original_address,  # Keep unchanged
                'Fix_Applied': 'NO_MATCH',
                'Issue_Type': 'No correction rule found'
            })
            fix_counts['NO_MATCH'] += 1

    return output_df, pd.DataFrame(log_entries), fix_counts

# ============================================================================
# GENERATE SUMMARY STATISTICS
# ============================================================================

def generate_summary(log_df, fix_counts, total_records):
    """Generate summary statistics"""
    print()
    print("=" * 80)
    print("FULLADDRESS2 AUTO-CORRECTION SUMMARY")
    print("=" * 80)
    print()
    print(f"Total Records Processed: {total_records:,}")
    print()
    print("Correction Results:")
    print(f"  FIXED: {fix_counts['FIXED']:,} records ({fix_counts['FIXED']/total_records*100:.1f}%)")
    print(f"  NO_MATCH: {fix_counts['NO_MATCH']:,} records ({fix_counts['NO_MATCH']/total_records*100:.1f}%)")
    print(f"  UNFIXED_CONTEXTUAL_REQUIRED: {fix_counts['UNFIXED_CONTEXTUAL_REQUIRED']:,} records ({fix_counts['UNFIXED_CONTEXTUAL_REQUIRED']/total_records*100:.1f}%)")
    print()

    # Show most common fixes
    fixed_records = log_df[log_df['Fix_Applied'] == 'FIXED']
    if len(fixed_records) > 0:
        print("Top 10 Most Common Corrections Applied:")
        correction_pairs = fixed_records.groupby(['Original_Address', 'New_Address']).size()
        top_corrections = correction_pairs.sort_values(ascending=False).head(10)
        for (orig, new), count in top_corrections.items():
            print(f"  [{count:,}x] '{orig}' -> '{new}'")
        print()

    # Show contextual required addresses
    contextual_records = log_df[log_df['Fix_Applied'] == 'UNFIXED_CONTEXTUAL_REQUIRED']
    if len(contextual_records) > 0:
        print("Addresses Requiring Contextual Information (Top 10):")
        contextual_counts = contextual_records['Original_Address'].value_counts().head(10)
        for address, count in contextual_counts.items():
            print(f"  [{count:,}x] '{address}'")
        print()

    print("=" * 80)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("=" * 80)
    print("APPLYING FULLADDRESS2 CORRECTIONS")
    print("=" * 80)
    print()

    # Load CAD data
    print(f"Loading CAD data from: {CAD_FILE}")
    cad_df = pd.read_csv(CAD_FILE, encoding='utf-8-sig')
    total_records = len(cad_df)
    print(f"  [OK] Loaded {total_records:,} records")
    print()

    # Load correction rules
    print(f"Loading correction rules from: {CORRECTIONS_FILE}")
    rules, contextual_required = load_correction_rules()
    print(f"  [OK] Loaded {len(rules):,} correction rules")
    print(f"  [OK] Identified {len(contextual_required):,} addresses requiring contextual info")
    print()

    # Apply corrections
    print("Applying corrections...")
    output_df, log_df, fix_counts = apply_corrections(cad_df, rules, contextual_required)
    print("  [OK] Corrections applied")
    print()

    # Save output file
    print(f"Saving corrected data to: {OUTPUT_FILE}")
    output_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print("  [OK] Saved corrected CAD data")
    print()

    # Save log file
    print(f"Saving correction log to: {LOG_FILE}")
    log_df.to_csv(LOG_FILE, index=False, encoding='utf-8-sig')
    print("  [OK] Saved correction log")
    print()

    # Generate summary
    generate_summary(log_df, fix_counts, total_records)

    print()
    print("CORRECTION PROCESS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
