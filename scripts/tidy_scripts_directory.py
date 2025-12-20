#!/usr/bin/env python
"""
Tidy up the scripts directory by organizing files into appropriate subdirectories.

Organizes:
- JSON validation reports → data/02_reports/cad_validation/
- Backup files → scripts/archive/
- Old/unused scripts → scripts/archive/
"""

import shutil
from pathlib import Path
from datetime import datetime
import json

def tidy_scripts_directory():
    """Organize scripts directory."""
    scripts_dir = Path(__file__).parent
    project_root = scripts_dir.parent
    
    # Create directories if needed
    reports_dir = project_root / 'data' / '02_reports' / 'cad_validation'
    archive_dir = scripts_dir / 'archive'
    reports_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    moved_files = []
    errors = []
    
    print("="*80)
    print("TIDYING SCRIPTS DIRECTORY")
    print("="*80)
    print(f"Scripts directory: {scripts_dir}")
    print()
    
    # 1. Move JSON validation reports
    print("[1] Moving JSON validation reports...")
    json_files = list(scripts_dir.glob('*_cad_validation_report_*.json'))
    json_files.extend(scripts_dir.glob('cad_validation_report_*.json'))
    
    for json_file in json_files:
        try:
            dest = reports_dir / json_file.name
            if dest.exists():
                # Add timestamp to avoid overwrite
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                dest = reports_dir / f"{json_file.stem}_{timestamp}{json_file.suffix}"
            shutil.move(str(json_file), str(dest))
            moved_files.append(('report', json_file.name, str(dest)))
            print(f"  Moved: {json_file.name} -> {dest.relative_to(project_root)}")
        except Exception as e:
            errors.append((json_file.name, str(e)))
            print(f"  ERROR moving {json_file.name}: {e}")
    
    print(f"  Moved {len(json_files)} validation report(s)")
    print()
    
    # 2. Move backup files
    print("[2] Moving backup files...")
    backup_patterns = [
        '*_backup*.py',
        '*_OLD.py',
        '*_OLD_*.py',
        'master_pipeline_OLD.py',
        'convert_excel_to_csv_OLD.py',
        'generate_esri_output_backup.py',
        'geocode_nj_locator_backup.py'
    ]
    
    backup_files = []
    for pattern in backup_patterns:
        backup_files.extend(scripts_dir.glob(pattern))
    
    for backup_file in backup_files:
        try:
            dest = archive_dir / backup_file.name
            if dest.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                dest = archive_dir / f"{backup_file.stem}_{timestamp}{backup_file.suffix}"
            shutil.move(str(backup_file), str(dest))
            moved_files.append(('backup', backup_file.name, str(dest)))
            print(f"  Moved: {backup_file.name} -> {dest.relative_to(project_root)}")
        except Exception as e:
            errors.append((backup_file.name, str(e)))
            print(f"  ERROR moving {backup_file.name}: {e}")
    
    print(f"  Moved {len(backup_files)} backup file(s)")
    print()
    
    # 3. Move old/unused scripts (one-time use scripts that are no longer needed)
    print("[3] Identifying old/unused scripts...")
    old_scripts = [
        'process_new_dataset.py',  # Replaced by process_new_dataset_complete.py
        'process_new_dataset_complete.py',  # One-time use, can archive
        'compare_outputs.py',  # One-time use
        'check_output_stats.py',  # Utility, can archive
        'investigate_record_count.py',  # One-time diagnostic
        'fix_geocoding_duplicates.py',  # One-time fix
        'fix_existing_geocoded_file.py',  # One-time fix
        'analyze_geocoding_duplicates.py',  # One-time diagnostic
    ]
    
    moved_old = 0
    for script_name in old_scripts:
        script_path = scripts_dir / script_name
        if script_path.exists():
            try:
                dest = archive_dir / script_name
                if dest.exists():
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    dest = archive_dir / f"{script_path.stem}_{timestamp}{script_path.suffix}"
                shutil.move(str(script_path), str(dest))
                moved_files.append(('old_script', script_name, str(dest)))
                moved_old += 1
                print(f"  Archived: {script_name} -> {dest.relative_to(project_root)}")
            except Exception as e:
                errors.append((script_name, str(e)))
                print(f"  ERROR archiving {script_name}: {e}")
    
    print(f"  Archived {moved_old} old script(s)")
    print()
    
    # 4. Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total files moved: {len(moved_files)}")
    print(f"  - Validation reports: {sum(1 for t, _, _ in moved_files if t == 'report')}")
    print(f"  - Backup files: {sum(1 for t, _, _ in moved_files if t == 'backup')}")
    print(f"  - Old scripts: {sum(1 for t, _, _ in moved_files if t == 'old_script')}")
    
    if errors:
        print(f"\nErrors: {len(errors)}")
        for filename, error in errors:
            print(f"  - {filename}: {error}")
    else:
        print("\n[SUCCESS] All files moved successfully!")
    
    print()
    print("Remaining files in scripts directory:")
    remaining = [f for f in scripts_dir.iterdir() if f.is_file() and f.suffix == '.py']
    print(f"  Python scripts: {len(remaining)}")
    print(f"  Batch files: {len(list(scripts_dir.glob('*.bat')))}")
    print()
    print("="*80)
    
    return len(moved_files), len(errors)


if __name__ == "__main__":
    moved, errors = tidy_scripts_directory()
    exit(0 if errors == 0 else 1)

