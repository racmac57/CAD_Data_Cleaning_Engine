"""
Case Number Generator
=====================
Author: Claude Code
Created: 2025-11-16 (EST)
Modified: 2025-11-16 (EST)

Purpose:
    Generate standardized ReportNumberNew values for CAD records.
    Implements YY-XXXXXX format for new reports and YY-XXXXXXA for supplements.
    Maintains per-year sequence counters with letter suffixes for supplements.

Format Specification:
    - NEW reports:        YY-XXXXXX (e.g., 25-000001)
    - SUPPLEMENT reports: YY-XXXXXXA (e.g., 25-000001A, 25-000001B, etc.)
    - Sequences reset each calendar year
    - Supplement suffixes: A-Z (max 26 supplements per case)

Inputs:
    - CAD DataFrame with columns: report_date, report_type
    - Sequence tracker: ref/case_number_sequences.json

Outputs:
    - DataFrame with ReportNumberNew column populated
    - Updated ref/case_number_sequences.json

Usage:
    from generate_case_numbers import generate_case_numbers
    df = generate_case_numbers(df, report_date_col='Time of Call', report_type_col='ReportType')
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
import pandas as pd
import pytest


class CaseNumberGenerator:
    """Generates standardized case numbers with year-based sequencing."""

    def __init__(self, sequence_file: str = None):
        """Initialize case number generator.

        Args:
            sequence_file: Path to JSON file tracking sequences. If None, uses default.
        """
        if sequence_file is None:
            project_root = Path(__file__).resolve().parent.parent
            sequence_file = project_root / 'ref' / 'case_number_sequences.json'

        self.sequence_file = Path(sequence_file)
        self.sequences = self._load_sequences()

    def _load_sequences(self) -> Dict[str, int]:
        """Load sequence counters from JSON file.

        Returns:
            dict: Year -> next sequence number mapping
        """
        if not self.sequence_file.exists():
            # Initialize with empty sequences
            return {}

        try:
            with open(self.sequence_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load sequences from {self.sequence_file}: {e}")
            return {}

    def _save_sequences(self):
        """Persist sequence counters to JSON file."""
        self.sequence_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.sequence_file, 'w') as f:
            json.dump(self.sequences, f, indent=2)

    def _get_next_sequence(self, year: str) -> int:
        """Get next sequence number for a given year.

        Args:
            year: Two-digit year string (e.g., '25')

        Returns:
            int: Next sequence number for that year
        """
        if year not in self.sequences:
            self.sequences[year] = 1
        else:
            self.sequences[year] += 1
        return self.sequences[year]

    def _format_case_number(self, year: str, sequence: int, supplement_suffix: str = '') -> str:
        """Format a case number according to specification.

        Args:
            year: Two-digit year string
            sequence: Sequence number (1-999999)
            supplement_suffix: Letter suffix for supplements (A-Z) or empty string

        Returns:
            str: Formatted case number (e.g., '25-000001' or '25-000001A')
        """
        return f"{year}-{sequence:06d}{supplement_suffix}"

    def generate_for_record(
        self,
        report_date: datetime,
        report_type: str,
        parent_case: str = None
    ) -> str:
        """Generate case number for a single record.

        Args:
            report_date: Date of the report
            report_type: Report type ('NEW' or 'SUPPLEMENT')
            parent_case: For supplements, the parent case number (e.g., '25-000001')

        Returns:
            str: Generated case number

        Raises:
            ValueError: If invalid report_type or missing parent_case for supplement
        """
        year = report_date.strftime('%y')  # Two-digit year
        report_type = str(report_type).upper().strip()

        if report_type == 'NEW':
            # Generate new sequence
            sequence = self._get_next_sequence(year)
            case_number = self._format_case_number(year, sequence)
            self._save_sequences()  # Persist updated sequence
            return case_number

        elif report_type == 'SUPPLEMENT':
            # Must have parent case
            if not parent_case:
                raise ValueError("SUPPLEMENT reports require parent_case parameter")

            # Extract year and sequence from parent case (e.g., '25-000001' -> year='25', seq=1)
            try:
                parts = parent_case.split('-')
                if len(parts) != 2:
                    raise ValueError(f"Invalid parent case format: {parent_case}")

                parent_year = parts[0]
                parent_seq_str = parts[1].rstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ')  # Remove any existing suffix
                parent_seq = int(parent_seq_str)

                # Find existing supplements for this parent case
                # Pattern: YY-XXXXXXA, YY-XXXXXXB, etc.
                existing_supplements = []
                for key in self.sequences.get(f"{parent_year}_supplements", {}):
                    if key.startswith(f"{parent_year}-{parent_seq:06d}"):
                        existing_supplements.append(key)

                # Determine next suffix letter
                if not existing_supplements:
                    suffix = 'A'
                else:
                    # Get highest suffix letter
                    last_suffix = max(s[-1] for s in existing_supplements)
                    if last_suffix == 'Z':
                        raise ValueError(f"Maximum supplements (26) reached for case {parent_case}")
                    suffix = chr(ord(last_suffix) + 1)

                # Track this supplement
                supp_key = f"{parent_year}_supplements"
                if supp_key not in self.sequences:
                    self.sequences[supp_key] = {}
                self.sequences[supp_key][f"{parent_year}-{parent_seq:06d}{suffix}"] = True

                case_number = self._format_case_number(parent_year, parent_seq, suffix)
                self._save_sequences()  # Persist updated sequence
                return case_number

            except (ValueError, IndexError) as e:
                raise ValueError(f"Error parsing parent case '{parent_case}': {e}")

        else:
            raise ValueError(f"Invalid report_type: {report_type}. Must be 'NEW' or 'SUPPLEMENT'")

    def generate_for_dataframe(
        self,
        df: pd.DataFrame,
        date_col: str = 'report_date',
        type_col: str = 'report_type',
        parent_col: str = None,
        output_col: str = 'ReportNumberNew'
    ) -> pd.DataFrame:
        """Generate case numbers for entire DataFrame.

        Args:
            df: Input DataFrame
            date_col: Column containing report dates
            type_col: Column containing report types ('NEW' or 'SUPPLEMENT')
            parent_col: Column containing parent case numbers (for supplements)
            output_col: Name of output column to create

        Returns:
            DataFrame with ReportNumberNew column added
        """
        df = df.copy()

        # Validate required columns
        if date_col not in df.columns:
            raise ValueError(f"Date column '{date_col}' not found in DataFrame")
        if type_col not in df.columns:
            raise ValueError(f"Type column '{type_col}' not found in DataFrame")

        # Convert date column to datetime
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

        # Generate case numbers
        case_numbers = []
        for idx, row in df.iterrows():
            report_date = row[date_col]
            report_type = row[type_col]
            parent_case = row[parent_col] if parent_col and parent_col in df.columns else None

            if pd.isna(report_date):
                case_numbers.append(None)
                continue

            try:
                case_num = self.generate_for_record(report_date, report_type, parent_case)
                case_numbers.append(case_num)
            except ValueError as e:
                print(f"Warning: Error generating case number for row {idx}: {e}")
                case_numbers.append(None)

        df[output_col] = case_numbers

        # Save updated sequences
        self._save_sequences()

        return df


def generate_case_numbers(
    df: pd.DataFrame,
    date_col: str = 'report_date',
    type_col: str = 'report_type',
    parent_col: str = None,
    output_col: str = 'ReportNumberNew',
    sequence_file: str = None
) -> pd.DataFrame:
    """Convenience function to generate case numbers for a DataFrame.

    Args:
        df: Input DataFrame
        date_col: Column containing report dates
        type_col: Column containing report types ('NEW' or 'SUPPLEMENT')
        parent_col: Column containing parent case numbers (for supplements)
        output_col: Name of output column to create
        sequence_file: Path to sequence tracker JSON file

    Returns:
        DataFrame with ReportNumberNew column added
    """
    generator = CaseNumberGenerator(sequence_file=sequence_file)
    return generator.generate_for_dataframe(df, date_col, type_col, parent_col, output_col)


# ── Unit Tests ──────────────────────────────────────────────────────────────

@pytest.fixture
def temp_sequence_file(tmp_path):
    """Provide a temporary sequence file for testing."""
    return tmp_path / "test_sequences.json"


@pytest.fixture
def generator(temp_sequence_file):
    """Provide a test case number generator."""
    return CaseNumberGenerator(sequence_file=str(temp_sequence_file))


def test_generate_new_case_number(generator):
    """Test generating new case numbers."""
    date1 = datetime(2025, 1, 15)
    case1 = generator.generate_for_record(date1, 'NEW')
    assert case1 == '25-000001'

    case2 = generator.generate_for_record(date1, 'NEW')
    assert case2 == '25-000002'


def test_generate_supplement_case_number(generator):
    """Test generating supplement case numbers."""
    date1 = datetime(2025, 1, 15)

    # Create parent case
    parent = generator.generate_for_record(date1, 'NEW')
    assert parent == '25-000001'

    # Create supplements
    supp1 = generator.generate_for_record(date1, 'SUPPLEMENT', parent_case=parent)
    assert supp1 == '25-000001A'

    supp2 = generator.generate_for_record(date1, 'SUPPLEMENT', parent_case=parent)
    assert supp2 == '25-000001B'


def test_year_rollover(generator):
    """Test sequence resets on year boundary."""
    date_2024 = datetime(2024, 12, 31)
    date_2025 = datetime(2025, 1, 1)

    case1 = generator.generate_for_record(date_2024, 'NEW')
    assert case1 == '24-000001'

    case2 = generator.generate_for_record(date_2025, 'NEW')
    assert case2 == '25-000001'  # Sequence resets for new year


def test_supplement_max_suffix(generator):
    """Test that supplements stop at Z suffix."""
    date1 = datetime(2025, 1, 15)
    parent = generator.generate_for_record(date1, 'NEW')

    # Generate 26 supplements (A-Z)
    for i in range(26):
        generator.generate_for_record(date1, 'SUPPLEMENT', parent_case=parent)

    # 27th supplement should raise error
    with pytest.raises(ValueError, match="Maximum supplements"):
        generator.generate_for_record(date1, 'SUPPLEMENT', parent_case=parent)


def test_dataframe_generation(generator):
    """Test generating case numbers for entire DataFrame."""
    df = pd.DataFrame({
        'report_date': [
            datetime(2025, 1, 1),
            datetime(2025, 1, 2),
            datetime(2025, 1, 3)
        ],
        'report_type': ['NEW', 'NEW', 'SUPPLEMENT'],
        'parent_case': [None, None, '25-000001']
    })

    result = generator.generate_for_dataframe(
        df,
        date_col='report_date',
        type_col='report_type',
        parent_col='parent_case'
    )

    assert 'ReportNumberNew' in result.columns
    assert result['ReportNumberNew'].iloc[0] == '25-000001'
    assert result['ReportNumberNew'].iloc[1] == '25-000002'
    assert result['ReportNumberNew'].iloc[2] == '25-000001A'


def test_invalid_report_type(generator):
    """Test that invalid report types raise errors."""
    date1 = datetime(2025, 1, 15)
    with pytest.raises(ValueError, match="Invalid report_type"):
        generator.generate_for_record(date1, 'INVALID')


def test_supplement_without_parent(generator):
    """Test that supplements require parent case."""
    date1 = datetime(2025, 1, 15)
    with pytest.raises(ValueError, match="require parent_case"):
        generator.generate_for_record(date1, 'SUPPLEMENT')


def test_sequence_persistence(temp_sequence_file):
    """Test that sequences persist across generator instances."""
    gen1 = CaseNumberGenerator(sequence_file=str(temp_sequence_file))
    date1 = datetime(2025, 1, 15)

    case1 = gen1.generate_for_record(date1, 'NEW')
    assert case1 == '25-000001'

    # Create new generator instance (should load saved sequences)
    gen2 = CaseNumberGenerator(sequence_file=str(temp_sequence_file))
    case2 = gen2.generate_for_record(date1, 'NEW')
    assert case2 == '25-000002'  # Should continue from where gen1 left off


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, '-v'])
