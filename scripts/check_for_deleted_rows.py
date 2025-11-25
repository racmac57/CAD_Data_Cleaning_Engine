"""
Diagnostic script to check if rows were accidentally deleted during manual editing.

Compares ReportNumberNew values between:
1. Merged output (source of truth)
2. Manual CSV (the file you edited)

Reports:
- Rows in merged that are MISSING from manual CSV (likely deleted)
- Rows in manual CSV that are NOT in merged (extra rows)
- Row count differences
- Sample of missing ReportNumberNew values
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

    output_path = base_dir / "Row_Deletion_Analysis.csv"

    print("=" * 70)
    print("CHECKING FOR DELETED ROWS IN MANUAL CSV")
    print("=" * 70)

    # Load both files
    print("\n1. Loading merged output (source of truth)...")
    merged_df = pd.read_excel(merged_path, dtype={"ReportNumberNew": str}, engine="openpyxl")
    merged_df["ReportNumberNew"] = merged_df["ReportNumberNew"].astype(str).str.strip()
    merged_df = merged_df.dropna(subset=["ReportNumberNew"])
    merged_set = set(merged_df["ReportNumberNew"].unique())

    print(f"   ✓ Loaded {len(merged_df):,} rows")
    print(f"   ✓ Unique ReportNumberNew: {len(merged_set):,}")

    print("\n2. Loading manual CSV (the file you edited)...")
    manual_df = pd.read_csv(manual_csv_path, dtype={"ReportNumberNew": str})
    manual_df["ReportNumberNew"] = manual_df["ReportNumberNew"].astype(str).str.strip()
    manual_df = manual_df.dropna(subset=["ReportNumberNew"])
    manual_set = set(manual_df["ReportNumberNew"].unique())

    print(f"   ✓ Loaded {len(manual_df):,} rows")
    print(f"   ✓ Unique ReportNumberNew: {len(manual_set):,}")

    # Find differences
    print("\n3. Comparing ReportNumberNew values...")
    missing_from_manual = merged_set - manual_set  # In merged, NOT in manual (DELETED)
    extra_in_manual = manual_set - merged_set  # In manual, NOT in merged (EXTRA)

    print(f"\n   ⚠️  MISSING FROM MANUAL CSV (likely deleted): {len(missing_from_manual):,}")
    print(f"   ℹ️  EXTRA IN MANUAL CSV (not in merged): {len(extra_in_manual):,}")

    # Show sample of missing rows
    if missing_from_manual:
        print("\n4. Sample of deleted ReportNumberNew values:")
        sample_deleted = sorted(list(missing_from_manual))[:20]
        for i, rn in enumerate(sample_deleted, 1):
            print(f"   {i:2d}. {rn}")
        if len(missing_from_manual) > 20:
            print(f"   ... and {len(missing_from_manual) - 20} more")

        # Get full details of deleted rows from merged
        deleted_rows = merged_df[merged_df["ReportNumberNew"].isin(missing_from_manual)].copy()
        
        # Add metadata columns
        deleted_rows["Status"] = "MISSING_FROM_MANUAL"
        deleted_rows["Incident"] = deleted_rows.get("Incident", pd.Series())
        deleted_rows["FullAddress2"] = deleted_rows.get("FullAddress2", pd.Series())
        deleted_rows["CADNotes_Preview"] = (
            deleted_rows.get("CADNotes", pd.Series())
            .astype(str)
            .str[:100]
            .fillna("")
        )

        # Export full details
        output_cols = ["ReportNumberNew", "Status", "Incident", "FullAddress2", "CADNotes_Preview"]
        output_cols = [c for c in output_cols if c in deleted_rows.columns]
        deleted_rows[output_cols].to_csv(output_path, index=False)

        print(f"\n   ✓ Full details exported to: {output_path}")
        print(f"   ✓ Total deleted rows: {len(deleted_rows):,}")

        # Check if deleted rows have specific incident patterns
        if "Incident" in deleted_rows.columns:
            print("\n5. Incident types of deleted rows:")
            incident_counts = deleted_rows["Incident"].value_counts().head(10)
            for incident, count in incident_counts.items():
                print(f"   - {incident}: {count:,}")

    if extra_in_manual:
        print("\n6. Extra ReportNumberNew values in manual CSV (not in merged):")
        sample_extra = sorted(list(extra_in_manual))[:10]
        for i, rn in enumerate(sample_extra, 1):
            print(f"   {i:2d}. {rn}")
        if len(extra_in_manual) > 10:
            print(f"   ... and {len(extra_in_manual) - 10} more")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Merged file has:     {len(merged_set):,} unique ReportNumberNew")
    print(f"Manual CSV has:      {len(manual_set):,} unique ReportNumberNew")
    print(f"Difference:          {len(merged_set) - len(manual_set):,} rows")

    if missing_from_manual:
        print(f"\n⚠️  WARNING: {len(missing_from_manual):,} ReportNumberNew values are")
        print("   in the merged file but MISSING from your manual CSV.")
        print("   This suggests rows may have been accidentally deleted during editing.")
        print(f"\n   Check: {output_path}")
        print("\n   Common causes:")
        print("   - Filtering and deleting visible rows (deletes hidden rows too in some cases)")
        print("   - Accidentally selecting entire rows and deleting them")
        print("   - Copy-paste overwriting rows")
        print("   - Excel table filter issues")
    else:
        print("\n✓ No missing ReportNumberNew values found!")
        print("  All rows from merged file are present in manual CSV.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

