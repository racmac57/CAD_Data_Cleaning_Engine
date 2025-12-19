"""
Full Pipeline Validator - Post-run validation checks

Validates that the CAD data correction pipeline completed successfully:
- Record count preservation
- Unique case count preservation
- Corrections applied verification
- Quality score validation
- Duplicate detection verification
- Audit trail completeness
- Output file integrity
"""

import sys
import pandas as pd
import numpy as np
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
import yaml

# Import utilities
sys.path.append(str(Path(__file__).parent.parent))

from utils.logger import setup_logger, log_validation_result
from utils.hash_utils import FileHashManager


class PipelineValidator:
    """Validates pipeline execution results."""

    def __init__(
        self,
        input_file: str,
        output_file: str,
        audit_file: Optional[str] = None,
        config_path: str = "config/config.yml"
    ):
        """
        Initialize pipeline validator.

        Args:
            input_file: Path to input file
            output_file: Path to output file
            audit_file: Path to audit trail file
            config_path: Path to configuration file
        """
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.audit_file = Path(audit_file) if audit_file else None
        self.config_path = config_path

        # Load configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # Setup logging
        self.logger = setup_logger(
            name="PipelineValidator",
            log_file=self.config['paths']['log_file'],
            level=logging.INFO,
            console_output=True
        )

        # Load data
        self.input_df = None
        self.output_df = None
        self.audit_df = None

        # Validation results
        self.validation_results = []
        self.passed = 0
        self.failed = 0

    def run_all_validations(self) -> bool:
        """
        Run all post-pipeline validation checks.

        Returns:
            True if all validations passed, False otherwise
        """
        self.logger.info("=" * 80)
        self.logger.info("CAD DATA CORRECTION FRAMEWORK - FULL PIPELINE VALIDATION")
        self.logger.info("=" * 80)
        self.logger.info(f"Input File: {self.input_file.name}")
        self.logger.info(f"Output File: {self.output_file.name}")
        self.logger.info("")

        # Load data files
        if not self._load_data():
            return False

        # Run validation checks
        self._check_file_exists()
        self._check_record_count_preserved()
        self._check_unique_cases_preserved()
        self._check_no_merge_artifacts()
        self._check_corrections_applied()
        self._check_hour_field_normalized()
        self._check_quality_scores()
        self._check_utf8_bom()
        self._check_audit_trail()
        self._check_duplicates_flagged()
        self._check_data_integrity()
        
        # Enhanced validation checks (from chunk 3 integration)
        self._check_case_number_format()
        self._check_address_completeness()
        self._check_time_sequence()
        self._check_how_reported_standardization()
        self._check_disposition_consistency()

        # Report results
        self._report_results()

        return self.failed == 0

    def _load_data(self) -> bool:
        """Load input, output, and audit files."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Loading Data Files")
        self.logger.info("-" * 80)

        try:
            # Load input file
            if self.input_file.suffix == '.xlsx':
                self.input_df = pd.read_excel(self.input_file)
            else:
                self.input_df = pd.read_csv(self.input_file, encoding='utf-8-sig')

            self.logger.info(f"Loaded input file: {len(self.input_df):,} records")

            # Load output file
            if not self.output_file.exists():
                self.logger.error(f"Output file not found: {self.output_file}")
                return False

            if self.output_file.suffix == '.xlsx':
                self.output_df = pd.read_excel(self.output_file)
            else:
                self.output_df = pd.read_csv(self.output_file, encoding='utf-8-sig')

            self.logger.info(f"Loaded output file: {len(self.output_df):,} records")

            # Load audit file if exists
            if self.audit_file and self.audit_file.exists():
                self.audit_df = pd.read_csv(self.audit_file, encoding='utf-8-sig')
                self.logger.info(f"Loaded audit file: {len(self.audit_df):,} entries")

            return True

        except Exception as e:
            self.logger.error(f"Error loading data files: {e}")
            return False

    def _add_result(self, check_name: str, passed: bool, message: str = ""):
        """Add validation result."""
        self.validation_results.append({
            'check': check_name,
            'passed': passed,
            'message': message
        })

        if passed:
            self.passed += 1
        else:
            self.failed += 1

        log_validation_result(self.logger, check_name, passed, message)

    def _check_file_exists(self):
        """Check that output file exists."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("File Existence Check")
        self.logger.info("-" * 80)

        exists = self.output_file.exists()
        if exists:
            size_mb = self.output_file.stat().st_size / 1024 / 1024
            self._add_result(
                "Output File Exists",
                True,
                f"{self.output_file.name} ({size_mb:.2f} MB)"
            )
        else:
            self._add_result(
                "Output File Exists",
                False,
                f"Not found: {self.output_file}"
            )

    def _check_record_count_preserved(self):
        """Verify that record count is preserved."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Record Count Check")
        self.logger.info("-" * 80)

        input_count = len(self.input_df)
        output_count = len(self.output_df)
        preserved = input_count == output_count

        self._add_result(
            "Record Count Preserved",
            preserved,
            f"Input: {input_count:,}, Output: {output_count:,} ({'preserved' if preserved else 'MISMATCH'})"
        )

    def _check_unique_cases_preserved(self):
        """Verify that unique case numbers are preserved."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Unique Case Numbers Check")
        self.logger.info("-" * 80)

        if 'ReportNumberNew' not in self.input_df.columns or 'ReportNumberNew' not in self.output_df.columns:
            self._add_result(
                "Unique Cases Preserved",
                False,
                "ReportNumberNew column not found"
            )
            return

        input_unique = self.input_df['ReportNumberNew'].nunique()
        output_unique = self.output_df['ReportNumberNew'].nunique()
        preserved = input_unique == output_unique

        self._add_result(
            "Unique Cases Preserved",
            preserved,
            f"Input: {input_unique:,}, Output: {output_unique:,} ({'preserved' if preserved else 'MISMATCH'})"
        )

    def _check_no_merge_artifacts(self):
        """Check for merge artifact duplicates."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Merge Artifacts Check")
        self.logger.info("-" * 80)

        # Check for duplicate case numbers
        if 'ReportNumberNew' in self.output_df.columns:
            duplicates = self.output_df['ReportNumberNew'].duplicated().sum()

            self._add_result(
                "No Merge Artifact Duplicates",
                duplicates == 0,
                f"Found {duplicates:,} duplicate case numbers"
            )

        # Check for merge artifact patterns
        merge_patterns = self.config.get('duplicate_detection', {}).get('merge_artifact_patterns', [])

        for pattern in merge_patterns:
            found_artifacts = 0
            for col in self.output_df.select_dtypes(include=['object']).columns:
                mask = self.output_df[col].astype(str).str.contains(pattern, case=False, na=False, regex=True)
                found_artifacts += mask.sum()

            self._add_result(
                f"No Merge Pattern: {pattern}",
                found_artifacts == 0,
                f"Found {found_artifacts:,} matches"
            )

    def _check_corrections_applied(self):
        """Verify that corrections were applied."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Corrections Applied Check")
        self.logger.info("-" * 80)

        # Check if audit trail exists
        if self.audit_df is not None and len(self.audit_df) > 0:
            correction_count = len(self.audit_df)

            self._add_result(
                "Corrections Applied",
                correction_count > 0,
                f"{correction_count:,} corrections recorded in audit trail"
            )

            # Check correction types
            if 'correction_type' in self.audit_df.columns:
                correction_types = self.audit_df['correction_type'].value_counts()
                self.logger.info("\nCorrection Types:")
                for corr_type, count in correction_types.items():
                    self.logger.info(f"  {corr_type}: {count:,}")

        else:
            self._add_result(
                "Corrections Applied",
                False,
                "Audit trail not found or empty"
            )

    def _check_hour_field_normalized(self):
        """Check that Hour field is properly extracted and normalized."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Hour Field Check")
        self.logger.info("-" * 80)

        if 'Hour' not in self.output_df.columns:
            self._add_result(
                "Hour Field Present",
                False,
                "Hour column not found in output"
            )
            return

        # Check how many Hour fields are populated
        non_null_hours = self.output_df['Hour'].notna().sum()
        total_with_time = self.output_df['Time of Call'].notna().sum() if 'Time of Call' in self.output_df.columns else 0

        coverage_pct = (non_null_hours / len(self.output_df)) * 100 if len(self.output_df) > 0 else 0

        self._add_result(
            "Hour Field Normalized",
            non_null_hours > 0,
            f"{non_null_hours:,} of {len(self.output_df):,} records ({coverage_pct:.1f}%)"
        )

        # Check Hour format (should be HH:MM)
        if non_null_hours > 0:
            sample_hours = self.output_df['Hour'].dropna().head(10)
            valid_format = all(
                isinstance(h, str) and ':' in h
                for h in sample_hours
            )

            self._add_result(
                "Hour Field Format",
                valid_format,
                "HH:MM format verified" if valid_format else "Invalid format detected"
            )

    def _check_quality_scores(self):
        """Verify that quality scores are present and valid."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Quality Scores Check")
        self.logger.info("-" * 80)

        if 'quality_score' not in self.output_df.columns:
            self._add_result(
                "Quality Scores Present",
                False,
                "quality_score column not found"
            )
            return

        # Check all records have quality scores
        non_null_scores = self.output_df['quality_score'].notna().sum()
        all_scored = non_null_scores == len(self.output_df)

        self._add_result(
            "All Records Scored",
            all_scored,
            f"{non_null_scores:,} of {len(self.output_df):,} records have scores"
        )

        # Check score range (0-100)
        min_score = self.output_df['quality_score'].min()
        max_score = self.output_df['quality_score'].max()
        avg_score = self.output_df['quality_score'].mean()

        valid_range = (0 <= min_score <= 100) and (0 <= max_score <= 100)

        self._add_result(
            "Quality Score Range Valid",
            valid_range,
            f"Range: {min_score:.1f} - {max_score:.1f}, Average: {avg_score:.1f}"
        )

        # Report score distribution
        high_quality = (self.output_df['quality_score'] >= 80).sum()
        medium_quality = ((self.output_df['quality_score'] >= 50) & (self.output_df['quality_score'] < 80)).sum()
        low_quality = (self.output_df['quality_score'] < 50).sum()

        self.logger.info(f"\nQuality Score Distribution:")
        self.logger.info(f"  High (>=80): {high_quality:,} ({high_quality/len(self.output_df)*100:.1f}%)")
        self.logger.info(f"  Medium (50-79): {medium_quality:,} ({medium_quality/len(self.output_df)*100:.1f}%)")
        self.logger.info(f"  Low (<50): {low_quality:,} ({low_quality/len(self.output_df)*100:.1f}%)")

    def _check_utf8_bom(self):
        """Check for UTF-8 BOM in output file."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("UTF-8 BOM Check")
        self.logger.info("-" * 80)

        if self.config['export']['excel']['include_utf8_bom']:
            # For Excel files, BOM is handled by openpyxl
            if self.output_file.suffix == '.xlsx':
                self._add_result(
                    "UTF-8 BOM Check",
                    True,
                    "Excel file - BOM handled by openpyxl"
                )
            else:
                # For CSV, check for BOM
                try:
                    with open(self.output_file, 'rb') as f:
                        start = f.read(3)
                        has_bom = start == b'\xef\xbb\xbf'

                    self._add_result(
                        "UTF-8 BOM Present",
                        has_bom,
                        "BOM found" if has_bom else "BOM not found"
                    )
                except Exception as e:
                    self._add_result(
                        "UTF-8 BOM Check",
                        False,
                        f"Error: {e}"
                    )
        else:
            self._add_result(
                "UTF-8 BOM Check",
                True,
                "BOM not required by configuration"
            )

    def _check_audit_trail(self):
        """Verify audit trail completeness."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Audit Trail Check")
        self.logger.info("-" * 80)

        if not self.config['export']['export_audit_trail']:
            self._add_result(
                "Audit Trail",
                True,
                "Audit trail export not required"
            )
            return

        if self.audit_df is None:
            self._add_result(
                "Audit Trail Exists",
                False,
                "Audit trail file not found"
            )
            return

        # Check required columns
        required_cols = ['timestamp', 'case_number', 'field', 'old_value', 'new_value', 'correction_type']
        missing_cols = [col for col in required_cols if col not in self.audit_df.columns]

        if missing_cols:
            self._add_result(
                "Audit Trail Schema",
                False,
                f"Missing columns: {', '.join(missing_cols)}"
            )
        else:
            self._add_result(
                "Audit Trail Schema",
                True,
                "All required columns present"
            )

        # Check completeness
        total_changes = len(self.audit_df)
        self._add_result(
            "Audit Trail Completeness",
            total_changes > 0,
            f"{total_changes:,} changes recorded"
        )

    def _check_duplicates_flagged(self):
        """Verify that duplicates were properly flagged."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Duplicate Flagging Check")
        self.logger.info("-" * 80)

        if not self.config['processing']['detect_duplicates']:
            self._add_result(
                "Duplicate Detection",
                True,
                "Duplicate detection not required"
            )
            return

        if 'duplicate_flag' not in self.output_df.columns:
            self._add_result(
                "Duplicate Flag Present",
                False,
                "duplicate_flag column not found"
            )
            return

        flagged_count = self.output_df['duplicate_flag'].sum()

        self._add_result(
            "Duplicates Flagged",
            'duplicate_flag' in self.output_df.columns,
            f"{flagged_count:,} records flagged as duplicates"
        )

    def _check_data_integrity(self):
        """Check data integrity using hash verification."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Data Integrity Check")
        self.logger.info("-" * 80)

        try:
            hash_manager = FileHashManager(
                manifest_path=self.config['paths']['hash_manifest']
            )

            # Get file history
            input_history = hash_manager.get_file_history(self.input_file.name)
            output_history = hash_manager.get_file_history(self.output_file.name)

            self._add_result(
                "Input Hash Recorded",
                len(input_history) > 0,
                f"{len(input_history)} hash records found"
            )

            self._add_result(
                "Output Hash Recorded",
                len(output_history) > 0,
                f"{len(output_history)} hash records found"
            )

        except Exception as e:
            self._add_result(
                "Hash Verification",
                False,
                f"Error: {e}"
            )

    def _check_case_number_format(self):
        """Validate case number format (YY-XXXXXX or YY-XXXXXX[A-Z] for supplements)."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Case Number Format Check")
        self.logger.info("-" * 80)

        if 'ReportNumberNew' not in self.output_df.columns:
            self._add_result(
                "Case Number Format",
                False,
                "ReportNumberNew column not found"
            )
            return

        pattern = r'^\d{2,4}-\d{6}[A-Z]?$'
        valid = self.output_df['ReportNumberNew'].astype(str).str.match(pattern, na=False)
        valid_count = valid.sum()
        invalid_count = (~valid).sum()
        pass_rate = valid_count / len(self.output_df) if len(self.output_df) > 0 else 0

        self._add_result(
            "Case Number Format Valid",
            pass_rate >= 0.95,  # 95% threshold
            f"{valid_count:,} valid, {invalid_count:,} invalid ({pass_rate:.1%})"
        )

        if invalid_count > 0:
            invalid_samples = self.output_df[~valid]['ReportNumberNew'].value_counts().head(5).to_dict()
            self.logger.warning(f"Invalid case number examples: {invalid_samples}")

    def _check_address_completeness(self):
        """Validate address completeness and structure."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Address Completeness Check")
        self.logger.info("-" * 80)

        if 'FullAddress2' not in self.output_df.columns:
            self._add_result(
                "Address Completeness",
                False,
                "FullAddress2 column not found"
            )
            return

        import re
        generic = {'UNKNOWN', 'NOT PROVIDED', 'N/A', 'NONE', '', 'TBD', 'TO BE DETERMINED'}
        suffix_pattern = re.compile(
            r'( STREET| AVENUE| ROAD| PLACE| DRIVE| COURT| BOULEVARD| LANE| WAY| HWY| HIGHWAY| ROUTE| AVE| ST| RD| BLVD| DR| CT| PL)'
        )

        def evaluate_address(value):
            if pd.isna(value):
                return False, ['missing_address']
            text = str(value).upper().strip()
            text = re.sub(r'\s+', ' ', text)
            if text in generic:
                return False, ['generic_placeholder']
            issues = []
            has_city_zip = text.endswith(', HACKENSACK, NJ, 07601')
            if not has_city_zip:
                issues.append('missing_city_state_zip')
            is_intersection = ' & ' in text
            if not is_intersection and not re.match(r'^\d+ ', text):
                issues.append('missing_house_number')
            if not suffix_pattern.search(text):
                issues.append('missing_street_suffix')
            if is_intersection and '&' not in text:
                issues.append('invalid_intersection_format')
            if issues:
                return False, issues
            return True, []

        passes = []
        for addr in self.output_df['FullAddress2']:
            is_valid, _ = evaluate_address(addr)
            passes.append(is_valid)

        valid_series = pd.Series(passes, index=self.output_df.index)
        valid_count = valid_series.sum()
        invalid_count = (~valid_series).sum()
        pass_rate = valid_count / len(self.output_df) if len(self.output_df) > 0 else 0

        self._add_result(
            "Address Completeness",
            pass_rate >= 0.85,  # 85% threshold
            f"{valid_count:,} valid, {invalid_count:,} invalid ({pass_rate:.1%})"
        )

    def _check_time_sequence(self):
        """Validate logical time sequence (Call -> Dispatch -> Out -> In)."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Time Sequence Check")
        self.logger.info("-" * 80)

        fields = ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In']
        missing_fields = [f for f in fields if f not in self.output_df.columns]

        if missing_fields:
            self._add_result(
                "Time Sequence",
                False,
                f"Missing fields: {', '.join(missing_fields)}"
            )
            return

        times = {f: pd.to_datetime(self.output_df.get(f), errors='coerce') for f in fields}
        valid_sequence = pd.Series([True] * len(self.output_df), index=self.output_df.index)

        if 'Time of Call' in self.output_df and 'Time Dispatched' in self.output_df:
            valid_sequence &= (times['Time of Call'] <= times['Time Dispatched']) | times['Time of Call'].isna() | times['Time Dispatched'].isna()
        if 'Time Dispatched' in self.output_df and 'Time Out' in self.output_df:
            valid_sequence &= (times['Time Dispatched'] <= times['Time Out']) | times['Time Dispatched'].isna() | times['Time Out'].isna()
        if 'Time Out' in self.output_df and 'Time In' in self.output_df:
            valid_sequence &= (times['Time Out'] <= times['Time In']) | times['Time Out'].isna() | times['Time In'].isna()

        valid_count = valid_sequence.sum()
        invalid_count = (~valid_sequence).sum()
        pass_rate = valid_count / len(self.output_df) if len(self.output_df) > 0 else 0

        self._add_result(
            "Time Sequence Valid",
            pass_rate >= 0.90,  # 90% threshold
            f"{valid_count:,} valid, {invalid_count:,} invalid ({pass_rate:.1%})"
        )

    def _check_how_reported_standardization(self):
        """Validate How Reported field standardization."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("How Reported Standardization Check")
        self.logger.info("-" * 80)

        if 'How Reported' not in self.output_df.columns:
            self._add_result(
                "How Reported Standardization",
                False,
                "How Reported column not found"
            )
            return

        valid_list = {
            '9-1-1', 'Walk-In', 'Phone', 'Self-Initiated', 'Radio', 'Teletype', 'Fax',
            'Other - See Notes', 'eMail', 'Mail', 'Virtual Patrol', 'Canceled Call'
        }

        # Normalize for comparison (case-insensitive)
        normalized = self.output_df['How Reported'].astype(str).str.strip()
        is_valid = normalized.str.upper().isin([v.upper() for v in valid_list])
        valid_count = is_valid.sum()
        invalid_count = (~is_valid).sum()
        pass_rate = valid_count / len(self.output_df) if len(self.output_df) > 0 else 0

        self._add_result(
            "How Reported Standardized",
            pass_rate >= 0.95,  # 95% threshold
            f"{valid_count:,} valid, {invalid_count:,} invalid ({pass_rate:.1%})"
        )

        if invalid_count > 0:
            invalid_samples = self.output_df[~is_valid]['How Reported'].value_counts().head(5).to_dict()
            self.logger.warning(f"Invalid How Reported examples: {invalid_samples}")

    def _check_disposition_consistency(self):
        """Validate disposition against approved list."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Disposition Consistency Check")
        self.logger.info("-" * 80)

        if 'Disposition' not in self.output_df.columns:
            self._add_result(
                "Disposition Consistency",
                False,
                "Disposition column not found"
            )
            return

        # Get valid dispositions from config or use defaults
        valid_list = self.config.get('validation_lists', {}).get('valid_dispositions', [
            "COMPLETE", "ADVISED", "ARREST", "UNFOUNDED", "CANCELLED",
            "GOA", "UTL", "SEE REPORT", "REFERRED"
        ])

        valid = self.output_df['Disposition'].astype(str).str.strip().str.upper().isin([v.upper() for v in valid_list])
        valid_count = valid.sum()
        invalid_count = (~valid).sum()
        null_count = self.output_df['Disposition'].isna().sum()
        pass_rate = valid_count / len(self.output_df) if len(self.output_df) > 0 else 0

        self._add_result(
            "Disposition Consistent",
            pass_rate >= 0.90,  # 90% threshold
            f"{valid_count:,} valid, {invalid_count:,} invalid, {null_count:,} null ({pass_rate:.1%})"
        )

        if invalid_count > 0:
            invalid_samples = self.output_df[~valid]['Disposition'].value_counts().head(5).to_dict()
            self.logger.warning(f"Invalid Disposition examples: {invalid_samples}")

    def _report_results(self):
        """Report validation results summary."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("VALIDATION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Total Checks: {self.passed + self.failed}")
        self.logger.info(f"Passed: {self.passed}")
        self.logger.info(f"Failed: {self.failed}")
        self.logger.info("")

        if self.failed > 0:
            self.logger.error("PIPELINE VALIDATION FAILED")
            self.logger.info("")
            self.logger.info("Failed Checks:")
            for result in self.validation_results:
                if not result['passed']:
                    self.logger.error(f"  ✗ {result['check']}: {result['message']}")
        else:
            self.logger.info("✓ ALL PIPELINE VALIDATIONS PASSED")

        self.logger.info("=" * 80)

    def get_validation_report(self) -> Dict:
        """
        Get structured validation report.

        Returns:
            Dictionary with validation results
        """
        return {
            'total_checks': self.passed + self.failed,
            'passed': self.passed,
            'failed': self.failed,
            'success': self.failed == 0,
            'results': self.validation_results.copy(),
            'input_records': len(self.input_df) if self.input_df is not None else 0,
            'output_records': len(self.output_df) if self.output_df is not None else 0,
            'audit_entries': len(self.audit_df) if self.audit_df is not None else 0
        }


def validate_pipeline_output(
    input_file: str,
    output_file: str,
    audit_file: Optional[str] = None,
    config_path: str = "config/config.yml"
) -> bool:
    """
    Convenience function to validate pipeline output.

    Args:
        input_file: Path to input file
        output_file: Path to output file
        audit_file: Path to audit trail file
        config_path: Path to configuration file

    Returns:
        True if all validations passed
    """
    validator = PipelineValidator(input_file, output_file, audit_file, config_path)
    return validator.run_all_validations()


if __name__ == "__main__":
    """Run pipeline validator from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="CAD Data Correction Framework - Pipeline Validator")
    parser.add_argument('--input', type=str, required=True, help="Path to input file")
    parser.add_argument('--output', type=str, required=True, help="Path to output file")
    parser.add_argument('--audit', type=str, help="Path to audit trail file")
    parser.add_argument('--config', type=str, default="config/config.yml", help="Path to configuration file")

    args = parser.parse_args()

    # Run validation
    success = validate_pipeline_output(
        input_file=args.input,
        output_file=args.output,
        audit_file=args.audit,
        config_path=args.config
    )

    # Exit with appropriate code
    sys.exit(0 if success else 1)
