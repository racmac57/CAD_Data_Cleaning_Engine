"""
Burglary Classification via Ollama LLM
=======================================
Author: Claude Code
Created: 2025-11-16 (EST)
Modified: 2025-11-16 (EST)

Purpose:
    Classify burglary incidents into Auto, Commercial, or Residence types
    using local Ollama LLM inference on RMS narrative text.
    Provides confidence scores and reasoning for each classification.

Background:
    Burglary records in CAD lack granular subtype classification. RMS
    narratives contain contextual details (vehicle info, business names,
    residential addresses) that allow accurate classification via LLM.

Requirements:
    - Ollama server running locally: http://localhost:11434
    - Install: https://ollama.ai/download
    - Pull model: ollama pull llama3.2

Inputs:
    - RMS data with Narrative column and Case Number
    - CAD data with ReportNumberNew for burglary incidents

Outputs:
    - data/02_reports/burglary_classification.csv with columns:
        * ReportNumberNew: Case number
        * Burglary_Type: Auto | Commercial | Residence
        * Confidence: 0.0-1.0 score
        * Reasoning: LLM explanation
        * Manual_Review: Flag for low confidence (<0.8)

Usage:
    python scripts/classify_burglary_ollama.py --rms-file data/rms/rms_export.xlsx
    python scripts/classify_burglary_ollama.py --rms-file data/rms/rms_export.xlsx --model llama3.2
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
import pandas as pd
import requests
from tqdm import tqdm


def check_ollama_connection(base_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama server is running and accessible.

    Args:
        base_url: Base URL for Ollama API

    Returns:
        bool: True if server is accessible, False otherwise
    """
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def classify_burglary_narrative(
    narrative: str,
    model: str = "llama3.2",
    base_url: str = "http://localhost:11434"
) -> Dict[str, any]:
    """Classify burglary type from narrative text using Ollama.

    Args:
        narrative: RMS narrative text to classify
        model: Ollama model name to use
        base_url: Base URL for Ollama API

    Returns:
        dict with keys: burglary_type, confidence, reasoning
    """
    # Construct classification prompt
    prompt = f"""You are a police records classifier. Analyze the following burglary narrative and classify it into exactly ONE of these types:

1. AUTO - Vehicle burglary (car, truck, motorcycle, etc.)
2. COMMERCIAL - Business or commercial property burglary
3. RESIDENCE - Residential property burglary (house, apartment, etc.)

NARRATIVE:
{narrative}

Respond in valid JSON format with these fields:
- burglary_type: "AUTO", "COMMERCIAL", or "RESIDENCE"
- confidence: A number between 0 and 1 (e.g., 0.95 for high confidence)
- reasoning: Brief explanation (max 50 words)

Example response:
{{"burglary_type": "AUTO", "confidence": 0.92, "reasoning": "Narrative mentions vehicle make/model and items stolen from car."}}

JSON response:"""

    try:
        # Call Ollama API
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=30
        )

        if response.status_code != 200:
            return {
                "burglary_type": "UNKNOWN",
                "confidence": 0.0,
                "reasoning": f"API error: {response.status_code}"
            }

        # Parse response
        result = response.json()
        response_text = result.get("response", "")

        # Parse JSON from response
        try:
            classification = json.loads(response_text)

            # Validate and normalize
            burglary_type = str(classification.get("burglary_type", "UNKNOWN")).upper().strip()
            if burglary_type not in ["AUTO", "COMMERCIAL", "RESIDENCE"]:
                burglary_type = "UNKNOWN"

            confidence = float(classification.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

            reasoning = str(classification.get("reasoning", ""))[:200]  # Truncate to 200 chars

            return {
                "burglary_type": burglary_type,
                "confidence": confidence,
                "reasoning": reasoning
            }

        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: try to extract type from text response
            response_upper = response_text.upper()
            if "AUTO" in response_upper:
                burglary_type = "AUTO"
            elif "COMMERCIAL" in response_upper:
                burglary_type = "COMMERCIAL"
            elif "RESIDENCE" in response_upper or "RESIDENTIAL" in response_upper:
                burglary_type = "RESIDENCE"
            else:
                burglary_type = "UNKNOWN"

            return {
                "burglary_type": burglary_type,
                "confidence": 0.5,
                "reasoning": f"Parse error: {str(e)}"
            }

    except requests.RequestException as e:
        return {
            "burglary_type": "UNKNOWN",
            "confidence": 0.0,
            "reasoning": f"Request failed: {str(e)}"
        }


def classify_burglaries_from_rms(
    rms_df: pd.DataFrame,
    case_number_col: str = 'Case Number',
    narrative_col: str = 'Narrative',
    model: str = "llama3.2",
    base_url: str = "http://localhost:11434",
    confidence_threshold: float = 0.8
) -> pd.DataFrame:
    """Classify all burglary records in RMS DataFrame.

    Args:
        rms_df: RMS DataFrame with narratives
        case_number_col: Column name for case numbers
        narrative_col: Column name for narrative text
        model: Ollama model to use
        base_url: Ollama API base URL
        confidence_threshold: Threshold for manual review flag

    Returns:
        DataFrame with classification results
    """
    results = []

    print(f"🤖 Classifying {len(rms_df):,} burglary records using Ollama ({model})...")

    for idx, row in tqdm(rms_df.iterrows(), total=len(rms_df), desc="Classifying"):
        case_number = row.get(case_number_col)
        narrative = row.get(narrative_col, "")

        # Skip if narrative is empty
        if pd.isna(narrative) or str(narrative).strip() == "":
            results.append({
                'ReportNumberNew': case_number,
                'Burglary_Type': 'UNKNOWN',
                'Confidence': 0.0,
                'Reasoning': 'Empty narrative',
                'Manual_Review': True
            })
            continue

        # Classify
        classification = classify_burglary_narrative(narrative, model, base_url)

        results.append({
            'ReportNumberNew': case_number,
            'Burglary_Type': classification['burglary_type'],
            'Confidence': classification['confidence'],
            'Reasoning': classification['reasoning'],
            'Manual_Review': classification['confidence'] < confidence_threshold
        })

    return pd.DataFrame(results)


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Classify burglary incidents using Ollama LLM."
    )
    parser.add_argument(
        "--rms-file",
        required=True,
        help="Path to RMS Excel file with burglary narratives"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to save classification CSV (default: data/02_reports/burglary_classification.csv)"
    )
    parser.add_argument(
        "--model",
        default="llama3.2",
        help="Ollama model name (default: llama3.2)"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:11434",
        help="Ollama API base URL (default: http://localhost:11434)"
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.8,
        help="Confidence threshold for manual review flag (default: 0.8)"
    )
    parser.add_argument(
        "--case-col",
        default="Case Number",
        help="RMS case number column name"
    )
    parser.add_argument(
        "--narrative-col",
        default="Narrative",
        help="RMS narrative column name"
    )
    args = parser.parse_args()

    # Check Ollama connection
    print(f"🔌 Checking Ollama connection at {args.base_url}...")
    if not check_ollama_connection(args.base_url):
        print(f"\n❌ ERROR: Cannot connect to Ollama at {args.base_url}")
        print("\nPlease ensure:")
        print("  1. Ollama is installed: https://ollama.ai/download")
        print("  2. Ollama server is running: ollama serve")
        print(f"  3. Model is available: ollama pull {args.model}")
        return

    print(f"✅ Ollama connection successful")

    # Load RMS data
    rms_file = Path(args.rms_file)
    if not rms_file.exists():
        raise FileNotFoundError(f"RMS file not found: {rms_file}")

    print(f"\n📂 Loading RMS data from: {rms_file}")
    if rms_file.suffix == '.xlsx':
        rms_df = pd.read_excel(rms_file)
    else:
        rms_df = pd.read_csv(rms_file)

    print(f"   Loaded {len(rms_df):,} records")

    # Validate columns
    if args.case_col not in rms_df.columns:
        raise ValueError(f"Case number column '{args.case_col}' not found in RMS data")
    if args.narrative_col not in rms_df.columns:
        raise ValueError(f"Narrative column '{args.narrative_col}' not found in RMS data")

    # Filter to burglary records (if Incident Type column exists)
    incident_cols = [col for col in rms_df.columns if 'incident' in col.lower() and 'type' in col.lower()]
    if incident_cols:
        burglary_mask = rms_df[incident_cols[0]].astype(str).str.upper().str.contains('BURG', na=False)
        rms_df = rms_df[burglary_mask].copy()
        print(f"   Filtered to {len(rms_df):,} burglary records")

    if len(rms_df) == 0:
        print("\n⚠️  No burglary records found to classify")
        return

    # Classify
    results_df = classify_burglaries_from_rms(
        rms_df,
        case_number_col=args.case_col,
        narrative_col=args.narrative_col,
        model=args.model,
        base_url=args.base_url,
        confidence_threshold=args.confidence_threshold
    )

    # Summary statistics
    print("\n" + "="*60)
    print("CLASSIFICATION SUMMARY")
    print("="*60)
    print(f"Total classified:        {len(results_df):,}")
    print(f"\nBreakdown by type:")
    print(results_df['Burglary_Type'].value_counts().to_string())
    print(f"\nConfidence distribution:")
    print(f"  High (≥{args.confidence_threshold}):   {(results_df['Confidence'] >= args.confidence_threshold).sum():,}")
    print(f"  Low (<{args.confidence_threshold}):    {(results_df['Confidence'] < args.confidence_threshold).sum():,}")
    print(f"\nManual review required:  {results_df['Manual_Review'].sum():,}")
    print("="*60)

    # Save output
    output_path = args.output
    if output_path is None:
        project_root = Path(__file__).resolve().parent.parent
        output_path = project_root / 'data' / '02_reports' / 'burglary_classification.csv'

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n💾 Classification results saved to: {output_path}")

    # Show sample results
    print("\nSample classifications:")
    sample = results_df.head(5)[['ReportNumberNew', 'Burglary_Type', 'Confidence', 'Manual_Review']]
    print(sample.to_string(index=False))

    print(f"\n✨ Classification complete!")


if __name__ == "__main__":
    main()
