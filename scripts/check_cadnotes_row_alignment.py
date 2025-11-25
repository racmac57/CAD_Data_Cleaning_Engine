"""
Check if CADNotes are aligned to the correct ReportNumberNew rows.

This compares the merged output (which has correct alignment) against
the manual CSV to see if CADNotes shifted to wrong rows.
"""
from pathlib import Path

import pandas as pd


def main() -> None:
    base_dir = Path(
        r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"
    )

    merged_path = base_dir / "Merged_Output_optimized.xlsx"
    manual_csv_path = (
        base_dir / "2019_2025_11_17_Updated_CAD_Export_manual_fix_v1.csv"
    )

    output_path = base_dir / "CADNotes_Row_Alignment_Issues.csv"

    print("=" * 70)
    print("CHECKING CAD NOTES ROW ALIGNMENT")
    print("=" * 70)

    # Load merged (source of truth)
    print("\n1. Loading merged output...")
    merged_df = pd.read_excel(
        merged_path,
        dtype={"ReportNumberNew": str},
        engine="openpyxl",
    )
    merged_df["ReportNumberNew"] = merged_df["ReportNumberNew"].astype(str).str.strip()
    
    # Normalize CADNotes (remove leading apostrophe)
    if "CADNotes" in merged_df.columns:
        merged_df["CADNotes_norm"] = (
            merged_df["CADNotes"].astype(str).str.lstrip("'").str.strip()
        )
    else:
        merged_df["CADNotes_norm"] = ""

    print(f"   ✓ Loaded {len(merged_df):,} rows")

    # Load manual CSV
    print("\n2. Loading manual CSV...")
    manual_df = pd.read_csv(
        manual_csv_path,
        dtype={"ReportNumberNew": str},
        low_memory=False,
    )
    manual_df["ReportNumberNew"] = manual_df["ReportNumberNew"].astype(str).str.strip()
    
    if "CADNotes" in manual_df.columns:
        manual_df["CADNotes_norm"] = (
            manual_df["CADNotes"].astype(str).str.strip()
        )
    else:
        manual_df["CADNotes_norm"] = ""

    print(f"   ✓ Loaded {len(manual_df):,} rows")

    # Filter manual to only the ReportNumberNew values that exist in merged
    target_rns = set(merged_df["ReportNumberNew"].dropna().unique())
    manual_filtered = manual_df[manual_df["ReportNumberNew"].isin(target_rns)].copy()
    
    print(f"\n3. Filtering manual CSV to {len(target_rns):,} target ReportNumberNew values...")
    print(f"   ✓ Found {len(manual_filtered):,} matching rows in manual CSV")

    # Join on ReportNumberNew to compare CADNotes
    print("\n4. Comparing CADNotes alignment...")
    comparison = merged_df[["ReportNumberNew", "CADNotes_norm"]].merge(
        manual_filtered[["ReportNumberNew", "CADNotes_norm"]],
        on="ReportNumberNew",
        how="left",
        suffixes=("_merged", "_manual"),
    )

    # Check if notes match
    comparison["CADNotes_Match"] = (
        comparison["CADNotes_norm_merged"] == comparison["CADNotes_norm_manual"]
    )
    comparison["CADNotes_Mismatch"] = ~comparison["CADNotes_Match"]

    # Fill NaN in manual notes (means row not found)
    comparison["CADNotes_norm_manual"] = comparison["CADNotes_norm_manual"].fillna("NOT_FOUND_IN_MANUAL")

    match_count = comparison["CADNotes_Match"].sum()
    mismatch_count = comparison["CADNotes_Mismatch"].sum()

    print(f"\n   ✓ CADNotes match exactly: {match_count:,} rows")
    print(f"   ⚠️  CADNotes mismatch: {mismatch_count:,} rows")

    # Show sample of mismatches
    if mismatch_count > 0:
        print("\n5. Sample of CADNotes mismatches:")
        mismatches = comparison[comparison["CADNotes_Mismatch"]].head(10)
        
        for idx, row in mismatches.iterrows():
            print(f"\n   ReportNumberNew: {row['ReportNumberNew']}")
            merged_note = str(row["CADNotes_norm_merged"])[:80]
            manual_note = str(row["CADNotes_norm_manual"])[:80]
            print(f"   Merged:  {merged_note}...")
            print(f"   Manual:  {manual_note}...")

        # Export full details
        output_cols = [
            "ReportNumberNew",
            "CADNotes_norm_merged",
            "CADNotes_norm_manual",
            "CADNotes_Match",
        ]
        comparison[output_cols].to_csv(output_path, index=False)
        print(f"\n   ✓ Full comparison exported to: {output_path}")

        # Check if manual CSV has duplicate ReportNumberNew
        duplicates = manual_filtered[manual_filtered["ReportNumberNew"].duplicated(keep=False)]
        if len(duplicates) > 0:
            print(f"\n   ⚠️  WARNING: Found {len(duplicates)} duplicate ReportNumberNew in manual CSV!")
            print("   This could cause CADNotes misalignment.")
            dup_rns = duplicates["ReportNumberNew"].unique()[:10]
            print(f"   Sample duplicate ReportNumberNew: {list(dup_rns)}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if mismatch_count == 0:
        print("✓ All CADNotes are correctly aligned!")
    else:
        print(f"⚠️  {mismatch_count:,} CADNotes may be misaligned or edited.")
        print("\n   Possible causes:")
        print("   1. Copy-paste operations that moved notes to wrong rows")
        print("   2. Sorting/filtering that reordered rows")
        print("   3. Manual edits to CADNotes column")
        print("   4. Excel table operations that shifted data")
        print(f"\n   Check: {output_path}")

    print("=" * 70)


if __name__ == "__main__":
    main()

