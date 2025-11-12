# 2025-10-16-18-50-00
# cad_rms_integration/schema_mapper.py
# Author: R. A. Carucci
# Purpose: Maps raw data fields to canonical schema and applies transformations

import yaml
import pandas as pd
import re
import logging
from typing import Dict, List, Any, Union, Optional
from pathlib import Path
from datetime import datetime
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('schema_mapper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SchemaMapper:
    """Maps raw data fields to canonical schema using YAML definition."""
    
    def __init__(self, schema_path: Union[str, Path]):
        """
        Initialize schema mapper from YAML file.
        
        Args:
            schema_path: Path to schema registry YAML file
        """
        self.schema_path = Path(schema_path)
        self.schema = self._load_schema()
        self.fields = self.schema.get('fields', {})
        self.transformations = self.schema.get('transformations', {})
        self.version = self.schema.get('version', 'unknown')
        
        # Build alias lookup table (alias -> canonical field)
        self.alias_map = self._build_alias_map()
        
        logger.info(f"Loaded schema registry version {self.version} with {len(self.fields)} fields")
    
    def _load_schema(self) -> Dict:
        """Load schema from YAML file."""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        
        try:
            with open(self.schema_path, 'r') as f:
                schema = yaml.safe_load(f)
            return schema
        except Exception as e:
            raise ValueError(f"Failed to load schema: {str(e)}")
    
    def _build_alias_map(self) -> Dict[str, str]:
        """Build mapping from aliases to canonical field names."""
        alias_map = {}
        
        for field_name, field_def in self.fields.items():
            # Add the canonical name itself as an alias
            alias_map[field_name.lower()] = field_name
            
            # Add all defined aliases
            aliases = field_def.get('aliases', [])
            for alias in aliases:
                alias_map[alias.lower()] = field_name
        
        return alias_map
    
    def get_canonical_name(self, raw_field: str) -> Optional[str]:
        """
        Get canonical field name for a raw field name.
        
        Args:
            raw_field: Original field name from data source
            
        Returns:
            Canonical field name or None if no match
        """
        return self.alias_map.get(raw_field.lower())
    
    def map_dataframe(self, df: pd.DataFrame, source_system: str = 'UNKNOWN') -> pd.DataFrame:
        """
        Map dataframe columns to canonical schema.
        
        Args:
            df: Original dataframe
            source_system: Source system identifier (e.g., 'CAD', 'RMS')
            
        Returns:
            Dataframe with canonicalized column names
        """
        logger.info(f"Mapping {len(df)} records from {source_system}")
        
        # Track mapped and unmapped fields
        mapped_fields = []
        unmapped_fields = []
        
        # Create new dataframe with canonical column names
        mapped_df = pd.DataFrame()
        
        # Track mappings for logging
        mappings = {}
        
        # Process each column in the original dataframe
        for col in df.columns:
            canonical_name = self.get_canonical_name(col)
            
            if canonical_name:
                # Field has a canonical mapping
                mapped_df[canonical_name] = df[col]
                mapped_fields.append(col)
                mappings[col] = canonical_name
            else:
                # No mapping found - keep original name
                mapped_df[col] = df[col]
                unmapped_fields.append(col)
        
        # Add source system and processing metadata
        mapped_df['data_source'] = source_system
        mapped_df['processing_timestamp'] = datetime.now()
        mapped_df['pipeline_version'] = self.schema.get('version', 'unknown')
        
        # Log mapping results
        logger.info(f"Mapped {len(mapped_fields)} fields, {len(unmapped_fields)} fields unmapped")
        if unmapped_fields:
            logger.warning(f"Unmapped fields: {', '.join(unmapped_fields)}")
        
        # Apply transformations and validations
        mapped_df = self._apply_transformations(mapped_df)
        mapped_df = self._apply_validations(mapped_df)
        mapped_df = self._compute_derived_fields(mapped_df)
        
        return mapped_df
    
    def _apply_transformations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply defined transformations to fields."""
        for field_name, field_def in self.fields.items():
            if field_name not in df.columns:
                continue
            
            transforms = field_def.get('transformations', [])
            if not transforms:
                continue
            
            for transform_name in transforms:
                transform_def = self.transformations.get(transform_name)
                if not transform_def:
                    logger.warning(f"Transformation {transform_name} not defined")
                    continue
                
                logger.debug(f"Applying transformation {transform_name} to {field_name}")
                
                try:
                    df = self._apply_single_transformation(df, field_name, transform_name, transform_def)
                except Exception as e:
                    logger.error(f"Failed to apply transformation {transform_name} to {field_name}: {str(e)}")
        
        return df
    
    def _apply_single_transformation(
        self, df: pd.DataFrame, field_name: str, transform_name: str, transform_def: Dict
    ) -> pd.DataFrame:
        """Apply a single transformation to a field."""
        # Handle different transformation types
        if transform_name == 'standardize_abbreviations':
            mappings = transform_def.get('mappings', [])
            for mapping in mappings:
                source, target = mapping.split(' → ')
                df[field_name] = df[field_name].astype(str).str.replace(
                    f"\\b{source}\\b", target, regex=True, case=False
                )
        
        elif transform_name == 'add_city_state':
            default_city = transform_def.get('default_city', 'HACKENSACK')
            default_state = transform_def.get('default_state', 'NJ')
            
            # Add city and state if not present
            missing_city_state = ~(
                df[field_name].astype(str).str.contains(default_city, case=False) & 
                df[field_name].astype(str).str.contains(default_state, case=False)
            )
            df.loc[missing_city_state, field_name] = (
                df.loc[missing_city_state, field_name].astype(str) + 
                f", {default_city}, {default_state}"
            )
        
        elif transform_name == 'extract_block':
            regex = transform_def.get('regex', '^(\\d+)')
            target_field = transform_def.get('target_field', 'block_number')
            
            # Extract block number using regex
            df[target_field] = df[field_name].astype(str).str.extract(regex, expand=False)
        
        elif transform_name == 'standardize_officer_name':
            # This would implement badge number extraction and name formatting
            # Simplified version here
            df[field_name] = df[field_name].astype(str)
        
        return df
    
    def _apply_validations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply field validations based on schema."""
        for field_name, field_def in self.fields.items():
            if field_name not in df.columns:
                continue
            
            validation = field_def.get('validation', {})
            if not validation:
                continue
            
            # Apply different validation types
            if 'regex' in validation:
                pattern = validation['regex']
                mask = ~df[field_name].astype(str).str.match(pattern)
                invalid_count = mask.sum()
                
                if invalid_count > 0:
                    logger.warning(f"{invalid_count} records failed regex validation for {field_name}")
                
                # Try fallback regex if available
                if 'fallback_regex' in validation and invalid_count > 0:
                    fallback_pattern = validation['fallback_regex']
                    fallback_mask = df[field_name][mask].astype(str).str.match(fallback_pattern)
                    logger.info(f"{fallback_mask.sum()} records matched fallback regex for {field_name}")
            
            if 'min_length' in validation:
                min_length = validation['min_length']
                mask = df[field_name].astype(str).str.len() < min_length
                if mask.sum() > 0:
                    logger.warning(f"{mask.sum()} records failed min length validation for {field_name}")
            
            if 'max_length' in validation:
                max_length = validation['max_length']
                mask = df[field_name].astype(str).str.len() > max_length
                if mask.sum() > 0:
                    logger.warning(f"{mask.sum()} records failed max length validation for {field_name}")
        
        return df
    
    def _compute_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute derived fields based on schema definition."""
        for field_name, field_def in self.fields.items():
            if not field_def.get('computed', False):
                continue
            
            # Skip if field already exists
            if field_name in df.columns and not df[field_name].isna().all():
                continue
            
            logger.debug(f"Computing derived field {field_name}")
            
            try:
                # Implement different derived field calculations
                if field_name == 'address_type':
                    df[field_name] = self._derive_address_type(df)
                
                elif field_name == 'badge_number':
                    df[field_name] = self._extract_badge_number(df)
                
            except Exception as e:
                logger.error(f"Failed to compute derived field {field_name}: {str(e)}")
        
        return df
    
    def _derive_address_type(self, df: pd.DataFrame) -> pd.Series:
        """Derive address type from address field."""
        address_field = 'address'
        if address_field not in df.columns:
            return pd.Series(index=df.index)
        
        # Define pattern matchers for different address types
        intersection_pattern = r'\s+&\s+|\s+and\s+|\s+at\s+'
        landmark_pattern = r'\b(PARK|SCHOOL|LIBRARY|HOSPITAL|STATION|MALL|PLAZA)\b'
        
        # Apply rules
        result = pd.Series('UNKNOWN', index=df.index)
        
        # Check for intersection pattern
        mask = df[address_field].astype(str).str.contains(intersection_pattern, case=False, regex=True)
        result[mask] = 'INTERSECTION'
        
        # Check for landmark pattern
        mask = df[address_field].astype(str).str.contains(landmark_pattern, case=False, regex=True)
        result[mask] = 'LANDMARK'
        
        # Default to street address if has number
        has_number = df[address_field].astype(str).str.match(r'^\d+')
        mask = (result == 'UNKNOWN') & has_number
        result[mask] = 'STREET_ADDRESS'
        
        return result
    
    def _extract_badge_number(self, df: pd.DataFrame) -> pd.Series:
        """Extract badge number from officer field."""
        officer_field = 'officer'
        if officer_field not in df.columns:
            return pd.Series(index=df.index)
        
        # Extract badge number pattern (#1234 or similar)
        result = df[officer_field].astype(str).str.extract(r'#(\d{3,4})', expand=False)
        
        # Ensure 4-digit format
        mask = result.notna() & (result.str.len() == 3)
        result[mask] = '0' + result[mask]
        
        return result
    
    def calculate_data_quality_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate data quality score based on field completeness and validation."""
        if 'data_quality_score' in df.columns:
            logger.info("Quality score field already exists - skipping calculation")
            return df
        
        logger.info("Calculating data quality scores")
        
        # Initialize scores
        df['data_quality_score'] = 0
        
        # Track scoring components
        components = {}
        
        # Score required fields (20 points each, max 60)
        required_fields = [
            field for field, field_def in self.fields.items() 
            if field_def.get('required', False) and not field_def.get('computed', False)
        ]
        
        required_weight = min(60, len(required_fields) * 20) / (len(required_fields) or 1)
        
        for field in required_fields:
            if field in df.columns:
                not_null = df[field].notna() & (df[field].astype(str) != '')
                df.loc[not_null, 'data_quality_score'] += required_weight
                components[f"required_{field}"] = not_null.mean() * 100
        
        # Score temporal fields (max 15 points)
        temporal_fields = [
            field for field, field_def in self.fields.items() 
            if field_def.get('group', '') == 'temporal'
        ]
        
        if temporal_fields:
            temporal_weight = 15 / len(temporal_fields)
            
            for field in temporal_fields:
                if field in df.columns:
                    not_null = df[field].notna()
                    df.loc[not_null, 'data_quality_score'] += temporal_weight
                    components[f"temporal_{field}"] = not_null.mean() * 100
        
        # Score spatial fields (max 15 points)
        spatial_fields = [
            field for field, field_def in self.fields.items() 
            if field_def.get('group', '') == 'spatial'
        ]
        
        if spatial_fields:
            spatial_weight = 15 / len(spatial_fields)
            
            for field in spatial_fields:
                if field in df.columns:
                    not_null = df[field].notna() & (df[field].astype(str) != '')
                    df.loc[not_null, 'data_quality_score'] += spatial_weight
                    components[f"spatial_{field}"] = not_null.mean() * 100
        
        # Score integration matches (10 points)
        if 'integration_type' in df.columns:
            matched = df['integration_type'] == 'CAD_RMS_MATCHED'
            df.loc[matched, 'data_quality_score'] += 10
            components["integration_match"] = matched.mean() * 100
        
        # Log quality score distribution
        quality_bins = [0, 60, 80, 100]
        quality_labels = ['Low', 'Medium', 'High']
        quality_counts = pd.cut(df['data_quality_score'], bins=quality_bins, labels=quality_labels).value_counts()
        
        logger.info("Data quality distribution:")
        for label, count in quality_counts.items():
            percentage = count / len(df) * 100
            logger.info(f"  {label}: {count} records ({percentage:.1f}%)")
        
        logger.info(f"Average quality score: {df['data_quality_score'].mean():.1f}")
        
        # Round scores to nearest integer
        df['data_quality_score'] = np.round(df['data_quality_score']).astype(int)
        
        return df

# Example usage
if __name__ == "__main__":
    # Example script to test the schema mapper
    mapper = SchemaMapper("schema_registry.yaml")
    
    # Example with sample data
    sample_data = {
        "Case Number": ["24-123456", "24-123457", "24-123458"],
        "Incident Date": ["2025-07-15", "2025-07-15", "2025-07-16"],
        "FullAddress2": ["123 MAIN ST", "456 ELM AVE & OAK ST", "789 HACKENSACK AVE"],
        "Time of Call": ["14:30:00", "15:45:00", "16:20:00"],
        "Incident": ["SUSPICIOUS PERSON", "MOTOR VEHICLE ACCIDENT", "THEFT"],
        "Officer": ["PO SMITH #1234", "SGT JONES #0567", ""],
        "PDZone": ["Z1", "Z2", "Z1"],
        "Disposition": ["COMPLETE", "REPORT TAKEN", "UNFOUNDED"]
    }
    
    sample_df = pd.DataFrame(sample_data)
    
    # Map to canonical schema
    canonical_df = mapper.map_dataframe(sample_df, source_system="CAD")
    
    # Calculate quality scores
    scored_df = mapper.calculate_data_quality_score(canonical_df)
    
    # Print results
    print("Original columns:", sample_df.columns.tolist())
    print("Canonical columns:", canonical_df.columns.tolist())
    print("Quality scores:", scored_df["data_quality_score"].tolist())
    
    print("\nExample record after mapping:")
    print(scored_df.iloc[0].to_dict())
