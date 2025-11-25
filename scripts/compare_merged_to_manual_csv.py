from pathlib import Path

import pandas as pd


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from all string columns."""
    return df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)


def _normalize_notes(s: pd.Series) -> pd.Series:
    """
    Normalise CAD notes for comparison:
    - remove leading apostrophe we added to avoid Excel formulas
    - strip whitespace
    """
    s = s.fillna("")
    return s.map(lambda v: v.lstrip("'").strip() if isinstance(v, str) else v)


def main() -> None:
    base_dir = Path(
        r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"
    )

    merged_path = base_dir / "Merged_Output_optimized.xlsx"
    manual_csv_path = (
        base_dir / "2019_2025_11_17_Updated_CAD_Export_manual_fix_v1.csv"
    )

    output_full = base_dir / "Merged_vs_Manual_Full.csv"
    output_mismatches = base_dir / "Merged_vs_Manual_Mismatches.csv"

    print("Loading merged output...")
    merged_df = pd.read_excel(merged_path, dtype=str, engine="openpyxl")
    merged_df = _clean_df(merged_df)

    print("Loading manually edited CAD CSV...")
    manual_df = pd.read_csv(manual_csv_path, dtype=str)
    manual_df = _clean_df(manual_df)

    if "ReportNumberNew" not in merged_df.columns:
        raise KeyError(
            "Column 'ReportNumberNew' not found in merged output. "
            f"Available columns: {list(merged_df.columns)}"
        )
    if "ReportNumberNew" not in manual_df.columns:
        raise KeyError(
            "Column 'ReportNumberNew' not found in manual CSV. "
            f"Available columns: {list(manual_df.columns)}"
        )

    # Columns we care most about comparing
    compare_cols = [
        "Incident",
        "How Reported",
        "FullAddress2",
        "Disposition",
        "Response Type",
        "CADNotes",
    ]

    # Restrict manual_df to relevant columns plus key
    manual_subset_cols = ["ReportNumberNew"] + [
        c for c in compare_cols if c in manual_df.columns
    ]
    manual_core = manual_df[manual_subset_cols].copy()
    manual_core = manual_core.add_suffix("_manual")
    manual_core = manual_core.rename(
        columns={"ReportNumberNew_manual": "ReportNumberNew"}
    )

    merged_subset_cols = ["ReportNumberNew"] + [
        c for c in compare_cols if c in merged_df.columns
    ]
    merged_core = merged_df[merged_subset_cols].copy()
    merged_core = merged_core.add_suffix("_merged")
    merged_core = merged_core.rename(
        columns={"ReportNumberNew_merged": "ReportNumberNew"}
    )

    print("Joining merged output with manual CSV on ReportNumberNew...")
    joined = merged_core.merge(manual_core, on="ReportNumberNew", how="left")

    # Normalised views for CADNotes comparison
    if "CADNotes_merged" in joined.columns:
        joined["CADNotes_merged_norm"] = _normalize_notes(joined["CADNotes_merged"])
    else:
        joined["CADNotes_merged_norm"] = ""
    if "CADNotes_manual" in joined.columns:
        joined["CADNotes_manual_norm"] = _normalize_notes(joined["CADNotes_manual"])
    else:
        joined["CADNotes_manual_norm"] = ""

    # Build per-column match flags (using normalised notes for CADNotes)
    for col in compare_cols:
        merged_col = f"{col}_merged"
        manual_col = f"{col}_manual"
        flag_col = f"match_{col.replace(' ', '_')}"

        if col == "CADNotes":
            # use normalised versions
            joined[flag_col] = (
                joined["CADNotes_merged_norm"] == joined["CADNotes_manual_norm"]
            )
        else:
            if merged_col in joined.columns and manual_col in joined.columns:
                joined[flag_col] = joined[merged_col] == joined[manual_col]
            else:
                joined[flag_col] = pd.NA

    # Any row where at least one important field does not match exactly
    flag_cols = [c for c in joined.columns if c.startswith("match_")]
    mismatches_mask = False
    for c in flag_cols:
        mismatches_mask = mismatches_mask | (joined[c] == False)  # noqa: E712

    mismatches = joined[mismatches_mask].copy()

    print(f"Total merged rows analysed: {len(joined)}")
    print(f"Rows with at least one mismatch: {len(mismatches)}")

    print(f"Writing full comparison to: {output_full}")
    joined.to_csv(output_full, index=False, encoding="utf-8-sig")

    print(f"Writing mismatches-only comparison to: {output_mismatches}")
    mismatches.to_csv(output_mismatches, index=False, encoding="utf-8-sig")

    print("Comparison complete.")


if __name__ == "__main__":
    main()


