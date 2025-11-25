# Changelog

All notable changes to the CAD Data Cleaning Engine project.

## [2025-11-24] - Address Corrections System & Hour Field Fix

### Added
- **Address Corrections Pipeline**:
  - `scripts/backfill_incomplete_addresses_from_rms.py`: Backfills incomplete addresses from RMS export
  - `scripts/apply_address_rule_corrections.py`: Applies rule-based corrections from CSV
  - `scripts/apply_street_names_corrections.py`: Uses official street names to correct addresses
  - `scripts/apply_address_standardization.py`: Expands abbreviations and standardizes formatting
  - `scripts/verify_addresses_against_street_names.py`: Verifies addresses against official street names
  - `scripts/identify_manual_corrections_needed.py`: Identifies records needing manual correction
  - `scripts/merge_manual_review_updates.py`: Merges manual review updates
  - `scripts/verify_hour_field.py`: Verifies Hour field extraction

### Changed
- **Hour Field Extraction**: Updated `scripts/apply_manual_corrections.py` to extract exact HH:mm from TimeOfCall without rounding (previously rounded to HH:00)
- **Address Standardization**: Integrated official Hackensack street names file for verification and abbreviation expansion

### Fixed
- Address abbreviations (St → Street, Terr → Terrace, Ave → Avenue)
- Extra spaces before commas in addresses
- Specific address corrections (Doremus Avenue to Newark, Palisades Avenue to Cliffside Park)
- Complete street name verification (Parkway, Colonial Terrace, Broadway, East Broadway, The Esplanade, Cambridge Terrace)

### Results
- **Address Corrections**: 9,607 corrections applied to ESRI production file
- **Completion Rate**: 99.5% (1,688 of 1,696 records corrected)
- **Hour Field**: 728,593 records updated with exact time values
- **Total Corrections**: 1,270,339 corrections applied to final ESRI export

## [2025-11-22] - CAD/RMS Integration & Validation

### Added
- `scripts/merge_cad_rms_incidents.py`: Joins cleaned CAD exports to RMS export
- `scripts/validate_cad_notes_alignment.py`: Compares CADNotes across exports
- `scripts/compare_merged_to_manual_csv.py`: Verifies field synchronization

## [2025-11-21] - FullAddress2 Corrections & ESRI Production Deployment

### Added
- Rule-based `FullAddress2` corrections using `doc/updates_corrections_FullAddress2.csv`
- ESRI production deployment path (`scripts/esri_production_deploy.py`)
- Final Response_Type cleanup pipeline (`scripts/final_cleanup_tro_fuzzy_rms.py`)
- Address backfill pass (`scripts/backfill_address_from_rms.py`)
- Review artifacts in `data/02_reports/`:
  - `tro_fro_manual_review.csv`
  - `unmapped_final_report.md`
  - `unmapped_breakdown_summary.csv`
  - `unmapped_cases_for_manual_backfill.csv`
  - `fuzzy_review.csv`
  - `address_backfill_from_rms_report.md`
  - `address_backfill_from_rms_log.csv`

### Changed
- ESRI sample exports now pull `Incident` text and `Response Type` directly from `CallType_Categories.csv`
- Title-case key human-readable fields
- Wrap `9-1-1` with Excel guard
- Write with UTF-8 BOM for proper en dash rendering

### Results
- ~99.96% Response_Type coverage achieved
- Improved valid address rate via RMS backfill

## [2025-11-21-b] - ESRI Rebuild, Final Cleanup, and Address Backfill

### Added
- Full pipeline rebuild for ESRI production deployment
- Unmapped incident reduction: 3,155 → 309 (99.96% coverage)
- RMS address backfill: 597,480 → 598,119 valid addresses (+639)
- New scripts:
  - `scripts/esri_production_deploy.py`
  - `scripts/final_cleanup_tro_fuzzy_rms.py`
  - `scripts/backfill_address_from_rms.py`
  - `scripts/apply_unmapped_incident_backfill.py`

### Results
- Response_Type coverage: 99.96%
- Address quality improvement: +639 valid addresses from RMS backfill

