#!/usr/bin/env python
"""
Address Backfill from RMS + ArcGIS Pro Geocoding Validation
Production-ready | Vectorized | Batch Geocoding | Full Metrics
"""

import pandas as pd
import re
import arcpy
from pathlib import Path
from datetime import datetime
from collections import Counter

# ==================== CONFIG ====================
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ESRI_DIR = DATA_DIR / "ESRI_CADExport"
RMS_DIR = DATA_DIR / "rms"
REPORTS_DIR = DATA_DIR / "02_reports"

CAD_INPUT = ESRI_DIR / "CAD_ESRI_Final_20251117_v2.xlsx"
CAD_OUTPUT = ESRI_DIR / "CAD_ESRI_Final_20251117_v3.xlsx"
RMS_INPUT = RMS_DIR / "2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx"
BACKFILL_LOG = REPORTS_DIR / "address_backfill_from_rms_log.csv"
REPORT_FILE = REPORTS_DIR / "address_backfill_from_rms_report.md"

# Update to your Hackensack composite locator
LOCATOR_PATH = r"C:\GIS\Locators\Hackensack_Composite_Locator.loc"

# Geocoding thresholds
MIN_SCORE = 90
ALLOWED_MATCH_TYPES = {"A", "M"}

# Street types & generic terms
STREET_TYPES = ['STREET','ST','AVENUE','AVE','ROAD','RD','DRIVE','DR','LANE','LN',
                'BOULEVARD','BLVD','COURT','CT','PLACE','PL','CIRCLE','CIR',
                'TERRACE','TER','WAY','PKWY','HIGHWAY','HWY','PLAZA','SQUARE','SQ']
GENERIC_TERMS = ['HOME','VARIOUS','UNKNOWN','PARKING GARAGE','REAR LOT','PARKING LOT',
                 'LOT','GARAGE','REAR','FRONT','SIDE','BEHIND','ACROSS','NEAR','BETWEEN',
                 'AREA','LOCATION','SCENE','UNDETERMINED','N/A','NA','NONE','BLANK','PARK']

STREET_REGEX = re.compile(r"\b(" + "|".join(re.escape(t) for t in STREET_TYPES) + r")\b", re.IGNORECASE)
CITY_STATE_ZIP_REGEX = re.compile(r'hackensack.*nj.*0760', re.IGNORECASE)

# ==================== HELPERS ====================
def normalize_key(val):
    return re.sub(r'\D', '', str(val) or '')

def vectorized_categorize(addresses: pd.Series):
    s = addresses.fillna('').astype(str).str.strip()
    u = s.str.upper()

    category = pd.Series("unknown", index=s.index)
    reason = pd.Series("", index=s.index)

    blank = s == ''
    category[blank] = 'blank'
    reason[blank] = 'Null or empty'

    po_box = u.str.contains(r'P\.?O\.?\s*BOX')
    category[po_box] = 'po_box'
    reason[po_box] = 'PO Box'

    # Generic terms
    generic_mask = pd.Series(False, index=s.index)
    for term in GENERIC_TERMS:
        mask = u.str.contains(rf'\b{re.escape(term)}\b')
        generic_mask |= mask
        category[mask & (category == "unknown")] = 'generic_location'
        reason[mask & (category == "unknown")] = f'Generic: {term}'

    # Intersections
    has_amp = s.str.contains(r'\s*&\s*')
    parts = s.str.split(r'\s*&\s*', n=1, expand=True)
    left = parts[0].str.strip() if has_amp.any() else pd.Series('', index=s.index)
    right = parts.get(1, pd.Series('', index=s.index)).str.strip()

    has_st_left = left.str.contains(STREET_REGEX, na=False)
    has_st_right = right.str.contains(STREET_REGEX, na=False)
    right_valid = right.notna() & (right != '') & (~right.str.match(r'^,?\s*(Hackensack|NJ|0760)', na=False))

    valid_int = has_amp & has_st_left & has_st_right & right_valid
    category[valid_int] = 'valid_intersection'
    reason[valid_int] = 'Valid intersection'

    # Standard addresses
    numeric_start = s.str.match(r'^\d+')
    has_street = s.str.contains(STREET_REGEX)
    has_csz = s.str.contains(CITY_STATE_ZIP_REGEX)

    valid_std = numeric_start & has_street & has_csz
    category[valid_std] = 'valid_standard'
    reason[valid_std] = 'Valid standard address'

    # Fallbacks
    category[(category == "unknown") & numeric_start & has_street] = 'incomplete'
    category[(category == "unknown") & numeric_start] = 'missing_street_type'
    category[(category == "unknown") & has_street] = 'missing_street_number'

    return category, reason

def add_quality_metrics(df: pd.DataFrame, addr_col: str, suffix: str):
    s = df[addr_col].fillna('').astype(str).str.strip()
    u = s.str.upper()

    df[f"Addr_Length{suffix}"] = s.str.len()
    df[f"Word_Count{suffix}"] = s.str.split().str.len()
    df[f"Has_Number{suffix}"] = s.str.match(r'^\d+', na=False)
    df[f"Has_Street_Type{suffix}"] = s.str.contains(STREET_REGEX, na=False)
    df[f"Has_CityStateZip{suffix}"] = s.str.contains(CITY_STATE_ZIP_REGEX, na=False)
    df[f"Has_Intersection{suffix}"] = s.str.contains(r'\s*&\s*', na=False)
    df[f"Is_Uppercase{suffix}"] = s.eq(u)
    df[f"Contains_Generic{suffix}"] = pd.Series(False, index=df.index)
    for term in GENERIC_TERMS:
        df[f"Contains_Generic{suffix}"] |= u.str.contains(rf'\b{re.escape(term)}\b', na=False)
    df[f"Has_POBox{suffix}"] = u.str.contains(r'P\.?O\.?\s*BOX')

def batch_geocode_with_metrics(unique_addrs: pd.Series):
    if unique_addrs.empty or not arcpy.Exists(LOCATOR_PATH):
        return pd.Series([False]*len(unique_addrs), index=unique_addrs.index), {}

    arcpy.env.overwriteOutput = True
    fc = r"in_memory/addr_batch"
    table = r"in_memory/geocode_result"
    for obj in [fc, table]:
        if arcpy.Exists(obj): arcpy.Delete_management(obj)

    sr = arcpy.SpatialReference(4326)
    arcpy.CreateFeatureClass_management("in_memory", "addr_batch", "POINT", spatial_reference=sr)
    arcpy.AddField_management(fc, "InputAddr", "TEXT", field_length=255)

    with arcpy.da.InsertCursor(fc, ["InputAddr", "SHAPE@"]) as cur:
        for a in unique_addrs.dropna().unique():
            cur.insertRow((a, None))

    arcpy.geocoding.GeocodeAddresses(fc, LOCATOR_PATH,
        "'Single Line' Address VISIBLE NONE", table, "STATIC")

    fields = ["InputAddr", "Status", "Score", "Match_type"]
    data = arcpy.da.TableToNumPyArray(table, fields, null_value=None)
    res_df = pd.DataFrame(data)

    res_df["Geocode_OK"] = (res_df["Status"] == "M") & \
                           (res_df["Score"] >= MIN_SCORE) & \
                           (res_df["Match_type"].isin(ALLOWED_MATCH_TYPES))

    metrics = {
        "Geocode_Attempts": len(res_df),
        "Geocode_Matched_%": (res_df["Status"] == "M").mean() * 100,
        "Avg_Score": res_df["Score"].mean(),
        "Score_90plus_%": (res_df["Score"] >= 90).mean() * 100,
        "Score_95plus_%": (res_df["Score"] >= 95).mean() * 100,
        "Score_100_%": (res_df["Score"] == 100).mean() * 100,
        "Exact_Match_%": (res_df["Match_type"] == "A").mean() * 100,
    }

    ok_series = pd.Series(res_df.set_index("InputAddr")["Geocode_OK"])
    result = pd.Series(False, index=unique_addrs.index)
    result[ok_series.index] = ok_series
    result = result.fillna(False)

    return result, metrics

# ==================== MAIN ====================
def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading data...")
    cad_df = pd.read_excel(CAD_INPUT, dtype=str)
    rms_df = pd.read_excel(RMS_INPUT, dtype=str)

    # Normalize join keys
    cad_df['join_key'] = cad_df['ReportNumberNew'].apply(normalize_key)
    rms_df['join_key'] = rms_df['Case Number'].apply(normalize_key)

    rms_addr_col = next((c for c in ["FullAddress2","FullAddress","Full Address","Address"] if c in rms_df.columns), None)
    if not rms_addr_col:
        raise ValueError("No address column found in RMS")

    rms_lookup = rms_df.set_index('join_key')[rms_addr_col].to_dict()

    # Initial categorization
    cad_df['Address_Category_Before'], cad_df['Address_Reason_Before'] = vectorized_categorize(cad_df['FullAddress2'])

    # Pull RMS addresses
    cad_df['RMS_Address'] = cad_df['join_key'].map(rms_lookup)
    cad_df['RMS_Address_Category'], _ = vectorized_categorize(cad_df['RMS_Address'])

    # Candidates for backfill
    need_fix = ~cad_df['Address_Category_Before'].isin({'valid_standard', 'valid_intersection'})
    rms_good = cad_df['RMS_Address_Category'].isin({'valid_standard', 'valid_intersection'})
    candidates = cad_df.loc[need_fix & rms_good, 'RMS_Address']

    print("Batch geocoding RMS candidates...")
    cad_df['RMS_Geocode_OK'], geocode_metrics = batch_geocode_with_metrics(candidates)
    cad_df['RMS_Geocode_OK'] = cad_df['RMS_Geocode_OK'].fillna(False)

    # Final backfill
    backfill_mask = need_fix & rms_good & cad_df['RMS_Geocode_OK']
    cad_df['FullAddress2_Original'] = cad_df['FullAddress2']
    cad_df.loc[backfill_mask, 'FullAddress2'] = cad_df.loc[backfill_mask, 'RMS_Address']

    # Final categorization & metrics
    cad_df['Address_Category_After'], cad_df['Address_Reason_After'] = vectorized_categorize(cad_df['FullAddress2'])
    add_quality_metrics(cad_df, "FullAddress2_Original", "_Before")
    add_quality_metrics(cad_df, "FullAddress2", "_After")

    # Summary stats
    total = len(cad_df)
    valid_before = cad_df['Address_Category_Before'].isin({'valid_standard','valid_intersection'}).sum()
    valid_after = cad_df['Address_Category_After'].isin({'valid_standard','valid_intersection'}).sum()
    backfilled = backfill_mask.sum()

    summary_stats = {
        "Total Records": total,
        "Valid Before": f"{valid_before:,} ({valid_before/total*100:.2f}%)",
        "Valid After": f"{valid_after:,} ({valid_after/total*100:.2f}%)",
        "Backfilled": f"{backfilled:,}",
        "Net Gain": valid_after - valid_before,
        "Avg Length After": f"{cad_df['Addr_Length_After'].mean():.1f}",
        "Has Street Type After %": f"{cad_df['Has_Street_Type_After'].mean()*100:.1f}",
        "Has City/State/Zip After %": f"{cad_df['Has_CityStateZip_After'].mean()*100:.1f}",
        "Generic Remaining %": f"{cad_df['Contains_Generic_After'].mean()*100:.2f}",
        **{k: f"{v:.2f}" for k, v in geocode_metrics.items() if "Score" in k or "Match" in k}
    }

    # Save outputs
    cad_df.to_excel(CAD_OUTPUT, index=False)
    cad_df[backfill_mask].to_csv(BACKFILL_LOG, index=False)

    # Write report
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Address Backfill Report – {datetime.now():%Y-%m-%d %H:%M}\n\n")
        f.write("## Executive Summary\n\n")
        f.write("| Metric                  | Value              |\n")
        f.write("|-------------------------|--------------------|\n")
        for k, v in summary_stats.items():
            f.write(f"| {k:<23} | {v:<18} |\n")
        f.write("\n## Geocoding Accuracy (RMS Candidates)\n\n")
        f.write("| Metric                  | Value   |\n")
        f.write("|-------------------------|---------|\n")
        for k, v in geocode_metrics.items():
            f.write(f"| {k.replace('_', ' '):<23} | {v:.2f} |\n")

    print(f"Done. Backfilled {backfilled:,} addresses. Report → {REPORT_FILE.name}")

if __name__ == "__main__":
    main()