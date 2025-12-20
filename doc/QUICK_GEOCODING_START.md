# Quick Start: Geocoding Your Data

## You Have Two Options

Since you have both the ArcGIS Pro locator and the local `.loc` file, here are your options:

### Option 3: Local .loc File (FASTEST - Recommended) ⚡

**Best for**: Maximum speed, offline processing, large datasets

```bash
cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"

python scripts/geocode_nj_locator.py \
    --input "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx" \
    --locator "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc" \
    --format excel \
    --batch-size 1000
```

**Or use the batch file**:
```bash
scripts\run_geocoding_local.bat
```

**Performance**: ~5,000 addresses/minute  
**Time for 710K records**: ~2-3 hours

---

### Option 1: ArcGIS Pro Locator (FAST)

**Best for**: When you want to use ArcGIS Pro's registered locator

```bash
cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"

python scripts/geocode_nj_locator.py \
    --input "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx" \
    --locator "NJ_Geocode" \
    --use-web-service \
    --format excel \
    --batch-size 1000
```

**Or use the batch file**:
```bash
scripts\run_geocoding_arcgis_pro.bat
```

**Performance**: ~2,000-3,000 addresses/minute  
**Time for 710K records**: ~4-6 hours

---

## Recommendation

**Use Option 3 (local .loc file)** because:
- ✅ **2-3x faster** than ArcGIS Pro locator
- ✅ Works **offline** (no internet needed)
- ✅ **No rate limits**
- ✅ Better for large datasets

## What Happens

1. Script loads your polished ESRI file
2. Finds addresses missing coordinates (~82,717 records)
3. Deduplicates to unique addresses (~17,676 addresses)
4. Geocodes addresses in batches
5. Merges results back into DataFrame
6. Saves to: `CAD_ESRI_POLISHED_20251219_131114_geocoded.xlsx`

## Expected Results

- **Input**: 710,626 records
- **Records needing geocoding**: ~82,717 (11.6%)
- **Unique addresses**: ~17,676
- **Expected success rate**: ~88-90%
- **Final geocoded records**: ~627,000-630,000

## Troubleshooting

### "arcpy not available" Error

Make sure you're using ArcGIS Pro's Python:
```bash
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" scripts/geocode_nj_locator.py ...
```

### "Locator file not found" Error

Verify the path:
```bash
Test-Path "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc"
```

### File is Open in Excel

Close the Excel file before running the script.

## Quick Commands

**Test the locator file exists**:
```powershell
Test-Path "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc"
```

**Run geocoding (local file)**:
```bash
scripts\run_geocoding_local.bat
```

**Run geocoding (ArcGIS Pro locator)**:
```bash
scripts\run_geocoding_arcgis_pro.bat
```

