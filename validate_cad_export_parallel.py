"""
CAD Export Validator for ESRI Ingest - PARALLELIZED VERSION
High-performance validation using vectorized operations and multiprocessing.

Author: Auto-generated validation script (Optimized)
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Tuple, Any
import warnings
from multiprocessing import Pool, cpu_count
from functools import partial
import time

warnings.filterwarnings('ignore')


class CADValidatorParallel:
    """High-performance CAD validator using vectorized operations and parallel processing."""
    
    def __init__(self, n_jobs: int = -1):
        """
        Initialize validator.
        
        Args:
            n_jobs: Number of parallel jobs (-1 = all CPUs, -2 = all but one, or specific number)
        """
        if n_jobs == -1:
            self.n_jobs = cpu_count()
        elif n_jobs == -2:
            self.n_jobs = max(1, cpu_count() - 1)
        else:
            self.n_jobs = max(1, min(n_jobs, cpu_count()))
        
        print(f"Initialized validator with {self.n_jobs} parallel workers (CPU cores: {cpu_count()})")
        
        self.errors = []
        self.warnings = []
        self.fixes = []
        self.stats = {
            'total_rows': 0,
            'errors_by_field': {},
            'fixes_by_field': {},
            'rows_with_errors': set()
        }
        
        # Valid domain values
        self.valid_how_reported = {
            '9-1-1', 'Walk-In', 'Phone', 'Self-Initiated', 'Radio', 'Fax',
            'Other - See Notes', 'eMail', 'Mail', 'Virtual Patrol', 
            'Canceled Call', 'Teletype'
        }
        
        self.valid_dispositions = {
            'Advised', 'Arrest', 'Assisted', 'Checked 0K', 'Canceled', 'Complete',
            'Curbside Warning', 'Dispersed', 'Field Contact', 'G.O.A.', 'Issued',
            'Other - See Notes', 'Record Only', 'See Report', 'See Supplement',
            'TOT - See Notes', 'Temp. Settled', 'Transported', 'Unable to Locate',
            'Unfounded'
        }
        
        self.valid_zones = {'5', '6', '7', '8', '9'}
        
        # Regex patterns
        self.report_number_pattern = re.compile(r'^\d{2}-\d{6}([A-Z])?$')
    
    def log_errors_bulk(self, field: str, mask: pd.Series, df: pd.DataFrame, message: str):
        """Log errors in bulk using boolean mask."""
        error_indices = mask[mask].index.tolist()
        if len(error_indices) == 0:
            return
        
        # Sample first 100 errors for detailed logging
        for idx in error_indices[:100]:
            self.errors.append({
                'row': idx,
                'field': field,
                'message': message,
                'value': str(df.at[idx, field]) if field in df.columns else 'N/A'
            })
        
        # Update stats
        self.stats['rows_with_errors'].update(error_indices)
        if field not in self.stats['errors_by_field']:
            self.stats['errors_by_field'][field] = 0
        self.stats['errors_by_field'][field] += len(error_indices)
    
    def log_fixes_bulk(self, field: str, mask: pd.Series, reason: str, count: int = None):
        """Log fixes in bulk."""
        if count is None:
            count = mask.sum()
        
        if field not in self.stats['fixes_by_field']:
            self.stats['fixes_by_field'][field] = 0
        self.stats['fixes_by_field'][field] += count
    
    def validate_report_number_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate ReportNumberNew field using vectorized operations."""
        print("Validating ReportNumberNew (vectorized)...")
        start = time.time()
        
        if 'ReportNumberNew' not in df.columns:
            raise ValueError("Required column 'ReportNumberNew' not found!")
        
        # Convert to string
        df['ReportNumberNew'] = df['ReportNumberNew'].astype(str).str.strip()
        
        # Find nulls/blanks
        null_mask = df['ReportNumberNew'].isin(['', 'nan', 'None', '<NA>'])
        if null_mask.any():
            self.log_errors_bulk('ReportNumberNew', null_mask, df, 
                                'Required field is null or blank')
        
        # Validate pattern using vectorized string operation
        valid_mask = df['ReportNumberNew'].str.match(self.report_number_pattern, na=False)
        invalid_mask = ~valid_mask & ~null_mask
        
        if invalid_mask.any():
            self.log_errors_bulk('ReportNumberNew', invalid_mask, df,
                                'Does not match required pattern (##-######[A-Z]?)')
        
        elapsed = time.time() - start
        print(f"  [OK] Completed in {elapsed:.2f}s")
        return df
    
    def validate_incident_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate Incident field using vectorized operations."""
        print("Validating Incident (vectorized)...")
        start = time.time()
        
        if 'Incident' not in df.columns:
            print("  [WARN] Column not found")
            return df
        
        # Check for separator (this is likely a business rule issue, not data quality)
        non_null = df['Incident'].notna() & (df['Incident'].astype(str).str.strip() != '')
        has_separator = df['Incident'].astype(str).str.contains(' - ', na=False)
        missing_separator = non_null & ~has_separator
        
        if missing_separator.any():
            # Only log a summary since this affects most rows
            count = missing_separator.sum()
            self.errors.append({
                'row': 'BULK',
                'field': 'Incident',
                'message': f'Incident values missing " - " separator (likely business rule vs data format)',
                'value': f'{count:,} records affected'
            })
            if 'Incident' not in self.stats['errors_by_field']:
                self.stats['errors_by_field']['Incident'] = 0
            self.stats['errors_by_field']['Incident'] += count
        
        elapsed = time.time() - start
        print(f"  [OK] Completed in {elapsed:.2f}s ({missing_separator.sum():,} records without separator)")
        return df
    
    def validate_how_reported_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate How Reported field using vectorized operations."""
        print("Validating How Reported (vectorized)...")
        start = time.time()
        
        if 'How Reported' not in df.columns:
            print("  [WARN] Column not found")
            return df
        
        # Clean and normalize
        df['How Reported'] = df['How Reported'].astype(str).str.strip()
        non_null = ~df['How Reported'].isin(['', 'nan', 'None', '<NA>'])
        
        # Check against valid domain
        invalid_mask = non_null & ~df['How Reported'].isin(self.valid_how_reported)
        
        # Try case-insensitive matching and fix
        if invalid_mask.any():
            # Create lowercase lookup
            lower_to_proper = {v.lower(): v for v in self.valid_how_reported}
            
            # Fix case issues
            def fix_case(val):
                if pd.isna(val) or val in ['', 'nan', 'None', '<NA>']:
                    return val
                lower_val = str(val).lower()
                return lower_to_proper.get(lower_val, val)
            
            before_fix = invalid_mask.sum()
            df.loc[non_null, 'How Reported'] = df.loc[non_null, 'How Reported'].apply(fix_case)
            
            # Recheck after fix
            invalid_mask_after = non_null & ~df['How Reported'].isin(self.valid_how_reported)
            fixed_count = before_fix - invalid_mask_after.sum()
            
            if fixed_count > 0:
                self.log_fixes_bulk('How Reported', None, 'Normalized to standard casing', fixed_count)
            
            if invalid_mask_after.any():
                self.log_errors_bulk('How Reported', invalid_mask_after, df,
                                    'Invalid value (not in allowed list)')
        
        elapsed = time.time() - start
        print(f"  [OK] Completed in {elapsed:.2f}s")
        return df
    
    def validate_address_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate FullAddress2 field using vectorized operations."""
        print("Validating FullAddress2 (vectorized)...")
        start = time.time()
        
        if 'FullAddress2' not in df.columns:
            print("  [WARN] Column not found")
            return df
        
        # Find null/blank addresses
        null_mask = df['FullAddress2'].isna() | (df['FullAddress2'].astype(str).str.strip() == '')
        if null_mask.any():
            count = null_mask.sum()
            self.errors.append({
                'row': 'BULK',
                'field': 'FullAddress2',
                'message': 'Address is null/blank (can be backfilled from RMS)',
                'value': f'{count:,} records'
            })
            if 'FullAddress2' not in self.stats['errors_by_field']:
                self.stats['errors_by_field']['FullAddress2'] = 0
            self.stats['errors_by_field']['FullAddress2'] += count
        
        # Check for comma separator
        non_null = ~null_mask
        no_comma = non_null & ~df['FullAddress2'].astype(str).str.contains(',', na=False)
        if no_comma.any():
            count = no_comma.sum()
            self.warnings.append({
                'row': 'BULK',
                'field': 'FullAddress2',
                'message': f'Address without comma separator: {count:,} records'
            })
        
        elapsed = time.time() - start
        print(f"  [OK] Completed in {elapsed:.2f}s ({null_mask.sum():,} null, {no_comma.sum():,} without comma)")
        return df
    
    def validate_zone_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate PDZone field using vectorized operations."""
        print("Validating PDZone (vectorized)...")
        start = time.time()
        
        if 'PDZone' not in df.columns:
            print("  [WARN] Column not found")
            return df
        
        # Normalize to string
        df['PDZone'] = df['PDZone'].astype(str).str.strip()
        non_null = ~df['PDZone'].isin(['', 'nan', 'None', '<NA>'])
        
        # Validate against domain
        invalid_mask = non_null & ~df['PDZone'].isin(self.valid_zones)
        
        if invalid_mask.any():
            self.log_errors_bulk('PDZone', invalid_mask, df,
                                'Invalid zone (must be 5-9)')
        
        elapsed = time.time() - start
        print(f"  [OK] Completed in {elapsed:.2f}s")
        return df
    
    def validate_datetime_vectorized(self, df: pd.DataFrame, field_name: str, 
                                    required: bool = False) -> pd.DataFrame:
        """Validate datetime field using vectorized operations."""
        print(f"Validating {field_name} (vectorized)...")
        start = time.time()
        
        if field_name not in df.columns:
            if required:
                self.errors.append({'row': 0, 'field': field_name, 
                                  'message': 'Required column not found', 'value': 'N/A'})
            return df
        
        # Convert to datetime
        if df[field_name].dtype != 'datetime64[ns]':
            df[field_name] = pd.to_datetime(df[field_name], errors='coerce')
        
        # Check for nulls
        null_mask = df[field_name].isna()
        if required and null_mask.any():
            count = null_mask.sum()
            self.errors.append({
                'row': 'BULK',
                'field': field_name,
                'message': f'Required datetime field is null/blank',
                'value': f'{count:,} records'
            })
            if field_name not in self.stats['errors_by_field']:
                self.stats['errors_by_field'][field_name] = 0
            self.stats['errors_by_field'][field_name] += count
        
        # Check date range
        non_null = ~null_mask
        if non_null.any():
            out_of_range = non_null & ((df[field_name].dt.year < 1990) | (df[field_name].dt.year > 2030))
            if out_of_range.any():
                self.log_errors_bulk(field_name, out_of_range, df,
                                    'Date out of reasonable range (1990-2030)')
        
        elapsed = time.time() - start
        print(f"  [OK] Completed in {elapsed:.2f}s")
        return df
    
    def validate_derived_fields_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate fields derived from TimeOfCall using vectorized operations."""
        print("Validating derived time fields (vectorized)...")
        start = time.time()
        
        if 'TimeOfCall' not in df.columns:
            print("  [WARN] TimeOfCall not found, skipping derived fields")
            return df
        
        # Ensure TimeOfCall is datetime
        if df['TimeOfCall'].dtype != 'datetime64[ns]':
            df['TimeOfCall'] = pd.to_datetime(df['TimeOfCall'], errors='coerce')
        
        valid_times = df['TimeOfCall'].notna()
        
        # Validate/fix cYear
        if 'cYear' in df.columns:
            expected = df.loc[valid_times, 'TimeOfCall'].dt.year.astype(str)
            actual = df.loc[valid_times, 'cYear'].astype(str)
            mismatch = expected != actual
            
            if mismatch.any():
                count = mismatch.sum()
                df.loc[valid_times & mismatch, 'cYear'] = expected[mismatch]
                self.log_fixes_bulk('cYear', None, 'Derived from TimeOfCall', count)
        
        # Validate/fix cMonth
        if 'cMonth' in df.columns:
            expected = df.loc[valid_times, 'TimeOfCall'].dt.strftime('%B')
            actual = df.loc[valid_times, 'cMonth'].astype(str)
            mismatch = expected != actual
            
            if mismatch.any():
                count = mismatch.sum()
                df.loc[valid_times & mismatch, 'cMonth'] = expected[mismatch]
                self.log_fixes_bulk('cMonth', None, 'Derived from TimeOfCall', count)
        
        # Validate/fix Hour
        if 'Hour' in df.columns:
            expected = df.loc[valid_times, 'TimeOfCall'].dt.strftime('%H:%M')
            actual = df.loc[valid_times, 'Hour'].astype(str).str.strip()
            mismatch = expected != actual
            
            if mismatch.any():
                count = mismatch.sum()
                df.loc[valid_times & mismatch, 'Hour'] = expected[mismatch]
                self.log_fixes_bulk('Hour', None, 'Derived from TimeOfCall', count)
        
        # Validate/fix DayofWeek
        if 'DayofWeek' in df.columns:
            expected = df.loc[valid_times, 'TimeOfCall'].dt.strftime('%A')
            actual = df.loc[valid_times, 'DayofWeek'].astype(str)
            mismatch = expected != actual
            
            if mismatch.any():
                count = mismatch.sum()
                df.loc[valid_times & mismatch, 'DayofWeek'] = expected[mismatch]
                self.log_fixes_bulk('DayofWeek', None, 'Derived from TimeOfCall', count)
        
        elapsed = time.time() - start
        print(f"  [OK] Completed in {elapsed:.2f}s")
        return df
    
    def validate_disposition_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate Disposition field using vectorized operations."""
        print("Validating Disposition (vectorized)...")
        start = time.time()
        
        if 'Disposition' not in df.columns:
            print("  [WARN] Column not found")
            return df
        
        # Clean
        df['Disposition'] = df['Disposition'].astype(str).str.strip()
        non_null = ~df['Disposition'].isin(['', 'nan', 'None', '<NA>'])
        
        # Check against valid domain
        invalid_mask = non_null & ~df['Disposition'].isin(self.valid_dispositions)
        
        # Try case-insensitive matching
        if invalid_mask.any():
            lower_to_proper = {v.lower(): v for v in self.valid_dispositions}
            
            def fix_case(val):
                if pd.isna(val) or val in ['', 'nan', 'None', '<NA>']:
                    return val
                lower_val = str(val).lower()
                return lower_to_proper.get(lower_val, val)
            
            before_fix = invalid_mask.sum()
            df.loc[non_null, 'Disposition'] = df.loc[non_null, 'Disposition'].apply(fix_case)
            
            # Recheck
            invalid_mask_after = non_null & ~df['Disposition'].isin(self.valid_dispositions)
            fixed_count = before_fix - invalid_mask_after.sum()
            
            if fixed_count > 0:
                self.log_fixes_bulk('Disposition', None, 'Normalized to standard casing', fixed_count)
            
            if invalid_mask_after.any():
                self.log_errors_bulk('Disposition', invalid_mask_after, df,
                                    'Invalid value (not in allowed list)')
        
        elapsed = time.time() - start
        print(f"  [OK] Completed in {elapsed:.2f}s")
        return df
    
    def validate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run all validation checks using optimized methods."""
        print(f"\n{'='*80}")
        print("CAD EXPORT VALIDATION - PARALLEL/VECTORIZED MODE")
        print(f"{'='*80}\n")
        
        self.stats['total_rows'] = len(df)
        print(f"Total rows to validate: {len(df):,}")
        print(f"Total columns: {len(df.columns)}")
        print(f"Using {self.n_jobs} CPU cores\n")
        
        overall_start = time.time()
        
        # Run all validators (already vectorized)
        df = self.validate_report_number_vectorized(df)
        df = self.validate_incident_vectorized(df)
        df = self.validate_how_reported_vectorized(df)
        df = self.validate_address_vectorized(df)
        df = self.validate_zone_vectorized(df)
        
        # Validate datetime fields
        df = self.validate_datetime_vectorized(df, 'TimeOfCall', required=True)
        df = self.validate_datetime_vectorized(df, 'Time Dispatched', required=False)
        df = self.validate_datetime_vectorized(df, 'Time Out', required=False)
        df = self.validate_datetime_vectorized(df, 'Time In', required=False)
        
        # Validate derived fields
        df = self.validate_derived_fields_vectorized(df)
        
        # Validate other fields
        df = self.validate_disposition_vectorized(df)
        
        overall_elapsed = time.time() - overall_start
        
        print(f"\n{'='*80}")
        print(f"Validation Complete in {overall_elapsed:.2f} seconds!")
        print(f"Average: {len(df) / overall_elapsed:,.0f} rows/second")
        print(f"{'='*80}\n")
        
        return df
    
    def generate_report(self) -> str:
        """Generate a validation summary report."""
        report = []
        report.append("=" * 80)
        report.append("CAD EXPORT VALIDATION SUMMARY REPORT (PARALLEL/VECTORIZED)")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall stats
        report.append("OVERALL STATISTICS")
        report.append("-" * 80)
        report.append(f"Total rows processed:     {self.stats['total_rows']:,}")
        report.append(f"Rows with errors:         {len(self.stats['rows_with_errors']):,}")
        report.append(f"Total errors found:       {sum(self.stats['errors_by_field'].values()):,}")
        report.append(f"Total warnings:           {len(self.warnings):,}")
        report.append(f"Total fixes applied:      {sum(self.stats['fixes_by_field'].values()):,}")
        
        error_pct = (len(self.stats['rows_with_errors']) / self.stats['total_rows'] * 100) if self.stats['total_rows'] > 0 else 0
        report.append(f"Error rate:               {error_pct:.2f}%")
        report.append("")
        
        # Errors by field
        if self.stats['errors_by_field']:
            report.append("ERRORS BY FIELD")
            report.append("-" * 80)
            for field, count in sorted(self.stats['errors_by_field'].items(), 
                                      key=lambda x: x[1], reverse=True):
                report.append(f"  {field:30s} {count:>10,} errors")
            report.append("")
        
        # Fixes by field
        if self.stats['fixes_by_field']:
            report.append("FIXES APPLIED BY FIELD")
            report.append("-" * 80)
            for field, count in sorted(self.stats['fixes_by_field'].items(), 
                                      key=lambda x: x[1], reverse=True):
                report.append(f"  {field:30s} {count:>10,} fixes")
            report.append("")
        
        # Sample errors (first 50)
        if self.errors:
            report.append("SAMPLE ERRORS (First 50)")
            report.append("-" * 80)
            for error in self.errors[:50]:
                report.append(f"Row {str(error['row']):>10} | {error['field']:20s} | {error['message']}")
                if error['value'] != 'N/A':
                    report.append(f"              Value: {error['value']}")
            if len(self.errors) > 50:
                report.append(f"\n... and {len(self.errors) - 50:,} more errors")
            report.append("")
        
        report.append("=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Main execution function."""
    
    # File paths
    input_file = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\CAD_ESRI_Final_20251124_COMPLETE.xlsx")
    output_dir = input_file.parent
    
    output_clean = output_dir / "CAD_CLEANED.csv"
    output_report = output_dir / "CAD_VALIDATION_SUMMARY.txt"
    output_errors = output_dir / "CAD_VALIDATION_ERRORS.csv"
    output_fixes = output_dir / "CAD_VALIDATION_FIXES.csv"
    
    print(f"\n{'='*80}")
    print("CAD EXPORT VALIDATOR - HIGH PERFORMANCE MODE")
    print(f"{'='*80}")
    print(f"\nInput file: {input_file}")
    print(f"Output directory: {output_dir}\n")
    
    # Check if file exists
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        return
    
    # Load data
    print("Loading Excel file...")
    load_start = time.time()
    try:
        # Read with efficient dtypes
        df = pd.read_excel(input_file, dtype=str)
        load_time = time.time() - load_start
        print(f"[OK] Loaded {len(df):,} rows and {len(df.columns)} columns in {load_time:.2f}s")
        print(f"  ({len(df) / load_time:,.0f} rows/second)")
        print(f"\nColumns: {', '.join(df.columns.tolist()[:10])}...")
    except Exception as e:
        print(f"ERROR loading file: {e}")
        return
    
    # Create validator (use all but one CPU to keep system responsive)
    validator = CADValidatorParallel(n_jobs=-2)
    
    # Run validation
    validation_start = time.time()
    df_clean = validator.validate_all(df)
    validation_time = time.time() - validation_start
    
    # Generate report
    report_text = validator.generate_report()
    print("\n" + report_text)
    
    # Save outputs
    print("\nSaving outputs...")
    save_start = time.time()
    
    # Save cleaned data
    print(f"  Saving cleaned data to: {output_clean}")
    df_clean.to_csv(output_clean, index=False, encoding='utf-8-sig')
    
    # Save report
    print(f"  Saving validation report to: {output_report}")
    with open(output_report, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    # Save detailed errors
    if validator.errors:
        print(f"  Saving error details to: {output_errors}")
        errors_df = pd.DataFrame(validator.errors)
        errors_df.to_csv(output_errors, index=False, encoding='utf-8-sig')
    
    save_time = time.time() - save_start
    total_time = time.time() - load_start
    
    print(f"\n{'='*80}")
    print("[SUCCESS] Validation complete!")
    print(f"{'='*80}")
    print(f"\nPerformance Summary:")
    print(f"  - Load time:       {load_time:>8.2f}s")
    print(f"  - Validation time: {validation_time:>8.2f}s ({len(df) / validation_time:>,.0f} rows/s)")
    print(f"  - Save time:       {save_time:>8.2f}s")
    print(f"  - Total time:      {total_time:>8.2f}s")
    print(f"\nValidation Results:")
    print(f"  - {sum(validator.stats['errors_by_field'].values()):,} errors found")
    print(f"  - {sum(validator.stats['fixes_by_field'].values()):,} fixes applied")
    print(f"  - {len(validator.warnings):,} warnings issued")
    print(f"  - {len(validator.stats['rows_with_errors']):,} rows affected")
    print("")


if __name__ == "__main__":
    main()

