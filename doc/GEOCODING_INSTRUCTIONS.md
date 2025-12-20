# How to Run the NJ Geocoder

## Quick Start

To geocode your polished ESRI output file, run:

```bash
python scripts/geocode_nj_geocoder.py --input "data/ESRI_CADExport/CAD_ESRI_POLISHED_20251219_131114.xlsx" --format excel
```

## Command Options

### Basic Usage

**Minimum required** (uses defaults):
```bash
python scripts/geocode_nj_geocoder.py --input "path/to/your/file.xlsx"
```

**With custom output path**:
```bash
python scripts/geocode_nj_geocoder.py --input "data/ESRI_CADExport/CAD_ESRI_POLISHED_20251219_131114.xlsx" --output "data/ESRI_CADExport/CAD_ESRI_GEOCODED.xlsx" --format excel
```

### Full Command with All Options

```bash
python scripts/geocode_nj_geocoder.py \
    --input "data/ESRI_CADExport/CAD_ESRI_POLISHED_20251219_131114.xlsx" \
    --output "data/ESRI_CADExport/CAD_ESRI_GEOCODED.xlsx" \
    --address-column "FullAddress2" \
    --latitude-column "latitude" \
    --longitude-column "longitude" \
    --batch-size 100 \
    --max-workers 5 \
    --format excel
```

## Parameters Explained

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--input` | **Required** | Path to your Excel/CSV file |
| `--output` | Auto-generated | Output file path (default: input with `_geocoded` suffix) |
| `--address-column` | `FullAddress2` | Name of address column to geocode |
| `--latitude-column` | `latitude` | Name of latitude column to populate |
| `--longitude-column` | `longitude` | Name of longitude column to populate |
| `--batch-size` | `100` | Number of addresses per batch |
| `--max-workers` | `5` | Concurrent geocoding requests |
| `--format` | `csv` | Output format: `csv` or `excel` |

## For Your Current File

**Recommended command**:
```bash
cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"
python scripts/geocode_nj_geocoder.py --input "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx" --format excel
```

This will:
- Geocode all 710,625 records with missing coordinates
- Process unique addresses (reduces API calls)
- Save output as: `CAD_ESRI_POLISHED_20251219_131114_geocoded.xlsx`

## Performance Notes

- **Processing Time**: ~10-20 minutes for 710K records (depends on unique addresses)
- **API Rate**: Uses 5 concurrent workers by default
- **Success Rate**: Typically 80-95% for valid Hackensack addresses
- **Unique Addresses**: Script automatically deduplicates to minimize API calls

## What Happens

1. Script loads your Excel file
2. Identifies records with missing latitude/longitude
3. Extracts unique addresses (deduplicates)
4. Geocodes addresses using NJ Geocoder service
5. Maps results back to all records with matching addresses
6. Saves geocoded file

## Output

The script will:
- Show progress every 1000 addresses
- Display geocoding statistics (successful, failed, no results)
- Save the geocoded file with coordinates backfilled
- Create a log file with detailed statistics

## Troubleshooting

**If you get connection errors**:
- Check internet connection
- Verify NJ Geocoder service is accessible: https://geo.nj.gov/arcgis/rest/services/Tasks/NJ_Geocode/GeocodeServer
- Reduce `--max-workers` to 3 if getting rate limited

**If success rate is low**:
- Check address quality in FullAddress2 column
- Review geocoding log for common issues
- Some addresses may need manual correction

## Example Output

```
Loading data from: data/ESRI_CADExport/CAD_ESRI_POLISHED_20251219_131114.xlsx
Loaded 710,625 records
Geocoding 710,625 addresses using NJ Geocoder service...
Using 5 concurrent workers, batch size: 100
Found 45,231 unique addresses to geocode
Processed 1,000 / 45,231 unique addresses (2.2%)
...
Backfilled coordinates for 642,891 records
Geocoding stats: 642,891 successful, 67,734 no results, 0 failed
Processing time: 12.5 minutes
Output file: data/ESRI_CADExport/CAD_ESRI_POLISHED_20251219_131114_geocoded.xlsx
```

