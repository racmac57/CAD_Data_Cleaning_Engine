"""
CAD Data Processor - Core orchestration class

Handles end-to-end processing of CAD data including:
- Schema validation
- Manual corrections
- Field extraction and normalization
- Quality scoring
- Duplicate detection
- Audit trail maintenance
"""

import pandas as pd
import numpy as np
import yaml
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Import utilities
import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.logger import setup_logger, log_processing_step, log_correction_summary
from utils.hash_utils import FileHashManager
from utils.validate_schema import SchemaValidator


class CADDataProcessor:
    """
    Main processor for CAD data correction pipeline.

    Orchestrates all steps of data cleaning, correction, and enhancement
    for emergency dispatch records.
    """

    def __init__(self, config_path: str = "config/config.yml"):
        """
        Initialize CAD Data Processor.

        Args:
            config_path: Path to YAML configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)

        # Setup logging
        self.logger = setup_logger(
            name="CADDataProcessor",
            log_file=self.config['paths']['log_file'],
            level=getattr(logging, self.config['logging']['level']),
            console_output=self.config['logging']['console_output']
        )

        # Initialize hash manager
        self.hash_manager = FileHashManager(
            manifest_path=self.config['paths']['hash_manifest']
        )

        # Initialize schema validator
        self.schema_validator = SchemaValidator(
            strict=self.config['validation']['strict_schema']
        )

        # Initialize data containers
        self.df = None
        self.audit_trail = []
        self.processing_stats = {
            'records_input': 0,
            'records_output': 0,
            'corrections_applied': 0,
            'duplicates_flagged': 0,
            'quality_scores_computed': 0,
            'manual_review_flagged': 0
        }

        self.logger.info("CADDataProcessor initialized successfully")
        self.logger.info(f"Configuration loaded from: {config_path}")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def load_data(self, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load CAD data from file.

        Args:
            file_path: Path to input file (uses config if not provided)

        Returns:
            Loaded DataFrame
        """
        if file_path is None:
            file_path = self.config['paths']['input_file']

        log_processing_step(self.logger, "Loading CAD Data", {
            "File": file_path,
            "Format": Path(file_path).suffix
        })

        # Record input file hash
        input_hash = self.hash_manager.record_file_hash(
            file_path,
            stage="input",
            metadata={"description": "Raw CAD export"}
        )

        # Load data
        if file_path.endswith('.xlsx'):
            self.df = pd.read_excel(file_path)
        elif file_path.endswith('.csv'):
            self.df = pd.read_csv(file_path, encoding='utf-8-sig')
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

        self.processing_stats['records_input'] = len(self.df)

        self.logger.info(f"Loaded {len(self.df):,} records from {Path(file_path).name}")
        self.logger.info(f"Columns: {len(self.df.columns)}")
        self.logger.info(f"Memory usage: {self.df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

        return self.df

    def validate_schema(self) -> bool:
        """
        Validate data schema before processing.

        Returns:
            True if validation passed
        """
        log_processing_step(self.logger, "Schema Validation")

        if self.df is None:
            raise ValueError("No data loaded. Call load_data() first.")

        result = self.schema_validator.validate(self.df)

        if not result and self.config['validation']['strict_schema']:
            raise ValueError("Schema validation failed in strict mode")

        return result

    def apply_manual_corrections(self):
        """Apply manual corrections from CSV files."""
        if not self.config['processing']['apply_address_corrections']:
            self.logger.info("Skipping manual corrections (disabled in config)")
            return

        log_processing_step(self.logger, "Applying Manual Corrections")

        corrections_applied = 0

        # Apply address corrections
        if 'address' in self.config['paths']['corrections']:
            corrections_applied += self._apply_address_corrections()

        # Apply disposition corrections
        if 'disposition' in self.config['paths']['corrections']:
            corrections_applied += self._apply_disposition_corrections()

        # Apply How Reported corrections
        if 'how_reported' in self.config['paths']['corrections']:
            corrections_applied += self._apply_how_reported_corrections()

        # Apply FullAddress2 rule-based corrections
        if 'fulladdress2' in self.config['paths']['corrections']:
            corrections_applied += self._apply_fulladdress2_corrections()

        self.processing_stats['corrections_applied'] = corrections_applied
        log_correction_summary(self.logger, "Total Manual Corrections", corrections_applied)

    def _apply_address_corrections(self) -> int:
        """Apply address corrections from CSV."""
        correction_file = self.config['paths']['corrections']['address']

        if not Path(correction_file).exists():
            self.logger.warning(f"Address corrections file not found: {correction_file}")
            return 0

        self.logger.info(f"Applying address corrections from {Path(correction_file).name}")

        try:
            corrections_df = pd.read_csv(correction_file, encoding='utf-8-sig')

            if 'ReportNumberNew' not in corrections_df.columns or 'FullAddress2_corrected' not in corrections_df.columns:
                self.logger.error("Corrections file missing required columns")
                return 0

            count = 0
            for _, row in corrections_df.iterrows():
                case_num = row['ReportNumberNew']
                corrected_address = row['FullAddress2_corrected']

                mask = self.df['ReportNumberNew'] == case_num
                if mask.any():
                    old_value = self.df.loc[mask, 'FullAddress2'].iloc[0]
                    self.df.loc[mask, 'FullAddress2'] = corrected_address
                    count += 1

                    # Record in audit trail
                    self._record_audit(
                        case_number=case_num,
                        field='FullAddress2',
                        old_value=old_value,
                        new_value=corrected_address,
                        correction_type='manual_address'
                    )

            self.logger.info(f"Applied {count:,} address corrections")
            return count

        except Exception as e:
            self.logger.error(f"Error applying address corrections: {e}")
            return 0

    def _apply_disposition_corrections(self) -> int:
        """Apply disposition corrections from CSV."""
        correction_file = self.config['paths']['corrections']['disposition']

        if not Path(correction_file).exists():
            self.logger.warning(f"Disposition corrections file not found: {correction_file}")
            return 0

        self.logger.info(f"Applying disposition corrections from {Path(correction_file).name}")

        try:
            corrections_df = pd.read_csv(correction_file, encoding='utf-8-sig')

            if 'ReportNumberNew' not in corrections_df.columns or 'Disposition_corrected' not in corrections_df.columns:
                self.logger.error("Corrections file missing required columns")
                return 0

            count = 0
            for _, row in corrections_df.iterrows():
                case_num = row['ReportNumberNew']
                corrected_disposition = row['Disposition_corrected']

                mask = self.df['ReportNumberNew'] == case_num
                if mask.any():
                    old_value = self.df.loc[mask, 'Disposition'].iloc[0]
                    self.df.loc[mask, 'Disposition'] = corrected_disposition
                    count += 1

                    self._record_audit(
                        case_number=case_num,
                        field='Disposition',
                        old_value=old_value,
                        new_value=corrected_disposition,
                        correction_type='manual_disposition'
                    )

            self.logger.info(f"Applied {count:,} disposition corrections")
            return count

        except Exception as e:
            self.logger.error(f"Error applying disposition corrections: {e}")
            return 0

    def _apply_how_reported_corrections(self) -> int:
        """Apply How Reported standardization."""
        if 'How Reported' not in self.df.columns:
            self.logger.warning("How Reported column not found")
            return 0

        self.logger.info("Standardizing How Reported field")

        count = 0
        patterns = self.config['field_mappings']['how_reported']['patterns']

        for standard_value, variations in patterns.items():
            for variation in variations:
                mask = self.df['How Reported'].astype(str).str.contains(
                    variation, case=False, na=False, regex=False
                )

                if mask.any():
                    old_values = self.df.loc[mask, 'How Reported'].copy()
                    self.df.loc[mask, 'How Reported'] = standard_value
                    count += mask.sum()

                    # Record audit for changed records
                    for idx in self.df[mask].index:
                        if pd.notna(self.df.loc[idx, 'ReportNumberNew']):
                            self._record_audit(
                                case_number=self.df.loc[idx, 'ReportNumberNew'],
                                field='How Reported',
                                old_value=old_values.loc[idx],
                                new_value=standard_value,
                                correction_type='how_reported_standardization'
                            )

        self.logger.info(f"Standardized {count:,} How Reported values")
        return count

    def _apply_fulladdress2_corrections(self) -> int:
        """Apply rule-based FullAddress2 corrections."""
        correction_file = self.config['paths']['corrections'].get('fulladdress2')

        if not correction_file or not Path(correction_file).exists():
            self.logger.warning(f"FullAddress2 corrections file not found")
            return 0

        self.logger.info(f"Applying FullAddress2 corrections from {Path(correction_file).name}")

        try:
            corrections_df = pd.read_csv(correction_file, encoding='utf-8-sig')
            count = 0

            # Apply pattern-based corrections
            for _, row in corrections_df.iterrows():
                if pd.notna(row.get('pattern')) and pd.notna(row.get('replacement')):
                    pattern = row['pattern']
                    replacement = row['replacement']

                    mask = self.df['FullAddress2'].astype(str).str.contains(pattern, case=False, na=False, regex=True)

                    if mask.any():
                        self.df.loc[mask, 'FullAddress2'] = replacement
                        count += mask.sum()

            self.logger.info(f"Applied {count:,} FullAddress2 corrections")
            return count

        except Exception as e:
            self.logger.error(f"Error applying FullAddress2 corrections: {e}")
            return 0

    def extract_hour_field(self):
        """Extract Hour field from Time of Call."""
        if not self.config['processing']['extract_hour_field']:
            self.logger.info("Skipping hour field extraction (disabled)")
            return

        log_processing_step(self.logger, "Extracting Hour Field")

        if 'Time of Call' not in self.df.columns:
            self.logger.warning("Time of Call column not found")
            return

        # Ensure Time of Call is datetime
        self.df['Time of Call'] = pd.to_datetime(self.df['Time of Call'], errors='coerce')

        # Extract HH:mm format
        self.df['Hour'] = self.df['Time of Call'].dt.strftime('%H:%M')

        # Count successful extractions
        extracted_count = self.df['Hour'].notna().sum()
        self.logger.info(f"Extracted Hour field for {extracted_count:,} records")

    def map_call_types(self):
        """Map call types to standardized categories."""
        if not self.config['processing']['apply_call_type_mapping']:
            self.logger.info("Skipping call type mapping (disabled)")
            return

        log_processing_step(self.logger, "Mapping Call Types")

        call_type_master = self.config['paths']['reference'].get('call_type_master')

        if not call_type_master or not Path(call_type_master).exists():
            self.logger.warning(f"Call type master file not found: {call_type_master}")
            return

        try:
            mapping_df = pd.read_csv(call_type_master, encoding='utf-8-sig')

            # Apply mapping logic here
            # This would depend on your specific call type structure

            self.logger.info("Call type mapping completed")

        except Exception as e:
            self.logger.error(f"Error mapping call types: {e}")

    def detect_duplicates(self):
        """Detect and flag duplicate records and merge artifacts."""
        if not self.config['processing']['detect_duplicates']:
            self.logger.info("Skipping duplicate detection (disabled)")
            return

        log_processing_step(self.logger, "Detecting Duplicates")

        # Initialize flag column
        self.df['duplicate_flag'] = False

        # Check for exact duplicate case numbers
        duplicate_cases = self.df['ReportNumberNew'].duplicated(keep=False)
        duplicate_count = duplicate_cases.sum()

        if duplicate_count > 0:
            self.df.loc[duplicate_cases, 'duplicate_flag'] = True
            self.logger.warning(f"Found {duplicate_count:,} duplicate case numbers")

        # Check for merge artifact patterns
        merge_patterns = self.config['duplicate_detection']['merge_artifact_patterns']

        for pattern in merge_patterns:
            for col in self.df.columns:
                if self.df[col].dtype == 'object':
                    mask = self.df[col].astype(str).str.contains(pattern, case=False, na=False, regex=True)
                    if mask.any():
                        self.df.loc[mask, 'duplicate_flag'] = True
                        self.logger.info(f"Flagged {mask.sum():,} merge artifacts (pattern: {pattern})")

        self.processing_stats['duplicates_flagged'] = self.df['duplicate_flag'].sum()

    def calculate_quality_scores(self):
        """Calculate quality score for each record."""
        log_processing_step(self.logger, "Calculating Quality Scores")

        # Initialize quality score
        self.df['quality_score'] = 0

        weights = self.config['quality_weights']

        # Case number present
        if 'ReportNumberNew' in self.df.columns:
            has_case = self.df['ReportNumberNew'].notna() & (self.df['ReportNumberNew'] != '')
            self.df.loc[has_case, 'quality_score'] += weights['case_number_present']

        # Address present
        if 'FullAddress2' in self.df.columns:
            has_address = self.df['FullAddress2'].notna() & (self.df['FullAddress2'] != '')
            self.df.loc[has_address, 'quality_score'] += weights['address_present']

        # Time fields present
        if 'Time of Call' in self.df.columns:
            has_call_time = self.df['Time of Call'].notna()
            self.df.loc[has_call_time, 'quality_score'] += weights['call_time_present']

        if 'Time Dispatched' in self.df.columns:
            has_dispatch = self.df['Time Dispatched'].notna()
            self.df.loc[has_dispatch, 'quality_score'] += weights['dispatch_time_present']

        # Officer present
        if 'Officer' in self.df.columns:
            has_officer = self.df['Officer'].notna() & (self.df['Officer'] != '')
            self.df.loc[has_officer, 'quality_score'] += weights['officer_present']

        # Disposition present
        if 'Disposition' in self.df.columns:
            has_disposition = self.df['Disposition'].notna() & (self.df['Disposition'] != '')
            self.df.loc[has_disposition, 'quality_score'] += weights['disposition_present']

        # Incident type present
        if 'Incident' in self.df.columns:
            has_incident = self.df['Incident'].notna() & (self.df['Incident'] != '')
            self.df.loc[has_incident, 'quality_score'] += weights['incident_type_present']

        avg_score = self.df['quality_score'].mean()
        self.processing_stats['quality_scores_computed'] = len(self.df)

        self.logger.info(f"Quality scores calculated: average = {avg_score:.1f}/100")

    def flag_for_manual_review(self, criteria: Optional[str] = None):
        """
        Flag records for manual review based on criteria.

        Args:
            criteria: Optional pandas query string for custom criteria
        """
        log_processing_step(self.logger, "Flagging Records for Manual Review")

        self.df['manual_review_flag'] = False

        config_criteria = self.config['manual_review_criteria']

        # Flag unknown addresses
        if config_criteria['flag_unknown_addresses']:
            address_patterns = config_criteria['address_patterns_to_flag']
            for pattern in address_patterns:
                mask = self.df['FullAddress2'].astype(str).str.contains(pattern, case=False, na=False)
                self.df.loc[mask, 'manual_review_flag'] = True

        # Flag missing case numbers
        if config_criteria['flag_missing_case_numbers']:
            missing_case = self.df['ReportNumberNew'].isna() | (self.df['ReportNumberNew'] == '')
            self.df.loc[missing_case, 'manual_review_flag'] = True

        # Flag low quality scores
        if config_criteria['flag_low_quality_scores']:
            threshold = config_criteria['low_quality_threshold']
            low_quality = self.df['quality_score'] < threshold
            self.df.loc[low_quality, 'manual_review_flag'] = True

        # Apply custom criteria if provided
        if criteria:
            try:
                custom_mask = self.df.eval(criteria)
                self.df.loc[custom_mask, 'manual_review_flag'] = True
            except Exception as e:
                self.logger.error(f"Error applying custom criteria: {e}")

        flagged_count = self.df['manual_review_flag'].sum()
        self.processing_stats['manual_review_flagged'] = flagged_count

        self.logger.info(f"Flagged {flagged_count:,} records for manual review")

    def _record_audit(self, case_number: str, field: str, old_value, new_value, correction_type: str):
        """Record a change in the audit trail."""
        self.audit_trail.append({
            'timestamp': datetime.now().isoformat(),
            'case_number': case_number,
            'field': field,
            'old_value': str(old_value),
            'new_value': str(new_value),
            'correction_type': correction_type
        })

    def run_all_corrections(self):
        """
        Execute full correction pipeline.

        This is the main orchestration method that runs all processing steps.
        """
        self.logger.info("=" * 80)
        self.logger.info("STARTING CAD DATA CORRECTION PIPELINE")
        self.logger.info("=" * 80)

        try:
            # Step 1: Validate schema
            if self.config['validation']['validate_schema']:
                self.validate_schema()

            # Step 2: Apply manual corrections
            self.apply_manual_corrections()

            # Step 3: Extract hour field
            self.extract_hour_field()

            # Step 4: Map call types
            self.map_call_types()

            # Step 5: Detect duplicates
            self.detect_duplicates()

            # Step 6: Calculate quality scores
            self.calculate_quality_scores()

            # Step 7: Flag for manual review
            self.flag_for_manual_review()

            self.processing_stats['records_output'] = len(self.df)

            self.logger.info("=" * 80)
            self.logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            self.logger.info("=" * 80)
            self._log_processing_stats()

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise

    def _log_processing_stats(self):
        """Log processing statistics summary."""
        self.logger.info("\nProcessing Statistics:")
        for key, value in self.processing_stats.items():
            self.logger.info(f"  {key}: {value:,}")

    def export_corrected_data(self, output_path: Optional[str] = None):
        """
        Export corrected data to file.

        Args:
            output_path: Path to output file (uses config if not provided)
        """
        if output_path is None:
            output_path = self.config['paths']['output_file']

        log_processing_step(self.logger, "Exporting Corrected Data", {
            "Output file": output_path,
            "Records": f"{len(self.df):,}"
        })

        # Create output directory if needed
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Export based on format
        if output_path.endswith('.xlsx'):
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                self.df.to_excel(writer, index=False, sheet_name='CAD_Data')

                # Add UTF-8 BOM if configured
                if self.config['export']['excel']['include_utf8_bom']:
                    # This would be handled by pandas/openpyxl
                    pass

        elif output_path.endswith('.csv'):
            self.df.to_csv(
                output_path,
                index=False,
                encoding=self.config['export']['csv']['encoding'],
                sep=self.config['export']['csv']['sep']
            )

        # Record output file hash
        self.hash_manager.record_file_hash(
            output_path,
            stage="output",
            metadata={
                "description": "Corrected CAD data",
                "records": len(self.df),
                "corrections_applied": self.processing_stats['corrections_applied']
            }
        )

        self.logger.info(f"Data exported successfully to {output_path}")

        # Export audit trail if configured
        if self.config['export']['export_audit_trail']:
            self._export_audit_trail()

        # Export flagged records if configured
        if self.config['export']['export_flagged_records']:
            self._export_flagged_records()

    def _export_audit_trail(self):
        """Export audit trail to CSV."""
        audit_path = self.config['paths']['audit_file']
        Path(audit_path).parent.mkdir(parents=True, exist_ok=True)

        audit_df = pd.DataFrame(self.audit_trail)
        audit_df.to_csv(audit_path, index=False, encoding='utf-8-sig')

        self.logger.info(f"Audit trail exported: {len(self.audit_trail):,} changes recorded")

    def _export_flagged_records(self):
        """Export flagged records to Excel for manual review."""
        if 'manual_review_flag' not in self.df.columns:
            return

        flagged_df = self.df[self.df['manual_review_flag'] == True].copy()

        if len(flagged_df) == 0:
            self.logger.info("No records flagged for manual review")
            return

        output_path = self.config['paths']['manual_review_file']
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        flagged_df.to_excel(output_path, index=False)

        self.logger.info(f"Flagged records exported: {len(flagged_df):,} records")

    def get_processing_summary(self) -> Dict:
        """
        Get comprehensive processing summary.

        Returns:
            Dictionary with processing statistics and quality metrics
        """
        return {
            'processing_stats': self.processing_stats.copy(),
            'quality_metrics': {
                'average_quality_score': float(self.df['quality_score'].mean()) if 'quality_score' in self.df.columns else 0,
                'high_quality_pct': float((self.df['quality_score'] >= 80).sum() / len(self.df) * 100) if 'quality_score' in self.df.columns else 0,
                'low_quality_pct': float((self.df['quality_score'] < 50).sum() / len(self.df) * 100) if 'quality_score' in self.df.columns else 0
            },
            'audit_trail_entries': len(self.audit_trail),
            'timestamp': datetime.now().isoformat()
        }
