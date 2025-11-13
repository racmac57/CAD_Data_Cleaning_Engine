# Add A and B

**User:** Anonymous (gmfzqprc7z@privaterelay.appleid.com)  
**Created:** 11/12/2025 18:16:24  
**Updated:** 11/12/2025 18:21:01  
**Exported:** 11/12/2025 18:22:46  
**Link:** [https://chatgpt.com/g/g-2DQzU5UZl-code-copilot/c/69151547-8b40-8333-84f8-6dda8a8e25d9](https://chatgpt.com/g/g-2DQzU5UZl-code-copilot/c/69151547-8b40-8333-84f8-6dda8a8e25d9)  

## Prompt:
01\_validate\_and\_clean.py

Python

You are a senior-level expert in: Python, ArcPy, JSON, M code (Power Query), DAX, VBA, and HTML.

I will provide a code snippet (pasted below or attached as a file). Your task is to critically evaluate and improve it by performing the following:
🎯 Your Responsibilities:
Error Detection & Explanation
 - Detect and explain any syntax, logic, or runtime issues.
Corrections with Explanation
 - Propose and apply fixes with clear justifications and updated code.
Enhancements
 - Recommend improvements to performance, readability, and maintainability.
Refactoring & Best Practices
 - Refactor using language-specific best practices and modern standards.
Performance Optimization
 - Suggest changes that can significantly speed up processing, especially for large-scale or repetitive operations.
Blind Spot & Risk Analysis
 - Identify any potential issues, edge cases, or oversights the original code may not have accounted for. This includes scalability, error handling, data integrity, and environment-specific assumptions.
Validation
 - If the code is solid, confirm that, and suggest final polish-level refinements.
🧾 Please format your response using the following sections:
✅ Summary of Findings
 > A concise high-level evaluation of code quality, health, and risks.
🛠️ Corrections (with Explanations)
 > Specific bugs or flaws, with explanations and corrected versions.
🚀 Enhancements & Optimizations
 > Suggestions for improving efficiency, clarity, and maintainability. Include performance tuning advice when relevant.
⚠️ Blind Spots & Potential Issues
 > Highlight missing considerations, edge cases, scalability concerns, or technical debt risks.
📘 Best Practices
 > Notes on adherence to or violations of best practices, with suggestions for improvement.
📎 Code Source:
Pasted snippet below
OR attached file

>
> Analyze the code found in:
- > Pasted snippet

Thought for 26s

## Response:
Svg Vector Icons : http://www.onlinewebfonts.com/icon

✅ Summary of Findings

> Strong foundation, but a few correctness bugs, test mismatches, and unnecessary complexity. Biggest issues: duplicate incident mapping work, stratified sampling bug, address validator edge cases, and unit tests that don’t match uppercase normalization. Several unused imports and Windows-specific paths reduce portability.

🛠️ Corrections (with Explanations)  
**1) Stratified sampling error**

*   Bug: `train_test_split(..., stratify=df_with_strata[['incident_stratum']])` passes a DataFrame, which raises `ValueError`. Needs a 1D array/Series.
*   Fix: use `df_with_strata['incident_stratum']`.

**2) Double application of incident mapping**

*   Bug: `clean_data` merges to mapping, then returns `_apply_incident_mapping(cleaned_df)`, applying mapping twice. Wasteful and risks column churn.
*   Fix: remove the in-function merge. Rely on `_apply_incident_mapping` only.

**3) Safe assignment during mapping**

*   Bug: `df.loc[~mapped_incident.isna(), 'Incident'] = mapped_incident.dropna()` risks index misalignment.
*   Fix: index-aligned assignment without `dropna()`.

**4) Address validator false/weak checks**

*   Bug: Intersection check sets `is_intersection = ' & ' in text` then later checks `is_intersection and '&' not in text`, which cannot fail. Also misses cases where `&` has inconsistent spacing.
*   Fix: normalize whitespace around `&` first. Treat any `&` as intersection.

**5) Unit tests mismatch with normalization**

*   Bug: `clean_data` uppercases, but tests expect mixed case values like `Noise Complaint` and `Routine`. They fail.
*   Fix: update expected strings to uppercase, or relax tests using `.str.upper()`.

**6) Response Type backfill naming**

*   Issue: `clean_data` references `'Response Type_mapping'` which never exists with the chosen merge path. This path becomes dead code. Simplify to one backfill path.

**7) Minor**

*   Compile heavy regex once.
*   Use precise pass/fail accounting for case format rule including NaNs.
*   Normalize How Reported once. Avoid repeated work in `_export_sample`.

**Plan (pseudocode)**

*   Drop unused imports.
*   Fix `_stratified_sampling` stratify parameter.
*   In `clean_data`, remove inline mapping. Call `_apply_incident_mapping` once.
*   In `_apply_incident_mapping`, fix assignment and keep `Incident_Norm` consistent.
*   Improve address intersection handling.
*   Tighten rules, precompile regex.
*   Update tests to match uppercase normalization and mapping flow.
*   Make Windows paths configurable.
*   Keep CLI behavior unchanged.

```python
# file: 01_validate_and_clean.py
import argparse
import json
import logging
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
from pydantic import BaseModel
from sklearn.model_selection import train_test_split

# --- Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Precompiled regex ---
CASE_NUM_RE = re.compile(r"^\d{2,4}-\d{6}[A-Z]?$")
MULTISPACE_RE = re.compile(r"\s+")
STREET_SUFFIX_RE = re.compile(
    r"( STREET| AVENUE| ROAD| PLACE| DRIVE| COURT| BOULEVARD| LANE| WAY| HWY| HIGHWAY| ROUTE| AVE| ST| RD| BLVD| DR| CT| PL)"
)

# --- Mojibake helpers ---
ENCODING_REPLACEMENTS = {
    "â€“": "–",
    "â€”": "—",
    "â€œ": "“",
    "â€": "”",
    "â€˜": "‘",
    "â€™": "’",
    "â€¢": "•",
    "â€¦": "…",
    "â€": "”",
}

def fix_mojibake(text):
    if pd.isna(text):
        return text
    s = str(text)
    try:
        s = s.encode("latin1").decode("utf-8")
    except Exception:
        pass
    for bad, good in ENCODING_REPLACEMENTS.items():
        s = s.replace(bad, good)
    return s

# --- How Reported normalizers and Excel guard ---
HOW_REPORTED_STANDARD = {
    "9-1-1": {"911", "9-1-1", "9/1/1", "9 1 1", "E911", "E-911", "EMERGENCY 911", "EMERGENCY-911", "EMERGENCY/911"},
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

def _norm_txt(x: object) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    s = fix_mojibake(str(x)).strip().upper()
    s = MULTISPACE_RE.sub(" ", s)
    return s

def looks_like_date_2001_09_01(x: object) -> bool:
    try:
        ts = pd.to_datetime(x, errors="raise")
        return ts.date() == datetime(2001, 9, 1).date()
    except Exception:
        return False

def normalize_how_reported_value(x: object) -> str:
    s = _norm_txt(x)
    if s in {"9-1-1", "911", "9/1/1", "9 1 1", "E911", "EMERGENCY 911", "EMERGENCY/911", "EMERGENCY-911"}:
        return "9-1-1"
    if looks_like_date_2001_09_01(x) or s in {"2001-09-01", "09/01/2001", "9/1/2001"}:
        return "9-1-1"
    for target, variants in HOW_REPORTED_STANDARD.items():
        if s in variants:
            return target
    if re.fullmatch(r"9\s*[-/ ]\s*1\s*[-/ ]\s*1", s):
        return "9-1-1"
    return s or "UNKNOWN"

def guard_excel_text(value: object) -> object:
    if value is None:
        return value
    return str(value)

def normalize_incident_key(value: object) -> str:
    return _norm_txt(value)

class ConfigSchema(BaseModel):
    address_abbreviations: Dict[str, str]
    validation_lists: Dict[str, list[str]]

class CADDataValidator:
    def __init__(self, config_path: str = "config_enhanced.json"):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.incident_mapping = self._load_incident_mapping()
        self.validation_rules = self._initialize_validation_rules()
        self.sampling_config = {
            "stratified_sample_size": 1000,
            "systematic_interval": 100,
            "quality_thresholds": {"critical": 0.95, "important": 0.85, "optional": 0.70},
        }
        self.validation_results = {
            "total_records": 0,
            "rules_passed": {},
            "rules_failed": {},
            "sample_analysis": {},
            "data_quality_score": 0.0,
            "recommended_actions": [],
            "source_dataset": None,
        }
        self.current_dataset_label = None
        self.original_columns: list[str] = []
        self.unmapped_incidents: set[str] = set()
        self.address_issue_summary: Counter = Counter()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        logger.info(f"Loading configuration from {config_path}...")

        default_config = {
            "address_abbreviations": {" ST ": " STREET ", " AVE ": " AVENUE ", " BLVD ": " BOULEVARD "},
            "validation_lists": {
                "valid_dispositions": [
                    "COMPLETE",
                    "ADVISED",
                    "ARREST",
                    "UNFOUNDED",
                    "CANCELLED",
                    "GOA",
                    "UTL",
                    "SEE REPORT",
                    "REFERRED",
                ],
                "valid_zones": ["5", "6", "7", "8", "9"],
                "emergency_incidents": ["ROBBERY", "ASSAULT", "BURGLARY", "SHOOTING", "STABBING"],
                "non_emergency_incidents": ["NOISE COMPLAINT", "PARKING VIOLATION", "CIVIL DISPUTE"],
                "how_reported": [
                    "9-1-1",
                    "WALK-IN",
                    "PHONE",
                    "SELF-INITIATED",
                    "RADIO",
                    "TELETYPE",
                    "FAX",
                    "OTHER - SEE NOTES",
                    "EMAIL",
                    "MAIL",
                    "VIRTUAL PATROL",
                    "CANCELED CALL",
                ],
            },
        }

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file {config_path} not found. Using defaults.")
            return default_config
        except json.JSONDecodeError as e:
            logger.error(f"Config JSON invalid: {e}. Using defaults.")
            return default_config

        # Validate shape if pydantic available
        try:
            ConfigSchema(**cfg)
        except Exception as e:
            logger.error(f"Invalid config schema: {e}. Using defaults.")
            return default_config

        # Merge defaults
        for k, v in default_config.items():
            cfg.setdefault(k, v)
        if isinstance(cfg.get("validation_lists"), dict):
            for k, v in default_config["validation_lists"].items():
                cfg["validation_lists"].setdefault(k, v)
        else:
            cfg["validation_lists"] = default_config["validation_lists"]
        return cfg

    def reload_config(self, config_path: str | None = None) -> Dict[str, Any]:
        path = config_path or self.config_path
        logger.info(f"Reloading configuration from {path}...")
        self.config = self._load_config(path)
        self.config_path = path
        self.validation_rules = self._initialize_validation_rules()
        return self.config

    def _load_incident_mapping(self) -> pd.DataFrame:
        possible_paths = [
            r"C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\Classifications\CallTypes\CallType_Categories.csv",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "CallType_Categories.csv"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "CallType_Categories.csv"),
        ]

        for mapping_path in possible_paths:
            try:
                df = pd.read_csv(mapping_path)
                logger.info(f"Successfully loaded incident mapping from: {mapping_path}")
                df = df[["Incident", "Incident_Norm", "Response_Type"]].drop_duplicates()
                df["Incident"] = df["Incident"].apply(fix_mojibake)
                df["Incident_Norm"] = df["Incident_Norm"].apply(fix_mojibake)
                df["Response_Type"] = df["Response_Type"].apply(fix_mojibake)
                df["Incident_key"] = df["Incident"].apply(normalize_incident_key)
                return df
            except FileNotFoundError:
                continue

        logger.warning("Incident mapping file not found in any expected location. Using empty mapping.")
        return pd.DataFrame(columns=["Incident", "Incident_Norm", "Response_Type", "Incident_key"])

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            logger.warning("Empty DataFrame provided. Returning empty DataFrame.")
            return df
        logger.info("Starting data cleaning process...")

        cleaned_df = df.copy()
        total_modified = 0

        def _normalize_text(value, uppercase: bool = True):
            if pd.isna(value):
                return value
            text = fix_mojibake(str(value)).strip()
            text = MULTISPACE_RE.sub(" ", text)
            return text.upper() if uppercase else text

        # Clean text fields
        for col in ["Incident", "How Reported", "Response Type", "Disposition", "Officer", "CADNotes"]:
            if col in cleaned_df.columns:
                original = cleaned_df[col].copy()
                cleaned_df[col] = cleaned_df[col].apply(_normalize_text)
                total_modified += (cleaned_df[col] != original).sum()

        if "How Reported" in cleaned_df.columns:
            original = cleaned_df["How Reported"].copy()
            cleaned_df["How Reported"] = cleaned_df["How Reported"].apply(normalize_how_reported_value)
            total_modified += (cleaned_df["How Reported"] != original).sum()

        # Clean addresses
        if "FullAddress2" in cleaned_df.columns:
            original = cleaned_df["FullAddress2"].copy()
            abbreviations = self.config.get("address_abbreviations", {})
            for abbr, full in abbreviations.items():
                cleaned_df["FullAddress2"] = (
                    cleaned_df["FullAddress2"].astype(str).str.replace(abbr, full, case=False, regex=True)
                )
            cleaned_df["FullAddress2"] = cleaned_df["FullAddress2"].apply(_normalize_text)
            total_modified += (cleaned_df["FullAddress2"] != original).sum()

        logger.info(f"Cleaned {total_modified:,} rows in total.")
        # Apply mapping once, here
        return self._apply_incident_mapping(cleaned_df)

    def _apply_incident_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "Incident" not in df.columns:
            if "Incident_Norm" not in df.columns:
                df["Incident_Norm"] = df.get("Incident", pd.Series([], dtype=object))
            return df

        df = df.copy()
        df["Incident_key"] = df["Incident"].apply(normalize_incident_key)

        if self.incident_mapping.empty:
            df["Incident_Norm"] = df["Incident"]
            df.drop(columns=["Incident_key"], inplace=True, errors="ignore")
            return df

        mapping = self.incident_mapping[["Incident_key", "Incident_Norm", "Response_Type"]].rename(
            columns={"Incident_Norm": "__Incident_Norm_map", "Response_Type": "__Response_Type_map"}
        )

        df = df.merge(mapping, on="Incident_key", how="left")

        mapped_incident = df["__Incident_Norm_map"]
        original_incident = df["Incident"]

        unmapped_mask = mapped_incident.isna() & original_incident.notna()
        if unmapped_mask.any():
            self.unmapped_incidents.update(original_incident.loc[unmapped_mask].dropna().unique().tolist())

        # Safe aligned assignment
        mask = mapped_incident.notna()
        df.loc[mask, "Incident"] = mapped_incident[mask]
        df["Incident_Norm"] = df["Incident"]

        if "Response Type" not in df.columns:
            df["Response Type"] = pd.NA
        if "__Response_Type_map" in df.columns:
            fill_mask = df["Response Type"].isna() | (df["Response Type"].astype(str).str.strip() == "")
            df.loc[fill_mask, "Response Type"] = df.loc[fill_mask, "__Response_Type_map"]

        df.drop(columns=["Incident_key", "__Incident_Norm_map", "__Response_Type_map"], inplace=True, errors="ignore")
        return df

    def validate_cad_dataset(self, df: pd.DataFrame, sampling_method: str = "stratified") -> dict:
        self.original_columns = list(df.columns)
        self.unmapped_incidents = set()
        self.address_issue_summary = Counter()
        cleaned_df = self.clean_data(df)
        logger.info(f"Starting CAD dataset validation with {sampling_method} sampling...")
        self.validation_results["total_records"] = len(cleaned_df)
        if self.current_dataset_label:
            self.validation_results["source_dataset"] = self.current_dataset_label

        sample_df = self._create_sample(cleaned_df, sampling_method)

        if hasattr(sample_df, "attrs"):
            self.validation_results["stratum_distribution"] = sample_df.attrs.get("stratum_distribution", {})
            self.validation_results["stratification_method"] = sample_df.attrs.get(
                "stratification_method", sampling_method
            )

        self._export_sample(sample_df)

        sample_results = self._validate_sample(sample_df)
        full_results = self._extrapolate_results(sample_results, cleaned_df)
        recommendations = self._generate_validation_recommendations(full_results)

        self.validation_results.update(full_results)
        self.validation_results["unmapped_incidents"] = sorted(self.unmapped_incidents)
        self.validation_results["address_issue_summary"] = dict(self.address_issue_summary)
        self.validation_results["recommended_actions"] = recommendations
        return self.validation_results

    def _create_sample(self, df: pd.DataFrame, method: str) -> pd.DataFrame:
        if method == "stratified":
            return self._stratified_sampling(df)
        elif method == "systematic":
            return self._systematic_sampling(df)
        elif method == "random":
            return self._random_sampling(df)
        else:
            raise ValueError(f"Unknown sampling method: {method}")

    def _stratified_sampling(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Creating stratified sample...")
        df_with_strata = df.copy()

        if "Incident" in df.columns:
            incident_counts = df["Incident"].value_counts()
            top_incidents = incident_counts[incident_counts > 50].index
            df_with_strata["incident_stratum"] = df_with_strata["Incident"].apply(
                lambda x: x if x in top_incidents else "Other"
            )
            unique_strata = df_with_strata["incident_stratum"].nunique()
            logger.info("Using %d incident strata (min size > 50).", unique_strata)
        else:
            logger.warning("Incident column missing. Assigning all records to 'Unknown' stratum.")
            df_with_strata["incident_stratum"] = "Unknown"

        sample_size = min(self.sampling_config["stratified_sample_size"], len(df))
        try:
            sample_df, _ = train_test_split(
                df_with_strata,
                test_size=1 - (sample_size / len(df)),
                stratify=df_with_strata["incident_stratum"],  # fix: pass Series, not DataFrame
                random_state=42,
            )
            logger.info("Created stratified sample (incident_stratum): %s records", f"{len(sample_df):,}")

            stratum_dist = df_with_strata["incident_stratum"].value_counts().to_dict()
            logger.info("Stratum distribution: %s", stratum_dist)
            sample_df.attrs["stratum_distribution"] = stratum_dist
            sample_df.attrs["stratification_method"] = "incident_stratum"
        except Exception as e:
            logger.warning(f"Stratified sampling failed: {e}. Falling back to random.")
            sample_df = df.sample(n=sample_size, random_state=42)
            sample_df.attrs["stratification_method"] = "random"
            sample_df.attrs["stratum_distribution"] = {"random_sample": len(sample_df)}

        logger.info("Final sample size: %s records", f"{len(sample_df):,}")
        return sample_df

    def _build_esri_export(self, df: pd.DataFrame) -> pd.DataFrame:
        esri_columns = [
            "ReportNumberNew",
            "Incident",
            "How Reported",
            "FullAddress2",
            "PDZone",
            "Grid",
            "Time of Call",
            "cYear",
            "cMonth",
            "Hour_Calc",
            "DayofWeek",
            "Time Dispatched",
            "Time Out",
            "Time In",
            "Time Spent",
            "Time Response",
            "Officer",
            "Disposition",
            "latitude",
            "longitude",
            "Response Type",
        ]
        esri_df = pd.DataFrame(index=df.index)

        def get_series(column, default=None):
            if column in df.columns:
                return df[column]
            if default is not None:
                return pd.Series(default, index=df.index)
            return pd.Series([pd.NA] * len(df), index=df.index)

        esri_df["ReportNumberNew"] = get_series("ReportNumberNew")
        esri_df["Incident"] = get_series("Incident")
        esri_df["How Reported"] = get_series("How Reported")
        esri_df["FullAddress2"] = get_series("FullAddress2")
        esri_df["PDZone"] = pd.to_numeric(get_series("PDZone"), errors="coerce")
        esri_df["Grid"] = get_series("Grid")

        time_of_call = pd.to_datetime(get_series("Time of Call"), errors="coerce")
        esri_df["Time of Call"] = time_of_call
        esri_df["cYear"] = pd.to_numeric(get_series("cYear"), errors="coerce")
        esri_df["cMonth"] = get_series("cMonth")
        esri_df["Hour_Calc"] = time_of_call.dt.hour.astype("float64") if len(time_of_call) > 0 else pd.Series(dtype="float64")
        esri_df["DayofWeek"] = get_series("DayofWeek")
        esri_df["Time Dispatched"] = pd.to_datetime(get_series("Time Dispatched"), errors="coerce")
        esri_df["Time Out"] = pd.to_datetime(get_series("Time Out"), errors="coerce")
        esri_df["Time In"] = pd.to_datetime(get_series("Time In"), errors="coerce")

        time_spent = get_series("Time Spent")
        esri_df["Time Spent"] = time_spent.apply(lambda x: None if pd.isna(x) else str(x))
        time_response = get_series("Time Response")
        esri_df["Time Response"] = time_response.apply(lambda x: None if pd.isna(x) else str(x))

        esri_df["Officer"] = get_series("Officer")
        esri_df["Disposition"] = get_series("Disposition")
        esri_df["latitude"] = np.nan
        esri_df["longitude"] = np.nan
        esri_df["Response Type"] = get_series("Response Type")
        esri_df = esri_df[esri_columns]

        if "How Reported" in esri_df.columns:
            esri_df["How Reported"] = esri_df["How Reported"].apply(normalize_how_reported_value).apply(guard_excel_text)

        return esri_df

    def _export_sample(self, sample_df: pd.DataFrame) -> None:
        if sample_df is None or sample_df.empty:
            logger.warning("Sample DataFrame empty. Skipping sample export.")
            return
        project_root = Path(__file__).resolve().parent.parent
        sample_dir = project_root / "data" / "01_raw" / "sample"
        sample_dir.mkdir(parents=True, exist_ok=True)

        dataset_label = self.current_dataset_label or "cad_dataset"
        sample_size = len(sample_df)
        sample_name = f"{Path(dataset_label).stem}_SAMPLE_{sample_size}.csv"
        sample_path = sample_dir / sample_name

        export_df = self._build_esri_export(sample_df.copy())
        # No second normalization of How Reported needed here
        export_df.to_csv(sample_path, index=False)
        logger.info("Sample exported to %s", sample_path)
        self.validation_results["sample_output_path"] = str(sample_path)

    def _systematic_sampling(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Creating systematic sample...")
        interval = self.sampling_config["systematic_interval"]
        start_idx = np.random.randint(0, interval) if interval > 0 else 0
        sample_indices = list(range(start_idx, len(df), max(interval, 1)))
        sample_df = df.iloc[sample_indices].copy()
        logger.info(f"Created systematic sample: {len(sample_df):,} records (interval: {interval})")
        return sample_df

    def _random_sampling(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Creating random sample...")
        sample_size = min(self.sampling_config["stratified_sample_size"], len(df))
        sample_df = df.sample(n=sample_size, random_state=42)
        logger.info(f"Created random sample: {len(sample_df):,} records")
        return sample_df

    def _categorize_how_reported(self, value):
        if pd.isna(value):
            return "Unknown"
        value_str = str(value).upper()
        if any(term in value_str for term in ["9-1-1", "911", "EMERGENCY"]):
            return "Emergency"
        elif any(term in value_str for term in ["PHONE", "CALL"]):
            return "Phone"
        elif any(term in value_str for term in ["WALK", "PERSON"]):
            return "Walk-in"
        elif any(term in value_str for term in ["SELF", "INITIATED"]):
            return "Self-Initiated"
        else:
            return "Other"

    def _categorize_time_period(self, hour):
        if pd.isna(hour):
            return "Unknown"
        try:
            hour = int(hour)
            if 6 <= hour < 12:
                return "Morning"
            elif 12 <= hour < 18:
                return "Afternoon"
            elif 18 <= hour < 22:
                return "Evening"
            else:
                return "Night"
        except Exception:
            return "Unknown"

    def _validate_sample(self, sample_df: pd.DataFrame) -> dict:
        logger.info("Running validation rules on sample...")
        results = {"critical_rules": {}, "important_rules": {}, "optional_rules": {}, "sample_size": len(sample_df)}

        for category, rules in self.validation_rules.items():
            for rule_id, rule in rules.items():
                result = self._apply_validation_rule(sample_df, rule)
                result.update(
                    {
                        "rule_id": rule_id,
                        "description": rule["description"],
                        "severity": rule["severity"],
                        "fix_suggestion": rule.get("fix_suggestion", ""),
                    }
                )
                results[category][rule_id] = result

        return results

    def _apply_validation_rule(self, df: pd.DataFrame, rule: dict) -> dict:
        rule_id = rule["rule_id"]
        field = rule.get("field")
        fields = rule.get("fields", [field] if field else [])
        result = {
            "rule_id": rule_id,
            "description": rule["description"],
            "severity": rule["severity"],
            "passed": 0,
            "failed": 0,
            "pass_rate": 0.0,
            "failed_records": [],
            "fix_suggestion": rule.get("fix_suggestion", ""),
            "sample_size": len(df),
        }
        missing_fields = [f for f in fields if f not in df.columns]
        if missing_fields:
            result.update({"error": f"Missing fields: {missing_fields}", "failed": len(df)})
            return result

        if rule_id == "CRIT_001":
            result = self._validate_case_number_format(df, result)
        elif rule_id == "CRIT_002":
            result = self._validate_case_number_uniqueness(df, result)
        elif rule_id == "CRIT_003":
            result = self._validate_call_datetime(df, result)
        elif rule_id == "CRIT_004":
            result = self._validate_incident_type_presence(df, result)
        elif rule_id == "IMP_001":
            result = self._validate_address_completeness(df, result)
        elif rule_id == "IMP_002":
            result = self._validate_officer_assignment(df, result)
        elif rule_id == "IMP_003":
            result = self._validate_disposition_consistency(df, result)
        elif rule_id == "IMP_004":
            result = self._validate_time_sequence(df, result)
        elif rule_id == "IMP_005":
            result = self._validate_datetime_duration(df, result)
        elif rule_id == "IMP_006":
            result = self._validate_time_spent(df, result)
        elif rule_id == "OPT_001":
            result = self._validate_how_reported(df, result)
        elif rule_id == "OPT_002":
            result = self._validate_zone_validity(df, result)
        elif rule_id == "OPT_003":
            result = self._validate_response_type_consistency(df, result)

        result["pass_rate"] = result["passed"] / result["sample_size"] if result["sample_size"] > 0 else 0.0
        return result

    def _validate_case_number_format(self, df: pd.DataFrame, result: dict) -> dict:
        field = "ReportNumberNew"
        series = df[field].astype(str)
        valid = series.str.match(CASE_NUM_RE, na=False)
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        result["failed_records"] = df.loc[~valid, field].value_counts().head(10).to_dict()
        return result

    def _validate_case_number_uniqueness(self, df: pd.DataFrame, result: dict) -> dict:
        field = "ReportNumberNew"
        unique_count = df[field].nunique(dropna=True)
        result.update({"passed": unique_count, "failed": len(df) - unique_count})
        duplicates = df[field].value_counts()
        result["failed_records"] = duplicates[duplicates > 1].head(10).to_dict()
        return result

    def _validate_call_datetime(self, df: pd.DataFrame, result: dict) -> dict:
        field = "Time of Call"
        parsed = pd.to_datetime(df[field], errors="coerce")
        valid = parsed.notna() & (parsed >= "2020-01-01") & (parsed <= "2030-12-31")
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        result["failed_records"] = df.loc[~valid, field].value_counts().head(10).to_dict()
        return result

    def _validate_incident_type_presence(self, df: pd.DataFrame, result: dict) -> dict:
        field = "Incident"
        valid = df[field].notna() & (df[field].astype(str).str.strip() != "")
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        result["failed_records"] = df.loc[~valid, field].value_counts().head(10).to_dict()
        return result

    def _validate_address_completeness(self, df: pd.DataFrame, result: dict) -> dict:
        field = "FullAddress2"
        generic = {"UNKNOWN", "NOT PROVIDED", "N/A", "NONE", "", "TBD", "TO BE DETERMINED"}

        def evaluate_address(value):
            if pd.isna(value):
                return False, ["missing_address"]
            text = str(value).upper().strip()
            text = MULTISPACE_RE.sub(" ", text)
            if text in generic:
                return False, ["generic_placeholder"]
            issues = []
            # normalize intersection spacing: ' A & B ' -> 'A & B'
            normalized = MULTISPACE_RE.sub(" ", text.replace(" & ", " & "))
            has_city_zip = normalized.endswith(", HACKENSACK, NJ, 07601")
            if not has_city_zip:
                issues.append("missing_city_state_zip")
            is_intersection = "&" in normalized
            if not is_intersection and not re.match(r"^\d+ ", normalized):
                issues.append("missing_house_number")
            if not STREET_SUFFIX_RE.search(normalized) and not is_intersection:
                issues.append("missing_street_suffix")
            if is_intersection and " & " not in normalized:
                issues.append("intersection_spacing")
            if issues:
                return False, issues
            return True, []

        passes = []
        issue_counter = Counter()
        for addr in df[field]:
            is_valid, issues = evaluate_address(addr)
            passes.append(is_valid)
            if not is_valid:
                issue_counter.update(issues or ["unknown_format"])

        valid_series = pd.Series(passes, index=df.index)
        result.update({"passed": valid_series.sum(), "failed": (~valid_series).sum()})
        result["failed_records"] = dict(issue_counter.most_common(10))
        self.address_issue_summary.update(issue_counter)
        return result

    def _validate_officer_assignment(self, df: pd.DataFrame, result: dict) -> dict:
        dispatched = df["Time Dispatched"].notna() if "Time Dispatched" in df.columns else pd.Series([True] * len(df))
        has_officer = df["Officer"].notna() & (df["Officer"].astype(str).str.strip() != "")
        valid = ~(dispatched & ~has_officer)
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        result["failed_records"] = df.loc[~valid, "Officer"].value_counts().head(10).to_dict()
        return result

    def _validate_disposition_consistency(self, df: pd.DataFrame, result: dict) -> dict:
        field = "Disposition"
        valid_list = set(self.config["validation_lists"]["valid_dispositions"])
        valid = df[field].astype(str).str.strip().isin(valid_list)
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        result["failed_records"] = df.loc[~valid, field].value_counts().head(10).to_dict()
        return result

    def _validate_time_sequence(self, df: pd.DataFrame, result: dict) -> dict:
        fields = ["Time of Call", "Time Dispatched", "Time Out", "Time In"]
        times = {f: pd.to_datetime(df.get(f), errors="coerce") for f in fields}
        valid_sequence = pd.Series([True] * len(df), index=df.index)
        valid_sequence &= (times["Time of Call"] <= times["Time Dispatched"]) | times["Time of Call"].isna() | times[
            "Time Dispatched"
        ].isna()
        valid_sequence &= (times["Time Dispatched"] <= times["Time Out"]) | times["Time Dispatched"].isna() | times[
            "Time Out"
        ].isna()
        valid_sequence &= (times["Time Out"] <= times["Time In"]) | times["Time Out"].isna() | times["Time In"].isna()
        result.update({"passed": valid_sequence.sum(), "failed": (~valid_sequence).sum()})
        if (~valid_sequence).any():
            failed_df = df.loc[~valid_sequence, fields].head(10)
            result["failed_records"] = failed_df[fields].to_dict(orient="records")
        return result

    def _validate_datetime_duration(self, df: pd.DataFrame, result: dict) -> dict:
        fields = ["Time of Call", "Time Dispatched", "Time Out", "Time In"]
        parsed = {f: pd.to_datetime(df[f], errors="coerce") if f in df.columns else pd.Series(pd.NaT, index=df.index) for f in fields}
        valid = pd.Series([True] * len(df), index=df.index)
        if "Time of Call" in df.columns and "Time Dispatched" in df.columns:
            response = parsed["Time Dispatched"] - parsed["Time of Call"]
            valid &= (response >= pd.Timedelta(0)) | response.isna()
        if "Time Dispatched" in df.columns and "Time Out" in df.columns:
            out = parsed["Time Out"] - parsed["Time Dispatched"]
            valid &= (out >= pd.Timedelta(0)) | out.isna()
        if "Time Out" in df.columns and "Time In" in df.columns:
            back = parsed["Time In"] - parsed["Time Out"]
            valid &= (back >= pd.Timedelta(0)) | back.isna()
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        if (~valid).any():
            failed_df = df.loc[~valid, fields].head(10)
            result["failed_records"] = failed_df[fields].to_dict(orient="records")
        return result

    def _validate_time_spent(self, df: pd.DataFrame, result: dict) -> dict:
        field = "Time Spent"
        if field in df.columns:
            durations = pd.to_timedelta(df[field], errors="coerce")
            valid = durations.notna() & (durations >= pd.Timedelta(0)) & (durations <= pd.Timedelta(days=1))
            result.update({"passed": valid.sum(), "failed": (~valid).sum()})
            result["failed_records"] = df.loc[~valid, field].value_counts().head(10).to_dict()
        else:
            result.update({"passed": 0, "failed": len(df), "failed_records": {}})
        return result

    def _validate_how_reported(self, df: pd.DataFrame, result: dict) -> dict:
        field = "How Reported"
        valid_list = set(self.config["validation_lists"]["how_reported"])
        normalized = df[field].apply(normalize_how_reported_value)
        is_valid = normalized.isin(valid_list)
        result.update({"passed": is_valid.sum(), "failed": (~is_valid).sum()})
        if (~is_valid).any():
            result["failed_records"] = normalized[~is_valid].value_counts().head(10).to_dict()
        return result

    def _validate_zone_validity(self, df: pd.DataFrame, result: dict) -> dict:
        field = "PDZone"
        valid_zones = set(self.config["validation_lists"]["valid_zones"])
        valid = df[field].astype(str).str.strip().isin(valid_zones)
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        result["failed_records"] = df.loc[~valid, field].value_counts().head(10).to_dict()
        return result

    def _validate_response_type_consistency(self, df: pd.DataFrame, result: dict) -> dict:
        emergency_incidents = set(self.config["validation_lists"]["emergency_incidents"])
        non_emergency_incidents = set(self.config["validation_lists"]["non_emergency_incidents"])
        incident = df["Incident"].astype(str).str.upper()
        response = df["Response Type"].astype(str).str.upper()
        is_emergency_incident = incident.isin(emergency_incidents)
        is_emergency_response = response.isin(["EMERGENCY", "PRIORITY"])
        is_non_emergency_incident = incident.isin(non_emergency_incidents)
        is_non_emergency_response = response.isin(["NON-EMERGENCY", "ROUTINE"])
        consistent = (is_emergency_incident & is_emergency_response) | (is_non_emergency_incident & is_non_emergency_response) | (~is_emergency_incident & ~is_non_emergency_incident)
        result.update({"passed": consistent.sum(), "failed": (~consistent).sum()})
        if (~consistent).any():
            failed_df = df.loc[~consistent, ["Incident", "Response Type"]].head(10)
            result["failed_records"] = failed_df.to_dict(orient="records")
        return result

    def _extrapolate_results(self, sample_results: dict, full_df: pd.DataFrame) -> dict:
        extrapolated = {"critical_rules": {}, "important_rules": {}, "optional_rules": {}}
        full_size = len(full_df)
        sample_size = sample_results["sample_size"]
        factor = full_size / sample_size if sample_size > 0 else 0

        for category in extrapolated.keys():
            for rule_id, res in sample_results[category].items():
                extrapolated[category][rule_id] = {
                    "rule_id": rule_id,
                    "description": res["description"],
                    "severity": res["severity"],
                    "sample_passed": res["passed"],
                    "sample_failed": res["failed"],
                    "sample_pass_rate": res["pass_rate"],
                    "estimated_full_passed": int(res["passed"] * factor),
                    "estimated_full_failed": int(res["failed"] * factor),
                    "estimated_full_pass_rate": res["pass_rate"],
                    "failed_records": res.get("failed_records", {}),
                    "fix_suggestion": res.get("fix_suggestion", ""),
                }
        extrapolated["overall_quality_score"] = self._calculate_overall_quality_score(extrapolated)
        return extrapolated

    def _calculate_overall_quality_score(self, results: dict) -> float:
        weights = {"critical": 0.5, "important": 0.3, "optional": 0.2}
        score, total_weight = 0.0, 0.0
        for category, weight in weights.items():
            rates = [r["estimated_full_pass_rate"] for r in results[f"{category}_rules"].values()]
            if rates:
                avg_rate = sum(rates) / len(rates)
                score += avg_rate * weight
                total_weight += weight
        return (score / total_weight * 100) if total_weight > 0 else 0.0

    def _generate_validation_recommendations(self, results: dict) -> list:
        recommendations = []
        for category in ["critical", "important", "optional"]:
            threshold = self.sampling_config["quality_thresholds"][category]
            for rule_id, res in results[f"{category}_rules"].items():
                if res["estimated_full_pass_rate"] < threshold:
                    recommendations.append(
                        f"{category.upper()}: {res['description']} - Pass rate: {res['estimated_full_pass_rate']:.1%} (threshold: {threshold:.1%})"
                    )
                    recommendations.append(f"  Fix suggestion: {res['fix_suggestion']}")
        unmapped = self.validation_results.get("unmapped_incidents", [])
        if unmapped:
            sample_examples = ", ".join(list(unmapped)[:5])
            recommendations.append(
                f"INCIDENT MAPPING: {len(unmapped)} incident types not found in CallType_Categories.csv. Examples: {sample_examples}"
            )
        address_issues = self.validation_results.get("address_issue_summary") or {}
        if address_issues:
            top_issue, count = max(address_issues.items(), key=lambda item: item[1])
            recommendations.append(
                f"ADDRESS QUALITY: {count} address records flagged (top issue: {top_issue}). Review CAD vs RMS/Geocode backfill."
            )
        return recommendations

    def create_validation_report(self, output_path: str = None) -> str:
        dataset_label = self.validation_results.get("source_dataset") or getattr(self, "current_dataset_label", None)
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = ""
            if dataset_label:
                label_stem = os.path.splitext(os.path.basename(dataset_label))[0]
                year_match = re.match(r"^(\d{4})", label_stem)
                if year_match:
                    prefix = f"{year_match.group(1)}_"
                else:
                    sanitized = re.sub(r"[^A-Za-z0-9]+", "_", label_stem).strip("_")
                    if sanitized:
                        prefix = f"{sanitized}_"
            output_path = f"{prefix}cad_validation_report_{timestamp}.json"

        report = {
            "validation_metadata": {
                "timestamp": datetime.now().isoformat(),
                "validator_version": "CAD_Validator_2025.10.17",
                "total_records_validated": self.validation_results["total_records"],
                "stratification_method": self.validation_results.get("stratification_method", "unknown"),
                "source_dataset": dataset_label,
                "report_filename": output_path,
            },
            "validation_summary": {
                "overall_quality_score": self.validation_results.get("overall_quality_score", 0),
                "recommendations_count": len(self.validation_results.get("recommended_actions", [])),
            },
            "sampling_metadata": {
                "stratum_distribution": self.validation_results.get("stratum_distribution", {}),
                "stratification_method": self.validation_results.get("stratification_method", "unknown"),
                "sample_size": self.sampling_config.get("stratified_sample_size", 1000),
            },
            "recommended_actions": self.validation_results.get("recommended_actions", []),
            "validation_details": self.validation_results,
            "sampling_configuration": self.sampling_config,
        }

        def clean_for_json(obj):
            if isinstance(obj, dict):
                return {str(k): clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [clean_for_json(item) for item in obj]
            elif hasattr(obj, "isoformat"):
                return obj.isoformat()
            elif isinstance(obj, (pd.Timestamp, pd.Timedelta)):
                return str(obj)
            elif hasattr(obj, "tolist"):
                return obj.tolist()
            elif hasattr(obj, "__dict__"):
                return str(obj)
            else:
                return obj

        cleaned_report = clean_for_json(report)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_report, f, indent=2, ensure_ascii=False)
        logger.info(f"Validation report saved: {output_path}")
        return output_path

def validate_cad_dataset_with_sampling(
    config: Dict[str, Any], sampling_method: str = "stratified", validator: CADDataValidator | None = None
):
    cad_file = config.get("file_path", "")
    if not cad_file:
        raise ValueError("Config must include 'file_path' key.")
    logger.info(f"Loading data from: {cad_file}")
    df = pd.read_excel(cad_file) if cad_file.lower().endswith(".xlsx") else pd.read_csv(cad_file)
    if validator is None:
        validator = CADDataValidator(config_path=config.get("config_path", "config_enhanced.json"))
    else:
        config_path = config.get("config_path")
        if config_path and config_path != validator.config_path:
            validator.reload_config(config_path)
    dataset_label = os.path.basename(cad_file)
    validator.current_dataset_label = dataset_label
    validator.validation_results["source_dataset"] = dataset_label
    results = validator.validate_cad_dataset(df, sampling_method)
    report_path = validator.create_validation_report()
    return results, report_path

def main():
    pd.options.mode.copy_on_write = True
    parser = argparse.ArgumentParser(description="Clean and validate CAD datasets.")
    parser.add_argument(
        "--config",
        default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config_enhanced.json"),
        help="Path to configuration JSON file.",
    )
    parser.add_argument(
        "--raw-dir",
        default=r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Pipeline\data\01_raw",
        help="Directory containing CAD source files.",
    )
    parser.add_argument(
        "--sampling-method",
        choices=["stratified", "systematic", "random"],
        default="stratified",
        help="Sampling method to apply.",
    )
    parser.add_argument("--reload-config", action="store_true", help="Reload configuration before processing.")
    args = parser.parse_args()

    validator = CADDataValidator(config_path=args.config)
    if args.reload_config:
        validator.reload_config(args.config)

    all_cad_files = sorted([p for p in Path(args.raw_dir).glob("*.xlsx")])
    print(f"Found {len(all_cad_files)} files to process.")

    for cad_file_path in all_cad_files:
        print(f"\n{'='*60}\nPROCESSING: {cad_file_path.name}\n{'='*60}")
        validator.current_dataset_label = cad_file_path.name
        validator.validation_results["source_dataset"] = validator.current_dataset_label
        results, report_file = validate_cad_dataset_with_sampling(
            {"file_path": str(cad_file_path), "config_path": args.config}, args.sampling_method, validator=validator
        )
        print(f"  - Overall Quality Score: {results.get('overall_quality_score', 0):.1f}/100")
        print(f"  - Full report saved to: {report_file}")

    print("\nAll files processed successfully!")

if __name__ == "__main__":
    main()
```

🚀 Enhancements & Optimizations

*   Drop unused imports: `dask`, `psutil`, `plotly`, `pytest` from runtime module. Keep tests in a separate `tests/` file. Faster import and fewer dependencies.
*   Precompile regex. Less overhead in tight loops.
*   Single pass incident mapping. Lower compute, fewer columns.
*   Vectorize intersection normalization. Avoid per-row branching when possible.
*   Use categoricals for columns like `Incident`, `Disposition`, `Response Type` when large. Memory savings.
*   Make `systematic_interval` data-driven for tiny datasets to avoid empty samples. Already guarded now.

⚠️ Blind Spots & Potential Issues

*   Hard-coded Windows paths. Add env or CLI flag for mapping file root.
*   Timezone handling absent. CAD often mixes local/timezone. Parse with zone or normalize to UTC.
*   `case_number_uniqueness`: counts unique, not unique per year. If numbering resets annually, group by year.
*   Address check forces Hackensack zip. If ingesting mutual aid or legacy data, allow city/zip whitelist.
*   Large XLSX parsing memory. For very large inputs, stream CSV or chunk with `read_csv(chunksize=...)`.
*   Sampling threshold of `>50` for top incidents is static. Consider percentile cut or cap number of strata.

📘 Best Practices

*   Separate tests into `tests/test_validate_and_clean.py`. Avoid importing `pytest` in production code.
*   Keep config schema stable. Your `ConfigSchema` is good. Enforce enums for known lists for tighter validation.
*   Log at info for milestones and at debug for row counts. Current logging is fine, prune noisy messages in hot paths.
*   Ensure `ensure_ascii=False` in JSON. Keeps smart quotes unescaped. Added.

📎 Code Source:  
Pasted snippet.

**a.** Want me to split your pytest tests into a separate `tests/` module and add a minimal `pyproject.toml`?  
**b.** Do you want grouping logic for case number uniqueness by year prefix to avoid false duplicate flags?

## Prompt:
add A and B

## Response:
Svg Vector Icons : http://www.onlinewebfonts.com/icon

Thought for 6s

TL;DR: Implemented both.  
A. Split tests into `tests/` and added a minimal `pyproject.toml`.  
B. Updated uniqueness rule to check duplicates within the same year, not across years.

Plan
----

*   Add helper to extract year from `ReportNumberNew`.
*   Update `CRIT_002` to flag duplicates per year only.
*   Keep report of top duplicate pairs by year and case.
*   Create `tests/test_validate_and_clean.py` with cases for:
    *   Same case number across different years passes.
    *   Duplicate case number within same year fails.
    *   Mixed 2-digit and 4-digit year prefixes.
*   Add `pyproject.toml` with pytest config and project metadata.

```python
# file: 01_validate_and_clean.py
import argparse
import json
import logging
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel
from sklearn.model_selection import train_test_split

# --- Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Precompiled regex ---
CASE_NUM_RE = re.compile(r"^\d{2,4}-\d{6}[A-Z]?$")
CASE_PREFIX_RE = re.compile(r"^(\d{2,4})-")
MULTISPACE_RE = re.compile(r"\s+")
STREET_SUFFIX_RE = re.compile(
    r"( STREET| AVENUE| ROAD| PLACE| DRIVE| COURT| BOULEVARD| LANE| WAY| HWY| HIGHWAY| ROUTE| AVE| ST| RD| BLVD| DR| CT| PL)"
)

# --- Mojibake helpers ---
ENCODING_REPLACEMENTS = {
    "â€“": "–",
    "â€”": "—",
    "â€œ": "“",
    "â€": "”",
    "â€˜": "‘",
    "â€™": "’",
    "â€¢": "•",
    "â€¦": "…",
    "â€": "”",
}

def fix_mojibake(text):
    if pd.isna(text):
        return text
    s = str(text)
    try:
        s = s.encode("latin1").decode("utf-8")
    except Exception:
        pass
    for bad, good in ENCODING_REPLACEMENTS.items():
        s = s.replace(bad, good)
    return s

# --- How Reported normalizers and Excel guard ---
HOW_REPORTED_STANDARD = {
    "9-1-1": {"911", "9-1-1", "9/1/1", "9 1 1", "E911", "E-911", "EMERGENCY 911", "EMERGENCY-911", "EMERGENCY/911"},
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

def _norm_txt(x: object) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    s = fix_mojibake(str(x)).strip().upper()
    s = MULTISPACE_RE.sub(" ", s)
    return s

def looks_like_date_2001_09_01(x: object) -> bool:
    try:
        ts = pd.to_datetime(x, errors="raise")
        return ts.date() == datetime(2001, 9, 1).date()
    except Exception:
        return False

def normalize_how_reported_value(x: object) -> str:
    s = _norm_txt(x)
    if s in {"9-1-1", "911", "9/1/1", "9 1 1", "E911", "EMERGENCY 911", "EMERGENCY/911", "EMERGENCY-911"}:
        return "9-1-1"
    if looks_like_date_2001_09_01(x) or s in {"2001-09-01", "09/01/2001", "9/1/2001"}:
        return "9-1-1"
    for target, variants in HOW_REPORTED_STANDARD.items():
        if s in variants:
            return target
    if re.fullmatch(r"9\s*[-/ ]\s*1\s*[-/ ]\s*1", s):
        return "9-1-1"
    return s or "UNKNOWN"

def guard_excel_text(value: object) -> object:
    if value is None:
        return value
    return str(value)

def normalize_incident_key(value: object) -> str:
    return _norm_txt(value)

class ConfigSchema(BaseModel):
    address_abbreviations: Dict[str, str]
    validation_lists: Dict[str, list[str]]

class CADDataValidator:
    def __init__(self, config_path: str = "config_enhanced.json"):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.incident_mapping = self._load_incident_mapping()
        self.validation_rules = self._initialize_validation_rules()
        self.sampling_config = {
            "stratified_sample_size": 1000,
            "systematic_interval": 100,
            "quality_thresholds": {"critical": 0.95, "important": 0.85, "optional": 0.70},
        }
        self.validation_results = {
            "total_records": 0,
            "rules_passed": {},
            "rules_failed": {},
            "sample_analysis": {},
            "data_quality_score": 0.0,
            "recommended_actions": [],
            "source_dataset": None,
        }
        self.current_dataset_label = None
        self.original_columns: list[str] = []
        self.unmapped_incidents: set[str] = set()
        self.address_issue_summary: Counter = Counter()

    # --- New: case-number year helpers ---
    @staticmethod
    def _extract_year_from_case(case_num: str) -> Tuple[int | None, str]:
        """
        Returns (year, suffix) where suffix is the '######[A-Z]?' portion.
        Year normalization:
          - 4 digits: yyyy
          - 2 digits: 2000-2049 -> 2000+yy, else 1900+yy
        """
        if not isinstance(case_num, str):
            return None, ""
        m = CASE_PREFIX_RE.match(case_num)
        if not m:
            return None, ""
        year_token = m.group(1)
        try:
            if len(year_token) == 4:
                year = int(year_token)
            else:
                yy = int(year_token)
                year = 2000 + yy if yy <= 49 else 1900 + yy
        except Exception:
            return None, ""
        suffix = case_num[len(year_token) + 1 :]  # skip hyphen
        return year, suffix

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        logger.info(f"Loading configuration from {config_path}...")

        default_config = {
            "address_abbreviations": {" ST ": " STREET ", " AVE ": " AVENUE ", " BLVD ": " BOULEVARD "},
            "validation_lists": {
                "valid_dispositions": [
                    "COMPLETE",
                    "ADVISED",
                    "ARREST",
                    "UNFOUNDED",
                    "CANCELLED",
                    "GOA",
                    "UTL",
                    "SEE REPORT",
                    "REFERRED",
                ],
                "valid_zones": ["5", "6", "7", "8", "9"],
                "emergency_incidents": ["ROBBERY", "ASSAULT", "BURGLARY", "SHOOTING", "STABBING"],
                "non_emergency_incidents": ["NOISE COMPLAINT", "PARKING VIOLATION", "CIVIL DISPUTE"],
                "how_reported": [
                    "9-1-1",
                    "WALK-IN",
                    "PHONE",
                    "SELF-INITIATED",
                    "RADIO",
                    "TELETYPE",
                    "FAX",
                    "OTHER - SEE NOTES",
                    "EMAIL",
                    "MAIL",
                    "VIRTUAL PATROL",
                    "CANCELED CALL",
                ],
            },
        }

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file {config_path} not found. Using defaults.")
            return default_config
        except json.JSONDecodeError as e:
            logger.error(f"Config JSON invalid: {e}. Using defaults.")
            return default_config

        try:
            ConfigSchema(**cfg)
        except Exception as e:
            logger.error(f"Invalid config schema: {e}. Using defaults.")
            return default_config

        for k, v in default_config.items():
            cfg.setdefault(k, v)
        if isinstance(cfg.get("validation_lists"), dict):
            for k, v in default_config["validation_lists"].items():
                cfg["validation_lists"].setdefault(k, v)
        else:
            cfg["validation_lists"] = default_config["validation_lists"]
        return cfg

    def reload_config(self, config_path: str | None = None) -> Dict[str, Any]:
        path = config_path or self.config_path
        logger.info(f"Reloading configuration from {path}...")
        self.config = self._load_config(path)
        self.config_path = path
        self.validation_rules = self._initialize_validation_rules()
        return self.config

    def _load_incident_mapping(self) -> pd.DataFrame:
        possible_paths = [
            r"C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\Classifications\CallTypes\CallType_Categories.csv",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "CallType_Categories.csv"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "CallType_Categories.csv"),
        ]

        for mapping_path in possible_paths:
            try:
                df = pd.read_csv(mapping_path)
                logger.info(f"Successfully loaded incident mapping from: {mapping_path}")
                df = df[["Incident", "Incident_Norm", "Response_Type"]].drop_duplicates()
                df["Incident"] = df["Incident"].apply(fix_mojibake)
                df["Incident_Norm"] = df["Incident_Norm"].apply(fix_mojibake)
                df["Response_Type"] = df["Response_Type"].apply(fix_mojibake)
                df["Incident_key"] = df["Incident"].apply(normalize_incident_key)
                return df
            except FileNotFoundError:
                continue

        logger.warning("Incident mapping file not found in any expected location. Using empty mapping.")
        return pd.DataFrame(columns=["Incident", "Incident_Norm", "Response_Type", "Incident_key"])

    def _initialize_validation_rules(self) -> dict:
        return {
            "critical_rules": {
                "CRIT_001": {
                    "rule_id": "CRIT_001",
                    "field": "ReportNumberNew",
                    "description": "Case number format follows YY-###### or YYYY-######",
                    "severity": "critical",
                    "fix_suggestion": "Normalize to YYYY-###### if possible.",
                },
                "CRIT_002": {
                    "rule_id": "CRIT_002",
                    "field": "ReportNumberNew",
                    "description": "Case number unique within same year",
                    "severity": "critical",
                    "fix_suggestion": "De-duplicate per year. Investigate RMS export rules.",
                },
                "CRIT_003": {
                    "rule_id": "CRIT_003",
                    "field": "Time of Call",
                    "description": "Valid call datetime within expected range",
                    "severity": "critical",
                    "fix_suggestion": "Fix parser and source formatting.",
                },
                "CRIT_004": {
                    "rule_id": "CRIT_004",
                    "field": "Incident",
                    "description": "Incident type present",
                    "severity": "critical",
                    "fix_suggestion": "Backfill from mapping or notes.",
                },
            },
            "important_rules": {
                "IMP_001": {
                    "rule_id": "IMP_001",
                    "field": "FullAddress2",
                    "description": "Address completeness and format",
                    "severity": "important",
                    "fix_suggestion": "Standardize suffix, city, zip. Backfill where missing.",
                },
                "IMP_002": {
                    "rule_id": "IMP_002",
                    "fields": ["Officer", "Time Dispatched"],
                    "description": "Officer present when dispatched",
                    "severity": "important",
                    "fix_suggestion": "Assign primary officer or mark canceled.",
                },
                "IMP_003": {
                    "rule_id": "IMP_003",
                    "field": "Disposition",
                    "description": "Disposition in allowed list",
                    "severity": "important",
                    "fix_suggestion": "Map to controlled vocabulary.",
                },
                "IMP_004": {
                    "rule_id": "IMP_004",
                    "fields": ["Time of Call", "Time Dispatched", "Time Out", "Time In"],
                    "description": "Chronology is non-decreasing",
                    "severity": "important",
                    "fix_suggestion": "Correct clock drift or manual entry errors.",
                },
                "IMP_005": {
                    "rule_id": "IMP_005",
                    "fields": ["Time of Call", "Time Dispatched", "Time Out", "Time In"],
                    "description": "Durations are non-negative",
                    "severity": "important",
                    "fix_suggestion": "Fix negative intervals. Validate DST transitions.",
                },
                "IMP_006": {
                    "rule_id": "IMP_006",
                    "field": "Time Spent",
                    "description": "Parsable time spent within bounds",
                    "severity": "important",
                    "fix_suggestion": "Normalize hh:mm:ss and clip outliers.",
                },
            },
            "optional_rules": {
                "OPT_001": {
                    "rule_id": "OPT_001",
                    "field": "How Reported",
                    "description": "How Reported in controlled list",
                    "severity": "optional",
                    "fix_suggestion": "Normalize common variants to standard set.",
                },
                "OPT_002": {
                    "rule_id": "OPT_002",
                    "field": "PDZone",
                    "description": "Zone code valid",
                    "severity": "optional",
                    "fix_suggestion": "Map or recalc from grids.",
                },
                "OPT_003": {
                    "rule_id": "OPT_003",
                    "fields": ["Incident", "Response Type"],
                    "description": "Incident vs Response Type consistent",
                    "severity": "optional",
                    "fix_suggestion": "Align response tiering with call types.",
                },
            },
        }

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            logger.warning("Empty DataFrame provided. Returning empty DataFrame.")
            return df
        logger.info("Starting data cleaning process...")

        cleaned_df = df.copy()
        total_modified = 0

        def _normalize_text(value, uppercase: bool = True):
            if pd.isna(value):
                return value
            text = fix_mojibake(str(value)).strip()
            text = MULTISPACE_RE.sub(" ", text)
            return text.upper() if uppercase else text

        for col in ["Incident", "How Reported", "Response Type", "Disposition", "Officer", "CADNotes"]:
            if col in cleaned_df.columns:
                original = cleaned_df[col].copy()
                cleaned_df[col] = cleaned_df[col].apply(_normalize_text)
                total_modified += (cleaned_df[col] != original).sum()

        if "How Reported" in cleaned_df.columns:
            original = cleaned_df["How Reported"].copy()
            cleaned_df["How Reported"] = cleaned_df["How Reported"].apply(normalize_how_reported_value)
            total_modified += (cleaned_df["How Reported"] != original).sum()

        if "FullAddress2" in cleaned_df.columns:
            original = cleaned_df["FullAddress2"].copy()
            abbreviations = self.config.get("address_abbreviations", {})
            for abbr, full in abbreviations.items():
                cleaned_df["FullAddress2"] = (
                    cleaned_df["FullAddress2"].astype(str).str.replace(abbr, full, case=False, regex=True)
                )
            cleaned_df["FullAddress2"] = cleaned_df["FullAddress2"].apply(_normalize_text)
            total_modified += (cleaned_df["FullAddress2"] != original).sum()

        logger.info(f"Cleaned {total_modified:,} rows in total.")
        return self._apply_incident_mapping(cleaned_df)

    def _apply_incident_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "Incident" not in df.columns:
            if "Incident_Norm" not in df.columns:
                df["Incident_Norm"] = df.get("Incident", pd.Series([], dtype=object))
            return df

        df = df.copy()
        df["Incident_key"] = df["Incident"].apply(normalize_incident_key)

        if self.incident_mapping.empty:
            df["Incident_Norm"] = df["Incident"]
            df.drop(columns=["Incident_key"], inplace=True, errors="ignore")
            return df

        mapping = self.incident_mapping[["Incident_key", "Incident_Norm", "Response_Type"]].rename(
            columns={"Incident_Norm": "__Incident_Norm_map", "Response_Type": "__Response_Type_map"}
        )

        df = df.merge(mapping, on="Incident_key", how="left")

        mapped_incident = df["__Incident_Norm_map"]
        original_incident = df["Incident"]

        unmapped_mask = mapped_incident.isna() & original_incident.notna()
        if unmapped_mask.any():
            self.unmapped_incidents.update(original_incident.loc[unmapped_mask].dropna().unique().tolist())

        mask = mapped_incident.notna()
        df.loc[mask, "Incident"] = mapped_incident[mask]
        df["Incident_Norm"] = df["Incident"]

        if "Response Type" not in df.columns:
            df["Response Type"] = pd.NA
        if "__Response_Type_map" in df.columns:
            fill_mask = df["Response Type"].isna() | (df["Response Type"].astype(str).str.strip() == "")
            df.loc[fill_mask, "Response Type"] = df.loc[fill_mask, "__Response_Type_map"]

        df.drop(columns=["Incident_key", "__Incident_Norm_map", "__Response_Type_map"], inplace=True, errors="ignore")
        return df

    def validate_cad_dataset(self, df: pd.DataFrame, sampling_method: str = "stratified") -> dict:
        self.original_columns = list(df.columns)
        self.unmapped_incidents = set()
        self.address_issue_summary = Counter()
        cleaned_df = self.clean_data(df)
        logger.info(f"Starting CAD dataset validation with {sampling_method} sampling...")
        self.validation_results["total_records"] = len(cleaned_df)
        if self.current_dataset_label:
            self.validation_results["source_dataset"] = self.current_dataset_label

        sample_df = self._create_sample(cleaned_df, sampling_method)

        if hasattr(sample_df, "attrs"):
            self.validation_results["stratum_distribution"] = sample_df.attrs.get("stratum_distribution", {})
            self.validation_results["stratification_method"] = sample_df.attrs.get(
                "stratification_method", sampling_method
            )

        self._export_sample(sample_df)

        sample_results = self._validate_sample(sample_df)
        full_results = self._extrapolate_results(sample_results, cleaned_df)
        recommendations = self._generate_validation_recommendations(full_results)

        self.validation_results.update(full_results)
        self.validation_results["unmapped_incidents"] = sorted(self.unmapped_incidents)
        self.validation_results["address_issue_summary"] = dict(self.address_issue_summary)
        self.validation_results["recommended_actions"] = recommendations
        return self.validation_results

    def _create_sample(self, df: pd.DataFrame, method: str) -> pd.DataFrame:
        if method == "stratified":
            return self._stratified_sampling(df)
        elif method == "systematic":
            return self._systematic_sampling(df)
        elif method == "random":
            return self._random_sampling(df)
        else:
            raise ValueError(f"Unknown sampling method: {method}")

    def _stratified_sampling(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Creating stratified sample...")
        df_with_strata = df.copy()

        if "Incident" in df.columns:
            incident_counts = df["Incident"].value_counts()
            top_incidents = incident_counts[incident_counts > 50].index
            df_with_strata["incident_stratum"] = df_with_strata["Incident"].apply(
                lambda x: x if x in top_incidents else "Other"
            )
            unique_strata = df_with_strata["incident_stratum"].nunique()
            logger.info("Using %d incident strata.", unique_strata)
        else:
            logger.warning("Incident column missing. Assigning all records to 'Unknown' stratum.")
            df_with_strata["incident_stratum"] = "Unknown"

        sample_size = min(self.sampling_config["stratified_sample_size"], len(df))
        try:
            sample_df, _ = train_test_split(
                df_with_strata,
                test_size=1 - (sample_size / len(df)),
                stratify=df_with_strata["incident_stratum"],
                random_state=42,
            )
            logger.info("Created stratified sample: %s records", f"{len(sample_df):,}")

            stratum_dist = df_with_strata["incident_stratum"].value_counts().to_dict()
            sample_df.attrs["stratum_distribution"] = stratum_dist
            sample_df.attrs["stratification_method"] = "incident_stratum"
        except Exception as e:
            logger.warning(f"Stratified sampling failed: {e}. Falling back to random.")
            sample_df = df.sample(n=sample_size, random_state=42)
            sample_df.attrs["stratification_method"] = "random"
            sample_df.attrs["stratum_distribution"] = {"random_sample": len(sample_df)}

        logger.info("Final sample size: %s records", f"{len(sample_df):,}")
        return sample_df

    def _build_esri_export(self, df: pd.DataFrame) -> pd.DataFrame:
        esri_columns = [
            "ReportNumberNew",
            "Incident",
            "How Reported",
            "FullAddress2",
            "PDZone",
            "Grid",
            "Time of Call",
            "cYear",
            "cMonth",
            "Hour_Calc",
            "DayofWeek",
            "Time Dispatched",
            "Time Out",
            "Time In",
            "Time Spent",
            "Time Response",
            "Officer",
            "Disposition",
            "latitude",
            "longitude",
            "Response Type",
        ]
        esri_df = pd.DataFrame(index=df.index)

        def get_series(column, default=None):
            if column in df.columns:
                return df[column]
            if default is not None:
                return pd.Series(default, index=df.index)
            return pd.Series([pd.NA] * len(df), index=df.index)

        esri_df["ReportNumberNew"] = get_series("ReportNumberNew")
        esri_df["Incident"] = get_series("Incident")
        esri_df["How Reported"] = get_series("How Reported")
        esri_df["FullAddress2"] = get_series("FullAddress2")
        esri_df["PDZone"] = pd.to_numeric(get_series("PDZone"), errors="coerce")
        esri_df["Grid"] = get_series("Grid")

        time_of_call = pd.to_datetime(get_series("Time of Call"), errors="coerce")
        esri_df["Time of Call"] = time_of_call
        esri_df["cYear"] = pd.to_numeric(get_series("cYear"), errors="coerce")
        esri_df["cMonth"] = get_series("cMonth")
        esri_df["Hour_Calc"] = time_of_call.dt.hour.astype("float64") if len(time_of_call) > 0 else pd.Series(dtype="float64")
        esri_df["DayofWeek"] = get_series("DayofWeek")
        esri_df["Time Dispatched"] = pd.to_datetime(get_series("Time Dispatched"), errors="coerce")
        esri_df["Time Out"] = pd.to_datetime(get_series("Time Out"), errors="coerce")
        esri_df["Time In"] = pd.to_datetime(get_series("Time In"), errors="coerce")

        time_spent = get_series("Time Spent")
        esri_df["Time Spent"] = time_spent.apply(lambda x: None if pd.isna(x) else str(x))
        time_response = get_series("Time Response")
        esri_df["Time Response"] = time_response.apply(lambda x: None if pd.isna(x) else str(x))

        esri_df["Officer"] = get_series("Officer")
        esri_df["Disposition"] = get_series("Disposition")
        esri_df["latitude"] = np.nan
        esri_df["longitude"] = np.nan
        esri_df["Response Type"] = get_series("Response Type")
        esri_df = esri_df[esri_columns]

        if "How Reported" in esri_df.columns:
            esri_df["How Reported"] = esri_df["How Reported"].apply(normalize_how_reported_value).apply(guard_excel_text)

        return esri_df

    def _export_sample(self, sample_df: pd.DataFrame) -> None:
        if sample_df is None or sample_df.empty:
            logger.warning("Sample DataFrame empty. Skipping sample export.")
            return
        project_root = Path(__file__).resolve().parent.parent
        sample_dir = project_root / "data" / "01_raw" / "sample"
        sample_dir.mkdir(parents=True, exist_ok=True)

        dataset_label = self.current_dataset_label or "cad_dataset"
        sample_size = len(sample_df)
        sample_name = f"{Path(dataset_label).stem}_SAMPLE_{sample_size}.csv"
        sample_path = sample_dir / sample_name

        export_df = self._build_esri_export(sample_df.copy())
        export_df.to_csv(sample_path, index=False)
        logger.info("Sample exported to %s", sample_path)
        self.validation_results["sample_output_path"] = str(sample_path)

    def _systematic_sampling(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Creating systematic sample...")
        interval = self.sampling_config["systematic_interval"]
        start_idx = np.random.randint(0, interval) if interval > 0 else 0
        sample_indices = list(range(start_idx, len(df), max(interval, 1)))
        sample_df = df.iloc[sample_indices].copy()
        logger.info(f"Created systematic sample: {len(sample_df):,} records (interval: {interval})")
        return sample_df

    def _random_sampling(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Creating random sample...")
        sample_size = min(self.sampling_config["stratified_sample_size"], len(df))
        sample_df = df.sample(n=sample_size, random_state=42)
        logger.info(f"Created random sample: {len(sample_df):,} records")
        return sample_df

    def _categorize_how_reported(self, value):
        if pd.isna(value):
            return "Unknown"
        value_str = str(value).upper()
        if any(term in value_str for term in ["9-1-1", "911", "EMERGENCY"]):
            return "Emergency"
        elif any(term in value_str for term in ["PHONE", "CALL"]):
            return "Phone"
        elif any(term in value_str for term in ["WALK", "PERSON"]):
            return "Walk-in"
        elif any(term in value_str for term in ["SELF", "INITIATED"]):
            return "Self-Initiated"
        else:
            return "Other"

    def _categorize_time_period(self, hour):
        if pd.isna(hour):
            return "Unknown"
        try:
            hour = int(hour)
            if 6 <= hour < 12:
                return "Morning"
            elif 12 <= hour < 18:
                return "Afternoon"
            elif 18 <= hour < 22:
                return "Evening"
            else:
                return "Night"
        except Exception:
            return "Unknown"

    def _validate_sample(self, sample_df: pd.DataFrame) -> dict:
        logger.info("Running validation rules on sample...")
        results = {"critical_rules": {}, "important_rules": {}, "optional_rules": {}, "sample_size": len(sample_df)}

        for category, rules in self.validation_rules.items():
            for rule_id, rule in rules.items():
                result = self._apply_validation_rule(sample_df, rule)
                result.update(
                    {
                        "rule_id": rule_id,
                        "description": rule["description"],
                        "severity": rule["severity"],
                        "fix_suggestion": rule.get("fix_suggestion", ""),
                    }
                )
                results[category][rule_id] = result

        return results

    def _apply_validation_rule(self, df: pd.DataFrame, rule: dict) -> dict:
        rule_id = rule["rule_id"]
        field = rule.get("field")
        fields = rule.get("fields", [field] if field else [])
        result = {
            "rule_id": rule_id,
            "description": rule["description"],
            "severity": rule["severity"],
            "passed": 0,
            "failed": 0,
            "pass_rate": 0.0,
            "failed_records": [],
            "fix_suggestion": rule.get("fix_suggestion", ""),
            "sample_size": len(df),
        }
        missing_fields = [f for f in fields if f not in df.columns]
        if missing_fields:
            result.update({"error": f"Missing fields: {missing_fields}", "failed": len(df)})
            return result

        if rule_id == "CRIT_001":
            result = self._validate_case_number_format(df, result)
        elif rule_id == "CRIT_002":
            result = self._validate_case_number_uniqueness_per_year(df, result)  # Updated
        elif rule_id == "CRIT_003":
            result = self._validate_call_datetime(df, result)
        elif rule_id == "CRIT_004":
            result = self._validate_incident_type_presence(df, result)
        elif rule_id == "IMP_001":
            result = self._validate_address_completeness(df, result)
        elif rule_id == "IMP_002":
            result = self._validate_officer_assignment(df, result)
        elif rule_id == "IMP_003":
            result = self._validate_disposition_consistency(df, result)
        elif rule_id == "IMP_004":
            result = self._validate_time_sequence(df, result)
        elif rule_id == "IMP_005":
            result = self._validate_datetime_duration(df, result)
        elif rule_id == "IMP_006":
            result = self._validate_time_spent(df, result)
        elif rule_id == "OPT_001":
            result = self._validate_how_reported(df, result)
        elif rule_id == "OPT_002":
            result = self._validate_zone_validity(df, result)
        elif rule_id == "OPT_003":
            result = self._validate_response_type_consistency(df, result)

        result["pass_rate"] = result["passed"] / result["sample_size"] if result["sample_size"] > 0 else 0.0
        return result

    def _validate_case_number_format(self, df: pd.DataFrame, result: dict) -> dict:
        field = "ReportNumberNew"
        series = df[field].astype(str)
        valid = series.str.match(CASE_NUM_RE, na=False)
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        result["failed_records"] = df.loc[~valid, field].value_counts().head(10).to_dict()
        return result

    # --- Updated uniqueness: per year, same suffix must be unique within that year ---
    def _validate_case_number_uniqueness_per_year(self, df: pd.DataFrame, result: dict) -> dict:
        field = "ReportNumberNew"
        series = df[field].astype(str)

        # Extract year and numeric suffix
        parsed = series.apply(self._extract_year_from_case)
        years = parsed.apply(lambda t: t[0])
        suffixes = parsed.apply(lambda t: t[1])

        # Records with valid parsed year and suffix
        valid_mask = years.notna() & suffixes.astype(bool)
        df_valid = df[valid_mask].copy()
        df_valid["_year"] = years[valid_mask]
        df_valid["_suffix"] = suffixes[valid_mask]

        # Count duplicates within the same year on suffix
        dup_counts = (
            df_valid.groupby(["_year", "_suffix"]).size().rename("count").reset_index()
        )
        bad_pairs = dup_counts[dup_counts["count"] > 1].copy()

        # Mark rows that are part of duplicate pairs
        if not bad_pairs.empty:
            merge_keys = bad_pairs[["_year", "_suffix"]].assign(_dup=True)
            flagged = df_valid.merge(merge_keys, on=["_year", "_suffix"], how="left")["_dup"].fillna(False)
            failed = int(flagged.sum())
            passed = len(df) - failed
            # Build top offenders summary
            bad_pairs_sorted = bad_pairs.sort_values("count", ascending=False).head(10)
            result["failed_records"] = [
                {"year": int(r._year), "case_suffix": r._suffix, "count": int(r["count"])}
                for r in bad_pairs_sorted.itertuples(index=False)
            ]
        else:
            failed = 0
            passed = len(df)
            result["failed_records"] = []

        result.update({"passed": passed, "failed": failed})
        return result

    def _validate_call_datetime(self, df: pd.DataFrame, result: dict) -> dict:
        field = "Time of Call"
        parsed = pd.to_datetime(df[field], errors="coerce")
        valid = parsed.notna() & (parsed >= "2020-01-01") & (parsed <= "2030-12-31")
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        result["failed_records"] = df.loc[~valid, field].value_counts().head(10).to_dict()
        return result

    def _validate_incident_type_presence(self, df: pd.DataFrame, result: dict) -> dict:
        field = "Incident"
        valid = df[field].notna() & (df[field].astype(str).str.strip() != "")
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        result["failed_records"] = df.loc[~valid, field].value_counts().head(10).to_dict()
        return result

    def _validate_address_completeness(self, df: pd.DataFrame, result: dict) -> dict:
        field = "FullAddress2"
        generic = {"UNKNOWN", "NOT PROVIDED", "N/A", "NONE", "", "TBD", "TO BE DETERMINED"}

        def evaluate_address(value):
            if pd.isna(value):
                return False, ["missing_address"]
            text = str(value).upper().strip()
            text = MULTISPACE_RE.sub(" ", text)
            if text in generic:
                return False, ["generic_placeholder"]
            issues = []
            normalized = MULTISPACE_RE.sub(" ", text.replace(" & ", " & "))
            has_city_zip = normalized.endswith(", HACKENSACK, NJ, 07601")
            if not has_city_zip:
                issues.append("missing_city_state_zip")
            is_intersection = "&" in normalized
            if not is_intersection and not re.match(r"^\d+ ", normalized):
                issues.append("missing_house_number")
            if not STREET_SUFFIX_RE.search(normalized) and not is_intersection:
                issues.append("missing_street_suffix")
            if is_intersection and " & " not in normalized:
                issues.append("intersection_spacing")
            if issues:
                return False, issues
            return True, []

        passes = []
        issue_counter = Counter()
        for addr in df[field]:
            is_valid, issues = evaluate_address(addr)
            passes.append(is_valid)
            if not is_valid:
                issue_counter.update(issues or ["unknown_format"])

        valid_series = pd.Series(passes, index=df.index)
        result.update({"passed": valid_series.sum(), "failed": (~valid_series).sum()})
        result["failed_records"] = dict(issue_counter.most_common(10))
        self.address_issue_summary.update(issue_counter)
        return result

    def _validate_officer_assignment(self, df: pd.DataFrame, result: dict) -> dict:
        dispatched = df["Time Dispatched"].notna() if "Time Dispatched" in df.columns else pd.Series([True] * len(df))
        has_officer = df["Officer"].notna() & (df["Officer"].astype(str).str.strip() != "")
        valid = ~(dispatched & ~has_officer)
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        result["failed_records"] = df.loc[~valid, "Officer"].value_counts().head(10).to_dict()
        return result

    def _validate_disposition_consistency(self, df: pd.DataFrame, result: dict) -> dict:
        field = "Disposition"
        valid_list = set(self.config["validation_lists"]["valid_dispositions"])
        valid = df[field].astype(str).str.strip().isin(valid_list)
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        result["failed_records"] = df.loc[~valid, field].value_counts().head(10).to_dict()
        return result

    def _validate_time_sequence(self, df: pd.DataFrame, result: dict) -> dict:
        fields = ["Time of Call", "Time Dispatched", "Time Out", "Time In"]
        times = {f: pd.to_datetime(df.get(f), errors="coerce") for f in fields}
        valid_sequence = pd.Series([True] * len(df), index=df.index)
        valid_sequence &= (times["Time of Call"] <= times["Time Dispatched"]) | times["Time of Call"].isna() | times[
            "Time Dispatched"
        ].isna()
        valid_sequence &= (times["Time Dispatched"] <= times["Time Out"]) | times["Time Dispatched"].isna() | times[
            "Time Out"
        ].isna()
        valid_sequence &= (times["Time Out"] <= times["Time In"]) | times["Time Out"].isna() | times["Time In"].isna()
        result.update({"passed": valid_sequence.sum(), "failed": (~valid_sequence).sum()})
        if (~valid_sequence).any():
            failed_df = df.loc[~valid_sequence, fields].head(10)
            result["failed_records"] = failed_df[fields].to_dict(orient="records")
        return result

    def _validate_datetime_duration(self, df: pd.DataFrame, result: dict) -> dict:
        fields = ["Time of Call", "Time Dispatched", "Time Out", "Time In"]
        parsed = {f: pd.to_datetime(df[f], errors="coerce") if f in df.columns else pd.Series(pd.NaT, index=df.index) for f in fields}
        valid = pd.Series([True] * len(df), index=df.index)
        if "Time of Call" in df.columns and "Time Dispatched" in df.columns:
            response = parsed["Time Dispatched"] - parsed["Time of Call"]
            valid &= (response >= pd.Timedelta(0)) | response.isna()
        if "Time Dispatched" in df.columns and "Time Out" in df.columns:
            out = parsed["Time Out"] - parsed["Time Dispatched"]
            valid &= (out >= pd.Timedelta(0)) | out.isna()
        if "Time Out" in df.columns and "Time In" in df.columns:
            back = parsed["Time In"] - parsed["Time Out"]
            valid &= (back >= pd.Timedelta(0)) | back.isna()
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        if (~valid).any():
            failed_df = df.loc[~valid, fields].head(10)
            result["failed_records"] = failed_df[fields].to_dict(orient="records")
        return result

    def _validate_time_spent(self, df: pd.DataFrame, result: dict) -> dict:
        field = "Time Spent"
        if field in df.columns:
            durations = pd.to_timedelta(df[field], errors="coerce")
            valid = durations.notna() & (durations >= pd.Timedelta(0)) & (durations <= pd.Timedelta(days=1))
            result.update({"passed": valid.sum(), "failed": (~valid).sum()})
            result["failed_records"] = df.loc[~valid, field].value_counts().head(10).to_dict()
        else:
            result.update({"passed": 0, "failed": len(df), "failed_records": {}})
        return result

    def _validate_how_reported(self, df: pd.DataFrame, result: dict) -> dict:
        field = "How Reported"
        valid_list = set(self.config["validation_lists"]["how_reported"])
        normalized = df[field].apply(normalize_how_reported_value)
        is_valid = normalized.isin(valid_list)
        result.update({"passed": is_valid.sum(), "failed": (~is_valid).sum()})
        if (~is_valid).any():
            result["failed_records"] = normalized[~is_valid].value_counts().head(10).to_dict()
        return result

    def _validate_zone_validity(self, df: pd.DataFrame, result: dict) -> dict:
        field = "PDZone"
        valid_zones = set(self.config["validation_lists"]["valid_zones"])
        valid = df[field].astype(str).str.strip().isin(valid_zones)
        result.update({"passed": valid.sum(), "failed": (~valid).sum()})
        result["failed_records"] = df.loc[~valid, field].value_counts().head(10).to_dict()
        return result

    def _validate_response_type_consistency(self, df: pd.DataFrame, result: dict) -> dict:
        emergency_incidents = set(self.config["validation_lists"]["emergency_incidents"])
        non_emergency_incidents = set(self.config["validation_lists"]["non_emergency_incidents"])
        incident = df["Incident"].astype(str).str.upper()
        response = df["Response Type"].astype(str).str.upper()
        is_emergency_incident = incident.isin(emergency_incidents)
        is_emergency_response = response.isin(["EMERGENCY", "PRIORITY"])
        is_non_emergency_incident = incident.isin(non_emergency_incidents)
        is_non_emergency_response = response.isin(["NON-EMERGENCY", "ROUTINE"])
        consistent = (is_emergency_incident & is_emergency_response) | (is_non_emergency_incident & is_non_emergency_response) | (~is_emergency_incident & ~is_non_emergency_incident)
        result.update({"passed": consistent.sum(), "failed": (~consistent).sum()})
        if (~consistent).any():
            failed_df = df.loc[~consistent, ["Incident", "Response Type"]].head(10)
            result["failed_records"] = failed_df.to_dict(orient="records")
        return result

    def _extrapolate_results(self, sample_results: dict, full_df: pd.DataFrame) -> dict:
        extrapolated = {"critical_rules": {}, "important_rules": {}, "optional_rules": {}}
        full_size = len(full_df)
        sample_size = sample_results["sample_size"]
        factor = full_size / sample_size if sample_size > 0 else 0

        for category in extrapolated.keys():
            for rule_id, res in sample_results[category].items():
                extrapolated[category][rule_id] = {
                    "rule_id": rule_id,
                    "description": res["description"],
                    "severity": res["severity"],
                    "sample_passed": res["passed"],
                    "sample_failed": res["failed"],
                    "sample_pass_rate": res["pass_rate"],
                    "estimated_full_passed": int(res["passed"] * factor),
                    "estimated_full_failed": int(res["failed"] * factor),
                    "estimated_full_pass_rate": res["pass_rate"],
                    "failed_records": res.get("failed_records", {}),
                    "fix_suggestion": res.get("fix_suggestion", ""),
                }
        extrapolated["overall_quality_score"] = self._calculate_overall_quality_score(extrapolated)
        return extrapolated

    def _calculate_overall_quality_score(self, results: dict) -> float:
        weights = {"critical": 0.5, "important": 0.3, "optional": 0.2}
        score, total_weight = 0.0, 0.0
        for category, weight in weights.items():
            rates = [r["estimated_full_pass_rate"] for r in results[f"{category}_rules"].values()]
            if rates:
                avg_rate = sum(rates) / len(rates)
                score += avg_rate * weight
                total_weight += weight
        return (score / total_weight * 100) if total_weight > 0 else 0.0

    def _generate_validation_recommendations(self, results: dict) -> list:
        recommendations = []
        for category in ["critical", "important", "optional"]:
            threshold = self.sampling_config["quality_thresholds"][category]
            for rule_id, res in results[f"{category}_rules"].items():
                if res["estimated_full_pass_rate"] < threshold:
                    recommendations.append(
                        f"{category.upper()}: {res['description']} - Pass rate: {res['estimated_full_pass_rate']:.1%} (threshold: {threshold:.1%})"
                    )
                    recommendations.append(f"  Fix suggestion: {res['fix_suggestion']}")
        unmapped = self.validation_results.get("unmapped_incidents", [])
        if unmapped:
            sample_examples = ", ".join(list(unmapped)[:5])
            recommendations.append(
                f"INCIDENT MAPPING: {len(unmapped)} incident types not found in CallType_Categories.csv. Examples: {sample_examples}"
            )
        address_issues = self.validation_results.get("address_issue_summary") or {}
        if address_issues:
            top_issue, count = max(address_issues.items(), key=lambda item: item[1])
            recommendations.append(
                f"ADDRESS QUALITY: {count} address records flagged (top issue: {top_issue}). Review CAD vs RMS/Geocode backfill."
            )
        return recommendations

    def create_validation_report(self, output_path: str = None) -> str:
        dataset_label = self.validation_results.get("source_dataset") or getattr(self, "current_dataset_label", None)
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = ""
            if dataset_label:
                label_stem = os.path.splitext(os.path.basename(dataset_label))[0]
                year_match = re.match(r"^(\d{4})", label_stem)
                if year_match:
                    prefix = f"{year_match.group(1)}_"
                else:
                    sanitized = re.sub(r"[^A-Za-z0-9]+", "_", label_stem).strip("_")
                    if sanitized:
                        prefix = f"{sanitized}_"
            output_path = f"{prefix}cad_validation_report_{timestamp}.json"

        report = {
            "validation_metadata": {
                "timestamp": datetime.now().isoformat(),
                "validator_version": "CAD_Validator_2025.10.17",
                "total_records_validated": self.validation_results["total_records"],
                "stratification_method": self.validation_results.get("stratification_method", "unknown"),
                "source_dataset": dataset_label,
                "report_filename": output_path,
            },
            "validation_summary": {
                "overall_quality_score": self.validation_results.get("overall_quality_score", 0),
                "recommendations_count": len(self.validation_results.get("recommended_actions", [])),
            },
            "sampling_metadata": {
                "stratum_distribution": self.validation_results.get("stratum_distribution", {}),
                "stratification_method": self.validation_results.get("stratification_method", "unknown"),
                "sample_size": self.sampling_config.get("stratified_sample_size", 1000),
            },
            "recommended_actions": self.validation_results.get("recommended_actions", []),
            "validation_details": self.validation_results,
            "sampling_configuration": self.sampling_config,
        }

        def clean_for_json(obj):
            if isinstance(obj, dict):
                return {str(k): clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [clean_for_json(item) for item in obj]
            elif hasattr(obj, "isoformat"):
                return obj.isoformat()
            elif isinstance(obj, (pd.Timestamp, pd.Timedelta)):
                return str(obj)
            elif hasattr(obj, "tolist"):
                return obj.tolist()
            elif hasattr(obj, "__dict__"):
                return str(obj)
            else:
                return obj

        cleaned_report = clean_for_json(report)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_report, f, indent=2, ensure_ascii=False)
        logger.info(f"Validation report saved: {output_path}")
        return output_path

def validate_cad_dataset_with_sampling(
    config: Dict[str, Any], sampling_method: str = "stratified", validator: CADDataValidator | None = None
):
    cad_file = config.get("file_path", "")
    if not cad_file:
        raise ValueError("Config must include 'file_path' key.")
    logger.info(f"Loading data from: {cad_file}")
    df = pd.read_excel(cad_file) if cad_file.lower().endswith(".xlsx") else pd.read_csv(cad_file)
    if validator is None:
        validator = CADDataValidator(config_path=config.get("config_path", "config_enhanced.json"))
    else:
        config_path = config.get("config_path")
        if config_path and config_path != validator.config_path:
            validator.reload_config(config_path)
    dataset_label = os.path.basename(cad_file)
    validator.current_dataset_label = dataset_label
    validator.validation_results["source_dataset"] = dataset_label
    results = validator.validate_cad_dataset(df, sampling_method)
    report_path = validator.create_validation_report()
    return results, report_path

def main():
    pd.options.mode.copy_on_write = True
    parser = argparse.ArgumentParser(description="Clean and validate CAD datasets.")
    parser.add_argument(
        "--config",
        default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config_enhanced.json"),
        help="Path to configuration JSON file.",
    )
    parser.add_argument(
        "--raw-dir",
        default=r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Pipeline\data\01_raw",
        help="Directory containing CAD source files.",
    )
    parser.add_argument(
        "--sampling-method",
        choices=["stratified", "systematic", "random"],
        default="stratified",
        help="Sampling method to apply.",
    )
    parser.add_argument("--reload-config", action="store_true", help="Reload configuration before processing.")
    args = parser.parse_args()

    validator = CADDataValidator(config_path=args.config)
    if args.reload_config:
        validator.reload_config(args.config)

    all_cad_files = sorted([p for p in Path(args.raw_dir).glob("*.xlsx")])
    print(f"Found {len(all_cad_files)} files to process.")

    for cad_file_path in all_cad_files:
        print(f"\n{'='*60}\nPROCESSING: {cad_file_path.name}\n{'='*60}")
        validator.current_dataset_label = cad_file_path.name
        validator.validation_results["source_dataset"] = validator.current_dataset_label
        results, report_file = validate_cad_dataset_with_sampling(
            {"file_path": str(cad_file_path), "config_path": args.config}, args.sampling_method, validator=validator
        )
        print(f"  - Overall Quality Score: {results.get('overall_quality_score', 0):.1f}/100")
        print(f"  - Full report saved to: {report_file}")

    print("\nAll files processed successfully!")

if __name__ == "__main__":
    main()
```

```python
# file: tests/test_validate_and_clean.py
import pandas as pd
from 01_validate_and_clean import CADDataValidator

def _df(rows):
    return pd.DataFrame(rows)

def test_case_number_uniqueness_per_year_all_good():
    df = _df([
        {"ReportNumberNew": "23-000001"},
        {"ReportNumberNew": "2023-000001"},  # same suffix as first but different normalized year
        {"ReportNumberNew": "24-000001"},
        {"ReportNumberNew": "2024-000002"},
    ])
    v = CADDataValidator()
    res = {}
    res = v._validate_case_number_uniqueness_per_year(df, {"passed": 0, "failed": 0, "failed_records": []})
    assert res["failed"] == 0
    assert res["passed"] == len(df)

def test_case_number_uniqueness_per_year_duplicates_within_year():
    df = _df([
        {"ReportNumberNew": "2023-123456"},
        {"ReportNumberNew": "23-123456"},   # same year 2023 after normalization -> duplicate
        {"ReportNumberNew": "2024-123456"}, # different year -> not duplicate with above
        {"ReportNumberNew": "24-123456"},   # same year 2024 -> duplicate with previous
    ])
    v = CADDataValidator()
    res = v._validate_case_number_uniqueness_per_year(df, {"passed": 0, "failed": 0, "failed_records": []})
    # two duplicates within years -> 4 rows flagged
    assert res["failed"] == 4
    assert any(item["year"] == 2023 and item["case_suffix"] == "123456" for item in res["failed_records"])
    assert any(item["year"] == 2024 and item["case_suffix"] == "123456" for item in res["failed_records"])

def test_case_number_format_regex_accepts_upper_suffix():
    df = _df([
        {"ReportNumberNew": "2025-000001A"},
        {"ReportNumberNew": "25-000001"},
        {"ReportNumberNew": "25-000001B"},
    ])
    v = CADDataValidator()
    res = v._validate_case_number_format(df, {"passed": 0, "failed": 0, "failed_records": []})
    assert res["failed"] == 0
```

```toml
# file: pyproject.toml
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cad-data-validator"
version = "0.1.0"
description = "CAD data cleaning and validation utilities"
requires-python = ">=3.10"
dependencies = [
    "pandas>=2.1",
    "numpy>=1.26",
    "scikit-learn>=1.3",
    "pydantic>=2.5",
]

[tool.pytest.ini_options]
pythonpath = [
  "."
]
testpaths = ["tests"]
addopts = "-q"
```

**a.** Want me to add parametrized tests for the address validator edge cases.  
**b.** Do you want CLI flag `--year-duplicate-scope {global,per-year}` to switch behavior without code changes.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)