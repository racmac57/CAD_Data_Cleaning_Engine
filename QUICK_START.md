# CAD Data Correction Framework - Quick Start Guide

> **Note**: For the complete ETL pipeline (validation, RMS backfill, geocoding, ESRI output), see `doc/ETL_PIPELINE_REFINEMENT.md` and use `scripts/master_pipeline.py`.

## 🚀 Getting Started in 5 Minutes

### Step 1: Install Dependencies

```bash
pip install -r framework_requirements.txt
```

### Step 2: Configure Your Paths

Edit `config/config.yml` and set your input file:

```yaml
paths:
  input_file: "data/ESRI_CADExport/CAD_ESRI_Final_20251117_v3.xlsx"
  output_file: "data/output/CAD_CLEANED.xlsx"
```

### Step 3: Run Validation

Test that everything is configured correctly:

```bash
python main.py --validate-only
```

You should see:
```
✓ ALL VALIDATIONS PASSED - Ready to run pipeline
```

### Step 4: Test with Sample Data

Run in test mode (processes 1,000 records):

```bash
python main.py --test-mode
```

### Step 5: Run Full Pipeline

Process all data:

```bash
python main.py
```

## 📊 What Happens During Processing?

The framework runs three phases automatically:

### Phase 1: Pre-Validation ✓
- Checks Python environment
- Verifies all files exist
- Validates configuration
- Checks schema compliance
- Verifies disk space and memory

### Phase 2: Processing Pipeline →
- Loads CAD data
- Applies manual corrections
- Extracts hour field (HH:mm)
- Maps call types
- Detects duplicates
- Calculates quality scores (0-100)
- Flags records for manual review
- Exports corrected data

### Phase 3: Post-Validation ✓
- Verifies record count preserved
- Checks corrections applied
- Validates quality scores
- Confirms audit trail complete
- Verifies file integrity

## 📁 Output Files

After processing, check these files:

```
data/output/CAD_CLEANED.xlsx           # Corrected CAD data
data/audit/audit_log.csv               # All changes made
data/manual_review/flagged_records.xlsx # Records needing review
logs/cad_processing.log                # Processing logs
data/audit/hash_manifest.json          # File integrity hashes
```

## 🎯 Common Tasks

### Check Processing Statistics

```python
from processors.cad_data_processor import CADDataProcessor

processor = CADDataProcessor()
processor.load_data()
processor.run_all_corrections()

summary = processor.get_processing_summary()
print(f"Records: {summary['processing_stats']['records_output']:,}")
print(f"Corrections: {summary['processing_stats']['corrections_applied']:,}")
print(f"Quality: {summary['quality_metrics']['average_quality_score']:.1f}/100")
```

### Apply Only Specific Corrections

```python
processor = CADDataProcessor()
processor.load_data()

# Apply only address corrections
processor._apply_address_corrections()

# Calculate quality scores
processor.calculate_quality_scores()

# Export
processor.export_corrected_data()
```

### Flag Records with Custom Criteria

```python
processor = CADDataProcessor()
processor.load_data()

# Flag records with unknown addresses
processor.flag_for_manual_review(
    "FullAddress2.str.contains('UNKNOWN', case=False, na=False)"
)

processor._export_flagged_records()
```

## ⚙️ Configuration Tips

### Enable Geocoding

```yaml
geocoding:
  enabled: true
  locator_path: "path/to/locator"
```

### Adjust Quality Scoring Weights

```yaml
quality_weights:
  case_number_present: 20
  address_present: 25      # Increased importance
  call_time_present: 10
  officer_present: 15
  # ... (total must = 100)
```

### Enable Debug Logging

```yaml
logging:
  level: "DEBUG"  # Change from INFO to DEBUG
  verbose_logging: true
```

## 🔍 Troubleshooting

### "Schema validation failed"
→ Check that input file has all required columns:
- ReportNumberNew
- Incident
- Disposition
- How Reported
- FullAddress2
- Time of Call
- Officer

### "Memory error during processing"
→ Reduce chunk size in config:
```yaml
processing:
  chunk_size: 5000  # Reduce from 10000
```

### "Corrections file not found"
→ Create manual correction CSV files or disable:
```yaml
processing:
  apply_address_corrections: false  # Disable if no file
```

### "No records flagged for manual review"
→ This is normal if your data quality is high. Lower threshold:
```yaml
manual_review_criteria:
  low_quality_threshold: 50  # Increase from 30
```

## 📚 Next Steps

1. **Review the audit trail**: Check `data/audit/audit_log.csv` to see all changes
2. **Inspect flagged records**: Review `data/manual_review/flagged_records.xlsx`
3. **Analyze quality metrics**: Look at quality score distribution
4. **Check logs**: Review `logs/cad_processing.log` for detailed processing info

## 🆘 Getting Help

- **Full documentation**: See `FRAMEWORK_README.md`
- **API reference**: See docstrings in code files
- **Configuration reference**: See inline comments in `config/config.yml`
- **Examples**: See `examples/basic_usage.py`

## ✅ Validation Checklist

Before running in production:

- [ ] Input file path is correct
- [ ] All correction files exist (or disabled in config)
- [ ] Output directory is writable
- [ ] Sufficient disk space (5+ GB free)
- [ ] Sufficient memory (2+ GB available)
- [ ] Tested in --test-mode successfully
- [ ] Reviewed configuration settings
- [ ] Backed up original data

## 🎓 Key Concepts

**Quality Score**: 0-100 point score based on data completeness
**Audit Trail**: Complete record of all field-level changes
**Manual Review**: Records flagged for human verification
**Duplicate Flag**: Records identified as potential duplicates
**Hash Manifest**: SHA256 hashes for file integrity verification

---

**Ready to process your CAD data? Run:**

```bash
python main.py
```

**Questions? Check `FRAMEWORK_README.md` for detailed documentation.**
