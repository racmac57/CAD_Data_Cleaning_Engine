"""Compare ESRI CAD export files to determine which is most complete."""
import pandas as pd
from pathlib import Path
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_DIR = BASE_DIR / "data" / "ESRI_CADExport"

files_to_check = [
    "CAD_ESRI_Final_20251117.xlsx",
    "CAD_ESRI_Final_20251117_v2.xlsx",
    "CAD_ESRI_Final_20251117_v3.xlsx",
    "CAD_ESRI_Final_20251121.xlsx",
]

print("="*80)
print("COMPARING ESRI CAD EXPORT FILES")
print("="*80)

results = []

for filename in files_to_check:
    filepath = ESRI_DIR / filename
    if not filepath.exists():
        print(f"\n[WARNING] {filename} - FILE NOT FOUND")
        continue
    
    try:
        df = pd.read_excel(filepath, nrows=0)  # Just get columns first
        columns = list(df.columns)
        
        # Now read full file for stats
        df = pd.read_excel(filepath)
        
        file_size = filepath.stat().st_size / (1024*1024)  # MB
        mod_time = filepath.stat().st_mtime
        
        # Key metrics
        total_rows = len(df)
        has_incident = df['Incident'].notna().sum() if 'Incident' in df.columns else 0
        has_disposition = df['Disposition'].notna().sum() if 'Disposition' in df.columns else 0
        has_fulladdress2 = df['FullAddress2'].notna().sum() if 'FullAddress2' in df.columns else 0
        has_response_type = df['Response Type'].notna().sum() if 'Response Type' in df.columns else 0
        
        results.append({
            'filename': filename,
            'size_mb': file_size,
            'rows': total_rows,
            'has_incident': has_incident,
            'has_disposition': has_disposition,
            'has_fulladdress2': has_fulladdress2,
            'has_response_type': has_response_type,
            'columns': len(columns),
            'mod_time': pd.Timestamp.fromtimestamp(mod_time)
        })
        
        print(f"\n[OK] {filename}")
        print(f"   Size: {file_size:.1f} MB")
        print(f"   Rows: {total_rows:,}")
        print(f"   Columns: {len(columns)}")
        print(f"   Modified: {pd.Timestamp.fromtimestamp(mod_time)}")
        print(f"   Incident coverage: {has_incident:,} ({has_incident/total_rows*100:.1f}%)")
        print(f"   Disposition coverage: {has_disposition:,} ({has_disposition/total_rows*100:.1f}%)")
        print(f"   FullAddress2 coverage: {has_fulladdress2:,} ({has_fulladdress2/total_rows*100:.1f}%)")
        print(f"   Response Type coverage: {has_response_type:,} ({has_response_type/total_rows*100:.1f}%)")
        
    except Exception as e:
        print(f"\n[ERROR] {filename} - ERROR: {e}")

# Determine most complete
if results:
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    # Score based on completeness
    for r in results:
        score = (
            r['has_incident'] / r['rows'] * 0.25 +
            r['has_disposition'] / r['rows'] * 0.25 +
            r['has_fulladdress2'] / r['rows'] * 0.25 +
            r['has_response_type'] / r['rows'] * 0.25
        )
        r['completeness_score'] = score
    
    # Sort by completeness score, then by modification time
    results.sort(key=lambda x: (x['completeness_score'], x['mod_time']), reverse=True)
    
    best = results[0]
    print(f"\n[MOST COMPLETE] {best['filename']}")
    print(f"   Completeness Score: {best['completeness_score']*100:.1f}%")
    print(f"   Modified: {best['mod_time']}")
    print(f"   Size: {best['size_mb']:.1f} MB")
    
    print(f"\n[ALL FILES RANKED BY COMPLETENESS]")
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r['filename']} - {r['completeness_score']*100:.1f}% complete")

