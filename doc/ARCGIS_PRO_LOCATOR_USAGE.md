# Using ArcGIS Pro Locator for Geocoding

## Overview

If you have ArcGIS Pro with a locator saved (like "NJ_Geocode"), you can use it directly for geocoding. This is faster than the web service and doesn't require local `.loc` files.

## Your Setup

Based on your information:
- **Locator Name**: `NJ_Geocode`
- **Type**: Locator (registered in ArcGIS Pro)
- **Path**: `https://geo.nj.gov/arcgis/rest/services/Tasks/NJ Geocode/GeocodeServer/NJ Geocode`

## Option 1: Use ArcGIS Pro Locator Name

If the locator is registered in ArcGIS Pro, you can reference it by name:

```bash
python scripts/geocode_nj_locator.py \
    --input "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx" \
    --locator "NJ_Geocode" \
    --use-web-service \
    --format excel
```

## Option 2: Use Web Service URL

You can also use the full web service URL:

```bash
python scripts/geocode_nj_locator.py \
    --input "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx" \
    --locator "https://geo.nj.gov/arcgis/rest/services/Tasks/NJ Geocode/GeocodeServer/NJ Geocode" \
    --use-web-service \
    --format excel
```

## Option 3: Use Local Locator Files (Fastest)

If you have the local `.loc` or `.loz` files, use them for best performance:

```bash
python scripts/geocode_nj_locator.py \
    --input "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx" \
    --locator "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc" \
    --format excel
```

**Note**: No `--use-web-service` flag needed for local files.

## Finding Your Locator in ArcGIS Pro

1. Open ArcGIS Pro
2. Go to **Catalog** pane
3. Look under **Locators** or **Project** > **Locators**
4. Find your locator (e.g., "NJ_Geocode")
5. Right-click > **Properties** to see the full path/name

## Recommended Approach

For best performance with your setup:

1. **If you have local `.loc` files** → Use Option 3 (fastest, offline)
2. **If locator is in ArcGIS Pro** → Use Option 1 (fast, uses ArcGIS Pro's connection)
3. **If neither available** → Use the web service script (`geocode_nj_geocoder.py`)

## Performance Comparison

| Method | Speed | Setup |
|--------|-------|-------|
| Local `.loc` file | Fastest (~5,000 addr/min) | Requires local file |
| ArcGIS Pro locator | Fast (~2,000-3,000 addr/min) | Requires ArcGIS Pro |
| Web service (arcpy) | Medium (~500-1,000 addr/min) | Requires ArcGIS Pro |
| Web service (requests) | Slowest (~100-200 addr/min) | No ArcGIS needed |

## Troubleshooting

### "Locator not found" Error

**Solution**: Verify the locator name or path:
- Check ArcGIS Pro Catalog for exact locator name
- Use full path if using local file
- Use `--use-web-service` flag for ArcGIS Pro locator references

### "arcpy not available" Error

**Solution**: Make sure you're running Python from ArcGIS Pro's Python environment:
```bash
# Use ArcGIS Pro's Python
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" scripts/geocode_nj_locator.py ...
```

Or install `arcpy` in your current Python environment (if compatible).

## Example: Full Command

```bash
cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"

# Using ArcGIS Pro locator name
python scripts/geocode_nj_locator.py \
    --input "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx" \
    --locator "NJ_Geocode" \
    --use-web-service \
    --format excel \
    --batch-size 1000
```

This will:
1. Load your polished ESRI file
2. Find addresses missing coordinates
3. Geocode using your ArcGIS Pro locator
4. Save results to `CAD_ESRI_POLISHED_20251219_131114_geocoded.xlsx`

