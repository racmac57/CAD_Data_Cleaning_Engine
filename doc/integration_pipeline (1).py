# 2025-10-16-18-55-00
# cad_rms_integration/integration_pipeline.py
# Author: R. A. Carucci
# Purpose: Modular CAD/RMS integration pipeline with flexible stages and configuration

import pandas as pd
import numpy as np
import logging
import json
import yaml
import gc
from pathlib import Path
from datetime import datetime, timedelta
import time
from typing import Dict, List, Tuple, Optional, Set, Any, Union
import re

# Import custom modules
# Uncomment after implementing these modules
# from schema_mapper import SchemaMapper
# from data_quality import QualityScorer
# from address_normalizer import AddressNormalizer
# from officer_mapper import OfficerMapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integration_pipeline.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntegrationPipeline:
    """
    Modular CAD/RMS data integration pipeline with configurable stages.
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the pipeline with configuration.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.schema_registry_path = Path(self.config.get('schema_registry', 'schema_registry.yaml'))
        
        # Set up paths
        self.base_path = Path(self.config.get('base_path', '.'))
        self.exports_path = self.base_path / self.config.get('exports_directory', '05_EXPORTS')
        self.output_path = self.base_path / self.config.get('output_directory', 'output')
        self.reports_path = self.base_path / self.config.get('reports_directory', 'reports')
        
        # Ensure output directories exist
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.reports_path.mkdir(parents=True, exist_ok=True)
        
        # Integration statistics
        self.stats = {
            'cad_records_loaded': 0,
            'rms_records_loaded': 0,
            'successful_matches': 0,
            'failed_matches': 0,
            'cad_only_records': 0,
            'rms_only_records': 0,
            'quality_fixes_applied': 0,
            'processing_errors': 0,
            'elapsed_time': 0,
        }
        
        # Load schema registry
        # Replace with actual schema mapper once implemented
        # self.schema_mapper = SchemaMapper(self.schema_registry_path)
        
        logger.info(f"Initialized integration pipeline with config: {self.config_path}")
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {str(e)}")
    
    def load_cad_data(self) -> pd.DataFrame:
        """Load and preprocess CAD data from configured sources."""
        logger.info("Loading CAD data...")
        
        cad_files = []
        for pattern in self.config.get('cad_file_patterns', ['*_CAD*.xlsx']):
            cad_files.extend(list(self.exports_path.glob(pattern)))
        
        logger.info(f"Found {len(cad_files)} CAD files: {[f.name for f in cad_files]}")
        
        exclude_patterns = self.config.get('exclude_patterns', ['*CORRUPTED*', '*OLD*'])
        for pattern in exclude_patterns:
            cad_files = [f for f in cad_files if not f.match(pattern)]
        
        logger.info(f"After exclusions: {len(cad_files)} CAD files")
        
        combined_cad = []
        
        for file_path in sorted(cad_files):
            try:
                logger.info(f"Processing {file_path.name}...")
                
                # Use chunking for large files
                chunk_size = self.config.get('chunk_size', 10000)
                if 'chunkable_files' in self.config and any(file_path.match(pattern) for pattern in self.config['chunkable_files']):
                    # Process in chunks
                    chunks = []
                    for chunk_idx, chunk in enumerate(pd.read_excel(file_path, engine='openpyxl', chunksize=chunk_size)):
                        logger.info(f"Processing chunk {chunk_idx+1} with {len(chunk)} rows")
                        processed_chunk = self._preprocess_cad_chunk(chunk, file_path.name)
                        chunks.append(processed_chunk)
                        
                        # Force garbage collection
                        del processed_chunk
                        gc.collect()
                    
                    file_df = pd.concat(chunks, ignore_index=True)
                else:
                    # Process entire file at once
                    df = pd.read_excel(file_path, engine='openpyxl')
                    file_df = self._preprocess_cad_chunk(df, file_path.name)
                
                combined_cad.append(file_df)
                logger.info(f"Loaded {len(file_df):,} CAD records from {file_path.name}")
                
                # Force garbage collection
                del file_df
                gc.collect()
                
            except Exception as e:
                logger.error(f"Error processing CAD file {file_path.name}: {str(e)}")
                self.stats['processing_errors'] += 1
        
        if combined_cad:
            cad_data = pd.concat(combined_cad, ignore_index=True)
            self.stats['cad_records_loaded'] = len(cad_data)
            logger.info(f"Total CAD records: {len(cad_data):,}")
            return cad_data
        else:
            logger.error("No CAD data could be loaded!")
            return pd.DataFrame()
    
    def _preprocess_cad_chunk(self, df: pd.DataFrame, source_file: str) -> pd.DataFrame:
        """Preprocess CAD data chunk with basic cleaning and standardization."""
        # Add source tracking
        df['Data_Source'] = 'CAD'
        df['Source_File'] = source_file
        df['Load_Timestamp'] = datetime.now()
        
        # Extract case number using regex
        if 'ReportNumberNew' in df.columns:
            # Use configured regex pattern
            case_pattern = self.config.get('case_number_regex', r'(\d{2}-\d{6})')
            df['Case_Number'] = df['ReportNumberNew'].astype(str).str.extract(case_pattern, expand=False)
        
        # Fix 'BACKUP' call addresses
        if 'FullAddress2' in df.columns and 'Incident' in df.columns:
            backup_pattern = self.config.get('backup_pattern', r'BACKUP|Assist Own Agency')
            backup_mask = df['Incident'].str.contains(backup_pattern, case=False, na=False)
            missing_address_mask = df['FullAddress2'].isna() | (df['FullAddress2'] == '')
            
            fix_mask = backup_mask & missing_address_mask
            if fix_mask.any():
                df.loc[fix_mask, 'FullAddress2'] = 'Location Per CAD System'
                self.stats['quality_fixes_applied'] += fix_mask.sum()
                logger.info(f"Fixed {fix_mask.sum()} backup addresses")
        
        # Convert time fields to datetime
        time_fields = ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In']
        for field in time_fields:
            if field in df.columns:
                df[field] = pd.to_datetime(df[field], errors='coerce')
        
        # Calculate response times
        if all(field in df.columns for field in ['Time of Call', 'Time Dispatched']):
            df['Response_Time_Seconds'] = (
                df['Time Dispatched'] - df['Time of Call']
            ).dt.total_seconds()
        
        if all(field in df.columns for field in ['Time Dispatched', 'Time Out']):
            df['Travel_Time_Seconds'] = (
                df['Time Out'] - df['Time Dispatched']
            ).dt.total_seconds()
        
        # Use memory-efficient data types
        df = self._optimize_dtypes(df)
        
        return df
    
    def load_rms_data(self) -> pd.DataFrame:
        """Load and preprocess RMS data from configured sources."""
        logger.info("Loading RMS data...")
        
        rms_files = []
        for pattern in self.config.get('rms_file_patterns', ['*_RMS*.xlsx']):
            rms_files.extend(list(self.exports_path.glob(pattern)))
        
        logger.info(f"Found {len(rms_files)} RMS files: {[f.name for f in rms_files]}")
        
        exclude_patterns = self.config.get('exclude_patterns', ['*CORRUPTED*', '*OLD*'])
        for pattern in exclude_patterns:
            rms_files = [f for f in rms_files if not f.match(pattern)]
        
        logger.info(f"After exclusions: {len(rms_files)} RMS files")
        
        combined_rms = []
        
        for file_path in sorted(rms_files):
            try:
                logger.info(f"Processing {file_path.name}...")
                
                # Use chunking for large files
                chunk_size = self.config.get('chunk_size', 10000)
                if 'chunkable_files' in self.config and any(file_path.match(pattern) for pattern in self.config['chunkable_files']):
                    # Process in chunks
                    chunks = []
                    for chunk_idx, chunk in enumerate(pd.read_excel(file_path, engine='openpyxl', chunksize=chunk_size)):
                        logger.info(f"Processing chunk {chunk_idx+1} with {len(chunk)} rows")
                        processed_chunk = self._preprocess_rms_chunk(chunk, file_path.name)
                        chunks.append(processed_chunk)
                        
                        # Force garbage collection
                        del processed_chunk
                        gc.collect()
                    
                    file_df = pd.concat(chunks, ignore_index=True)
                else:
                    # Process entire file at once
                    df = pd.read_excel(file_path, engine='openpyxl')
                    file_df = self._preprocess_rms_chunk(df, file_path.name)
                
                combined_rms.append(file_df)
                logger.info(f"Loaded {len(file_df):,} RMS records from {file_path.name}")
                
                # Force garbage collection
                del file_df
                gc.collect()
                
            except Exception as e:
                logger.error(f"Error processing RMS file {file_path.name}: {str(e)}")
                self.stats['processing_errors'] += 1
        
        if combined_rms:
            rms_data = pd.concat(combined_rms, ignore_index=True)
            self.stats['rms_records_loaded'] = len(rms_data)
            logger.info(f"Total RMS records: {len(rms_data):,}")
            return rms_data
        else:
            logger.warning("No RMS data could be loaded - proceeding with CAD-only pipeline")
            return pd.DataFrame()
    
    def _preprocess_rms_chunk(self, df: pd.DataFrame, source_file: str) -> pd.DataFrame:
        """Preprocess RMS data chunk with basic cleaning and standardization."""
        # Add source tracking
        df['Data_Source'] = 'RMS'
        df['Source_File'] = source_file
        df['Load_Timestamp'] = datetime.now()
        
        # Find and extract case number
        case_columns = ['CaseNumber', 'Case Number', 'Report Number', 'ReportNumber']
        case_column = next((col for col in case_columns if col in df.columns), None)
        
        if case_column:
            # Use configured regex pattern
            case_pattern = self.config.get('case_number_regex', r'(\d{2}-\d{6})')
            df['Case_Number'] = df[case_column].astype(str).str.extract(case_pattern, expand=False)
            
            # Identify supplements
            supplement_pattern = self.config.get('supplement_pattern', r'[A-Z]$|S\d+$')
            df['Is_Supplement'] = df[case_column].astype(str).str.contains(supplement_pattern, na=False)
            
            # Store original case number for reference
            df['Original_Case_Number'] = df[case_column]
        
        # Convert date fields to datetime
        date_columns = ['ReportDate', 'Report Date', 'IncidentDate', 'Incident Date']
        for column in date_columns:
            if column in df.columns:
                df[column] = pd.to_datetime(df[column], errors='coerce')
        
        # Fix time field issues - convert "1" to proper time
        time_columns = [col for col in df.columns if 'time' in col.lower() or 'hour' in col.lower()]
        for column in time_columns:
            if column in df.columns and df[column].dtype == 'object':
                # Check for improper time values
                improper_time = df[column].astype(str).str.match(r'^\d{1,2}$')
                if improper_time.any():
                    # Convert single digits to proper time format
                    df.loc[improper_time, column] = df.loc[improper_time, column].astype(str) + ':00:00'
                    self.stats['quality_fixes_applied'] += improper_time.sum()
                    logger.info(f"Fixed {improper_time.sum()} improper time values in {column}")
                
                # Convert to datetime
                df[column] = pd.to_datetime(df[column], errors='coerce')
        
        # Use memory-efficient data types
        df = self._optimize_dtypes(df)
        
        return df
    
    def integrate_data(self, cad_data: pd.DataFrame, rms_data: pd.DataFrame) -> pd.DataFrame:
        """Integrate CAD and RMS data using advanced matching strategies."""
        logger.info("Integrating CAD and RMS data...")
        
        if rms_data.empty:
            logger.warning("No RMS data available - continuing with CAD-only dataset")
            # Add integration tracking fields to CAD data
            cad_data['Integration_Type'] = 'CAD_ONLY'
            cad_data['Match_Confidence'] = 'NONE'
            cad_data['RMS_Data_Available'] = False
            
            self.stats['cad_only_records'] = len(cad_data)
            return cad_data
        
        # Strategy 1: Direct case number matching
        logger.info("Performing direct case number matching...")
        
        # Ensure case number column exists in both dataframes
        if 'Case_Number' not in cad_data.columns:
            logger.error("Case_Number field missing in CAD data")
            self.stats['processing_errors'] += 1
            cad_data['Case_Number'] = ''
        
        if 'Case_Number' not in rms_data.columns:
            logger.error("Case_Number field missing in RMS data")
            self.stats['processing_errors'] += 1
            rms_data['Case_Number'] = ''
        
        # Filter out invalid case numbers
        valid_cad = cad_data['Case_Number'].notna() & (cad_data['Case_Number'] != '')
        valid_rms = rms_data['Case_Number'].notna() & (rms_data['Case_Number'] != '')
        
        logger.info(f"Valid case numbers: {valid_cad.sum():,} in CAD, {valid_rms.sum():,} in RMS")
        
        # Filter RMS supplements if configured
        if self.config.get('exclude_supplements', True) and 'Is_Supplement' in rms_data.columns:
            non_supplement = ~rms_data['Is_Supplement']
            logger.info(f"Filtering {(~non_supplement).sum():,} supplement cases from RMS")
            rms_match_data = rms_data[valid_rms & non_supplement].copy()
        else:
            rms_match_data = rms_data[valid_rms].copy()
        
        # Create RMS lookup dictionary for faster matching
        rms_lookup = {}
        
        logger.info(f"Creating RMS lookup from {len(rms_match_data):,} records...")
        
        # Identify key RMS fields to include in lookup
        rms_keys = ['Case_Number']
        
        # Add disposition field if available
        disposition_fields = ['Disposition', 'Status', 'CaseStatus']
        disposition_field = next((f for f in disposition_fields if f in rms_match_data.columns), None)
        if disposition_field:
            rms_keys.append(disposition_field)
        
        # Add officer field if available
        officer_fields = ['Officer', 'Officer Name', 'Reporting Officer']
        officer_field = next((f for f in officer_fields if f in rms_match_data.columns), None)
        if officer_field:
            rms_keys.append(officer_field)
        
        # Build lookup dictionary
        for _, row in rms_match_data[rms_keys].iterrows():
            case_num = row['Case_Number']
            if pd.notna(case_num) and case_num != '':
                # Store key fields in dictionary
                rms_lookup[case_num] = {
                    field: row[field] for field in rms_keys if field in row.index
                }
        
        logger.info(f"RMS lookup created with {len(rms_lookup):,} unique case numbers")
        
        # Initialize integration fields
        cad_data['Integration_Type'] = 'CAD_ONLY'
        cad_data['Match_Confidence'] = 'NONE'
        cad_data['RMS_Data_Available'] = False
        
        if disposition_field:
            cad_data['RMS_Disposition'] = ''
        
        if officer_field:
            cad_data['RMS_Officer'] = ''
        
        # Perform matching
        logger.info("Performing case number matching...")
        
        matched_count = 0
        batch_size = self.config.get('processing_batch_size', 5000)
        total_batches = (len(cad_data) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(cad_data))
            
            if batch_idx % 10 == 0 or batch_idx == total_batches - 1:
                logger.info(f"Processing batch {batch_idx + 1}/{total_batches}")
            
            batch_matches = 0
            
            for idx in range(start_idx, end_idx):
                case_num = cad_data.at[idx, 'Case_Number']
                
                if pd.notna(case_num) and case_num != '' and case_num in rms_lookup:
                    # Match found!
                    rms_record = rms_lookup[case_num]
                    
                    # Update integration fields
                    cad_data.at[idx, 'Integration_Type'] = 'CAD_RMS_MATCHED'
                    cad_data.at[idx, 'Match_Confidence'] = 'HIGH'
                    cad_data.at[idx, 'RMS_Data_Available'] = True
                    
                    # Copy relevant RMS fields
                    if disposition_field and disposition_field in rms_record:
                        cad_data.at[idx, 'RMS_Disposition'] = rms_record[disposition_field]
                    
                    if officer_field and officer_field in rms_record:
                        cad_data.at[idx, 'RMS_Officer'] = rms_record[officer_field]
                    
                    batch_matches += 1
            
            matched_count += batch_matches
        
        # Update statistics
        self.stats['successful_matches'] = matched_count
        self.stats['failed_matches'] = len(cad_data) - matched_count
        self.stats['cad_only_records'] = len(cad_data) - matched_count
        
        logger.info(f"Matching complete:")
        logger.info(f"  - Total CAD records: {len(cad_data):,}")
        logger.info(f"  - Matched records: {matched_count:,} ({matched_count / len(cad_data) * 100:.1f}%)")
        logger.info(f"  - CAD-only records: {len(cad_data) - matched_count:,}")
        
        return cad_data
    
    def calculate_quality_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate data quality scores based on field completeness."""
        logger.info("Calculating data quality scores...")
        
        # Initialize quality score
        df['Data_Quality_Score'] = 0
        
        # Score components (total 100 points possible)
        
        # Case number present (20 points)
        has_case = df['Case_Number'].notna() & (df['Case_Number'] != '')
        df.loc[has_case, 'Data_Quality_Score'] += 20
        
        # Address present (20 points)
        if 'FullAddress2' in df.columns:
            has_address = df['FullAddress2'].notna() & (df['FullAddress2'] != '')
            df.loc[has_address, 'Data_Quality_Score'] += 20
        
        # Time data present (20 points total)
        if 'Time of Call' in df.columns:
            has_call_time = df['Time of Call'].notna()
            df.loc[has_call_time, 'Data_Quality_Score'] += 10
        
        if 'Time Dispatched' in df.columns:
            has_dispatch_time = df['Time Dispatched'].notna()
            df.loc[has_dispatch_time, 'Data_Quality_Score'] += 10
        
        # Integration success (25 points)
        is_matched = df['Integration_Type'] == 'CAD_RMS_MATCHED'
        df.loc[is_matched, 'Data_Quality_Score'] += 25
        
        # Officer data (15 points)
        if 'Officer' in df.columns:
            has_officer = df['Officer'].notna() & (df['Officer'] != '')
            df.loc[has_officer, 'Data_Quality_Score'] += 15
        
        # Log quality distribution
        quality_bins = [0, 60, 80, 101]  # Upper bound is exclusive
        quality_labels = ['Low', 'Medium', 'High']
        
        quality_dist = pd.cut(df['Data_Quality_Score'], bins=quality_bins, labels=quality_labels)
        quality_counts = quality_dist.value_counts()
        
        logger.info("Data quality distribution:")
        for label in ['High', 'Medium', 'Low']:
            if label in quality_counts:
                count = quality_counts[label]
                percentage = count / len(df) * 100
                logger.info(f"  {label}: {count:,} records ({percentage:.1f}%)")
        
        logger.info(f"Average quality score: {df['Data_Quality_Score'].mean():.1f}/100")
        
        return df
    
    def _optimize_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize data types for memory efficiency."""
        for col in df.columns:
            if df[col].dtype == 'object':
                # Convert to category if low cardinality
                nunique = df[col].nunique()
                if nunique > 0 and nunique / len(df) < 0.5:
                    df[col] = df[col].astype('category')
            elif df[col].dtype == 'float64':
                # Downcast floats
                df[col] = pd.to_numeric(df[col], downcast='float')
            elif df[col].dtype == 'int64':
                # Downcast integers
                df[col] = pd.to_numeric(df[col], downcast='integer')
        
        return df
    
    def save_results(self, df: pd.DataFrame) -> Dict[str, Path]:
        """Save results in multiple formats."""
        logger.info("Saving integration results...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Define output files
        output_files = {
            'csv': self.output_path / f"integrated_cad_rms_{timestamp}.csv",
            'excel': self.output_path / f"integrated_cad_rms_{timestamp}.xlsx",
            'powerbi': self.output_path / f"powerbi_ready_{timestamp}.csv"
        }
        
        # Save full dataset
        df.to_csv(output_files['csv'], index=False)
        
        # Save Excel with limited columns to avoid size issues
        max_excel_cols = self.config.get('max_excel_columns', 50)
        if len(df.columns) > max_excel_cols:
            logger.warning(f"Limiting Excel output to {max_excel_cols} columns (from {len(df.columns)})")
            priority_columns = self.config.get('priority_columns', [
                'Case_Number', 'Integration_Type', 'Data_Quality_Score',
                'Time of Call', 'Time Dispatched', 'FullAddress2', 'Incident', 'Officer'
            ])
            
            # Ensure priority columns are included
            excel_columns = [
                col for col in priority_columns if col in df.columns
            ]
            
            # Add remaining columns up to the limit
            remaining_columns = [
                col for col in df.columns if col not in excel_columns
            ][:max_excel_cols - len(excel_columns)]
            
            excel_columns.extend(remaining_columns)
            df[excel_columns].to_excel(output_files['excel'], index=False)
        else:
            df.to_excel(output_files['excel'], index=False)
        
        # Create PowerBI-optimized version
        powerbi_columns = self.config.get('powerbi_columns', [
            'Case_Number', 'Incident', 'Time of Call', 'Time Dispatched',
            'Time Out', 'Time In', 'FullAddress2', 'PDZone', 'Grid',
            'Officer', 'Integration_Type', 'Data_Quality_Score',
            'RMS_Disposition', 'Data_Source', 'Source_File'
        ])
        
        # Only include columns that exist
        available_powerbi_cols = [col for col in powerbi_columns if col in df.columns]
        
        # Create clean PowerBI dataset
        powerbi_df = df[available_powerbi_cols].copy()
        
        # Convert all object columns to strings with empty string for nulls
        for col in powerbi_df.columns:
            if powerbi_df[col].dtype == 'object' or powerbi_df[col].dtype.name == 'category':
                powerbi_df[col] = powerbi_df[col].fillna('').astype(str)
        
        # Save PowerBI-ready CSV
        powerbi_df.to_csv(output_files['powerbi'], index=False)
        
        # Log file sizes
        for name, path in output_files.items():
            size_mb = path.stat().st_size / (1024 * 1024)
            logger.info(f"  - {name.upper()}: {path.name} ({size_mb:.1f} MB)")
        
        return output_files
    
    def generate_report(self, df: pd.DataFrame) -> Dict:
        """Generate comprehensive integration report."""
        logger.info("Generating integration report...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Calculate detailed statistics
        total_records = len(df)
        match_rate = 0
        if 'Integration_Type' in df.columns:
            matches = (df['Integration_Type'] == 'CAD_RMS_MATCHED').sum()
            match_rate = matches / total_records if total_records > 0 else 0
        
        quality_stats = {}
        if 'Data_Quality_Score' in df.columns:
            quality_stats = {
                'average_quality_score': float(df['Data_Quality_Score'].mean()),
                'median_quality_score': float(df['Data_Quality_Score'].median()),
                'high_quality_count': int((df['Data_Quality_Score'] >= 80).sum()),
                'medium_quality_count': int(((df['Data_Quality_Score'] >= 60) & 
                                           (df['Data_Quality_Score'] < 80)).sum()),
                'low_quality_count': int((df['Data_Quality_Score'] < 60).sum())
            }
        
        # Create comprehensive report
        report = {
            'report_metadata': {
                'timestamp': timestamp,
                'pipeline_version': self.config.get('pipeline_version', '1.0.0'),
                'schema_version': self.config.get('schema_version', 'unknown')
            },
            'execution_statistics': {
                'start_time': self.stats.get('start_time', ''),
                'end_time': self.stats.get('end_time', ''),
                'elapsed_seconds': self.stats.get('elapsed_time', 0),
                'cad_files_processed': len(self.config.get('cad_file_patterns', [])),
                'rms_files_processed': len(self.config.get('rms_file_patterns', []))
            },
            'integration_statistics': {
                'cad_records_processed': self.stats.get('cad_records_loaded', 0),
                'rms_records_processed': self.stats.get('rms_records_loaded', 0),
                'matched_records': self.stats.get('successful_matches', 0),
                'cad_only_records': self.stats.get('cad_only_records', 0),
                'match_rate_percentage': round(match_rate * 100, 2),
                'processing_errors': self.stats.get('processing_errors', 0)
            },
            'data_quality_statistics': quality_stats,
            'field_completeness': self._calculate_field_completeness(df),
            'recommendations': self._generate_recommendations(df)
        }
        
        # Save report
        report_file = self.reports_path / f"integration_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Integration report saved: {report_file}")
        return report
    
    def _calculate_field_completeness(self, df: pd.DataFrame) -> Dict:
        """Calculate field completeness statistics."""
        completeness = {}
        
        key_fields = self.config.get('key_fields', [
            'Case_Number', 'FullAddress2', 'Time of Call', 'Incident', 'Officer'
        ])
        
        for field in key_fields:
            if field in df.columns:
                if df[field].dtype == 'datetime64[ns]':
                    not_null = df[field].notna()
                else:
                    not_null = df[field].notna() & (df[field].astype(str) != '')
                
                completeness[field] = {
                    'count': int(not_null.sum()),
                    'percentage': float(not_null.mean() * 100),
                    'null_count': int((~not_null).sum())
                }
        
        return completeness
    
    def _generate_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Generate recommendations based on data analysis."""
        recommendations = []
        
        # Check match rate
        match_rate = 0
        if 'Integration_Type' in df.columns:
            match_rate = (df['Integration_Type'] == 'CAD_RMS_MATCHED').mean()
        
        if match_rate < 0.7:
            recommendations.append(
                f"Low match rate ({match_rate:.1%}) detected. Consider reviewing case number formats "
                f"and improving extraction patterns."
            )
        
        # Check quality distribution
        if 'Data_Quality_Score' in df.columns:
            low_quality = (df['Data_Quality_Score'] < 60).mean()
            if low_quality > 0.3:
                recommendations.append(
                    f"High proportion of low-quality records ({low_quality:.1%}). "
                    f"Focus on improving address standardization and officer mapping."
                )
        
        # Check for missing fields
        key_fields = self.config.get('key_fields', [
            'Case_Number', 'FullAddress2', 'Time of Call', 'Incident', 'Officer'
        ])
        
        missing_fields = [field for field in key_fields if field not in df.columns]
        if missing_fields:
            recommendations.append(
                f"Critical fields missing: {', '.join(missing_fields)}. "
                f"Review export configuration and field mapping."
            )
        
        # Add standard recommendations
        if self.stats['processing_errors'] > 0:
            recommendations.append(
                f"Processing errors detected ({self.stats['processing_errors']}). "
                f"Review log for details and address issues."
            )
        
        # Return recommendations or default message
        return recommendations or ["No specific recommendations - integration pipeline running smoothly."]
    
    def run_pipeline(self) -> Dict:
        """Run the complete integration pipeline."""
        logger.info("="*60)
        logger.info("STARTING CAD/RMS INTEGRATION PIPELINE")
        logger.info("="*60)
        
        start_time = time.time()
        self.stats['start_time'] = datetime.now().isoformat()
        
        try:
            # Step 1: Load CAD data
            logger.info("STEP 1: Loading CAD data...")
            cad_data = self.load_cad_data()
            if cad_data.empty:
                raise ValueError("Failed to load any CAD data!")
            
            # Step 2: Load RMS data (optional)
            logger.info("STEP 2: Loading RMS data...")
            rms_data = self.load_rms_data()
            
            # Step 3: Integrate data
            logger.info("STEP 3: Integrating CAD and RMS data...")
            integrated_data = self.integrate_data(cad_data, rms_data)
            
            # Free memory
            del cad_data
            del rms_data
            gc.collect()
            
            # Step 4: Calculate quality scores
            logger.info("STEP 4: Calculating quality scores...")
            scored_data = self.calculate_quality_scores(integrated_data)
            
            # Step 5: Save results
            logger.info("STEP 5: Saving results...")
            output_files = self.save_results(scored_data)
            
            # Step 6: Generate report
            logger.info("STEP 6: Generating report...")
            report = self.generate_report(scored_data)
            
            # Calculate elapsed time
            end_time = time.time()
            elapsed_seconds = end_time - start_time
            self.stats['end_time'] = datetime.now().isoformat()
            self.stats['elapsed_time'] = elapsed_seconds
            
            logger.info("="*60)
            logger.info("INTEGRATION PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("="*60)
            logger.info(f"Total processing time: {elapsed_seconds:.1f} seconds")
            logger.info(f"Records processed: {len(scored_data):,}")
            
            return {
                'success': True,
                'record_count': len(scored_data),
                'output_files': output_files,
                'report': report,
                'stats': self.stats
            }
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
            
            # Calculate elapsed time even on failure
            end_time = time.time()
            elapsed_seconds = end_time - start_time
            self.stats['end_time'] = datetime.now().isoformat()
            self.stats['elapsed_time'] = elapsed_seconds
            
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }

if __name__ == "__main__":
    # Example configuration path
    config_path = "config.yaml"
    
    # Create pipeline
    try:
        pipeline = IntegrationPipeline(config_path)
        results = pipeline.run_pipeline()
        
        if results['success']:
            print("\n" + "="*50)
            print("CAD/RMS INTEGRATION COMPLETED SUCCESSFULLY")
            print("="*50)
            print(f"Records processed: {results['record_count']:,}")
            print(f"Match rate: {results['report']['integration_statistics']['match_rate_percentage']}%")
            print(f"Processing time: {results['stats']['elapsed_time']:.1f} seconds")
            
            print("\nOutput files:")
            for name, path in results['output_files'].items():
                print(f"  - {name.upper()}: {path}")
            
            if results['report']['recommendations']:
                print("\nRecommendations:")
                for i, rec in enumerate(results['report']['recommendations'], 1):
                    print(f"  {i}. {rec}")
        else:
            print("\n" + "="*50)
            print("CAD/RMS INTEGRATION FAILED")
            print("="*50)
            print(f"Error: {results['error']}")
            print(f"Processing time: {results['stats']['elapsed_time']:.1f} seconds")
    
    except Exception as e:
        print(f"Failed to initialize pipeline: {str(e)}")
