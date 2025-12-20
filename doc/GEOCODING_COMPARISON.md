# Geocoding Methods Comparison

## Available Geocoding Methods

This project supports two geocoding methods:

### 1. Web Service Geocoding (`geocode_nj_geocoder.py`)

**Uses**: New Jersey Geocoder REST API  
**Endpoint**: `https://geo.nj.gov/arcgis/rest/services/Tasks/NJ_Geocode/GeocodeServer`

**Pros**:
- ✅ No ArcGIS installation required
- ✅ Works on any system with Python
- ✅ Always uses latest geocoding data
- ✅ No local file management

**Cons**:
- ❌ Slower (network latency)
- ❌ Rate limits (may need throttling)
- ❌ Requires internet connection
- ❌ API may have usage restrictions

**Performance**: ~100-200 addresses/minute

**Usage**:
```bash
python scripts/geocode_nj_geocoder.py --input "file.xlsx" --format excel
```

### 2. Local Locator Geocoding (`geocode_nj_locator.py`)

**Uses**: Local ArcGIS locator file (`.loc` or `.loz`)  
**Example**: `C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc`

**Pros**:
- ✅ **Much faster** (10-50x faster than web service)
- ✅ **No rate limits**
- ✅ **Works offline**
- ✅ **Higher throughput** (thousands of addresses/minute)
- ✅ **No API costs**

**Cons**:
- ❌ Requires ArcGIS Pro or ArcGIS Desktop
- ❌ Requires local locator file
- ❌ Locator file may need periodic updates

**Performance**: ~1,000-5,000 addresses/minute

**Usage**:
```bash
python scripts/geocode_nj_locator.py \
    --input "file.xlsx" \
    --locator "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc" \
    --format excel
```

## Performance Comparison

| Metric | Web Service | Local Locator |
|--------|-------------|---------------|
| **Speed** | ~100-200 addr/min | ~1,000-5,000 addr/min |
| **Rate Limits** | Yes | No |
| **Offline** | No | Yes |
| **Setup Required** | None | ArcGIS + Locator File |
| **Best For** | Small batches, no ArcGIS | Large batches, frequent use |

## Recommendation

- **Use Local Locator** if:
  - You have ArcGIS Pro/Desktop installed
  - You have the locator file available
  - You're processing large datasets (>10,000 addresses)
  - You need fast turnaround times

- **Use Web Service** if:
  - You don't have ArcGIS installed
  - You're processing small batches (<1,000 addresses)
  - You need the latest geocoding data
  - You're working on a system without ArcGIS

## Both Methods Include

✅ Automatic address deduplication  
✅ Vectorized merge operations  
✅ Duplicate prevention fixes  
✅ Progress logging  
✅ Statistics reporting  
✅ Batch processing  
✅ Error handling and retries

## Example: Processing 100,000 Addresses

**Web Service**:
- Time: ~8-16 hours (with rate limiting)
- Network: Required
- Cost: Free (but may hit rate limits)

**Local Locator**:
- Time: ~20-100 minutes
- Network: Not required
- Cost: Free (no limits)

## Switching Between Methods

Both scripts produce identical output formats. You can:
1. Start with web service for testing
2. Switch to local locator for production runs
3. Use either method interchangeably

The output files are compatible and can be used in the same downstream processes.

