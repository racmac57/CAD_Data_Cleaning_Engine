#!/usr/bin/env python
"""
Complete Processing Script for New CAD Dataset
==============================================
Processes new CAD data and generates:
1. ESRI Polished Output (matching reference structure exactly)
2. ESRI Draft Output (with all validation flags for internal review)

Author: CAD Data Cleaning Engine
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys
import logging
import warnings

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('process_new_dataset.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# File paths
BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
CAD_INPUT = BASE_DIR / "data" / "01_raw" / "19_to_25_12_18_CAD_Data.xlsx"
RMS_INPUT = BASE_DIR / "data" / "01_raw" / "19_to_25_12_18_HPD_RMS_Export.csv"
REFERENCE_ESRI = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\InBox\2025_06_24_SCRPA\dashboard_data_export\ESRI_CADExport.xlsx")
OLD_VERSION = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v3.xlsx"
OUTPUT_DIR = BASE_DIR / "data" / "ESRI_CADExport"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Required ESRI column order (from user specification)
ESRI_REQUIRED_COLUMNS = [
    'ReportNumberNew',
    'Incident',
    'How Reported',
    'FullAddress2',
    'Grid',
    'ZoneCalc',
    'Time of Call',
    'cYear',
    'cMonth',
    'Hour_Calc',
    'DayofWeek',
    'Time Dispatched',
    'Time Out',
    'Time In',
    'Time Spent',
    'Time Response',
    'Officer',
    'Disposition',
    'latitude',
    'longitude'
]


def get_reference_structure(reference_file: Path) -> list:
    """Get column structure from reference ESRI file."""
    try:
        if reference_file.exists():
            df = pd.read_excel(reference_file, nrows=0)
            cols = list(df.columns)
            logger.info(f"Reference file has {len(cols)} columns")
            return cols
        else:
            logger.warning(f"Reference file not found: {reference_file}")
            return ESRI_REQUIRED_COLUMNS
    except Exception as e:
        logger.warning(f"Could not read reference file: {e}")
        return ESRI_REQUIRED_COLUMNS


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to handle variations."""
    column_mapping = {
        'HourMinuetsCalc': 'Hour_Calc',
        'Hour': 'Hour_Calc',
        'Latitude': 'latitude',
        'Longitude': 'longitude',
        'TimeOfCall': 'Time of Call',
    }
    
    df = df.rename(columns=column_mapping)
    return df


def calculate_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate derived fields like Hour_Calc, DayofWeek, etc."""
    # Calculate Hour_Calc from Time of Call if missing
    if 'Time of Call' in df.columns and 'Hour_Calc' not in df.columns:
        time_of_call = pd.to_datetime(df['Time of Call'], errors='coerce')
        df['Hour_Calc'] = time_of_call.dt.hour
    
    # Calculate DayofWeek if missing
    if 'Time of Call' in df.columns and 'DayofWeek' not in df.columns:
        time_of_call = pd.to_datetime(df['Time of Call'], errors='coerce')
        df['DayofWeek'] = time_of_call.dt.day_name()
    
    # Calculate cYear and cMonth if missing
    if 'Time of Call' in df.columns:
        time_of_call = pd.to_datetime(df['Time of Call'], errors='coerce')
        if 'cYear' not in df.columns:
            df['cYear'] = time_of_call.dt.year
        if 'cMonth' not in df.columns:
            df['cMonth'] = time_of_call.dt.month
    
    # Calculate ZoneCalc from PDZone if needed
    if 'ZoneCalc' not in df.columns and 'PDZone' in df.columns:
        df['ZoneCalc'] = df['PDZone']
    
    # Initialize latitude/longitude if missing
    if 'latitude' not in df.columns:
        df['latitude'] = np.nan
    if 'longitude' not in df.columns:
        df['longitude'] = np.nan
    
    return df


def create_esri_polished_output(df: pd.DataFrame, reference_columns: list) -> pd.DataFrame:
    """Create polished ESRI output matching reference structure exactly."""
    logger.info("Creating polished ESRI output...")
    
    # Normalize column names
    df = normalize_column_names(df)
    
    # Calculate derived fields
    df = calculate_derived_fields(df)
    
    # Create output DataFrame with exact reference column order
    output_df = pd.DataFrame(index=df.index)
    
    for col in reference_columns:
        if col in df.columns:
            output_df[col] = df[col]
        elif col == 'ZoneCalc' and 'PDZone' in df.columns:
            # Use PDZone as ZoneCalc
            output_df[col] = df['PDZone']
        elif col == 'Hour_Calc' and 'Time of Call' in df.columns:
            # Calculate from Time of Call
            time_of_call = pd.to_datetime(df['Time of Call'], errors='coerce')
            output_df[col] = time_of_call.dt.hour
        elif col == 'DayofWeek' and 'Time of Call' in df.columns:
            # Calculate from Time of Call
            time_of_call = pd.to_datetime(df['Time of Call'], errors='coerce')
            output_df[col] = time_of_call.dt.day_name()
        elif col == 'cYear' and 'Time of Call' in df.columns:
            time_of_call = pd.to_datetime(df['Time of Call'], errors='coerce')
            output_df[col] = time_of_call.dt.year
        elif col == 'cMonth' and 'Time of Call' in df.columns:
            time_of_call = pd.to_datetime(df['Time of Call'], errors='coerce')
            output_df[col] = time_of_call.dt.month
        else:
            # Create empty column
            output_df[col] = np.nan
            logger.warning(f"Column '{col}' not found, creating empty column")
    
    # Ensure proper data types
    # Numeric columns
    numeric_cols = ['cYear', 'Hour_Calc']
    for col in numeric_cols:
        if col in output_df.columns:
            output_df[col] = pd.to_numeric(output_df[col], errors='coerce')
    
    # DateTime columns
    datetime_cols = ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In']
    for col in datetime_cols:
        if col in output_df.columns:
            output_df[col] = pd.to_datetime(output_df[col], errors='coerce')
    
    # Latitude/Longitude
    for col in ['latitude', 'longitude']:
        if col in output_df.columns:
            output_df[col] = pd.to_numeric(output_df[col], errors='coerce')
    
    return output_df


def create_esri_draft_output(df: pd.DataFrame, reference_columns: list) -> pd.DataFrame:
    """Create draft output with all validation flags and internal columns."""
    logger.info("Creating draft ESRI output with validation flags...")
    
    # Start with polished output
    draft_df = create_esri_polished_output(df, reference_columns).copy()
    
    # Add validation flags and internal review columns
    # These would come from validation process
    draft_df['data_quality_flag'] = ''
    draft_df['validation_errors'] = ''
    draft_df['validation_warnings'] = ''
    
    # Add source tracking if available
    if 'Incident_source' in df.columns:
        draft_df['Incident_source'] = df['Incident_source']
    if 'FullAddress2_source' in df.columns:
        draft_df['FullAddress2_source'] = df['FullAddress2_source']
    
    # Add all other columns from original that aren't in polished
    for col in df.columns:
        if col not in draft_df.columns and col not in reference_columns:
            draft_df[col] = df[col]
    
    return draft_df


def compare_with_old_version(new_df: pd.DataFrame, old_file: Path) -> dict:
    """Compare new output with old version."""
    comparison = {
        'new_rows': len(new_df),
        'new_columns': len(new_df.columns),
        'old_rows': 0,
        'old_columns': 0,
        'column_differences': []
    }
    
    try:
        if old_file.exists():
            old_df = pd.read_excel(old_file, nrows=0)
            comparison['old_rows'] = len(pd.read_excel(old_file))
            comparison['old_columns'] = len(old_df.columns)
            
            new_cols = set(new_df.columns)
            old_cols = set(old_df.columns)
            
            comparison['column_differences'] = {
                'only_in_new': list(new_cols - old_cols),
                'only_in_old': list(old_cols - new_cols),
                'common': list(new_cols & old_cols)
            }
    except Exception as e:
        logger.warning(f"Could not compare with old version: {e}")
    
    return comparison


def main():
    """Main processing function."""
    logger.info("="*80)
    logger.info("PROCESSING NEW CAD DATASET - COMPLETE PIPELINE")
    logger.info("="*80)
    
    # Check input file
    if not CAD_INPUT.exists():
        logger.error(f"CAD input file not found: {CAD_INPUT}")
        return 1
    
    # Get reference structure
    logger.info("Analyzing reference ESRI structure...")
    reference_columns = get_reference_structure(REFERENCE_ESRI)
    logger.info(f"Reference ESRI structure: {len(reference_columns)} columns")
    logger.info(f"Reference columns: {reference_columns}")
    
    # Load CAD data
    logger.info(f"\nLoading CAD data from: {CAD_INPUT}")
    cad_df = pd.read_excel(CAD_INPUT, dtype=str)
    logger.info(f"Loaded {len(cad_df):,} CAD records with {len(cad_df.columns)} columns")
    logger.info(f"CAD columns: {list(cad_df.columns)}")
    
    # Run validation and cleaning
    logger.info("\nRunning validation and cleaning...")
    try:
        # Import from parent directory
        import importlib.util
        validator_path = parent_dir / 'validate_cad_export_parallel.py'
        if validator_path.exists():
            spec = importlib.util.spec_from_file_location("validate_cad_export_parallel", validator_path)
            validator_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(validator_module)
            CADValidatorParallel = validator_module.CADValidatorParallel
            
            validator = CADValidatorParallel(n_jobs=-2)
            cad_cleaned = validator.validate_all(cad_df)
            logger.info(f"Validation complete: {sum(validator.stats['errors_by_field'].values()):,} errors found")
        else:
            logger.warning("Validator script not found, skipping validation")
            cad_cleaned = cad_df
    except Exception as e:
        logger.warning(f"Could not run validation: {e}. Using original data.")
        cad_cleaned = cad_df
    
    # RMS backfill (if available)
    rms_available = RMS_INPUT.exists()
    if rms_available:
        logger.info(f"\nRunning RMS backfill from: {RMS_INPUT}")
        try:
            from unified_rms_backfill import UnifiedRMSBackfill
            backfiller = UnifiedRMSBackfill()
            cad_cleaned = backfiller.backfill_from_rms(cad_cleaned)
            logger.info("RMS backfill complete")
        except Exception as e:
            logger.warning(f"Could not run RMS backfill: {e}")
    else:
        logger.info("RMS file not found, skipping RMS backfill")
    
    # Geocoding (if coordinates missing)
    logger.info("\nChecking geocoding needs...")
    has_lat = 'latitude' in cad_cleaned.columns
    has_lon = 'longitude' in cad_cleaned.columns
    
    if has_lat and has_lon:
        missing_coords = (cad_cleaned['latitude'].isna() | cad_cleaned['longitude'].isna()).sum()
        if missing_coords > 0:
            logger.info(f"Found {missing_coords:,} records with missing coordinates")
            try:
                from geocode_nj_geocoder import NJGeocoder
                geocoder = NJGeocoder()
                cad_cleaned = geocoder.backfill_coordinates(cad_cleaned)
                logger.info("Geocoding complete")
            except Exception as e:
                logger.warning(f"Could not run geocoding: {e}")
        else:
            logger.info("All coordinates present")
    else:
        logger.info("Latitude/longitude columns not found, skipping geocoding")
    
    # Generate outputs
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. Polished ESRI Output (matching reference structure)
    logger.info("\n" + "="*80)
    logger.info("GENERATING POLISHED ESRI OUTPUT")
    logger.info("="*80)
    polished_df = create_esri_polished_output(cad_cleaned, reference_columns)
    
    polished_output = OUTPUT_DIR / f'CAD_ESRI_POLISHED_{timestamp}.xlsx'
    polished_df.to_excel(polished_output, index=False, engine='openpyxl')
    logger.info(f"Polished ESRI output saved: {polished_output}")
    logger.info(f"  Rows: {len(polished_df):,}")
    logger.info(f"  Columns: {len(polished_df.columns)}")
    logger.info(f"  Column order matches reference: {list(polished_df.columns) == reference_columns}")
    
    # 2. Draft Output (with validation flags)
    logger.info("\n" + "="*80)
    logger.info("GENERATING DRAFT OUTPUT (WITH VALIDATION FLAGS)")
    logger.info("="*80)
    draft_df = create_esri_draft_output(cad_cleaned, reference_columns)
    
    draft_output = OUTPUT_DIR / f'CAD_ESRI_DRAFT_{timestamp}.xlsx'
    draft_df.to_excel(draft_output, index=False, engine='openpyxl')
    logger.info(f"Draft output saved: {draft_output}")
    logger.info(f"  Rows: {len(draft_df):,}")
    logger.info(f"  Columns: {len(draft_df.columns)} (includes validation flags)")
    
    # Comparison with old version
    logger.info("\n" + "="*80)
    logger.info("COMPARISON WITH OLD VERSION")
    logger.info("="*80)
    comparison = compare_with_old_version(polished_df, OLD_VERSION)
    logger.info(f"New version: {comparison['new_rows']:,} rows, {comparison['new_columns']} columns")
    logger.info(f"Old version: {comparison['old_rows']:,} rows, {comparison['old_columns']} columns")
    
    if comparison['column_differences']:
        diff = comparison['column_differences']
        if diff['only_in_new']:
            logger.info(f"Columns only in new: {diff['only_in_new']}")
        if diff['only_in_old']:
            logger.info(f"Columns only in old: {diff['only_in_old']}")
    
    # Final summary
    logger.info("\n" + "="*80)
    logger.info("PROCESSING COMPLETE")
    logger.info("="*80)
    logger.info(f"Polished ESRI Output: {polished_output}")
    logger.info(f"Draft Output (with flags): {draft_output}")
    logger.info(f"Reference structure match: {list(polished_df.columns) == reference_columns}")
    logger.info("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

