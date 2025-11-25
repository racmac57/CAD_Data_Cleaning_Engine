"""
CAD Field Revert Script Using Diff Report

This script uses a field-by-field diff report to revert specific fields
back to their original values, ensuring data integrity.

Author: Claude Code
Date: 2025-11-22
"""

import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict


class CADFieldReverter:
    """Reverts CAD fields using a diff report."""

    def __init__(self):
        self.revert_stats = {
            'total_cases_touched': 0,
            'total_fields_reverted': 0,
            'field_revert_counts': defaultdict(int),
            'errors': []
        }

    def revert_changes(self, diff_path, incorrect_path, original_path, output_path):
        """
        Revert fields in the incorrect file using the diff report.

        Args:
            diff_path: Path to CAD_Field_Diff_Report.csv
            incorrect_path: Path to the file with incorrect values
            original_path: Path to the original file (for verification)
            output_path: Path to save the reverted file

        Returns:
            DataFrame with reverted values
        """
        print(f"\n{'='*60}")
        print("CAD Field Revert Process - Step 3")
        print(f"{'='*60}\n")

        # Load diff report
        print(f"Loading diff report: {diff_path}")
        diff_df = pd.read_csv(diff_path)
        print(f"  Diff records: {len(diff_df):,}")

        if len(diff_df) == 0:
            print("\n[INFO] Diff report is empty - no changes to revert")
            return None

        # Verify diff report structure
        required_cols = ['ReportNumberNew', 'Field_Name', 'Old_Value', 'New_Value', 'match']
        missing_cols = [col for col in required_cols if col not in diff_df.columns]
        if missing_cols:
            raise ValueError(f"Diff report missing columns: {missing_cols}")

        # Filter to only mismatches
        mismatches = diff_df[diff_df['match'] == False].copy()
        print(f"  Mismatches to revert: {len(mismatches):,}")

        if len(mismatches) == 0:
            print("\n[INFO] No mismatches found - all fields match")
            return None

        # Load incorrect file
        print(f"\nLoading file to correct: {incorrect_path}")
        df_incorrect = pd.read_csv(incorrect_path, low_memory=False)
        print(f"  Records: {len(df_incorrect):,}")
        print(f"  Columns: {len(df_incorrect.columns)}")

        # Verify ReportNumberNew exists
        if 'ReportNumberNew' not in df_incorrect.columns:
            raise ValueError("File missing 'ReportNumberNew' column")

        # Create a working copy
        df_reverted = df_incorrect.copy()

        # Group mismatches by ReportNumberNew
        print(f"\nReverting fields...")
        cases_modified = set()

        for report_num, group in mismatches.groupby('ReportNumberNew'):
            # Find row in df_reverted
            mask = df_reverted['ReportNumberNew'] == report_num

            if not mask.any():
                self.revert_stats['errors'].append(
                    f"ReportNumberNew {report_num} not found in file"
                )
                continue

            row_idx = df_reverted[mask].index[0]
            cases_modified.add(report_num)

            # Revert each field for this case
            for _, diff_row in group.iterrows():
                field_name = diff_row['Field_Name']
                old_value = diff_row['Old_Value']

                # Check if field exists
                if field_name not in df_reverted.columns:
                    self.revert_stats['errors'].append(
                        f"Field '{field_name}' not found in file for {report_num}"
                    )
                    continue

                # Revert the value
                # Handle empty strings as NaN
                if old_value == '' or pd.isna(old_value):
                    df_reverted.at[row_idx, field_name] = np.nan
                else:
                    df_reverted.at[row_idx, field_name] = old_value

                # Update stats
                self.revert_stats['total_fields_reverted'] += 1
                self.revert_stats['field_revert_counts'][field_name] += 1

        self.revert_stats['total_cases_touched'] = len(cases_modified)

        # Progress update
        print(f"  Cases modified: {len(cases_modified):,}")
        print(f"  Fields reverted: {self.revert_stats['total_fields_reverted']:,}")

        # Save reverted file
        print(f"\nSaving reverted file to: {output_path}")
        df_reverted.to_csv(output_path, index=False)

        file_size_mb = df_reverted.memory_usage(deep=True).sum() / (1024 * 1024)
        print(f"  Records: {len(df_reverted):,}")
        print(f"  Estimated size: {file_size_mb:.2f} MB")

        return df_reverted

    def verify_revert(self, reverted_path, original_path, diff_path):
        """
        Verify that the revert process was successful by comparing
        the reverted file to the original file.

        Args:
            reverted_path: Path to the reverted file
            original_path: Path to the original file
            diff_path: Path to the diff report

        Returns:
            Boolean indicating if verification passed
        """
        print(f"\n{'='*60}")
        print("Verification: Comparing Reverted to Original")
        print(f"{'='*60}\n")

        # Load diff to get fields that should have been reverted
        diff_df = pd.read_csv(diff_path)
        mismatches = diff_df[diff_df['match'] == False]

        if len(mismatches) == 0:
            print("[INFO] No mismatches to verify")
            return True

        # Get unique fields from diff
        reverted_fields = mismatches['Field_Name'].unique()
        print(f"Fields that were reverted: {list(reverted_fields)}")

        # Load files for comparison
        print(f"\nLoading reverted file: {reverted_path}")
        df_reverted = pd.read_csv(reverted_path, low_memory=False)

        print(f"Loading original file: {original_path}")
        df_original = pd.read_csv(original_path, low_memory=False)

        # Merge on ReportNumberNew
        df_merged = df_reverted.merge(
            df_original,
            on='ReportNumberNew',
            how='inner',
            suffixes=('_REVERTED', '_ORIGINAL')
        )

        print(f"\nRecords compared: {len(df_merged):,}")

        # Check each reverted field
        verification_passed = True
        issues_found = 0

        for field in reverted_fields:
            if field not in df_reverted.columns or field not in df_original.columns:
                print(f"  [WARNING] Field '{field}' not found in one or both files")
                continue

            reverted_col = f"{field}_REVERTED"
            original_col = f"{field}_ORIGINAL"

            # Normalize for comparison
            reverted_norm = df_merged[reverted_col].fillna('').astype(str).str.strip()
            original_norm = df_merged[original_col].fillna('').astype(str).str.strip()

            # Find differences
            mask = reverted_norm != original_norm
            diff_count = mask.sum()

            if diff_count > 0:
                print(f"  [ERROR] {field}: {diff_count:,} records still differ from original")
                verification_passed = False
                issues_found += diff_count
            else:
                print(f"  [OK] {field}: All values match original")

        print(f"\n{'='*60}")
        if verification_passed:
            print("[OK] Verification PASSED - All reverted fields match original")
        else:
            print(f"[ERROR] Verification FAILED - {issues_found:,} issues found")
        print(f"{'='*60}\n")

        return verification_passed

    def print_revert_summary(self):
        """Print revert operation summary."""
        print(f"\n{'='*60}")
        print("REVERT SUMMARY")
        print(f"{'='*60}")
        print(f"Total cases touched: {self.revert_stats['total_cases_touched']:,}")
        print(f"Total fields reverted: {self.revert_stats['total_fields_reverted']:,}")

        if self.revert_stats['field_revert_counts']:
            print(f"\nField-wise revert counts:")
            for field, count in sorted(
                self.revert_stats['field_revert_counts'].items(),
                key=lambda x: -x[1]
            ):
                print(f"  {field:.<30} {count:>10,}")

        if self.revert_stats['errors']:
            print(f"\n[WARNING] Errors encountered: {len(self.revert_stats['errors'])}")
            for error in self.revert_stats['errors'][:10]:  # Show first 10
                print(f"  - {error}")
            if len(self.revert_stats['errors']) > 10:
                print(f"  ... and {len(self.revert_stats['errors']) - 10} more")

        print(f"{'='*60}\n")

    def save_revert_log(self, log_path):
        """Save detailed revert log."""
        log_lines = [
            "="*60,
            "CAD Field Revert Log",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "="*60,
            "",
            f"Total cases touched: {self.revert_stats['total_cases_touched']:,}",
            f"Total fields reverted: {self.revert_stats['total_fields_reverted']:,}",
            "",
            "Field-wise revert counts:",
        ]

        for field, count in sorted(
            self.revert_stats['field_revert_counts'].items(),
            key=lambda x: -x[1]
        ):
            log_lines.append(f"  {field}: {count:,}")

        if self.revert_stats['errors']:
            log_lines.append("")
            log_lines.append(f"Errors encountered: {len(self.revert_stats['errors'])}")
            for error in self.revert_stats['errors']:
                log_lines.append(f"  - {error}")

        log_lines.append("")
        log_lines.append("="*60)

        with open(log_path, 'w') as f:
            f.write('\n'.join(log_lines))

        print(f"Revert log saved to: {log_path}")


def main():
    """Main execution function."""
    import sys
    import os

    # Define paths
    diff_path = "test/CAD_Field_Diff_Report.csv"
    incorrect_path = "test/2025_11_17_CAD_Cleaned_FullAddress2.csv"
    original_path = "test/2025_11_17_CAD_Cleanup_PreManual.csv"
    output_path = "test/2025_11_17_CAD_Reverted_From_Diff.csv"
    log_path = "test/CAD_Revert_Log.txt"

    print("\n" + "="*60)
    print("CAD Field Revert - Step 3")
    print("="*60)
    print(f"\nDiff report:      {diff_path}")
    print(f"File to correct:  {incorrect_path}")
    print(f"Original file:    {original_path}")
    print(f"Output file:      {output_path}")
    print(f"Log file:         {log_path}")
    print("="*60)

    # Check if required files exist
    missing_files = []
    for path, name in [
        (diff_path, "Diff report"),
        (incorrect_path, "File to correct"),
        (original_path, "Original file")
    ]:
        if not os.path.exists(path):
            missing_files.append((name, path))

    if missing_files:
        print("\n[ERROR] Required files not found:")
        for name, path in missing_files:
            print(f"  - {name}: {path}")
        print("\nPlease ensure you have:")
        print("  1. Run validate_cad_field_changes.py first to generate the diff report")
        print("  2. The cleaned FullAddress2 file exists")
        print("  3. The original pre-manual file exists")
        sys.exit(1)

    # Create reverter
    reverter = CADFieldReverter()

    # Execute revert
    try:
        df_reverted = reverter.revert_changes(
            diff_path,
            incorrect_path,
            original_path,
            output_path
        )

        if df_reverted is None:
            print("\n[INFO] No changes to revert - exiting")
            sys.exit(0)

    except Exception as e:
        print(f"\n[ERROR] Revert process failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Print summary
    reverter.print_revert_summary()

    # Save log
    reverter.save_revert_log(log_path)

    # Verify revert
    print("\nVerifying revert process...")
    try:
        verification_passed = reverter.verify_revert(
            output_path,
            original_path,
            diff_path
        )

        if verification_passed:
            print("\n[OK] Revert process completed successfully!")
            print(f"Reverted file saved to: {output_path}")
        else:
            print("\n[WARNING] Verification found issues - review the output carefully")

    except Exception as e:
        print(f"\n[WARNING] Verification failed: {e}")

    print(f"\nRevert complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
