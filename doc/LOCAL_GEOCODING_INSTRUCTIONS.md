# Local Locator Geocoding Instructions

## Overview

The local locator geocoding script (`scripts/geocode_nj_locator.py`) uses ArcGIS locator files (`.loc` or `.loz`) for fast, offline geocoding. This is **much faster** than the web service and has no rate limits.

## Requirements

- **ArcGIS Pro** or **ArcGIS Desktop** with `arcpy` installed
- Local locator file (`.loc` or `.loz`)
  - Example: `C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc`

## Advantages Over Web Service

✅ **Much faster** - No network latency  
✅ **No rate limits** - Process as many addresses as needed  
✅ **Works offline** - No internet connection required  
✅ **Higher throughput** - Can process thousands of addresses per minute  
✅ **No API costs** - Free to use

## Usage

### Basic Command

```bash
python scripts/geocode_nj_locator.py \
    --input "data/ESRI_CADExport/CAD_ESRI_POLISHED_20251219_131114.xlsx" \
    --locator "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc" \
    --format excel
```

### Full Options

```bash
python scripts/geocode_nj_locator.py \
    --input "path/to/input.xlsx" \
    --locator "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc" \
    --output "path/to/output_geocoded.xlsx" \
    --format excel \
    --address-column "FullAddress2" \
    --latitude-column "latitude" \
    --longitude-column "longitude" \
    --batch-size 1000 \
    --max-workers 4
```

### Parameters

- `--input` (required): Input Excel or CSV file with addresses
- `--locator` (required): Path to local locator file (`.loc` or `.loz`)
- `--output` (optional): Output file path (default: input file with `_geocoded` suffix)
- `--format` (optional): Input file format - `excel` or `csv` (default: `excel`)
- `--address-column` (optional): Column name containing addresses (default: `FullAddress2`)
- `--latitude-column` (optional): Column name for latitude (default: `latitude`)
- `--longitude-column` (optional): Column name for longitude (default: `longitude`)
- `--batch-size` (optional): Number of addresses to geocode per batch (default: `1000`)
- `--max-workers` (optional): Maximum concurrent workers (default: `4`)

## Example: Geocode Your Polished ESRI File

```bash
cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"

python scripts/geocode_nj_locator.py \
    --input "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx" \
    --locator "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc" \
    --format excel \
    --batch-size 1000
```

## Performance Comparison

| Method | Speed | Rate Limits | Offline |
|--------|-------|-------------|---------|
| **Web Service** (`geocode_nj_geocoder.py`) | ~100-200 addresses/min | Yes (rate limiting) | No |
| **Local Locator** (`geocode_nj_locator.py`) | ~1,000-5,000 addresses/min | No | Yes |

## Troubleshooting

### Error: "arcpy is not available"

**Solution**: Install ArcGIS Pro or ArcGIS Desktop. The `arcpy` module comes with ArcGIS installations.

### Error: "Locator file not found"

**Solution**: Verify the locator file path is correct:
```bash
# Check if file exists
Test-Path "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc"
```

### Error: "Could not verify locator file"

**Solution**: The locator file might still work. The script will attempt to use it anyway. If geocoding fails, check:
1. The locator file is not corrupted
2. You have read permissions to the file
3. The locator file is compatible with your ArcGIS version

## Output

The script will:
1. Load your input file
2. Identify addresses that need geocoding (missing lat/lon)
3. Deduplicate addresses to minimize geocoding calls
4. Geocode addresses in batches
5. Merge results back into the original DataFrame
6. Save the geocoded file

**Output file**: `{input_filename}_geocoded.xlsx`

## Notes

- The script automatically deduplicates addresses before geocoding (saves time)
- Only addresses with missing coordinates are geocoded
- Results are merged back using vectorized operations (fast)
- The script includes the duplicate prevention fix from the web service version

## Comparison with Web Service Version

If you don't have ArcGIS/arcpy, use the web service version:
```bash
python scripts/geocode_nj_geocoder.py --input "file.xlsx" --format excel
```

The web service version:
- Works without ArcGIS
- Uses the NJ Geocoder REST API
- Has rate limits and slower performance
- Requires internet connection

