# CAD/RMS ETL Pipeline Refinement Documentation

**Date**: December 17, 2025  
**Status**: ✅ Complete Implementation  
**Last Updated**: December 19, 2025

## Overview

This document describes the refined ETL pipeline for CAD/RMS data cleaning, normalization, geocoding, and ESRI output generation. The pipeline achieves near 100% completeness and validation, suitable for direct ingestion into ArcGIS Pro.

## New Scripts

### 1. `scripts/geocode_nj_geocoder.py`
**Purpose**: Backfill missing latitude/longitude coordinates using the New Jersey Geocoder REST service.

**Service Endpoint**: `https://geo.nj.gov/arcgis/rest/services/Tasks/NJ_Geocode/GeocodeServer`

**Features**:
- Batch geocoding with parallel processing
- Automatic retry logic for failed requests
- High-quality match filtering (score >= 80)
- Progress tracking and statistics
- Handles CSV and Excel input/output

**Usage**:
```bash
python scripts/geocode_nj_geocoder.py \
    --input data/CAD_CLEANED.csv \
    --output data/CAD_geocoded.csv \
    --address-column FullAddress2 \
    --batch-size 100 \
    --max-workers 5
```

**Parameters**:
- `--input`: Input file path (required)
- `--output`: Output file path (optional, defaults to input with _geocoded suffix)
- `--address-column`: Name of address column (default: FullAddress2)
- `--latitude-column`: Name of latitude column (default: latitude)
- `--longitude-column`: Name of longitude column (default: longitude)
- `--batch-size`: Number of addresses per batch (default: 100)
- `--max-workers`: Concurrent requests (default: 5)
- `--format`: Output format: csv or excel (default: csv)

### 2. `scripts/unified_rms_backfill.py`
**Purpose**: Cross-map CAD records to RMS records and backfill missing/invalid CAD fields using validated RMS data.

**Features**:
- Follows merge policy from `cad_to_rms_field_map_latest.json`
- Handles field priority (e.g., Incident Type_1 → Incident Type_2 → Incident Type_3)
- Deduplicates RMS records according to policy
- Comprehensive backfill logging
- Supports multiple RMS files

**Usage**:
```bash
python scripts/unified_rms_backfill.py \
    --input data/CAD_CLEANED.csv \
    --output data/CAD_rms_backfilled.csv \
    --log data/rms_backfill_log.csv
```

**Parameters**:
- `--input`: Input CAD file path (required)
- `--output`: Output file path (optional)
- `--config`: Path to config_enhanced.json (optional)
- `--merge-policy`: Path to cad_to_rms_field_map_latest.json (optional)
- `--log`: Path to save backfill log CSV (optional)
- `--format`: Output format: csv or excel (default: csv)

**Backfill Fields** (from merge policy):
- `Incident`: From RMS Incident Type_1, Type_2, Type_3 (priority order)
- `FullAddress2`: From RMS FullAddress (only if CAD is null/blank)
- `Grid`: From RMS Grid (only if CAD is null/blank)
- `PDZone`: From RMS Zone (only if CAD is null/blank)
- `Officer`: From RMS Officer of Record (only if CAD is null/blank)

### 3. `scripts/generate_esri_output.py` (Original)
**Purpose**: Generate draft and polished ESRI outputs with strict column ordering.

**Note**: Enhanced version available at `scripts/enhanced_esri_output_generator.py` with additional features.

### 3a. `scripts/enhanced_esri_output_generator.py` (Enhanced - NEW)
**Purpose**: Enhanced ESRI output generator with comprehensive data quality reporting.

**Features**:
- Pre-geocoding polished output (generated after RMS backfill, before geocoding)
- Null value CSV reports (one per column with nulls, includes full record context)
- Comprehensive processing summary markdown report
- Type-safe numeric formatting (prevents ValueError crashes)
- Geographic coordinate validation (NJ bounds checking)
- Data quality scoring and recommendations

**Output Files**:
- `CAD_ESRI_DRAFT_*.xlsx`: All cleaned data with validation flags
- `CAD_ESRI_POLISHED_PRE_GEOCODE_*.xlsx`: Polished output before geocoding
- `CAD_ESRI_POLISHED_*.xlsx`: Final polished output (after geocoding)
- `CAD_NULL_VALUES_[ColumnName]_*.csv`: Null value reports (in `data/02_reports/data_quality/`)
- `PROCESSING_SUMMARY_*.md`: Comprehensive markdown report (in `data/02_reports/data_quality/`)

**Features**:
- **Draft Output**: All cleaned data with validation flags and internal review columns
- **Polished ESRI Output**: Final validated data with exact column order for ArcGIS Pro
- Automatic ZoneCalc calculation (from PDZone or Grid)
- How Reported normalization
- Removes internal validation columns from polished output

**Required ESRI Column Order**:
1. ReportNumberNew
2. Incident
3. How Reported
4. FullAddress2
5. Grid
6. ZoneCalc
7. Time of Call
8. cYear
9. cMonth
10. Hour_Calc
11. DayofWeek
12. Time Dispatched
13. Time Out
14. Time In
15. Time Spent
16. Time Response
17. Officer
18. Disposition
19. latitude
20. longitude

**Usage**:
```bash
python scripts/generate_esri_output.py \
    --input data/CAD_FINAL.csv \
    --output-dir data/ESRI_CADExport \
    --base-filename CAD_ESRI \
    --zonecalc-source PDZone \
    --format csv
```

**Parameters**:
- `--input`: Input file path (required)
- `--output-dir`: Output directory (optional, defaults to input file directory)
- `--base-filename`: Base filename for outputs (default: CAD_ESRI)
- `--zonecalc-source`: Source for ZoneCalc: PDZone or Grid (default: PDZone)
- `--format`: Output format: csv or excel (default: csv)

**Output Files**:
- `{base_filename}_DRAFT_{timestamp}.csv`: All columns with validation flags
- `{base_filename}_POLISHED_{timestamp}.csv`: Strict ESRI column order only

### 4. `scripts/master_pipeline.py`
**Purpose**: Orchestrates the complete ETL pipeline end-to-end.

**Pipeline Steps**:
1. Load and validate CAD data
2. Clean and normalize data
3. Backfill from RMS (if enabled)
4. Geocode missing coordinates (if enabled)
5. Generate draft and polished ESRI outputs

**Usage**:
```bash
python scripts/master_pipeline.py \
    --input data/2019_2025_12_14_All_CAD.csv \
    --output-dir data/ESRI_CADExport \
    --base-filename CAD_ESRI \
    --format csv
```

**Parameters**:
- `--input`: Input CAD file path (required)
- `--output-dir`: Output directory (optional)
- `--base-filename`: Base filename for outputs (default: CAD_ESRI)
- `--no-rms-backfill`: Skip RMS backfill step
- `--no-geocode`: Skip geocoding step
- `--format`: Output format: csv or excel (default: csv)
- `--config`: Path to config_enhanced.json (optional)

## Workflow

### Recommended Processing Sequence

1. **Initial Validation and Cleaning**
   ```bash
   python validate_cad_export_parallel.py
   ```
   This produces `CAD_CLEANED.csv` with auto-fixes applied.

2. **RMS Backfill** (if RMS data available)
   ```bash
   python scripts/unified_rms_backfill.py \
       --input CAD_CLEANED.csv \
       --output CAD_RMS_BACKFILLED.csv
   ```

3. **Geocoding** (if coordinates missing)
   ```bash
   python scripts/geocode_nj_geocoder.py \
       --input CAD_RMS_BACKFILLED.csv \
       --output CAD_GEOCODED.csv
   ```

4. **Generate ESRI Outputs**
   ```bash
   python scripts/generate_esri_output.py \
       --input CAD_GEOCODED.csv \
       --output-dir data/ESRI_CADExport
   ```

### Or Use Master Pipeline (All-in-One)

```bash
python scripts/master_pipeline.py \
    --input data/2019_2025_12_14_All_CAD.csv \
    --output-dir data/ESRI_CADExport
```

## Column Mapping and Transformations

### ZoneCalc Field
- **Source**: PDZone (default) or Grid
- **Calculation**: Direct mapping from PDZone if available, otherwise derived from Grid
- **Note**: ZoneCalc is required in ESRI output but may be the same as PDZone

### How Reported Normalization
The pipeline normalizes "How Reported" values to valid domain:
- `9-1-1`, `911`, `9/1/1` → `9-1-1`
- `WALK IN`, `WALK-IN`, `WALKIN` → `Walk-In`
- `PHONE` → `Phone`
- `SELF INITIATED`, `SELF-INITIATED` → `Self-Initiated`
- `EMAIL`, `E-MAIL` → `eMail`
- And other standard variations

### Internal Columns Excluded from Polished Output
The following columns are automatically excluded from the polished ESRI output:
- Validation flags: `data_quality_flag`, `validation_errors`, `validation_warnings`
- Source tracking: `Incident_source`, `FullAddress2_source`, `Grid_source`, `PDZone_source`, `Officer_source`
- Merge tracking: `merge_run_id`, `merge_timestamp`, `merge_join_key`, `merge_match_flag`, `merge_rms_row_count_for_key`
- Geocoding metadata: `geocode_score`, `geocode_match_type`, `geocode_status`
- Internal processing: `_join_key_normalized`, `_CleanAddress`, `Incident_key`

## Data Quality Targets

- **Error Rate**: < 5%
- **Critical Errors**: 0
- **ReportNumberNew**: 100% valid format
- **TimeOfCall**: 100% valid dates
- **Address Completeness**: >95%
- **Disposition/How Reported**: >98% valid
- **Geocoding Coverage**: >95% (target: 99.9%+)

## Dependencies

All scripts require:
- `pandas>=2.0.0`
- `numpy>=1.24.0`
- `openpyxl>=3.1.0`
- `requests>=2.31.0` (for geocoding)

Install with:
```bash
pip install -r requirements.txt
```

## Configuration Files

### `config/config_enhanced.json`
Contains paths and settings for:
- RMS data directory
- Zone master lookup
- Address abbreviations
- Field mappings

### `cad_to_rms_field_map_latest.json`
Defines:
- Join keys (CAD.ReportNumberNew ↔ RMS.Case Number)
- Field mappings with priority
- Update conditions (when to backfill)
- Deduplication policy

## Troubleshooting

### Geocoding Issues
- **Low success rate**: Check address quality in FullAddress2 column
- **Timeout errors**: Reduce `--max-workers` or increase `--batch-size`
- **Service unavailable**: Check NJ Geocoder service status

### RMS Backfill Issues
- **No matches**: Verify join keys match (ReportNumberNew vs Case Number)
- **Missing fields**: Check RMS files have required columns
- **Deduplication**: Review merge policy in `cad_to_rms_field_map_latest.json`

### ESRI Output Issues
- **Missing columns**: Check input data has all required fields
- **Column order**: Polished output enforces exact order automatically
- **ZoneCalc**: Verify PDZone or Grid column exists

## Performance

Expected processing times (approximate):
- **Validation** (702K records): ~15 seconds
- **Validation** (1.35M records): ~23 seconds
- **RMS Backfill** (702K records): ~30-60 seconds
- **Geocoding** (100K addresses): ~10-20 minutes (depends on service)
- **Output Generation**: <5 seconds

## Next Steps

1. Test pipeline with sample data
2. Process full 2019-2025 dataset
3. Validate polished output against ArcGIS Pro requirements
4. Document any additional field mappings or transformations needed

## Support

For issues or questions:
- Check script logs: `pipeline.log`
- Review validation reports: `CAD_VALIDATION_SUMMARY.txt`
- Check backfill logs: `rms_backfill_log.csv`

