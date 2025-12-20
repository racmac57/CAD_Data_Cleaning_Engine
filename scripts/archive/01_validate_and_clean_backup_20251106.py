import pandas as pd
import numpy as np
import logging
import re
import json
import glob
import os
from datetime import datetime
from sklearn.model_selection import train_test_split
from typing import Dict, Any
import dask.dataframe as dd
from dask import delayed
import dask.diagnostics as diagnostics
import psutil
from pydantic import BaseModel, ValidationError
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytest

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _clean_partition(part, config, incident_mapping):
    """Clean a single partition of the DataFrame.

    Args:
        part (pd.DataFrame): DataFrame partition to clean.
        config (dict): Configuration dictionary.
        incident_mapping (pd.DataFrame): Incident mapping DataFrame.

    Returns:
        pd.DataFrame: Cleaned partition with modification stats in attrs.
    """
    part = part.copy()
    stats = {'rows_modified': 0}
    for col in ['Incident', 'How Reported', 'Response Type', 'Disposition', 'Officer']:
        if col in part.columns:
            original = part[col].copy()
            part[col] = part[col].astype(str).str.upper().str.strip()
            stats['rows_modified'] += (part[col] != original).sum()
    if 'FullAddress2' in part.columns:
        original = part['FullAddress2'].copy()
        abbreviations = config.get('address_abbreviations', {})
        for abbr, full in abbreviations.items():
            part['FullAddress2'] = part['FullAddress2'].astype(str).str.replace(abbr, full, case=False, regex=True)
        part['FullAddress2'] = part['FullAddress2'].str.upper()
        stats['rows_modified'] += (part['FullAddress2'] != original).sum()
    if 'Incident' in part.columns and not incident_mapping.empty:
        part = part.merge(incident_mapping, on='Incident', how='left')
        part['Incident'] = part['Incident_Norm'].fillna(part['Incident'])
        part['Response Type'] = part['Response Type_x'].fillna(part['Response Type_y'])
        stats['rows_modified'] += part['Incident_Norm'].notna().sum()
    part.attrs['stats'] = stats
    return part

class ConfigSchema(BaseModel):
    """Pydantic schema for validating configuration."""
    address_abbreviations: Dict[str, str]
    validation_lists: Dict[str, list[str]]

class CADDataValidator:
    """A robust class for cleaning, validating, and analyzing CAD data with parallel processing.

    Incorporates feedback for consistency, active cleaning, external configuration, and Dask-based parallelism.
    """

    def __init__(self, config_path: str = 'config_enhanced.json'):
        """Initialize validator with configuration, rules, and cleaning patterns.

        Args:
            config_path (str): Path to the JSON configuration file. Defaults to 'config_enhanced.json'.

        Attributes:
            config (Dict[str, Any]): Loaded configuration dictionary.
            validation_rules (Dict): Rules for data validation.
            sampling_config (Dict): Configuration for sampling methods.
            validation_results (Dict): Results of validation process.
        """
        self.config = self._load_config(config_path)
        self.incident_mapping = self._load_incident_mapping()
        self.validation_rules = self._initialize_validation_rules()
        self.sampling_config = {
            'stratified_sample_size': 1000,
            'systematic_interval': 100,
            'quality_thresholds': {'critical': 0.95, 'important': 0.85, 'optional': 0.70}
        }
        self.validation_results = {
            'total_records': 0,
            'rules_passed': {},
            'rules_failed': {},
            'sample_analysis': {},
            'data_quality_score': 0.0,
            'recommended_actions': [],
            'source_dataset': None
        }
        self.current_dataset_label = None

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load and validate configuration from a JSON file with a fallback default.

        Args:
            config_path (str): Path to the JSON configuration file.

        Returns:
            Dict[str, Any]: Validated configuration dictionary.

        Raises:
            ValidationError: If the config file does not match the expected schema.
        """
        logger.info(f"Loading configuration from {config_path}...")
        default_config = {
            'address_abbreviations': {' ST ': ' STREET ', ' AVE ': ' AVENUE ', ' BLVD ': ' BOULEVARD '},
            'validation_lists': {
                'valid_dispositions': ['COMPLETE', 'ADVISED', 'ARREST', 'UNFOUNDED', 'CANCELLED', 'GOA', 'UTL', 'SEE REPORT', 'REFERRED'],
                'valid_zones': ['5', '6', '7', '8', '9'],
                'emergency_incidents': ['ROBBERY', 'ASSAULT', 'BURGLARY', 'SHOOTING', 'STABBING'],
                'non_emergency_incidents': ['NOISE COMPLAINT', 'PARKING VIOLATION', 'CIVIL DISPUTE'],
                'how_reported': ['9-1-1', 'WALK-IN', 'PHONE', 'SELF-INITIATED', 'RADIO', 'TELETYPE', 'FAX', 'OTHER - SEE NOTES', 'EMAIL', 'MAIL', 'VIRTUAL PATROL', 'CANCELED CALL']
            }
        }
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            ConfigSchema(**config)  # Validate schema
            for key in default_config:
                if key not in config:
                    logger.warning(f"Missing config key: {key}. Using default.")
                    config[key] = default_config[key]
            return config
        except FileNotFoundError:
            logger.error(f"Config file {config_path} not found. Using default configuration.")
            return default_config
        except ValidationError as e:
            logger.error(f"Invalid config schema: {e}. Using default configuration.")
            return default_config

    def _load_incident_mapping(self) -> pd.DataFrame:
        """Load incident mapping from CSV file.

        Returns:
            pd.DataFrame: Mapping of Incident to Incident_Norm and Response_Type.

        Raises:
            FileNotFoundError: If the mapping file is not found.
        """
        # Try multiple possible locations for the mapping file
        possible_paths = [
            r"C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\Classifications\CallTypes\CallType_Categories.csv",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'CallType_Categories.csv'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'CallType_Categories.csv')
        ]
        
        for mapping_path in possible_paths:
            try:
                df = pd.read_csv(mapping_path)
                logger.info(f"Successfully loaded incident mapping from: {mapping_path}")
                return df[['Incident', 'Incident_Norm', 'Response_Type']].drop_duplicates()
            except FileNotFoundError:
                continue
        
        logger.warning("Incident mapping file not found in any expected location. Using empty mapping.")
        return pd.DataFrame(columns=['Incident', 'Incident_Norm', 'Response_Type'])

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply cleaning operations to the DataFrame.

        Args:
            df (pd.DataFrame): Input DataFrame to clean.

        Returns:
            pd.DataFrame: Cleaned DataFrame with standardized text and addresses.
        """
        if df.empty:
            logger.warning("Empty DataFrame provided. Returning empty DataFrame.")
            return df
        logger.info("Starting data cleaning process...")
        
        cleaned_df = df.copy()
        total_modified = 0
        
        # Clean text fields
        for col in ['Incident', 'How Reported', 'Response Type', 'Disposition', 'Officer']:
            if col in cleaned_df.columns:
                original = cleaned_df[col].copy()
                cleaned_df[col] = cleaned_df[col].astype(str).str.upper().str.strip()
                total_modified += (cleaned_df[col] != original).sum()
        
        # Clean addresses
        if 'FullAddress2' in cleaned_df.columns:
            original = cleaned_df['FullAddress2'].copy()
            abbreviations = self.config.get('address_abbreviations', {})
            for abbr, full in abbreviations.items():
                cleaned_df['FullAddress2'] = cleaned_df['FullAddress2'].astype(str).str.replace(abbr, full, case=False, regex=True)
            cleaned_df['FullAddress2'] = cleaned_df['FullAddress2'].str.upper()
            total_modified += (cleaned_df['FullAddress2'] != original).sum()
        
        # Apply incident mapping
        if 'Incident' in cleaned_df.columns and not self.incident_mapping.empty:
            cleaned_df = cleaned_df.merge(self.incident_mapping, on='Incident', how='left', suffixes=('', '_mapping'))
            cleaned_df['Incident'] = cleaned_df['Incident_Norm'].fillna(cleaned_df['Incident'])
            if 'Response Type_mapping' in cleaned_df.columns:
                cleaned_df['Response Type'] = cleaned_df['Response Type_mapping'].fillna(cleaned_df['Response Type'])
            total_modified += cleaned_df['Incident_Norm'].notna().sum()
        
        logger.info(f"Cleaned {total_modified:,} rows in total.")
        return cleaned_df

    def validate_cad_dataset(self, df: pd.DataFrame, sampling_method: str = 'stratified') -> dict:
        """Validate CAD dataset with cleaning and sampling.

        Args:
            df (pd.DataFrame): Input DataFrame to validate.
            sampling_method (str): Sampling method ('stratified', 'systematic', 'random'). Defaults to 'stratified'.

        Returns:
            dict: Validation results including quality score and recommendations.
        """
        cleaned_df = self.clean_data(df)
        logger.info(f"Starting CAD dataset validation with {sampling_method} sampling...")
        self.validation_results['total_records'] = len(cleaned_df)
        if self.current_dataset_label:
            self.validation_results['source_dataset'] = self.current_dataset_label

        sample_df = self._create_sample(cleaned_df, sampling_method)

        # Store sampling metadata from sample_df attrs
        if hasattr(sample_df, 'attrs'):
            self.validation_results['stratum_distribution'] = sample_df.attrs.get('stratum_distribution', {})
            self.validation_results['stratification_method'] = sample_df.attrs.get('stratification_method', sampling_method)

        sample_results = self._validate_sample(sample_df)
        full_results = self._extrapolate_results(sample_results, cleaned_df)
        recommendations = self._generate_validation_recommendations(full_results)

        self.validation_results.update(full_results)
        self.validation_results['recommended_actions'] = recommendations
        return self.validation_results

    def _create_sample(self, df: pd.DataFrame, method: str) -> pd.DataFrame:
        """Create a sample from the DataFrame using the specified method.

        Args:
            df (pd.DataFrame): Input DataFrame to sample.
            method (str): Sampling method ('stratified', 'systematic', 'random').

        Returns:
            pd.DataFrame: Sampled DataFrame.

        Raises:
            ValueError: If an unknown sampling method is provided.
        """
        if method == 'stratified':
            return self._stratified_sampling(df)
        elif method == 'systematic':
            return self._systematic_sampling(df)
        elif method == 'random':
            return self._random_sampling(df)
        else:
            raise ValueError(f"Unknown sampling method: {method}")

    def _stratified_sampling(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create a stratified sample using incident-based strata only."""
        logger.info("Creating stratified sample...")
        df_with_strata = df.copy()

        if 'Incident' in df.columns:
            incident_counts = df['Incident'].value_counts()
            top_incidents = incident_counts[incident_counts > 50].index
            df_with_strata['incident_stratum'] = df_with_strata['Incident'].apply(
                lambda x: x if x in top_incidents else 'Other')
            unique_strata = df_with_strata['incident_stratum'].nunique()
            logger.info("Using %d incident strata (min size > 50).", unique_strata)
        else:
            logger.warning("Incident column missing; assigning all records to 'Unknown' stratum.")
            df_with_strata['incident_stratum'] = 'Unknown'

        sample_size = min(self.sampling_config['stratified_sample_size'], len(df))

        try:
            sample_df, _ = train_test_split(
                df_with_strata, test_size=1 - (sample_size / len(df)),
                stratify=df_with_strata[['incident_stratum']],
                random_state=42
            )
            logger.info("Created stratified sample (incident_stratum): %s records", f"{len(sample_df):,}")

            stratum_dist = df_with_strata['incident_stratum'].value_counts().to_dict()
            logger.info("Stratum distribution: %s", stratum_dist)
            sample_df.attrs['stratum_distribution'] = stratum_dist
            sample_df.attrs['stratification_method'] = 'incident_stratum'

        except Exception as e:
            logger.warning(f"Stratified sampling failed: {e}. Falling back to random.")
            sample_df = df.sample(n=sample_size, random_state=42)
            sample_df.attrs['stratification_method'] = 'random'
            sample_df.attrs['stratum_distribution'] = {'random_sample': len(sample_df)}

        logger.info("Final sample size: %s records", f"{len(sample_df):,}")
        return sample_df

    def _systematic_sampling(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create systematic sample with fixed interval.

        Args:
            df (pd.DataFrame): Input DataFrame to sample.

        Returns:
            pd.DataFrame: Systematic sample DataFrame.
        """
        logger.info("Creating systematic sample...")
        interval = self.sampling_config['systematic_interval']
        start_idx = np.random.randint(0, interval)
        sample_indices = list(range(start_idx, len(df), interval))
        sample_df = df.iloc[sample_indices].copy()
        logger.info(f"Created systematic sample: {len(sample_df):,} records (interval: {interval})")
        return sample_df

    def _random_sampling(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create random sample.

        Args:
            df (pd.DataFrame): Input DataFrame to sample.

        Returns:
            pd.DataFrame: Random sample DataFrame.
        """
        logger.info("Creating random sample...")
        sample_size = min(self.sampling_config['stratified_sample_size'], len(df))
        sample_df = df.sample(n=sample_size, random_state=42)
        logger.info(f"Created random sample: {len(sample_df):,} records")
        return sample_df

    def _categorize_how_reported(self, value):
        """Categorize 'How Reported' values into standard groups.

        Args:
            value: Value to categorize.

        Returns:
            str: Categorized value ('Emergency', 'Phone', 'Walk-in', 'Self-Initiated', 'Other', or 'Unknown').
        """
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
        """Categorize hour into time periods.

        Args:
            hour: Hour value to categorize.

        Returns:
            str: Time period ('Morning', 'Afternoon', 'Evening', 'Night', or 'Unknown').
        """
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

    def _validate_sample(self, sample_df: pd.DataFrame) -> dict:
        """Run validation rules on sample.

        Args:
            sample_df (pd.DataFrame): Sample DataFrame to validate.

        Returns:
            dict: Validation results for each rule category.
        """
        logger.info("Running validation rules on sample...")
        results = {
            'critical_rules': {},
            'important_rules': {},
            'optional_rules': {},
            'sample_size': len(sample_df)
        }

        for category, rules in self.validation_rules.items():
            for rule_id, rule in rules.items():
                result = self._apply_validation_rule(sample_df, rule)
                result.update({
                    'rule_id': rule_id,
                    'description': rule['description'],
                    'severity': rule['severity'],
                    'fix_suggestion': rule.get('fix_suggestion', '')
                })
                results[category][rule_id] = result

        return results

    def _apply_validation_rule(self, df: pd.DataFrame, rule: dict) -> dict:
        """Apply a single validation rule to a DataFrame partition.

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            rule (dict): Validation rule configuration.

        Returns:
            dict: Validation result for the rule.
        """
        rule_id = rule['rule_id']
        field = rule.get('field')
        fields = rule.get('fields', [field] if field else [])
        result = {
            'rule_id': rule_id, 'description': rule['description'], 'severity': rule['severity'],
            'passed': 0, 'failed': 0, 'pass_rate': 0.0, 'failed_records': [],
            'fix_suggestion': rule.get('fix_suggestion', ''), 'sample_size': len(df)
        }
        missing_fields = [f for f in fields if f not in df.columns]
        if missing_fields:
            result.update({'error': f"Missing fields: {missing_fields}", 'failed': len(df)})
            return result

        if rule_id == 'CRIT_001': result = self._validate_case_number_format(df, result)
        elif rule_id == 'CRIT_002': result = self._validate_case_number_uniqueness(df, result)
        elif rule_id == 'CRIT_003': result = self._validate_call_datetime(df, result)
        elif rule_id == 'CRIT_004': result = self._validate_incident_type_presence(df, result)
        elif rule_id == 'IMP_001': result = self._validate_address_completeness(df, result)
        elif rule_id == 'IMP_002': result = self._validate_officer_assignment(df, result)
        elif rule_id == 'IMP_003': result = self._validate_disposition_consistency(df, result)
        elif rule_id == 'IMP_004': result = self._validate_time_sequence(df, result)
        elif rule_id == 'IMP_005': result = self._validate_datetime_duration(df, result)
        elif rule_id == 'IMP_006': result = self._validate_time_spent(df, result)
        elif rule_id == 'OPT_001': result = self._validate_how_reported(df, result)
        elif rule_id == 'OPT_002': result = self._validate_zone_validity(df, result)
        elif rule_id == 'OPT_003': result = self._validate_response_type_consistency(df, result)
        
        result['pass_rate'] = result['passed'] / result['sample_size'] if result['sample_size'] > 0 else 0.0
        return result

    def _validate_case_number_format(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate case number format (YY-XXXXXX or YY-XXXXXX[A-Z] for supplements).

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and failed records.
        """
        field, pattern = 'ReportNumberNew', r'^\d{2,4}-\d{6}[A-Z]?$'
        valid = df[field].astype(str).str.match(pattern, na=False)
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        return result

    def _validate_case_number_uniqueness(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate uniqueness of case numbers.

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and duplicate records.
        """
        field = 'ReportNumberNew'
        unique_count = df[field].nunique()
        result.update({'passed': unique_count, 'failed': len(df) - unique_count})
        duplicates = df[field].value_counts()
        result['failed_records'] = duplicates[duplicates > 1].head(10).to_dict()
        return result

    def _validate_call_datetime(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate 'Time of Call' datetime within reasonable range.

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and failed records.
        """
        field = 'Time of Call'
        parsed = pd.to_datetime(df[field], errors='coerce')
        valid = parsed.notna() & (parsed >= '2020-01-01') & (parsed <= '2030-12-31')
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        return result

    def _validate_incident_type_presence(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate presence of non-empty incident type.

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and failed records.
        """
        field = 'Incident'
        valid = df[field].notna() & (df[field].astype(str).str.strip() != '')
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        return result

    def _validate_address_completeness(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate presence and non-generic addresses.

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and failed records.
        """
        field = 'FullAddress2'
        generic = ['UNKNOWN', 'NOT PROVIDED', 'N/A', 'NONE', '', 'TBD', 'TO BE DETERMINED']
        pattern = r'^\d+ .+ (Street|Avenue|Road|Place|Drive|Court|Boulevard|St|Ave|Rd|Pl|Dr|Ct|Blvd)( & .+ (Street|Avenue|Road|Place|Drive|Court|Boulevard|St|Ave|Rd|Pl|Dr|Ct|Blvd))?, Hackensack, NJ, 07601$'
        valid = df[field].notna() & (~df[field].astype(str).str.upper().isin(generic)) & df[field].astype(str).str.match(pattern, na=False, case=False)
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        return result

    def _validate_officer_assignment(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate officer assignment for dispatched calls.

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and failed records.
        """
        dispatched = df['Time Dispatched'].notna() if 'Time Dispatched' in df.columns else pd.Series([True] * len(df))
        has_officer = df['Officer'].notna() & (df['Officer'].astype(str).str.strip() != '')
        valid = ~(dispatched & ~has_officer)
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid]['Officer'].value_counts().head(10).to_dict()
        return result

    def _validate_disposition_consistency(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate disposition against approved list.

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and failed records.
        """
        field = 'Disposition'
        valid_list = self.config['validation_lists']['valid_dispositions']
        valid = df[field].astype(str).str.strip().isin(valid_list)
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        return result

    def _validate_time_sequence(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate logical time sequence (Call -> Dispatch -> Out -> In).

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and failed records.
        """
        fields = ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In']
        times = {f: pd.to_datetime(df.get(f), errors='coerce') for f in fields}
        valid_sequence = pd.Series([True] * len(df), index=df.index)
        if 'Time of Call' in df and 'Time Dispatched' in df:
            valid_sequence &= (times['Time of Call'] <= times['Time Dispatched']) | times['Time of Call'].isna() | times['Time Dispatched'].isna()
        if 'Time Dispatched' in df and 'Time Out' in df:
            valid_sequence &= (times['Time Dispatched'] <= times['Time Out']) | times['Time Dispatched'].isna() | times['Time Out'].isna()
        if 'Time Out' in df and 'Time In' in df:
            valid_sequence &= (times['Time Out'] <= times['Time In']) | times['Time Out'].isna() | times['Time In'].isna()
        result.update({'passed': valid_sequence.sum(), 'failed': (~valid_sequence).sum()})
        if (~valid_sequence).any():
            failed_df = df[~valid_sequence][fields].head(10)
            result['failed_records'] = failed_df[fields].to_dict(orient='records')
        return result

    def _validate_datetime_duration(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate duration between datetime fields.

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and failed records.
        """
        fields = ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In']
        
        # Parse datetime fields first
        parsed_times = {}
        for field in fields:
            if field in df.columns:
                parsed_times[field] = pd.to_datetime(df[field], errors='coerce')
            else:
                parsed_times[field] = pd.Series([pd.NaT] * len(df), index=df.index)
        
        # Calculate durations only if we have valid datetime columns
        valid = pd.Series([True] * len(df), index=df.index)
        
        if 'Time of Call' in df.columns and 'Time Dispatched' in df.columns:
            response_duration = parsed_times['Time Dispatched'] - parsed_times['Time of Call']
            valid &= (response_duration >= pd.Timedelta(0)) | response_duration.isna()
        
        if 'Time Dispatched' in df.columns and 'Time Out' in df.columns:
            out_duration = parsed_times['Time Out'] - parsed_times['Time Dispatched']
            valid &= (out_duration >= pd.Timedelta(0)) | out_duration.isna()
        
        if 'Time Out' in df.columns and 'Time In' in df.columns:
            in_duration = parsed_times['Time In'] - parsed_times['Time Out']
            valid &= (in_duration >= pd.Timedelta(0)) | in_duration.isna()
        
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        if (~valid).any():
            failed_df = df[~valid][fields].head(10)
            result['failed_records'] = failed_df[fields].to_dict(orient='records')
        return result

    def _validate_time_spent(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate Time Spent as a positive duration.

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and failed records.
        """
        field = 'Time Spent'
        if field in df.columns:
            durations = pd.to_timedelta(df[field], errors='coerce')
            valid = durations.notna() & (durations >= pd.Timedelta(0)) & (durations <= pd.Timedelta(days=1))
            result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
            result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        else:
            result.update({'passed': 0, 'failed': len(df), 'failed_records': {}})
        return result

    def _validate_how_reported(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate standardization of 'How Reported' field.

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and failed records.
        """
        field = 'How Reported'
        valid_list = self.config['validation_lists']['how_reported']
        is_date = df[field].astype(str).str.match(r'^\d{4}-\d{2}-\d{2}', na=False)
        non_standard = ~df[field].astype(str).str.upper().isin(valid_list)
        issues = is_date | non_standard
        result.update({'passed': (~issues).sum(), 'failed': issues.sum()})
        result['failed_records'] = df[issues][field].value_counts().head(10).to_dict()
        return result

    def _validate_zone_validity(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate PD Zone against valid identifiers.

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and failed records.
        """
        field = 'PDZone'
        valid_zones = self.config['validation_lists']['valid_zones']
        valid = df[field].astype(str).str.strip().isin(valid_zones)
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        return result

    def _validate_response_type_consistency(self, df: pd.DataFrame, result: dict) -> dict:
        """Validate response type consistency with incident severity.

        Args:
            df (pd.DataFrame): DataFrame partition to validate.
            result (dict): Initial result dictionary.

        Returns:
            dict: Updated result with pass/fail counts and failed records.
        """
        emergency_incidents = self.config['validation_lists']['emergency_incidents']
        non_emergency_incidents = self.config['validation_lists']['non_emergency_incidents']
        incident = df['Incident'].astype(str).str.upper()
        response = df['Response Type'].astype(str).str.upper()
        is_emergency_incident = incident.isin(emergency_incidents)
        is_emergency_response = response.isin(['EMERGENCY', 'PRIORITY'])
        is_non_emergency_incident = incident.isin(non_emergency_incidents)
        is_non_emergency_response = response.isin(['NON-EMERGENCY', 'ROUTINE'])
        consistent = ((is_emergency_incident & is_emergency_response) |
                      (is_non_emergency_incident & is_non_emergency_response) |
                      (~is_emergency_incident & ~is_non_emergency_incident))
        result.update({'passed': consistent.sum(), 'failed': (~consistent).sum()})
        if (~consistent).any():
            failed_df = df[~consistent][['Incident', 'Response Type']].head(10)
            result['failed_records'] = failed_df.to_dict(orient='records')
        return result

    def _extrapolate_results(self, sample_results: dict, full_df: pd.DataFrame) -> dict:
        """Extrapolate sample validation results to the full dataset.

        Args:
            sample_results (dict): Validation results from sample.
            full_df (pd.DataFrame): Full DataFrame for size reference.

        Returns:
            dict: Extrapolated results with estimated pass/fail counts.
        """
        extrapolated = {'critical_rules': {}, 'important_rules': {}, 'optional_rules': {}}
        full_size = len(full_df)
        sample_size = sample_results['sample_size']
        factor = full_size / sample_size if sample_size > 0 else 0
        
        for category in extrapolated.keys():
            for rule_id, res in sample_results[category].items():
                extrapolated[category][rule_id] = {
                    'rule_id': rule_id, 'description': res['description'], 'severity': res['severity'],
                    'sample_passed': res['passed'], 'sample_failed': res['failed'],
                    'sample_pass_rate': res['pass_rate'],
                    'estimated_full_passed': int(res['passed'] * factor),
                    'estimated_full_failed': int(res['failed'] * factor),
                    'estimated_full_pass_rate': res['pass_rate'],
                    'failed_records': res.get('failed_records', {}),
                    'fix_suggestion': res.get('fix_suggestion', '')
                }
        extrapolated['overall_quality_score'] = self._calculate_overall_quality_score(extrapolated)
        return extrapolated

    def _calculate_overall_quality_score(self, results: dict) -> float:
        """Calculate overall data quality score based on rule pass rates.

        Args:
            results (dict): Validation results with pass rates.

        Returns:
            float: Weighted quality score (0-100).
        """
        weights = {'critical': 0.5, 'important': 0.3, 'optional': 0.2}
        score, total_weight = 0.0, 0.0
        for category, weight in weights.items():
            rates = [r['estimated_full_pass_rate'] for r in results[f"{category}_rules"].values()]
            if rates:
                avg_rate = sum(rates) / len(rates)
                score += avg_rate * weight
                total_weight += weight
        return (score / total_weight * 100) if total_weight > 0 else 0.0

    def _generate_validation_recommendations(self, results: dict) -> list:
        """Generate recommendations based on validation results.

        Args:
            results (dict): Validation results with pass rates.

        Returns:
            list: List of recommendation strings for failed rules.
        """
        recommendations = []
        for category in ['critical', 'important', 'optional']:
            threshold = self.sampling_config['quality_thresholds'][category]
            for rule_id, res in results[f"{category}_rules"].items():
                if res['estimated_full_pass_rate'] < threshold:
                    recommendations.append(
                        f"{category.upper()}: {res['description']} - "
                        f"Pass rate: {res['estimated_full_pass_rate']:.1%} "
                        f"(threshold: {threshold:.1%})"
                    )
                    recommendations.append(f"  Fix suggestion: {res['fix_suggestion']}")
        return recommendations

    def create_validation_report(self, output_path: str = None) -> str:
        """Create a comprehensive validation report in JSON format.

        Args:
            output_path (str, optional): Path to save the report. Defaults to timestamped filename.

        Returns:
            str: Path to the saved report file.
        """
        dataset_label = self.validation_results.get('source_dataset') or getattr(self, 'current_dataset_label', None)
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            prefix = ''
            if dataset_label:
                label_stem = os.path.splitext(os.path.basename(dataset_label))[0]
                year_match = re.match(r'^(\d{4})', label_stem)
                if year_match:
                    prefix = f"{year_match.group(1)}_"
                else:
                    sanitized = re.sub(r'[^A-Za-z0-9]+', '_', label_stem).strip('_')
                    if sanitized:
                        prefix = f"{sanitized}_"
            output_path = f"{prefix}cad_validation_report_{timestamp}.json"

        report = {
            'validation_metadata': {
                'timestamp': datetime.now().isoformat(),
                'validator_version': 'CAD_Validator_2025.10.17',
                'total_records_validated': self.validation_results['total_records'],
                'stratification_method': self.validation_results.get('stratification_method', 'unknown'),
                'source_dataset': dataset_label,
                'report_filename': output_path
            },
            'validation_summary': {
                'overall_quality_score': self.validation_results.get('overall_quality_score', 0),
                'recommendations_count': len(self.validation_results.get('recommended_actions', []))
            },
            'sampling_metadata': {
                'stratum_distribution': self.validation_results.get('stratum_distribution', {}),
                'stratification_method': self.validation_results.get('stratification_method', 'unknown'),
                'sample_size': self.sampling_config.get('stratified_sample_size', 1000)
            },
            'recommended_actions': self.validation_results.get('recommended_actions', []),
            'validation_details': self.validation_results,
            'sampling_configuration': self.sampling_config
        }
        def clean_for_json(obj):
            """Recursively clean data structures for JSON serialization."""
            if isinstance(obj, dict):
                return {str(k): clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [clean_for_json(item) for item in obj]
            elif hasattr(obj, 'isoformat'):  # datetime objects
                return obj.isoformat()
            elif isinstance(obj, (pd.Timestamp, pd.Timedelta)):
                return str(obj)
            elif hasattr(obj, 'tolist'):  # numpy arrays
                return obj.tolist()
            elif hasattr(obj, '__dict__'):  # custom objects
                return str(obj)
            else:
                return obj
        
        # Clean the report data before JSON serialization
        cleaned_report = clean_for_json(report)
        
        with open(output_path, 'w') as f:
            json.dump(cleaned_report, f, indent=2)
        logger.info(f"Validation report saved: {output_path}")
        return output_path

    def _initialize_validation_rules(self) -> dict:
        """Initialize comprehensive validation rules for CAD data.

        Returns:
            dict: Dictionary of validation rules organized by severity.
        """
        return {
            'critical_rules': {
                'case_number_format': {
                    'rule_id': 'CRIT_001',
                    'description': 'Case number must follow format: YY-XXXXXX or YY-XXXXXX[A-Z] for supplements',
                    'field': 'ReportNumberNew',
                    'pattern': r'^\d{2,4}-\d{6}[A-Z]?$',
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
                },
                'datetime_duration_validity': {
                    'rule_id': 'IMP_005',
                    'description': 'Durations between datetime fields must be non-negative',
                    'fields': ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In'],
                    'severity': 'important',
                    'fix_suggestion': 'Correct negative durations or investigate data entry errors'
                },
                'time_spent_validity': {
                    'rule_id': 'IMP_006',
                    'description': 'Time Spent must be a positive duration',
                    'field': 'Time Spent',
                    'severity': 'important',
                    'fix_suggestion': 'Validate duration format and ensure positive values'
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

def validate_cad_dataset_with_sampling(config: Dict[str, Any], sampling_method: str = 'stratified'):
    """Validate CAD dataset with specified sampling method.

    Args:
        config (Dict[str, Any]): Configuration dictionary with 'file_path' and optional 'config_path'.
        sampling_method (str): Sampling method ('stratified', 'systematic', 'random'). Defaults to 'stratified'.

    Returns:
        tuple: Validation results and path to the saved report.

    Raises:
        ValueError: If 'file_path' is missing from config.
    """
    cad_file = config.get('file_path', '')
    if not cad_file:
        raise ValueError("Config must include 'file_path' key.")
    logger.info(f"Loading data from: {cad_file}")
    df = pd.read_excel(cad_file) if cad_file.endswith('.xlsx') else pd.read_csv(cad_file)
    validator = CADDataValidator(config_path=config.get('config_path', 'config_enhanced.json'))
    dataset_label = os.path.basename(cad_file)
    validator.current_dataset_label = dataset_label
    validator.validation_results['source_dataset'] = dataset_label
    results = validator.validate_cad_dataset(df, sampling_method)
    report_path = validator.create_validation_report()
    return results, report_path

if __name__ == "__main__":
    # --- Automated Batch Processing ---

    # Define the directory containing your raw data files
    raw_data_directory = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Pipeline\data\01_raw"

    # Find all .xlsx files in that directory
    all_cad_files = glob.glob(os.path.join(raw_data_directory, "*.xlsx"))

    print(f"Found {len(all_cad_files)} files to process.")

    # Loop through each file found and run the validation
    for cad_file_path in all_cad_files:
        print(f"\n{'='*60}\nPROCESSING: {os.path.basename(cad_file_path)}\n{'='*60}")

        # Load the main config, but use the current file path from the loop
        validator_config = {
            'file_path': cad_file_path,
            'config_path': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config_enhanced.json')
        }

        # Use only one sampling method for automated runs, 'stratified' is best
        results, report_file = validate_cad_dataset_with_sampling(validator_config, 'stratified')

        print(f"  - Overall Quality Score: {results.get('overall_quality_score', 0):.1f}/100")
        print(f"  - Full report saved to: {report_file}")

    print("\nAll files processed successfully!")

# --- Unit Tests ---

@pytest.fixture
def sample_data():
    """Provide sample data for testing, including edge cases."""
    return pd.DataFrame({
        'ReportNumberNew': ['25-123456', '25-987654A', '25-123457', '25-123456B', None, 'invalid', '25-123456AB'],
        'Incident': ['Noise Complaint', 'ROBBERY', 'Task Assignment', 'ASSAULT', '', None, 'UNKNOWN'],
        'How Reported': ['PHONE', '9-1-1', 'INVALID', 'RADIO', None, '2024-01-01', 'EMAIL'],
        'FullAddress2': ['123 Main Street, Hackensack, NJ, 07601', 'INVALID', '456 Elm St, Hackensack, NJ, 07601', 'Main & Atlantic, Hackensack, NJ, 07601', None, '123 Main St', '123 Main Street, Other City, NJ, 00000'],
        'PDZone': ['7', '5', '10', '6', None, '4', '9'],
        'Time of Call': ['2025-10-17 17:00:00', '2025-10-17 17:05:00', '2025-10-17 17:10:00', '2025-10-17 17:15:00', '2035-01-01 00:00:00', None, '2019-01-01 00:00:00'],
        'Time Dispatched': ['2025-10-17 17:02:00', '2025-10-17 17:06:00', '2025-10-17 17:12:00', '2025-10-17 17:14:00', None, '2025-10-17 16:59:00', '2025-10-17 17:16:00'],
        'Time Out': ['2025-10-17 17:03:00', '2025-10-17 17:07:00', '2025-10-17 17:13:00', '2025-10-17 17:16:00', None, '2025-10-17 17:00:00', '2025-10-17 17:15:00'],
        'Time In': ['2025-10-17 17:04:00', '2025-10-17 17:08:00', '2025-10-17 17:14:00', '2025-10-17 17:17:00', None, '2025-10-17 16:58:00', '2025-10-17 17:18:00'],
        'Time Spent': ['0 days 00:04:00', '0 days 00:03:00', '-0 days 00:01:00', '0 days 25:00:00', None, 'invalid', '0 days 00:00:00'],
        'Officer': ['P.O. John Doe', None, 'P.O. Jane Doe', 'P.O. John Doe', '', 'P.O. Invalid', None],
        'Disposition': ['COMPLETE', 'ADVISED', 'INVALID', 'COMPLETE', None, 'COMPLETE', 'ADVISED'],
        'Response Type': ['ROUTINE', 'EMERGENCY', 'ROUTINE', 'URGENT', None, 'EMERGENCY', 'ROUTINE']
    })

@pytest.fixture
def validator():
    """Provide a test instance of CADDataValidator."""
    return CADDataValidator()

def test_validate_case_number_format(validator, sample_data):
    result = validator._validate_case_number_format(sample_data, {'rule_id': 'CRIT_001', 'field': 'ReportNumberNew', 'severity': 'critical'})
    assert result['passed'] == 4
    assert result['failed'] == 3

def test_validate_case_number_uniqueness(validator, sample_data):
    result = validator._validate_case_number_uniqueness(sample_data, {'rule_id': 'CRIT_002', 'field': 'ReportNumberNew', 'severity': 'critical'})
    assert result['passed'] == 7  # Assuming all unique
    assert result['failed'] == 0

def test_validate_call_datetime(validator, sample_data):
    result = validator._validate_call_datetime(sample_data, {'rule_id': 'CRIT_003', 'field': 'Time of Call', 'severity': 'critical'})
    assert result['passed'] == 4
    assert result['failed'] == 3

def test_validate_incident_type_presence(validator, sample_data):
    result = validator._validate_incident_type_presence(sample_data, {'rule_id': 'CRIT_004', 'field': 'Incident', 'severity': 'critical'})
    assert result['passed'] == 5
    assert result['failed'] == 2

def test_validate_address_completeness(validator, sample_data):
    result = validator._validate_address_completeness(sample_data, {'rule_id': 'IMP_001', 'field': 'FullAddress2', 'severity': 'important'})
    assert result['passed'] == 3
    assert result['failed'] == 4

def test_validate_officer_assignment(validator, sample_data):
    result = validator._validate_officer_assignment(sample_data, {'rule_id': 'IMP_002', 'field': 'Officer', 'severity': 'important'})
    assert result['passed'] == 4
    assert result['failed'] == 3

def test_validate_disposition_consistency(validator, sample_data):
    result = validator._validate_disposition_consistency(sample_data, {'rule_id': 'IMP_003', 'field': 'Disposition', 'severity': 'important'})
    assert result['passed'] == 5
    assert result['failed'] == 2

def test_validate_time_sequence(validator, sample_data):
    result = validator._validate_time_sequence(sample_data, {'rule_id': 'IMP_004', 'fields': ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In'], 'severity': 'important'})
    assert result['passed'] == 4
    assert result['failed'] == 3

def test_validate_datetime_duration(validator, sample_data):
    result = validator._validate_datetime_duration(sample_data, {'rule_id': 'IMP_005', 'fields': ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In'], 'severity': 'important'})
    assert result['passed'] == 4
    assert result['failed'] == 3

def test_validate_time_spent(validator, sample_data):
    result = validator._validate_time_spent(sample_data, {'rule_id': 'IMP_006', 'field': 'Time Spent', 'severity': 'important'})
    assert result['passed'] == 2
    assert result['failed'] == 5

def test_validate_how_reported(validator, sample_data):
    result = validator._validate_how_reported(sample_data, {'rule_id': 'OPT_001', 'field': 'How Reported', 'severity': 'optional'})
    assert result['passed'] == 4
    assert result['failed'] == 3

def test_validate_zone_validity(validator, sample_data):
    result = validator._validate_zone_validity(sample_data, {'rule_id': 'OPT_002', 'field': 'PDZone', 'severity': 'optional'})
    assert result['passed'] == 5
    assert result['failed'] == 2

def test_validate_response_type_consistency(validator, sample_data):
    result = validator._validate_response_type_consistency(sample_data, {'rule_id': 'OPT_003', 'fields': ['Response Type', 'Incident'], 'severity': 'optional'})
    assert result['passed'] == 5
    assert result['failed'] == 2

def test_clean_data_incident_mapping(validator, sample_data):
    cleaned = validator.clean_data(sample_data)
    assert cleaned['Incident'].iloc[0] == 'NOISE COMPLAINT'  # Assuming mapping normalizes to upper
    assert cleaned['Response Type'].iloc[0] == 'ROUTINE'

def test_validate_empty_dataframe(validator):
    empty_df = pd.DataFrame()
    cleaned = validator.clean_data(empty_df)
    assert cleaned.empty
    results = validator.validate_cad_dataset(empty_df)
    assert results['total_records'] == 0
    assert results['data_quality_score'] == 0.0

def test_validate_missing_columns(validator):
    df_missing = pd.DataFrame({'InvalidColumn': [1, 2]})
    results = validator.validate_cad_dataset(df_missing)
    for category in results:
        if isinstance(results[category], dict):
            for rule in results[category].values():
                assert 'error' in rule or rule['passed'] == 0