# Master Generation Prompt: CAD Data Correction Framework

## 📋 Single Prompt for Complete Framework Generation

Copy this entire prompt to Claude (or another LLM) to generate the complete CAD Data Correction Framework:

---

## 🎯 PROMPT START

Generate a complete, production-ready, modular CAD Data Correction Framework for a corrupted emergency dispatch dataset (700K+ records) with the following issues:

- **Duplicate corruption** from broken merge logic
- **Partial manual corrections** scattered across multiple CSV files
- **Missing quality scoring** (no data completeness assessment)
- **No audit trail** of changes made
- **Address data corruption** (incomplete, unknown, malformed addresses)

---

## 🏗️ SYSTEM ARCHITECTURE

Build a **7-module framework** with the following structure:

```
CAD_Data_Cleaning_Engine/
├── main.py                              # CLI orchestrator
├── config/
│   └── config.yml                       # YAML configuration
├── processors/
│   ├── __init__.py
│   └── cad_data_processor.py            # Core processor class
├── validators/
│   ├── __init__.py
│   ├── validation_harness.py            # Pre-run validation
│   └── validate_full_pipeline.py        # Post-run validation
├── utils/
│   ├── __init__.py
│   ├── logger.py                        # Structured logging
│   ├── hash_utils.py                    # File integrity (SHA256)
│   └── validate_schema.py               # Schema validation
├── examples/
│   └── basic_usage.py                   # Usage examples
├── logs/
│   └── cad_processing.log               # Auto-generated
├── data/
│   ├── input/                           # Input files
│   ├── output/                          # Corrected data
│   ├── audit/                           # Audit trail + hashes
│   └── manual_review/                   # Flagged records
└── [Documentation files]
```

---

## 📦 MODULE SPECIFICATIONS

### 1. `processors/cad_data_processor.py` (Core Orchestrator)

Create a `CADDataProcessor` class with these methods:

**Initialization**:
- `__init__(config_path: str)`: Load config, initialize logger, hash manager, schema validator

**Data Loading**:
- `load_data(file_path: Optional[str])`: Load Excel/CSV, record input hash, return DataFrame

**Validation**:
- `validate_schema() -> bool`: Check all required columns exist, validate data types

**Correction Methods**:
- `apply_manual_corrections()`: Orchestrate all correction types
  - `_apply_address_corrections() -> int`: Apply from CSV with columns [ReportNumberNew, FullAddress2_corrected]
  - `_apply_disposition_corrections() -> int`: Apply from CSV with columns [ReportNumberNew, Disposition_corrected]
  - `_apply_how_reported_corrections() -> int`: Standardize "How Reported" field (fix Excel date artifacts like "1901" → "9-1-1")
  - `_apply_fulladdress2_corrections() -> int`: Apply rule-based pattern corrections

**Field Extraction**:
- `extract_hour_field()`: Extract HH:mm format from "Time of Call" datetime field

**Call Type Mapping**:
- `map_call_types()`: Map incident types to Fire/Medical/Police categories using CallType_Master_Mapping.csv

**Quality & Duplicates**:
- `detect_duplicates()`: Flag duplicate case numbers and merge artifact patterns
- `calculate_quality_scores()`: Score 0-100 based on field completeness:
  - Case number present: 20 pts
  - Address present: 20 pts
  - Call time present: 10 pts
  - Dispatch time present: 10 pts
  - Officer present: 20 pts
  - Disposition present: 10 pts
  - Incident type present: 10 pts

**Manual Review**:
- `flag_for_manual_review(criteria: Optional[str])`: Flag records based on:
  - Unknown addresses (UNKNOWN, UNK, N/A, NULL)
  - Missing case numbers
  - Quality score < threshold
  - Custom pandas query string

**Pipeline Execution**:
- `run_all_corrections()`: Execute all steps in sequence with error handling

**Export**:
- `export_corrected_data(output_path: Optional[str])`: Write corrected data, audit trail, flagged records
- `_export_audit_trail()`: Write CSV with [timestamp, case_number, field, old_value, new_value, correction_type]
- `_export_flagged_records()`: Write Excel with records for manual review

**Audit Trail**:
- `_record_audit(case_number, field, old_value, new_value, correction_type)`: Track every change

**Reporting**:
- `get_processing_summary() -> Dict`: Return stats (records processed, corrections applied, quality metrics, audit entries)

**Required CAD Schema** (18 columns):
- ReportNumberNew, Incident, Disposition, How Reported, FullAddress2
- PDZone, Grid, Time of Call, Time Dispatched, Time Out, Time In, Hour
- Officer, Time Spent, Time Response, CADNotes, Narrative, Response Type

---

### 2. `validators/validation_harness.py` (Pre-Run Validation)

Create a `ValidationHarness` class that checks:

**Environment Checks**:
- Python version ≥ 3.8
- Operating system info
- Working directory

**Dependency Checks**:
- pandas, numpy, yaml, openpyxl, psutil installed
- Get versions where available

**File Existence Checks**:
- Input file exists and is readable
- Correction files exist (or optional)
- Reference files exist (or optional)

**Configuration Validation**:
- Required config sections present (project, paths, processing, validation, export, logging)
- Quality weights sum to 100
- Log level is valid (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Schema Validation**:
- Load sample of input data (first 100 rows)
- Validate against CAD schema
- Report missing columns and type mismatches

**Resource Checks**:
- Disk space ≥ 5 GB free
- Memory available ≥ 2 GB
- Memory usage < 90%

**Methods**:
- `run_all_validations() -> bool`: Execute all checks, return True if all passed
- `_add_result(check_name, passed, message)`: Track validation results
- `_report_results()`: Print summary of passed/failed checks
- `get_validation_report() -> Dict`: Return structured validation results

**Standalone Usage**:
- Support command-line execution: `python -m validators.validation_harness --config config/config.yml`

---

### 3. `validators/validate_full_pipeline.py` (Post-Run Validation)

Create a `PipelineValidator` class that verifies:

**Data Integrity**:
- `_check_record_count_preserved()`: Input count == Output count
- `_check_unique_cases_preserved()`: Unique case numbers preserved
- `_check_no_merge_artifacts()`: No duplicate case numbers, no merge patterns in data

**Correction Verification**:
- `_check_corrections_applied()`: Audit trail has expected entries
- `_check_hour_field_normalized()`: Hour field populated and in HH:mm format

**Quality Validation**:
- `_check_quality_scores()`: All records have scores, range is 0-100, calculate distribution

**Output Validation**:
- `_check_utf8_bom()`: UTF-8 BOM present (if configured for CSV)
- `_check_audit_trail()`: Audit file exists, has required columns, has entries
- `_check_duplicates_flagged()`: duplicate_flag column present
- `_check_data_integrity()`: Hash verification using hash manifest

**Methods**:
- `run_all_validations() -> bool`: Execute all checks, return True if all passed
- `_load_data() -> bool`: Load input, output, audit files
- `get_validation_report() -> Dict`: Return structured validation results

**Standalone Usage**:
- Support command-line execution with --input, --output, --audit, --config flags

---

### 4. `utils/logger.py` (Structured Logging)

Provide these functions:

- `setup_logger(name, log_file, level, max_bytes, backup_count, console_output) -> Logger`:
  - Create logger with RotatingFileHandler
  - Format: `%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s`
  - Console format: `%(asctime)s | %(levelname)-8s | %(message)s`
  - Create logs directory if needed

- `log_dataframe_info(logger, df, name)`: Log DataFrame shape, memory, columns, null counts

- `log_processing_step(logger, step_name, details)`: Log processing step with optional details dict

- `log_validation_result(logger, validation_name, passed, message)`: Log validation result with status

- `log_correction_summary(logger, correction_type, records_affected, details)`: Log correction summary

- `log_error_with_context(logger, error, context)`: Log error with context info

---

### 5. `utils/hash_utils.py` (File Integrity)

Create a `FileHashManager` class:

**Methods**:
- `__init__(manifest_path)`: Initialize with path to hash_manifest.json
- `compute_file_hash(file_path, algorithm='sha256') -> str`: Compute file hash
- `record_file_hash(file_path, stage, metadata) -> str`: Compute and record hash in manifest
- `verify_file_hash(file_path, expected_hash) -> bool`: Verify file hash matches
- `compare_files(file1, file2) -> bool`: Compare two files by hash
- `get_file_history(file_name) -> List[Dict]`: Get all hash records for a file
- `detect_changes(file_path, stage) -> Optional[Dict]`: Check if file changed since last record
- `generate_integrity_report() -> str`: Generate formatted integrity report
- `export_manifest(output_path)`: Export manifest to different location

**Manifest Format** (JSON):
```json
{
  "version": "1.0",
  "files": {
    "filename_stage_timestamp": {
      "hash": "sha256_hash",
      "algorithm": "sha256",
      "size_bytes": 12345,
      "stage": "input|output",
      "timestamp": "2025-11-24T10:30:00",
      "path": "/full/path/to/file",
      "metadata": {}
    }
  },
  "last_updated": "2025-11-24T10:30:00"
}
```

**Convenience Functions**:
- `compute_hash(file_path) -> str`
- `verify_integrity(file_path, expected_hash) -> bool`

---

### 6. `utils/validate_schema.py` (Schema Validation)

Create a `SchemaValidator` class:

**Components**:
- `DataType` enum: STRING, INTEGER, FLOAT, DATETIME, BOOLEAN, OBJECT

- `CAD_SCHEMA` dict with format:
  ```python
  {
    "ColumnName": {
      "type": DataType.STRING,
      "nullable": True/False,
      "description": "Field description"
    }
  }
  ```

**Methods**:
- `__init__(schema, strict)`: Initialize with schema (use CAD_SCHEMA by default)
- `validate(df) -> bool`: Validate DataFrame against schema
- `_check_required_columns(df) -> List[str]`: Check all schema columns present
- `_check_data_types(df) -> List[str]`: Validate column data types
- `_check_nullable_constraints(df) -> List[str]`: Check nullable constraints
- `_check_extra_columns(df) -> List[str]`: Find columns not in schema
- `_is_type_compatible(actual_dtype, expected_type) -> bool`: Check type compatibility
- `get_validation_report() -> Dict`: Return structured validation results

**Convenience Functions**:
- `validate_cad_schema(df, strict) -> bool`
- `create_custom_schema(field_definitions) -> Dict`

---

### 7. `main.py` (CLI Orchestrator)

Create command-line interface with these options:

**Arguments**:
- `--config PATH`: Path to config file (default: config/config.yml)
- `--validate-only`: Run validation checks only, no processing
- `--test-mode`: Process sample of data (size from config)
- `--skip-validation`: Skip pre-validation (not recommended)
- `--skip-post-validation`: Skip post-validation

**Workflow**:
1. Print header with version, config path, timestamp, mode
2. Verify config file exists
3. **Phase 1**: Run `validation_harness` (unless skipped)
   - If fails in non-skip mode, exit with error
4. **Phase 2**: Run correction pipeline (unless validate-only mode)
   - Initialize `CADDataProcessor`
   - Load data (sample if test-mode)
   - Run `run_all_corrections()`
   - Export results
   - Print summary
5. **Phase 3**: Run `validate_full_pipeline` (unless skipped)
   - If fails, print warning but don't error (data was processed)
6. Print final summary with output file paths

**Error Handling**:
- Try/except around each phase
- Print clear error messages
- Exit with appropriate code (0 = success, 1 = failure)

---

## ⚙️ CONFIGURATION FILE (`config/config.yml`)

Create comprehensive YAML config with these sections:

### 1. **project**: Metadata
```yaml
project:
  name: "CAD Data Correction Framework"
  version: "1.0.0"
  description: "Production-safe correction system for corrupted emergency CAD data"
```

### 2. **paths**: All file paths
```yaml
paths:
  input_file: "data/input/CAD_Data.xlsx"
  output_file: "data/output/CAD_CLEANED.xlsx"

  corrections:
    address: "data/manual_corrections/address_corrections.csv"
    disposition: "data/manual_corrections/disposition_corrections.csv"
    how_reported: "data/manual_corrections/how_reported_corrections.csv"
    fulladdress2: "data/manual_corrections/fulladdress2_corrections.csv"
    street_names: "ref/hackensack_municipal_streets.xlsx"

  reference:
    call_type_master: "ref/CallType_Master_Mapping.csv"
    call_type_categories: "ref/CallType_Categories.csv"
    rms_export: "data/rms/RMS_Export.xlsx"

  log_file: "logs/cad_processing.log"
  audit_file: "data/audit/audit_log.csv"
  hash_manifest: "data/audit/hash_manifest.json"

  manual_review_dir: "data/manual_review"
  manual_review_file: "data/manual_review/flagged_records.xlsx"
```

### 3. **processing**: Processing options
```yaml
processing:
  apply_address_corrections: true
  apply_disposition_corrections: true
  apply_how_reported_corrections: true
  apply_call_type_mapping: true
  extract_hour_field: true
  normalize_addresses: true
  parse_officer_info: true
  clean_narratives: true
  detect_duplicates: true
  flag_merge_artifacts: true

  chunk_size: 10000
  use_dask: false
  n_workers: 4
```

### 4. **validation**: Validation settings
```yaml
validation:
  validate_schema: true
  strict_schema: false
  check_record_count: true
  check_case_numbers: true
  check_duplicate_cases: true
  require_quality_scores: true
  require_audit_trail: true
  check_utf8_bom: true
  verify_corrections_applied: true
  verify_hash_integrity: true
```

### 5. **quality_weights**: Scoring weights (must sum to 100)
```yaml
quality_weights:
  case_number_present: 20
  address_present: 20
  call_time_present: 10
  dispatch_time_present: 10
  officer_present: 20
  disposition_present: 10
  incident_type_present: 10
```

### 6. **manual_review_criteria**: Flagging rules
```yaml
manual_review_criteria:
  flag_unknown_addresses: true
  flag_missing_case_numbers: true
  flag_low_quality_scores: true
  flag_suspicious_duplicates: true
  flag_invalid_times: true

  low_quality_threshold: 30

  address_patterns_to_flag:
    - "UNKNOWN"
    - "UNK"
    - "N/A"
    - "NULL"
    - "NONE"
    - "?"
```

### 7. **field_mappings**: Field standardization
```yaml
field_mappings:
  how_reported:
    patterns:
      "9-1-1": ["911", "9-1-1", "9/1/1", "E911", "1901", "September 1"]
      "PHONE": ["PHONE", "TEL", "TELEPHONE"]
      "WALK-IN": ["WALK-IN", "WALK IN", "IN PERSON"]
      "SELF-INITIATED": ["SELF-INITIATED", "OFFICER INITIATED", "OI", "SI"]

  disposition:
    patterns:
      "See Report": ["sees Report", "sees report", "See report"]
      "GOA": ["goa"]
      "UTL": ["utl"]
```

### 8. **export**: Output options
```yaml
export:
  format: "xlsx"

  excel:
    include_utf8_bom: true
    engine: "openpyxl"
    freeze_panes: "A2"

  csv:
    encoding: "utf-8-sig"
    sep: ","
    quoting: 1

  export_audit_trail: true
  export_flagged_records: true
  export_quality_report: true
```

### 9. **logging**: Logging configuration
```yaml
logging:
  level: "INFO"
  format: "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
  date_format: "%Y-%m-%d %H:%M:%S"
  max_log_size_mb: 10
  backup_count: 5
  console_output: true
```

### 10. **development**: Test/debug options
```yaml
development:
  test_mode: false
  test_sample_size: 1000
  test_random_seed: 42
  debug_mode: false
  verbose_logging: false
  save_intermediate_files: false
```

---

## 📚 DOCUMENTATION FILES

Generate these markdown documentation files:

### 1. `FRAMEWORK_README.md` (500-600 lines)
- Complete technical documentation
- Overview and features
- Directory structure
- Installation instructions
- Quick start guide
- Core component descriptions
- Configuration reference
- Usage examples
- Validation workflow
- Quality scoring explanation
- Audit trail format
- Output file descriptions
- Troubleshooting guide
- Performance tuning
- Best practices

### 2. `QUICK_START.md` (200-300 lines)
- 5-minute getting started guide
- Installation (1 command)
- Configuration (what to edit)
- Validation (run checks)
- Test mode (sample data)
- Full run (production)
- Output files overview
- Common tasks (simple examples)
- Troubleshooting quick reference

### 3. `DEPLOYMENT_GUIDE.md` (400-500 lines)
- Production deployment instructions
- Complete directory structure with descriptions
- Detailed installation steps
- Configuration guide
- Full workflow explanation (3 phases)
- Core module details
- Validation details
- Output file formats
- Performance optimization
- Common customizations
- Troubleshooting (detailed)
- Advanced usage examples
- Security & data safety
- Pre-deployment checklist
- Command reference

### 4. `FRAMEWORK_SUMMARY.md` (150-200 lines)
- High-level overview
- Complete file inventory
- Framework capabilities table
- Processing pipeline diagram
- Quick start commands
- Output files summary
- Quality scoring breakdown
- Safety features
- Documentation reference
- Framework statistics
- Key features summary

---

## 🧪 EXAMPLES FILE

Create `examples/basic_usage.py` with 8 complete examples:

1. **example_1_basic_pipeline()**: Run complete pipeline with default config
2. **example_2_validation_only()**: Run validation checks without processing
3. **example_3_custom_corrections()**: Apply specific corrections only
4. **example_4_manual_review_query()**: Flag records with custom criteria
5. **example_5_post_validation()**: Validate pipeline output
6. **example_6_batch_processing()**: Process data in chunks
7. **example_7_audit_trail_analysis()**: Analyze audit trail after processing
8. **example_8_quality_metrics()**: Analyze quality score distribution

Each example should be complete, runnable, and demonstrate a specific use case.

---

## 🔧 ADDITIONAL FILES

### 1. `verify_framework.py` (200-250 lines)
Create a verification script that checks:
- Python version
- Dependencies installed
- Directory structure complete
- Core files exist
- Modules can be imported
- Config file is valid YAML
- Basic functionality works

Print colored output (✓ for pass, ✗ for fail) and final summary.

### 2. `framework_requirements.txt`
List all Python dependencies:
```
pandas>=1.5.0
numpy>=1.23.0
openpyxl>=3.0.10
PyYAML>=6.0
psutil>=5.9.0
pydantic>=2.0.0
dask[complete]>=2023.1.0  # Optional
tqdm>=4.65.0  # Optional
pytest>=7.3.0
```

### 3. `__init__.py` files
Create package initialization files for:
- `processors/__init__.py`: Import CADDataProcessor
- `validators/__init__.py`: Import ValidationHarness, PipelineValidator
- `utils/__init__.py`: Import all utility functions

---

## ✅ SUCCESS CRITERIA

The generated framework must:

1. **Be modular**: Each component independently functional and testable
2. **Be production-safe**:
   - No in-place data modification
   - Complete audit trail
   - File integrity verification
   - Record count preservation guaranteed
3. **Be fault-tolerant**:
   - 40+ validation checks (pre and post)
   - Comprehensive error handling
   - Graceful failures with clear messages
4. **Be well-documented**:
   - 4 documentation files (1,500+ lines total)
   - Inline docstrings for all functions
   - 8 usage examples
5. **Be configurable**:
   - All behavior controlled via YAML
   - No hardcoded paths or values
6. **Be auditable**:
   - Every change tracked with before/after values
   - Timestamp and correction type recorded
   - Exportable audit trail
7. **Handle 700K+ records efficiently**:
   - Process in ~5 minutes
   - Chunk-based processing
   - Memory-efficient operations

---

## 📊 EXPECTED OUTPUT

After generation, the framework should:

1. **Process 728,593 records** in ~4-5 minutes
2. **Apply ~14,000 corrections** from manual correction files
3. **Calculate quality scores** averaging 85-90/100
4. **Flag ~17,000 records** for manual review
5. **Detect ~170 duplicates** (merge artifacts)
6. **Generate 5 output files**:
   - Corrected data (Excel)
   - Audit trail (CSV)
   - Flagged records (Excel)
   - Hash manifest (JSON)
   - Processing log (text)

---

## 🎯 VALIDATION WORKFLOW

The framework must implement this 3-phase workflow:

**Phase 1: Pre-Validation** (30 seconds)
- Environment checks (Python, dependencies)
- File existence checks
- Configuration validation
- Schema compliance
- Resource checks (disk, memory)
- EXIT if critical failures

**Phase 2: Processing** (4 minutes)
- Load data + record hash
- Validate schema
- Apply all corrections
- Extract hour field
- Map call types
- Detect duplicates
- Calculate quality scores
- Flag for manual review
- Export all outputs
- Record output hash

**Phase 3: Post-Validation** (30 seconds)
- Record count preserved
- Corrections applied
- Quality scores valid
- Audit trail complete
- Hash integrity verified
- WARN if non-critical failures

---

## 💡 IMPLEMENTATION NOTES

1. **Use pandas** for all data manipulation (not Dask by default)
2. **Use openpyxl** for Excel I/O
3. **Use PyYAML** for config loading
4. **Use logging module** with RotatingFileHandler
5. **Use hashlib** for SHA256 hashing
6. **Use pathlib.Path** for all file path operations
7. **Use type hints** for all function signatures
8. **Use docstrings** (Google or NumPy style) for all functions
9. **Follow PEP 8** style guidelines
10. **Handle Windows paths** (framework runs on Windows)

---

## 🚀 FINAL DELIVERABLE

Generate a complete, ready-to-run framework with:

- ✅ **7 core modules** (2,650 lines)
- ✅ **4 documentation files** (1,600 lines)
- ✅ **1 config file** (250 lines)
- ✅ **1 examples file** (400 lines)
- ✅ **1 verification script** (250 lines)
- ✅ **3 __init__.py files**
- ✅ **1 requirements.txt**

**Total**: ~18 files, 3,500+ lines of production code + documentation

The framework should be immediately usable by running:
```bash
pip install -r framework_requirements.txt
python verify_framework.py
python main.py --validate-only
python main.py --test-mode
python main.py
```

---

## 🎯 PROMPT END

---

## 📝 Usage Instructions

**To use this prompt:**

1. Copy everything between "PROMPT START" and "PROMPT END"
2. Paste into Claude (or another LLM)
3. The AI will generate all 18 files with complete implementations
4. Review and test the generated framework
5. Customize config.yml for your specific paths

**Expected generation time**: 10-15 minutes (depending on AI)

**Result**: Complete, production-ready CAD Data Correction Framework
