#!/usr/bin/env python
"""
Check if pipeline completed successfully and list all generated outputs.
"""

from pathlib import Path
from datetime import datetime
import sys

def check_pipeline_completion(timestamp_prefix: str = None):
    """Check pipeline outputs for a given timestamp."""
    project_root = Path(__file__).parent.parent
    
    esri_dir = project_root / 'data' / 'ESRI_CADExport'
    reports_dir = project_root / 'data' / '02_reports' / 'data_quality'
    
    print("="*80)
    print("PIPELINE COMPLETION CHECK")
    print("="*80)
    print()
    
    # Find files by timestamp or latest
    if timestamp_prefix:
        pattern = f"*{timestamp_prefix}*"
    else:
        # Find latest files
        esri_files = list(esri_dir.glob("CAD_ESRI_*"))
        if esri_files:
            # Extract timestamp from most recent file
            latest = max(esri_files, key=lambda p: p.stat().st_mtime)
            # Extract timestamp pattern (YYYYMMDD_HHMMSS)
            import re
            match = re.search(r'(\d{8}_\d{6})', latest.name)
            if match:
                timestamp_prefix = match.group(1)
                pattern = f"*{timestamp_prefix}*"
            else:
                pattern = "*"
        else:
            pattern = "*"
    
    print(f"Checking for files matching: *{timestamp_prefix}*")
    print()
    
    # Check ESRI outputs
    print("[1] ESRI Output Files:")
    esri_files = list(esri_dir.glob(f"CAD_ESRI_*{timestamp_prefix}*")) if timestamp_prefix else list(esri_dir.glob("CAD_ESRI_*"))
    esri_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    expected_esri = {
        'DRAFT': False,
        'POLISHED_PRE_GEOCODE': False,
        'POLISHED': False
    }
    
    for file in esri_files[:10]:  # Show latest 10
        size_mb = file.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(file.stat().st_mtime)
        
        if 'DRAFT' in file.name:
            expected_esri['DRAFT'] = True
            status = "[OK]"
        elif 'POLISHED_PRE_GEOCODE' in file.name:
            expected_esri['POLISHED_PRE_GEOCODE'] = True
            status = "[OK]"
        elif 'POLISHED' in file.name and 'PRE_GEOCODE' not in file.name:
            expected_esri['POLISHED'] = True
            status = "[OK]"
        else:
            status = "[?]"
        
        print(f"  {status} {file.name}")
        print(f"      Size: {size_mb:.1f} MB | Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print()
    
    # Check data quality reports
    print("[2] Data Quality Reports:")
    if reports_dir.exists():
        report_files = list(reports_dir.glob(f"*{timestamp_prefix}*")) if timestamp_prefix else list(reports_dir.glob("*"))
        report_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        null_reports = [f for f in report_files if 'NULL_VALUES' in f.name]
        summary_reports = [f for f in report_files if 'PROCESSING_SUMMARY' in f.name]
        
        if null_reports:
            print(f"  [OK] Null value reports: {len(null_reports)} file(s)")
            for f in null_reports[:5]:  # Show first 5
                size_kb = f.stat().st_size / 1024
                print(f"      - {f.name} ({size_kb:.1f} KB)")
        else:
            print("  [WARN] No null value reports found")
        
        if summary_reports:
            print(f"  [OK] Processing summary: {len(summary_reports)} file(s)")
            for f in summary_reports:
                size_kb = f.stat().st_size / 1024
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                print(f"      - {f.name} ({size_kb:.1f} KB, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
        else:
            print("  [WARN] No processing summary found")
    else:
        print("  [WARN] data_quality directory does not exist")
    
    print()
    
    # Summary
    print("="*80)
    print("COMPLETION STATUS")
    print("="*80)
    
    all_ok = True
    
    if expected_esri['DRAFT']:
        print("[OK] Draft output generated")
    else:
        print("[MISSING] Draft output")
        all_ok = False
    
    if expected_esri['POLISHED_PRE_GEOCODE']:
        print("[OK] Pre-geocoding polished output generated")
    else:
        print("[MISSING] Pre-geocoding polished output")
        all_ok = False
    
    if expected_esri['POLISHED']:
        print("[OK] Final polished output generated (after geocoding)")
    else:
        print("[INFO] Final polished output not yet generated (geocoding step pending)")
    
    if reports_dir.exists() and (null_reports or summary_reports):
        print("[OK] Data quality reports generated")
    else:
        print("[WARN] Data quality reports may be missing")
    
    print()
    
    if all_ok and expected_esri['POLISHED_PRE_GEOCODE']:
        print("[SUCCESS] Pre-geocoding outputs complete!")
        print("Next step: Run geocoding to generate final polished output")
    elif expected_esri['POLISHED']:
        print("[SUCCESS] Pipeline fully complete!")
    else:
        print("[INCOMPLETE] Some outputs may be missing")
    
    print("="*80)
    
    return all_ok


if __name__ == "__main__":
    timestamp = sys.argv[1] if len(sys.argv) > 1 else None
    success = check_pipeline_completion(timestamp)
    sys.exit(0 if success else 1)

