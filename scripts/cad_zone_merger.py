import os
import glob
import re
import pandas as pd

# ── 1) CONFIG ────────────────────────────────────────────────────────────────
# Root folder containing your CAD exports (will recurse into all subfolders)
EXPORT_ROOT = r"C:\Users\carucci_r\OneDrive - City of Hackensack\05_EXPORTS\_CAD"

# Your deduped lookup table
ZONE_MASTER = r"C:\TEMP\zone_grid_master.xlsx"

# ── 2) LOAD ZONE LOOKUP ─────────────────────────────────────────────────────
zone_df = pd.read_excel(ZONE_MASTER)
zone_df = (
    zone_df[["CrossStreetName","Grid","PDZone"]]
    .drop_duplicates()
    .rename(columns={"CrossStreetName":"LookupAddress"})
)

# ── 3) ADDRESS NORMALIZATION ───────────────────────────────────────────────
# Map full street words → abbreviations
SUFFIX_MAP = {
    "Street":"St","Avenue":"Ave","Road":"Rd","Place":"Pl",
    "Drive":"Dr","Court":"Ct","Boulevard":"Blvd"
}

def normalize_address(addr):
    if pd.isna(addr): 
        return addr
    s = addr.replace(" & ", " / ")
    for full, abbr in SUFFIX_MAP.items():
        # word‑boundary replace
        s = re.sub(rf"\b{full}\b", abbr, s, flags=re.IGNORECASE)
    return s.title().strip()

# ── 4) FIND ALL CAD FILES ──────────────────────────────────────────────────
pattern = os.path.join(EXPORT_ROOT, "**", "*.xlsx")
cad_files = glob.glob(pattern, recursive=True)

if not cad_files:
    raise FileNotFoundError(f"No .xlsx files found under {EXPORT_ROOT!r}")

print(f"🔍 Found {len(cad_files)} CAD exports to process.")

# ── 5) PROCESS EACH FILE ───────────────────────────────────────────────────
for cad_path in cad_files:
    # load
    df = pd.read_excel(cad_path)
    
    # normalize address for joining
    df["CleanAddress"] = df["FullAddress2"].apply(normalize_address)
    
    # merge in zone/grid
    merged = pd.merge(
        df,
        zone_df,
        left_on="CleanAddress",
        right_on="LookupAddress",
        how="left"
    )
    
    # write out
    out_path = cad_path.replace(".xlsx", "_zoned.xlsx")
    merged.to_excel(out_path, index=False)
    print(f"✅  Wrote {os.path.basename(out_path)} ({len(merged)} rows)")

print("🎉 All done.")
