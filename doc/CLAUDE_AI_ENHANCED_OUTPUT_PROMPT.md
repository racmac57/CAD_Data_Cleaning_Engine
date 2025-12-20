# Claude AI Prompt: Enhanced ETL Output Generation

## Context

You are working with a CAD/RMS data cleaning and ETL pipeline for the City of Hackensack. The pipeline processes exported CAD (Computer-Aided Dispatch) and RMS (Records Management System) data, cleans it, backfills missing values from RMS, geocodes addresses, and generates outputs for ESRI ArcGIS Pro.

## Current Pipeline Structure

The pipeline (`scripts/master_pipeline.py`) currently:
1. Validates and cleans CAD data
2. Backfills missing CAD fields from RMS data (including FullAddress2, Incident, Grid, PDZone, Officer)
3. Geocodes missing latitude/longitude coordinates
4. Generates two outputs:
   - **Draft Output**: All cleaned data with validation flags and internal review columns
   - **Polished ESRI Output**: Final validated data with strict column order for ArcGIS Pro

## Required Enhancements

Please enhance the output generation to provide the following:

### 1. Polished Version for ESRI (Already Exists - Keep As-Is)
- File: `CAD_ESRI_POLISHED_YYYYMMDD_HHMMSS.xlsx`
- Contains: Final validated data with strict ESRI column order
- Status: ✅ Already implemented in `scripts/generate_esri_output.py`

### 2. Pre-Geocoding Polished Version (NEW)
- File: `CAD_ESRI_POLISHED_PRE_GEOCODE_YYYYMMDD_HHMMSS.xlsx`
- Contains: Polished ESRI output BEFORE geocoding step
- Purpose: Allows geocoding to be run separately or re-run if needed
- Should have: All polished columns including `latitude` and `longitude` (may be null/empty)

### 3. Null Value Reports by Column (NEW)
- **Location**: `data/02_reports/data_quality/` (create directory if needed)
- For each column that has null/blank values, create a separate CSV file
- File naming: `CAD_NULL_VALUES_[ColumnName]_YYYYMMDD_HHMMSS.csv`
- Example: If "Incident" column has 5 records with null/blank values, create:
  - `data/02_reports/data_quality/CAD_NULL_VALUES_Incident_YYYYMMDD_HHMMSS.csv` with those 5 records (all columns included)
- Include ALL columns in each null report CSV (not just the null column)
- Only create CSV files for columns that actually have null/blank values
- Columns to check: All columns in the polished ESRI output

### 4. Processing Summary Markdown Report (NEW)
- **Location**: `data/02_reports/data_quality/PROCESSING_SUMMARY_YYYYMMDD_HHMMSS.md`
- File: `PROCESSING_SUMMARY_YYYYMMDD_HHMMSS.md`
- Should include:

#### A. Executive Summary
- Total records processed
- Records successfully processed
- Records with issues/warnings
- Overall data quality score

#### B. Processing Statistics
- Validation statistics (rules passed/failed)
- RMS backfill statistics:
  - Records matched to RMS
  - Fields backfilled (Incident, FullAddress2, Grid, PDZone, Officer)
  - Backfill counts per field
- Geocoding statistics:
  - Records geocoded
  - Success rate
  - Records still missing coordinates

#### C. Data Quality Issues
- Columns with null/blank values:
  - Column name
  - Count of null/blank records
  - Percentage of total records
  - Link to corresponding null value CSV file
- Invalid values by column:
  - Column name
  - Invalid value examples
  - Count of invalid records
- Duplicate records (if any)
- Records with incorrect locations (coordinates outside expected bounds, etc.)

#### D. Records Requiring Manual Review
- List of specific issues:
  - Missing critical fields (e.g., FullAddress2, Incident)
  - Invalid coordinates
  - Data inconsistencies
  - Records that couldn't be matched to RMS

#### E. Recommendations
- Suggested corrections
- Priority items for manual review
- Data quality improvement suggestions

## Technical Requirements

### File Locations
- **ESRI Output Files**: `data/ESRI_CADExport/`
  - Draft and polished ESRI outputs (Excel files)
  - Pre-geocoding polished output
- **Data Quality Reports**: `data/02_reports/data_quality/`
  - Null value CSVs (one per column with nulls)
  - Processing summary markdown report
- Use timestamp format: `YYYYMMDD_HHMMSS` (e.g., `20251219_143022`)
- Create directories if they don't exist

### Code Structure
- Enhance `scripts/generate_esri_output.py` or create new `scripts/enhanced_output_generator.py`
- Integrate with existing `scripts/master_pipeline.py`
- Maintain backward compatibility with existing outputs
- Use `pathlib.Path` for cross-platform path handling
- Create directories with `Path.mkdir(parents=True, exist_ok=True)`

### Dependencies
- Use pandas for data manipulation
- Use pathlib for file paths
- Use datetime for timestamps
- Follow existing logging patterns

### Performance
- Use vectorized operations where possible
- Handle large datasets efficiently (700K+ records)
- Don't create unnecessary intermediate files

## Current Code References

### Key Files to Review:
1. `scripts/generate_esri_output.py` - Current output generator
2. `scripts/master_pipeline.py` - Main pipeline orchestrator
3. `scripts/unified_rms_backfill.py` - RMS backfill logic
4. `scripts/geocode_nj_locator.py` - Geocoding logic
5. `cad_to_rms_field_map_latest.json` - Field mapping configuration

### ESRI Required Column Order:
```
ReportNumberNew, Incident, How Reported, FullAddress2, Grid, ZoneCalc,
Time of Call, cYear, cMonth, Hour_Calc, DayofWeek, Time Dispatched,
Time Out, Time In, Time Spent, Time Response, Officer, Disposition,
latitude, longitude
```

## Implementation Guidelines

1. **Directory Structure**: 
   - Create `data/02_reports/data_quality/` if it doesn't exist
   - Use `data/ESRI_CADExport/` for ESRI outputs (usually exists)
   - See `doc/DATA_DIRECTORY_STRUCTURE.md` for full structure

2. **Pre-Geocoding Output**: Generate polished output after RMS backfill but before geocoding
   - Save to: `data/ESRI_CADExport/CAD_ESRI_POLISHED_PRE_GEOCODE_YYYYMMDD_HHMMSS.xlsx`

3. **Null Value CSVs**: 
   - Use vectorized pandas operations to identify null/blank values efficiently
   - Save to: `data/02_reports/data_quality/CAD_NULL_VALUES_[ColumnName]_YYYYMMDD_HHMMSS.csv`
   - Include ALL columns in each CSV (full record context)

4. **Markdown Report**: 
   - Use Python string formatting or template engine for clean markdown generation
   - Save to: `data/02_reports/data_quality/PROCESSING_SUMMARY_YYYYMMDD_HHMMSS.md`
   - Include links to null value CSV files (relative paths)

5. **Error Handling**: Gracefully handle missing columns, empty dataframes, etc.

6. **Logging**: Log all file generation activities with full paths

7. **Testing**: Ensure outputs are valid and can be opened in Excel/ArcGIS Pro

## Expected Output Files

After running the enhanced pipeline, the output structure should be:

### ESRI Output Directory (`data/ESRI_CADExport/`)
```
data/ESRI_CADExport/
├── CAD_ESRI_DRAFT_YYYYMMDD_HHMMSS.xlsx (existing)
├── CAD_ESRI_POLISHED_YYYYMMDD_HHMMSS.xlsx (existing - final for ESRI)
└── CAD_ESRI_POLISHED_PRE_GEOCODE_YYYYMMDD_HHMMSS.xlsx (NEW - for geocoding)
```

### Data Quality Reports Directory (`data/02_reports/data_quality/`)
```
data/02_reports/data_quality/
├── CAD_NULL_VALUES_Incident_YYYYMMDD_HHMMSS.csv (NEW - if nulls exist)
├── CAD_NULL_VALUES_FullAddress2_YYYYMMDD_HHMMSS.csv (NEW - if nulls exist)
├── CAD_NULL_VALUES_latitude_YYYYMMDD_HHMMSS.csv (NEW - if nulls exist)
├── ... (one CSV per column with nulls)
└── PROCESSING_SUMMARY_YYYYMMDD_HHMMSS.md (NEW - comprehensive report)
```

**Note**: The `data/02_reports/data_quality/` directory should be created if it doesn't exist. This keeps diagnostic/report files separate from production ESRI outputs.

## Questions to Consider

1. Should null value CSVs include all columns or just the problematic column?
   - **Answer**: Include ALL columns (so user can see full context of records with issues)

2. Should we create null reports for draft or polished output?
   - **Answer**: Polished output (since that's what goes to ESRI)

3. What defines "incorrect locations"?
   - **Answer**: Coordinates outside New Jersey bounds (approximately lat: 38.8-41.4, lon: -75.6 to -73.9), or coordinates that are clearly invalid (0,0 or null)

4. Should the pre-geocode output include latitude/longitude columns even if empty?
   - **Answer**: Yes, include them as empty/null so the geocoding script can populate them

## Success Criteria

✅ All 4 output types are generated correctly
✅ Null value CSVs contain full record context
✅ Markdown report is comprehensive and readable
✅ Files are properly named with timestamps
✅ No breaking changes to existing pipeline
✅ Performance is acceptable for 700K+ records
✅ All outputs are valid and can be opened in Excel/ArcGIS Pro

## Additional Notes

- The pipeline already handles RMS backfill for FullAddress2 (confirmed in `cad_to_rms_field_map_latest.json`)
- Geocoding uses local ArcGIS locator files for fast processing
- The polished output must maintain strict ESRI column order
- Internal validation columns should be excluded from polished output (already handled)

## Directory Structure Summary

**ESRI Outputs** (Production files):
- `data/ESRI_CADExport/CAD_ESRI_DRAFT_*.xlsx`
- `data/ESRI_CADExport/CAD_ESRI_POLISHED_*.xlsx`
- `data/ESRI_CADExport/CAD_ESRI_POLISHED_PRE_GEOCODE_*.xlsx`

**Data Quality Reports** (Diagnostic files):
- `data/02_reports/data_quality/CAD_NULL_VALUES_*.csv` (one per column with nulls)
- `data/02_reports/data_quality/PROCESSING_SUMMARY_*.md`

**Key Point**: Null value CSVs and processing summary go in `data/02_reports/data_quality/`, NOT in `data/ESRI_CADExport/`. This keeps diagnostic reports separate from production ESRI outputs.

See `doc/DATA_DIRECTORY_STRUCTURE.md` for complete directory structure documentation.

---

**Please implement these enhancements while maintaining code quality, performance, and backward compatibility.**

