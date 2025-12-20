#!/usr/bin/env python
"""
Process New CAD/RMS Dataset and Generate ESRI Outputs
======================================================
Processes the updated dataset and generates:
1. ESRI Polished Output (matching reference structure)
2. ESRI Draft Output (with validation flags for internal review)

Author: CAD Data Cleaning Engine
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys
import logging

# Add scripts directory to path
scripts_dir = Path(__file__).resolve().parent
parent_dir = scripts_dir.parent
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(parent_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# File paths
BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
CAD_INPUT = BASE_DIR / "data" / "01_raw" / "19_to_25_12_18_CAD_Data.xlsx"
RMS_INPUT = BASE_DIR / "data" / "01_raw" / "19_to_25_12_18_HPD_RMS_Export.csv"
REFERENCE_ESRI = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\InBox\2025_06_24_SCRPA\dashboard_data_export\ESRI_CADExport.xlsx")
OLD_VERSION = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v3.xlsx"
OUTPUT_DIR = BASE_DIR / "data" / "ESRI_CADExport"

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
        df = pd.read_excel(reference_file, nrows=0)
        return list(df.columns)
    except Exception as e:
        logger.warning(f"Could not read reference file: {e}")
        return ESRI_REQUIRED_COLUMNS


def get_old_version_structure(old_file: Path) -> dict:
    """Get structure from old processed version."""
    try:
        df = pd.read_excel(old_file, nrows=0)
        return {
            'columns': list(df.columns),
            'total_columns': len(df.columns),
            'esri_columns': [c for c in df.columns if c not in ['data_quality_flag', 'ReportNumberNew_str', 'join_key'] and not c.startswith('Address_') and not c.startswith('RMS_') and not c.startswith('Addr_') and not c.startswith('Word_') and not c.startswith('Has_') and not c.startswith('Is_') and not c.startswith('Contains_') and not c.startswith('Digit_') and not c.startswith('Comma_')]
        }
    except Exception as e:
        logger.warning(f"Could not read old version: {e}")
        return {}


def load_cad_data(cad_file: Path) -> pd.DataFrame:
    """Load CAD data from Excel file."""
    logger.info(f"Loading CAD data from: {cad_file}")
    df = pd.read_excel(cad_file, dtype=str)
    logger.info(f"Loaded {len(df):,} CAD records with {len(df.columns)} columns")
    return df


def load_rms_data(rms_file: Path) -> pd.DataFrame:
    """Load RMS data from CSV file."""
    logger.info(f"Loading RMS data from: {rms_file}")
    df = pd.read_csv(rms_file, dtype=str, encoding='utf-8-sig')
    logger.info(f"Loaded {len(df):,} RMS records with {len(df.columns)} columns")
    return df


def map_columns_to_reference(df: pd.DataFrame, reference_columns: list) -> pd.DataFrame:
    """Map and reorder columns to match reference structure."""
    logger.info("Mapping columns to reference structure...")
    
    # Column mapping (handle variations in column names)
    column_mapping = {
        'TimeOfCall': 'Time of Call',
        'TimeOfCall': 'Time of Call',
        'Hour': 'Hour_Calc',
        'Latitude': 'latitude',
        'Longitude': 'longitude',
        'PDZone': 'ZoneCalc',  # ZoneCalc may be same as PDZone
    }
    
    # Rename columns
    df = df.rename(columns=column_mapping)
    
    # Create output DataFrame with reference column order
    output_df = pd.DataFrame(index=df.index)
    
    for col in reference_columns:
        if col in df.columns:
            output_df[col] = df[col]
        elif col == 'ZoneCalc' and 'PDZone' in df.columns:
            # Use PDZone as ZoneCalc
            output_df[col] = df['PDZone']
        else:
            # Create empty column
            output_df[col] = np.nan
            logger.warning(f"Column '{col}' not found, creating empty column")
    
    return output_df


def main():
    """Main processing function."""
    logger.info("="*80)
    logger.info("PROCESSING NEW CAD/RMS DATASET")
    logger.info("="*80)
    
    # Check input files
    if not CAD_INPUT.exists():
        logger.error(f"CAD input file not found: {CAD_INPUT}")
        return 1
    
    if not RMS_INPUT.exists():
        logger.warning(f"RMS input file not found: {RMS_INPUT} - continuing without RMS backfill")
        rms_available = False
    else:
        rms_available = True
    
    # Get reference structure
    logger.info("Analyzing reference ESRI structure...")
    try:
        reference_columns = get_reference_structure(REFERENCE_ESRI)
        logger.info(f"Reference ESRI has {len(reference_columns)} columns")
        logger.info(f"Reference columns: {reference_columns[:10]}...")
    except Exception as e:
        logger.warning(f"Could not read reference file, using default structure: {e}")
        reference_columns = ESRI_REQUIRED_COLUMNS
    
    # Get old version structure for comparison
    old_structure = get_old_version_structure(OLD_VERSION)
    if old_structure:
        logger.info(f"Old version has {old_structure['total_columns']} columns ({len(old_structure['esri_columns'])} ESRI columns)")
    
    # Load CAD data
    cad_df = load_cad_data(CAD_INPUT)
    
    # Import pipeline components
    try:
        from master_pipeline import CADETLPipeline
        logger.info("Using master pipeline for processing...")
        
        # Initialize pipeline
        pipeline = CADETLPipeline(
            rms_backfill=rms_available,
            geocode=True,
            geocode_only_missing=True
        )
        
        # Run pipeline
        timestamp = datetime.now().strftime('%Y%m%d')
        outputs = pipeline.run(
            CAD_INPUT,
            output_dir=OUTPUT_DIR,
            base_filename=f'CAD_ESRI_{timestamp}',
            format='excel'
        )
        
        logger.info("Pipeline completed successfully!")
        logger.info(f"Draft output: {outputs['draft']}")
        logger.info(f"Polished output: {outputs['polished']}")
        
        # Now adjust polished output to match reference structure
        logger.info("Adjusting polished output to match reference structure...")
        polished_df = pd.read_excel(outputs['polished'])
        
        # Map to reference structure
        final_esri_df = map_columns_to_reference(polished_df, reference_columns)
        
        # Save final ESRI output
        final_output = OUTPUT_DIR / f'CAD_ESRI_FINAL_{timestamp}.xlsx'
        final_esri_df.to_excel(final_output, index=False, engine='openpyxl')
        logger.info(f"Final ESRI output saved: {final_output}")
        
        # Comparison report
        logger.info("\n" + "="*80)
        logger.info("COMPARISON SUMMARY")
        logger.info("="*80)
        logger.info(f"Reference columns: {len(reference_columns)}")
        logger.info(f"Final output columns: {len(final_esri_df.columns)}")
        logger.info(f"Match: {'YES' if list(final_esri_df.columns) == reference_columns else 'NO'}")
        
        if list(final_esri_df.columns) != reference_columns:
            missing = set(reference_columns) - set(final_esri_df.columns)
            extra = set(final_esri_df.columns) - set(reference_columns)
            if missing:
                logger.warning(f"Missing columns: {missing}")
            if extra:
                logger.warning(f"Extra columns: {extra}")
        
        return 0
        
    except ImportError as e:
        logger.error(f"Could not import pipeline components: {e}")
        logger.info("Falling back to manual processing...")
        # Fallback processing would go here
        return 1


if __name__ == "__main__":
    sys.exit(main())

