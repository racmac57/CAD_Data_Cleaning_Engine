"""
CAD Field-by-Field Validation and Diff Report Generator

This script compares two CAD CSV files field-by-field to detect changes,
with special focus on ensuring CADNotes alignment.

Author: Claude Code
Date: 2025-11-22
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
from datetime import datetime


class CADFieldValidator:
    """Validates and compares CAD fields across two versions."""

    def __init__(self):
        self.fields_to_compare = [
            'Incident',
            'Disposition',
            'How Reported',
            'FullAddress2',
            'Response Type',
            'CADNotes'
        ]
        self.stats = {
            'total_records': 0,
            'records_compared': 0,
            'total_mismatches': 0,
            'field_changes': {},
            'cadnotes_mismatches': 0
        }

    def normalize_text(self, text):
        """Normalize text for comparison."""
        if pd.isna(text):
            return ''

        # Convert to string
        text = str(text)

        # Remove leading apostrophe (Excel guard)
        if text.startswith("'"):
            text = text[1:]

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        # Normalize common punctuation variations
        text = text.replace('\r\n', ' ')
        text = text.replace('\n', ' ')
        text = text.replace('\r', ' ')

        # Additional normalization for CADNotes
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)

        return text

    def compare_files(self, before_path, after_path):
        """
        Compare two CAD CSV files field-by-field.

        Returns:
            diff_df: DataFrame with field-level differences
            summary: Dictionary with comparison statistics
        """
        print(f"\n{'='*60}")
        print("CAD Field-by-Field Validation")
        print(f"{'='*60}\n")

        # Load files
        print(f"Loading BEFORE file: {before_path}")
        df_before = pd.read_csv(before_path, low_memory=False)
        print(f"  Records: {len(df_before):,}")

        print(f"\nLoading AFTER file: {after_path}")
        df_after = pd.read_csv(after_path, low_memory=False)
        print(f"  Records: {len(df_after):,}")

        # Check for ReportNumberNew
        if 'ReportNumberNew' not in df_before.columns:
            raise ValueError("BEFORE file missing 'ReportNumberNew' column")
        if 'ReportNumberNew' not in df_after.columns:
            raise ValueError("AFTER file missing 'ReportNumberNew' column")

        # Merge on ReportNumberNew
        print(f"\nMerging on ReportNumberNew...")
        df_merged = df_before.merge(
            df_after,
            on='ReportNumberNew',
            how='inner',
            suffixes=('_BEFORE', '_AFTER')
        )

        self.stats['total_records'] = len(df_before)
        self.stats['records_compared'] = len(df_merged)

        print(f"  Records in both files: {len(df_merged):,}")

        if len(df_merged) == 0:
            print("\n[WARNING] No matching records found!")
            return pd.DataFrame(), self.stats

        # Compare fields
        print(f"\nComparing fields...")
        diff_records = []

        for field in self.fields_to_compare:
            before_col = f"{field}_BEFORE"
            after_col = f"{field}_AFTER"

            # Check if columns exist
            if before_col not in df_merged.columns or after_col not in df_merged.columns:
                print(f"  [WARNING] Field '{field}' not found in one or both files")
                continue

            print(f"  Comparing: {field}")

            # Normalize values
            before_normalized = df_merged[before_col].apply(self.normalize_text)
            after_normalized = df_merged[after_col].apply(self.normalize_text)

            # Find differences
            mask = before_normalized != after_normalized
            num_changes = mask.sum()

            print(f"    Changes detected: {num_changes:,}")

            if num_changes > 0:
                self.stats['field_changes'][field] = num_changes
                self.stats['total_mismatches'] += num_changes

                if field == 'CADNotes':
                    self.stats['cadnotes_mismatches'] = num_changes

                # Create diff records for this field
                changed_rows = df_merged[mask].copy()

                for idx, row in changed_rows.iterrows():
                    diff_records.append({
                        'ReportNumberNew': row['ReportNumberNew'],
                        'Field_Name': field,
                        'Old_Value': self.normalize_text(row[before_col]),
                        'New_Value': self.normalize_text(row[after_col]),
                        'match': False
                    })

        # Create diff DataFrame
        if diff_records:
            diff_df = pd.DataFrame(diff_records)
            print(f"\n  Total field-level changes: {len(diff_df):,}")
        else:
            diff_df = pd.DataFrame(columns=[
                'ReportNumberNew', 'Field_Name', 'Old_Value', 'New_Value', 'match'
            ])
            print(f"\n  No changes detected!")

        return diff_df, self.stats

    def create_cadnotes_audit(self, before_path, after_path):
        """
        Create CADNotes-only mismatch audit.

        Returns:
            DataFrame with CADNotes mismatches only
        """
        print(f"\n{'='*60}")
        print("CADNotes-Only Mismatch Audit")
        print(f"{'='*60}\n")

        # Load files
        print(f"Loading files...")
        df_before = pd.read_csv(before_path, low_memory=False)
        df_after = pd.read_csv(after_path, low_memory=False)

        # Check for CADNotes
        if 'CADNotes' not in df_before.columns or 'CADNotes' not in df_after.columns:
            print("[WARNING] CADNotes column not found in one or both files")
            return pd.DataFrame()

        # Merge on ReportNumberNew
        df_merged = df_before[['ReportNumberNew', 'CADNotes']].merge(
            df_after[['ReportNumberNew', 'CADNotes']],
            on='ReportNumberNew',
            how='inner',
            suffixes=('_BEFORE', '_AFTER')
        )

        print(f"  Records compared: {len(df_merged):,}")

        # Normalize and compare
        before_normalized = df_merged['CADNotes_BEFORE'].apply(self.normalize_text)
        after_normalized = df_merged['CADNotes_AFTER'].apply(self.normalize_text)

        # Find mismatches
        mask = before_normalized != after_normalized
        mismatches = df_merged[mask].copy()

        print(f"  CADNotes mismatches: {len(mismatches):,}")

        if len(mismatches) > 0:
            # Rename columns and add match flag
            mismatches = mismatches.rename(columns={
                'CADNotes_BEFORE': 'CADNotes_BEFORE',
                'CADNotes_AFTER': 'CADNotes_AFTER'
            })
            mismatches['match'] = False

            # Reorder columns
            mismatches = mismatches[['ReportNumberNew', 'CADNotes_BEFORE', 'CADNotes_AFTER', 'match']]

        return mismatches

    def print_summary(self):
        """Print comparison summary."""
        print(f"\n{'='*60}")
        print("COMPARISON SUMMARY")
        print(f"{'='*60}")
        print(f"Total records in BEFORE file: {self.stats['total_records']:,}")
        print(f"Records compared: {self.stats['records_compared']:,}")
        print(f"Total field-level changes: {self.stats['total_mismatches']:,}")

        if self.stats['field_changes']:
            print(f"\nChanges by field:")
            for field, count in sorted(self.stats['field_changes'].items(), key=lambda x: -x[1]):
                print(f"  {field:.<30} {count:>10,}")

        if self.stats['cadnotes_mismatches'] > 0:
            print(f"\n[WARNING] CADNotes mismatches detected: {self.stats['cadnotes_mismatches']:,}")
            print("  This may indicate data alignment issues!")

        print(f"{'='*60}\n")


def main():
    """Main execution function."""
    import sys
    import os

    # Define paths
    before_path = "test/2025_11_17_CAD_Cleanup_PreManual.csv"
    after_path = "test/2025_11_17_CAD_Cleaned_FullAddress2.csv"
    diff_output = "test/CAD_Field_Diff_Report.csv"
    cadnotes_output = "test/CADNotes_Mismatches.csv"

    print("\n" + "="*60)
    print("CAD Field Validation - Step 1 & 2")
    print("="*60)
    print(f"\nBEFORE: {before_path}")
    print(f"AFTER:  {after_path}")
    print(f"\nDiff output:      {diff_output}")
    print(f"CADNotes output:  {cadnotes_output}")
    print("="*60)

    # Check if files exist
    if not os.path.exists(before_path):
        print(f"\n[ERROR] BEFORE file not found: {before_path}")
        sys.exit(1)

    if not os.path.exists(after_path):
        print(f"\n[ERROR] AFTER file not found: {after_path}")
        print("\nThe AFTER file needs to be created first.")
        print("Once you have the cleaned FullAddress2 file, place it at:")
        print(f"  {after_path}")
        print("\nThen run this script again.")
        sys.exit(1)

    # Create validator
    validator = CADFieldValidator()

    # Step 1: Generate field-by-field diff
    try:
        diff_df, stats = validator.compare_files(before_path, after_path)

        if len(diff_df) > 0:
            print(f"\nWriting diff report to: {diff_output}")
            diff_df.to_csv(diff_output, index=False)
            print(f"  Records written: {len(diff_df):,}")
        else:
            print(f"\nNo changes detected - no diff file created.")

    except Exception as e:
        print(f"\n[ERROR] Failed to generate diff report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 2: Generate CADNotes-only audit
    try:
        cadnotes_df = validator.create_cadnotes_audit(before_path, after_path)

        if len(cadnotes_df) > 0:
            print(f"\nWriting CADNotes audit to: {cadnotes_output}")
            cadnotes_df.to_csv(cadnotes_output, index=False)
            print(f"  Mismatch records: {len(cadnotes_df):,}")
        else:
            print(f"\nNo CADNotes mismatches - no audit file created.")

    except Exception as e:
        print(f"\n[WARNING] Failed to generate CADNotes audit: {e}")

    # Print summary
    validator.print_summary()

    # Final status
    if stats['total_mismatches'] == 0:
        print("[OK] Files are identical - no changes detected")
    elif stats.get('cadnotes_mismatches', 0) > 0:
        print("[WARNING] CADNotes mismatches detected - review audit file!")
    else:
        print(f"[OK] {stats['total_mismatches']:,} field changes detected and logged")

    print(f"\nValidation complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
