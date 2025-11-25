from pathlib import Path
import pandas as pd


def _escape_excel_formula(val):
    """
    Prevent Excel from treating string values as formulas.
    Any string starting with =, +, -, or @ is prefixed with a single quote.
    """
    if isinstance(val, str) and val and val[0] in ("=", "+", "-", "@"):
        return "'" + val
    return val


# --- PATHS ---
base_dir = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")

cad_path = base_dir / "ref" / "2019_2025_11_17_Updated_CAD_Export_manual_fix_v1.xlsx"
rms_path = base_dir / "data" / "rms" / "2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx"
output_path = base_dir / "Merged_Output_optimized.xlsx"

# --- CONFIG ---
target_incidents = {
    "Applicant Taxi / Limo",
    "Attempted Burglary 2C:18-2",
    "Burglary 2C:18-2",
    "Missing Person",
    "Missing Person- Return",
    "Service of TRO / FRO",
    "Targeted Area Patrol",
    "Violation: TRO/ FRO 2C:25-31",
    "Violation: TRO/ FRO 2C:29-9b",
}

cad_cols = [
    "ReportNumberNew",
    "Incident",
    "How Reported",
    "FullAddress2",
    "Disposition",
    "Response Type",
    "CADNotes",
]
rms_cols = [
    "Case Number",
    "Incident Type_1",
    "FullAddress",
    "Narrative",
]

print("Loading CAD...")
df_cad = pd.read_excel(
    cad_path,
    usecols=cad_cols,
    dtype=str,
    engine="openpyxl",
    sheet_name=0,
)
df_cad = df_cad.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

print("Loading RMS...")
df_rms = pd.read_excel(
    rms_path,
    usecols=rms_cols,
    dtype=str,
    engine="openpyxl",
    sheet_name=0,
)
df_rms["Case Number"] = df_rms["Case Number"].str.strip()

# Optional: drop duplicates on keys early
df_cad = df_cad.drop_duplicates(subset=["ReportNumberNew"])
df_rms = df_rms.drop_duplicates(subset=["Case Number"])

print("Filtering CAD by incidents...")
filtered = df_cad[df_cad["Incident"].isin(target_incidents)]
print(f"Filtered CAD rows: {len(filtered)}")

if filtered.empty:
    print("No CAD records matched the incident list. Exiting.")
else:
    print("Merging...")
    merged = filtered.merge(
        df_rms,
        left_on="ReportNumberNew",
        right_on="Case Number",
        how="inner",
    )

    # Keep both keys + other columns
    output_cols = ["ReportNumberNew", "Case Number"] + cad_cols[1:] + rms_cols[1:]
    output_cols = [c for c in output_cols if c in merged.columns]

    final_df = merged[output_cols].applymap(_escape_excel_formula)

    final_df.to_excel(output_path, index=False)
    print(f"Done. {len(final_df)} rows exported to {output_path}")