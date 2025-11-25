#!/usr/bin/env python
"""
Apply Unmapped Incident Backfill
================================

Uses `doc/2025_11_21_unmapped_incident.csv` to normalize / backfill
unmapped Incident values in the ESRI CAD export before running the
final cleanup (TRO/FRO + fuzzy + RMS) script.

Inputs
------
- data/ESRI_CADExport/CAD_ESRI_Final_20251117.xlsx
- doc/2025_11_21_unmapped_incident.csv

Output
------
- Overwrites data/ESRI_CADExport/CAD_ESRI_Final_20251117.xlsx in place
  with updated `Incident` values based on the "Change to" column.
"""

from pathlib import Path
from datetime import datetime

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DOC_DIR = BASE_DIR / "doc"
DATA_DIR = BASE_DIR / "data"
ESRI_DIR = DATA_DIR / "ESRI_CADExport"

CAD_FILE = ESRI_DIR / "CAD_ESRI_Final_20251117_v2.xlsx"  # Production file
UNMAPPED_FILE = DOC_DIR / "2025_11_21_unmapped_incident.csv"


def main():
    print("=" * 60)
    print("APPLY UNMAPPED INCIDENT BACKFILL")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not CAD_FILE.exists():
        raise FileNotFoundError(f"CAD ESRI export not found: {CAD_FILE}")
    if not UNMAPPED_FILE.exists():
        raise FileNotFoundError(f"Unmapped incident mapping file not found: {UNMAPPED_FILE}")

    # Load CAD ESRI export
    cad_df = pd.read_excel(CAD_FILE, engine="openpyxl")
    if "Incident" not in cad_df.columns:
        raise RuntimeError("CAD export is missing required 'Incident' column")

    print(f"Loaded CAD file: {CAD_FILE.name} ({len(cad_df):,} records)")

    # Load unmapped incident mapping (Rank,Incident,Count,Sample Report#,Change to)
    mapping_df = pd.read_csv(UNMAPPED_FILE, dtype=str).fillna("")
    expected_cols = {"Incident", "Change to "}
    missing = expected_cols.difference(mapping_df.columns)
    if missing:
        raise RuntimeError(
            f"Unmapped incident CSV is missing expected columns: {', '.join(sorted(missing))}"
        )

    # Build mapping dict: original Incident -> new Incident
    mapping = (
        mapping_df[["Incident", "Change to "]]
        .rename(columns={"Change to ": "ChangeTo"})
        .query("Incident != '' and ChangeTo != ''")
    )
    incident_map = dict(
        zip(mapping["Incident"].astype(str).str.strip(), mapping["ChangeTo"].astype(str).str.strip())
    )

    print(f"Loaded {len(incident_map):,} unmapped incident backfill rules")

    # Apply mapping
    before_unique = cad_df["Incident"].nunique(dropna=False)
    changed_rows = 0

    def _apply_change(incident: object) -> object:
        nonlocal changed_rows
        if pd.isna(incident):
            return incident
        s = str(incident).strip()
        if s in incident_map:
            changed_rows += 1
            return incident_map[s]
        return incident

    cad_df["Incident"] = cad_df["Incident"].apply(_apply_change)

    after_unique = cad_df["Incident"].nunique(dropna=False)

    print(f"Rows updated: {changed_rows:,}")
    print(f"Unique Incident values before: {before_unique:,}")
    print(f"Unique Incident values after:  {after_unique:,}")

    # Save back to the same CAD file (in place)
    cad_df.to_excel(CAD_FILE, index=False)
    print(f"Updated CAD file saved: {CAD_FILE}")

    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()


