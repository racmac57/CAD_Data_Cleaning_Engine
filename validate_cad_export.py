"""
CAD Export Validator for ESRI Ingest
Validates and cleans CAD data according to field schemas and business rules.

Author: Auto-generated validation script
Date: 2025-12-16
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Tuple, Any
import warnings
warnings.filterwarnings('ignore')


class CADValidator:
    """Validates CAD export data according to defined schemas and business rules."""
    
    def __init__(self):
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
        self.valid_how_reported = [
            '9-1-1', 'Walk-In', 'Phone', 'Self-Initiated', 'Radio', 'Fax',
            'Other - See Notes', 'eMail', 'Mail', 'Virtual Patrol', 
            'Canceled Call', 'Teletype'
        ]
        
        self.valid_dispositions = [
            'Advised', 'Arrest', 'Assisted', 'Checked 0K', 'Canceled', 'Complete',
            'Curbside Warning', 'Dispersed', 'Field Contact', 'G.O.A.', 'Issued',
            'Other - See Notes', 'Record Only', 'See Report', 'See Supplement',
            'TOT - See Notes', 'Temp. Settled', 'Transported', 'Unable to Locate',
            'Unfounded'
        ]
        
        self.valid_zones = ['5', '6', '7', '8', '9']
        
        # Regex patterns
        self.report_number_pattern = re.compile(r'^\d{2}-\d{6}([A-Z])?$')
        
    def log_error(self, row_idx: int, field: str, message: str, value: Any = None):
        """Log a validation error."""
        self.errors.append({
            'row': row_idx,
            'field': field,
            'message': message,
            'value': str(value) if value is not None else 'NULL'
        })
        self.stats['rows_with_errors'].add(row_idx)
        if field not in self.stats['errors_by_field']:
            self.stats['errors_by_field'][field] = 0
        self.stats['errors_by_field'][field] += 1
    
    def log_fix(self, row_idx: int, field: str, old_value: Any, new_value: Any, reason: str):
        """Log an applied fix."""
        self.fixes.append({
            'row': row_idx,
            'field': field,
            'old_value': str(old_value),
            'new_value': str(new_value),
            'reason': reason
        })
        if field not in self.stats['fixes_by_field']:
            self.stats['fixes_by_field'][field] = 0
        self.stats['fixes_by_field'][field] += 1
    
    def log_warning(self, row_idx: int, field: str, message: str):
        """Log a warning."""
        self.warnings.append({
            'row': row_idx,
            'field': field,
            'message': message
        })
    
    def is_null_or_blank(self, value: Any) -> bool:
        """Check if value is null, NaN, or blank string."""
        if pd.isna(value):
            return True
        if isinstance(value, str) and value.strip() == '':
            return True
        return False
    
    def validate_report_number(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate ReportNumberNew field."""
        print("Validating ReportNumberNew...")
        
        if 'ReportNumberNew' not in df.columns:
            raise ValueError("Required column 'ReportNumberNew' not found!")
        
        for idx, row in df.iterrows():
            value = row['ReportNumberNew']
            
            # Check if null
            if self.is_null_or_blank(value):
                self.log_error(idx, 'ReportNumberNew', 'Required field is null or blank')
                continue
            
            # Ensure it's string
            value_str = str(value).strip()
            
            # Validate pattern
            if not self.report_number_pattern.match(value_str):
                self.log_error(idx, 'ReportNumberNew', 
                              f'Does not match required pattern (##-######[A-Z]?)', value_str)
            
            # Fix: ensure stored as text with leading zeros preserved
            if df.at[idx, 'ReportNumberNew'] != value_str:
                self.log_fix(idx, 'ReportNumberNew', df.at[idx, 'ReportNumberNew'], 
                           value_str, 'Normalized to string')
                df.at[idx, 'ReportNumberNew'] = value_str
        
        return df
    
    def validate_incident(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate Incident field."""
        print("Validating Incident...")
        
        if 'Incident' not in df.columns:
            self.log_warning(0, 'Incident', 'Column not found in dataset')
            return df
        
        for idx, row in df.iterrows():
            value = row['Incident']
            
            if self.is_null_or_blank(value):
                self.log_warning(idx, 'Incident', 'Incident is blank (can be backfilled from RMS)')
                continue
            
            value_str = str(value).strip()
            
            # Check if contains " - " separator
            if ' - ' not in value_str:
                self.log_error(idx, 'Incident', 
                              'Incident must contain " - " separator', value_str)
        
        return df
    
    def validate_how_reported(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate How Reported field."""
        print("Validating How Reported...")
        
        if 'How Reported' not in df.columns:
            self.log_warning(0, 'How Reported', 'Column not found in dataset')
            return df
        
        for idx, row in df.iterrows():
            value = row['How Reported']
            
            if self.is_null_or_blank(value):
                continue  # Optional field
            
            value_str = str(value).strip()
            
            # Force as text to prevent Excel date artifacts
            df.at[idx, 'How Reported'] = value_str
            
            # Check against valid domain
            if value_str not in self.valid_how_reported:
                # Try to match case-insensitively
                matched = False
                for valid in self.valid_how_reported:
                    if value_str.lower() == valid.lower():
                        self.log_fix(idx, 'How Reported', value_str, valid, 
                                   'Normalized to standard casing')
                        df.at[idx, 'How Reported'] = valid
                        matched = True
                        break
                
                if not matched:
                    self.log_error(idx, 'How Reported', 
                                  f'Invalid value (not in allowed list)', value_str)
        
        return df
    
    def validate_address(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate FullAddress2 field."""
        print("Validating FullAddress2...")
        
        if 'FullAddress2' not in df.columns:
            self.log_warning(0, 'FullAddress2', 'Column not found in dataset')
            return df
        
        for idx, row in df.iterrows():
            value = row['FullAddress2']
            
            if self.is_null_or_blank(value):
                self.log_error(idx, 'FullAddress2', 
                              'Address is null/blank (can be backfilled from RMS)')
                continue
            
            value_str = str(value).strip()
            
            # Check if contains comma (typical address format)
            if ',' not in value_str:
                self.log_warning(idx, 'FullAddress2', 
                               'Address does not contain comma separator')
        
        return df
    
    def validate_zone(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate PDZone field."""
        print("Validating PDZone...")
        
        if 'PDZone' not in df.columns:
            self.log_warning(0, 'PDZone', 'Column not found in dataset')
            return df
        
        for idx, row in df.iterrows():
            value = row['PDZone']
            
            if self.is_null_or_blank(value):
                continue  # Optional field
            
            value_str = str(value).strip()
            
            # Normalize to string
            df.at[idx, 'PDZone'] = value_str
            
            # Validate against domain
            if value_str not in self.valid_zones:
                self.log_error(idx, 'PDZone', 
                              f'Invalid zone (must be 5-9)', value_str)
        
        return df
    
    def validate_datetime_field(self, df: pd.DataFrame, field_name: str, 
                                required: bool = False) -> pd.DataFrame:
        """Validate a datetime field."""
        print(f"Validating {field_name}...")
        
        if field_name not in df.columns:
            if required:
                self.log_error(0, field_name, 'Required column not found in dataset')
            return df
        
        for idx, row in df.iterrows():
            value = row[field_name]
            
            if self.is_null_or_blank(value):
                if required:
                    self.log_error(idx, field_name, 'Required datetime field is null/blank')
                continue
            
            # Try to parse as datetime
            try:
                if not isinstance(value, (pd.Timestamp, datetime)):
                    parsed = pd.to_datetime(value, errors='raise')
                    df.at[idx, field_name] = parsed
                else:
                    parsed = value
                
                # Sanity check: reasonable date range (1990-2030)
                if parsed.year < 1990 or parsed.year > 2030:
                    self.log_error(idx, field_name, 
                                  f'Date out of reasonable range', parsed)
            
            except Exception as e:
                self.log_error(idx, field_name, 
                              f'Invalid datetime format', value)
        
        return df
    
    def validate_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate fields derived from TimeOfCall."""
        print("Validating derived time fields...")
        
        if 'TimeOfCall' not in df.columns:
            return df
        
        for idx, row in df.iterrows():
            time_of_call = row['TimeOfCall']
            
            if pd.isna(time_of_call):
                continue
            
            if not isinstance(time_of_call, (pd.Timestamp, datetime)):
                try:
                    time_of_call = pd.to_datetime(time_of_call)
                except:
                    continue
            
            # Validate cYear
            if 'cYear' in df.columns:
                expected_year = str(time_of_call.year)
                actual_year = str(row['cYear']) if not pd.isna(row['cYear']) else None
                
                if actual_year != expected_year:
                    self.log_fix(idx, 'cYear', actual_year, expected_year, 
                               'Derived from TimeOfCall')
                    df.at[idx, 'cYear'] = expected_year
            
            # Validate cMonth
            if 'cMonth' in df.columns:
                expected_month = time_of_call.strftime('%B')
                actual_month = row['cMonth'] if not pd.isna(row['cMonth']) else None
                
                if actual_month != expected_month:
                    self.log_fix(idx, 'cMonth', actual_month, expected_month, 
                               'Derived from TimeOfCall')
                    df.at[idx, 'cMonth'] = expected_month
            
            # Validate Hour
            if 'Hour' in df.columns:
                expected_hour = time_of_call.strftime('%H:%M')
                actual_hour = row['Hour'] if not pd.isna(row['Hour']) else None
                
                # Handle various hour formats
                if actual_hour and isinstance(actual_hour, str):
                    actual_hour = actual_hour.strip()
                
                if actual_hour != expected_hour:
                    self.log_fix(idx, 'Hour', actual_hour, expected_hour, 
                               'Derived from TimeOfCall')
                    df.at[idx, 'Hour'] = expected_hour
            
            # Validate DayofWeek
            if 'DayofWeek' in df.columns:
                expected_dow = time_of_call.strftime('%A')
                actual_dow = row['DayofWeek'] if not pd.isna(row['DayofWeek']) else None
                
                if actual_dow != expected_dow:
                    self.log_fix(idx, 'DayofWeek', actual_dow, expected_dow, 
                               'Derived from TimeOfCall')
                    df.at[idx, 'DayofWeek'] = expected_dow
        
        return df
    
    def validate_time_sequence(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate that time fields follow logical sequence."""
        print("Validating time sequence...")
        
        time_fields = ['TimeOfCall', 'Time Dispatched', 'Time Out', 'Time In']
        available_fields = [f for f in time_fields if f in df.columns]
        
        if len(available_fields) < 2:
            return df
        
        for idx, row in df.iterrows():
            times = {}
            
            # Collect all non-null times
            for field in available_fields:
                value = row[field]
                if not pd.isna(value):
                    if isinstance(value, (pd.Timestamp, datetime)):
                        times[field] = value
                    else:
                        try:
                            times[field] = pd.to_datetime(value)
                        except:
                            continue
            
            # Check sequence
            if len(times) >= 2:
                time_list = [(field, times[field]) for field in available_fields if field in times]
                
                for i in range(len(time_list) - 1):
                    field1, time1 = time_list[i]
                    field2, time2 = time_list[i + 1]
                    
                    if time1 > time2:
                        self.log_error(idx, field2, 
                                      f'{field1} ({time1}) is after {field2} ({time2})')
        
        return df
    
    def validate_disposition(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate Disposition field."""
        print("Validating Disposition...")
        
        if 'Disposition' not in df.columns:
            self.log_warning(0, 'Disposition', 'Column not found in dataset')
            return df
        
        for idx, row in df.iterrows():
            value = row['Disposition']
            
            if self.is_null_or_blank(value):
                continue  # Optional field
            
            value_str = str(value).strip()
            
            # Check against valid domain
            if value_str not in self.valid_dispositions:
                # Try to match case-insensitively
                matched = False
                for valid in self.valid_dispositions:
                    if value_str.lower() == valid.lower():
                        self.log_fix(idx, 'Disposition', value_str, valid, 
                                   'Normalized to standard casing')
                        df.at[idx, 'Disposition'] = valid
                        matched = True
                        break
                
                if not matched:
                    self.log_error(idx, 'Disposition', 
                                  f'Invalid value (not in allowed list)', value_str)
        
        return df
    
    def validate_coordinates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate latitude and longitude fields."""
        print("Validating coordinates...")
        
        # Check latitude
        if 'latitude' in df.columns:
            for idx, row in df.iterrows():
                value = row['latitude']
                
                if self.is_null_or_blank(value):
                    continue  # Optional field
                
                try:
                    lat = float(value)
                    if lat < -90 or lat > 90:
                        self.log_error(idx, 'latitude', 
                                      f'Latitude out of range [-90, 90]', lat)
                except (ValueError, TypeError):
                    self.log_error(idx, 'latitude', 
                                  'Invalid numeric value', value)
        
        # Check longitude
        if 'longitude' in df.columns:
            for idx, row in df.iterrows():
                value = row['longitude']
                
                if self.is_null_or_blank(value):
                    continue  # Optional field
                
                try:
                    lon = float(value)
                    if lon < -180 or lon > 180:
                        self.log_error(idx, 'longitude', 
                                      f'Longitude out of range [-180, 180]', lon)
                except (ValueError, TypeError):
                    self.log_error(idx, 'longitude', 
                                  'Invalid numeric value', value)
        
        return df
    
    def validate_officer(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate Officer field."""
        print("Validating Officer...")
        
        if 'Officer' not in df.columns:
            self.log_warning(0, 'Officer', 'Column not found in dataset')
            return df
        
        for idx, row in df.iterrows():
            value = row['Officer']
            
            if self.is_null_or_blank(value):
                self.log_warning(idx, 'Officer', 
                               'Officer is blank (can be backfilled from RMS)')
        
        return df
    
    def validate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run all validation checks."""
        print(f"\n{'='*60}")
        print("CAD Export Validation Starting...")
        print(f"{'='*60}\n")
        
        self.stats['total_rows'] = len(df)
        print(f"Total rows to validate: {len(df):,}\n")
        
        # Run all validators
        df = self.validate_report_number(df)
        df = self.validate_incident(df)
        df = self.validate_how_reported(df)
        df = self.validate_address(df)
        df = self.validate_zone(df)
        
        # Validate datetime fields
        df = self.validate_datetime_field(df, 'TimeOfCall', required=True)
        df = self.validate_datetime_field(df, 'Time Dispatched', required=False)
        df = self.validate_datetime_field(df, 'Time Out', required=False)
        df = self.validate_datetime_field(df, 'Time In', required=False)
        
        # Validate derived fields and sequences
        df = self.validate_derived_fields(df)
        df = self.validate_time_sequence(df)
        
        # Validate other fields
        df = self.validate_disposition(df)
        df = self.validate_officer(df)
        df = self.validate_coordinates(df)
        
        print(f"\n{'='*60}")
        print("Validation Complete!")
        print(f"{'='*60}\n")
        
        return df
    
    def generate_report(self) -> str:
        """Generate a validation summary report."""
        report = []
        report.append("=" * 80)
        report.append("CAD EXPORT VALIDATION SUMMARY REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall stats
        report.append("OVERALL STATISTICS")
        report.append("-" * 80)
        report.append(f"Total rows processed:     {self.stats['total_rows']:,}")
        report.append(f"Rows with errors:         {len(self.stats['rows_with_errors']):,}")
        report.append(f"Total errors found:       {len(self.errors):,}")
        report.append(f"Total warnings:           {len(self.warnings):,}")
        report.append(f"Total fixes applied:      {len(self.fixes):,}")
        
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
        
        # Top errors (first 50)
        if self.errors:
            report.append("TOP ERRORS (First 50)")
            report.append("-" * 80)
            for error in self.errors[:50]:
                report.append(f"Row {error['row']:>6} | {error['field']:20s} | {error['message']}")
                if error['value'] != 'NULL':
                    report.append(f"           Value: {error['value']}")
            if len(self.errors) > 50:
                report.append(f"\n... and {len(self.errors) - 50:,} more errors")
            report.append("")
        
        # Sample fixes (first 20)
        if self.fixes:
            report.append("SAMPLE FIXES APPLIED (First 20)")
            report.append("-" * 80)
            for fix in self.fixes[:20]:
                report.append(f"Row {fix['row']:>6} | {fix['field']:20s} | {fix['reason']}")
                report.append(f"           {fix['old_value']} -> {fix['new_value']}")
            if len(self.fixes) > 20:
                report.append(f"\n... and {len(self.fixes) - 20:,} more fixes")
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
    
    print(f"\nInput file: {input_file}")
    print(f"Output directory: {output_dir}\n")
    
    # Check if file exists
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        return
    
    # Load data
    print("Loading Excel file...")
    try:
        df = pd.read_excel(input_file, dtype=str)
        print(f"Loaded {len(df):,} rows and {len(df.columns)} columns")
        print(f"Columns: {', '.join(df.columns.tolist()[:10])}...")
    except Exception as e:
        print(f"ERROR loading file: {e}")
        return
    
    # Create validator and run validation
    validator = CADValidator()
    df_clean = validator.validate_all(df)
    
    # Generate report
    report_text = validator.generate_report()
    try:
        print("\n" + report_text)
    except UnicodeEncodeError:
        # Fallback for console encoding issues
        print("\n[Report generated - see output file for full details]")
    
    # Save outputs
    print("\nSaving outputs...")
    
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
    
    # Save detailed fixes
    if validator.fixes:
        print(f"  Saving fix details to: {output_fixes}")
        fixes_df = pd.DataFrame(validator.fixes)
        fixes_df.to_csv(output_fixes, index=False, encoding='utf-8-sig')
    
    print("\n[SUCCESS] Validation complete!")
    print(f"\nSummary:")
    print(f"  - {len(validator.errors):,} errors found")
    print(f"  - {len(validator.fixes):,} fixes applied")
    print(f"  - {len(validator.warnings):,} warnings issued")
    print(f"  - {len(validator.stats['rows_with_errors']):,} rows affected")


if __name__ == "__main__":
    main()

