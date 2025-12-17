# Next Actions - CAD Data Validation & Processing

**Date Created**: December 17, 2025  
**Status**: Ready to Execute  
**Priority**: High

---

## 🎯 Objectives

1. **Verify & Fix ESRI Final File** using the corrected high-performance validator
2. **Process Updated CAD Export** (full 2019-2025 dataset)
3. **Generate Production-Ready Output** for ESRI submission

---

## 📋 Action Plan

### Phase 1: Validate ESRI Final File (Current Production File)

#### Step 1.1: Run High-Performance Validation

**File**: `CAD_ESRI_Final_20251124_COMPLETE.csv`  
**Records**: 702,352  
**Expected Time**: ~15 seconds

```bash
cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"
python validate_cad_export_parallel.py
```

**Note**: Script will automatically:
- Load the file specified in the script (update path if needed)
- Run all validation rules with index alignment fix
- Generate cleaned output
- Create validation reports

#### Step 1.2: Review Validation Results

Check these output files:
- `CAD_VALIDATION_SUMMARY.txt` - Overall statistics and error summary
- `CAD_VALIDATION_ERRORS.csv` - Detailed error log
- `CAD_VALIDATION_FIXES.csv` - Applied fixes log
- `CAD_CLEANED.csv` - Cleaned dataset output

**Key Metrics to Review**:
- Total errors found
- Rows with errors (percentage)
- Errors by field (Incident, Disposition, How Reported, etc.)
- Auto-fixes applied

#### Step 1.3: Analyze Issues

**Expected Issues** (based on previous validation):

| Issue | Expected Count | Severity | Action Required |
|-------|---------------|----------|----------------|
| **Incident missing " - " separator** | ~654K | ⚠️ Business Rule | Review if separator is actually required |
| **Disposition invalid values** | ~26K | 🔴 Data Quality | Review and map to valid domain |
| **How Reported invalid values** | ~400 | 🟡 Minor | Case normalization auto-fixes most |
| **ReportNumberNew format issues** | ~32 | 🔴 Critical | Manual review required |
| **PDZone invalid** | ~3 | 🟡 Minor | Can backfill from RMS |

#### Step 1.4: Decision Points

**For Incident Field** (~654K errors):
- [ ] **Option A**: Relax validation rule (incidents don't need " - " separator)
- [ ] **Option B**: Apply incident type prefixes (requires mapping table)
- [ ] **Option C**: Backfill from RMS where available (as mentioned in email)

**For Disposition** (~26K errors):
- [ ] Review invalid values in `Invalid_Disposition_Values.csv`
- [ ] Create mapping rules for common variants
- [ ] Apply to dataset and re-validate

**For ReportNumberNew** (~32 errors):
- [ ] Review specific records in error log
- [ ] Determine if they can be fixed or should be excluded
- [ ] Apply fixes if possible

---

### Phase 2: Process Updated CAD Export (Full 2019-2025 Dataset)

#### Step 2.1: Prepare for Full Processing

**File**: `2019_2025_12_14_All_CAD.csv`  
**Expected Records**: 1,355,164 (based on line count)  
**Expected Time**: ~23 seconds with optimized script

**Pre-flight Checks**:
- [ ] Verify file integrity (not corrupted)
- [ ] Check available disk space (need ~2GB for outputs)
- [ ] Ensure memory available (8GB+ recommended)
- [ ] Backup original file if not already backed up

#### Step 2.2: Update Validation Script for CSV Input

The current script is configured for `.xlsx` files. Update `validate_cad_export_parallel.py`:

```python
# Current (line ~582):
input_file = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\CAD_ESRI_Final_20251124_COMPLETE.xlsx")

# Change to:
input_file = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\data\2019_2025_12_14_All_CAD.csv")

# And update the load method (line ~599):
# Current:
df = pd.read_excel(input_file, dtype=str)

# Change to:
df = pd.read_csv(input_file, dtype=str, encoding='utf-8-sig')
```

**Or create a new script**: `validate_cad_export_parallel_csv.py`

#### Step 2.3: Run Full Validation

```bash
python validate_cad_export_parallel.py
# Expected duration: ~23 seconds for 1.35M records
```

#### Step 2.4: Review Full Dataset Results

**Output Files** (with _FULL suffix to distinguish):
- `CAD_CLEANED_FULL.csv` - Cleaned 1.35M records
- `CAD_VALIDATION_SUMMARY_FULL.txt` - Full validation report
- `CAD_VALIDATION_ERRORS_FULL.csv` - All errors
- `CAD_VALIDATION_FIXES_FULL.csv` - All fixes applied

**Analysis Questions**:
1. How does error rate compare to ESRI file?
2. Are there new error patterns in the additional records?
3. What percentage of records have critical errors?
4. Can we achieve target quality metrics?

---

### Phase 3: Apply Corrections & Generate Production File

#### Step 3.1: Prioritize Fixes

**Critical (Must Fix)**:
- [ ] ReportNumberNew format errors
- [ ] Invalid TimeOfCall values
- [ ] Completely missing required fields

**Important (Should Fix)**:
- [ ] Invalid Disposition values
- [ ] Invalid How Reported values
- [ ] Address quality issues

**Optional (Review)**:
- [ ] Incident separator requirement
- [ ] Derived field mismatches (auto-fixed)
- [ ] PDZone validation

#### Step 3.2: Apply Corrections

Based on validation results, apply appropriate fixes:

**Option A: Use Cleaned Output**
```bash
# The validator already produces CAD_CLEANED.csv with auto-fixes applied
cp CAD_CLEANED.csv CAD_PRODUCTION_READY_$(date +%Y%m%d).csv
```

**Option B: Apply Additional Manual Corrections**
```python
# Create a correction script based on specific issues found
python scripts/apply_validation_corrections.py \
    --input CAD_CLEANED.csv \
    --corrections-file manual_corrections.csv \
    --output CAD_PRODUCTION_READY.csv
```

**Option C: RMS Backfill**
```python
# Backfill missing/invalid fields from RMS export
python scripts/backfill_from_rms.py \
    --cad-file CAD_CLEANED.csv \
    --rms-file data/rms/HPD_RMS_Export.xlsx \
    --output CAD_PRODUCTION_READY.csv
```

#### Step 3.3: Final Validation

Run validation one more time on corrected file:
```bash
python validate_cad_export_parallel.py
```

**Target Quality Metrics**:
- ✅ Error rate < 5%
- ✅ Critical errors = 0
- ✅ ReportNumberNew: 100% valid format
- ✅ TimeOfCall: 100% valid dates
- ✅ Address completeness: >95%
- ✅ Disposition/How Reported: >98% valid

---

## 🔧 Quick Commands Reference

### Validate ESRI File
```bash
cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"
python validate_cad_export_parallel.py
```

### Validate Full CAD Export (after updating script)
```bash
python validate_cad_export_parallel.py
# Or use dedicated CSV version:
python validate_cad_export_parallel_csv.py
```

### Check File Info
```bash
# Line count
wc -l "data\2019_2025_12_14_All_CAD.csv"

# File size
ls -lh "data\2019_2025_12_14_All_CAD.csv"

# First few lines (headers)
head -5 "data\2019_2025_12_14_All_CAD.csv"
```

### Compare Files
```python
# Quick comparison script
import pandas as pd

esri = pd.read_csv('data/CAD_ESRI_Final_20251124_COMPLETE.csv', nrows=5)
full = pd.read_csv('data/2019_2025_12_14_All_CAD.csv', nrows=5)

print("ESRI columns:", esri.columns.tolist())
print("\nFull columns:", full.columns.tolist())
print("\nMissing in Full:", set(esri.columns) - set(full.columns))
print("Missing in ESRI:", set(full.columns) - set(esri.columns))
```

---

## 📊 Expected Outcomes

### After Phase 1 (ESRI File)
- ✅ Validation report confirms data quality
- ✅ Known issues documented
- ✅ Auto-fixes applied (case normalization, derived fields)
- ✅ Decision made on Incident field requirement
- ✅ Ready for ESRI submission OR corrections identified

### After Phase 2 (Full Dataset)
- ✅ Complete validation of 1.35M records
- ✅ Error patterns identified across full time range
- ✅ Comparison with ESRI file quality
- ✅ New issues (if any) discovered and documented

### After Phase 3 (Production File)
- ✅ Production-ready dataset generated
- ✅ Quality metrics met
- ✅ Documentation complete
- ✅ Ready for ESRI submission or further processing

---

## ⚠️ Important Notes

### Performance
- **ESRI File (702K)**: ~12 seconds
- **Full File (1.35M)**: ~23 seconds (estimated)
- **Both files validated**: ~35 seconds total

### Memory Requirements
- Minimum: 4GB RAM available
- Recommended: 8GB RAM available
- Large file may require 16GB for optimal performance

### Disk Space
- Input files: ~500MB
- Output files: ~1GB (cleaned + logs)
- Total needed: ~2GB free space

### Backup Strategy
- [ ] Original files backed up before processing
- [ ] Validation outputs dated/versioned
- [ ] Production file includes date in filename
- [ ] Git commit before major changes

---

## 📝 Checklist

### Pre-Processing
- [ ] Index alignment bug fix verified in script
- [ ] Script configured for correct input file
- [ ] Backup of original data exists
- [ ] Sufficient disk space available
- [ ] Memory requirements met

### Phase 1: ESRI File
- [ ] Validation run completed
- [ ] Results reviewed
- [ ] Issues documented
- [ ] Decisions made on corrections
- [ ] Fixes applied (if needed)

### Phase 2: Full Dataset  
- [ ] Script updated for CSV input
- [ ] Full validation completed
- [ ] Results compared with ESRI file
- [ ] New patterns identified
- [ ] Quality assessment complete

### Phase 3: Production
- [ ] All corrections applied
- [ ] Final validation passed
- [ ] Quality metrics achieved
- [ ] Documentation updated
- [ ] Production file generated

### Post-Processing
- [ ] Results committed to Git
- [ ] Documentation updated (README, CHANGELOG)
- [ ] Team notified of completion
- [ ] ESRI submission prepared (if applicable)

---

## 🚀 Ready to Start?

**Recommended Sequence**:

1. **Start with ESRI file** (smaller, faster, known baseline)
   ```bash
   python validate_cad_export_parallel.py
   ```

2. **Review results** and make decisions on issues

3. **Update script** for full dataset if needed

4. **Process full dataset** with lessons learned

5. **Generate production file** based on results

---

## 📞 Questions or Issues?

- Script errors? Check `BUGFIX_INDEX_ALIGNMENT.md` for known issues
- Performance issues? See `PERFORMANCE_COMPARISON.md`
- Validation rules? Check field schemas in JSON files
- Business logic? Review `VALIDATION_EXECUTIVE_SUMMARY.md`

**Status**: Ready to execute ✅  
**Next Step**: Run validation on ESRI file (Phase 1, Step 1.1)

