"""Archive old ESRI files and designate the production file."""
import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
ESRI_DIR = BASE_DIR / "data" / "ESRI_CADExport"
ARCHIVE_DIR = ESRI_DIR / "archive"

# Production file (most complete, standard format)
PRODUCTION_FILE = "CAD_ESRI_Final_20251117_v2.xlsx"

# Files to archive
FILES_TO_ARCHIVE = [
    "CAD_ESRI_Final_20251117.xlsx",           # Original
    "CAD_ESRI_Final_20251117_v3.xlsx",        # Analysis version (49 cols)
    "CAD_ESRI_Final_20251121.xlsx",           # Alternative version
]

ARCHIVE_DIR.mkdir(exist_ok=True)

print("="*80)
print("ARCHIVING ESRI FILES")
print("="*80)
print(f"\nProduction File: {PRODUCTION_FILE}")
print(f"Archive Directory: {ARCHIVE_DIR}\n")

# Archive files
archived = []
for filename in FILES_TO_ARCHIVE:
    source = ESRI_DIR / filename
    if source.exists():
        # Create archive filename with timestamp
        timestamp = datetime.fromtimestamp(source.stat().st_mtime).strftime("%Y%m%d_%H%M%S")
        archive_name = f"{timestamp}_{filename}"
        dest = ARCHIVE_DIR / archive_name
        
        print(f"Archiving: {filename}")
        print(f"  -> {archive_name}")
        shutil.move(str(source), str(dest))
        archived.append(filename)
    else:
        print(f"Skipping (not found): {filename}")

print(f"\n[SUCCESS] Archived {len(archived)} file(s)")
print(f"\nProduction file remains: {PRODUCTION_FILE}")
print(f"Archive location: {ARCHIVE_DIR}")

