# Script Review Prompt for Claude AI

Use this prompt to review the CAD/RMS ETL pipeline scripts for correctness, efficiency, and parallel processing optimization.

---

## Review Prompt

```
Please review the following Python scripts for a CAD/RMS data cleaning and ETL pipeline. 
Focus on correctness, efficiency, and parallel processing/multi-core utilization.

**Scripts to Review:**
1. scripts/geocode_nj_geocoder.py - NJ Geocoder service integration for latitude/longitude backfill
2. scripts/unified_rms_backfill.py - RMS data backfill processor
3. scripts/generate_esri_output.py - ESRI output generator with strict column ordering
4. scripts/master_pipeline.py - Master pipeline orchestrator

**Review Criteria:**

### 1. Correctness
- [ ] Logic errors or bugs
- [ ] Edge cases not handled
- [ ] Data type handling (especially pandas/numpy)
- [ ] Error handling completeness
- [ ] Input validation
- [ ] Output validation
- [ ] Memory leaks or resource cleanup
- [ ] Thread safety (if applicable)

### 2. Efficiency
- [ ] Unnecessary data copying
- [ ] Inefficient pandas operations (should use vectorized operations where possible)
- [ ] Redundant computations
- [ ] Memory usage optimization
- [ ] I/O operations (file reading/writing efficiency)
- [ ] Algorithm complexity
- [ ] Caching opportunities

### 3. Parallel Processing & Multi-Core Usage
- [ ] Opportunities for parallelization that are currently sequential
- [ ] Proper use of multiprocessing/threading/concurrent.futures
- [ ] CPU core utilization (should leverage all available cores where beneficial)
- [ ] Thread/process pool sizing
- [ ] Data parallelism opportunities (e.g., processing DataFrame chunks in parallel)
- [ ] I/O-bound vs CPU-bound operations (use appropriate concurrency model)
- [ ] Race conditions or synchronization issues
- [ ] Overhead vs benefit of parallelization

### 4. Specific Areas of Focus

**For geocode_nj_geocoder.py:**
- Is the batch geocoding implementation efficient?
- Are there opportunities to parallelize the geocoding requests better?
- Is the retry logic correct and efficient?
- Can we use async/await for I/O-bound geocoding requests instead of ThreadPoolExecutor?
- Is the unique address deduplication optimal?

**For unified_rms_backfill.py:**
- Is the merge operation efficient for large datasets?
- Can the field backfill loop be vectorized?
- Are there opportunities to parallelize the RMS file loading?
- Is the deduplication logic optimal?
- Can we use pandas merge more efficiently?

**For generate_esri_output.py:**
- Are the column operations vectorized?
- Is the ZoneCalc calculation efficient?
- Can the How Reported normalization be vectorized?
- Are there unnecessary DataFrame copies?

**For master_pipeline.py:**
- Is the pipeline orchestration efficient?
- Can multiple steps run in parallel where data dependencies allow?
- Is memory usage optimized between steps?
- Are there opportunities for streaming/chunked processing for large datasets?

### 5. Code Quality
- [ ] Code organization and structure
- [ ] Documentation completeness
- [ ] Type hints usage
- [ ] Consistent error handling patterns
- [ ] Logging appropriateness

### 6. Performance Recommendations
- [ ] Specific optimizations to suggest
- [ ] Performance bottlenecks identified
- [ ] Scalability concerns for large datasets (1M+ records)
- [ ] Memory-efficient alternatives

**Expected Output:**
Please provide:
1. A summary of findings (correctness issues, efficiency improvements, parallelization opportunities)
2. Specific code suggestions with examples
3. Performance impact estimates where possible
4. Priority ranking of recommendations (high/medium/low)

**Context:**
- Datasets can be 700K-1.5M records
- Scripts should handle large datasets efficiently
- Python 3.8+ environment
- Standard libraries: pandas, numpy, requests, concurrent.futures
- Windows environment (multiprocessing considerations)
```

---

## Alternative: Focused Review Prompts

### For Parallel Processing Focus Only

```
Review the following Python scripts specifically for parallel processing and multi-core 
utilization opportunities:

[Scripts list]

Focus on:
1. Sequential operations that could be parallelized
2. Current parallelization implementation correctness
3. CPU core utilization (should use all available cores where beneficial)
4. I/O-bound vs CPU-bound operation identification
5. ThreadPoolExecutor vs ProcessPoolExecutor appropriateness
6. Batch/chunk processing opportunities
7. Data parallelism (processing DataFrame chunks in parallel)

Provide specific code examples showing how to improve parallelization.
```

### For Efficiency Focus Only

```
Review the following Python scripts for efficiency and performance optimization:

[Scripts list]

Focus on:
1. Pandas vectorization opportunities (avoid loops over rows)
2. Memory usage optimization
3. Unnecessary data copying
4. Algorithm complexity improvements
5. I/O optimization
6. Caching opportunities

Provide specific code examples showing optimizations.
```

### For Correctness Focus Only

```
Review the following Python scripts for correctness, bugs, and edge cases:

[Scripts list]

Focus on:
1. Logic errors
2. Edge cases not handled
3. Error handling gaps
4. Data type issues
5. Memory/resource leaks
6. Thread safety issues
7. Input/output validation

Provide specific bug fixes and edge case handling.
```

---

## Usage Instructions

1. **Copy the main review prompt** above
2. **Read each script** and append its contents to the prompt
3. **Submit to Claude AI** for comprehensive review
4. **Or use focused prompts** for specific areas of concern

## Example Usage

```
[Main Review Prompt]

--- scripts/geocode_nj_geocoder.py ---
[Paste script contents here]

--- scripts/unified_rms_backfill.py ---
[Paste script contents here]

--- scripts/generate_esri_output.py ---
[Paste script contents here]

--- scripts/master_pipeline.py ---
[Paste script contents here]
```

---

## Expected Review Output Format

The AI should provide:

1. **Executive Summary**
   - Overall assessment
   - Critical issues found
   - High-impact improvements

2. **Detailed Findings**
   - Organized by script
   - Organized by category (correctness/efficiency/parallelization)
   - Code examples with fixes

3. **Prioritized Recommendations**
   - High priority: Critical bugs, major performance issues
   - Medium priority: Efficiency improvements, better parallelization
   - Low priority: Code quality, minor optimizations

4. **Performance Impact Estimates**
   - Expected speedup from parallelization
   - Memory usage improvements
   - Scalability improvements

