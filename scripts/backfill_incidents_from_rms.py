"""
RMS Incident Backfill Script
=============================
Author: Claude Code
Created: 2025-11-16 (EST)
Modified: 2025-11-16 (EST)

Purpose:
    Backfill null CAD Incident values using RMS data.
    Joins CAD records to RMS records by case number and fills missing
    incident types from RMS.Incident Type_1 field.

Background:
    The CAD system has 249 records with null Incident values. Many of these
    have corresponding RMS records with incident types populated. This script
    recovers those incident types by joining on case number.

Inputs:
    - CAD DataFrame with ReportNumberNew column (may have null Incidents)
    - RMS Excel files in data/rms/*.xlsx with Case Number and Incident Type_1

Outputs:
    - DataFrame with Incident column backfilled from RMS
    - Log file: data/02_reports/incident_backfill_log.csv
    - Console summary: matched, filled, still_null counts

Usage:
    from backfill_incidents_from_rms import backfill_incidents
    df = backfill_incidents(cad_df, rms_dir='data/rms')
"""

import argparse
import glob
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Tuple
import pandas as pd
import numpy as np


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


def load_rms_data(rms_dir: str, case_number_col: str = 'Case Number') -> pd.DataFrame:
    """Load and consolidate all RMS files from directory.

    Args:
        rms_dir: Directory containing RMS Excel files
        case_number_col: Name of case number column in RMS data

    Returns:
        DataFrame with consolidated RMS records
    """
    rms_files = glob.glob(os.path.join(rms_dir, '*.xlsx'))

    if not rms_files:
        print(f"⚠️  No RMS files found in {rms_dir}")
        return pd.DataFrame()

    print(f"📂 Loading {len(rms_files)} RMS file(s) from {rms_dir}")

    rms_dataframes = []
    for rms_file in rms_files:
        try:
            df = pd.read_excel(rms_file)
            print(f"   Loaded {len(df):,} records from {os.path.basename(rms_file)}")
            rms_dataframes.append(df)
        except Exception as e:
            print(f"   ⚠️  Error loading {os.path.basename(rms_file)}: {e}")
            continue

    if not rms_dataframes:
        return pd.DataFrame()

    # Consolidate all RMS data
    rms_df = pd.concat(rms_dataframes, ignore_index=True)
    print(f"   Total RMS records: {len(rms_df):,}")

    # Normalize column names
    rms_df.columns = rms_df.columns.str.strip()

    # Check for required columns
    if case_number_col not in rms_df.columns:
        print(f"   ⚠️  Warning: '{case_number_col}' column not found in RMS data")
        print(f"   Available columns: {', '.join(rms_df.columns[:10])}")
        return pd.DataFrame()

    return rms_df


def backfill_incidents(
    cad_df: pd.DataFrame,
    rms_dir: str,
    cad_case_col: str = 'ReportNumberNew',
    cad_incident_col: str = 'Incident',
    rms_case_col: str = 'Case Number',
    rms_incident_col: str = 'Incident Type_1',
    log_path: str = None
) -> Tuple[pd.DataFrame, dict]:
    """Backfill null CAD incidents using RMS data.

    Args:
        cad_df: CAD DataFrame with potential null Incident values
        rms_dir: Directory containing RMS Excel files
        cad_case_col: CAD case number column name
        cad_incident_col: CAD incident type column name
        rms_case_col: RMS case number column name
        rms_incident_col: RMS incident type column name
        log_path: Path to save backfill log CSV

    Returns:
        Tuple of (updated DataFrame, statistics dict)
    """
    print("="*60)
    print("RMS INCIDENT BACKFILL")
    print("="*60)

    # Load RMS data
    rms_df = load_rms_data(rms_dir, rms_case_col)

    if rms_df.empty:
        print("\n⚠️  No RMS data available for backfill")
        return cad_df, {'error': 'No RMS data loaded'}

    # Check for required RMS columns
    if rms_incident_col not in rms_df.columns:
        print(f"\n⚠️  RMS incident column '{rms_incident_col}' not found")
        print(f"Available columns: {', '.join(rms_df.columns[:10])}")
        return cad_df, {'error': f'Missing column {rms_incident_col}'}

    # Identify null incidents in CAD
    null_mask = cad_df[cad_incident_col].isna() | (cad_df[cad_incident_col].astype(str).str.strip() == '')
    null_count_before = null_mask.sum()

    print(f"\n📊 Initial CAD Status:")
    print(f"   Total CAD records:       {len(cad_df):,}")
    print(f"   Null incidents:          {null_count_before:,}")
    print(f"   Non-null incidents:      {(~null_mask).sum():,}")

    if null_count_before == 0:
        print("\n✅ No null incidents to backfill!")
        return cad_df, {'null_before': 0, 'filled': 0, 'null_after': 0}

    # Create RMS lookup (deduplicate by case number, keep first)
    rms_lookup = rms_df[[rms_case_col, rms_incident_col]].drop_duplicates(subset=[rms_case_col])
    rms_lookup = rms_lookup.rename(columns={
        rms_case_col: cad_case_col,
        rms_incident_col: 'RMS_Incident'
    })

    # Filter to non-null RMS incidents
    rms_lookup = rms_lookup[rms_lookup['RMS_Incident'].notna() & (rms_lookup['RMS_Incident'].astype(str).str.strip() != '')]
    print(f"\n📋 RMS Lookup:")
    print(f"   Unique RMS cases:        {len(rms_lookup):,}")

    # Join CAD to RMS
    cad_df = cad_df.copy()
    cad_df = cad_df.merge(rms_lookup, on=cad_case_col, how='left')

    # Backfill null incidents
    backfill_mask = null_mask & cad_df['RMS_Incident'].notna()
    filled_count = backfill_mask.sum()

    if filled_count > 0:
        cad_df.loc[backfill_mask, cad_incident_col] = cad_df.loc[backfill_mask, 'RMS_Incident']

    # Check remaining nulls
    null_mask_after = cad_df[cad_incident_col].isna() | (cad_df[cad_incident_col].astype(str).str.strip() == '')
    null_count_after = null_mask_after.sum()

    # Statistics
    stats = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'cad_total': len(cad_df),
        'null_before': int(null_count_before),
        'rms_available': len(rms_lookup),
        'matched': int(backfill_mask.sum()),
        'filled': int(filled_count),
        'null_after': int(null_count_after),
        'fill_rate': (filled_count / null_count_before * 100) if null_count_before > 0 else 0
    }

    print(f"\n📈 Backfill Results:")
    print(f"   RMS matches found:       {stats['matched']:,}")
    print(f"   Incidents filled:        {stats['filled']:,}")
    print(f"   Still null:              {stats['null_after']:,}")
    print(f"   Fill rate:               {stats['fill_rate']:.1f}%")

    # Create log DataFrame
    if log_path:
        log_df = pd.DataFrame({
            'CAD_CaseNumber': cad_df.loc[backfill_mask, cad_case_col],
            'Original_Incident': None,  # Was null
            'RMS_Incident': cad_df.loc[backfill_mask, 'RMS_Incident'],
            'Backfill_Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        # Ensure output directory exists
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Save log
        log_df.to_csv(log_path, index=False, encoding='utf-8-sig')
        print(f"\n💾 Backfill log saved to: {log_path}")
        stats['log_file'] = str(log_path)

    # Drop temporary RMS column
    cad_df = cad_df.drop(columns=['RMS_Incident'], errors='ignore')

    print("="*60)

    return cad_df, stats


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Backfill null CAD incidents using RMS data."
    )
    parser.add_argument(
        "--cad-file",
        required=True,
        help="Path to CAD CSV/Excel file"
    )
    parser.add_argument(
        "--rms-dir",
        default=None,
        help="Directory containing RMS Excel files (overrides config)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to save updated CAD file (defaults to <input>_backfilled.csv)"
    )
    parser.add_argument(
        "--log",
        default=None,
        help="Path to save backfill log CSV (overrides config)"
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to configuration JSON file"
    )
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Determine RMS directory
    rms_dir = args.rms_dir
    if rms_dir is None and 'paths' in config and 'rms_dir' in config['paths']:
        rms_dir = config['paths']['rms_dir']
    if rms_dir is None:
        project_root = Path(__file__).resolve().parent.parent
        rms_dir = project_root / 'data' / 'rms'

    # Determine log path
    log_path = args.log
    if log_path is None and 'paths' in config and 'output_dir' in config['paths']:
        log_path = Path(config['paths']['output_dir']) / 'incident_backfill_log.csv'
    if log_path is None:
        project_root = Path(__file__).resolve().parent.parent
        log_path = project_root / 'data' / '02_reports' / 'incident_backfill_log.csv'

    # Load CAD data
    cad_file = Path(args.cad_file)
    if not cad_file.exists():
        raise FileNotFoundError(f"CAD file not found: {cad_file}")

    print(f"📂 Loading CAD data from: {cad_file}")
    if cad_file.suffix == '.xlsx':
        cad_df = pd.read_excel(cad_file)
    else:
        cad_df = pd.read_csv(cad_file)

    # Get RMS config
    rms_config = config.get('rms', {})
    cad_case_col = rms_config.get('join_key_cad', 'ReportNumberNew')
    rms_case_col = rms_config.get('join_key_rms', 'Case Number')
    rms_incident_col = rms_config.get('incident_field', 'Incident Type_1')

    # Backfill
    updated_df, stats = backfill_incidents(
        cad_df,
        str(rms_dir),
        cad_case_col=cad_case_col,
        rms_case_col=rms_case_col,
        rms_incident_col=rms_incident_col,
        log_path=str(log_path)
    )

    # Save output
    output_path = args.output
    if output_path is None:
        output_path = cad_file.parent / f"{cad_file.stem}_backfilled.csv"

    output_path = Path(output_path)
    updated_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n💾 Updated CAD file saved to: {output_path}")

    print(f"\n✨ Backfill complete!")


if __name__ == "__main__":
    main()
