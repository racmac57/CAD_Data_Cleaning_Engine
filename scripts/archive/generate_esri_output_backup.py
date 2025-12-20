#!/usr/bin/env python
"""
ESRI Output Generator - Draft and Polished Outputs
===================================================
Generates two outputs:
1. Draft Output: All cleaned data with validation flags and internal review columns
2. Polished ESRI Output: Final validated data with strict column order for ArcGIS Pro

Required ESRI Column Order:
ReportNumberNew, Incident, How Reported, FullAddress2, Grid, ZoneCalc, 
Time of Call, cYear, cMonth, Hour_Calc, DayofWeek, Time Dispatched, 
Time Out, Time In, Time Spent, Time Response, Officer, Disposition, 
latitude, longitude

Author: CAD Data Cleaning Engine
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
import logging
import warnings

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Required ESRI column order (exact as specified)
ESRI_REQUIRED_COLUMNS = [
    'ReportNumberNew',
    'Incident',
    'How Reported',
    'FullAddress2',
    'Grid',
    'ZoneCalc',  # Note: May be same as PDZone or calculated
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

# Internal validation columns to exclude from polished output
INTERNAL_COLUMNS = {
    # Validation flags
    'data_quality_flag',
    'validation_errors',
    'validation_warnings',
    # Source tracking
    'Incident_source',
    'FullAddress2_source',
    'Grid_source',
    'PDZone_source',
    'Officer_source',
    # Merge tracking
    'merge_run_id',
    'merge_timestamp',
    'merge_join_key',
    'merge_match_flag',
    'merge_rms_row_count_for_key',
    # Geocoding metadata
    'geocode_score',
    'geocode_match_type',
    'geocode_status',
    # Internal processing
    '_join_key_normalized',
    '_CleanAddress',
    'Incident_key',
    # Additional internal columns
    'CADNotes',
    'Response Type',  # Note: Not in required list, but may be needed
}


class ESRIOutputGenerator:
    """Generate draft and polished ESRI outputs with strict column ordering."""
    
    def __init__(self, zonecalc_source: str = 'PDZone'):
        """
        Initialize ESRI output generator.
        
        Args:
            zonecalc_source: Source column for ZoneCalc ('PDZone' or 'Grid' or calculated)
        """
        self.zonecalc_source = zonecalc_source
        self.stats = {
            'draft_columns': 0,
            'polished_columns': 0,
            'missing_required': [],
            'extra_columns_removed': [],
            'zonecalc_mapping': None
        }
    
    def _calculate_zonecalc(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate ZoneCalc field.
        
        Strategy:
        1. If PDZone exists and is valid, use it
        2. If Grid exists, derive from Grid (if mapping available)
        3. Otherwise, leave as null
        """
        if 'PDZone' in df.columns:
            # Use PDZone directly if available
            zonecalc = df['PDZone'].copy()
            # Convert to string, handle nulls
            zonecalc = zonecalc.astype(str).replace('nan', '').replace('None', '')
            zonecalc = zonecalc.replace('', np.nan)
            self.stats['zonecalc_mapping'] = 'PDZone'
            return zonecalc
        elif 'Grid' in df.columns and self.zonecalc_source == 'Grid':
            # Could derive from Grid if mapping exists
            # For now, use Grid as-is
            zonecalc = df['Grid'].copy()
            self.stats['zonecalc_mapping'] = 'Grid'
            return zonecalc
        else:
            # Return null series
            return pd.Series([np.nan] * len(df), index=df.index)
    
    def _normalize_how_reported_vectorized(self, series: pd.Series) -> pd.Series:
        """Vectorized normalization of How Reported values."""
        # Convert to string and uppercase for matching
        s = series.astype(str).str.strip().str.upper()
        
        # Direct mapping dictionary (uppercase keys)
        mapping = {
            '911': '9-1-1',
            '9-1-1': '9-1-1',
            '9/1/1': '9-1-1',
            '9 1 1': '9-1-1',
            'E911': '9-1-1',
            'EMERGENCY 911': '9-1-1',
            'EMERGENCY/911': '9-1-1',
            'EMERGENCY-911': '9-1-1',
            'WALK IN': 'Walk-In',
            'WALK-IN': 'Walk-In',
            'WALKIN': 'Walk-In',
            'PHONE': 'Phone',
            'SELF INITIATED': 'Self-Initiated',
            'SELF-INITIATED': 'Self-Initiated',
            'RADIO': 'Radio',
            'FAX': 'Fax',
            'EMAIL': 'eMail',
            'E-MAIL': 'eMail',
            'MAIL': 'Mail',
            'VIRTUAL PATROL': 'Virtual Patrol',
            'CANCELED': 'Canceled Call',
            'CANCELLED': 'Canceled Call',
            'CANCELED CALL': 'Canceled Call',
            'CANCELLED CALL': 'Canceled Call',
            'TELETYPE': 'Teletype',
            'OTHER - SEE NOTES': 'Other - See Notes',
            'OTHER': 'Other - See Notes'
        }
        
        # Use pandas replace (vectorized)
        result = s.replace(mapping)
        
        # Handle nulls and empty strings
        result = result.replace(['NAN', 'NONE', ''], '')
        result = result.where(result != '', series.astype(str).str.strip())  # Keep original if no match
        
        return result
    
    def _normalize_how_reported(self, value: Any) -> str:
        """Normalize How Reported value (legacy method for single values)."""
        if pd.isna(value):
            return ''
        s = str(value).strip().upper()
        mapping = {
            '911': '9-1-1', '9-1-1': '9-1-1', 'WALK IN': 'Walk-In', 'WALK-IN': 'Walk-In',
            'WALKIN': 'Walk-In', 'PHONE': 'Phone', 'SELF INITIATED': 'Self-Initiated',
            'SELF-INITIATED': 'Self-Initiated', 'RADIO': 'Radio', 'FAX': 'Fax',
            'EMAIL': 'eMail', 'E-MAIL': 'eMail', 'MAIL': 'Mail',
            'VIRTUAL PATROL': 'Virtual Patrol', 'CANCELED': 'Canceled Call',
            'CANCELLED': 'Canceled Call', 'TELETYPE': 'Teletype'
        }
        return mapping.get(s, str(value).strip())
    
    def _prepare_draft_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare draft output with all columns including validation flags.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with all columns (draft output)
        """
        # No copy needed - return reference if df won't be modified
        self.stats['draft_columns'] = len(df.columns)
        return df  # Removed .copy() for memory efficiency
    
    def _prepare_polished_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare polished ESRI output with strict column order.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with only required columns in exact order
        """
        # Track missing required columns
        missing_required = []
        
        # Select columns that exist, excluding ZoneCalc (will be calculated)
        cols_to_select = [c for c in ESRI_REQUIRED_COLUMNS if c != 'ZoneCalc' and c in df.columns]
        missing_required = [c for c in ESRI_REQUIRED_COLUMNS if c not in df.columns and c != 'ZoneCalc']
        
        # Create polished DataFrame with existing columns (single copy with column selection)
        polished_df = df[cols_to_select].copy() if cols_to_select else pd.DataFrame(index=df.index)
        
        # Add missing columns as empty
        for col in missing_required:
            polished_df[col] = np.nan
            logger.warning(f"Required column '{col}' not found in input data")
        
        # Calculate ZoneCalc
        polished_df['ZoneCalc'] = self._calculate_zonecalc(df)
        
        # Reorder to exact required order
        polished_df = polished_df[[c for c in ESRI_REQUIRED_COLUMNS if c in polished_df.columns]]
        
        # Special handling for How Reported normalization (vectorized)
        if 'How Reported' in polished_df.columns:
            polished_df['How Reported'] = self._normalize_how_reported_vectorized(polished_df['How Reported'])
        
        # Ensure data types are appropriate (vectorized)
        # Numeric columns
        numeric_cols = ['cYear', 'Hour_Calc']
        for col in numeric_cols:
            if col in polished_df.columns:
                polished_df[col] = pd.to_numeric(polished_df[col], errors='coerce')
        
        # DateTime columns
        datetime_cols = ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In']
        for col in datetime_cols:
            if col in polished_df.columns:
                polished_df[col] = pd.to_datetime(polished_df[col], errors='coerce')
        
        # Track removed columns
        removed_cols = set(df.columns) - set(ESRI_REQUIRED_COLUMNS)
        removed_cols = [c for c in removed_cols if c not in INTERNAL_COLUMNS]
        
        self.stats['polished_columns'] = len(polished_df.columns)
        self.stats['missing_required'] = missing_required
        self.stats['extra_columns_removed'] = sorted(removed_cols)
        
        return polished_df
    
    def generate_outputs(
        self,
        df: pd.DataFrame,
        output_dir: Path,
        base_filename: str = 'CAD_ESRI',
        format: str = 'csv'
    ) -> Dict[str, Path]:
        """
        Generate both draft and polished outputs.
        
        Args:
            df: Input DataFrame
            output_dir: Output directory
            base_filename: Base filename (without extension)
            format: Output format ('csv' or 'excel')
            
        Returns:
            Dictionary with 'draft' and 'polished' file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate draft output
        logger.info("Generating draft output (all columns)...")
        draft_df = self._prepare_draft_output(df)
        
        draft_filename = f"{base_filename}_DRAFT_{timestamp}"
        if format == 'csv':
            draft_path = output_dir / f"{draft_filename}.csv"
            draft_df.to_csv(draft_path, index=False, encoding='utf-8-sig')
        else:
            draft_path = output_dir / f"{draft_filename}.xlsx"
            draft_df.to_excel(draft_path, index=False, engine='openpyxl')
        
        logger.info(f"  Draft output: {draft_path} ({len(draft_df):,} rows, {len(draft_df.columns)} columns)")
        
        # Generate polished output
        logger.info("Generating polished ESRI output (strict column order)...")
        polished_df = self._prepare_polished_output(df)
        
        polished_filename = f"{base_filename}_POLISHED_{timestamp}"
        if format == 'csv':
            polished_path = output_dir / f"{polished_filename}.csv"
            polished_df.to_csv(polished_path, index=False, encoding='utf-8-sig')
        else:
            polished_path = output_dir / f"{polished_filename}.xlsx"
            polished_df.to_excel(polished_path, index=False, engine='openpyxl')
        
        logger.info(f"  Polished output: {polished_path} ({len(polished_df):,} rows, {len(polished_df.columns)} columns)")
        
        # Print summary
        print("\n" + "="*80)
        print("ESRI OUTPUT GENERATION SUMMARY")
        print("="*80)
        print(f"Draft Output:")
        print(f"  File: {draft_path}")
        print(f"  Rows: {len(draft_df):,}")
        print(f"  Columns: {len(draft_df.columns):,} (includes validation flags)")
        print(f"\nPolished ESRI Output:")
        print(f"  File: {polished_path}")
        print(f"  Rows: {len(polished_df):,}")
        print(f"  Columns: {len(polished_df.columns):,} (strict ESRI order)")
        
        if self.stats['missing_required']:
            print(f"\n⚠️  Missing Required Columns:")
            for col in self.stats['missing_required']:
                print(f"    - {col}")
        
        if self.stats['extra_columns_removed']:
            print(f"\n📋 Extra Columns Removed ({len(self.stats['extra_columns_removed'])}):")
            for col in self.stats['extra_columns_removed'][:10]:
                print(f"    - {col}")
            if len(self.stats['extra_columns_removed']) > 10:
                print(f"    ... and {len(self.stats['extra_columns_removed']) - 10} more")
        
        print(f"\nZoneCalc Mapping: {self.stats['zonecalc_mapping']}")
        print("="*80)
        
        return {
            'draft': draft_path,
            'polished': polished_path
        }
    
    def get_stats(self) -> Dict:
        """Get generation statistics."""
        return self.stats.copy()


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate draft and polished ESRI outputs'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input CSV/Excel file path'
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
        '--zonecalc-source',
        type=str,
        choices=['PDZone', 'Grid'],
        default='PDZone',
        help='Source for ZoneCalc field (default: PDZone)'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['csv', 'excel'],
        default='csv',
        help='Output format (default: csv)'
    )
    
    args = parser.parse_args()
    
    # Determine output directory
    input_path = Path(args.input)
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = input_path.parent
    
    # Load data
    logger.info(f"Loading data from: {input_path}")
    if input_path.suffix.lower() == '.csv':
        df = pd.read_csv(input_path, dtype=str, encoding='utf-8-sig')
    else:
        df = pd.read_excel(input_path, dtype=str)
    
    logger.info(f"Loaded {len(df):,} records with {len(df.columns)} columns")
    
    # Generate outputs
    generator = ESRIOutputGenerator(zonecalc_source=args.zonecalc_source)
    outputs = generator.generate_outputs(
        df,
        output_dir,
        base_filename=args.base_filename,
        format=args.format
    )
    
    print(f"\n✅ Outputs generated successfully!")
    print(f"   Draft:   {outputs['draft']}")
    print(f"   Polished: {outputs['polished']}")


if __name__ == "__main__":
    main()

