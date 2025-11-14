"""
Utility script to tidy the CallType_Categories mapping before it is re-ingested
by the CAD cleaning pipeline.

The helper normalises whitespace, replaces en/em dashes with ASCII hyphens and
standardises trailing statute tokens (e.g. " - 2C:12-1a").
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = REPO_ROOT / "call_types" / "CallType_Categories.csv"
DEFAULT_OUTPUT = REPO_ROOT / "call_types" / "CallType_Categories_clean.csv"
DEFAULT_CHANGES = REPO_ROOT / "call_types" / "CallType_Categories_changes.csv"

STATUTE_SUFFIX_RE = re.compile(r"\s*-\s*((?:2C|39):[0-9A-Za-z.\-]+)\s*$")


def clean_value(value: object) -> str:
    """Normalise a single call-type string."""
    if pd.isna(value):
        return ""

    s = str(value).strip()
    if not s:
        return s

    # Collapse internal whitespace and normalise dash characters.
    s = re.sub(r"\s+", " ", s)
    s = s.replace("\u2014", "-").replace("\u2013", "-")

    match = STATUTE_SUFFIX_RE.search(s)
    if not match:
        return s

    base_text = s[: match.start()].rstrip(" -")
    statute = match.group(1).replace(" ", "")
    return f"{base_text} - {statute}"


def clean_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """Apply cleaning to relevant text columns."""
    cleaned = df.copy()
    for col in ["Incident", "Incident_Norm", "Response_Type"]:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].map(clean_value)
    return cleaned


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean CallType_Categories mapping text casing/punctuation."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to CallType_Categories CSV/XLSX (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Path for cleaned output (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--changes",
        type=Path,
        default=DEFAULT_CHANGES,
        help=f"Optional change report output (default: {DEFAULT_CHANGES})",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input file not found: {args.input}")

    if args.input.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(args.input)
    else:
        df = pd.read_csv(args.input)

    if "Incident" not in df.columns:
        raise ValueError(
            "Expected 'Incident' column not found in mapping file."
        )

    cleaned = clean_mapping(df)
    changed = cleaned.loc[(cleaned != df).any(axis=1)]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix.lower() in {".xlsx", ".xls"}:
        cleaned.to_excel(args.output, index=False)
    else:
        cleaned.to_csv(args.output, index=False)

    if changed.empty:
        print("No changes were required.")
    else:
        args.changes.parent.mkdir(parents=True, exist_ok=True)
        if args.changes.suffix.lower() in {".xlsx", ".xls"}:
            changed.to_excel(args.changes, index=False)
        else:
            changed.to_csv(args.changes, index=False)
        print(f"Rows changed: {len(changed)}")
        print(f"Change report written to: {args.changes}")

    print(f"Cleaned mapping written to: {args.output}")


if __name__ == "__main__":
    main()

