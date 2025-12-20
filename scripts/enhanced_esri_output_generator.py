#!/usr/bin/env python
"""
Enhanced ESRI Output Generator with Data Quality Reports
=========================================================
Generates:
1. Draft and Polished ESRI outputs (existing)
2. Pre-Geocoding Polished output (NEW)
3. Null value reports by column (NEW)
4. Processing summary markdown report (NEW)

Author: CAD Data Cleaning Engine
Date: 2025-12-19
Version: 2.0 (Enhanced)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
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

# Internal validation columns to exclude from polished output
INTERNAL_COLUMNS = {
    'data_quality_flag', 'validation_errors', 'validation_warnings',
    'Incident_source', 'FullAddress2_source', 'Grid_source', 'PDZone_source', 'Officer_source',
    'merge_run_id', 'merge_timestamp', 'merge_join_key', 'merge_match_flag', 'merge_rms_row_count_for_key',
    'geocode_score', 'geocode_match_type', 'geocode_status',
    '_join_key_normalized', '_CleanAddress', 'Incident_key',
    'CADNotes', 'Response Type',
}

# New Jersey geographic bounds (for validation)
NJ_LAT_MIN, NJ_LAT_MAX = 38.8, 41.4
NJ_LON_MIN, NJ_LON_MAX = -75.6, -73.9


class EnhancedESRIOutputGenerator:
    """Enhanced ESRI output generator with comprehensive data quality reporting."""
    
    def __init__(self, zonecalc_source: str = 'PDZone'):
        """
        Initialize enhanced output generator.
        
        Args:
            zonecalc_source: Source column for ZoneCalc ('PDZone' or 'Grid')
        """
        self.zonecalc_source = zonecalc_source
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Statistics tracking
        self.stats = {
            'draft_columns': 0,
            'polished_columns': 0,
            'missing_required': [],
            'extra_columns_removed': [],
            'zonecalc_mapping': None,
            'null_reports_generated': 0,
            'validation_stats': {},
            'rms_backfill_stats': {},
            'geocoding_stats': {},
            'data_quality_issues': {}
        }
    
    def _calculate_zonecalc(self, df: pd.DataFrame) -> pd.Series:
        """Calculate ZoneCalc field."""
        if 'PDZone' in df.columns:
            zonecalc = df['PDZone'].copy()
            zonecalc = zonecalc.astype(str).replace('nan', '').replace('None', '')
            zonecalc = zonecalc.replace('', np.nan)
            self.stats['zonecalc_mapping'] = 'PDZone'
            return zonecalc
        elif 'Grid' in df.columns and self.zonecalc_source == 'Grid':
            zonecalc = df['Grid'].copy()
            self.stats['zonecalc_mapping'] = 'Grid'
            return zonecalc
        else:
            return pd.Series([np.nan] * len(df), index=df.index)
    
    def _normalize_how_reported(self, value) -> str:
        """Normalize How Reported values to valid domain."""
        if pd.isna(value):
            return ''
        
        s = str(value).strip().upper()
        
        # Common variations mapping
        variations = {
            '911': '9-1-1', '9-1-1': '9-1-1',
            'WALK IN': 'Walk-In', 'WALK-IN': 'Walk-In', 'WALKIN': 'Walk-In',
            'PHONE': 'Phone',
            'SELF INITIATED': 'Self-Initiated', 'SELF-INITIATED': 'Self-Initiated',
            'RADIO': 'Radio', 'FAX': 'Fax',
            'EMAIL': 'eMail', 'E-MAIL': 'eMail',
            'MAIL': 'Mail',
            'VIRTUAL PATROL': 'Virtual Patrol',
            'CANCELED': 'Canceled Call', 'CANCELLED': 'Canceled Call',
            'TELETYPE': 'Teletype'
        }
        
        return variations.get(s, str(value).strip())
    
    def _prepare_polished_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare polished ESRI output with strict column order."""
        polished_df = pd.DataFrame(index=df.index)
        missing_required = []
        
        for col in ESRI_REQUIRED_COLUMNS:
            if col == 'ZoneCalc':
                polished_df[col] = self._calculate_zonecalc(df)
            elif col in df.columns:
                polished_df[col] = df[col]
            else:
                polished_df[col] = np.nan
                missing_required.append(col)
                logger.warning(f"Required column '{col}' not found in input data")
        
        # Normalize How Reported
        if 'How Reported' in polished_df.columns:
            polished_df['How Reported'] = polished_df['How Reported'].apply(self._normalize_how_reported)
        
        # Ensure data types
        numeric_cols = ['cYear', 'Hour_Calc']
        for col in numeric_cols:
            if col in polished_df.columns:
                polished_df[col] = pd.to_numeric(polished_df[col], errors='coerce')
        
        datetime_cols = ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In']
        for col in datetime_cols:
            if col in polished_df.columns:
                polished_df[col] = pd.to_datetime(polished_df[col], errors='coerce')
        
        removed_cols = set(df.columns) - set(ESRI_REQUIRED_COLUMNS)
        removed_cols = [c for c in removed_cols if c not in INTERNAL_COLUMNS]
        
        self.stats['polished_columns'] = len(polished_df.columns)
        self.stats['missing_required'] = missing_required
        self.stats['extra_columns_removed'] = sorted(removed_cols)
        
        return polished_df
    
    def _analyze_null_values(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Analyze null/blank values by column.
        
        Returns:
            Dictionary mapping column names to DataFrames of records with nulls in that column
        """
        null_reports = {}
        
        for col in df.columns:
            # Check for null or blank values
            is_null = df[col].isna()
            is_blank = df[col].astype(str).str.strip().isin(['', 'nan', 'None'])
            has_null_or_blank = is_null | is_blank
            
            null_count = has_null_or_blank.sum()
            
            if null_count > 0:
                # Extract records with null/blank values (include ALL columns for context)
                null_records = df[has_null_or_blank].copy()
                null_reports[col] = null_records
                
                logger.info(f"Column '{col}': {null_count:,} null/blank values ({null_count/len(df)*100:.2f}%)")
        
        return null_reports
    
    def _validate_coordinates(self, df: pd.DataFrame) -> Dict[str, List]:
        """
        Validate geographic coordinates.
        
        Returns:
            Dictionary with validation results
        """
        issues = {
            'missing_coords': [],
            'out_of_bounds': [],
            'zero_coords': []
        }
        
        if 'latitude' in df.columns and 'longitude' in df.columns:
            # Missing coordinates
            missing = df['latitude'].isna() | df['longitude'].isna()
            issues['missing_coords'] = df[missing].index.tolist()
            
            # Out of bounds (outside NJ)
            valid_coords = ~missing
            if valid_coords.any():
                lat = pd.to_numeric(df.loc[valid_coords, 'latitude'], errors='coerce')
                lon = pd.to_numeric(df.loc[valid_coords, 'longitude'], errors='coerce')
                
                out_of_bounds = (
                    (lat < NJ_LAT_MIN) | (lat > NJ_LAT_MAX) |
                    (lon < NJ_LON_MIN) | (lon > NJ_LON_MAX)
                )
                issues['out_of_bounds'] = df.loc[valid_coords][out_of_bounds].index.tolist()
                
                # Zero coordinates
                zero_coords = (lat == 0) & (lon == 0)
                issues['zero_coords'] = df.loc[valid_coords][zero_coords].index.tolist()
        
        return issues
    
    def _generate_null_value_reports(self, df: pd.DataFrame, output_dir: Path) -> List[Path]:
        """
        Generate separate CSV files for each column with null/blank values.
        
        Returns:
            List of generated CSV file paths
        """
        # Use base_dir to find data/02_reports/data_quality/
        base_dir = output_dir.parent if output_dir.name == 'ESRI_CADExport' else output_dir
        reports_dir = base_dir / '02_reports' / 'data_quality'
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        null_reports = self._analyze_null_values(df)
        generated_files = []
        
        for col_name, null_df in null_reports.items():
            # Sanitize column name for filename
            safe_col_name = col_name.replace(' ', '_').replace('/', '_')
            filename = f"CAD_NULL_VALUES_{safe_col_name}_{self.timestamp}.csv"
            filepath = reports_dir / filename
            
            # Save CSV with all columns
            null_df.to_csv(filepath, index=False, encoding='utf-8-sig')
            generated_files.append(filepath)
            
            logger.info(f"Generated null value report: {filepath}")
        
        self.stats['null_reports_generated'] = len(generated_files)
        return generated_files
    
    def _generate_processing_summary(
        self,
        df: pd.DataFrame,
        null_reports: List[Path],
        output_dir: Path,
        validation_stats: Dict = None,
        rms_backfill_stats: Dict = None,
        geocoding_stats: Dict = None
    ) -> Path:
        """
        Generate comprehensive processing summary markdown report.
        
        Returns:
            Path to generated markdown file
        """
        # Use base_dir to find data/02_reports/data_quality/
        base_dir = output_dir.parent if output_dir.name == 'ESRI_CADExport' else output_dir
        reports_dir = base_dir / '02_reports' / 'data_quality'
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        summary_file = reports_dir / f"PROCESSING_SUMMARY_{self.timestamp}.md"
        
        # Analyze data quality
        null_analysis = self._analyze_null_values(df)
        coord_validation = self._validate_coordinates(df)
        
        # Calculate overall quality score
        total_cells = len(df) * len(df.columns)
        null_cells = sum(len(null_df) for null_df in null_analysis.values())
        quality_score = ((total_cells - null_cells) / total_cells * 100) if total_cells > 0 else 0
        
        # Build markdown content
        md_content = []
        md_content.append(f"# CAD/RMS ETL Processing Summary")
        md_content.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_content.append(f"**Pipeline Version**: 2.0 (Enhanced)\n")
        
        # Executive Summary
        md_content.append("## Executive Summary\n")
        md_content.append(f"- **Total Records Processed**: {len(df):,}")
        md_content.append(f"- **Records Successfully Processed**: {len(df):,}")
        
        issues_count = sum(len(null_df) for null_df in null_analysis.values())
        md_content.append(f"- **Records with Issues/Warnings**: {issues_count:,}")
        md_content.append(f"- **Overall Data Quality Score**: {quality_score:.2f}%\n")
        
        # Processing Statistics
        md_content.append("## Processing Statistics\n")
        
        # Validation stats
        if validation_stats:
            md_content.append("### Validation")
            # Handle validator stats format (errors_by_field, fixes_by_field)
            total_errors = sum(validation_stats.get('errors_by_field', {}).values())
            total_fixes = sum(validation_stats.get('fixes_by_field', {}).values())
            rows_with_errors = len(validation_stats.get('rows_with_errors', set()))
            total_rows = validation_stats.get('total_rows', 0)
            
            md_content.append(f"- **Total Rows Processed**: {total_rows:,}")
            md_content.append(f"- **Rows with Errors**: {rows_with_errors:,}")
            md_content.append(f"- **Total Errors Found**: {total_errors:,}")
            md_content.append(f"- **Total Fixes Applied**: {total_fixes:,}\n")
        
        # RMS backfill stats
        if rms_backfill_stats:
            md_content.append("### RMS Backfill")
            # Try different possible keys for matched records
            matched_records = (rms_backfill_stats.get('matches_found') or 
                             rms_backfill_stats.get('matched_records') or 
                             rms_backfill_stats.get('cad_records_matched'))
            if matched_records is not None and isinstance(matched_records, (int, float)):
                md_content.append(f"- **Records Matched to RMS**: {matched_records:,}")
            else:
                md_content.append("- **Records Matched to RMS**: N/A")
            
            fields_backfilled = rms_backfill_stats.get('fields_backfilled', {})
            if fields_backfilled:
                md_content.append(f"- **Total Fields Backfilled**: {sum(fields_backfilled.values()):,}")
                md_content.append("\n**Backfill by Field**:")
                for field, count in sorted(fields_backfilled.items()):
                    md_content.append(f"  - {field}: {count:,}")
            md_content.append("")
        
        # Geocoding stats
        if geocoding_stats:
            md_content.append("### Geocoding")
            md_content.append(f"- **Records Geocoded**: {geocoding_stats.get('successful', 0):,}")
            md_content.append(f"- **Success Rate**: {geocoding_stats.get('success_rate', 0):.1f}%")
            md_content.append(f"- **Records Still Missing Coordinates**: {len(coord_validation.get('missing_coords', [])):,}\n")
        
        # Data Quality Issues
        md_content.append("## Data Quality Issues\n")
        
        # Null/blank values
        md_content.append("### Columns with Null/Blank Values\n")
        if null_analysis:
            md_content.append("| Column Name | Null/Blank Count | Percentage | Report File |")
            md_content.append("|-------------|------------------|------------|-------------|")
            
            for col_name, null_df in sorted(null_analysis.items(), key=lambda x: len(x[1]), reverse=True):
                count = len(null_df)
                pct = count / len(df) * 100
                safe_col_name = col_name.replace(' ', '_').replace('/', '_')
                report_file = f"CAD_NULL_VALUES_{safe_col_name}_{self.timestamp}.csv"
                md_content.append(f"| {col_name} | {count:,} | {pct:.2f}% | [{report_file}](./{report_file}) |")
            md_content.append("")
        else:
            md_content.append("[OK] No null/blank values detected\n")
        
        # Coordinate validation
        md_content.append("### Geographic Coordinate Validation\n")
        md_content.append(f"- **Missing Coordinates**: {len(coord_validation['missing_coords']):,} records")
        md_content.append(f"- **Out of Bounds Coordinates**: {len(coord_validation['out_of_bounds']):,} records")
        md_content.append(f"- **Zero Coordinates**: {len(coord_validation['zero_coords']):,} records\n")
        
        # Records Requiring Manual Review
        md_content.append("## Records Requiring Manual Review\n")
        
        critical_issues = []
        
        # Missing critical fields
        critical_fields = ['ReportNumberNew', 'Incident', 'FullAddress2']
        for field in critical_fields:
            if field in null_analysis:
                critical_issues.append(f"- **Missing {field}**: {len(null_analysis[field]):,} records")
        
        # Invalid coordinates
        if len(coord_validation['out_of_bounds']) > 0:
            critical_issues.append(f"- **Invalid Coordinates**: {len(coord_validation['out_of_bounds']):,} records outside NJ bounds")
        
        if critical_issues:
            md_content.extend(critical_issues)
            md_content.append("")
        else:
            md_content.append("[OK] No critical issues requiring immediate attention\n")
        
        # Recommendations
        md_content.append("## Recommendations\n")
        
        recommendations = []
        
        # Priority recommendations based on issues
        if 'Incident' in null_analysis and len(null_analysis['Incident']) > 0:
            recommendations.append("1. **HIGH PRIORITY**: Review records with missing Incident type - may require RMS cross-reference")
        
        if 'FullAddress2' in null_analysis and len(null_analysis['FullAddress2']) > 0:
            recommendations.append("2. **HIGH PRIORITY**: Review records with missing addresses - impacts geocoding and spatial analysis")
        
        if len(coord_validation['missing_coords']) > 0:
            recommendations.append("3. **MEDIUM PRIORITY**: Run geocoding for records with missing coordinates")
        
        if len(coord_validation['out_of_bounds']) > 0:
            recommendations.append("4. **MEDIUM PRIORITY**: Review out-of-bounds coordinates - may indicate data entry errors")
        
        if recommendations:
            md_content.extend(recommendations)
        else:
            md_content.append("[OK] Data quality is excellent - no specific recommendations at this time")
        
        md_content.append("\n---")
        md_content.append(f"\n*Report generated by CAD/RMS ETL Pipeline v2.0*")
        
        # Write markdown file
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_content))
        
        logger.info(f"Generated processing summary: {summary_file}")
        return summary_file
    
    def generate_outputs(
        self,
        df: pd.DataFrame,
        output_dir: Path,
        base_filename: str = 'CAD_ESRI',
        format: str = 'csv',
        pre_geocode: bool = False,
        validation_stats: Dict = None,
        rms_backfill_stats: Dict = None,
        geocoding_stats: Dict = None
    ) -> Dict[str, Path]:
        """
        Generate all outputs: draft, polished, null reports, and summary.
        
        Args:
            df: Input DataFrame
            output_dir: Base output directory
            base_filename: Base filename for ESRI outputs
            format: Output format ('csv' or 'excel')
            pre_geocode: If True, this is the pre-geocoding output
            validation_stats: Validation statistics from pipeline
            rms_backfill_stats: RMS backfill statistics from pipeline
            geocoding_stats: Geocoding statistics from pipeline
            
        Returns:
            Dictionary with paths to all generated files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        outputs = {}
        
        # Generate draft output (all columns)
        logger.info("Generating draft output (all columns)...")
        draft_df = df.copy()
        self.stats['draft_columns'] = len(draft_df.columns)
        
        draft_suffix = '_DRAFT'
        draft_filename = f"{base_filename}{draft_suffix}_{self.timestamp}"
        
        if format == 'csv':
            draft_path = output_dir / f"{draft_filename}.csv"
            draft_df.to_csv(draft_path, index=False, encoding='utf-8-sig')
        else:
            draft_path = output_dir / f"{draft_filename}.xlsx"
            draft_df.to_excel(draft_path, index=False, engine='openpyxl')
        
        outputs['draft'] = draft_path
        logger.info(f"  Draft output: {draft_path} ({len(draft_df):,} rows, {len(draft_df.columns)} columns)")
        
        # Generate polished output (strict ESRI order)
        logger.info("Generating polished ESRI output (strict column order)...")
        polished_df = self._prepare_polished_output(df)
        
        polished_suffix = '_POLISHED_PRE_GEOCODE' if pre_geocode else '_POLISHED'
        polished_filename = f"{base_filename}{polished_suffix}_{self.timestamp}"
        
        if format == 'csv':
            polished_path = output_dir / f"{polished_filename}.csv"
            polished_df.to_csv(polished_path, index=False, encoding='utf-8-sig')
        else:
            polished_path = output_dir / f"{polished_filename}.xlsx"
            polished_df.to_excel(polished_path, index=False, engine='openpyxl')
        
        outputs['polished'] = polished_path
        logger.info(f"  Polished output: {polished_path} ({len(polished_df):,} rows, {len(polished_df.columns)} columns)")
        
        # Generate null value reports (use polished output)
        logger.info("Generating null value reports by column...")
        null_reports = self._generate_null_value_reports(polished_df, output_dir)
        outputs['null_reports'] = null_reports
        logger.info(f"  Generated {len(null_reports)} null value report(s)")
        
        # Generate processing summary
        logger.info("Generating processing summary markdown report...")
        summary_path = self._generate_processing_summary(
            polished_df,
            null_reports,
            output_dir,
            validation_stats=validation_stats,
            rms_backfill_stats=rms_backfill_stats,
            geocoding_stats=geocoding_stats
        )
        outputs['summary'] = summary_path
        
        # Print summary
        print("\n" + "="*80)
        print("ENHANCED ESRI OUTPUT GENERATION SUMMARY")
        print("="*80)
        print(f"Draft Output:")
        print(f"  File: {draft_path}")
        print(f"  Rows: {len(draft_df):,}")
        print(f"  Columns: {len(draft_df.columns):,} (includes validation flags)")
        
        print(f"\nPolished ESRI Output{' (Pre-Geocode)' if pre_geocode else ''}:")
        print(f"  File: {polished_path}")
        print(f"  Rows: {len(polished_df):,}")
        print(f"  Columns: {len(polished_df.columns):,} (strict ESRI order)")
        
        print(f"\nData Quality Reports:")
        print(f"  Null value CSVs: {len(null_reports)} file(s)")
        print(f"  Processing summary: {summary_path}")
        
        if self.stats['missing_required']:
            print(f"\n[WARN] Missing Required Columns:")
            for col in self.stats['missing_required']:
                print(f"    - {col}")
        
        print(f"\nZoneCalc Mapping: {self.stats['zonecalc_mapping']}")
        print("="*80)
        
        return outputs
    
    def get_stats(self) -> Dict:
        """Get generation statistics."""
        return self.stats.copy()


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate enhanced ESRI outputs with data quality reports'
    )
    parser.add_argument('--input', type=str, required=True, help='Input CSV/Excel file path')
    parser.add_argument('--output-dir', type=str, help='Output directory (default: same as input file)')
    parser.add_argument('--base-filename', type=str, default='CAD_ESRI', help='Base filename for outputs')
    parser.add_argument('--zonecalc-source', type=str, choices=['PDZone', 'Grid'], default='PDZone')
    parser.add_argument('--format', type=str, choices=['csv', 'excel'], default='csv')
    parser.add_argument('--pre-geocode', action='store_true', help='Generate pre-geocoding output')
    
    args = parser.parse_args()
    
    # Determine output directory
    input_path = Path(args.input)
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    
    # Load data
    logger.info(f"Loading data from: {input_path}")
    if input_path.suffix.lower() == '.csv':
        df = pd.read_csv(input_path, dtype=str, encoding='utf-8-sig')
    else:
        df = pd.read_excel(input_path, dtype=str)
    
    logger.info(f"Loaded {len(df):,} records with {len(df.columns)} columns")
    
    # Generate outputs
    generator = EnhancedESRIOutputGenerator(zonecalc_source=args.zonecalc_source)
    outputs = generator.generate_outputs(
        df,
        output_dir,
        base_filename=args.base_filename,
        format=args.format,
        pre_geocode=args.pre_geocode
    )
    
    print(f"\n[SUCCESS] Outputs generated successfully!")
    print(f"   Draft:             {outputs['draft']}")
    print(f"   Polished:          {outputs['polished']}")
    print(f"   Null Reports:      {len(outputs['null_reports'])} file(s)")
    print(f"   Processing Summary: {outputs['summary']}")


if __name__ == "__main__":
    main()

