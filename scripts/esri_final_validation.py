"""
ESRI Final Export Quality Validation Script

Validates the CAD ESRI final export file against the standards defined in
CAD_Data_Cleaning_Engine.md.

This script performs comprehensive validation across 12 categories:
1. Schema Validation
2. TimeOfCall Validation
3. Response_Type Validation
4. How Reported Validation
5. FullAddress2 Validation
6. ReportNumberNew Validation
7. Officer Validation
8. Disposition Validation
9. Grid and PDZone Validation
10. Incident Validation
11. Latitude/Longitude Validation
12. Data Quality Flags

Output: Markdown validation report and CSV files for invalid records
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ESRIFinalValidator:
    """Comprehensive ESRI final export validator."""

    def __init__(self, input_file: str, output_dir: str = "data/02_reports"):
        """Initialize validator with file paths."""
        self.input_file = input_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Define expected schema
        self.required_columns = [
            'TimeOfCall', 'cYear', 'cMonth', 'Hour', 'DayofWeek',
            'Incident', 'Response_Type', 'How Reported', 'FullAddress2',
            'Grid', 'PDZone', 'Officer', 'Disposition', 'ReportNumberNew',
            'Latitude', 'Longitude', 'data_quality_flag'
        ]

        # Define valid How Reported values
        self.valid_how_reported = [
            '9-1-1', 'Walk-In', 'Phone', 'Self-Initiated', 'Radio',
            'Teletype', 'Fax', 'Other - See Notes', 'eMail', 'Mail',
            'Virtual Patrol', 'Canceled Call'
        ]

        # Define valid Response_Type values
        self.valid_response_types = ['Emergency', 'Urgent', 'Routine', 'Administrative']

        # Define Beat to PDZone mapping
        self.beat_to_pdzone = {
            'E1': '5', 'E2': '5', 'E3': '5',
            'F1': '6', 'F2': '6', 'F3': '6',
            'G1': '7', 'G2': '7', 'G3': '7', 'G4': '7', 'G5': '7',
            'H1': '8', 'H2': '8', 'H3': '8', 'H4': '8', 'H5': '8',
            'I1': '9', 'I2': '9', 'I3': '9', 'I4': '9A', 'I5': '9', 'I6': '9'
        }

        # Validation results
        self.validation_results = {}
        self.invalid_records = {}

    def load_data(self) -> pd.DataFrame:
        """Load ESRI export file."""
        logger.info(f"Loading data from {self.input_file}...")
        df = pd.read_excel(self.input_file)
        logger.info(f"Loaded {len(df):,} records")
        return df

    def validate_schema(self, df: pd.DataFrame) -> dict:
        """Validate schema and column presence."""
        logger.info("Validating schema...")

        actual_columns = list(df.columns)
        missing_columns = [col for col in self.required_columns if col not in actual_columns]
        unexpected_columns = [col for col in actual_columns if col not in self.required_columns]

        result = {
            'status': 'PASS' if not missing_columns else 'FAIL',
            'total_columns': len(actual_columns),
            'required_columns': len(self.required_columns),
            'missing_columns': missing_columns,
            'unexpected_columns': unexpected_columns,
            'column_list': actual_columns
        }

        return result

    def validate_timeofcall(self, df: pd.DataFrame) -> dict:
        """Validate TimeOfCall field and derived fields."""
        logger.info("Validating TimeOfCall and derived fields...")

        # Check for null values
        null_count = df['TimeOfCall'].isna().sum()

        # Validate format
        valid_format_count = 0
        if 'TimeOfCall' in df.columns:
            valid_format_count = df['TimeOfCall'].notna().sum()

        # Validate derived fields
        cyear_issues = 0
        cmonth_issues = 0
        hour_issues = 0
        dayofweek_issues = 0

        # Check cYear
        if 'cYear' in df.columns:
            df_check = df[df['TimeOfCall'].notna()].copy()
            df_check['expected_year'] = df_check['TimeOfCall'].dt.year.astype(str)
            cyear_issues = (df_check['cYear'] != df_check['expected_year']).sum()

        # Check cMonth
        if 'cMonth' in df.columns:
            df_check = df[df['TimeOfCall'].notna()].copy()
            df_check['expected_month'] = df_check['TimeOfCall'].dt.strftime('%B')
            cmonth_issues = (df_check['cMonth'] != df_check['expected_month']).sum()

        # Check Hour
        if 'Hour' in df.columns:
            df_check = df[df['TimeOfCall'].notna()].copy()
            df_check['expected_hour'] = df_check['TimeOfCall'].dt.strftime('%H:00')
            hour_issues = (df_check['Hour'] != df_check['expected_hour']).sum()

        # Check DayofWeek
        if 'DayofWeek' in df.columns:
            df_check = df[df['TimeOfCall'].notna()].copy()
            df_check['expected_dayofweek'] = df_check['TimeOfCall'].dt.strftime('%A')
            dayofweek_issues = (df_check['DayofWeek'] != df_check['expected_dayofweek']).sum()

        result = {
            'status': 'PASS' if null_count == 0 and cyear_issues == 0 and cmonth_issues == 0 and hour_issues == 0 and dayofweek_issues == 0 else 'FAIL',
            'null_count': int(null_count),
            'valid_format_count': int(valid_format_count),
            'total_records': len(df),
            'cyear_issues': int(cyear_issues),
            'cmonth_issues': int(cmonth_issues),
            'hour_issues': int(hour_issues),
            'dayofweek_issues': int(dayofweek_issues)
        }

        return result

    def validate_response_type(self, df: pd.DataFrame) -> dict:
        """Validate Response_Type field."""
        logger.info("Validating Response_Type...")

        total = len(df)
        null_count = df['Response_Type'].isna().sum()

        # Check for valid values
        valid_mask = df['Response_Type'].isin(self.valid_response_types)
        valid_count = valid_mask.sum()
        invalid_count = (~valid_mask & df['Response_Type'].notna()).sum()

        coverage = ((total - null_count) / total * 100) if total > 0 else 0

        # Get distribution
        distribution = df['Response_Type'].value_counts(dropna=False).to_dict()

        result = {
            'status': 'PASS' if coverage >= 99 and invalid_count == 0 else 'FAIL',
            'total_records': total,
            'null_count': int(null_count),
            'valid_count': int(valid_count),
            'invalid_count': int(invalid_count),
            'coverage_percent': round(coverage, 2),
            'distribution': {str(k): int(v) for k, v in distribution.items()}
        }

        return result

    def validate_how_reported(self, df: pd.DataFrame) -> dict:
        """Validate How Reported field."""
        logger.info("Validating How Reported...")

        total = len(df)
        null_count = df['How Reported'].isna().sum()

        # Check for valid values
        valid_mask = df['How Reported'].isin(self.valid_how_reported)
        valid_count = valid_mask.sum()
        invalid_count = (~valid_mask & df['How Reported'].notna()).sum()

        # Get invalid values
        invalid_values = df.loc[~valid_mask & df['How Reported'].notna(), 'How Reported'].value_counts().to_dict()

        result = {
            'status': 'PASS' if null_count == 0 and invalid_count == 0 else 'FAIL',
            'total_records': total,
            'null_count': int(null_count),
            'valid_count': int(valid_count),
            'invalid_count': int(invalid_count),
            'invalid_values': {str(k): int(v) for k, v in list(invalid_values.items())[:10]}
        }

        return result

    def validate_fulladdress2(self, df: pd.DataFrame) -> dict:
        """Validate FullAddress2 field."""
        logger.info("Validating FullAddress2...")

        total = len(df)
        null_count = df['FullAddress2'].isna().sum()

        # Define patterns for valid addresses
        # Standard address: starts with number, has street type, city, state, zip
        standard_pattern = r'^\d+\s+[A-Z\s]+\s+(STREET|AVENUE|ROAD|DRIVE|COURT|LANE|BOULEVARD|PLACE|PARKWAY|WAY|TERRACE|CIRCLE)\s*,?\s*[A-Z\s]+,\s*[A-Z]{2}\s+\d{5}'

        # Intersection: two streets with & separator
        intersection_pattern = r'^[A-Z\s]+\s+(STREET|AVENUE|ROAD|DRIVE|COURT|LANE|BOULEVARD|PLACE|PARKWAY|WAY|TERRACE|CIRCLE)\s*&\s*[A-Z\s]+\s+(STREET|AVENUE|ROAD|DRIVE|COURT|LANE|BOULEVARD|PLACE|PARKWAY|WAY|TERRACE|CIRCLE)\s*,?\s*[A-Z\s]+,\s*[A-Z]{2}\s+\d{5}'

        # Check valid addresses
        df_check = df[df['FullAddress2'].notna()].copy()
        df_check['addr_upper'] = df_check['FullAddress2'].astype(str).str.upper().str.strip()

        standard_valid = df_check['addr_upper'].str.contains(standard_pattern, regex=True, na=False)
        intersection_valid = df_check['addr_upper'].str.contains(intersection_pattern, regex=True, na=False)

        valid_mask = standard_valid | intersection_valid
        valid_count = valid_mask.sum()
        invalid_count = (~valid_mask).sum()

        # Identify invalid patterns
        invalid_patterns = {
            'no_street_number': (~df_check['addr_upper'].str.match(r'^\d+', na=False) & ~df_check['addr_upper'].str.contains('&', na=False)).sum(),
            'no_street_type': (~df_check['addr_upper'].str.contains(r'(STREET|AVENUE|ROAD|DRIVE|COURT|LANE|BOULEVARD|PLACE|PARKWAY|WAY|TERRACE|CIRCLE)', na=False)).sum(),
            'po_box': df_check['addr_upper'].str.contains(r'P\.?O\.?\s*BOX', regex=True, na=False).sum(),
            'generic_text': df_check['addr_upper'].str.contains(r'(VARIOUS|UNKNOWN|REAR LOT|PARKING GARAGE|^HOME$)', regex=True, na=False).sum()
        }

        # Store invalid addresses for CSV output
        if invalid_count > 0:
            invalid_df = df_check[~valid_mask].copy()
            invalid_df = invalid_df[['ReportNumberNew', 'TimeOfCall', 'FullAddress2', 'Incident']].head(1000)
            self.invalid_records['invalid_addresses'] = invalid_df

        result = {
            'status': 'PASS' if (valid_count / (total - null_count) * 100) >= 90 else 'WARNING',
            'total_records': total,
            'null_count': int(null_count),
            'valid_count': int(valid_count),
            'invalid_count': int(invalid_count),
            'valid_percent': round((valid_count / (total - null_count) * 100) if (total - null_count) > 0 else 0, 2),
            'invalid_patterns': {k: int(v) for k, v in invalid_patterns.items()}
        }

        return result

    def validate_reportnumbernew(self, df: pd.DataFrame) -> dict:
        """Validate ReportNumberNew field."""
        logger.info("Validating ReportNumberNew...")

        total = len(df)
        null_count = df['ReportNumberNew'].isna().sum()

        # Define valid pattern: YY-XXXXXX or YY-XXXXXXA
        valid_pattern = r'^\d{2}-\d{6}[A-Z]?$'

        df_check = df[df['ReportNumberNew'].notna()].copy()
        valid_mask = df_check['ReportNumberNew'].astype(str).str.match(valid_pattern, na=False)
        valid_count = valid_mask.sum()
        invalid_count = (~valid_mask).sum()

        # Check for duplicates
        duplicates = df_check[df_check['ReportNumberNew'].duplicated(keep=False)]
        duplicate_count = len(duplicates)

        # Store invalid case numbers for CSV output
        if invalid_count > 0:
            invalid_df = df_check[~valid_mask].copy()
            invalid_df = invalid_df[['ReportNumberNew', 'TimeOfCall', 'Incident']].head(1000)
            self.invalid_records['invalid_case_numbers'] = invalid_df

        result = {
            'status': 'PASS' if invalid_count == 0 and duplicate_count == 0 else 'FAIL',
            'total_records': total,
            'null_count': int(null_count),
            'valid_count': int(valid_count),
            'invalid_count': int(invalid_count),
            'duplicate_count': duplicate_count,
            'valid_percent': round((valid_count / (total - null_count) * 100) if (total - null_count) > 0 else 0, 2)
        }

        return result

    def validate_officer(self, df: pd.DataFrame) -> dict:
        """Validate Officer field."""
        logger.info("Validating Officer...")

        total = len(df)
        null_count = df['Officer'].isna().sum()

        # Define valid pattern: RANK FirstName LastName BadgeNumber
        valid_pattern = r'^([A-Z]{2,4}\.)\s+([A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s+([A-Za-z]+(?:-[A-Za-z]+)*(?:\s[A-Za-z]+(?:-[A-Za-z]+)*)*)\s+(\d{2,4})$'

        df_check = df[df['Officer'].notna()].copy()
        valid_mask = df_check['Officer'].astype(str).str.match(valid_pattern, na=False)
        valid_count = valid_mask.sum()
        invalid_count = (~valid_mask).sum()

        # Store invalid officers for CSV output
        if invalid_count > 0:
            invalid_df = df_check[~valid_mask].copy()
            invalid_df = invalid_df[['ReportNumberNew', 'TimeOfCall', 'Officer', 'Incident']].head(1000)
            self.invalid_records['invalid_officers'] = invalid_df

        result = {
            'status': 'WARNING' if invalid_count > 0 else 'PASS',
            'total_records': total,
            'null_count': int(null_count),
            'valid_count': int(valid_count),
            'invalid_count': int(invalid_count),
            'valid_percent': round((valid_count / (total - null_count) * 100) if (total - null_count) > 0 else 0, 2)
        }

        return result

    def validate_disposition(self, df: pd.DataFrame) -> dict:
        """Validate Disposition field."""
        logger.info("Validating Disposition...")

        total = len(df)
        null_count = df['Disposition'].isna().sum()

        # Get distribution
        distribution = df['Disposition'].value_counts(dropna=False).head(20).to_dict()

        result = {
            'status': 'PASS' if null_count == 0 else 'FAIL',
            'total_records': total,
            'null_count': int(null_count),
            'unique_values': int(df['Disposition'].nunique(dropna=False)),
            'distribution': {str(k): int(v) for k, v in distribution.items()}
        }

        return result

    def validate_grid_pdzone(self, df: pd.DataFrame) -> dict:
        """Validate Grid and PDZone fields."""
        logger.info("Validating Grid and PDZone...")

        total = len(df)
        grid_null = df['Grid'].isna().sum()
        pdzone_null = df['PDZone'].isna().sum()

        # Check valid Grid values (Beat values)
        valid_grids = list(self.beat_to_pdzone.keys())
        grid_valid = df['Grid'].isin(valid_grids).sum()
        grid_invalid = (~df['Grid'].isin(valid_grids) & df['Grid'].notna()).sum()

        # Check valid PDZone values
        valid_pdzones = ['5', '6', '7', '8', '9', '9A']
        pdzone_valid = df['PDZone'].isin(valid_pdzones).sum()
        pdzone_invalid = (~df['PDZone'].isin(valid_pdzones) & df['PDZone'].notna()).sum()

        # Check Grid to PDZone mapping
        mapping_issues = 0
        df_check = df[(df['Grid'].notna()) & (df['PDZone'].notna())].copy()
        for idx, row in df_check.iterrows():
            expected_pdzone = self.beat_to_pdzone.get(str(row['Grid']), None)
            if expected_pdzone and str(row['PDZone']) != expected_pdzone:
                mapping_issues += 1

        result = {
            'status': 'WARNING' if grid_invalid > 0 or pdzone_invalid > 0 or mapping_issues > 0 else 'PASS',
            'total_records': total,
            'grid_null_count': int(grid_null),
            'pdzone_null_count': int(pdzone_null),
            'grid_valid_count': int(grid_valid),
            'grid_invalid_count': int(grid_invalid),
            'pdzone_valid_count': int(pdzone_valid),
            'pdzone_invalid_count': int(pdzone_invalid),
            'mapping_issues': mapping_issues
        }

        return result

    def validate_incident(self, df: pd.DataFrame) -> dict:
        """Validate Incident field."""
        logger.info("Validating Incident...")

        total = len(df)
        null_count = df['Incident'].isna().sum()

        # Check for mojibake characters
        df_check = df[df['Incident'].notna()].copy()
        mojibake_pattern = r'[^\x00-\x7F]+'
        mojibake_count = df_check['Incident'].astype(str).str.contains(mojibake_pattern, regex=True, na=False).sum()

        # Get top incidents
        top_incidents = df['Incident'].value_counts(dropna=False).head(20).to_dict()

        # Check for case sensitivity duplicates
        incident_lower = df_check['Incident'].astype(str).str.lower()
        case_duplicates = len(df_check['Incident'].unique()) - len(incident_lower.unique())

        result = {
            'status': 'WARNING' if null_count > (total * 0.01) else 'PASS',
            'total_records': total,
            'null_count': int(null_count),
            'null_percent': round((null_count / total * 100) if total > 0 else 0, 2),
            'unique_values': int(df['Incident'].nunique(dropna=True)),
            'mojibake_count': int(mojibake_count),
            'case_duplicates': case_duplicates,
            'top_incidents': {str(k): int(v) for k, v in list(top_incidents.items())[:10]}
        }

        return result

    def validate_coordinates(self, df: pd.DataFrame) -> dict:
        """Validate Latitude and Longitude fields."""
        logger.info("Validating Latitude and Longitude...")

        total = len(df)
        lat_null = df['Latitude'].isna().sum()
        lon_null = df['Longitude'].isna().sum()

        # Check valid ranges
        df_check = df[(df['Latitude'].notna()) & (df['Longitude'].notna())].copy()

        lat_valid = ((df_check['Latitude'] >= -90) & (df_check['Latitude'] <= 90)).sum()
        lon_valid = ((df_check['Longitude'] >= -180) & (df_check['Longitude'] <= 180)).sum()

        lat_invalid = len(df_check) - lat_valid
        lon_invalid = len(df_check) - lon_valid

        # Check Hackensack range (approximately)
        hackensack_lat_range = (40.85, 40.91)
        hackensack_lon_range = (-74.07, -74.01)

        in_hackensack = (
            (df_check['Latitude'] >= hackensack_lat_range[0]) &
            (df_check['Latitude'] <= hackensack_lat_range[1]) &
            (df_check['Longitude'] >= hackensack_lon_range[0]) &
            (df_check['Longitude'] <= hackensack_lon_range[1])
        ).sum()

        result = {
            'status': 'INFO',
            'total_records': total,
            'lat_null_count': int(lat_null),
            'lon_null_count': int(lon_null),
            'lat_valid_count': int(lat_valid),
            'lon_valid_count': int(lon_valid),
            'lat_invalid_count': int(lat_invalid),
            'lon_invalid_count': int(lon_invalid),
            'in_hackensack_range': int(in_hackensack),
            'null_percent': round((lat_null / total * 100) if total > 0 else 0, 2)
        }

        return result

    def validate_data_quality_flags(self, df: pd.DataFrame) -> dict:
        """Validate data_quality_flag field."""
        logger.info("Validating data_quality_flag...")

        total = len(df)

        # Get distribution of flags
        distribution = df['data_quality_flag'].value_counts(dropna=False).to_dict()
        flagged_count = (df['data_quality_flag'] != 0).sum()

        result = {
            'status': 'INFO',
            'total_records': total,
            'flagged_count': int(flagged_count),
            'flagged_percent': round((flagged_count / total * 100) if total > 0 else 0, 2),
            'distribution': {str(k): int(v) for k, v in distribution.items()}
        }

        return result

    def calculate_overall_score(self) -> dict:
        """Calculate overall data quality score."""
        logger.info("Calculating overall data quality score...")

        # Weight each validation category
        weights = {
            'schema': 10,
            'timeofcall': 10,
            'response_type': 15,
            'how_reported': 15,
            'fulladdress2': 10,
            'reportnumbernew': 10,
            'officer': 5,
            'disposition': 10,
            'grid_pdzone': 5,
            'incident': 10,
            'coordinates': 0,  # Informational only
            'data_quality_flags': 0  # Informational only
        }

        scores = {}
        for category, result in self.validation_results.items():
            if category not in weights or weights[category] == 0:
                continue

            status = result.get('status', 'INFO')
            if status == 'PASS':
                scores[category] = weights[category]
            elif status == 'WARNING':
                scores[category] = weights[category] * 0.75
            elif status == 'FAIL':
                scores[category] = 0
            else:
                scores[category] = weights[category]  # INFO gets full credit

        total_score = sum(scores.values())
        max_score = sum(w for w in weights.values() if w > 0)

        overall_percent = (total_score / max_score * 100) if max_score > 0 else 0

        return {
            'total_score': round(total_score, 2),
            'max_score': max_score,
            'overall_percent': round(overall_percent, 2),
            'category_scores': scores
        }

    def generate_markdown_report(self) -> str:
        """Generate comprehensive validation report in markdown format."""
        logger.info("Generating markdown report...")

        overall = self.calculate_overall_score()

        # Determine overall pass/fail status
        overall_status = "PASS" if overall['overall_percent'] >= 95 else "FAIL"

        report = f"""# CAD ESRI Final Export Validation Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Input File:** {self.input_file}
**Overall Status:** {overall_status}
**Data Quality Score:** {overall['overall_percent']:.1f}% ({overall['total_score']:.1f}/{overall['max_score']})

---

## Executive Summary

"""

        # Add executive summary
        if overall_status == "PASS":
            report += "✅ **VALIDATION PASSED** - All critical validation checks passed with acceptable thresholds.\n\n"
        else:
            report += "❌ **VALIDATION FAILED** - One or more critical validation checks failed. Review findings below.\n\n"

        # Summary statistics
        schema_result = self.validation_results.get('schema', {})
        report += f"""### Key Statistics

- **Total Records:** {schema_result.get('total_columns', 'N/A'):,} (Expected: {len(self.required_columns)})
- **Data Quality Score:** {overall['overall_percent']:.1f}%
- **Critical Failures:** {sum(1 for r in self.validation_results.values() if r.get('status') == 'FAIL')}
- **Warnings:** {sum(1 for r in self.validation_results.values() if r.get('status') == 'WARNING')}

---

## Detailed Validation Results

"""

        # 1. Schema Validation
        report += self._format_schema_section()

        # 2. TimeOfCall Validation
        report += self._format_timeofcall_section()

        # 3. Response_Type Validation
        report += self._format_response_type_section()

        # 4. How Reported Validation
        report += self._format_how_reported_section()

        # 5. FullAddress2 Validation
        report += self._format_fulladdress2_section()

        # 6. ReportNumberNew Validation
        report += self._format_reportnumbernew_section()

        # 7. Officer Validation
        report += self._format_officer_section()

        # 8. Disposition Validation
        report += self._format_disposition_section()

        # 9. Grid and PDZone Validation
        report += self._format_grid_pdzone_section()

        # 10. Incident Validation
        report += self._format_incident_section()

        # 11. Latitude/Longitude Validation
        report += self._format_coordinates_section()

        # 12. Data Quality Flags
        report += self._format_data_quality_flags_section()

        # Recommendations
        report += self._format_recommendations_section()

        return report

    def _format_schema_section(self) -> str:
        """Format schema validation section."""
        result = self.validation_results.get('schema', {})
        status_icon = "✅" if result.get('status') == 'PASS' else "❌"

        section = f"""### 1. Schema Validation {status_icon}

**Status:** {result.get('status', 'N/A')}

- **Total Columns:** {result.get('total_columns', 0)}
- **Required Columns:** {result.get('required_columns', 0)}
- **Missing Columns:** {len(result.get('missing_columns', []))}
- **Unexpected Columns:** {len(result.get('unexpected_columns', []))}

"""

        if result.get('missing_columns'):
            section += f"**Missing:** {', '.join(result['missing_columns'])}\n\n"

        if result.get('unexpected_columns'):
            section += f"**Unexpected:** {', '.join(result['unexpected_columns'])}\n\n"

        return section

    def _format_timeofcall_section(self) -> str:
        """Format TimeOfCall validation section."""
        result = self.validation_results.get('timeofcall', {})
        status_icon = "✅" if result.get('status') == 'PASS' else "❌"

        section = f"""### 2. TimeOfCall Validation {status_icon}

**Status:** {result.get('status', 'N/A')}

- **Total Records:** {result.get('total_records', 0):,}
- **Null Values:** {result.get('null_count', 0):,}
- **Valid Format:** {result.get('valid_format_count', 0):,}

**Derived Field Issues:**
- **cYear Issues:** {result.get('cyear_issues', 0):,}
- **cMonth Issues:** {result.get('cmonth_issues', 0):,}
- **Hour Issues:** {result.get('hour_issues', 0):,}
- **DayofWeek Issues:** {result.get('dayofweek_issues', 0):,}

"""
        return section

    def _format_response_type_section(self) -> str:
        """Format Response_Type validation section."""
        result = self.validation_results.get('response_type', {})
        status_icon = "✅" if result.get('status') == 'PASS' else "⚠️" if result.get('status') == 'WARNING' else "❌"

        section = f"""### 3. Response_Type Validation {status_icon}

**Status:** {result.get('status', 'N/A')}

- **Total Records:** {result.get('total_records', 0):,}
- **Coverage:** {result.get('coverage_percent', 0):.2f}%
- **Valid Values:** {result.get('valid_count', 0):,}
- **Invalid Values:** {result.get('invalid_count', 0):,}
- **Null Values:** {result.get('null_count', 0):,}

**Distribution:**
"""

        for value, count in result.get('distribution', {}).items():
            pct = (count / result.get('total_records', 1) * 100)
            section += f"- {value}: {count:,} ({pct:.2f}%)\n"

        section += "\n"
        return section

    def _format_how_reported_section(self) -> str:
        """Format How Reported validation section."""
        result = self.validation_results.get('how_reported', {})
        status_icon = "✅" if result.get('status') == 'PASS' else "❌"

        section = f"""### 4. How Reported Validation {status_icon}

**Status:** {result.get('status', 'N/A')}

- **Total Records:** {result.get('total_records', 0):,}
- **Null Values:** {result.get('null_count', 0):,}
- **Valid Values:** {result.get('valid_count', 0):,}
- **Invalid Values:** {result.get('invalid_count', 0):,}

"""

        if result.get('invalid_values'):
            section += "**Top Invalid Values:**\n"
            for value, count in list(result['invalid_values'].items())[:10]:
                section += f"- {value}: {count:,}\n"
            section += "\n"

        return section

    def _format_fulladdress2_section(self) -> str:
        """Format FullAddress2 validation section."""
        result = self.validation_results.get('fulladdress2', {})
        status_icon = "✅" if result.get('status') == 'PASS' else "⚠️" if result.get('status') == 'WARNING' else "❌"

        section = f"""### 5. FullAddress2 Validation {status_icon}

**Status:** {result.get('status', 'N/A')}

- **Total Records:** {result.get('total_records', 0):,}
- **Null Values:** {result.get('null_count', 0):,}
- **Valid Addresses:** {result.get('valid_count', 0):,} ({result.get('valid_percent', 0):.2f}%)
- **Invalid Addresses:** {result.get('invalid_count', 0):,}

**Invalid Pattern Breakdown:**
"""

        for pattern, count in result.get('invalid_patterns', {}).items():
            section += f"- {pattern.replace('_', ' ').title()}: {count:,}\n"

        section += "\n"
        return section

    def _format_reportnumbernew_section(self) -> str:
        """Format ReportNumberNew validation section."""
        result = self.validation_results.get('reportnumbernew', {})
        status_icon = "✅" if result.get('status') == 'PASS' else "❌"

        section = f"""### 6. ReportNumberNew Validation {status_icon}

**Status:** {result.get('status', 'N/A')}

- **Total Records:** {result.get('total_records', 0):,}
- **Null Values:** {result.get('null_count', 0):,}
- **Valid Format:** {result.get('valid_count', 0):,} ({result.get('valid_percent', 0):.2f}%)
- **Invalid Format:** {result.get('invalid_count', 0):,}
- **Duplicates:** {result.get('duplicate_count', 0):,}

"""
        return section

    def _format_officer_section(self) -> str:
        """Format Officer validation section."""
        result = self.validation_results.get('officer', {})
        status_icon = "✅" if result.get('status') == 'PASS' else "⚠️"

        section = f"""### 7. Officer Validation {status_icon}

**Status:** {result.get('status', 'N/A')}

- **Total Records:** {result.get('total_records', 0):,}
- **Null Values:** {result.get('null_count', 0):,}
- **Valid Format:** {result.get('valid_count', 0):,} ({result.get('valid_percent', 0):.2f}%)
- **Invalid Format:** {result.get('invalid_count', 0):,}

"""
        return section

    def _format_disposition_section(self) -> str:
        """Format Disposition validation section."""
        result = self.validation_results.get('disposition', {})
        status_icon = "✅" if result.get('status') == 'PASS' else "❌"

        section = f"""### 8. Disposition Validation {status_icon}

**Status:** {result.get('status', 'N/A')}

- **Total Records:** {result.get('total_records', 0):,}
- **Null Values:** {result.get('null_count', 0):,}
- **Unique Values:** {result.get('unique_values', 0):,}

**Top Disposition Values:**
"""

        for value, count in list(result.get('distribution', {}).items())[:10]:
            pct = (count / result.get('total_records', 1) * 100)
            section += f"- {value}: {count:,} ({pct:.2f}%)\n"

        section += "\n"
        return section

    def _format_grid_pdzone_section(self) -> str:
        """Format Grid/PDZone validation section."""
        result = self.validation_results.get('grid_pdzone', {})
        status_icon = "✅" if result.get('status') == 'PASS' else "⚠️"

        section = f"""### 9. Grid and PDZone Validation {status_icon}

**Status:** {result.get('status', 'N/A')}

**Grid:**
- **Null Values:** {result.get('grid_null_count', 0):,}
- **Valid Values:** {result.get('grid_valid_count', 0):,}
- **Invalid Values:** {result.get('grid_invalid_count', 0):,}

**PDZone:**
- **Null Values:** {result.get('pdzone_null_count', 0):,}
- **Valid Values:** {result.get('pdzone_valid_count', 0):,}
- **Invalid Values:** {result.get('pdzone_invalid_count', 0):,}

**Mapping Issues:** {result.get('mapping_issues', 0):,}

"""
        return section

    def _format_incident_section(self) -> str:
        """Format Incident validation section."""
        result = self.validation_results.get('incident', {})
        status_icon = "✅" if result.get('status') == 'PASS' else "⚠️"

        section = f"""### 10. Incident Validation {status_icon}

**Status:** {result.get('status', 'N/A')}

- **Total Records:** {result.get('total_records', 0):,}
- **Null Values:** {result.get('null_count', 0):,} ({result.get('null_percent', 0):.2f}%)
- **Unique Incidents:** {result.get('unique_values', 0):,}
- **Mojibake Characters:** {result.get('mojibake_count', 0):,}
- **Case Sensitivity Duplicates:** {result.get('case_duplicates', 0)}

**Top Incident Types:**
"""

        for value, count in list(result.get('top_incidents', {}).items())[:10]:
            pct = (count / result.get('total_records', 1) * 100)
            section += f"- {value}: {count:,} ({pct:.2f}%)\n"

        section += "\n"
        return section

    def _format_coordinates_section(self) -> str:
        """Format coordinates validation section."""
        result = self.validation_results.get('coordinates', {})

        section = f"""### 11. Latitude/Longitude Validation ℹ️

**Status:** {result.get('status', 'N/A')} (Informational)

- **Total Records:** {result.get('total_records', 0):,}
- **Null Coordinates:** {result.get('lat_null_count', 0):,} ({result.get('null_percent', 0):.2f}%)
- **Valid Latitude:** {result.get('lat_valid_count', 0):,}
- **Valid Longitude:** {result.get('lon_valid_count', 0):,}
- **In Hackensack Range:** {result.get('in_hackensack_range', 0):,}
- **Invalid Latitude:** {result.get('lat_invalid_count', 0):,}
- **Invalid Longitude:** {result.get('lon_invalid_count', 0):,}

"""
        return section

    def _format_data_quality_flags_section(self) -> str:
        """Format data quality flags section."""
        result = self.validation_results.get('data_quality_flags', {})

        section = f"""### 12. Data Quality Flags ℹ️

**Status:** {result.get('status', 'N/A')} (Informational)

- **Total Records:** {result.get('total_records', 0):,}
- **Flagged Records:** {result.get('flagged_count', 0):,} ({result.get('flagged_percent', 0):.2f}%)

**Flag Distribution:**
"""

        for flag, count in result.get('distribution', {}).items():
            pct = (count / result.get('total_records', 1) * 100)
            section += f"- Flag {flag}: {count:,} ({pct:.2f}%)\n"

        section += "\n"
        return section

    def _format_recommendations_section(self) -> str:
        """Format recommendations section."""
        section = "## Recommendations\n\n"

        recommendations = []

        # Check each validation result for issues
        if self.validation_results.get('response_type', {}).get('coverage_percent', 100) < 99:
            recommendations.append("- **Response_Type Coverage:** Coverage is below 99%. Review and populate missing Response_Type values.")

        if self.validation_results.get('how_reported', {}).get('invalid_count', 0) > 0:
            recommendations.append("- **How Reported:** Invalid values detected. Review and map to valid How Reported categories.")

        if self.validation_results.get('fulladdress2', {}).get('valid_percent', 100) < 90:
            recommendations.append("- **FullAddress2:** Address validity is below 90%. Review and correct invalid address formats.")

        if self.validation_results.get('reportnumbernew', {}).get('invalid_count', 0) > 0:
            recommendations.append("- **ReportNumberNew:** Invalid case number formats detected. Review and correct to YY-XXXXXX format.")

        if self.validation_results.get('disposition', {}).get('null_count', 0) > 0:
            recommendations.append("- **Disposition:** Null values detected. Populate all Disposition fields.")

        if self.validation_results.get('incident', {}).get('null_percent', 0) > 1:
            recommendations.append("- **Incident:** High percentage of null incidents. Continue RMS backfill process.")

        if not recommendations:
            section += "✅ No critical recommendations. All validation checks passed acceptable thresholds.\n\n"
        else:
            section += "\n".join(recommendations) + "\n\n"

        return section

    def save_reports(self, df: pd.DataFrame):
        """Save all validation reports and CSV files."""
        logger.info("Saving validation reports...")

        # Save markdown report
        report = self.generate_markdown_report()
        report_path = self.output_dir / f"esri_final_validation_{self.timestamp}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Saved validation report: {report_path}")

        # Save invalid records CSVs
        for record_type, invalid_df in self.invalid_records.items():
            csv_path = self.output_dir / f"{record_type}_{self.timestamp}.csv"
            invalid_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"Saved {record_type}: {csv_path}")

        # Save null critical fields CSV
        critical_fields = ['Incident', 'How Reported', 'Disposition', 'ReportNumberNew']
        null_mask = df[critical_fields].isna().any(axis=1)
        if null_mask.any():
            null_df = df[null_mask][['ReportNumberNew', 'TimeOfCall'] + critical_fields].head(1000)
            csv_path = self.output_dir / f"null_critical_fields_{self.timestamp}.csv"
            null_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"Saved null critical fields: {csv_path}")

    def run_validation(self):
        """Run complete validation workflow."""
        logger.info("Starting ESRI final validation...")

        # Load data
        df = self.load_data()

        # Run all validations
        self.validation_results['schema'] = self.validate_schema(df)
        self.validation_results['timeofcall'] = self.validate_timeofcall(df)
        self.validation_results['response_type'] = self.validate_response_type(df)
        self.validation_results['how_reported'] = self.validate_how_reported(df)
        self.validation_results['fulladdress2'] = self.validate_fulladdress2(df)
        self.validation_results['reportnumbernew'] = self.validate_reportnumbernew(df)
        self.validation_results['officer'] = self.validate_officer(df)
        self.validation_results['disposition'] = self.validate_disposition(df)
        self.validation_results['grid_pdzone'] = self.validate_grid_pdzone(df)
        self.validation_results['incident'] = self.validate_incident(df)
        self.validation_results['coordinates'] = self.validate_coordinates(df)
        self.validation_results['data_quality_flags'] = self.validate_data_quality_flags(df)

        # Save reports
        self.save_reports(df)

        # Print summary
        overall = self.calculate_overall_score()
        logger.info(f"\n{'='*60}")
        logger.info(f"VALIDATION COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Overall Score: {overall['overall_percent']:.1f}%")
        logger.info(f"Status: {'PASS' if overall['overall_percent'] >= 95 else 'FAIL'}")
        logger.info(f"{'='*60}\n")

        return self.validation_results


def main():
    """Main execution function."""
    import sys

    # Input file
    input_file = "data/ESRI_CADExport/CAD_ESRI_Final_20251117_v2.xlsx"

    # Allow command-line override
    if len(sys.argv) > 1:
        input_file = sys.argv[1]

    # Create validator and run
    validator = ESRIFinalValidator(input_file)
    results = validator.run_validation()

    print("\n✅ Validation complete! Check data/02_reports/ for detailed results.")


if __name__ == "__main__":
    main()
