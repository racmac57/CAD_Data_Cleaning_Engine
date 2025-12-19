#!/usr/bin/env python3
"""Analyze why so many corrections were applied."""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Load files
esri_file = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251124_corrected.xlsx"
rules_file = BASE_DIR / "test" / "updates_corrections_FullAddress2.csv"
manual_file = BASE_DIR / "data" / "02_reports" / "final_address_manual_corrections_20251124_222705.csv"

print("=" * 80)
print("ANALYZING CORRECTION ISSUE")
print("=" * 80)

# Load data
df = pd.read_excel(esri_file, dtype=str)
rules = pd.read_csv(rules_file, encoding='utf-8-sig')
manual = pd.read_csv(manual_file, encoding='utf-8-sig')

print(f"\nTotal ESRI records: {len(df):,}")
print(f"Total rules: {len(rules):,}")
print(f"Total manual corrections: {len(manual):,}")

# Check how many records match each rule
print("\n" + "=" * 80)
print("CHECKING RULE MATCHES")
print("=" * 80)

total_matches = 0
for idx, rule in rules.iterrows():
    if pd.isna(rule['And/Or If FullAddress2 is']) or str(rule['And/Or If FullAddress2 is']).strip() == 'And/Or If FullAddress2 is':
        continue
    
    original = str(rule['And/Or If FullAddress2 is']).strip()
    corrected = str(rule['Then Change FullAddress2 to']).strip() if pd.notna(rule['Then Change FullAddress2 to']) else None
    
    if not original or not corrected:
        continue
    
    # Check matches
    address_match = df['FullAddress2'].astype(str).str.strip() == original
    
    if pd.notna(rule['If Incident is']):
        incident_match = df['Incident'].astype(str).str.strip() == str(rule['If Incident is']).strip()
        mask = address_match & incident_match
    else:
        mask = address_match
    
    count = mask.sum()
    if count > 0:
        # Check if they're already corrected
        already_corrected = (df.loc[mask, 'FullAddress2'].astype(str).str.strip() == corrected).sum()
        needs_correction = count - already_corrected
        
        print(f"\nRule {idx}: {original[:50]}...")
        print(f"  Matches: {count:,}")
        print(f"  Already corrected: {already_corrected:,}")
        print(f"  Needs correction: {needs_correction:,}")
        
        total_matches += count

print(f"\nTotal rule matches: {total_matches:,}")

# Check manual corrections
print("\n" + "=" * 80)
print("CHECKING MANUAL CORRECTION MATCHES")
print("=" * 80)

manual_corrections = {}
for idx, row in manual.iterrows():
    current = str(row['CurrentAddress']).strip() if pd.notna(row['CurrentAddress']) else None
    corrected = str(row['Corrected Streets']).strip() if pd.notna(row['Corrected Streets']) else None
    
    if current and corrected:
        manual_corrections[current] = corrected

print(f"Valid manual corrections: {len(manual_corrections):,}")

manual_matches = 0
for current, corrected in list(manual_corrections.items())[:10]:  # Check first 10
    matches = (df['FullAddress2'].astype(str).str.strip() == current).sum()
    if matches > 0:
        print(f"\n{current[:50]}...")
        print(f"  Matches: {matches:,}")
        manual_matches += matches

print(f"\nSample manual matches: {manual_matches:,}")

# Check for duplicate rules
print("\n" + "=" * 80)
print("CHECKING FOR DUPLICATE RULES")
print("=" * 80)

rule_addresses = {}
for idx, rule in rules.iterrows():
    if pd.isna(rule['And/Or If FullAddress2 is']) or str(rule['And/Or If FullAddress2 is']).strip() == 'And/Or If FullAddress2 is':
        continue
    
    original = str(rule['And/Or If FullAddress2 is']).strip()
    if original in rule_addresses:
        print(f"DUPLICATE RULE: {original[:50]}...")
        print(f"  First occurrence: row {rule_addresses[original]}")
        print(f"  Second occurrence: row {idx}")
    else:
        rule_addresses[original] = idx

print(f"\nUnique rule addresses: {len(rule_addresses):,}")

