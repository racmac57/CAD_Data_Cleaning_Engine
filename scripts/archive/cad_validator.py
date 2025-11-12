import pandas as pd
import numpy as np
import logging
import re
import json
from datetime import datetime
from sklearn.model_selection import train_test_split
import warnings

# --- Setup ---
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
                'important': 0.85,  # 85% of records must pass important rules [cite: 3]
                'optional': 0.70   # 70% of records must pass optional rules [cite: 3]
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

    def _initialize_validation_rules(self) -> dict:
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

    def _initialize_cleaning_rules(self) -> dict:
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
                    ' ST ': ' STREET ', ' AVE ': ' AVENUE ', ' BLVD ': ' BOULEVARD ',
                    ' RD ': ' ROAD ', ' DR ': ' DRIVE '
                },
                'remove_extra_spaces': True,
                'uppercase': True,
                'handle_intersections': True
            },
            'datetime_cleaning': {
                'handle_date_conversions': True,
                'standardize_format': '%Y-%m-%d %H:%M:%S',
                'validate_range': {'start_date': '2020-01-01', 'end_date': '2030-12-31'}
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

    def validate_cad_dataset(self, df: pd.DataFrame, sampling_method: str = 'stratified') -> dict:
        """Main validation method with sampling."""
        logger.info(f"Starting CAD dataset validation with {sampling_method} sampling...")
        self.validation_results['total_records'] = len(df)
        sample_df = self._create_sample(df, sampling_method)
        sample_results = self._validate_sample(sample_df)
        full_results = self._extrapolate_results(sample_results, df)
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
        strata_definitions = {
            'incident_type': 'Incident' if 'Incident' in df.columns else None,
            'how_reported': 'How Reported' if 'How Reported' in df.columns else None,
            'time_period': 'Time of Call' if 'Time of Call' in df.columns else None
        }
        df_with_strata = df.copy()
        if strata_definitions['incident_type']:
            incident_counts = df[strata_definitions['incident_type']].value_counts()
            top_incidents = incident_counts.head(10).index
            df_with_strata['incident_stratum'] = df_with_strata[strata_definitions['incident_type']].apply(
                lambda x: x if x in top_incidents else 'Other'
            )
        if strata_definitions['how_reported']:
            df_with_strata['reported_stratum'] = df_with_strata[strata_definitions['how_reported']].apply(
                self._categorize_how_reported
            )
        if strata_definitions['time_period']:
            df_with_strata['time_stratum'] = pd.to_datetime(
                df_with_strata[strata_definitions['time_period']], errors='coerce'
            ).dt.hour.apply(self._categorize_time_period)
        
        sample_size = min(self.sampling_config['stratified_sample_size'], len(df))
        try:
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
        start_idx = np.random.randint(0, interval)
        sample_indices = list(range(start_idx, len(df), interval))
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
        if pd.isna(value): return 'Unknown'
        value_str = str(value).upper()
        if any(term in value_str for term in ['9-1-1', '911', 'EMERGENCY']): return 'Emergency'
        elif any(term in value_str for term in ['PHONE', 'CALL']): return 'Phone'
        elif any(term in value_str for term in ['WALK', 'PERSON']): return 'Walk-in'
        elif any(term in value_str for term in ['SELF', 'INITIATED']): return 'Self-Initiated'
        else: return 'Other'

    def _categorize_time_period(self, hour):
        if pd.isna(hour): return 'Unknown'
        try:
            hour = int(hour)
            if 6 <= hour < 12: return 'Morning'
            elif 12 <= hour < 18: return 'Afternoon'
            elif 18 <= hour < 22: return 'Evening'
            else: return 'Night'
        except:
            return 'Unknown'

    def _validate_sample(self, sample_df: pd.DataFrame) -> dict:
        """Run validation rules on sample."""
        logger.info("Running validation rules on sample...")
        results = {'critical_rules': {}, 'important_rules': {}, 'optional_rules': {}, 'sample_size': len(sample_df)}
        for rule_id, rule in self.validation_rules['critical_rules'].items():
            results['critical_rules'][rule_id] = self._apply_validation_rule(sample_df, rule)
        for rule_id, rule in self.validation_rules['important_rules'].items():
            results['important_rules'][rule_id] = self._apply_validation_rule(sample_df, rule)
        for rule_id, rule in self.validation_rules['optional_rules'].items():
            results['optional_rules'][rule_id] = self._apply_validation_rule(sample_df, rule)
        return results

    def _apply_validation_rule(self, df: pd.DataFrame, rule: dict) -> dict:
        """Apply a single validation rule."""
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
        
        # Apply specific validation logic based on rule_id
        if rule_id == 'CRIT_001': result = self._validate_case_number_format(df, result)
        elif rule_id == 'CRIT_002': result = self._validate_case_number_uniqueness(df, result)
        elif rule_id == 'CRIT_003': result = self._validate_call_datetime(df, result)
        elif rule_id == 'CRIT_004': result = self._validate_incident_type_presence(df, result)
        elif rule_id == 'IMP_001': result = self._validate_address_completeness(df, result)
        elif rule_id == 'IMP_002': result = self._validate_officer_assignment(df, result)
        elif rule_id == 'IMP_003': result = self._validate_disposition_consistency(df, result)
        elif rule_id == 'IMP_004': result = self._validate_time_sequence(df, result)
        elif rule_id == 'OPT_001': result = self._validate_how_reported(df, result)
        elif rule_id == 'OPT_002': result = self._validate_zone_validity(df, result)
        elif rule_id == 'OPT_003': result = self._validate_response_type_consistency(df, result)
        
        total_records = len(df)
        result['pass_rate'] = result['passed'] / total_records if total_records > 0 else 0.0
        return result

    def _validate_case_number_format(self, df: pd.DataFrame, result: dict) -> dict:
        field, pattern = 'ReportNumberNew', r'^\d{2,4}-\d{6}$'
        valid = df[field].astype(str).str.match(pattern, na=False)
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        return result

    def _validate_case_number_uniqueness(self, df: pd.DataFrame, result: dict) -> dict:
        field = 'ReportNumberNew'
        unique_count = df[field].nunique()
        result.update({'passed': unique_count, 'failed': len(df) - unique_count})
        duplicates = df[field].value_counts()
        result['failed_records'] = duplicates[duplicates > 1].head(10).to_dict()
        return result

    def _validate_call_datetime(self, df: pd.DataFrame, result: dict) -> dict:
        field = 'Time of Call'
        parsed = pd.to_datetime(df[field], errors='coerce')
        valid = parsed.notna() & (parsed >= '2020-01-01') & (parsed <= '2030-12-31')
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        return result

    def _validate_incident_type_presence(self, df: pd.DataFrame, result: dict) -> dict:
        field = 'Incident'
        valid = df[field].notna() & (df[field].astype(str).str.strip() != '')
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        return result
    
    def _validate_address_completeness(self, df: pd.DataFrame, result: dict) -> dict:
        field = 'FullAddress2'
        generic = ['UNKNOWN', 'NOT PROVIDED', 'N/A', 'NONE', '', 'TBD', 'TO BE DETERMINED']
        valid = df[field].notna() & (~df[field].astype(str).str.upper().isin(generic))
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        return result

    def _validate_officer_assignment(self, df: pd.DataFrame, result: dict) -> dict:
        dispatched = df['Time Dispatched'].notna() if 'Time Dispatched' in df.columns else pd.Series([True] * len(df))
        has_officer = df['Officer'].notna() & (df['Officer'].astype(str).str.strip() != '')
        valid = ~(dispatched & ~has_officer)
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid]['Officer'].value_counts().head(10).to_dict()
        return result

    def _validate_disposition_consistency(self, df: pd.DataFrame, result: dict) -> dict:
        field = 'Disposition'
        valid_list = ['COMPLETE', 'ADVISED', 'ARREST', 'UNFOUNDED', 'CANCELLED', 'GOA', 'UTL', 'SEE REPORT', 'REFERRED']
        valid = df[field].astype(str).str.upper().str.strip().isin(valid_list)
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        return result
    
    def _validate_time_sequence(self, df: pd.DataFrame, result: dict) -> dict:
        fields = ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In']
        times = {f: pd.to_datetime(df[f], errors='coerce') for f in fields}
        valid = (times['Time of Call'] <= times['Time Dispatched']) & \
                (times['Time Dispatched'] <= times['Time Out']) & \
                (times['Time Out'] <= times['Time In'])
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        return result

    def _validate_how_reported(self, df: pd.DataFrame, result: dict) -> dict:
        field = 'How Reported'
        standard = ['9-1-1', 'PHONE', 'WALK-IN', 'SELF-INITIATED', 'OTHER']
        is_date = df[field].astype(str).str.match(r'^\d{4}-\d{2}-\d{2}', na=False)
        non_standard = ~df[field].astype(str).str.upper().isin(standard)
        issues = is_date | non_standard
        result.update({'passed': (~issues).sum(), 'failed': issues.sum()})
        result['failed_records'] = df[issues][field].value_counts().head(10).to_dict()
        return result

    def _validate_zone_validity(self, df: pd.DataFrame, result: dict) -> dict:
        field = 'PDZone'
        valid_zones = [str(i) for i in range(1, 13)] + ['UNK']
        valid = df[field].astype(str).str.strip().isin(valid_zones)
        result.update({'passed': valid.sum(), 'failed': (~valid).sum()})
        result['failed_records'] = df[~valid][field].value_counts().head(10).to_dict()
        return result

    def _validate_response_type_consistency(self, df: pd.DataFrame, result: dict) -> dict:
        emergency_incidents = ['ROBBERY', 'ASSAULT', 'BURGLARY', 'SHOOTING', 'STABBING']
        non_emergency_incidents = ['NOISE COMPLAINT', 'PARKING VIOLATION', 'CIVIL DISPUTE']
        
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
        return result

    def _extrapolate_results(self, sample_results: dict, full_df: pd.DataFrame) -> dict:
        """Extrapolate sample results to full dataset."""
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
        """Calculate overall data quality score."""
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
        """Generate recommendations based on validation results."""
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
        """Create comprehensive validation report in JSON format."""
        if output_path is None:
            output_path = f"cad_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'validation_metadata': {
                'timestamp': datetime.now().isoformat(),
                'validator_version': 'CAD_Validator_2025.08.10',
                'total_records_validated': self.validation_results['total_records']
            },
            'validation_summary': {
                'overall_quality_score': self.validation_results.get('overall_quality_score', 0),
                'recommendations_count': len(self.validation_results.get('recommended_actions', []))
            },
            'recommended_actions': self.validation_results.get('recommended_actions', []),
            'validation_details': self.validation_results,
            'sampling_configuration': self.sampling_config,
        }
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Validation report saved: {output_path}")
        return output_path

# --- Usage Example ---
def validate_cad_dataset_with_sampling(cad_file: str, sampling_method: str = 'stratified'):
    """Helper function to load data, run validation, and create a report."""
    logger.info(f"Loading data from: {cad_file}")
    df = pd.read_excel(cad_file) if cad_file.endswith('.xlsx') else pd.read_csv(cad_file)
    validator = CADDataValidator()
    results = validator.validate_cad_dataset(df, sampling_method)
    report_path = validator.create_validation_report()
    return results, report_path

if __name__ == "__main__":
    # IMPORTANT: Update this path to your actual CAD data file.
    cad_file_path = r"C:\Users\carucci_r\OneDrive - City of Hackensack\05_EXPORTS\_CAD\99_sample\CAD_Data_Sample.xlsx"

    # Test the 'stratified' sampling method
    sampling_methods_to_test = ['stratified', 'systematic', 'random']
    
    for method in sampling_methods_to_test:
        print(f"\n{'='*60}")
        print(f"PERFORMING VALIDATION WITH '{method.upper()}' SAMPLING")
        print(f"{'='*60}")
        
        results, report_file = validate_cad_dataset_with_sampling(cad_file_path, method)
        
        print(f"Overall Quality Score: {results['overall_quality_score']:.1f}/100")
        print(f"Total Records Analyzed: {results['total_records']:,}")
        
        # Display top 3 recommendations for brevity
        recommendations = results.get('recommended_actions', [])
        print("\nTop Recommendations:")
        if not recommendations:
            print("  No major issues found based on the quality thresholds!")
        else:
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"  {i}. {rec}")
        print(f"\nFull report saved to: {report_file}")