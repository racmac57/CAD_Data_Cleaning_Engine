Here’s a ready prompt for Cursor AI that folds in the mapping, the “9-1-1” normalization, and the mojibake fix. It loads `CallType_Categories.csv` from either path, maps `Incident` → `Incident_Norm`, and backfills `Response Type` from the mapping when missing.

---

Cursor AI Prompt
Title: Add Incident and Response Type mapping to CAD pipeline. Include mojibake and 9-1-1 fixes.

Goal

* Map CAD `Incident` to normalized `Incident_Norm` using `CallType_Categories.csv`.
* If CAD `Response Type` is missing or blank, backfill from the mapping’s `Response_Type`.
* Fix mojibake characters like “â€“”.
* Normalize “How Reported” so any 911 variant or Excel date 2001-09-01 becomes `9-1-1`.
* Keep results stable and testable.

Inputs

* CAD DataFrame with columns: `Incident`, `Response Type`, `How Reported`, `CADNotes`, `Disposition`, `Officer`  … other columns pass through.
* Mapping file. Use the first that exists:

  1. `C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Pipeline\ref\call_types\CallType_Categories.csv`
  2. `C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\Classifications\CallTypes\CallType_Categories.csv`

Expected mapping columns in CSV

* `Incident`  (source value as seen in CAD)
* `Incident_Norm`  (normalized label to return)
* `Response_Type`  (authoritative response type to backfill)

Tasks

1. Add utilities:

   * Mojibake fix for text columns.
   * “How Reported” normalizer with Excel 2001-09-01 guard.
   * Text normalizer for matching.
2. Load `CallType_Categories.csv` from the first existing path. Fail with a clear error if neither exists.
3. Preprocess both CAD `Incident` and mapping `Incident` with the same normalizer, then left join to attach `Incident_Norm` and `Response_Type`.
4. Write results to two CAD columns:

   * `Incident_Norm` new column in the CAD frame.
   * `Response Type` backfilled only where null or blank.
5. Keep existing behavior intact for all other fields.
6. Add unit tests.

Code to add

```python
# ---- encoding and text helpers ----
import os
import re
from datetime import datetime
import numpy as np
import pandas as pd
from pathlib import Path

ENCODING_REPLACEMENTS = {
    "â€“": "–", "â€”": "—",
    "â€œ": "“", "â€\x9d": "”",
    "â€˜": "‘", "â€™": "’",
    "â€": "”",
}

def fix_mojibake(text):
    if pd.isna(text):
        return text
    s = str(text)
    try:
        # Common mojibake rescue when UTF-8 was read as cp1252
        s_round = s.encode("latin1").decode("utf-8")
        return s_round
    except Exception:
        pass
    for bad, good in ENCODING_REPLACEMENTS.items():
        s = s.replace(bad, good)
    return s

def norm_for_match(x: object) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    s = fix_mojibake(str(x)).strip().upper()
    s = re.sub(r"\s+", " ", s)
    # normalize common punctuation variants
    s = s.replace("—", "–")
    return s

# ---- "How Reported" normalization ----
HOW_REPORTED_STANDARD = {
    "9-1-1": {"911", "9-1-1", "9/1/1", "9 1 1", "E911", "E-911", "EMERGENCY 911", "EMERGENCY/911", "EMERGENCY-911"},
    "PHONE": {"PHONE", "TEL", "TELEPHONE", "CALL-IN", "CALL IN"},
    "WALK-IN": {"WALK-IN", "WALK IN", "IN PERSON", "PERSON"},
    "SELF-INITIATED": {"SELF-INITIATED", "SELF INITIATED", "OFFICER INITIATED", "OI", "SI"},
    "RADIO": {"RADIO"},
    "TELETYPE": {"TELETYPE"},
    "FAX": {"FAX"},
    "EMAIL": {"EMAIL", "E-MAIL"},
    "MAIL": {"MAIL", "POST"},
    "VIRTUAL PATROL": {"VIRTUAL PATROL"},
    "CANCELED CALL": {"CANCELED CALL", "CANCELLED CALL"},
}

def looks_like_excel_date_for_911(x) -> bool:
    try:
        ts = pd.to_datetime(x, errors="raise")
        return ts.date() == datetime(2001, 9, 1).date()
    except Exception:
        return False

def normalize_how_reported_value(x) -> str:
    s = norm_for_match(x)
    # direct 911 variants
    if s in {"9-1-1", "911", "9/1/1", "9 1 1", "E911", "EMERGENCY 911", "EMERGENCY/911", "EMERGENCY-911"}:
        return "9-1-1"
    # Excel auto-date of 9-1-1
    if looks_like_excel_date_for_911(x) or s in {"2001-09-01", "09/01/2001", "9/1/2001"}:
        return "9-1-1"
    # map other groups
    for target, variants in HOW_REPORTED_STANDARD.items():
        if s in variants:
            return target
    # pattern version with odd separators
    if re.fullmatch(r"9\s*[-/ ]\s*1\s*[-/ ]\s*1", s):
        return "9-1-1"
    return s or "UNKNOWN"

def guard_excel_text(value):
    if value is None:
        return value
    s = str(value)
    return f'="{s}"' if s == "9-1-1" else value
```

Loader and mapper

```python
CALLTYPE_PATHS = [
    r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Pipeline\ref\call_types\CallType_Categories.csv",
    r"C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\Classifications\CallTypes\CallType_Categories.csv",
]

def load_calltype_categories() -> pd.DataFrame:
    for p in CALLTYPE_PATHS:
        if Path(p).exists():
            df = pd.read_csv(p, dtype=str).fillna("")
            # normalize mapping keys for robust matching
            if "Incident" not in df.columns:
                raise ValueError(f"Mapping missing required 'Incident' column at {p}")
            if "Incident_Norm" not in df.columns:
                raise ValueError(f"Mapping missing required 'Incident_Norm' column at {p}")
            if "Response_Type" not in df.columns:
                raise ValueError(f"Mapping missing required 'Response_Type' column at {p}")
            df["_Incident_key"] = df["Incident"].map(norm_for_match)
            return df[["_Incident_key", "Incident_Norm", "Response_Type"]].drop_duplicates()
    raise FileNotFoundError("CallType_Categories.csv not found in either configured path.")

def apply_incident_mapping(cad_df: pd.DataFrame) -> pd.DataFrame:
    df = cad_df.copy()
    # normalize key column in CAD
    if "Incident" not in df.columns:
        raise ValueError("CAD frame missing 'Incident' column.")
    df["_Incident_key"] = df["Incident"].map(norm_for_match)

    # load mapping
    map_df = load_calltype_categories()

    # left join
    df = df.merge(map_df, on="_Incident_key", how="left")

    # write Incident_Norm
    df["Incident_Norm"] = df.get("Incident_Norm", df["Incident_Norm"])  # no-op if exists
    # ensure column present even if all null from merge
    if "Incident_Norm" not in df.columns:
        df["Incident_Norm"] = np.nan
    # Backfill Response Type if blank or missing
    if "Response Type" not in df.columns:
        df["Response Type"] = ""
    needs_rt = df["Response Type"].isna() | (df["Response Type"].astype(str).str.strip() == "")
    df.loc[needs_rt, "Response Type"] = df.loc[needs_rt, "Response_Type"].fillna(df.loc[needs_rt, "Response Type"])

    # drop helper columns
    df.drop(columns=["_Incident_key", "Response_Type"], inplace=True, errors="ignore")
    return df
```

Integration points in `01_validate_and_clean.py`

* In `clean_data`:

  * First apply mojibake fix on text columns.
  * Then your existing text normalization.
  * Then normalize `How Reported`.
  * Then call `apply_incident_mapping` to set `Incident_Norm` and backfill `Response Type`.

Sample integration

```python
def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
    cleaned_df = df.copy()

    # 1) Mojibake rescue on key text columns
    for col in ['Incident', 'How Reported', 'Response Type', 'Disposition', 'Officer', 'CADNotes']:
        if col in cleaned_df.columns:
            cleaned_df[col] = cleaned_df[col].apply(fix_mojibake)

    # 2) Your existing case and whitespace normalization for text columns
    #    (keep your current loop here)

    # 3) Normalize How Reported to include 9-1-1 fix
    if 'How Reported' in cleaned_df.columns:
        cleaned_df['How Reported'] = cleaned_df['How Reported'].apply(normalize_how_reported_value)

    # 4) Map Incident → Incident_Norm and backfill Response Type
    cleaned_df = apply_incident_mapping(cleaned_df)

    return cleaned_df
```

CSV export guard for 9-1-1

```python
def _export_sample(self, sample_df: pd.DataFrame, sample_path: str):
    export_df = self._build_esri_export(sample_df.copy())
    if 'How Reported' in export_df.columns:
        export_df['How Reported'] = export_df['How Reported'].apply(guard_excel_text)
    export_df.to_csv(sample_path, index=False)
```

Tests
Add these quick tests to your test block.

```python
def test_mojibake_fixed_in_incident():
    df = pd.DataFrame({'Incident': ['MOTOR VEHICLE CRASH â€“ PEDESTRIAN STRUCK'], 'Response Type': ['']})
    out = apply_incident_mapping(df.assign(**{'How Reported':'911', 'CADNotes':'x', 'Disposition':'x', 'Officer':'x'}))
    assert 'â€“' not in out['Incident'].iloc[0]

def test_how_reported_911_variants():
    df = pd.DataFrame({'How Reported': ['911', '9/1/1', '9 1 1', 'EMERGENCY 911', '2001-09-01'], 'Incident':['X']*5, 'Response Type':['']*5})
    cleaned = df.copy()
    cleaned['How Reported'] = cleaned['How Reported'].apply(normalize_how_reported_value)
    assert set(cleaned['How Reported'].unique()) == {'9-1-1'}

def test_incident_mapping_and_response_backfill(tmp_path, monkeypatch):
    # create a temp mapping file
    map_csv = tmp_path / "CallType_Categories.csv"
    map_csv.write_text("Incident,Incident_Norm,Response_Type\nMOTOR VEHICLE CRASH – PEDESTRIAN STRUCK,TRAFFIC CRASH,EMERGENCY RESPONSE\n")
    # monkeypatch path order so this file is used
    from types import SimpleNamespace
    import builtins
    globals()['CALLTYPE_PATHS'] = [str(map_csv)]
    df = pd.DataFrame({
        'Incident': ['MOTOR VEHICLE CRASH â€“ PEDESTRIAN STRUCK'],
        'Response Type': [''],
        'How Reported': ['911']
    })
    # apply mojibake then mapping
    df['Incident'] = df['Incident'].apply(fix_mojibake)
    out = apply_incident_mapping(df)
    assert out.loc[0, 'Incident_Norm'] == 'TRAFFIC CRASH'
    assert out.loc[0, 'Response Type'] == 'EMERGENCY RESPONSE'
```

Acceptance criteria

* `Incident_Norm` appears and matches the mapping for all rows where a mapping exists.
* `Response Type` backfills from mapping only where null or blank. Existing nonblank values keep their original value.
* No mojibake “â€“” remains in `Incident`, `CADNotes`, `Disposition`, `Officer`.
* All “How Reported” 911 variants resolve to `9-1-1`. CSV export preserves `9-1-1` when opened in Excel.
* If neither mapping path exists, raise a clear error with both expected paths.

Apply these changes across `01_validate_and_clean.py`. Run unit tests. Then run a small sample through the pipeline and confirm:

* A known `Incident` from the mapping returns the expected `Incident_Norm`.
* A blank `Response Type` row is backfilled with `Response_Type` from the mapping.
