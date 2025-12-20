# Geocoding Performance Optimization - Implementation Guide

**Date**: 2025-12-19  
**Target**: Improve geocoding speed from ~17,676 unique addresses  
**Current Performance**: ~5,000 addr/min (~3.5 minutes for your dataset)  
**Target Performance**: ~15,000-20,000 addr/min (~1 minute for your dataset)

---

## Executive Summary

Your geocoding script has **parallel processing infrastructure (max_workers) but doesn't use it**. The batch loop is **100% sequential**. With proper parallelization, you can achieve **3-4x speedup** for your 17K unique addresses.

### Quick Wins (Implement First)

| Optimization | Effort | Impact | Time Saved |
|--------------|--------|--------|------------|
| **Parallel batch processing** | Medium | **3-4x faster** | 2-3 min → ~45 sec |
| **Increase batch size** | Low | 20-30% faster | Additional 10-15 sec |
| **Pre-allocate arcpy workspace** | Low | 10-15% faster | Additional 5-10 sec |

### Expected Results After Optimization

- **Before**: ~3.5 minutes for 17,676 unique addresses
- **After**: ~45-60 seconds for 17,676 unique addresses
- **Speedup**: 3.5-4.6x faster

---

## CRITICAL ISSUE: Sequential Batch Processing

### Current Code (Lines 318-332)
```python
for i in range(0, len(unique_addresses), batch_size):
    batch = unique_addresses.iloc[i:i+batch_size].tolist()
    
    # Use batch table geocoding (faster)
    results = self.geocode_batch_table(batch)  # ← Sequential!
    
    # Store results
    for addr, result in zip(batch, results):
        if result and result.get('status') == 'success':
            geocode_results[addr] = result
```

**Problem**: Processes one batch at a time. With 17,676 addresses and batch_size=1000, this processes 18 batches sequentially.

---

## HIGH PRIORITY OPTIMIZATION 1: Parallel Batch Processing

### Implementation for Cursor AI

Replace the sequential batch loop with parallel processing:

```python
def backfill_coordinates(self, df, address_column='FullAddress2', 
                        latitude_column='latitude', longitude_column='longitude',
                        batch_size=1000, progress_interval=1000):
    """Backfill with PARALLEL batch processing."""
    
    # ... existing validation code ...
    
    # Get unique addresses
    unique_addresses = rows_to_geocode[address_column].drop_duplicates()
    logger.info(f"Found {len(unique_addresses):,} unique addresses to geocode")
    
    # Create batches
    address_batches = []
    for i in range(0, len(unique_addresses), batch_size):
        batch = unique_addresses.iloc[i:i+batch_size].tolist()
        address_batches.append((i // batch_size, batch))
    
    logger.info(f"Processing {len(address_batches)} batches with {self.max_workers} workers...")
    
    # PARALLEL PROCESSING with ProcessPoolExecutor
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import multiprocessing as mp
    
    # Use ProcessPoolExecutor for CPU-bound arcpy operations
    # Note: Each worker needs its own arcpy context
    n_workers = min(self.max_workers, mp.cpu_count(), len(address_batches))
    
    geocode_results = {}
    processed = 0
    
    # Define worker function (must be picklable for ProcessPoolExecutor)
    def geocode_batch_worker(batch_data):
        """Worker function for parallel batch geocoding."""
        batch_idx, addresses = batch_data
        
        # Each worker creates its own geocoder instance
        # This ensures arcpy context is thread-safe
        worker_geocoder = NJGeocoderLocal(
            locator_path=self.locator_path_str,
            max_workers=1,  # No nested parallelism
            use_web_service=self.use_web_service
        )
        
        results = worker_geocoder.geocode_batch_table(addresses)
        
        # Return batch results
        batch_results = {}
        for addr, result in zip(addresses, results):
            if result and result.get('status') == 'success':
                batch_results[addr] = result
        
        return batch_idx, batch_results
    
    # Process batches in parallel
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        # Submit all batches
        future_to_batch = {
            executor.submit(geocode_batch_worker, batch_data): batch_data[0]
            for batch_data in address_batches
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_batch):
            batch_idx = future_to_batch[future]
            try:
                idx, batch_results = future.result()
                geocode_results.update(batch_results)
                
                processed += len(address_batches[idx][1])
                if processed % progress_interval == 0 or processed >= len(unique_addresses):
                    logger.info(f"Processed {processed:,} / {len(unique_addresses):,} unique addresses "
                              f"({processed/len(unique_addresses)*100:.1f}%)")
                    
            except Exception as e:
                logger.error(f"Batch {batch_idx} failed: {e}")
    
    # Update stats from all workers
    self.stats['successful'] = len(geocode_results)
    
    # ... existing merge code (lines 335-380) ...
```

### Alternative: ThreadPoolExecutor (if arcpy is thread-safe)

If arcpy operations are thread-safe (test first), use ThreadPoolExecutor for less overhead:

```python
# Use ThreadPoolExecutor instead of ProcessPoolExecutor
with ThreadPoolExecutor(max_workers=n_workers) as executor:
    # Same code as above
```

**Impact**: 3-4x faster for 18 batches with 4 workers

---

## HIGH PRIORITY OPTIMIZATION 2: Increase Batch Size

### Current Setting
```python
--batch-size 1000
```

### Recommended Setting
```python
--batch-size 5000  # or even 10000 for local .loc files
```

**Rationale**:
- Local `.loc` files have no rate limits
- Larger batches reduce overhead from arcpy table creation/destruction
- arcpy `GeocodeAddresses` is optimized for large batches

**Implementation**: Just change the command line argument or default value:

```python
parser.add_argument(
    '--batch-size',
    type=int,
    default=5000,  # Changed from 1000
    help='Batch size for geocoding (default: 5000)'
)
```

**Impact**: 20-30% faster for large batches (fewer table creation/destruction cycles)

---

## MEDIUM PRIORITY OPTIMIZATION 3: Pre-allocate arcpy Workspace

### Current Code (Lines 201-242)

Every batch creates and destroys in-memory tables:
```python
temp_table = "in_memory\\temp_geocode_table"
arcpy.management.CreateTable("in_memory", "temp_geocode_table")
# ... geocoding ...
arcpy.management.Delete(temp_table)
```

### Optimized Code

Use persistent workspace with unique table names:

```python
def geocode_batch_table_optimized(self, addresses: List[str], batch_id: str = None) -> List[Optional[Dict]]:
    """Optimized batch geocoding with persistent workspace."""
    
    if not addresses:
        return []
    
    # Use unique table names to avoid conflicts in parallel processing
    import uuid
    if batch_id is None:
        batch_id = str(uuid.uuid4())[:8]
    
    temp_table = f"in_memory\\geocode_input_{batch_id}"
    geocoded_table = f"in_memory\\geocoded_output_{batch_id}"
    
    try:
        # Create input table (optimized)
        arcpy.management.CreateTable("in_memory", f"geocode_input_{batch_id}")
        arcpy.management.AddField(temp_table, "OBJECTID", "LONG")
        arcpy.management.AddField(temp_table, "Address", "TEXT", field_length=255)
        
        # Batch insert addresses (faster than individual inserts)
        with arcpy.da.InsertCursor(temp_table, ["OBJECTID", "Address"]) as cursor:
            cursor.insertRows([(idx, str(addr).strip()) for idx, addr in enumerate(addresses, 1)])
        
        # Geocode entire batch at once
        arcpy.geocoding.GeocodeAddresses(
            temp_table,
            self.locator_path_str,
            "Address SingleLine",
            geocoded_table,
            "outSR=4326"
        )
        
        # Extract results (vectorized read)
        results = [None] * len(addresses)
        
        # Read all results at once
        fields = ["OBJECTID", "X", "Y", "Score", "Status"]
        with arcpy.da.SearchCursor(geocoded_table, fields) as cursor:
            for row in cursor:
                obj_id, x, y, score, status = row
                idx = obj_id - 1
                
                if 0 <= idx < len(addresses):
                    if score and score >= 80 and x and y:
                        results[idx] = {
                            'latitude': y,
                            'longitude': x,
                            'score': score,
                            'match_type': status or 'Unknown',
                            'status': 'success'
                        }
                        self.stats['successful'] += 1
                    else:
                        results[idx] = {
                            'latitude': None,
                            'longitude': None,
                            'score': score or 0,
                            'match_type': status or 'No Match',
                            'status': 'low_score' if score and score < 80 else 'no_match'
                        }
                        self.stats['no_results'] += 1
        
        return results
        
    except Exception as e:
        logger.error(f"Batch geocoding failed: {e}")
        self.stats['failed'] += len(addresses)
        return [None] * len(addresses)
        
    finally:
        # Cleanup
        try:
            arcpy.management.Delete(temp_table)
            arcpy.management.Delete(geocoded_table)
        except:
            pass
```

**Key Improvements**:
1. `insertRows` (batch insert) instead of individual `insertRow` calls
2. Unique table names for parallel safety
3. Vectorized result reading
4. Better error handling

**Impact**: 10-15% faster per batch

---

## MEDIUM PRIORITY OPTIMIZATION 4: Memory-Efficient DataFrame Operations

### Current Code (Lines 335-373)

Already optimized! The vectorized merge is good. However, ensure results_df deduplication:

```python
# CRITICAL FIX: Already implemented (line 348)
results_df = results_df.drop_duplicates(subset=['address'], keep='first')
```

✅ **Already fixed - no changes needed**

---

## LOW PRIORITY OPTIMIZATION 5: Progress Tracking with tqdm

### Add Visual Progress Bar

```python
from tqdm import tqdm

# In parallel processing loop
with ProcessPoolExecutor(max_workers=n_workers) as executor:
    futures = {
        executor.submit(geocode_batch_worker, batch_data): batch_data[0]
        for batch_data in address_batches
    }
    
    # Progress bar
    with tqdm(total=len(unique_addresses), desc="Geocoding") as pbar:
        for future in as_completed(futures):
            try:
                idx, batch_results = future.result()
                geocode_results.update(batch_results)
                pbar.update(len(address_batches[idx][1]))
            except Exception as e:
                logger.error(f"Batch failed: {e}")
```

**Implementation**: Add `tqdm` to requirements.txt:
```
tqdm>=4.65.0
```

---

## Configuration Recommendations

### Optimal Command Line Arguments

```bash
# For local .loc file
python scripts/geocode_nj_locator.py \
    --input "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx" \
    --locator "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc" \
    --format excel \
    --batch-size 5000 \
    --max-workers 4
```

### Worker Count Recommendation

```python
# Optimal workers = min(CPU cores, number of batches)
import multiprocessing as mp

optimal_workers = min(
    mp.cpu_count() - 1,  # Leave 1 core for system
    len(address_batches),
    8  # Cap at 8 to avoid arcpy conflicts
)
```

For your system:
- **CPU cores**: Likely 4-8
- **Optimal workers**: 4-6
- **Batch count**: 4 batches with batch_size=5000 (17,676 / 5000 ≈ 4)

---

## Implementation Checklist for Cursor AI

### Phase 1: Core Parallelization (30 minutes)
- [ ] Implement parallel batch processing with ProcessPoolExecutor
- [ ] Add batch_id parameter to geocode_batch_table
- [ ] Update worker function to be picklable
- [ ] Test with 2 workers on small dataset

### Phase 2: Batch Optimization (15 minutes)
- [ ] Change default batch_size to 5000
- [ ] Implement insertRows batch insert
- [ ] Add unique table naming with UUID
- [ ] Test with larger batches

### Phase 3: Progress & Monitoring (15 minutes)
- [ ] Add tqdm progress bar
- [ ] Add memory monitoring (optional)
- [ ] Improve logging with batch completion times

### Phase 4: Testing (30 minutes)
- [ ] Test with 1000 addresses (small dataset)
- [ ] Test with full 17,676 addresses
- [ ] Verify no duplicate records in output
- [ ] Compare performance before/after

---

## Performance Benchmarks

### Before Optimization
```
Dataset: 17,676 unique addresses
Batch size: 1000
Workers: 1 (sequential)
Time: ~3.5 minutes
Speed: ~5,000 addr/min
```

### After Optimization (Expected)
```
Dataset: 17,676 unique addresses
Batch size: 5000
Workers: 4 (parallel)
Time: ~45-60 seconds
Speed: ~18,000-24,000 addr/min
Speedup: 3.5-4.6x
```

### Breakdown of Improvements
| Optimization | Time Saved | New Time |
|--------------|------------|----------|
| Baseline | - | 3.5 min |
| + Parallel processing (4 workers) | -2.6 min | 0.9 min |
| + Larger batches (5000) | -0.2 min | 0.7 min |
| + Batch insert optimization | -0.1 min | 0.6 min |
| **TOTAL** | **-2.9 min** | **0.6 min** |

---

## Troubleshooting

### "ProcessPoolExecutor: Can't pickle arcpy objects"

**Solution**: Ensure worker function is defined at module level, not inside class:

```python
# Move outside class definition
def _geocode_batch_worker_global(locator_path, addresses, use_web_service=False):
    """Global worker function for parallel geocoding."""
    geocoder = NJGeocoderLocal(locator_path, max_workers=1, use_web_service=use_web_service)
    return geocoder.geocode_batch_table(addresses)
```

### "arcpy: Table already exists"

**Solution**: Use unique table names with UUID or timestamp:
```python
import uuid
table_id = str(uuid.uuid4())[:8]
temp_table = f"in_memory\\geocode_{table_id}"
```

### Memory Issues with Large Datasets

**Solution**: Limit workers or reduce batch size:
```python
# Monitor memory usage
import psutil
mem_gb = psutil.virtual_memory().available / (1024**3)
max_workers = min(4, int(mem_gb / 2))  # 2GB per worker
```

---

## Testing Script

Create `test_geocoding_performance.py`:

```python
#!/usr/bin/env python
"""Test geocoding performance with different configurations."""

import time
import pandas as pd
from pathlib import Path
from geocode_nj_locator import NJGeocoderLocal

def benchmark_geocoding(input_file, locator_path, batch_size, max_workers):
    """Benchmark geocoding with specific configuration."""
    
    # Load data
    df = pd.read_excel(input_file)
    print(f"Loaded {len(df):,} records")
    
    # Initialize geocoder
    geocoder = NJGeocoderLocal(locator_path, max_workers=max_workers)
    
    # Benchmark
    start = time.time()
    df_geocoded = geocoder.backfill_coordinates(df, batch_size=batch_size)
    elapsed = time.time() - start
    
    # Results
    stats = geocoder.get_stats()
    print(f"\nBatch Size: {batch_size}, Workers: {max_workers}")
    print(f"Time: {elapsed:.2f}s ({elapsed/60:.2f} min)")
    print(f"Success: {stats['successful']:,}")
    print(f"Speed: {stats['successful']/elapsed:.0f} addr/sec")
    
    return elapsed, stats

# Test configurations
configs = [
    (1000, 1),   # Baseline
    (1000, 4),   # Parallel
    (5000, 4),   # Parallel + large batch
]

for batch_size, workers in configs:
    benchmark_geocoding(
        "data/ESRI_CADExport/CAD_ESRI_POLISHED_20251219_131114.xlsx",
        "C:/Dev/SCRPA_Time_v3/10_Refrence_Files/NJ_Geocode/NJ_Geocode.loc",
        batch_size,
        workers
    )
    print("-" * 60)
```

---

## Final Recommendations

### Immediate Actions (Do Now)
1. **Implement parallel batch processing** - 3-4x speedup
2. **Increase batch size to 5000** - Additional 20-30% speedup
3. **Test on small dataset first** (1000 addresses)

### After Initial Testing
1. Optimize insertRows batch operation
2. Add progress monitoring
3. Fine-tune worker count based on CPU

### Expected Final Performance
- **17,676 addresses**: ~45-60 seconds
- **Full 710K dataset** (82K missing coords): ~5-7 minutes total
- **Overall speedup**: 4-5x faster than current

---

## Questions for Testing

1. How many CPU cores does your machine have?
   ```python
   import multiprocessing
   print(f"CPU cores: {multiprocessing.cpu_count()}")
   ```

2. Is arcpy thread-safe on your system?
   - Test with ThreadPoolExecutor first (faster than ProcessPoolExecutor)
   - If errors occur, fall back to ProcessPoolExecutor

3. What's your available RAM?
   - Each worker needs ~500MB-1GB
   - Limit workers if < 8GB RAM available
