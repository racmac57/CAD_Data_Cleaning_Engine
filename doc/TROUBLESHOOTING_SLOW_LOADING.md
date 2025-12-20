# Troubleshooting: Slow Excel File Loading

## Problem

Loading large Excel files (700K+ rows) can take 60-90+ seconds, especially if:
- File is on OneDrive (sync overhead)
- File is on network drive
- System has limited RAM
- Excel file has complex formatting

## Solutions

### Option 1: Convert to CSV First (RECOMMENDED) ⚡

CSV files load **5-10x faster** than Excel files:

```cmd
# One-time conversion
python scripts\convert_excel_to_csv.py --input "data\01_raw\19_to_25_12_18_CAD_Data.xlsx"

# Then use CSV in pipeline (much faster!)
python scripts\master_pipeline.py --input "data\01_raw\19_to_25_12_18_CAD_Data.csv" --format excel
```

**Benefits**:
- CSV loads in ~5-10 seconds vs 60-90 seconds for Excel
- No formatting overhead
- Smaller file size
- Faster subsequent runs

### Option 2: Move File to Local Drive

If file is on OneDrive or network drive:
1. Copy file to local drive (e.g., `C:\temp\`)
2. Run pipeline from local copy
3. Move outputs back to OneDrive after processing

**Speed improvement**: 2-3x faster

### Option 3: Use Chunked Reading (For Very Large Files)

For files that don't fit in memory, modify the loading code to read in chunks. 
This is already handled automatically by pandas for very large files.

### Option 4: Optimize Excel File

If you must use Excel:
1. Remove unnecessary formatting
2. Remove empty rows/columns
3. Save as `.xlsx` (not `.xls`)
4. Close Excel before running pipeline

## Performance Comparison

| File Type | Size | Load Time | Notes |
|-----------|------|-----------|-------|
| **Excel (.xlsx)** | 710K rows | 60-90s | OneDrive: slower |
| **Excel (.xlsx)** | 710K rows | 30-60s | Local drive: faster |
| **CSV** | 710K rows | 5-10s | **5-10x faster!** |

## Expected Load Times

### Excel File (710K rows)
- **OneDrive**: 60-90 seconds
- **Local SSD**: 30-60 seconds
- **Local HDD**: 60-120 seconds

### CSV File (710K rows)
- **OneDrive**: 5-10 seconds
- **Local SSD**: 3-5 seconds
- **Local HDD**: 5-10 seconds

## Quick Fix

**Fastest solution**: Convert to CSV once, then use CSV for all future runs:

```cmd
# Step 1: Convert (one-time, takes ~30-60 seconds)
python scripts\convert_excel_to_csv.py --input "data\01_raw\19_to_25_12_18_CAD_Data.xlsx"

# Step 2: Use CSV (much faster!)
python scripts\master_pipeline.py --input "data\01_raw\19_to_25_12_18_CAD_Data.csv" --format excel
```

## Why Excel is Slow

1. **XML parsing**: Excel files are compressed XML, requires parsing
2. **Formatting**: Excel stores cell formatting, colors, etc.
3. **OneDrive sync**: Network I/O overhead
4. **Memory**: Excel reader loads entire file structure into memory

## Why CSV is Fast

1. **Simple format**: Plain text, no parsing needed
2. **No formatting**: Just data
3. **Streaming**: Can read line-by-line
4. **Optimized**: Pandas CSV reader is highly optimized

## Monitoring Progress

The updated pipeline now shows:
```
[STEP 1] Loading CAD data...
  Reading file: data\01_raw\19_to_25_12_18_CAD_Data.xlsx
  This may take 30-60 seconds for large Excel files...
  Reading Excel file (this may take a minute for 700K+ rows)...
  ✓ Loaded 710,626 records with 25 columns in 45.2 seconds
```

If it takes longer than 2 minutes, consider converting to CSV.

---

**Recommendation**: Convert to CSV for 5-10x faster loading! 🚀

