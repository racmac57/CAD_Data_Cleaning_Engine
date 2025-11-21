import os
import glob
import re
import json
import argparse
from pathlib import Path
import pandas as pd

# ── 1) LOAD CONFIG ──────────────────────────────────────────────────────────
def load_config(config_path: str = None) -> dict:
    """Load configuration from JSON file.

    Args:
        config_path: Path to config JSON file. If None, uses default location.

    Returns:
        dict: Configuration dictionary with expanded paths.
    """
    if config_path is None:
        # Default to config/config_enhanced.json relative to script location
        script_dir = Path(__file__).resolve().parent
        config_path = script_dir.parent / 'config' / 'config_enhanced.json'

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Expand path templates
    if 'paths' in config:
        paths = config['paths'].copy()
        max_iterations = 10
        for _ in range(max_iterations):
            changed = False
            for key, value in paths.items():
                if isinstance(value, str) and '{' in value:
                    for ref_key, ref_value in paths.items():
                        if '{' + ref_key + '}' in value and '{' not in ref_value:
                            paths[key] = value.replace('{' + ref_key + '}', ref_value)
                            changed = True
            if not changed:
                break
        config['paths'] = paths

    return config

# ── 2) ZONE MERGE FUNCTION ──────────────────────────────────────────────────
def merge_zones(df: pd.DataFrame, zone_master_path: str) -> pd.DataFrame:
    """Merge zone/grid data into CAD DataFrame.

    Args:
        df: CAD DataFrame with FullAddress2 column.
        zone_master_path: Path to zone master Excel file.

    Returns:
        DataFrame with Grid and PDZone columns merged in.
    """
    # Load zone lookup
    zone_df = pd.read_excel(zone_master_path)
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

    # Normalize address for joining
    df["CleanAddress"] = df["FullAddress2"].apply(normalize_address)

    # Merge in zone/grid
    merged = pd.merge(
        df,
        zone_df,
        left_on="CleanAddress",
        right_on="LookupAddress",
        how="left"
    )

    return merged


# ── 4) MAIN FUNCTION ────────────────────────────────────────────────────────
def main():
    """Process CAD files and merge zone/grid data."""
    parser = argparse.ArgumentParser(
        description="Merge zone/grid data into CAD exports using zone master lookup."
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to configuration JSON file. Defaults to config/config_enhanced.json"
    )
    parser.add_argument(
        "--export-root",
        default=None,
        help="Root directory containing CAD exports (overrides config path)."
    )
    parser.add_argument(
        "--zone-master",
        default=None,
        help="Path to zone master Excel file (overrides config path)."
    )
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Determine export root (command-line arg takes precedence)
    export_root = args.export_root
    if export_root is None and 'paths' in config and 'cad_export_root' in config['paths']:
        export_root = config['paths']['cad_export_root']

    if export_root is None:
        # Fallback to default
        onedrive_root = config.get('paths', {}).get('onedrive_root', '')
        if onedrive_root:
            export_root = os.path.join(onedrive_root, '05_EXPORTS', '_CAD')
        else:
            raise ValueError("No export root specified. Use --export-root or set paths.cad_export_root in config.")

    # Determine zone master path (command-line arg takes precedence)
    zone_master = args.zone_master
    if zone_master is None and 'paths' in config and 'zone_master' in config['paths']:
        zone_master = config['paths']['zone_master']

    if zone_master is None:
        raise ValueError("No zone master path specified. Use --zone-master or set paths.zone_master in config.")

    # Find all CAD files
    pattern = os.path.join(export_root, "**", "*.xlsx")
    cad_files = glob.glob(pattern, recursive=True)

    if not cad_files:
        raise FileNotFoundError(f"No .xlsx files found under {export_root!r}")

    print(f"🔍 Found {len(cad_files)} CAD exports to process.")

    # Process each file
    for cad_path in cad_files:
        # Load
        df = pd.read_excel(cad_path)

        # Merge in zone/grid
        merged = merge_zones(df, zone_master)

        # Write out
        out_path = cad_path.replace(".xlsx", "_zoned.xlsx")
        merged.to_excel(out_path, index=False)
        print(f"✅  Wrote {os.path.basename(out_path)} ({len(merged)} rows)")

    print("🎉 All done.")


if __name__ == "__main__":
    main()
