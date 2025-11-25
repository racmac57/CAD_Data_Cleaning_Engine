from pathlib import Path

import pandas as pd


def find_column(df: pd.DataFrame, candidates: list[str], label: str) -> str:
    """Return the first matching column name from candidates, or raise with a clear message."""
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(
        f"Could not find a column for {label}. Tried {candidates}. "
        f"Available columns: {list(df.columns)}"
    )


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from all string columns."""
    return df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)


def main() -> None:
    base_dir = Path(
        r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"
    )

    merged_path = base_dir / "Merged_Output_optimized.xlsx"
    ref_path = base_dir / "ref" / "2019_2025_11_17_Updated_CAD_Export_manual_fix_v1.xlsx"
    raw_2019_path = base_dir / "data" / "01_raw" / "2019_ALL_CAD.xlsx"

    output_full = base_dir / "CAD_Notes_Validation_Full.csv"
    output_mismatches = base_dir / "CAD_Notes_Validation_Mismatches.csv"

    print("Loading merged output...")
    merged_df = pd.read_excel(merged_path, dtype=str, engine="openpyxl")
    merged_df = _clean_df(merged_df)

    print("Loading reference CAD (manual fix)...")
    ref_df = pd.read_excel(ref_path, dtype=str, engine="openpyxl")
    ref_df = _clean_df(ref_df)

    print("Loading raw 2019 CAD...")
    raw_df = pd.read_excel(raw_2019_path, dtype=str, engine="openpyxl")
    raw_df = _clean_df(raw_df)

    # Detect key and notes columns in each dataset
    key_col_merged = find_column(
        merged_df, ["ReportNumberNew", "ReportNumber", "CaseNumber"], "merged key"
    )
    notes_col_merged = find_column(
        merged_df, ["CADNotes", "CAD Notes", "CAD_Notes", "Notes"], "merged CAD notes"
    )

    key_col_ref = find_column(
        ref_df, ["ReportNumberNew", "ReportNumber"], "reference key"
    )
    notes_col_ref = find_column(
        ref_df, ["CADNotes", "CAD Notes", "CAD_Notes", "Notes"], "reference CAD notes"
    )
    incident_col_ref = find_column(
        ref_df, ["Incident", "Incident Type", "IncidentType"], "reference incident"
    )

    key_col_raw = find_column(
        raw_df, ["ReportNumberNew", "ReportNumber"], "raw 2019 key"
    )
    notes_col_raw = find_column(
        raw_df, ["CADNotes", "CAD Notes", "CAD_Notes", "Notes"], "raw 2019 CAD notes"
    )
    incident_col_raw = find_column(
        raw_df, ["Incident", "Incident Type", "IncidentType"], "raw 2019 incident"
    )

    print("Aligning by report number...")
    # Start from merged and bring in ref + raw context
    merged_core = merged_df[[key_col_merged, notes_col_merged]].rename(
        columns={
            key_col_merged: "ReportNumberNew",
            notes_col_merged: "CADNotes_merged",
        }
    )

    ref_core = ref_df[
        [key_col_ref, notes_col_ref, incident_col_ref]
    ].rename(
        columns={
            key_col_ref: "ReportNumberNew",
            notes_col_ref: "CADNotes_ref",
            incident_col_ref: "Incident_ref",
        }
    )

    raw_core = raw_df[
        [key_col_raw, notes_col_raw, incident_col_raw]
    ].rename(
        columns={
            key_col_raw: "ReportNumberNew",
            notes_col_raw: "CADNotes_raw",
            incident_col_raw: "Incident_raw",
        }
    )

    # Left-join to keep exactly the merged universe
    joined = (
        merged_core
        .merge(ref_core, on="ReportNumberNew", how="left")
        .merge(raw_core, on="ReportNumberNew", how="left")
    )

    # Comparison flags
    joined["match_merged_vs_ref"] = joined["CADNotes_merged"] == joined["CADNotes_ref"]
    joined["match_merged_vs_raw"] = joined["CADNotes_merged"] == joined["CADNotes_raw"]

    # Any rows where notes don't match either ref or raw, or where ref/raw is missing
    mismatches = joined[
        (~joined["match_merged_vs_ref"])
        | (~joined["match_merged_vs_raw"])
        | joined["CADNotes_ref"].isna()
        | joined["CADNotes_raw"].isna()
    ]

    print(f"Total merged rows analysed: {len(joined)}")
    print(f"Rows with potential CADNotes issues: {len(mismatches)}")

    print(f"Writing full validation to: {output_full}")
    joined.to_csv(output_full, index=False, encoding="utf-8-sig")

    print(f"Writing mismatches-only validation to: {output_mismatches}")
    mismatches.to_csv(output_mismatches, index=False, encoding="utf-8-sig")

    print("Validation complete.")


if __name__ == "__main__":
    main()


