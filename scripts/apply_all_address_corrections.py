#!/usr/bin/env python3
"""
Apply all address corrections to ESRI export file.

This script:
1. Loads conditional rules from updates_corrections_FullAddress2.csv
2. Loads manual corrections from final_address_manual_corrections CSV
3. Applies both to the ESRI export file
4. Creates a backup before updating
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys

BASE_DIR = Path(__file__).parent.parent

# File paths
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected.xlsx"
RULES_FILE = BASE_DIR / "test" / "updates_corrections_FullAddress2.csv"
MANUAL_CORRECTIONS_FILE = BASE_DIR / "data" / "02_reports" / "final_address_manual_corrections_20251124_222705.csv"
OUTPUT_DIR = BASE_DIR / "data" / "ESRI_CADExport"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_conditional_rules():
    """Load conditional rules from CSV."""
    print("\nLoading conditional rules...")
    df = pd.read_csv(RULES_FILE, encoding='utf-8-sig')
    
    # Column names
    incident_col = df.columns[0]  # "If Incident is"
    address_col = df.columns[1]   # "And/Or If FullAddress2 is"
    correction_col = df.columns[2]  # "Then Change FullAddress2 to"
    
    rules = []
    
    for idx, row in df.iterrows():
        # Skip header row if present
        if pd.isna(row[address_col]) or str(row[address_col]).strip() == 'And/Or If FullAddress2 is':
            continue
        
        incident_condition = row[incident_col] if pd.notna(row[incident_col]) else None
        original_address = row[address_col]
        corrected_address = row[correction_col] if pd.notna(row[correction_col]) else None
        
        # Skip rows with no address to match or no correction
        if pd.isna(original_address) or str(original_address).strip() == '':
            continue
        if pd.isna(corrected_address) or str(corrected_address).strip() == '':
            continue
        
        original_address = str(original_address).strip()
        corrected_address = str(corrected_address).strip()
        
        rules.append({
            'incident_condition': incident_condition.strip() if incident_condition else None,
            'original_address': original_address,
            'corrected_address': corrected_address
        })
    
    print(f"  Loaded {len(rules):,} conditional rules")
    return rules

def load_manual_corrections():
    """Load manual corrections from CSV."""
    print("\nLoading manual corrections...")
    df = pd.read_csv(MANUAL_CORRECTIONS_FILE, encoding='utf-8-sig')
    
    # Column names
    current_col = df.columns[0]  # "CurrentAddress"
    corrected_col = df.columns[1]  # "Corrected Streets"
    
    corrections = {}
    
    for idx, row in df.iterrows():
        current_address = row[current_col]
        corrected_address = row[corrected_col]
        
        # Skip rows with no current address or no correction
        if pd.isna(current_address) or str(current_address).strip() == '':
            continue
        if pd.isna(corrected_address) or str(corrected_address).strip() == '':
            continue
        
        current_address = str(current_address).strip()
        corrected_address = str(corrected_address).strip()
        
        # Use current address as key (normalize for matching)
        corrections[current_address] = corrected_address
    
    print(f"  Loaded {len(corrections):,} manual corrections")
    return corrections

def apply_conditional_rules(df, rules):
    """Apply conditional rules to dataframe."""
    print("\nApplying conditional rules...")
    
    # Create backup column
    df['FullAddress2_Original'] = df['FullAddress2'].copy()
    
    corrections_applied = 0
    
    # Deduplicate rules (keep first occurrence)
    seen_rules = set()
    unique_rules = []
    for rule in rules:
        rule_key = (rule['original_address'], rule['incident_condition'], rule['corrected_address'])
        if rule_key not in seen_rules:
            seen_rules.add(rule_key)
            unique_rules.append(rule)
    
    print(f"  Deduplicated from {len(rules):,} to {len(unique_rules):,} unique rules")
    
    for rule in unique_rules:
        # Build mask for matching records
        address_match = df['FullAddress2'].astype(str).str.strip() == rule['original_address']
        
        if rule['incident_condition']:
            # Rule has incident condition - match both address and incident
            incident_match = df['Incident'].astype(str).str.strip() == rule['incident_condition']
            mask = address_match & incident_match
        else:
            # Rule applies to all incidents - just match address
            mask = address_match
        
        # Only apply if address doesn't already match corrected value
        if mask.any():
            already_corrected = (df.loc[mask, 'FullAddress2'].astype(str).str.strip() == rule['corrected_address']).sum()
            needs_correction = mask.sum() - already_corrected
            
            if needs_correction > 0:
                # Only update records that need correction
                df.loc[mask & (df['FullAddress2'].astype(str).str.strip() != rule['corrected_address']), 'FullAddress2'] = rule['corrected_address']
                corrections_applied += needs_correction
    
    print(f"  Applied {corrections_applied:,} conditional rule corrections")
    return df, corrections_applied

def apply_manual_corrections(df, corrections):
    """Apply manual corrections to dataframe."""
    print("\nApplying manual corrections...")
    
    corrections_applied = 0
    
    # Create normalized address column for matching
    df['_address_normalized'] = df['FullAddress2'].astype(str).str.strip()
    
    # Apply corrections using map
    df['_corrected_address'] = df['_address_normalized'].map(corrections)
    
    # Update where correction found AND address doesn't already match corrected value
    mask = df['_corrected_address'].notna()
    
    if mask.any():
        # Only update records where current address != corrected address
        needs_correction = mask & (df['_address_normalized'] != df['_corrected_address'])
        count = needs_correction.sum()
        
        if count > 0:
            df.loc[needs_correction, 'FullAddress2'] = df.loc[needs_correction, '_corrected_address']
            corrections_applied = count
    
    # Clean up temp column
    df = df.drop(columns=['_address_normalized', '_corrected_address'])
    
    print(f"  Applied {corrections_applied:,} manual corrections")
    return df, corrections_applied

def main():
    """Main execution function."""
    print("=" * 80)
    print("Apply All Address Corrections")
    print("=" * 80)
    
    # Load ESRI file
    print(f"\nLoading ESRI file: {ESRI_FILE.name}")
    if not ESRI_FILE.exists():
        print(f"ERROR: File not found: {ESRI_FILE}")
        return
    
    try:
        df = pd.read_excel(ESRI_FILE, dtype=str)
        print(f"Loaded {len(df):,} records")
    except Exception as e:
        print(f"Error loading ESRI file: {e}")
        return
    
    # Load rules and corrections
    rules = load_conditional_rules()
    manual_corrections = load_manual_corrections()
    
    # Apply corrections (conditional rules first, then manual)
    df, conditional_count = apply_conditional_rules(df, rules)
    df, manual_count = apply_manual_corrections(df, manual_corrections)
    
    # Create backup BEFORE removing the original column
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = OUTPUT_DIR / f"CAD_ESRI_Final_{timestamp}_pre_address_corrections_backup.xlsx"
    print(f"\nCreating backup: {backup_file.name}")
    
    # Save full backup with original address column
    backup_df = df.copy()
    backup_df['FullAddress2'] = backup_df['FullAddress2_Original']
    backup_df = backup_df.drop(columns=['FullAddress2_Original'], errors='ignore')
    backup_df.to_excel(backup_file, index=False, engine='openpyxl')
    
    # Remove backup column before saving updated file
    df = df.drop(columns=['FullAddress2_Original'], errors='ignore')
    
    # Save updated file
    print(f"\nSaving updated file: {ESRI_FILE.name}")
    df.to_excel(ESRI_FILE, index=False, engine='openpyxl')
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total records processed: {len(df):,}")
    print(f"Conditional rule corrections: {conditional_count:,}")
    print(f"Manual corrections: {manual_count:,}")
    print(f"Total corrections applied: {conditional_count + manual_count:,}")
    print(f"\nUpdated file: {ESRI_FILE}")
    print(f"Backup file: {backup_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()

