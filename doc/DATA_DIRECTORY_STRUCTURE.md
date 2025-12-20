# Data Directory Structure

## Overview

The data directory is organized to separate raw inputs, processed outputs, reports, and ESRI-specific files.

## Directory Structure

```
data/
├── 01_raw/                    # Raw input files (CAD and RMS)
│   ├── sample/                # Sample files for testing
│   ├── 19_to_25_12_18_CAD_Data.xlsx
│   └── ...
│
├── 02_cleaned/                # Cleaned data (currently unused)
│
├── 02_reports/                # Reports and diagnostic files
│   ├── cad_validation/        # CAD validation reports
│   ├── data_quality/         # Data quality reports (NEW)
│   │   ├── CAD_NULL_VALUES_*.csv
│   │   └── PROCESSING_SUMMARY_*.md
│   └── ... (other reports)
│
├── 03_enriched/               # Enriched data (currently unused)
│
├── 04_combined/               # Combined data (currently unused)
│
├── ESRI_CADExport/            # ESRI-specific outputs
│   ├── archive/               # Archived ESRI outputs
│   ├── CAD_ESRI_DRAFT_*.xlsx
│   ├── CAD_ESRI_POLISHED_*.xlsx
│   └── CAD_ESRI_POLISHED_PRE_GEOCODE_*.xlsx
│
└── rms/                       # RMS input files
    └── 19_to_25_12_18_HPD_RMS_Export.xlsx
```

## File Locations by Type

### ESRI Output Files
**Location**: `data/ESRI_CADExport/`

- **Draft Output**: `CAD_ESRI_DRAFT_YYYYMMDD_HHMMSS.xlsx`
  - All cleaned data with validation flags and internal review columns
  - Used for internal review and validation

- **Polished ESRI Output**: `CAD_ESRI_POLISHED_YYYYMMDD_HHMMSS.xlsx`
  - Final validated data with strict ESRI column order
  - Ready for ArcGIS Pro ingestion
  - Excludes internal validation columns

- **Pre-Geocoding Polished**: `CAD_ESRI_POLISHED_PRE_GEOCODE_YYYYMMDD_HHMMSS.xlsx`
  - Polished output before geocoding step
  - Allows geocoding to be run separately or re-run
  - Includes latitude/longitude columns (may be null/empty)

### Data Quality Reports
**Location**: `data/02_reports/data_quality/`

- **Null Value CSVs**: `CAD_NULL_VALUES_[ColumnName]_YYYYMMDD_HHMMSS.csv`
  - One CSV per column that has null/blank values
  - Contains full record context (all columns)
  - Only created if nulls exist in that column

- **Processing Summary**: `PROCESSING_SUMMARY_YYYYMMDD_HHMMSS.md`
  - Comprehensive markdown report
  - Includes statistics, data quality issues, recommendations
  - Links to null value CSV files

## Directory Creation

The pipeline should automatically create directories if they don't exist:
- `data/ESRI_CADExport/` (usually exists)
- `data/02_reports/data_quality/` (created if needed)

## Rationale

### Why Separate ESRI_CADExport from Reports?

1. **ESRI_CADExport**: Production-ready outputs for ArcGIS Pro
   - Clean, validated data
   - Strict column ordering
   - No diagnostic/internal columns

2. **02_reports/data_quality**: Diagnostic and review files
   - Null value reports (for manual review)
   - Processing summaries (for analysis)
   - Not intended for ESRI ingestion

### Benefits

- **Clear separation** between production outputs and diagnostic reports
- **Easier navigation** - ESRI files in one place, reports in another
- **Better organization** - follows existing `02_reports/` pattern
- **Scalability** - can add more report types in `02_reports/` subdirectories

## File Naming Conventions

### Timestamp Format
- Format: `YYYYMMDD_HHMMSS`
- Example: `20251219_143022`
- Used for: All output files to prevent overwrites

### ESRI Files
- Pattern: `CAD_ESRI_[TYPE]_YYYYMMDD_HHMMSS.xlsx`
- Types: `DRAFT`, `POLISHED`, `POLISHED_PRE_GEOCODE`

### Null Value Reports
- Pattern: `CAD_NULL_VALUES_[ColumnName]_YYYYMMDD_HHMMSS.csv`
- Column names: Sanitized (spaces replaced, special chars removed)

### Processing Summary
- Pattern: `PROCESSING_SUMMARY_YYYYMMDD_HHMMSS.md`

## Integration with Pipeline

The enhanced output generator should:
1. Check if `data/02_reports/data_quality/` exists, create if not
2. Generate null value CSVs in `data/02_reports/data_quality/`
3. Generate processing summary in `data/02_reports/data_quality/`
4. Generate ESRI outputs in `data/ESRI_CADExport/`
5. Reference null value CSV paths in the processing summary markdown
