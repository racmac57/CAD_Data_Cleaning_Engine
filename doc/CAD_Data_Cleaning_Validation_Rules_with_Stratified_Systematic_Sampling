# **CAD Data Cleaning & Validation Rules with Stratified/Systematic Sampling**

Based on the CAD processing script, here's a comprehensive data cleaning and validation framework with sampling strategies:

## **CAD Data Cleaning & Validation Rules Class**

```python
import pandas as pd
import numpy as np
import logging
import re
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

class CADDataValidator:
    """Comprehensive CAD data validation with stratified and systematic sampling."""
    
    def __init__(self):
        """Initialize validator with rules and sampling configuration."""
        self.validation_rules = self._initialize_validation_rules()
        self.cleaning_rules = self._initialize_cleaning_rules()
        self.sampling_config = {
            'stratified_sample_size': 1000,
            'systematic_interval': 100,
            'quality_thresholds': {
                'critical': 0.95,  # 95% of records must pass critical rules
                'important': 0.85,  # 85% of records must pass important rules
                'optional': 0.70   # 70% of records must pass optional rules
            }
        }
        
        self.validation_results = {
            'total_records': 0,
            'rules_passed': {},
            'rules_failed': {},
            'sample_analysis': {},
            'data_quality_score': 0.0,
            'recommended_actions': []
        }
    
    def _initialize_validation_rules(self) -> Dict:
        """Initialize comprehensive validation rules for CAD data."""
        return {
            'critical_rules': {
                'case_number_format': {
                    'rule_id': 'CRIT_001',
                    'description': 'Case number must follow format: YY-XXXXXX or YYYY-XXXXXX',
                    'field': 'ReportNumberNew',
                    'pattern': r'^\d{2,4}-\d{6}$',
                    'severity': 'critical',
                    'fix_suggestion': 'Standardize case number format, pad with zeros if needed'
                },
                'case_number_uniqueness': {
                    'rule_id': 'CRIT_002',
                    'description': 'Case numbers must be unique within dataset',
                    'field': 'ReportNumberNew',
                    'severity': 'critical',
                    'fix_suggestion': 'Remove duplicates, investigate duplicate sources'
                },
                'call_datetime_validity': {
                    'rule_id': 'CRIT_003',
                    'description': 'Time of Call must be valid datetime within reasonable range',
                    'field': 'Time of Call',
                    'severity': 'critical',
                    'fix_suggestion': 'Validate datetime parsing, check for timezone issues'
                },
                'incident_type_presence': {
                    'rule_id': 'CRIT_004',
                    'description': 'Incident type must not be null or empty',
                    'field': 'Incident',
                    'severity': 'critical',
                    'fix_suggestion': 'Map null values to "Unknown" or investigate missing data'
                }
            },
            'important_rules': {
                'address_completeness': {
                    'rule_id': 'IMP_001',
                    'description': 'Address should be present and not generic',
                    'field': 'FullAddress2',
                    'severity': 'important',
                    'fix_suggestion': 'Validate address completeness, flag generic addresses'
                },
                'officer_assignment': {
                    'rule_id': 'IMP_002',
                    'description': 'Officer field should not be null for dispatched calls',
                    'field': 'Officer',
                    'severity': 'important',
                    'fix_suggestion': 'Check officer assignment logic, validate against roster'
                },
                'disposition_consistency': {
                    'rule_id': 'IMP_003',
                    'description': 'Disposition should be from approved list',
                    'field': 'Disposition',
                    'severity': 'important',
                    'fix_suggestion': 'Standardize disposition values, create lookup table'
                },
                'time_sequence_validity': {
                    'rule_id': 'IMP_004',
                    'description': 'Time sequence should be logical (Call -> Dispatch -> Out -> In)',
                    'fields': ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In'],
                    'severity': 'important',
                    'fix_suggestion': 'Validate time sequence logic, flag outliers'
                }
            },
            'optional_rules': {
                'how_reported_standardization': {
                    'rule_id': 'OPT_001',
                    'description': 'How Reported should be from standardized list',
                    'field': 'How Reported',
                    'severity': 'optional',
                    'fix_suggestion': 'Map variations to standard values (9-1-1, Phone, Walk-in, etc.)'
                },
                'zone_validity': {
                    'rule_id': 'OPT_002',
                    'description': 'PD Zone should be valid zone identifier',
                    'field': 'PDZone',
                    'severity': 'optional',
                    'fix_suggestion': 'Validate against zone master list'
                },
                'response_type_consistency': {
                    'rule_id': 'OPT_003',
                    'description': 'Response Type should align with incident severity',
                    'fields': ['Response Type', 'Incident'],
                    'severity': 'optional',
                    'fix_suggestion': 'Create response type validation matrix'
                }
            }
        }
    
    def _initialize_cleaning_rules(self) -> Dict:
        """Initialize data cleaning rules for CAD data."""
        return {
            'case_number_cleaning': {
                'remove_special_chars': r'[^A-Z0-9\-]',
                'standardize_format': r'^(\d{2,4})-(\d{6})$',
                'pad_zeros': True,
                'uppercase': True
            },
            'address_cleaning': {
                'standardize_abbreviations': {
                    ' ST ': ' STREET ',
                    ' AVE ': ' AVENUE ',
                    ' BLVD ': ' BOULEVARD ',
                    ' RD ': ' ROAD ',
                    ' DR ': ' DRIVE '
                },
                'remove_extra_spaces': True,
                'uppercase': True,
                'handle_intersections': True
            },
            'datetime_cleaning': {
                'handle_date_conversions': True,  # Fix 9-1-1 -> date issues
                'standardize_format': '%Y-%m-%d %H:%M:%S',
                'validate_range': {
                    'start_date': '2020-01-01',
                    'end_date': '2030-12-31'
                }
            },
            'text_field_cleaning': {
                'remove_artifacts': [r'\?\s*-\s*\?\?\s*-\s*\?', r'^\?\s*$'],
                'standardize_whitespace': True,
                'handle_null_values': True
            },
            'officer_cleaning': {
                'parse_name_components': True,
                'extract_badge_numbers': True,
                'standardize_ranks': True,
                'remove_extra_spaces': True
            }
        }
    
    def validate_cad_dataset(self, df: pd.DataFrame, sampling_method: str = 'stratified') -> Dict:
        """Main validation method with sampling."""
        logger.info(f"Starting CAD dataset validation with {sampling_method} sampling...")
        
        self.validation_results['total_records'] = len(df)
        
        # Step 1: Create sample for detailed analysis
        sample_df = self._create_sample(df, sampling_method)
        
        # Step 2: Run validation rules on sample
        sample_results = self._validate_sample(sample_df)
        
        # Step 3: Extrapolate results to full dataset
        full_results = self._extrapolate_results(sample_results, df)
        
        # Step 4: Generate recommendations
        recommendations = self._generate_validation_recommendations(full_results)
        
        self.validation_results.update(full_results)
        self.validation_results['recommended_actions'] = recommendations
        
        return self.validation_results
    
    def _create_sample(self, df: pd.DataFrame, method: str) -> pd.DataFrame:
        """Create sample using specified sampling method."""
        
        if method == 'stratified':
            return self._stratified_sampling(df)
        elif method == 'systematic':
            return self._systematic_sampling(df)
        elif method == 'random':
            return self._random_sampling(df)
        else:
            raise ValueError(f"Unknown sampling method: {method}")
    
    def _stratified_sampling(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create stratified sample based on key characteristics."""
        logger.info("Creating stratified sample...")
        
        # Define strata based on key CAD characteristics
        strata_definitions = {
            'incident_type': 'Incident' if 'Incident' in df.columns else None,
            'how_reported': 'How Reported' if 'How Reported' in df.columns else None,
            'time_period': 'Time of Call' if 'Time of Call' in df.columns else None
        }
        
        # Create strata
        df_with_strata = df.copy()
        
        # Incident type strata
        if strata_definitions['incident_type']:
            incident_counts = df[strata_definitions['incident_type']].value_counts()
            top_incidents = incident_counts.head(10).index
            df_with_strata['incident_stratum'] = df_with_strata[strata_definitions['incident_type']].apply(
                lambda x: x if x in top_incidents else 'Other'
            )
        
        # How reported strata
        if strata_definitions['how_reported']:
            df_with_strata['reported_stratum'] = df_with_strata[strata_definitions['how_reported']].apply(
                self._categorize_how_reported
            )
        
        # Time period strata
        if strata_definitions['time_period']:
            df_with_strata['time_stratum'] = pd.to_datetime(
                df_with_strata[strata_definitions['time_period']], errors='coerce'
            ).dt.hour.apply(self._categorize_time_period)
        
        # Perform stratified sampling
        sample_size = min(self.sampling_config['stratified_sample_size'], len(df))
        
        try:
            # Use sklearn for stratified sampling
            if len(df) > sample_size:
                sample_df, _ = train_test_split(
                    df_with_strata,
                    test_size=1 - (sample_size / len(df)),
                    stratify=df_with_strata.get('incident_stratum', None),
                    random_state=42
                )
            else:
                sample_df = df_with_strata
                
        except Exception as e:
            logger.warning(f"Stratified sampling failed, falling back to random: {e}")
            sample_df = df.sample(n=min(sample_size, len(df)), random_state=42)
        
        logger.info(f"Created stratified sample: {len(sample_df):,} records")
        return sample_df
    
    def _systematic_sampling(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create systematic sample with fixed interval."""
        logger.info("Creating systematic sample...")
        
        interval = self.sampling_config['systematic_interval']
        total_records = len(df)
        
        # Calculate starting point and sample indices
        start_idx = np.random.randint(0, interval)
        sample_indices = list(range(start_idx, total_records, interval))
        
        sample_df = df.iloc[sample_indices].copy()
        
        logger.info(f"Created systematic sample: {len(sample_df):,} records (interval: {interval})")
        return sample_df
    
    def _random_sampling(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create random sample."""
        logger.info("Creating random sample...")
        
        sample_size = min(self.sampling_config['stratified_sample_size'], len(df))
        sample_df = df.sample(n=sample_size, random_state=42)
        
        logger.info(f"Created random sample: {len(sample_df):,} records")
        return sample_df
    
    def _categorize_how_reported(self, value):
        """Categorize how reported values."""
        if pd.isna(value):
            return 'Unknown'
        
        value_str = str(value).upper()
        
        if any(term in value_str for term in ['9-1-1', '911', 'EMERGENCY']):
            return 'Emergency'
        elif any(term in value_str for term in ['PHONE', 'CALL']):
            return 'Phone'
        elif any(term in value_str for term in ['WALK', 'PERSON']):
            return 'Walk-in'
        elif any(term in value_str for term in ['SELF', 'INITIATED']):
            return 'Self-Initiated'
        else:
            return 'Other'
    
    def _categorize_time_period(self, hour):
        """Categorize time periods."""
        if pd.isna(hour):
            return 'Unknown'
        
        try:
            hour = int(hour)
            if 6 <= hour < 12:
                return 'Morning'
            elif 12 <= hour < 18:
                return 'Afternoon'
            elif 18 <= hour < 22:
                return 'Evening'
            else:
                return 'Night'
        except:
            return 'Unknown'
    
    def _validate_sample(self, sample_df: pd.DataFrame) -> Dict:
        """Run validation rules on sample."""
        logger.info("Running validation rules on sample...")
        
        results = {
            'critical_rules': {},
            'important_rules': {},
            'optional_rules': {},
            'sample_size': len(sample_df)
        }
        
        # Validate critical rules
        for rule_id, rule in self.validation_rules['critical_rules'].items():
            result = self._apply_validation_rule(sample_df, rule)
            results['critical_rules'][rule_id] = result
        
        # Validate important rules
        for rule_id, rule in self.validation_rules['important_rules'].items():
            result = self._apply_validation_rule(sample_df, rule)
            results['important_rules'][rule_id] = result
        
        # Validate optional rules
        for rule_id, rule in self.validation_rules['optional_rules'].items():
            result = self._apply_validation_rule(sample_df, rule)
            results['optional_rules'][rule_id] = result
        
        return results
    
    def _apply_validation_rule(self, df: pd.DataFrame, rule: Dict) -> Dict:
        """Apply a single validation rule."""
        
        rule_id = rule['rule_id']
        field = rule.get('field')
        fields = rule.get('fields', [field] if field else [])
        
        result = {
            'rule_id': rule_id,
            'description': rule['description'],
            'severity': rule['severity'],
            'passed': 0,
            'failed': 0,
            'pass_rate': 0.0,
            'failed_records': [],
            'fix_suggestion': rule.get('fix_suggestion', '')
        }
        
        # Check if required fields exist
        missing_fields = [f for f in fields if f not in df.columns]
        if missing_fields:
            result['error'] = f"Missing fields: {missing_fields}"
            result['passed'] = 0
            result['failed'] = len(df)
            result['pass_rate'] = 0.0
            return result
        
        # Apply specific validation logic
        if rule_id == 'CRIT_001':  # Case number format
            result = self._validate_case_number_format(df, result)
        elif rule_id == 'CRIT_002':  # Case number uniqueness
            result = self._validate_case_number_uniqueness(df, result)
        elif rule_id == 'CRIT_003':  # Call datetime validity
            result = self._validate_call_datetime(df, result)
        elif rule_id == 'CRIT_004':  # Incident type presence
            result = self._validate_incident_type_presence(df, result)
        elif rule_id == 'IMP_001':  # Address completeness
            result = self._validate_address_completeness(df, result)
        elif rule_id == 'IMP_002':  # Officer assignment
            result = self._validate_officer_assignment(df, result)
        elif rule_id == 'IMP_003':  # Disposition consistency
            result = self._validate_disposition_consistency(df, result)
        elif rule_id == 'IMP_004':  # Time sequence validity
            result = self._validate_time_sequence(df, result)
        elif rule_id == 'OPT_001':  # How reported standardization
            result = self._validate_how_reported(df, result)
        elif rule_id == 'OPT_002':  # Zone validity
            result = self._validate_zone_validity(df, result)
        elif rule_id == 'OPT_003':  # Response type consistency
            result = self._validate_response_type_consistency(df, result)
        
        # Calculate pass rate
        total_records = len(df)
        result['pass_rate'] = result['passed'] / total_records if total_records > 0 else 0.0
        
        return result
    
    def _validate_case_number_format(self, df: pd.DataFrame, result: Dict) -> Dict:
        """Validate case number format."""
        field = 'ReportNumberNew'
        pattern = r'^\d{2,4}-\d{6}$'
        
        if field not in df.columns:
            result['error'] = f"Field {field} not found"
            return result
        
        # Check format
        valid_format = df[field].astype(str).str.match(pattern, na=False)
        result['passed'] = valid_format.sum()
        result['failed'] = (~valid_format).sum()
        
        # Store failed records
        failed_mask = ~valid_format
        result['failed_records'] = df[failed_mask][field].value_counts().head(10).to_dict()
        
        return result
    
    def _validate_case_number_uniqueness(self, df: pd.DataFrame, result: Dict) -> Dict:
        """Validate case number uniqueness."""
        field = 'ReportNumberNew'
        
        if field not in df.columns:
            result['error'] = f"Field {field} not found"
            return result
        
        # Check for duplicates
        unique_count = df[field].nunique()
        total_count = len(df)
        duplicate_count = total_count - unique_count
        
        result['passed'] = unique_count
        result['failed'] = duplicate_count
        
        # Find duplicates
        duplicates = df[field].value_counts()
        duplicates = duplicates[duplicates > 1]
        result['failed_records'] = duplicates.head(10).to_dict()
        
        return result
    
    def _validate_call_datetime(self, df: pd.DataFrame, result: Dict) -> Dict:
        """Validate call datetime."""
        field = 'Time of Call'
        
        if field not in df.columns:
            result['error'] = f"Field {field} not found"
            return result
        
        # Parse datetime
        parsed_datetime = pd.to_datetime(df[field], errors='coerce')
        
        # Check for valid dates
        valid_datetime = parsed_datetime.notna()
        
        # Check for reasonable date range
        reasonable_range = (parsed_datetime >= '2020-01-01') & (parsed_datetime <= '2030-12-31')
        
        # Combine checks
        valid_records = valid_datetime & reasonable_range
        
        result['passed'] = valid_records.sum()
        result['failed'] = (~valid_records).sum()
        
        # Store failed records
        failed_mask = ~valid_records
        result['failed_records'] = df[failed_mask][field].value_counts().head(10).to_dict()
        
        return result
    
    def _validate_incident_type_presence(self, df: pd.DataFrame, result: Dict) -> Dict:
        """Validate incident type presence."""
        field = 'Incident'
        
        if field not in df.columns:
            result['error'] = f"Field {field} not found"
            return result
        
        # Check for null or empty values
        valid_incidents = df[field].notna() & (df[field].astype(str).str.strip() != '')
        
        result['passed'] = valid_incidents.sum()
        result['failed'] = (~valid_incidents).sum()
        
        # Store failed records
        failed_mask = ~valid_incidents
        result['failed_records'] = df[failed_mask][field].value_counts().head(10).to_dict()
        
        return result
    
    def _validate_address_completeness(self, df: pd.DataFrame, result: Dict) -> Dict:
        """Validate address completeness."""
        field = 'FullAddress2'
        
        if field not in df.columns:
            result['error'] = f"Field {field} not found"
            return result
        
        # Check for null or generic addresses
        generic_addresses = [
            'UNKNOWN', 'NOT PROVIDED', 'N/A', 'NONE', '', 'TBD', 'TO BE DETERMINED'
        ]
        
        valid_addresses = df[field].notna() & \
                         (~df[field].astype(str).str.upper().isin(generic_addresses))
        
        result['passed'] = valid_addresses.sum()
        result['failed'] = (~valid_addresses).sum()
        
        # Store failed records
        failed_mask = ~valid_addresses
        result['failed_records'] = df[failed_mask][field].value_counts().head(10).to_dict()
        
        return result
    
    def _validate_officer_assignment(self, df: pd.DataFrame, result: Dict) -> Dict:
        """Validate officer assignment."""
        field = 'Officer'
        
        if field not in df.columns:
            result['error'] = f"Field {field} not found"
            return result
        
        # Check for null officers on dispatched calls
        dispatched_calls = df['Time Dispatched'].notna() if 'Time Dispatched' in df.columns else pd.Series([True] * len(df))
        has_officer = df[field].notna() & (df[field].astype(str).str.strip() != '')
        
        valid_assignments = dispatched_calls & has_officer
        
        result['passed'] = valid_assignments.sum()
        result['failed'] = (~valid_assignments).sum()
        
        # Store failed records
        failed_mask = ~valid_assignments
        result['failed_records'] = df[failed_mask][field].value_counts().head(10).to_dict()
        
        return result
    
    def _validate_disposition_consistency(self, df: pd.DataFrame, result: Dict) -> Dict:
        """Validate disposition consistency."""
        field = 'Disposition'
        
        if field not in df.columns:
            result['error'] = f"Field {field} not found"
            return result
        
        # Standard disposition values
        valid_dispositions = [
            'COMPLETE', 'ADVISED', 'ARREST', 'UNFOUNDED', 'CANCELLED', 
            'GOA', 'UTL', 'SEE REPORT', 'REFERRED'
        ]
        
        disposition_values = df[field].astype(str).str.upper().str.strip()
        valid_dispositions_check = disposition_values.isin(valid_dispositions)
        
        result['passed'] = valid_dispositions_check.sum()
        result['failed'] = (~valid_dispositions_check).sum()
        
        # Store failed records
        failed_mask = ~valid_dispositions_check
        result['failed_records'] = df[failed_mask][field].value_counts().head(10).to_dict()
        
        return result
    
    def _validate_time_sequence(self, df: pd.DataFrame, result: Dict) -> Dict:
        """Validate time sequence logic."""
        time_fields = ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In']
        
        missing_fields = [f for f in time_fields if f not in df.columns]
        if missing_fields:
            result['error'] = f"Missing time fields: {missing_fields}"
            return result
        
        # Parse all time fields
        parsed_times = {}
        for field in time_fields:
            parsed_times[field] = pd.to_datetime(df[field], errors='coerce')
        
        # Check sequence: Call <= Dispatch <= Out <= In
        valid_sequence = (
            (parsed_times['Time of Call'] <= parsed_times['Time Dispatched']) &
            (parsed_times['Time Dispatched'] <= parsed_times['Time Out']) &
            (parsed_times['Time Out'] <= parsed_times['Time In'])
        )
        
        result['passed'] = valid_sequence.sum()
        result['failed'] = (~valid_sequence).sum()
        
        return result
    
    def _validate_how_reported(self, df: pd.DataFrame, result: Dict) -> Dict:
        """Validate how reported standardization."""
        field = 'How Reported'
        
        if field not in df.columns:
            result['error'] = f"Field {field} not found"
            return result
        
        # Standard how reported values
        standard_values = ['9-1-1', 'PHONE', 'WALK-IN', 'SELF-INITIATED', 'OTHER']
        
        # Check for date conversion issues (9-1-1 -> date)
        date_pattern = r'^\d{4}-\d{2}-\d{2}'
        is_date_conversion = df[field].astype(str).str.match(date_pattern, na=False)
        
        # Check for non-standard values
        non_standard = ~df[field].astype(str).str.upper().isin(standard_values)
        
        # Combine issues
        has_issues = is_date_conversion | non_standard
        
        result['passed'] = (~has_issues).sum()
        result['failed'] = has_issues.sum()
        
        # Store failed records
        failed_mask = has_issues
        result['failed_records'] = df[failed_mask][field].value_counts().head(10).to_dict()
        
        return result
    
    def _validate_zone_validity(self, df: pd.DataFrame, result: Dict) -> Dict:
        """Validate zone validity."""
        field = 'PDZone'
        
        if field not in df.columns:
            result['error'] = f"Field {field} not found"
            return result
        
        # Valid zones (this should be customized for your department)
        valid_zones = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'UNK']
        
        zone_values = df[field].astype(str).str.strip()
        valid_zones_check = zone_values.isin(valid_zones)
        
        result['passed'] = valid_zones_check.sum()
        result['failed'] = (~valid_zones_check).sum()
        
        # Store failed records
        failed_mask = ~valid_zones_check
        result['failed_records'] = df[failed_mask][field].value_counts().head(10).to_dict()
        
        return result
    
    def _validate_response_type_consistency(self, df: pd.DataFrame, result: Dict) -> Dict:
        """Validate response type consistency with incident."""
        response_field = 'Response Type'
        incident_field = 'Incident'
        
        if response_field not in df.columns or incident_field not in df.columns:
            result['error'] = f"Missing fields: {response_field} or {incident_field}"
            return result
        
        # Define response type consistency rules
        emergency_incidents = ['ROBBERY', 'ASSAULT', 'BURGLARY', 'SHOOTING', 'STABBING']
        non_emergency_incidents = ['NOISE COMPLAINT', 'PARKING VIOLATION', 'CIVIL DISPUTE']
        
        # Check consistency
        incident_upper = df[incident_field].astype(str).str.upper()
        response_upper = df[response_field].astype(str).str.upper()
        
        # Emergency incidents should have emergency response
        emergency_incident_mask = incident_upper.isin(emergency_incidents)
        emergency_response_mask = response_upper.isin(['EMERGENCY', 'PRIORITY'])
        
        # Non-emergency incidents should have non-emergency response
        non_emergency_incident_mask = incident_upper.isin(non_emergency_incidents)
        non_emergency_response_mask = response_upper.isin(['NON-EMERGENCY', 'ROUTINE'])
        
        # Calculate consistency
        consistent = (
            (emergency_incident_mask & emergency_response_mask) |
            (non_emergency_incident_mask & non_emergency_response_mask) |
            (~emergency_incident_mask & ~non_emergency_incident_mask)  # Unknown incidents
        )
        
        result['passed'] = consistent.sum()
        result['failed'] = (~consistent).sum()
        
        return result
    
    def _extrapolate_results(self, sample_results: Dict, full_df: pd.DataFrame) -> Dict:
        """Extrapolate sample results to full dataset."""
        
        extrapolated = {
            'critical_rules': {},
            'important_rules': {},
            'optional_rules': {},
            'overall_quality_score': 0.0
        }
        
        # Extrapolate each rule category
        for category in ['critical_rules', 'important_rules', 'optional_rules']:
            extrapolated[category] = {}
            
            for rule_id, result in sample_results[category].items():
                # Extrapolate counts
                sample_size = result['sample_size']
                full_size = len(full_df)
                extrapolation_factor = full_size / sample_size if sample_size > 0 else 0
                
                extrapolated[category][rule_id] = {
                    'rule_id': rule_id,
                    'description': result['description'],
                    'severity': result['severity'],
                    'sample_passed': result['passed'],
                    'sample_failed': result['failed'],
                    'sample_pass_rate': result['pass_rate'],
                    'estimated_full_passed': int(result['passed'] * extrapolation_factor),
                    'estimated_full_failed': int(result['failed'] * extrapolation_factor),
                    'estimated_full_pass_rate': result['pass_rate'],
                    'failed_records': result.get('failed_records', {}),
                    'fix_suggestion': result.get('fix_suggestion', '')
                }
        
        # Calculate overall quality score
        extrapolated['overall_quality_score'] = self._calculate_overall_quality_score(extrapolated)
        
        return extrapolated
    
    def _calculate_overall_quality_score(self, results: Dict) -> float:
        """Calculate overall data quality score."""
        
        # Weight rules by severity
        weights = {'critical': 0.5, 'important': 0.3, 'optional': 0.2}
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for category, weight in weights.items():
            category_key = f"{category}_rules"
            if category_key in results:
                category_pass_rates = [
                    rule['estimated_full_pass_rate'] 
                    for rule in results[category_key].values()
                ]
                
                if category_pass_rates:
                    category_avg = sum(category_pass_rates) / len(category_pass_rates)
                    weighted_score += category_avg * weight
                    total_weight += weight
        
        return (weighted_score / total_weight * 100) if total_weight > 0 else 0.0
    
    def _generate_validation_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Check critical rules
        for rule_id, result in results['critical_rules'].items():
            if result['estimated_full_pass_rate'] < self.sampling_config['quality_thresholds']['critical']:
                recommendations.append(
                    f"CRITICAL: {result['description']} - "
                    f"Pass rate: {result['estimated_full_pass_rate']:.1%} "
                    f"(threshold: {self.sampling_config['quality_thresholds']['critical']:.1%})"
                )
                recommendations.append(f"  Fix suggestion: {result['fix_suggestion']}")
        
        # Check important rules
        for rule_id, result in results['important_rules'].items():
            if result['estimated_full_pass_rate'] < self.sampling_config['quality_thresholds']['important']:
                recommendations.append(
                    f"IMPORTANT: {result['description']} - "
                    f"Pass rate: {result['estimated_full_pass_rate']:.1%} "
                    f"(threshold: {self.sampling_config['quality_thresholds']['important']:.1%})"
                )
        
        # Check overall quality
        if results['overall_quality_score'] < 80:
            recommendations.append(
                f"Overall data quality score is {results['overall_quality_score']:.1f}/100. "
                "Consider comprehensive data cleaning before proceeding with analysis."
            )
        
        return recommendations
    
    def create_validation_report(self, output_path: str = None) -> str:
        """Create comprehensive validation report."""
        
        if output_path is None:
            output_path = f"cad_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'validation_metadata': {
                'timestamp': datetime.now().isoformat(),
                'validator_version': 'CAD_Validator_2025.08.10',
                'total_records_validated': self.validation_results['total_records']
            },
            'validation_results': self.validation_results,
            'sampling_configuration': self.sampling_config,
            'validation_rules': self.validation_rules,
            'summary': {
                'overall_quality_score': self.validation_results.get('overall_quality_score', 0),
                'critical_issues': len([r for r in self.validation_results.get('critical_rules', {}).values() 
                                      if r.get('estimated_full_pass_rate', 0) < self.sampling_config['quality_thresholds']['critical']]),
                'important_issues': len([r for r in self.validation_results.get('important_rules', {}).values() 
                                       if r.get('estimated_full_pass_rate', 0) < self.sampling_config['quality_thresholds']['important']]),
                'recommendations_count': len(self.validation_results.get('recommended_actions', []))
            }
        }
        
        # Save report
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Validation report saved: {output_path}")
        return output_path
```

## **Usage Example**

```python
def validate_cad_dataset_with_sampling(cad_file: str, sampling_method: str = 'stratified') -> Dict:
    """Validate CAD dataset with specified sampling method."""
    
    # Load CAD data
    df = pd.read_excel(cad_file)
    
    # Initialize validator
    validator = CADDataValidator()
    
    # Run validation
    results = validator.validate_cad_dataset(df, sampling_method)
    
    # Create report
    report_path = validator.create_validation_report()
    
    return results, report_path

# Example usage
if __name__ == "__main__":
    cad_file = "path/to/large_cad_dataset.xlsx"
    
    # Test different sampling methods
    sampling_methods = ['stratified', 'systematic', 'random']
    
    for method in sampling_methods:
        print(f"\n{'='*50}")
        print(f"VALIDATION WITH {method.upper()} SAMPLING")
        print(f"{'='*50}")
        
        results, report_path = validate_cad_dataset_with_sampling(cad_file, method)
        
        print(f"Overall Quality Score: {results['overall_quality_score']:.1f}/100")
        print(f"Total Records: {results['total_records']:,}")
        print(f"Critical Issues: {len([r for r in results['critical_rules'].values() if r['estimated_full_pass_rate'] < 0.95])}")
        print(f"Important Issues: {len([r for r in results['important_rules'].values() if r['estimated_full_pass_rate'] < 0.85])}")
        print(f"Recommendations: {len(results['recommended_actions'])}")
        
        # Show top recommendations
        print("\nTop Recommendations:")
        for i, rec in enumerate(results['recommended_actions'][:3], 1):
            print(f"  {i}. {rec}")
```

## **Key Features of This Validation Framework**

### **Sampling Strategies:**
1. **Stratified Sampling**: Ensures representative samples across incident types, reporting methods, and time periods
2. **Systematic Sampling**: Fixed interval sampling for consistent coverage
3. **Random Sampling**: Simple random sampling for baseline comparison

### **Validation Rules:**
1. **Critical Rules**: Must pass 95% threshold (case numbers, datetime, incident types)
2. **Important Rules**: Must pass 85% threshold (addresses, officers, dispositions)
3. **Optional Rules**: Should pass 70% threshold (standardization, consistency)

### **Data Quality Metrics:**
1. **Field-level validation**: Format, completeness, consistency checks
2. **Cross-field validation**: Time sequences, response consistency
3. **Business rule validation**: Officer assignments, disposition logic

### **Reporting Features:**
1. **Comprehensive reports**: JSON format with detailed analysis
2. **Extrapolated results**: Sample results projected to full dataset
3. **Actionable recommendations**: Specific fixes for identified issues
4. **Quality scoring**: Overall data quality assessment

This framework provides a robust foundation for validating large CAD datasets and identifying specific areas that need data cleaning attention.