"""
Build the Call Type / Incident master mapping and supporting audit reports.

This script merges the cleaned CallType_Categories workbook with historical
incident exports, producing a master CSV plus duplicates / anomaly / unmapped
reports suitable for review and ingestion by the CAD pipeline.
"""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import pandas as pd


STATUTE_SUFFIX_RE = re.compile(r"\s*-\s*((?:2C|39):[0-9A-Za-z.\-]+)\s*$", re.IGNORECASE)
SMALL_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "if",
    "in",
    "nor",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
ACRONYMS = {
    "ABC",
    "AD",
    "ALPR",
    "TAS",
    "JV",
    "A.T.R.A.",
    "A.C.O.R.N.",
    "DV",
    "DWI",
    "MV",
    "MVA",
    "EMS",
    "DPW",
    "DOA",
    "CDS",
    "UCC",
    "CPR",
    "AED",
}


def normalise_unicode(value: str) -> str:
    value = value.replace("\u00a0", " ")
    value = unicodedata.normalize("NFKC", value)
    return "".join(ch for ch in value if unicodedata.category(ch)[0] != "C")


def smart_title_case(text: str) -> str:
    if not text:
        return text

    text = re.sub(r"9-1-1\s*emergency", "9-1-1 Emergency", text, flags=re.IGNORECASE)

    words = text.split()
    result: list[str] = []
    for idx, word in enumerate(words):
        word_upper = word.upper()
        lower_word = word.lower()
        if word_upper in ACRONYMS or (word.isupper() and len(word) > 1 and lower_word not in SMALL_WORDS):
            result.append(word_upper)
            continue

        if idx not in (0, len(words) - 1) and lower_word in SMALL_WORDS:
            result.append(lower_word)
        else:
            result.append(word.capitalize())

    return " ".join(result)


def normalise_call_type(value: str) -> str:
    if value is None:
        return ""

    s = str(value)
    s = normalise_unicode(s)
    s = s.strip()
    if not s:
        return ""

    s = re.sub(r"\s+", " ", s)
    s = s.replace("\u2014", "-").replace("\u2013", "-")

    match = STATUTE_SUFFIX_RE.search(s)
    if not match:
        return smart_title_case(s)

    base = s[: match.start()].rstrip(" -")
    statute = match.group(1).replace(" ", "").upper()
    base = smart_title_case(base)
    return f"{base} - {statute}"


def extract_statute(normalised: str) -> str:
    match = STATUTE_SUFFIX_RE.search(normalised)
    if match:
        token = match.group(1).upper()
        return token.split(":")[0]
    return ""


def load_historical_values(path: Path) -> Counter:
    df = pd.read_csv(path, sep="\t", encoding="latin1")
    values: list[str] = []
    for column in df.columns:
        series = (
            df[column]
            .dropna()
            .astype(str)
            .map(lambda x: normalise_unicode(x).strip())
            .replace("", pd.NA)
            .dropna()
            .tolist()
        )
        values.extend(series)
    return Counter(values)


def load_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def build_master_mapping(
    clean_path: Path, historical_counts: Counter, output_dir: Path
) -> dict[str, pd.DataFrame]:
    clean_df = load_table(clean_path)
    if not {"Incident", "Incident_Norm"}.issubset(set(clean_df.columns)):
        raise ValueError("Clean mapping must include 'Incident' and 'Incident_Norm' columns.")

    response_col = None
    for candidate in ("Response_Type", "Response Type", "Response"):
        if candidate in clean_df.columns:
            response_col = candidate
            break

    master_rows: list[dict] = []
    mapping_changes: list[dict] = []
    suggested_clean_edits: list[dict] = []
    anomalies: list[dict] = []

    approved_raw_values: set[str] = set()

    for _, row in clean_df.iterrows():
        raw_value = normalise_unicode(str(row["Incident"])).strip()
        approved_raw_values.add(raw_value)
        proposed_norm = normalise_call_type(raw_value)
        existing_norm = normalise_unicode(str(row["Incident_Norm"])).strip()

        if proposed_norm != existing_norm:
            mapping_changes.append(
                {
                    "Raw_Value": raw_value,
                    "Old_Incident_Norm": existing_norm,
                    "New_Incident_Norm": proposed_norm,
                }
            )
            suggested_clean_edits.append(
                {
                    "Raw_Value": raw_value,
                    "Current_Clean": existing_norm,
                    "Suggested_Clean": proposed_norm,
                }
            )

        response_value = ""
        if response_col:
            response_value = str(row[response_col]) if not pd.isna(row[response_col]) else ""

        statute = extract_statute(proposed_norm)
        master_rows.append(
            {
                "Raw_Value": raw_value,
                "Incident_Norm": proposed_norm,
                "Category_Type": row.get("Category_Type", ""),
                "Response_Type": response_value,
                "Statute": statute,
                "Source": "Current CAD",
                "Status": "Approved",
                "Note": "",
            }
        )

        if proposed_norm != normalise_call_type(proposed_norm):
            anomalies.append(
                {
                    "Raw_Value": raw_value,
                    "Incident_Norm": proposed_norm,
                    "Issue": "Normalizer not idempotent – review formatting",
                }
            )

    # Historical values
    new_rows = []
    unmapped_rows = []
    for raw_value, count in historical_counts.items():
        if raw_value in approved_raw_values:
            continue
        proposed_norm = normalise_call_type(raw_value)
        statute = extract_statute(proposed_norm)
        status = "Needs Review" if proposed_norm else "Unmapped"
        note = ""
        if not proposed_norm:
            note = "Normalization produced empty string"
            unmapped_rows.append(
                {
                    "Raw_Value": raw_value,
                    "Suggested_Norm": "",
                    "Count": count,
                }
            )
        else:
            unmapped_rows.append(
                {
                    "Raw_Value": raw_value,
                    "Suggested_Norm": proposed_norm,
                    "Count": count,
                }
            )

        new_rows.append(
            {
                "Raw_Value": raw_value,
                "Incident_Norm": proposed_norm,
                "Category_Type": "",
                "Response_Type": "",
                "Statute": statute,
                "Source": "Historical CAD",
                "Status": status,
                "Note": note,
            }
        )

    master_rows.extend(new_rows)

    master_df = pd.DataFrame(master_rows).drop_duplicates(subset=["Raw_Value"]).reset_index(drop=True)

    # Duplicate review groups
    duplicates_map: defaultdict[str, list[str]] = defaultdict(list)
    for _, row in master_df.iterrows():
        duplicates_map[row["Incident_Norm"]].append(row["Raw_Value"])

    duplicates_rows = [
        {
            "Incident_Norm": norm,
            "Raw_Values": "; ".join(sorted(set(raw_values))),
            "Unique_Raw_Count": len(set(raw_values)),
        }
        for norm, raw_values in duplicates_map.items()
        if norm and len(set(raw_values)) > 1
    ]
    duplicates_df = pd.DataFrame(duplicates_rows)
    if not duplicates_df.empty:
        duplicates_df = duplicates_df.sort_values("Incident_Norm")

    anomalies_df = pd.DataFrame(anomalies)
    if not anomalies_df.empty:
        anomalies_df = anomalies_df.sort_values("Incident_Norm")

    mapping_changes_df = pd.DataFrame(mapping_changes)
    suggested_clean_edits_df = pd.DataFrame(suggested_clean_edits)

    unmapped_df = pd.DataFrame(unmapped_rows)
    if not unmapped_df.empty:
        unmapped_df = unmapped_df.sort_values("Count", ascending=False)

    return {
        "master": master_df,
        "duplicates": duplicates_df,
        "anomalies": anomalies_df,
        "unmapped": unmapped_df,
        "mapping_changes": mapping_changes_df,
        "suggested_clean_edits": suggested_clean_edits_df,
    }


def write_csv(df: pd.DataFrame, path: Path) -> None:
    if df.empty:
        df.to_csv(path, index=False)
        return
    df.to_csv(path, index=False, quoting=csv.QUOTE_ALL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Call Type master mapping and audit files."
    )
    parser.add_argument(
        "--clean",
        type=Path,
        default=Path("ref/CallType_Categories_clean.xlsx"),
        help="Path to cleaned CallType_Categories workbook.",
    )
    parser.add_argument(
        "--historical",
        type=Path,
        default=Path("ref/2019_2025_10_Call_Types_Incidents.csv.txt"),
        help="Path to historical incident export (tab-delimited).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("ref"),
        help="Directory to write output CSV files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir: Path = args.out_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    historical_counts = load_historical_values(args.historical)
    outputs = build_master_mapping(args.clean, historical_counts, output_dir)

    write_csv(outputs["master"], output_dir / "CallType_Master_Mapping.csv")
    write_csv(outputs["duplicates"], output_dir / "duplicates_review.csv")
    write_csv(outputs["anomalies"], output_dir / "anomalies.csv")
    write_csv(outputs["unmapped"], output_dir / "unmapped_incidents.csv")
    write_csv(outputs["mapping_changes"], output_dir / "mapping_changes.csv")
    write_csv(
        outputs["suggested_clean_edits"],
        output_dir / "suggested_clean_edits.csv",
    )

    print("Call Type master mapping and audit files have been written to:")
    for name in [
        "CallType_Master_Mapping.csv",
        "duplicates_review.csv",
        "anomalies.csv",
        "unmapped_incidents.csv",
        "mapping_changes.csv",
        "suggested_clean_edits.csv",
    ]:
        print(f"  - {output_dir / name}")


if __name__ == "__main__":
    main()

