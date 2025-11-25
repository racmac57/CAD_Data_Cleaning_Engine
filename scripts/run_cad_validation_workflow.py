"""
Master CAD Validation and Revert Workflow

This script orchestrates the complete 3-step validation and revert process:
1. Generate field-by-field diff report
2. Create CADNotes-only mismatch audit
3. Revert changes using diff report

Author: Claude Code
Date: 2025-11-22
"""

import sys
import os
from datetime import datetime


def check_file_exists(path, description):
    """Check if a file exists and print status."""
    if os.path.exists(path):
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"  [OK] {description}")
        print(f"       Path: {path}")
        print(f"       Size: {size_mb:.2f} MB")
        return True
    else:
        print(f"  [MISSING] {description}")
        print(f"            Path: {path}")
        return False


def main():
    """Main workflow execution."""
    print("\n" + "="*70)
    print(" CAD VALIDATION AND REVERT WORKFLOW")
    print("="*70)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis workflow will:")
    print("  Step 1: Compare BEFORE/AFTER files and generate diff report")
    print("  Step 2: Create CADNotes-only mismatch audit")
    print("  Step 3: Revert incorrect changes using diff report")
    print("="*70)

    # Define file paths
    paths = {
        'before': 'test/2025_11_17_CAD_Cleanup_PreManual.csv',
        'after': 'test/2025_11_17_CAD_Cleaned_FullAddress2.csv',
        'diff_report': 'test/CAD_Field_Diff_Report.csv',
        'cadnotes_audit': 'test/CADNotes_Mismatches.csv',
        'reverted': 'test/2025_11_17_CAD_Reverted_From_Diff.csv',
        'revert_log': 'test/CAD_Revert_Log.txt'
    }

    # Check prerequisites
    print("\n" + "-"*70)
    print("PREREQUISITE CHECK")
    print("-"*70)

    before_exists = check_file_exists(paths['before'], "BEFORE file (original)")
    after_exists = check_file_exists(paths['after'], "AFTER file (cleaned)")

    print()

    if not before_exists:
        print("[ERROR] BEFORE file is missing!")
        print("\nThe BEFORE file should have been created by convert_test_files.py")
        print("Run that script first to create the test files.")
        sys.exit(1)

    if not after_exists:
        print("[INFO] AFTER file not found yet")
        print("\nThe AFTER file needs to be created by your FullAddress2 cleaning process.")
        print("Once you have cleaned the FullAddress2 field, save the result as:")
        print(f"  {paths['after']}")
        print("\nThen run this workflow again to:")
        print("  1. Compare the changes")
        print("  2. Detect any CADNotes drift")
        print("  3. Revert unintended changes")
        print("\n" + "="*70)
        print("WORKFLOW STATUS: Waiting for AFTER file")
        print("="*70)
        sys.exit(0)

    # All files exist - run the workflow
    print("[OK] All prerequisite files found")
    print("\n" + "-"*70)

    # Ask for confirmation
    response = input("\nProceed with validation workflow? (y/n): ").strip().lower()
    if response != 'y':
        print("\nWorkflow cancelled by user")
        sys.exit(0)

    print("\n" + "="*70)

    # Step 1 & 2: Run validation and diff generation
    print("\nSTEP 1 & 2: VALIDATION AND DIFF GENERATION")
    print("="*70)

    try:
        print("\nRunning: validate_cad_field_changes.py")
        print("-"*70)

        # Import and run validation
        sys.path.insert(0, 'scripts')
        from validate_cad_field_changes import CADFieldValidator

        validator = CADFieldValidator()

        # Generate diff report
        diff_df, stats = validator.compare_files(paths['before'], paths['after'])

        if len(diff_df) > 0:
            diff_df.to_csv(paths['diff_report'], index=False)
            print(f"\n[OK] Diff report saved: {paths['diff_report']}")
        else:
            print(f"\n[INFO] No differences found - files are identical")

        # Generate CADNotes audit
        cadnotes_df = validator.create_cadnotes_audit(paths['before'], paths['after'])

        if len(cadnotes_df) > 0:
            cadnotes_df.to_csv(paths['cadnotes_audit'], index=False)
            print(f"[OK] CADNotes audit saved: {paths['cadnotes_audit']}")
        else:
            print(f"[INFO] No CADNotes mismatches found")

        # Print summary
        validator.print_summary()

        # Check for CADNotes issues
        if stats.get('cadnotes_mismatches', 0) > 0:
            print("\n" + "!"*70)
            print("WARNING: CADNotes mismatches detected!")
            print("!"*70)
            print(f"\n{stats['cadnotes_mismatches']:,} CADNotes records have changed.")
            print("This may indicate data alignment issues.")
            print(f"\nReview: {paths['cadnotes_audit']}")
            print("\nYou should investigate these mismatches before proceeding to Step 3.")

            response = input("\nContinue to Step 3 (revert)? (y/n): ").strip().lower()
            if response != 'y':
                print("\nWorkflow stopped. Review the CADNotes audit and fix issues.")
                sys.exit(0)

    except Exception as e:
        print(f"\n[ERROR] Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 3: Revert changes if requested
    print("\n\n" + "="*70)
    print("STEP 3: REVERT CHANGES")
    print("="*70)

    if stats['total_mismatches'] == 0:
        print("\n[INFO] No changes to revert - files are identical")
        print("\n" + "="*70)
        print("WORKFLOW COMPLETE")
        print("="*70)
        sys.exit(0)

    print(f"\nFound {stats['total_mismatches']:,} field-level changes")
    print("\nThis step will revert the AFTER file back to original values")
    print("using the diff report.")

    response = input("\nProceed with revert? (y/n): ").strip().lower()
    if response != 'y':
        print("\nRevert cancelled - diff reports have been saved for review")
        sys.exit(0)

    try:
        print("\nRunning: revert_cad_using_diff.py")
        print("-"*70)

        # Import and run revert
        from revert_cad_using_diff import CADFieldReverter

        reverter = CADFieldReverter()

        # Execute revert
        df_reverted = reverter.revert_changes(
            paths['diff_report'],
            paths['after'],
            paths['before'],
            paths['reverted']
        )

        if df_reverted is not None:
            # Print summary
            reverter.print_revert_summary()

            # Save log
            reverter.save_revert_log(paths['revert_log'])

            # Verify
            print("\nVerifying revert...")
            verification_passed = reverter.verify_revert(
                paths['reverted'],
                paths['before'],
                paths['diff_report']
            )

            if verification_passed:
                print("\n" + "="*70)
                print("WORKFLOW COMPLETE - SUCCESS")
                print("="*70)
                print(f"\nReverted file: {paths['reverted']}")
                print(f"Revert log:    {paths['revert_log']}")
            else:
                print("\n" + "="*70)
                print("WORKFLOW COMPLETE - WITH WARNINGS")
                print("="*70)
                print("\nVerification found issues. Review the output carefully.")
        else:
            print("\n[INFO] No changes needed to be reverted")

    except Exception as e:
        print(f"\n[ERROR] Revert failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
