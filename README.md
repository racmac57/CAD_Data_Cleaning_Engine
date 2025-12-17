# **Complete CAD Data Cleaning & Enrichment Code**

Here's the comprehensive code for CAD data processing that you can provide to an AI assistant.

## Recent Updates (2025-12-17)

- **High-Performance Validation Engine**:
  - **26.7x speed improvement**: New parallelized/vectorized validation script (`validate_cad_export_parallel.py`)
  - Processing time reduced from 5 minutes 20 seconds to just **12 seconds** for 702,352 records
  - Performance: **58,529 rows/second** (up from 2,195 rows/second)
  - Uses vectorized pandas operations instead of slow row-by-row iteration
  - Multi-core ready (configurable CPU utilization)
  - Identical validation logic and error detection as original
  - Memory-efficient columnar operations
  - Detailed performance analysis in `PERFORMANCE_COMPARISON.md`

- **Validation Improvements**:
  - Better bulk error tracking (26,997 unique affected rows vs 657,078 in original)
  - More accurate error rate calculation (3.84% vs 93.55%)
  - Same comprehensive validation rules applied
  - Optimized for iterative development and production pipelines

## Recent Updates (2025-12-15)

- **CAD + RMS Data Dictionary (JSON, v2)**:
  - Added repo-backed schema and mapping artifacts to standardize names, coercions, defaults, and cross-system joins:
    - CAD: `cad_field_map.json`, `cad_fields_schema.json`
    - RMS: `rms_field_map.json`, `rms_fields_schema.json`
  - Added explicit **reverse maps** for ETL merge/backfill rules:
    - `cad_to_rms_field_map.json` (CAD drives merge; enrich with RMS)
    - `rms_to_cad_field_map.json` (RMS patches CAD)
  - **Naming conventions**:
    - `source_field_name`: raw export header (exact spelling/spaces)
    - `internal_field_name`: safe Python key (no spaces)
  - **ETL standards location (OneDrive)**:
    - `C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\Standards\CAD\DataDictionary\current\schema\`
  - **Key join + backfill rules** (codified in JSON maps):
    - Join: `cad.ReportNumberNew` ↔ `rms.CaseNumber` (RMS “Case Number”)
    - Incident backfill order: `IncidentType1` → `IncidentType2` → `IncidentType3`
    - Address backfill only when CAD address is blank/invalid

## Recent Updates (2025-11-25)

- **ESRI File Rebuild & Duplicate Fix**: 
  - Identified and fixed severe duplicate corruption in ESRI export (955,759 records with 81,920 duplicates for single case)
  - Rebuilt complete ESRI file preserving ALL legitimate records: `CAD_ESRI_Final_20251124_COMPLETE.xlsx`
  - Final file: 702,352 records (only 84 completely identical duplicates removed)
  - All 542,565 unique cases preserved
  - Address corrections applied: 86,932 records corrected from cleaned version

- **Address Quality Improvements**:
  - **85.3% reduction in invalid addresses** (from 18.4% to 2.7% invalid)
  - Raw data: 18.4% invalid addresses
  - Cleaned data: 97.3% valid addresses (929,703 records)
  - RMS backfill: 1,447 addresses corrected from RMS data
  - Rule-based corrections: 119 conditional rules applied
  - Manual corrections: 408 manual corrections applied

- **Data Quality Validation**:
  - Comprehensive quality check script: `scripts/comprehensive_quality_check.py`
  - Corrected previous quality report (was showing incorrect 0.9% improvement)
  - Actual improvement: 15.7 percentage points (85.3% reduction)
  - Field coverage: 99.98% Incident, 99.96% Response_Type, 100% Disposition

- **New Scripts**:
  - `scripts/rebuild_esri_with_all_records.py`: Rebuilds ESRI file preserving all legitimate records
  - `scripts/fix_esri_duplicates.py`: Fixes duplicate corruption (deduplicates properly)
  - `scripts/apply_all_address_corrections.py`: Applies both conditional rules and manual corrections
  - `scripts/generate_final_manual_address_corrections.py`: Generates CSV for manual address corrections with RMS backfill
  - `scripts/comprehensive_quality_check.py`: Comprehensive quality validation
  - `scripts/verify_complete_esri_file.py`: Verifies final ESRI file completeness

- **Production File**: Final ESRI export: `CAD_ESRI_Final_20251124_COMPLETE.xlsx`
  - 702,352 records (all legitimate records preserved)
  - 542,565 unique cases
  - 97.5% valid addresses (684,935 valid)
  - File size: 58.1 MB
  - **Status: ✅ READY FOR ESRI SUBMISSION**
  - Location: `data/ESRI_CADExport/CAD_ESRI_Final_20251124_COMPLETE.xlsx`
  - Email template: `data/02_reports/EMAIL_TO_ESRI_FINAL.md`

## Recent Updates (2025-11-24)

- **Address Corrections System**: Comprehensive address correction pipeline implemented:
  - RMS backfill: Automatically backfills incomplete addresses (missing street numbers, incomplete intersections) from RMS export using Case Number matching
  - Rule-based corrections: Applied corrections from `test/updates_corrections_FullAddress2.csv` for parks, generic locations, and specific address patterns
  - Street name standardization: Integrated official Hackensack street names file for verification and abbreviation expansion
  - Manual review workflow: Created scripts for efficient manual correction process

- **Hour Field Correction**: Fixed Hour field extraction to preserve exact time (HH:mm) from TimeOfCall without rounding

## Recent Updates (2025-11-22)

- Added `scripts/merge_cad_rms_incidents.py` to join cleaned CAD exports to the consolidated RMS export on `ReportNumberNew`/`Case Number` for targeted incident types, writing `Merged_Output_optimized.xlsx` with both CAD and RMS context (including CAD/RMS case numbers and narratives).
- Added `scripts/validate_cad_notes_alignment.py` to compare `CADNotes` across the merged export, the updated CAD master workbook, and the original 2019 CAD export, producing CSV reports that highlight any note-level misalignment by `ReportNumberNew`.
- Added `scripts/compare_merged_to_manual_csv.py` to verify that key CAD fields (especially `CADNotes`) in `Merged_Output_optimized.xlsx` stay in sync with the manually edited `2019_2025_11_17_Updated_CAD_Export_manual_fix_v1.csv`, with mismatch-only output for fast QA.

## Recent Updates (2025-11-21)
- Added support for rule-based `FullAddress2` corrections using `doc/updates_corrections_FullAddress2.csv` (or `paths.fulladdress2_corrections` in `config_enhanced.json`). These rules are applied at the start of the cleaning pipeline so downstream zone/grid backfill sees corrected park/home/intersection addresses.
- Added an optimized ESRI production deployment path (`scripts/esri_production_deploy.py`) plus a final Response_Type cleanup pipeline (`scripts/final_cleanup_tro_fuzzy_rms.py`) and address backfill pass (`scripts/backfill_address_from_rms.py`), achieving ~99.96% Response_Type coverage and improving valid address rate via RMS backfill.
- New review artifacts are written to `data/02_reports/`, including `tro_fro_manual_review.csv` (TRO/FRO narrative corrections), `unmapped_final_report.md`, `unmapped_breakdown_summary.csv`, `unmapped_cases_for_manual_backfill.csv`, `fuzzy_review.csv`, and `address_backfill_from_rms_report.md`/`address_backfill_from_rms_log.csv` for audit and manual follow-up.
- Trimmed the repository history and working tree by removing legacy `NJ_Geocode` assets that exceeded GitHub’s 100 MB cap.
- Added `doc/reminder_tomorrow.md` to track upcoming delivery tasks and QA follow-ups.
- ESRI sample exports now pull `Incident` text and `Response Type` directly from `CallType_Categories.csv`, title-case key human-readable fields, wrap `9-1-1` with an Excel guard, and write with a UTF-8 BOM so en dashes render correctly. A helper script (`ref/clean_calltypes.py`) keeps the mapping workbook’s casing and punctuation consistent.
- Introduced `scripts/build_calltype_master.py`, which builds `ref/CallType_Master_Mapping.csv` plus duplicate, anomaly, mapping-change, and unmapped review CSVs from the cleaned call-type workbook and historical incidents. These artifacts are the new source of truth for call type normalization.

> **Heads up:** The local working directory now lives at `CAD_Data_Cleaning_Engine`. Update any automation or shortcuts that referenced the previous folder name.

## **CAD Data Processing Class**

```python
import pandas as pd
import numpy as np
import logging
import re
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple

class CADDataProcessor:
    """Comprehensive CAD data cleaning and enrichment processor."""
    
    def __init__(self):
        """Initialize CAD processor with configuration."""
        self.processing_stats = {
            'records_processed': 0,
            'case_numbers_cleaned': 0,
            'addresses_normalized': 0,
            'time_fields_fixed': 0,
            'officer_names_mapped': 0,
            'narrative_entries_cleaned': 0,
            'quality_issues_fixed': 0
        }
    
    def process_cad_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main entry point for CAD data processing."""
        logger.info(f"Starting CAD data processing for {len(df):,} records...")
        
        # Step 1: Core field standardization
        df = self.standardize_core_fields(df)
        
        # Step 2: How Reported field cleaning (critical for 9-1-1 analysis)
        df = self.fix_how_reported_field(df)
        
        # Step 3: Time field cleaning and enhancement
        df = self.clean_and_enhance_time_fields(df)
        
        # Step 4: Officer field enhancement
        df = self.enhance_officer_fields(df)
        
        # Step 5: Address enhancement and geographic processing
        df = self.enhance_address_fields(df)
        
        # Step 6: Text field cleaning
        df = self.clean_text_fields(df)
        
        # Step 7: Data quality validation and scoring
        df = self.add_data_quality_metrics(df)
        
        # Step 8: Create enhanced derived fields
        df = self.create_enhanced_fields(df)
        
        self.processing_stats['records_processed'] = len(df)
        logger.info(f"CAD processing completed. Records processed: {len(df):,}")
        
        return df
    
    def standardize_core_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize core CAD fields with comprehensive cleaning."""
        logger.info("Standardizing core CAD fields...")
        
        # Case Number Standardization
        if 'ReportNumberNew' in df.columns:
            # Create clean case number
            df['CAD_Case_Number_Clean'] = df['ReportNumberNew'].astype(str).str.strip().str.upper()
            
            # Extract valid case number pattern (e.g., 24-123456)
            df['Case_Number'] = df['ReportNumberNew'].astype(str).str.extract(r'(\d{2}-\d{6})', expand=False)
            
            # Remove records without valid case numbers
            initial_count = len(df)
            df = df.dropna(subset=['Case_Number'])
            dropped_count = initial_count - len(df)
            if dropped_count > 0:
                logger.info(f"  Dropped {dropped_count:,} records without valid case numbers")
                self.processing_stats['case_numbers_cleaned'] += dropped_count
        
        # Incident Type Standardization
        if 'Incident' in df.columns:
            df['CAD_Incident_Type'] = df['Incident'].astype(str).str.strip()
        
        # Address Standardization
        if 'FullAddress2' in df.columns:
            df['CAD_Address_Clean'] = df['FullAddress2'].astype(str).str.strip().str.upper()
        
        # DateTime Standardization
        if 'Time of Call' in df.columns:
            df['CAD_DateTime'] = pd.to_datetime(df['Time of Call'], errors='coerce')
        
        # Disposition Standardization
        if 'Disposition' in df.columns:
            df['CAD_Disposition'] = df['Disposition'].astype(str).str.strip()
        
        # Add processing metadata
        df['CAD_Processing_Stage'] = 'Enhanced'
        df['CAD_Processing_DateTime'] = datetime.now()
        
        return df
    
    def fix_how_reported_field(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fix How Reported field - critical for 9-1-1 analysis."""
        logger.info("Fixing How Reported field...")
        
        if 'How Reported' not in df.columns:
            logger.warning("How Reported field not found in data")
            return df
        
        # Convert to string first
        df['How Reported'] = df['How Reported'].astype(str)
        
        # Fix date conversion artifacts (common Excel issue where 9-1-1 becomes dates)
        patterns_to_fix = [
            r'.*1901.*',           # Excel date conversion artifacts
            r'.*44197.*',          # Excel serial date numbers
            r'.*sep.*1.*1901.*',   # September 1, 1901 variations
            r'.*9/1/1901.*',       # Date format variations
            r'.*1901-09-01.*',     # ISO date format
            r'^911$',              # Just "911"
            r'.*9.*1.*1.*',        # Various 9-1-1 formats
            r'.*september.*1.*1901.*'  # Full month name
        ]
        
        fixed_count = 0
        for pattern in patterns_to_fix:
            mask = df['How Reported'].str.contains(pattern, na=False, regex=True, case=False)
            if mask.any():
                fixed_count += mask.sum()
                df.loc[mask, 'How Reported'] = '9-1-1'
        
        # Also fix any remaining variations
        df.loc[df['How Reported'].str.contains(r'^9.*1.*1', na=False, regex=True), 'How Reported'] = '9-1-1'
        
        # Standardize other common values
        df.loc[df['How Reported'].str.contains(r'^phone$', na=False, regex=True, case=False), 'How Reported'] = 'Phone'
        df.loc[df['How Reported'].str.contains(r'^walk.*in', na=False, regex=True, case=False), 'How Reported'] = 'Walk-in'
        df.loc[df['How Reported'].str.contains(r'^self.*init', na=False, regex=True, case=False), 'How Reported'] = 'Self-Initiated'
        
        # Create clean version for analysis
        df['CAD_How_Reported'] = df['How Reported']
        
        logger.info(f"  Fixed {fixed_count:,} How Reported entries")
        self.processing_stats['quality_issues_fixed'] += fixed_count
        
        return df
    
    def clean_and_enhance_time_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean time fields and create enhanced time calculations."""
        logger.info("Cleaning and enhancing time fields...")
        
        # Fix time duration fields (common issues: negatives, "?", artifacts)
        time_fields = ['Time Spent', 'Time Response']
        for field in time_fields:
            if field in df.columns:
                logger.info(f"  Processing {field}...")
                
                # Convert to string first to handle "?" values
                df[field] = df[field].astype(str)
                
                # Replace "?" with NaN
                question_mask = df[field].str.contains(r'^\?+$', na=False, regex=True)
                if question_mask.any():
                    df.loc[question_mask, field] = np.nan
                    logger.info(f"    Replaced {question_mask.sum():,} '?' values with NaN")
                
                # Convert to numeric, replacing errors with NaN
                df[field] = pd.to_numeric(df[field], errors='coerce')
                
                # Replace negative values and NaN with 0
                negative_mask = (df[field] < 0) | (df[field].isna())
                if negative_mask.any():
                    df.loc[negative_mask, field] = 0
                    logger.info(f"    Fixed {negative_mask.sum():,} negative/null values")
                
                # Create clean duration format (HH:MM)
                df[f'{field}_Clean'] = df[field].apply(self.format_duration)
                df[f'CAD_{field.replace(" ", "_")}'] = df[f'{field}_Clean']
        
        # Standardize datetime fields
        datetime_columns = ['Time of Call', 'Time Dispatched', 'Time Out', 'Time In']
        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                # Create standardized column names
                clean_col_name = f"CAD_{col.replace(' ', '_')}"
                df[clean_col_name] = df[col]
        
        # Create time-of-day categorization
        if 'Time of Call' in df.columns:
            df['CAD_Time_Of_Day'] = df['Time of Call'].dt.hour.apply(self.categorize_time_of_day)
            df['CAD_Enhanced_Time_Of_Day'] = df['CAD_Time_Of_Day'].apply(self.enhance_time_of_day)
        
        self.processing_stats['time_fields_fixed'] += 1
        return df
    
    def format_duration(self, decimal_hours):
        """Format duration from decimal hours to HH:MM format."""
        if pd.isna(decimal_hours) or decimal_hours <= 0:
            return "0:00"
        
        try:
            decimal_hours = float(decimal_hours)
            hours = int(decimal_hours)
            minutes = int((decimal_hours - hours) * 60)
            
            # Cap at reasonable maximum (24 hours)
            if hours > 24:
                return "24:00+"
            
            return f"{hours}:{minutes:02d}"
        except:
            return "0:00"
    
    def categorize_time_of_day(self, hour):
        """Categorize hour into time period."""
        if pd.isna(hour):
            return "Unknown"
        
        try:
            hour = int(hour)
            if 0 <= hour < 4:
                return "00:00 - 03:59 - Early Morning"
            elif 4 <= hour < 8:
                return "04:00 - 07:59 - Morning"
            elif 8 <= hour < 12:
                return "08:00 - 11:59 - Morning Peak"
            elif 12 <= hour < 16:
                return "12:00 - 15:59 - Afternoon"
            elif 16 <= hour < 20:
                return "16:00 - 19:59 - Evening Peak"
            else:
                return "20:00 - 23:59 - Night"
        except:
            return "Unknown"
    
    def enhance_time_of_day(self, time_of_day):
        """Create enhanced time categorization for shift analysis."""
        if pd.isna(time_of_day):
            return "Unknown"
        
        time_str = str(time_of_day).lower()
        
        if 'morning' in time_str:
            return "Day Shift"
        elif 'afternoon' in time_str:
            return "Day Shift"
        elif 'evening' in time_str:
            return "Evening Shift"
        elif 'night' in time_str or 'early morning' in time_str:
            return "Night Shift"
        else:
            return "Unknown Shift"
    
    def enhance_officer_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhance officer-related fields with parsing and mapping."""
        logger.info("Enhancing officer fields...")
        
        if 'Officer' not in df.columns:
            logger.warning("Officer field not found in data")
            return df
        
        # Create mapped officer field (would use Assignment_Master lookup in production)
        df['Officer_Mapped'] = df['Officer'].apply(self.map_officer_name)
        
        # Parse officer information into components
        officer_info = df['Officer_Mapped'].apply(self.parse_officer_info)
        
        df['CAD_Officer_Name'] = [info['name'] for info in officer_info]
        df['CAD_Officer_Badge'] = [info['badge'] for info in officer_info]
        df['CAD_Officer_Rank'] = [info['rank'] for info in officer_info]
        
        # Count successfully parsed officers
        parsed_count = (df['CAD_Officer_Name'] != '').sum()
        logger.info(f"  Successfully parsed {parsed_count:,} officer records")
        self.processing_stats['officer_names_mapped'] += parsed_count
        
        return df
    
    def parse_officer_info(self, officer_mapped):
        """Parse officer information into components."""
        if pd.isna(officer_mapped) or officer_mapped == "":
            return {'name': '', 'badge': '', 'rank': ''}
        
        officer_str = str(officer_mapped).strip()
        
        # Try to extract badge number (usually numeric)
        badge_match = re.search(r'\b(\d{3,5})\b', officer_str)
        badge = badge_match.group(1) if badge_match else ''
        
        # Try to extract rank (common prefixes)
        rank_patterns = ['SGT', 'LT', 'CAPT', 'DET', 'PO', 'OFFICER', 'SERGEANT', 'LIEUTENANT', 'CAPTAIN']
        rank = ''
        for pattern in rank_patterns:
            if pattern in officer_str.upper():
                rank = pattern
                break
        
        # Name is what's left after removing badge and rank indicators
        name = re.sub(r'\b\d{3,5}\b', '', officer_str)  # Remove badge
        for pattern in rank_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+', ' ', name).strip()
        
        return {'name': name, 'badge': badge, 'rank': rank}
    
    def map_officer_name(self, officer):
        """Map officer names for consistency."""
        if pd.isna(officer):
            return ""
        
        # This would normally use Assignment_Master_V2.xlsx lookup
        # For now, just clean up the format
        officer_str = str(officer).strip()
        officer_str = re.sub(r'\s+', ' ', officer_str)
        
        return officer_str
    
    def enhance_address_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhance address fields for geographic analysis."""
        logger.info("Enhancing address fields...")
        
        if 'FullAddress2' not in df.columns:
            logger.warning("FullAddress2 field not found in data")
            return df
        
        # Create block extraction
        df['CAD_Block'] = df['FullAddress2'].apply(self.extract_block)
        
        # Create normalized address
        df['CAD_Address_Normalized'] = df['FullAddress2'].apply(self.normalize_address)
        
        # Fix BACKUP call address restoration
        if 'Incident' in df.columns:
            backup_mask = df['Incident'].str.contains('BACKUP|Assist Own Agency', case=False, na=False)
            missing_address_mask = df['FullAddress2'].isna() | (df['FullAddress2'].astype(str).str.strip() == '')
            
            fix_mask = backup_mask & missing_address_mask
            if fix_mask.any():
                df.loc[fix_mask, 'FullAddress2'] = 'Location Per CAD System'
                logger.info(f"  Fixed {fix_mask.sum():,} backup call addresses")
        
        # Add zone and grid information if available
        if 'PDZone' in df.columns:
            df['CAD_Zone'] = df['PDZone'].fillna('UNK')
        
        if 'Grid' in df.columns:
            df['CAD_Grid'] = df['Grid'].fillna('')
        
        self.processing_stats['addresses_normalized'] += 1
        return df
    
    def extract_block(self, address):
        """Extract block information from address."""
        if pd.isna(address):
            return ""
        
        address_str = str(address).strip()
        
        # Extract first number and street name
        match = re.match(r'^(\d+)\s+(.+?)(?:\s+(?:APT|UNIT|#).*)?$', address_str, re.IGNORECASE)
        if match:
            street_num = int(match.group(1))
            street_name = match.group(2).strip()
            
            # Create block range (round down to nearest 100)
            block_start = (street_num // 100) * 100
            block_end = block_start + 99
            
            return f"{block_start}-{block_end} {street_name}"
        
        return address_str
    
    def normalize_address(self, address):
        """Normalize address for consistency."""
        if pd.isna(address):
            return ""
        
        address_str = str(address).strip().upper()
        
        # Common standardizations
        replacements = {
            ' ST ': ' STREET ',
            ' AVE ': ' AVENUE ',
            ' BLVD ': ' BOULEVARD ',
            ' RD ': ' ROAD ',
            ' DR ': ' DRIVE ',
            ' CT ': ' COURT ',
            ' PL ': ' PLACE ',
            ' LN ': ' LANE ',
            ' PKWY ': ' PARKWAY '
        }
        
        for old, new in replacements.items():
            address_str = address_str.replace(old, new)
        
        return address_str
    
    def clean_text_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean narrative and notes fields."""
        logger.info("Cleaning text fields...")
        
        # Clean CAD Notes
        if 'CADNotes' in df.columns:
            df['CADNotes_Original'] = df['CADNotes'].copy()
            df['CADNotes_Cleaned'] = df['CADNotes'].apply(self.clean_narrative)
            
            # Count cleaned notes
            cleaned_count = (df['CADNotes'] != df['CADNotes_Cleaned']).sum()
            logger.info(f"  Cleaned {cleaned_count:,} CADNotes entries")
            self.processing_stats['narrative_entries_cleaned'] += cleaned_count
        
        # Clean Narrative field
        if 'Narrative' in df.columns:
            df['Narrative_Clean'] = df['Narrative'].apply(self.clean_narrative)
        
        # Fix Disposition field
        if 'Disposition' in df.columns:
            df['Disposition'] = df['Disposition'].astype(str)
            df['Disposition'] = df['Disposition'].str.replace('sees Report', 'See Report', case=False, regex=False)
            df['Disposition'] = df['Disposition'].str.replace('sees report', 'See Report', case=False, regex=False)
            df['Disposition'] = df['Disposition'].str.replace('goa', 'GOA', case=False, regex=False)
            df['Disposition'] = df['Disposition'].str.replace('utl', 'UTL', case=False, regex=False)
        
        # Fix Response Type blanks
        if 'Response Type' in df.columns:
            before_blanks = df['Response Type'].isna().sum()
            df['Response Type'] = df['Response Type'].fillna('Not Specified')
            if before_blanks > 0:
                logger.info(f"  Filled {before_blanks:,} blank Response Type values")
        
        return df
    
    def clean_narrative(self, narrative):
        """Clean narrative text."""
        if pd.isna(narrative):
            return ""
        
        text = str(narrative).strip()
        
        # Remove common artifacts
        artifacts = [
            r'\?\s*-\s*\?\?\s*-\s*\?\s*-\s*\?',
            r'\?\s*-\s*\?\s*-\s*\?',
            r'^\?\s*$',
            r'^\s*-+\s*$',
            r'^\s*\?\s*$'
        ]
        
        for artifact in artifacts:
            text = re.sub(artifact, '', text, flags=re.IGNORECASE)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Return empty string if only punctuation remains
        if re.match(r'^[\?\-\s]*$', text):
            return ""
        
        return text
    
    def add_data_quality_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add data quality scoring and validation metrics."""
        logger.info("Adding data quality metrics...")
        
        # Initialize quality score
        df['Data_Quality_Score'] = 0
        
        # Score components (total 100 points possible)
        
        # Case number present (20 points)
        has_case_number = df['Case_Number'].notna() & (df['Case_Number'] != '')
        df.loc[has_case_number, 'Data_Quality_Score'] += 20
        
        # Address present (20 points)  
        if 'FullAddress2' in df.columns:
            has_address = df['FullAddress2'].notna() & (df['FullAddress2'] != '')
            df.loc[has_address, 'Data_Quality_Score'] += 20
        
        # Time data present (20 points)
        if 'Time of Call' in df.columns:
            has_call_time = df['Time of Call'].notna()
            df.loc[has_call_time, 'Data_Quality_Score'] += 10
        
        if 'Time Dispatched' in df.columns:
            has_dispatch_time = df['Time Dispatched'].notna()
            df.loc[has_dispatch_time, 'Data_Quality_Score'] += 10
        
        # Officer information (20 points)
        if 'Officer' in df.columns:
            has_officer = df['Officer'].notna() & (df['Officer'] != '')
            df.loc[has_officer, 'Data_Quality_Score'] += 20
        
        # Disposition available (10 points)
        if 'Disposition' in df.columns:
            has_disposition = df['Disposition'].notna() & (df['Disposition'] != '')
            df.loc[has_disposition, 'Data_Quality_Score'] += 10
        
        # Incident type available (10 points)
        if 'Incident' in df.columns:
            has_incident = df['Incident'].notna() & (df['Incident'] != '')
            df.loc[has_incident, 'Data_Quality_Score'] += 10
        
        # Add processing metadata
        df['Processing_Timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df['Pipeline_Version'] = 'CAD_Enhanced_2025.08.10'
        
        # Quality score statistics
        avg_quality = df['Data_Quality_Score'].mean()
        logger.info(f"  Average data quality score: {avg_quality:.1f}/100")
        
        return df
    
    def create_enhanced_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create additional enhanced fields for analysis."""
        logger.info("Creating enhanced fields...")
        
        # Response time calculation
        if 'Time of Call' in df.columns and 'Time Dispatched' in df.columns:
            df['CAD_Response_Time_Minutes'] = (df['Time Dispatched'] - df['Time of Call']).dt.total_seconds() / 60
            df['CAD_Response_Time_Minutes'] = df['CAD_Response_Time_Minutes'].fillna(0)
        
        # On-scene duration calculation
        if 'Time Out' in df.columns and 'Time In' in df.columns:
            df['CAD_On_Scene_Duration_Minutes'] = (df['Time In'] - df['Time Out']).dt.total_seconds() / 60
            df['CAD_On_Scene_Duration_Minutes'] = df['CAD_On_Scene_Duration_Minutes'].fillna(0)
        
        # Day of week
        if 'Time of Call' in df.columns:
            df['CAD_Day_of_Week'] = df['Time of Call'].dt.day_name()
            df['CAD_Is_Weekend'] = df['Time of Call'].dt.dayofweek.isin([5, 6])
        
        # Month and year for trend analysis
        if 'Time of Call' in df.columns:
            df['CAD_Year'] = df['Time of Call'].dt.year
            df['CAD_Month'] = df['Time of Call'].dt.month
            df['CAD_Quarter'] = df['Time of Call'].dt.quarter
        
        # Priority level (if available)
        if 'Priority' in df.columns:
            df['CAD_Priority'] = df['Priority'].astype(str).str.strip().str.upper()
        elif 'Response Type' in df.columns:
            # Infer priority from response type
            df['CAD_Priority'] = df['Response Type'].apply(self.infer_priority)
        
        logger.info("  Enhanced fields created successfully")
        return df
    
    def infer_priority(self, response_type):
        """Infer priority level from response type."""
        if pd.isna(response_type):
            return "UNKNOWN"
        
        response_str = str(response_type).upper()
        
        if any(term in response_str for term in ['EMERGENCY', 'URGENT', 'PRIORITY']):
            return "HIGH"
        elif any(term in response_str for term in ['NON-EMERGENCY', 'ROUTINE']):
            return "LOW"
        else:
            return "MEDIUM"
    
    def get_processing_stats(self) -> Dict:
        """Get processing statistics."""
        return self.processing_stats.copy()
    
    def create_cad_summary_report(self, df: pd.DataFrame) -> Dict:
        """Create comprehensive CAD processing summary report."""
        report = {
            'processing_timestamp': datetime.now().isoformat(),
            'total_records': len(df),
            'processing_stats': self.get_processing_stats(),
            'data_quality_metrics': {
                'average_quality_score': float(df['Data_Quality_Score'].mean()) if 'Data_Quality_Score' in df.columns else 0,
                'high_quality_records': int((df['Data_Quality_Score'] >= 80).sum()) if 'Data_Quality_Score' in df.columns else 0,
                'records_with_case_numbers': int(df['Case_Number'].notna().sum()) if 'Case_Number' in df.columns else 0,
                'records_with_addresses': int(df['FullAddress2'].notna().sum()) if 'FullAddress2' in df.columns else 0,
                'records_with_call_times': int(df['Time of Call'].notna().sum()) if 'Time of Call' in df.columns else 0
            },
            'field_enhancements': {
                'case_numbers_cleaned': 'CAD_Case_Number_Clean, Case_Number',
                'addresses_enhanced': 'CAD_Address_Clean, CAD_Address_Normalized, CAD_Block',
                'time_fields_enhanced': 'CAD_Time_Of_Day, CAD_Enhanced_Time_Of_Day, CAD_Response_Time_Minutes',
                'officer_fields_parsed': 'CAD_Officer_Name, CAD_Officer_Badge, CAD_Officer_Rank',
                'text_fields_cleaned': 'CADNotes_Cleaned, Narrative_Clean',
                'quality_metrics_added': 'Data_Quality_Score, Processing_Timestamp'
            }
        }
        
        return report
```

## **Usage Example**

```python
# Example usage of the CAD data processor
def process_cad_export(cad_file_path: str) -> Tuple[pd.DataFrame, Dict]:
    """Process a CAD export file using the CAD processor."""
    
    # Load CAD data
    df = pd.read_excel(cad_file_path)
    
    # Initialize processor
    processor = CADDataProcessor()
    
    # Process the data
    enhanced_df = processor.process_cad_data(df)
    
    # Get processing statistics
    stats = processor.get_processing_stats()
    
    # Create summary report
    report = processor.create_cad_summary_report(enhanced_df)
    
    return enhanced_df, report

# Usage
if __name__ == "__main__":
    cad_file = "path/to/cad_export.xlsx"
    processed_data, processing_report = process_cad_export(cad_file)
    
    print(f"Processed {len(processed_data):,} CAD records")
    print(f"Average quality score: {processing_report['data_quality_metrics']['average_quality_score']:.1f}/100")
    print(f"Processing stats: {processing_report['processing_stats']}")
```

## **Key Features of This CAD Processing Code**

1. **Comprehensive Field Cleaning**: Handles case numbers, addresses, time fields, officer names, and text fields
2. **Critical 9-1-1 Fix**: Resolves Excel date conversion artifacts that turn "9-1-1" into dates
3. **Time Enhancement**: Creates time-of-day categories and shift analysis
4. **Geographic Processing**: Extracts blocks and normalizes addresses for mapping
5. **Officer Parsing**: Separates names, badges, and ranks
6. **Quality Scoring**: 100-point quality assessment system
7. **Enhanced Fields**: Response times, on-scene duration, day-of-week analysis
8. **Comprehensive Logging**: Detailed processing statistics and reporting

This code can be directly integrated into existing scripts or used as a standalone CAD processing module.