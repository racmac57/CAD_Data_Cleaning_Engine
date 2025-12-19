#!/usr/bin/env python
"""
Master CAD/RMS ETL Pipeline
=============================
Orchestrates the complete data cleaning, normalization, geocoding, and ESRI output generation.

Pipeline Steps:
1. Load and validate CAD data
2. Clean and normalize data
3. Backfill from RMS (if available)
4. Geocode missing coordinates (if needed)
5. Generate draft and polished ESRI outputs

Author: CAD Data Cleaning Engine
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict
import logging
import sys
import warnings

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import pipeline components
# Add scripts directory to path
scripts_dir = Path(__file__).resolve().parent
parent_dir = scripts_dir.parent
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(parent_dir))

try:
    from unified_rms_backfill import UnifiedRMSBackfill
    from geocode_nj_geocoder import NJGeocoder
    from generate_esri_output import ESRIOutputGenerator
    # Import validator from parent directory
    import importlib.util
    validator_path = parent_dir / 'validate_cad_export_parallel.py'
    if validator_path.exists():
        spec = importlib.util.spec_from_file_location("validate_cad_export_parallel", validator_path)
        validator_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator_module)
        CADValidatorParallel = validator_module.CADValidatorParallel
    else:
        raise ImportError(f"Validator not found at {validator_path}")
except ImportError as e:
    logger.error(f"Failed to import pipeline components: {e}")
    logger.error("Make sure all required scripts are available")
    sys.exit(1)


class CADETLPipeline:
    """Master ETL pipeline for CAD/RMS data processing."""
    
    def __init__(
        self,
        config_path: str = None,
        rms_backfill: bool = True,
        geocode: bool = True,
        geocode_only_missing: bool = True
    ):
        """
        Initialize pipeline.
        
        Args:
            config_path: Path to config file (optional)
            rms_backfill: Whether to perform RMS backfill
            geocode: Whether to perform geocoding
            geocode_only_missing: Only geocode records with missing coordinates
        """
        self.base_dir = Path(__file__).resolve().parent.parent
        self.rms_backfill = rms_backfill
        self.geocode = geocode
        self.geocode_only_missing = geocode_only_missing
        
        # Initialize components
        self.validator = CADValidatorParallel(n_jobs=-2)
        self.rms_backfiller = UnifiedRMSBackfill(config_path=config_path) if rms_backfill else None
        self.geocoder = NJGeocoder() if geocode else None
        self.output_generator = ESRIOutputGenerator()
        
        # Pipeline statistics
        self.stats = {
            'start_time': None,
            'end_time': None,
            'input_rows': 0,
            'output_rows': 0,
            'validation_errors': 0,
            'rms_backfilled': 0,
            'geocoded': 0,
            'steps_completed': []
        }
    
    def run(
        self,
        input_file: Path,
        output_dir: Path = None,
        base_filename: str = 'CAD_ESRI',
        format: str = 'csv'
    ) -> Dict[str, Path]:
        """
        Run complete ETL pipeline.
        
        Args:
            input_file: Input CAD data file
            output_dir: Output directory (default: input file directory)
            base_filename: Base filename for outputs
            format: Output format ('csv' or 'excel')
            
        Returns:
            Dictionary with output file paths
        """
        self.stats['start_time'] = datetime.now()
        
        logger.info("="*80)
        logger.info("CAD/RMS ETL PIPELINE - STARTING")
        logger.info("="*80)
        logger.info(f"Input file: {input_file}")
        
        # Step 1: Load data
        logger.info("\n[STEP 1] Loading CAD data...")
        if input_file.suffix.lower() == '.csv':
            df = pd.read_csv(input_file, dtype=str, encoding='utf-8-sig')
        else:
            df = pd.read_excel(input_file, dtype=str)
        
        self.stats['input_rows'] = len(df)
        logger.info(f"  Loaded {len(df):,} records with {len(df.columns)} columns")
        self.stats['steps_completed'].append('load')
        
        # Step 2: Validate and clean
        logger.info("\n[STEP 2] Validating and cleaning data...")
        df_cleaned = self.validator.validate_all(df)
        validation_errors = sum(self.validator.stats['errors_by_field'].values())
        self.stats['validation_errors'] = validation_errors
        logger.info(f"  Validation complete: {validation_errors:,} errors found")
        logger.info(f"  Fixes applied: {sum(self.validator.stats['fixes_by_field'].values()):,}")
        self.stats['steps_completed'].append('validate')
        
        # Step 3: RMS backfill (if enabled)
        if self.rms_backfill and self.rms_backfiller:
            logger.info("\n[STEP 3] Backfilling from RMS data...")
            df_cleaned = self.rms_backfiller.backfill_from_rms(df_cleaned)
            rms_stats = self.rms_backfiller.get_stats()
            self.stats['rms_backfilled'] = sum(rms_stats['fields_backfilled'].values())
            logger.info(f"  RMS backfill complete: {self.stats['rms_backfilled']:,} fields backfilled")
            self.stats['steps_completed'].append('rms_backfill')
        else:
            logger.info("\n[STEP 3] RMS backfill skipped (disabled)")
        
        # Step 4: Geocoding (if enabled)
        if self.geocode and self.geocoder:
            logger.info("\n[STEP 4] Geocoding missing coordinates...")
            
            # Check if geocoding is needed
            has_lat = 'latitude' in df_cleaned.columns
            has_lon = 'longitude' in df_cleaned.columns
            
            if has_lat and has_lon:
                missing_coords = (
                    df_cleaned['latitude'].isna() | 
                    df_cleaned['longitude'].isna()
                ).sum()
                
                if missing_coords > 0:
                    logger.info(f"  Found {missing_coords:,} records with missing coordinates")
                    df_cleaned = self.geocoder.backfill_coordinates(df_cleaned)
                    geocode_stats = self.geocoder.get_stats()
                    self.stats['geocoded'] = geocode_stats['successful']
                    logger.info(f"  Geocoding complete: {self.stats['geocoded']:,} coordinates backfilled")
                    self.stats['steps_completed'].append('geocode')
                else:
                    logger.info("  All coordinates present, skipping geocoding")
            else:
                logger.warning("  Latitude/longitude columns not found, skipping geocoding")
        else:
            logger.info("\n[STEP 4] Geocoding skipped (disabled)")
        
        # Step 5: Generate outputs
        logger.info("\n[STEP 5] Generating ESRI outputs...")
        if output_dir is None:
            output_dir = input_file.parent
        
        outputs = self.output_generator.generate_outputs(
            df_cleaned,
            output_dir,
            base_filename=base_filename,
            format=format
        )
        self.stats['output_rows'] = len(df_cleaned)
        self.stats['steps_completed'].append('output')
        
        # Final summary
        self.stats['end_time'] = datetime.now()
        elapsed = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info("\n" + "="*80)
        logger.info("PIPELINE COMPLETE")
        logger.info("="*80)
        logger.info(f"Processing time: {elapsed:.2f} seconds")
        logger.info(f"Input records:   {self.stats['input_rows']:,}")
        logger.info(f"Output records:   {self.stats['output_rows']:,}")
        logger.info(f"Validation errors: {self.stats['validation_errors']:,}")
        logger.info(f"RMS backfilled:   {self.stats['rms_backfilled']:,} fields")
        logger.info(f"Geocoded:         {self.stats['geocoded']:,} coordinates")
        logger.info(f"\nOutput files:")
        logger.info(f"  Draft:   {outputs['draft']}")
        logger.info(f"  Polished: {outputs['polished']}")
        logger.info("="*80)
        
        return outputs
    
    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        return self.stats.copy()


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Master CAD/RMS ETL Pipeline'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input CAD CSV/Excel file path'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory (default: same as input file)'
    )
    parser.add_argument(
        '--base-filename',
        type=str,
        default='CAD_ESRI',
        help='Base filename for outputs (default: CAD_ESRI)'
    )
    parser.add_argument(
        '--no-rms-backfill',
        action='store_true',
        help='Skip RMS backfill step'
    )
    parser.add_argument(
        '--no-geocode',
        action='store_true',
        help='Skip geocoding step'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['csv', 'excel'],
        default='csv',
        help='Output format (default: csv)'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to config_enhanced.json (optional)'
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = CADETLPipeline(
        config_path=args.config,
        rms_backfill=not args.no_rms_backfill,
        geocode=not args.no_geocode
    )
    
    # Run pipeline
    input_path = Path(args.input)
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    try:
        outputs = pipeline.run(
            input_path,
            output_dir=output_dir,
            base_filename=args.base_filename,
            format=args.format
        )
        
        print("\n✅ Pipeline completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

