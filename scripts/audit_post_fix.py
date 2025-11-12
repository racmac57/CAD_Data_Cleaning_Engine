import glob
import re
import sys
from pathlib import Path

import pandas as pd

SAMPLE_DIR = Path(
    r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Pipeline\data\01_raw\sample"
)
TEXT_COLS = ["Incident", "CADNotes", "Disposition", "Officer", "How Reported"]
MOJIBAKE_PAT = re.compile(r"(?:â€“|â€”|â€œ|â€\x9d|â€˜|â€™|â€)")


def load_csvs():
    files = sorted(glob.glob(str(SAMPLE_DIR / "*_SAMPLE_1000.csv")))
    if not files:
        print("No sample CSVs found.")
        sys.exit(1)
    for file_path in files:
        yield file_path, pd.read_csv(file_path, dtype=str).fillna("")


def audit_frame(name: str, df: pd.DataFrame):
    issues = []

    # 1) 9-1-1 normalization checks
    if "How Reported" in df.columns:
        bad_excel_date = df["How Reported"].str.contains(
            r"(?:2001-09-01|09/01/2001|9/1/2001)", case=False, na=False, regex=True
        )
        normalized_911 = df["How Reported"].str.fullmatch(
            r"\s*9-1-1\s*", case=False, na=False
        )
        variant_911 = df["How Reported"].str.contains(
            r"^\s*(?:911|9\s*[/\- ]\s*1\s*[/\- ]\s*1)\s*$",
            case=False,
            na=False,
            regex=True,
        )
        not_normalized = variant_911 & ~normalized_911
        if bad_excel_date.any():
            issues.append(("how_reported_excel_date", int(bad_excel_date.sum())))
        if not_normalized.any():
            issues.append(("how_reported_not_9-1-1", int(not_normalized.sum())))

    # 2) Mojibake scan
    for column in [col for col in TEXT_COLS if col in df.columns]:
        hits = df[column].astype(str).str.contains(MOJIBAKE_PAT, regex=True)
        if hits.any():
            issues.append((f"mojibake_{column}", int(hits.sum())))

    # 3) Incident mapping results
    if "Incident_Norm" in df.columns:
        null_norm = df["Incident_Norm"].astype(str).str.strip() == ""
        issues.append(("incident_norm_missing", int(null_norm.sum())))
    else:
        issues.append(("incident_norm_column_missing", -1))

    # 4) Response Type coverage
    if "Response Type" in df.columns:
        blank_rt = df["Response Type"].astype(str).str.strip() == ""
        issues.append(("response_type_blank_after_backfill", int(blank_rt.sum())))
    else:
        issues.append(("response_type_column_missing", -1))

    # 5) Column count for schema conformity
    issues.append(("column_count", df.shape[1]))

    return issues


def main():
    any_failures = False
    for path, frame in load_csvs():
        name = Path(path).name
        print(f"\n== {name} ==")
        for key, value in audit_frame(name, frame):
            print(f"{key}: {value}")
            if key in {
                "how_reported_excel_date",
                "how_reported_not_9-1-1",
                "incident_norm_missing",
                "response_type_blank_after_backfill",
                "incident_norm_column_missing",
                "response_type_column_missing",
                "mojibake_Incident",
                "mojibake_CADNotes",
                "mojibake_Disposition",
                "mojibake_Officer",
                "mojibake_How Reported",
            } and value not in (0, -1):
                any_failures = True

    if any_failures:
        sys.exit(2)


if __name__ == "__main__":
    pd.options.mode.copy_on_write = True
    main()

