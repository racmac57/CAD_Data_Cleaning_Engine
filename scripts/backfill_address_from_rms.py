#!/usr/bin/env python
"""
Address Backfill From RMS + Briefing Report
===========================================

Goal
- Improve CAD FullAddress2 quality using RMS addresses
- Join on ReportNumberNew (CAD) ↔ Case Number (RMS) with normalized keys
- Overwrite only when RMS address validates as geocodable by pattern rules
- Produce a Markdown briefing and a detailed backfill log

Input
- data/ESRI_CADExport/CAD_ESRI_Final_20251117_v2.xlsx
- data/rms/2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx

Output
- data/ESRI_CADExport/CAD_ESRI_Final_20251117_v3.xlsx
- data/02_reports/address_backfill_from_rms_log.csv
- data/02_reports/address_backfill_from_rms_report.md
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
from collections import Counter


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Backtrack from this file:
# <repo_root>/scripts/backfill_addresses_from_rms.py
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
ESRI_DIR = DATA_DIR / "ESRI_CADExport"
RMS_DIR = DATA_DIR / "rms"
REPORTS_DIR = DATA_DIR / "02_reports"

CAD_INPUT = ESRI_DIR / "CAD_ESRI_Final_20251117_v2.xlsx"
CAD_OUTPUT = ESRI_DIR / "CAD_ESRI_Final_20251117_v3.xlsx"
RMS_INPUT = RMS_DIR / "2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx"

BACKFILL_LOG = REPORTS_DIR / "address_backfill_from_rms_log.csv"
REPORT_FILE = REPORTS_DIR / "address_backfill_from_rms_report.md"


# ---------------------------------------------------------------------------
# Address classification helpers
# ---------------------------------------------------------------------------

STREET_TYPES = [
    "STREET", "ST", "AVENUE", "AVE", "ROAD", "RD", "DRIVE", "DR", "LANE", "LN",
    "BOULEVARD", "BLVD", "COURT", "CT", "PLACE", "PL", "CIRCLE", "CIR",
    "TERRACE", "TER", "WAY", "PARKWAY", "PKWY", "HIGHWAY", "HWY", "PLAZA",
    "SQUARE", "SQ", "TRAIL", "TRL", "PATH", "ALLEY", "WALK", "EXPRESSWAY",
    "TURNPIKE", "TPKE", "ROUTE", "RT"
]

GENERIC_TERMS = [
    "HOME", "VARIOUS", "UNKNOWN", "PARKING GARAGE", "REAR LOT", "PARKING LOT",
    "LOT", "GARAGE", "REAR", "FRONT", "SIDE", "BEHIND", "ACROSS", "NEAR",
    "BETWEEN", "AREA", "LOCATION", "SCENE", "UNDETERMINED", "N/A", "NA",
    "NONE", "BLANK", "PARK"
]

STREET_REGEX = r"\b(?:" + "|".join(STREET_TYPES) + r")\b"
CITY_STATE_ZIP_REGEX = r"Hackensack.*NJ.*0760"


def has_street_type(text: str) -> bool:
    text_upper = str(text).upper()
    for st_type in STREET_TYPES:
        if re.search(rf"\b{st_type}\b", text_upper):
            return True
    return False


def has_city_state_zip(text: str) -> bool:
    return bool(re.search(CITY_STATE_ZIP_REGEX, str(text), re.IGNORECASE))


def categorize_address(address):
    """
    Categorize an address into quality buckets.
    Returns: (category, reason)
    """
    if pd.isna(address) or str(address).strip() == "":
        return "blank", "Null or empty address"

    addr = str(address).strip()
    addr_upper = addr.upper()

    # PO Box
    if re.search(r"P\.?O\.?\s*BOX", addr_upper):
        return "po_box", "PO Box address"

    # Generic location terms
    for term in GENERIC_TERMS:
        if addr_upper.startswith(term) or f" {term} " in addr_upper:
            # Park special case with intersection
            if term == "PARK" and "&" in addr:
                parts = addr.split("&")
                if len(parts) == 2 and has_street_type(parts[1]):
                    break
            return "generic_location", f"Generic term: {term}"

    # Intersection
    if "&" in addr:
        parts = addr.split("&")
        if len(parts) == 2:
            part1 = parts[0].strip()
            part2 = parts[1].strip()

            if (
                not part2
                or part2.startswith(",")
                or re.match(
                    r"^,?\s*(Hackensack|NJ|0760)", part2, re.IGNORECASE
                )
            ):
                return "incomplete_intersection", "Missing second street in intersection"

            has_type1 = has_street_type(part1)
            has_type2 = has_street_type(part2)

            if has_type1 and has_type2:
                return "valid_intersection", "Valid intersection format"
            if not has_type1 and not has_type2:
                return "missing_street_type", "Both streets missing type"
            if not has_type1:
                return "missing_street_type", f"First street missing type: {part1}"
            return "missing_street_type", f"Second street missing type: {part2}"

    # Standard address starting with a number
    if re.match(r"^\d+", addr):
        if has_street_type(addr):
            if has_city_state_zip(addr):
                return "valid_standard", "Valid standard address"
            return "incomplete", "Missing city/state/zip"
        return "missing_street_type", "No street type suffix"

    # No number, possible named location
    if has_street_type(addr):
        return "missing_street_number", "Street name without number"

    if re.match(r"^(Hackensack|NJ|0760)", addr, re.IGNORECASE):
        return "incomplete", "City/state only"

    return "missing_street_number", "No street number"


def classify_series(addr_series: pd.Series):
    cats = []
    reasons = []
    for val in addr_series:
        c, r = categorize_address(val)
        cats.append(c)
        reasons.append(r)
    return pd.Series(cats), pd.Series(reasons)


def add_quality_metrics(df: pd.DataFrame, addr_col: str = "FullAddress2", suffix: str = ""):
    """
    Add address quality flags and simple metrics to the dataframe.
    """
    s = df[addr_col].fillna("").astype(str).str.strip()
    u = s.str.upper()

    df[f"Addr_Length{suffix}"] = s.str.len()
    df[f"Word_Count{suffix}"] = s.str.split().str.len()
    df[f"Has_Number{suffix}"] = s.str.match(r"^\d+", na=False)
    df[f"Has_Street_Type{suffix}"] = s.str.contains(STREET_REGEX, na=False)
    df[f"Has_CityStateZip{suffix}"] = s.str.contains(CITY_STATE_ZIP_REGEX, na=False)
    df[f"Has_Intersection{suffix}"] = s.str.contains(r"\s*&\s*", na=False)
    df[f"Is_Uppercase{suffix}"] = s.eq(u)

    contains_generic = pd.Series(False, index=df.index)
    for term in GENERIC_TERMS:
        contains_generic = contains_generic | u.str.contains(rf"\b{re.escape(term)}\b")
    df[f"Contains_Generic{suffix}"] = contains_generic

    df[f"Has_POBox{suffix}"] = u.str.contains(r"P\.?O\.?\s*BOX")
    df[f"Digit_Count{suffix}"] = s.str.count(r"\d")
    df[f"Comma_Count{suffix}"] = s.str.count(",")


def generate_summary_stats(df: pd.DataFrame, valid_cats: set) -> dict:
    """
    Build high level summary statistics for the report.
    """
    total = len(df)
    if total == 0:
        return {}

    stats = {
        "Total_Records": total,
        "Valid_Before_%": df["Address_Category_Before"].isin(valid_cats).mean() * 100,
        "Valid_After_%": df["Address_Category_After"].isin(valid_cats).mean() * 100,
        "Backfilled_Count": (df["FullAddress2"] != df["FullAddress2_Original"]).sum(),
        "Avg_Length_Before": df["Addr_Length_Before"].mean(),
        "Avg_Length_After": df["Addr_Length_After"].mean(),
        "Has_Street_Type_Before_%": df["Has_Street_Type_Before"].mean() * 100,
        "Has_Street_Type_After_%": df["Has_Street_Type_After"].mean() * 100,
        "Has_CityStateZip_Before_%": df["Has_CityStateZip_Before"].mean() * 100,
        "Has_CityStateZip_After_%": df["Has_CityStateZip_After"].mean() * 100,
        "Contains_Generic_Before_%": df["Contains_Generic_Before"].mean() * 100,
        "Contains_Generic_After_%": df["Contains_Generic_After"].mean() * 100,
        "Has_Intersection_After_%": df["Has_Intersection_After"].mean() * 100,
        "Avg_Word_Count_After": df["Word_Count_After"].mean(),
    }
    return stats


def normalize_key(val):
    """
    Normalize case numbers and report numbers to a numeric-only join key.
    Example:
        "24-12345" -> "2412345"
        2412345    -> "2412345"
    """
    return re.sub(r"[^0-9]", "", str(val))


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("ADDRESS BACKFILL FROM RMS")
    print("=" * 60)

    # Load CAD and RMS
    cad_df = pd.read_excel(
        CAD_INPUT,
        engine="openpyxl"
    )
    print(f"Loaded CAD: {len(cad_df):,} records from {CAD_INPUT.name}")

    rms_df = pd.read_excel(
        RMS_INPUT,
        engine="openpyxl",
        dtype={"Case Number": str}
    )
    print(f"Loaded RMS: {len(rms_df):,} records from {RMS_INPUT.name}")

    # Basic column checks
    if "ReportNumberNew" not in cad_df.columns:
        raise RuntimeError("CAD export missing 'ReportNumberNew' column")

    if "Case Number" not in rms_df.columns:
        raise RuntimeError("RMS export missing 'Case Number' column")

    if "FullAddress2" not in cad_df.columns:
        raise RuntimeError("CAD export missing 'FullAddress2' column")

    # Normalize join keys
    cad_df["ReportNumberNew_str"] = cad_df["ReportNumberNew"].astype(str).str.strip()
    rms_df["CaseNumber_str"] = rms_df["Case Number"].astype(str).str.strip()

    cad_df["join_key"] = cad_df["ReportNumberNew_str"].apply(normalize_key)
    rms_df["join_key"] = rms_df["CaseNumber_str"].apply(normalize_key)

    # Choose RMS address column
    rms_addr_col = None
    for col in ["FullAddress2", "FullAddress", "Full Address", "Address"]:
        if col in rms_df.columns:
            rms_addr_col = col
            break

    if rms_addr_col is None:
        raise RuntimeError(
            "No address column found in RMS export "
            "(expected one of FullAddress2 / FullAddress / Full Address / Address)"
        )

    # Simple cleanup on RMS address field
    rms_df[rms_addr_col] = (
        rms_df[rms_addr_col]
        .astype(str)
        .str.replace("\n", " ", regex=False)
        .str.replace("\r", " ", regex=False)
        .str.replace("  ", " ", regex=False)
        .str.strip()
    )

    # Classify original CAD addresses
    cats_before, reasons_before = classify_series(cad_df["FullAddress2"])
    cad_df["Address_Category_Before"] = cats_before
    cad_df["Address_Reason_Before"] = reasons_before

    valid_cats = {"valid_standard", "valid_intersection"}
    invalid_focus = {
        "incomplete_intersection",
        "generic_location",
        "missing_street_type",
        "missing_street_number",
        "incomplete",
        "blank",
        "po_box"
    }

    total_records = len(cad_df)
    valid_before = cad_df["Address_Category_Before"].isin(valid_cats).sum()

    print(f"Valid before: {valid_before:,} of {total_records:,}")

    # Build RMS lookup dict (one address per join_key)
    rms_subset = rms_df[["join_key", rms_addr_col]].dropna(subset=[rms_addr_col])
    # If multiple RMS rows share the same join_key, keep the first non-null address
    rms_subset = rms_subset.drop_duplicates(subset=["join_key"], keep="first")

    rms_lookup = dict(zip(rms_subset["join_key"], rms_subset[rms_addr_col]))
    print(f"RMS lookup addresses: {len(rms_lookup):,} keys")

    # Identify CAD rows to fix
    fix_mask = cad_df["Address_Category_Before"].isin(invalid_focus)
    to_fix = fix_mask.sum()
    print(f"Targets for backfill (bad categories): {to_fix:,}")

    # Pull RMS address into CAD
    cad_df["RMS_Address"] = cad_df["join_key"].map(rms_lookup)

    # Classify RMS addresses only where present
    rms_cats = []
    rms_reasons = []
    for addr in cad_df["RMS_Address"]:
        if pd.isna(addr) or str(addr).strip() == "":
            rms_cats.append("none")
            rms_reasons.append("No RMS address")
        else:
            c, r = categorize_address(addr)
            rms_cats.append(c)
            rms_reasons.append(r)
    cad_df["RMS_Address_Category"] = rms_cats
    cad_df["RMS_Address_Reason"] = rms_reasons

    # Backfill rule:
    # If CAD address is in invalid_focus AND RMS address category is valid_standard or valid_intersection
    # then overwrite FullAddress2 with RMS address
    backfill_mask = (
        fix_mask &
        cad_df["RMS_Address_Category"].isin(valid_cats)
    )

    cad_df["FullAddress2_Original"] = cad_df["FullAddress2"]
    cad_df.loc[backfill_mask, "FullAddress2"] = cad_df.loc[backfill_mask, "RMS_Address"]

    backfilled_count = backfill_mask.sum()
    print(f"Backfilled from RMS: {backfilled_count:,} addresses")

    # Re-classify after backfill
    cats_after, reasons_after = classify_series(cad_df["FullAddress2"])
    cad_df["Address_Category_After"] = cats_after
    cad_df["Address_Reason_After"] = reasons_after

    valid_after = cad_df["Address_Category_After"].isin(valid_cats).sum()
    print(f"Valid after: {valid_after:,} of {total_records:,}")

    improved = valid_after - valid_before

    # Add quality metrics (before and after)
    add_quality_metrics(cad_df, "FullAddress2_Original", "_Before")
    add_quality_metrics(cad_df, "FullAddress2", "_After")

    summary_stats = generate_summary_stats(cad_df, valid_cats)

    # Build backfill log
    changed_mask = cad_df["FullAddress2"] != cad_df["FullAddress2_Original"]
    backfill_log_df = cad_df.loc[changed_mask, [
        "ReportNumberNew",
        "FullAddress2_Original",
        "RMS_Address",
        "FullAddress2",
        "Address_Category_Before",
        "Address_Category_After",
        "RMS_Address_Category"
    ]].copy()

    backfill_log_df.to_csv(BACKFILL_LOG, index=False)
    print(f"Backfill log written: {BACKFILL_LOG}")

    # Category breakdowns before and after
    def breakdown(series: pd.Series) -> dict:
        counts = Counter(series)
        result = {}
        for cat, cnt in counts.items():
            pct = (cnt / total_records) * 100 if total_records else 0.0
            result[cat] = (cnt, pct)
        return result

    breakdown_before = breakdown(cad_df["Address_Category_Before"])
    breakdown_after = breakdown(cad_df["Address_Category_After"])

    # Top 15 remaining problem patterns after backfill
    remaining_invalid_mask = ~cad_df["Address_Category_After"].isin(valid_cats)
    remaining_df = cad_df.loc[remaining_invalid_mask].copy()

    pattern_counts = (
        remaining_df
        .groupby("FullAddress2")["ReportNumberNew"]
        .count()
        .sort_values(ascending=False)
        .head(15)
    )

    # Park-related remaining patterns
    park_mask = remaining_df["FullAddress2"].astype(str).str.contains("PARK", case=False, na=False)
    park_counts = (
        remaining_df.loc[park_mask]
        .groupby("FullAddress2")["ReportNumberNew"]
        .count()
        .sort_values(ascending=False)
        .head(15)
    )

    # Write updated CAD file
    ESRI_DIR.mkdir(parents=True, exist_ok=True)
    cad_df.to_excel(CAD_OUTPUT, index=False)
    print(f"Updated CAD with backfilled addresses: {CAD_OUTPUT}")

    # Build Markdown report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("# Address Backfill From RMS\n\n")
        f.write(f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Source CAD file: {CAD_INPUT.name}\n\n")
        f.write(f"Source RMS file: {RMS_INPUT.name}\n\n")

        f.write("## Executive Summary\n\n")
        f.write("| Metric | Count | Percentage |\n")
        f.write("|--------|-------|------------|\n")
        f.write(f"| Total Records | {total_records:,} | 100.00% |\n")
        f.write(f"| Valid Before | {valid_before:,} | {valid_before / total_records * 100:0.2f}% |\n")
        f.write(f"| Valid After | {valid_after:,} | {valid_after / total_records * 100:0.2f}% |\n")
        f.write(f"| Addresses Backfilled From RMS | {backfilled_count:,} | - |\n")
        f.write(f"| Net Valid Gain | {improved:,} | - |\n\n")

        f.write("## Category Breakdown (Before)\n\n")
        f.write("| Category | Count | % |\n")
        f.write("|----------|-------|----|\n")
        for cat, (cnt, pct) in sorted(breakdown_before.items(), key=lambda x: -x[1][0]):
            f.write(f"| {cat} | {cnt:,} | {pct:0.2f} |\n")
        f.write("\n")

        f.write("## Category Breakdown (After)\n\n")
        f.write("| Category | Count | % |\n")
        f.write("|----------|-------|----|\n")
        for cat, (cnt, pct) in sorted(breakdown_after.items(), key=lambda x: -x[1][0]):
            f.write(f"| {cat} | {cnt:,} | {pct:0.2f} |\n")
        f.write("\n")

        f.write("## Top 15 Remaining Problem Address Patterns\n\n")
        f.write("| Address Pattern | Remaining Calls |\n")
        f.write("|-----------------|-----------------|\n")
        for addr, cnt in pattern_counts.items():
            addr_str = str(addr).replace("|", "/")
            f.write(f"| {addr_str} | {cnt:,} |\n")
        f.write("\n")

        f.write("## Top 15 Remaining Park-Related Patterns\n\n")
        f.write("| Address Pattern | Remaining Calls |\n")
        f.write("|-----------------|-----------------|\n")
        for addr, cnt in park_counts.items():
            addr_str = str(addr).replace("|", "/")
            f.write(f"| {addr_str} | {cnt:,} |\n")
        f.write("\n")

        if summary_stats:
            f.write("## Summary Statistics\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            for k, v in summary_stats.items():
                label = k.replace("_", " ")
                if isinstance(v, float):
                    f.write(f"| {label} | {v:0.2f} |\n")
                else:
                    f.write(f"| {label} | {v} |\n")
            f.write("\n")

        f.write("## Notes For Command Staff\n\n")
        f.write("- RMS backfill targeted incomplete intersections, generic locations, and missing street details.\n")
        f.write("- Only RMS addresses that scored as Valid Standard or Valid Intersection were applied.\n")
        f.write("- Backfill log lists each case where FullAddress2 changed so analysts retain full audit ability.\n")
        f.write("- Remaining patterns highlight park labels and other generic locations that still need a standard street address.\n")

    print(f"Report written: {REPORT_FILE}")


if __name__ == "__main__":
    main()
