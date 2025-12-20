// 2025-12-19-15-30-00
// CAD_Data_Cleaning_Engine/CURSOR_IMPLEMENTATION_GUIDE
// Author: R. A. Carucci
// Purpose: Step-by-step guide for implementing geocoding performance optimizations

# Geocoding Optimization - Implementation Guide for Cursor AI

## Overview

This guide provides step-by-step instructions to implement **3-4x geocoding speedup** through parallel processing and batch optimization.

**Current Performance**: ~5,000 addresses/minute (sequential)  
**Target Performance**: ~18,000-24,000 addresses/minute (parallel)  
**Expected Speedup**: 3.5-4.5x faster

---

## STEP 1: Replace Geocoding Script (5 minutes)

### Action Required

**Replace** the existing `scripts/geocode_nj_locator.py` with the optimized version.

### Files to Replace

```
FROM: scripts/geocode_nj_locator.py (current version)
TO:   scripts/geocode_nj_locator_optimized.py (new optimized version)
```

### Option A: Direct Replacement (Recommended)

```bash
# Backup current version
mv scripts/geocode_nj_locator.py scripts/geocode_nj_locator_backup.py

# Copy optimized version
cp geocode_nj_locator_optimized.py scripts/geocode_nj_locator.py
```

### Option B: Keep Both Versions

```bash
# Keep both versions for comparison
# Current: scripts/geocode_nj_locator.py
# Optimized: scripts/geocode_nj_locator_optimized.py

# Update batch files to use optimized version
```

---

## STEP 2: Update Batch Files (2 minutes)

### Replace run_geocoding_local.bat

**Current content:**
```batch
python scripts/geocode_nj_locator.py ^
    --batch-size 1000
```

**New optimized content:**
```batch
python scripts/geocode_nj_locator_optimized.py ^
    --batch-size 5000 ^
    --max-workers 4 ^
    --executor-type process
```

**OR** use the new optimized batch file:
```bash
scripts/run_geocoding_local_OPTIMIZED.bat
```

---

## STEP 3: Update Requirements (Optional, 1 minute)

### Add tqdm for Progress Bars

Add to `requirements.txt`:
```
tqdm>=4.65.0
```

Install:
```bash
pip install tqdm
```

**Note**: tqdm is optional. Script works without it but progress bars are nicer.

---

## STEP 4: Test on Small Sample (10 minutes)

### Create Test Dataset

```python
import pandas as pd

# Load full dataset
df = pd.read_excel('data/ESRI_CADExport/CAD_ESRI_POLISHED_20251219_131114.xlsx')

# Create 1000-record sample
df_sample = df.sample(n=1000, random_state=42)
df_sample.to_excel('data/test_sample_1000.xlsx', index=False)
```

### Run Quick Benchmark

```bash
python test_geocoding_performance.py ^
    --input "data/test_sample_1000.xlsx" ^
    --locator "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc" ^
    --quick
```

**Expected Output:**
```
Baseline:  ~0.5 min, ~2,000 addr/min
Optimized: ~0.15 min, ~6,000 addr/min
Speedup: ~3x faster
```

---

## STEP 5: Run Full Geocoding (Production)

### Execute Optimized Geocoding

```bash
# Option 1: Use optimized batch file
scripts\run_geocoding_local_OPTIMIZED.bat

# Option 2: Direct command
python scripts/geocode_nj_locator_optimized.py ^
    --input "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx" ^
    --locator "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc" ^
    --format excel ^
    --batch-size 5000 ^
    --max-workers 4
```

### Expected Results

**Your Dataset:**
- Total records: 710,626
- Records needing geocoding: ~82,717
- **Unique addresses**: ~17,676

**Sequential (Current):**
- Time: ~3.5 minutes
- Rate: ~5,000 addr/min

**Parallel (Optimized):**
- Time: ~45-60 seconds
- Rate: ~18,000-24,000 addr/min
- **Time saved: 2.5-3 minutes**

---

## STEP 6: Verify Results (5 minutes)

### Check for Duplicates

The optimized script includes duplicate prevention (line 348), but verify:

```python
import pandas as pd

# Load geocoded file
df = pd.read_excel('data/ESRI_CADExport/CAD_ESRI_POLISHED_20251219_131114_geocoded.xlsx')

# Check for duplicates
print(f"Total records: {len(df):,}")
print(f"Unique ReportNumberNew: {df['ReportNumberNew'].nunique():,}")

# Should be equal
if len(df) == df['ReportNumberNew'].nunique():
    print("✅ No duplicates - file is clean!")
else:
    print("⚠️ Duplicates found - run fix script")
```

### If Duplicates Found

```bash
python fix_existing_geocoded_file.py ^
    "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114_geocoded.xlsx"
```

---

## KEY CHANGES EXPLAINED

### Change 1: Parallel Batch Processing

**Before (Sequential):**
```python
for i in range(0, len(unique_addresses), batch_size):
    batch = unique_addresses.iloc[i:i+batch_size].tolist()
    results = self.geocode_batch_table(batch)  # One at a time
```

**After (Parallel):**
```python
with ProcessPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(geocode_worker, batch): batch 
               for batch in batches}
    for future in as_completed(futures):
        results = future.result()  # Multiple batches simultaneously
```

**Impact**: 3-4x faster

---

### Change 2: Larger Batch Size

**Before:**
```python
--batch-size 1000
```

**After:**
```python
--batch-size 5000
```

**Rationale**: 
- Local .loc files have NO rate limits
- Larger batches = fewer table create/destroy cycles
- arcpy optimized for large batches

**Impact**: Additional 20-30% faster

---

### Change 3: Batch Insert Optimization

**Before:**
```python
with arcpy.da.InsertCursor(table, ["OBJECTID", "Address"]) as cursor:
    for idx, addr in enumerate(addresses, 1):
        cursor.insertRow([idx, str(addr).strip()])  # One row at a time
```

**After:**
```python
address_rows = [(idx, str(addr).strip()) for idx, addr in enumerate(addresses, 1)]
with arcpy.da.InsertCursor(table, ["OBJECTID", "Address"]) as cursor:
    cursor.insertRows(address_rows)  # Batch insert
```

**Impact**: 10-15% faster per batch

---

### Change 4: Duplicate Prevention

**Already in your current script (line 348):**
```python
# CRITICAL FIX: Deduplicate results_df
results_df = results_df.drop_duplicates(subset=['address'], keep='first')
```

**Status**: ✅ Already implemented - no changes needed

---

## TROUBLESHOOTING

### Issue 1: "Can't pickle arcpy objects"

**Cause**: ProcessPoolExecutor requires picklable functions  
**Solution**: Worker function is now at module level (line 32-53)

### Issue 2: "Table already exists"

**Cause**: Parallel workers creating tables with same name  
**Solution**: Each batch now uses unique UUID-based table names (line 157)

```python
batch_id = str(uuid.uuid4())[:8]
temp_table = f"in_memory\\geocode_{batch_id}"
```

### Issue 3: Slower than expected

**Check CPU usage:**
```python
import multiprocessing as mp
print(f"CPU cores available: {mp.cpu_count()}")
```

**Recommendations:**
- 4 cores → use `--max-workers 3` (leave 1 for system)
- 8 cores → use `--max-workers 6`
- 16 cores → use `--max-workers 8` (cap at 8 to avoid arcpy conflicts)

### Issue 4: ThreadPoolExecutor vs ProcessPoolExecutor

**ProcessPoolExecutor (default, safer):**
- Each worker = separate Python process
- No GIL (Global Interpreter Lock) issues
- More memory overhead
- **Recommended for arcpy**

**ThreadPoolExecutor (optional, test first):**
```bash
--executor-type thread
```
- Faster if arcpy is thread-safe
- Less overhead
- May have conflicts if arcpy isn't thread-safe
- **Test on small sample first**

---

## PERFORMANCE TUNING

### Find Optimal Worker Count

```bash
# Test different worker counts
for /L %i in (1,1,8) do (
    echo Testing with %i workers
    python test_geocoding_performance.py ^
        --input test_sample.xlsx ^
        --locator "path\to\locator.loc" ^
        --workers %i
)
```

### Find Optimal Batch Size

```bash
# Test different batch sizes
for %b in (1000 2500 5000 10000) do (
    echo Testing batch size %b
    python test_geocoding_performance.py ^
        --input test_sample.xlsx ^
        --locator "path\to\locator.loc" ^
        --batch-size %b
)
```

---

## VALIDATION CHECKLIST

After implementation, verify:

- [ ] Optimized script runs without errors
- [ ] Output file has same record count as input
- [ ] No duplicate ReportNumberNew values
- [ ] Geocoding rate is 3-4x faster than baseline
- [ ] Geocoded coordinates look correct (spot check)
- [ ] Script completes in expected time (~45-60 seconds)

---

## ROLLBACK PLAN

If issues arise:

```bash
# Restore original script
mv scripts/geocode_nj_locator_backup.py scripts/geocode_nj_locator.py

# Use original batch file
scripts\run_geocoding_local.bat
```

---

## NEXT STEPS AFTER SUCCESS

### 1. Update Master Pipeline

If using `master_pipeline.py`, update it to use optimized geocoding:

```python
# In master_pipeline.py
from geocode_nj_locator_optimized import NJGeocoderLocal

self.geocoder = NJGeocoderLocal(
    max_workers=4,  # Enable parallel processing
    use_web_service=False
)
```

### 2. Document New Performance

Update `ETL_PIPELINE_REFINEMENT.md` with new timing:

```markdown
## Performance (Updated 2025-12-19)

- **Validation** (710K records): ~15 seconds
- **RMS Backfill** (710K records): ~30-60 seconds
- **Geocoding** (17K unique addresses): ~45-60 seconds (OPTIMIZED)
- **Output Generation**: ~5 seconds
- **Total**: ~2-3 minutes
```

### 3. Create Production Workflow

```bash
# Create optimized full pipeline batch file
@echo off
echo Running OPTIMIZED CAD/RMS ETL Pipeline
echo ========================================

python scripts/master_pipeline.py ^
    --input "data\2019_2025_12_14_All_CAD.csv" ^
    --output-dir "data\ESRI_CADExport" ^
    --max-workers 4

echo Pipeline complete!
pause
```

---

## EXPECTED FINAL RESULTS

### Before Optimization
```
Total pipeline time: ~22 minutes
- Validation: 15s
- RMS Backfill: 60s
- Geocoding: 20 min (100K addresses)
- Output: 5s
```

### After Optimization
```
Total pipeline time: ~4-5 minutes
- Validation: 15s
- RMS Backfill: 60s
- Geocoding: 2-3 min (100K addresses)  ← 7-10x faster!
- Output: 5s
```

**Time saved: ~17 minutes per run**

---

## SUPPORT

### Getting Help

If issues arise, run diagnostics:

```bash
python -c "import multiprocessing as mp; print(f'CPU cores: {mp.cpu_count()}')"
python -c "import arcpy; print('arcpy OK')"
python -c "import concurrent.futures; print('concurrent.futures OK')"
```

### Performance Issues

1. Check CPU usage during geocoding
2. Monitor memory usage (Task Manager)
3. Review log file for errors
4. Test with smaller sample first

---

## SUMMARY

**Implementation Time**: ~30 minutes  
**Testing Time**: ~15 minutes  
**Total Time**: ~45 minutes  

**Expected Results**:
- ✅ 3-4x faster geocoding
- ✅ No duplicate records
- ✅ Same accuracy as before
- ✅ Better progress monitoring
- ✅ More CPU utilization

**Next Run**: Your 17,676 unique addresses will geocode in ~45-60 seconds instead of ~3.5 minutes, saving **2.5-3 minutes per run**.

For full 710K dataset with 82K addresses needing geocoding: **~5-7 minutes total** instead of **~20 minutes**.

---

## Quick Reference Commands

```bash
# Test on sample
python test_geocoding_performance.py --input test_sample.xlsx --locator locator.loc --quick

# Run optimized geocoding
scripts\run_geocoding_local_OPTIMIZED.bat

# Check for duplicates
python fix_existing_geocoded_file.py geocoded_file.xlsx

# Verify results
python -c "import pandas as pd; df=pd.read_excel('geocoded.xlsx'); print(f'Records: {len(df):,}, Unique: {df['ReportNumberNew'].nunique():,}')"
```

---

**Ready to implement! Start with STEP 1.**
