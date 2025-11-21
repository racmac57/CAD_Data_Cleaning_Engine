"""
Response Type Coverage Audit Script
====================================
Author: Claude Code
Created: 2025-11-16 (EST)
Modified: 2025-11-16 (EST)

Purpose:
    Audit which CAD call type variants have Response_Type mappings defined.
    Compares raw CAD export incident types against CallType_Categories lookup
    to identify gaps in the Response_Type taxonomy.

Inputs:
    - ref/RAW_CAD_CALL_TYPE_EXPORT.xlsx: Raw CAD call type variants export
    - ref/call_types/CallType_Categories.xlsx: Master call type mapping with Response_Type

Outputs:
    - ref/response_type_gaps.csv: Incident types missing Response_Type mappings
    - Console summary: X/505 variants have Response_Type coverage

Usage:
    python scripts/audit_response_type_coverage.py
    python scripts/audit_response_type_coverage.py --config config/config_enhanced.json
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
import pandas as pd


def load_config(config_path: str = None) -> dict:
    """Load configuration from JSON file.

    Args:
        config_path: Path to config JSON file. If None, uses default location.

    Returns:
        dict: Configuration dictionary with expanded paths.
    """
    if config_path is None:
        script_dir = Path(__file__).resolve().parent
        config_path = script_dir.parent / 'config' / 'config_enhanced.json'

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Expand path templates
    if 'paths' in config:
        paths = config['paths'].copy()
        max_iterations = 10
        for _ in range(max_iterations):
            changed = False
            for key, value in paths.items():
                if isinstance(value, str) and '{' in value:
                    for ref_key, ref_value in paths.items():
                        if '{' + ref_key + '}' in value and '{' not in ref_value:
                            paths[key] = value.replace('{' + ref_key + '}', ref_value)
                            changed = True
            if not changed:
                break
        config['paths'] = paths

    return config


def audit_response_type_coverage(
    raw_export_path: str,
    categories_path: str,
    output_path: str
) -> dict:
    """Audit Response_Type coverage across CAD call type variants.

    Args:
        raw_export_path: Path to RAW_CAD_CALL_TYPE_EXPORT.xlsx
        categories_path: Path to CallType_Categories.xlsx
        output_path: Path to output gaps CSV

    Returns:
        dict: Summary statistics
    """
    print(f"📊 Auditing Response_Type coverage...")
    print(f"   Raw export: {raw_export_path}")
    print(f"   Categories: {categories_path}")

    # Load raw CAD export (contains all variant incident types)
    raw_df = pd.read_excel(raw_export_path)
    print(f"   Loaded {len(raw_df):,} raw call type records")

    # Get unique incident types from raw export
    # Try multiple possible column names
    incident_col = None
    for possible_name in ['Call Type', 'Incident', 'CallType', 'Call_Type']:
        if possible_name in raw_df.columns:
            incident_col = possible_name
            break

    if incident_col is None:
        # Fallback: search for columns containing 'incident' or 'call'
        possible_cols = [col for col in raw_df.columns if 'incident' in col.lower() or 'call' in col.lower()]
        if possible_cols:
            incident_col = possible_cols[0]
        else:
            raise ValueError(f"Cannot find incident/call type column in {raw_export_path}")

    raw_incidents = set(raw_df[incident_col].dropna().unique())
    print(f"   Found {len(raw_incidents):,} unique incident types in raw export (column: {incident_col})")

    # Load CallType_Categories mapping
    cat_df = pd.read_excel(categories_path)
    print(f"   Loaded {len(cat_df):,} category mapping records")

    # Normalize column names
    cat_df.columns = cat_df.columns.str.strip()

    # Find incident column in categories file
    cat_incident_col = None
    for possible_name in ['Call Type', 'Incident', 'CallType', 'Call_Type']:
        if possible_name in cat_df.columns:
            cat_incident_col = possible_name
            break

    if cat_incident_col is None:
        raise ValueError(f"Cannot find call type column in {categories_path}. Available: {list(cat_df.columns)}")

    # Find response type column
    response_col = None
    for possible_name in ['Response', 'Response_Type', 'Response Type', 'ResponseType']:
        if possible_name in cat_df.columns:
            response_col = possible_name
            break

    if response_col is None:
        raise ValueError(f"Cannot find response type column in {categories_path}. Available: {list(cat_df.columns)}")

    print(f"   Using columns: '{cat_incident_col}' and '{response_col}'")

    # Get incidents with Response defined (non-null, non-empty)
    cat_df[response_col] = cat_df[response_col].astype(str).str.strip()
    mapped_df = cat_df[cat_df[response_col].notna() & (cat_df[response_col] != '') & (cat_df[response_col] != 'nan')]
    mapped_incidents = set(mapped_df[cat_incident_col].dropna().unique())

    print(f"   Found {len(mapped_incidents):,} call types with {response_col} defined")

    # Identify gaps (incidents in raw export but missing Response_Type)
    unmapped_incidents = raw_incidents - mapped_incidents
    print(f"   Found {len(unmapped_incidents):,} incidents WITHOUT Response_Type")

    # Create gaps DataFrame
    gaps_df = pd.DataFrame({
        'Call_Type': sorted(unmapped_incidents),
        'Status': 'MISSING_RESPONSE_TYPE',
        'Audit_Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

    # Add frequency counts from raw export
    freq_counts = raw_df[incident_col].value_counts().to_dict()
    gaps_df['Call_Frequency'] = gaps_df['Call_Type'].map(freq_counts).fillna(0).astype(int)

    # Sort by frequency (most common unmapped types first)
    gaps_df = gaps_df.sort_values('Call_Frequency', ascending=False)

    # Save gaps to CSV
    gaps_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ Gaps report saved to: {output_path}")

    # Summary statistics
    total_variants = len(raw_incidents)
    mapped_count = len(mapped_incidents)
    unmapped_count = len(unmapped_incidents)
    coverage_pct = (mapped_count / total_variants * 100) if total_variants > 0 else 0

    summary = {
        'total_variants': total_variants,
        'mapped_count': mapped_count,
        'unmapped_count': unmapped_count,
        'coverage_percent': coverage_pct,
        'gaps_file': output_path
    }

    print("\n" + "="*60)
    print("RESPONSE TYPE COVERAGE SUMMARY")
    print("="*60)
    print(f"Total incident variants:     {total_variants:,}")
    print(f"With Response_Type defined:  {mapped_count:,}")
    print(f"Missing Response_Type:       {unmapped_count:,}")
    print(f"Coverage:                    {coverage_pct:.1f}%")
    print("="*60)

    if unmapped_count > 0:
        print("\nTop 10 most frequent unmapped call types:")
        print(gaps_df[['Call_Type', 'Call_Frequency']].head(10).to_string(index=False))

    return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Audit Response_Type coverage across CAD call type variants."
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to configuration JSON file"
    )
    parser.add_argument(
        "--raw-export",
        default=None,
        help="Path to RAW_CAD_CALL_TYPE_EXPORT.xlsx (overrides config)"
    )
    parser.add_argument(
        "--categories",
        default=None,
        help="Path to CallType_Categories.xlsx (overrides config)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to output gaps CSV (overrides config)"
    )
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Determine paths (command-line args take precedence)
    project_root = Path(__file__).resolve().parent.parent

    # Raw export path
    raw_export = args.raw_export
    if raw_export is None:
        raw_export = project_root / 'ref' / 'RAW_CAD_CALL_TYPE_EXPORT.xlsx'

    # Categories path
    categories = args.categories
    if categories is None and 'paths' in config and 'calltype_categories' in config['paths']:
        categories = config['paths']['calltype_categories']
    if categories is None:
        categories = project_root / 'ref' / 'call_types' / 'CallType_Categories.xlsx'

    # Output path
    output = args.output
    if output is None:
        output = project_root / 'ref' / 'response_type_gaps.csv'

    # Run audit
    summary = audit_response_type_coverage(
        str(raw_export),
        str(categories),
        str(output)
    )

    print(f"\n✨ Audit complete!")


if __name__ == "__main__":
    main()
