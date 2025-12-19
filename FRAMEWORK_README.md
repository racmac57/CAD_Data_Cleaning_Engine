# CAD Data Correction Framework

**Production-safe, modular correction system for 700K+ emergency dispatch records**

## Overview

This framework provides a fault-tolerant, end-to-end solution for correcting corrupted CAD (Computer-Aided Dispatch) data suffering from:

- Duplicate corruption from broken merge logic
- Partial manual corrections
- Quality scoring failures
- Missing or malformed field data
- UTF-8 encoding issues

## Features

✅ **Modular Architecture**: Separate concerns (processing, validation, logging, hashing)
✅ **Pre/Post Validation**: Comprehensive validation before and after processing
✅ **Audit Trail**: Complete change tracking for all field-level modifications
✅ **Quality Scoring**: 100-point quality assessment per record
✅ **Duplicate Detection**: Identifies and flags merge artifacts
✅ **File Integrity**: SHA256 hashing to detect silent corruption
✅ **Configurable**: YAML-based configuration for all settings
✅ **Production-Safe**: Handles 728,593 records with no data loss risk

## Directory Structure

```
CAD_Data_Cleaning_Engine/
│
├── main.py                          # Main entry point
├── config/
│   └── config.yml                   # Configuration file
│
├── processors/
│   ├── __init__.py
│   └── cad_data_processor.py        # Core processor class
│
├── validators/
│   ├── __init__.py
│   ├── validation_harness.py        # Pre-run validation
│   └── validate_full_pipeline.py    # Post-run validation
│
├── utils/
│   ├── __init__.py
│   ├── logger.py                    # Structured logging
│   ├── hash_utils.py                # File integrity hashing
│   └── validate_schema.py           # Schema validation
│
├── logs/
│   └── cad_processing.log           # Processing logs
│
├── data/
│   ├── input/                       # Input files
│   ├── output/                      # Corrected output
│   ├── audit/                       # Audit trails and hashes
│   └── manual_review/               # Flagged records
│
└── requirements.txt                 # Python dependencies
```

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the system:**
   - Edit `config/config.yml` to set file paths and processing options
   - Ensure input file path points to your CAD data
   - Configure correction file paths

## Quick Start

### 1. Basic Usage

Run the full pipeline with default configuration:

```bash
python main.py
```

### 2. Test Mode

Process a subset of data for testing:

```bash
python main.py --test-mode
```

### 3. Validation Only

Run validation checks without processing data:

```bash
python main.py --validate-only
```

### 4. Custom Configuration

Use a custom config file:

```bash
python main.py --config config/custom_config.yml
```

## Usage Examples

### Python API Usage

```python
from processors.cad_data_processor import CADDataProcessor
from utils.logger import setup_logger

# Initialize processor
processor = CADDataProcessor('config/config.yml')

# Load data
processor.load_data()

# Run all corrections
processor.run_all_corrections()

# Export corrected data
processor.export_corrected_data()

# Get processing summary
summary = processor.get_processing_summary()
print(f"Processed {summary['processing_stats']['records_output']:,} records")
print(f"Average quality: {summary['quality_metrics']['average_quality_score']:.1f}/100")
```

### Running Individual Steps

```python
# Just validate schema
processor.load_data()
processor.validate_schema()

# Apply specific corrections
processor.apply_manual_corrections()

# Calculate quality scores only
processor.calculate_quality_scores()

# Flag records for manual review
processor.flag_for_manual_review("FullAddress2.str.contains('UNKNOWN')")
```

## Configuration

The `config/config.yml` file controls all aspects of the pipeline:

### Key Configuration Sections

**Processing Options:**
```yaml
processing:
  apply_address_corrections: true
  apply_disposition_corrections: true
  extract_hour_field: true
  detect_duplicates: true
  chunk_size: 10000
```

**Quality Scoring Weights:**
```yaml
quality_weights:
  case_number_present: 20
  address_present: 20
  call_time_present: 10
  officer_present: 20
  # ... (total = 100)
```

**Validation Settings:**
```yaml
validation:
  validate_schema: true
  strict_schema: false
  check_record_count: true
  verify_corrections_applied: true
```

## Core Components

### 1. CADDataProcessor

Main orchestrator class that:
- Loads and validates CAD data
- Applies manual corrections (address, disposition, how_reported)
- Extracts hour field from TimeOfCall
- Maps call types to standardized categories
- Detects and flags duplicates
- Calculates quality scores (0-100)
- Maintains audit trail
- Exports corrected data

### 2. ValidationHarness

Pre-processing validation that checks:
- Environment (Python version, dependencies)
- File existence and accessibility
- Configuration validity
- Input schema compliance
- Disk space and memory availability

### 3. PipelineValidator

Post-processing validation that verifies:
- Record count preservation
- Unique case count preservation
- No merge artifact duplicates
- All corrections applied
- Quality scores present and valid
- Audit trail completeness
- File integrity via hashing

### 4. Utility Modules

**logger.py**: Structured, rotating logs with multiple output formats
**hash_utils.py**: SHA256 file hashing for integrity verification
**validate_schema.py**: DataFrame schema validation against expected structure

## Validation Workflow

The framework runs three validation phases:

### Phase 1: Pre-Processing Validation
```
✓ Environment checks
✓ Dependency verification
✓ File existence
✓ Configuration validation
✓ Schema compliance
✓ Resource availability
```

### Phase 2: Processing Pipeline
```
→ Load data
→ Apply corrections
→ Extract fields
→ Detect duplicates
→ Calculate quality scores
→ Flag for manual review
→ Export results
```

### Phase 3: Post-Processing Validation
```
✓ Record count preserved
✓ Unique cases preserved
✓ Corrections applied (100%)
✓ Quality scores valid
✓ Duplicates flagged
✓ Audit trail complete
✓ File integrity verified
```

## Quality Scoring

Each record receives a quality score (0-100) based on:

| Component | Weight | Criteria |
|-----------|--------|----------|
| Case Number | 20 | ReportNumberNew present |
| Address | 20 | FullAddress2 present |
| Call Time | 10 | Time of Call present |
| Dispatch Time | 10 | Time Dispatched present |
| Officer | 20 | Officer assigned |
| Disposition | 10 | Disposition present |
| Incident Type | 10 | Incident present |

**Quality Tiers:**
- High Quality: 80-100 points
- Medium Quality: 50-79 points
- Low Quality: 0-49 points

## Audit Trail

All field-level changes are recorded in `data/audit/audit_log.csv`:

```csv
timestamp,case_number,field,old_value,new_value,correction_type
2025-11-24T10:30:00,24-123456,FullAddress2,123 MAIN ST,123 MAIN STREET,manual_address
2025-11-24T10:30:01,24-123457,How Reported,911,9-1-1,how_reported_standardization
```

## Manual Review Workflow

Records flagged for manual review are exported to `data/manual_review/flagged_records.xlsx`:

**Flagging Criteria:**
- Unknown addresses (UNKNOWN, UNK, N/A, NULL)
- Missing case numbers
- Quality score below threshold
- Suspicious duplicates
- Invalid time values

## Error Handling

The framework includes comprehensive error handling:

```python
error_handling:
  on_validation_error: "warn"   # halt, warn, ignore
  on_processing_error: "warn"
  on_export_error: "halt"
  max_retries: 3
  create_backup: true
```

## Logging

Logs are written to `logs/cad_processing.log` with rotation:

```
2025-11-24 10:30:15 | INFO     | CADDataProcessor | Loading CAD Data
2025-11-24 10:30:16 | INFO     | CADDataProcessor | Loaded 728,593 records
2025-11-24 10:30:17 | INFO     | CADDataProcessor | Applying manual corrections
2025-11-24 10:30:20 | INFO     | CADDataProcessor | Applied 9,607 corrections
```

**Log Levels:**
- `DEBUG`: Detailed diagnostic information
- `INFO`: General information about processing
- `WARNING`: Warning messages (processing continues)
- `ERROR`: Error messages (may halt processing)
- `CRITICAL`: Critical errors (halt processing)

## File Integrity

SHA256 hashes are recorded in `data/audit/hash_manifest.json`:

```json
{
  "version": "1.0",
  "files": {
    "input_20251124": {
      "hash": "a3f2b1c9...",
      "size_bytes": 156789012,
      "stage": "input",
      "timestamp": "2025-11-24T10:30:00"
    },
    "output_20251124": {
      "hash": "d7e4c2a1...",
      "size_bytes": 156790123,
      "stage": "output",
      "timestamp": "2025-11-24T10:45:00"
    }
  }
}
```

## Troubleshooting

### Common Issues

**1. Schema Validation Fails**
- Check that input file has all required columns
- Review validation errors in log file
- Use `--validate-only` to diagnose without processing

**2. Memory Errors**
- Reduce `chunk_size` in config
- Enable `use_dask` for large datasets
- Close other applications to free memory

**3. Corrections Not Applied**
- Verify correction file paths in config
- Check correction CSV format (must have required columns)
- Review audit trail to see what was applied

**4. Quality Scores All Zero**
- Ensure quality weights sum to 100 in config
- Check that required fields are present in data
- Review log for quality score calculation messages

## Performance

The framework is optimized for large datasets:

- **Chunk Processing**: Processes data in configurable chunks
- **Dask Integration**: Optional parallel processing with Dask
- **Memory Management**: Efficient dtype optimization
- **Batch Operations**: Vectorized pandas operations

**Typical Performance (728K records):**
- Loading: ~30 seconds
- Corrections: ~2 minutes
- Quality Scoring: ~10 seconds
- Export: ~45 seconds
- **Total: ~4 minutes**

## Testing

### Test Mode

Process a small subset for testing:

```bash
python main.py --test-mode
```

This samples 1,000 records (configurable in `config.yml`):

```yaml
development:
  test_mode: true
  test_sample_size: 1000
  test_random_seed: 42
```

### Unit Testing

Individual components can be tested:

```python
# Test logger
python -m utils.logger

# Test hash utilities
python -m utils.hash_utils

# Test schema validator
python -m utils.validate_schema
```

## Command-Line Options

```
usage: main.py [-h] [--config CONFIG] [--validate-only] [--test-mode]
               [--skip-validation] [--skip-post-validation]

CAD Data Correction Framework - Production-safe correction system

optional arguments:
  -h, --help            Show help message
  --config CONFIG       Path to configuration file
  --validate-only       Run validation checks only
  --test-mode           Process subset of data
  --skip-validation     Skip pre-processing validation (NOT RECOMMENDED)
  --skip-post-validation Skip post-processing validation
```

## Best Practices

1. **Always run validation first**: Use `--validate-only` to check before processing
2. **Test with small samples**: Use `--test-mode` before full production runs
3. **Review audit trails**: Check what corrections were applied
4. **Monitor logs**: Watch for warnings and errors
5. **Verify hashes**: Ensure input file hasn't been corrupted
6. **Backup data**: Keep backups before major processing runs
7. **Review flagged records**: Check manual review exports for data quality issues

## Support and Documentation

- **Full Documentation**: See `README.md` and `IMPLEMENTATION_SUMMARY.md`
- **Configuration Reference**: See inline comments in `config/config.yml`
- **API Documentation**: See docstrings in module files
- **Validation Rules**: See `doc/validation_rules_summary.md`

## Version History

**v1.0.0** (2025-11-24)
- Initial release of modular framework
- Complete validation harness
- Audit trail support
- Quality scoring system
- Duplicate detection
- File integrity verification

## License

Internal use only - Hackensack Police Department

## Contact

For questions or issues, contact the Data Analytics team.

---

**Generated by CAD Data Correction Framework v1.0.0**
