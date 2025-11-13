### Summary
- ESRI’s reference extract has fixed headers (21 columns) and expects durations as strings, time fields as datetimes, and empty `latitude`/`longitude` (LawSoft doesn’t supply them).  
- The CAD batch script now emits ESRI-aligned samples (`Hour_Calc`, blank latitude/longitude) and an audit helper checks 9-1-1 normalization, mojibake, incident mapping, and backfilled response types.  
- Configuration for dispositions/zones/how-reported lives in `config\config_enhanced.json`; `--reload-config` hot-reloads it without editing code.  
- Incident mapping backs fills `Response Type` only when blank and logs unmapped items for CallType updates.  
- Cross-fill should combine CAD samples with RMS data (addresses, zones, grids) and optional GIS geocoding to minimize blanks before delivery to the dashboard.

### Latest Enhancements (2025-11-13)
- **Repository Trim:** Removed legacy `gis/geocoder/NJ_Geocode` binaries (>300 MB) from history so pushes stay under GitHub’s 100 MB cap. Automations should no longer expect those files on disk.
- **Follow-up Tracking:** Added `doc/reminder_tomorrow.md` as a lightweight place to capture next-day QA and delivery reminders alongside the checklist.

### Enhancements Prior to 2025-11-13
- **Text & Encoding:** `fix_mojibake` normalizes incidents, CAD notes, officer names, and dispositions; whitespace collapses across critical text fields.
- **How Reported:** All 9-1-1 variants collapse to `9-1-1`, preventing Excel from reformatting exports as dates.
- **Incident Mapping:** Matching uses a normalized key so legacy spellings map cleanly; response types are backfilled from `CallType_Categories.csv` only when missing.
- **Mapping Maintenance:** `scripts/list_unmapped_incidents.py` plus the append workflow keeps `CallType_Categories.csv` current (latest addition: `BURGLARY - RESIDENCE - 2C: 18-2`).
- **Config Reload:** `scripts/01_validate_and_clean.py` exposes CLI flags (`--config`, `--reload-config`, `--raw-dir`, `--sampling-method`) to run batches and test new JSON control lists quickly.
- **Post-run Audit:** `scripts/audit_post_fix.py` inspects every sample CSV for schema compliance, mojibake, missing mappings, and 9-1-1 drift.

### Enhancement Checklist (in recommended order)

**1. Schema & Formatting Alignment**
- Add an ESRI export helper that selects/reorders columns exactly as in `ESRI_CADExport.xlsx` (including blank `latitude`/`longitude`, `Hour_Calc` instead of `HourMinuetsCalc`).
- Ensure durations (`Time Spent`, `Time Response`) remain string formatted; datetime fields stay `datetime64`.

**2. Text Normalization & Validation Tightening**
- Extend string cleaning to collapse internal whitespace for incidents, dispositions, addresses, officers.
- Narrow the case-number regex to `^\d{2}-\d{6}([A-Z])?$` (if four-digit prefixes aren’t needed) and log top offenders.
- Uppercase categorical fields post-clean so they match validation lists exactly.

**3. Incident Mapping Feedback Loop**
- Capture any incidents that still fall into “Other” after mapping and write them to the validation report/recommended actions for CallType file updates.

**4. Address Diagnostics**
- Split the address rule into sub-checks (missing number, missing suffix/city/zip, intersection format) so failure reasons are actionable.
- Keep a report of unresolved/flagged addresses for manual review.

**5. RMS Cross-Fill**
- Build a join (by `ReportNumberNew` ↔ `Case Number`, with officer/disposition confirmations) to backfill `FullAddress2`, `PDZone`, and `Grid` from RMS exports where CAD data is missing or incomplete.
- Tag fills with provenance (`source = RMS`) for auditability.

**6. GIS / Geocode Enrichment (Optional but recommended)**
- Use the local geocoder or polygon datasets to populate missing `PDZone`, `Grid`, and optionally lat/long.
- For intersection addresses, geocode midpoint or leverage RMS before spatial join.

**7. Final ESRI Export Workflow**
- After enrichment and validation, generate both the ESRI-ready feed and an internal QA sheet (with audit columns, unmapped incidents, manual follow-up list).
- Re-run the validator on the finished dataset to confirm quality thresholds before handing it off to the dashboard team.

Let me know which checklist item you’d like to tackle first and I’ll help wire it up.

[2 tools called]

Here’s the logical plan I’ll follow so each enhancement builds cleanly on the last:

### 1. Baseline Observations
- Confirm the ESRI export columns, data types, and naming (`Hour_Calc`, blank `latitude/longitude`).
- Compare that schema with our current CAD sample output so we know the exact gaps (extra helper columns, different names, missing lat/long).

### 2. Schema Alignment
- Add an export helper that selects and orders columns exactly like the reference workbook—no extras, proper names, durations as strings, and blank latitude/longitude.
- Update the sample-export code to call that helper; keep the audit columns in a separate file so the ESRI feed stays clean.

### 3. Text & ID Normalization
- Extend string cleaning to collapse internal whitespace, then uppercase dispositions/incidents so they match validation lists.
- Tighten `ReportNumberNew` validation (e.g., enforce `YY-######` + optional single letter) and surface top failures in the report.

### 4. Incident Mapping Feedback
- Collect any incidents that still fall into “Other” after mapping and write them to the validation output, highlighting which need additions to `CallType_Categories.csv`.

### 5. Address Diagnostics
- Break the address rule into detailed checks (missing number, suffix/city/zip, intersection format) and carry reason codes into failed-records so you know exactly what to fix.

### 6. RMS Cross-Fill
- For rows with missing `FullAddress2`, `PDZone`, or `Grid`, join to RMS exports (`Case Number`, `Officer`, `Disposition == SEE REPORT`) to backfill values and note the source (CAD vs RMS).

### 7. GIS/Geocode Enrichment (Optional but Valuable)
- Use your existing `NJ_Geocode` tools or beat polygons to populate `latitude`, `longitude`, `PDZone`, and `Grid` when RMS doesn’t cover a record.
- Keep a manual follow-up list for anything still unresolved after RMS/geocode attempts.

### 8. Final QA & Delivery
- Re-run the validator on the enriched dataset to confirm all critical/important rules pass or are documented.
- Produce two outputs each run:  
  1) ESRI-ready feed with the exact column set.  
  2) QA workbook (unmapped incidents, address diagnostics, manual follow-up list).
- Hand off the ESRI feed to the dashboard team, keeping the QA sheet for data governance.

Let me know when you’re ready to start on step 2 (schema alignment) or if you’d like me to draft code for any specific step.