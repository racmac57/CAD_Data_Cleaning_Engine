"""
CAD Data Correction Framework - Main Entry Point

Production-safe correction system for 700K+ emergency dispatch records.

Usage:
    python main.py --config config/config.yml
    python main.py --config config/config.yml --validate-only
    python main.py --config config/config.yml --test-mode
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import traceback

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from processors.cad_data_processor import CADDataProcessor
from validators.validation_harness import ValidationHarness
from validators.validate_full_pipeline import PipelineValidator
from utils.logger import setup_logger


def run_validation_harness(config_path: str) -> bool:
    """
    Run pre-processing validation checks.

    Args:
        config_path: Path to configuration file

    Returns:
        True if all validations passed
    """
    print("\n" + "=" * 80)
    print("STEP 1: PRE-PROCESSING VALIDATION")
    print("=" * 80)

    harness = ValidationHarness(config_path)
    return harness.run_all_validations()


def run_correction_pipeline(config_path: str, test_mode: bool = False) -> bool:
    """
    Run the main correction pipeline.

    Args:
        config_path: Path to configuration file
        test_mode: If True, process only a subset of data

    Returns:
        True if pipeline completed successfully
    """
    print("\n" + "=" * 80)
    print("STEP 2: RUNNING CORRECTION PIPELINE")
    print("=" * 80)

    try:
        # Initialize processor
        processor = CADDataProcessor(config_path)

        # Load data
        processor.load_data()

        # If test mode, sample the data
        if test_mode:
            sample_size = processor.config['development']['test_sample_size']
            random_seed = processor.config['development']['test_random_seed']

            print(f"\nTEST MODE: Processing {sample_size:,} random records")
            processor.df = processor.df.sample(n=min(sample_size, len(processor.df)), random_state=random_seed)

        # Run all corrections
        processor.run_all_corrections()

        # Export corrected data
        processor.export_corrected_data()

        # Print summary
        summary = processor.get_processing_summary()
        print("\n" + "-" * 80)
        print("PROCESSING COMPLETE")
        print("-" * 80)
        print(f"Records processed: {summary['processing_stats']['records_output']:,}")
        print(f"Corrections applied: {summary['processing_stats']['corrections_applied']:,}")
        print(f"Average quality score: {summary['quality_metrics']['average_quality_score']:.1f}/100")
        print(f"Duplicates flagged: {summary['processing_stats']['duplicates_flagged']:,}")
        print(f"Manual review flagged: {summary['processing_stats']['manual_review_flagged']:,}")
        print(f"Audit trail entries: {summary['audit_trail_entries']:,}")

        return True

    except Exception as e:
        print(f"\nERROR: Pipeline failed with exception:")
        print(f"  {type(e).__name__}: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


def run_post_validation(config_path: str) -> bool:
    """
    Run post-processing validation checks.

    Args:
        config_path: Path to configuration file

    Returns:
        True if all validations passed
    """
    print("\n" + "=" * 80)
    print("STEP 3: POST-PROCESSING VALIDATION")
    print("=" * 80)

    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    input_file = config['paths']['input_file']
    output_file = config['paths']['output_file']
    audit_file = config['paths']['audit_file']

    validator = PipelineValidator(input_file, output_file, audit_file, config_path)
    return validator.run_all_validations()


def main():
    """Main entry point for CAD Data Correction Framework."""
    parser = argparse.ArgumentParser(
        description="CAD Data Correction Framework - Production-safe correction system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline with default config
  python main.py

  # Run with custom config
  python main.py --config config/custom_config.yml

  # Run validation checks only (no processing)
  python main.py --validate-only

  # Run in test mode (process subset of data)
  python main.py --test-mode

  # Skip pre-validation (not recommended)
  python main.py --skip-validation

  # Skip post-validation
  python main.py --skip-post-validation

For more information, see README.md
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yml',
        help='Path to configuration file (default: config/config.yml)'
    )

    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Run validation checks only without processing data'
    )

    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run in test mode (process subset of data)'
    )

    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip pre-processing validation (NOT RECOMMENDED)'
    )

    parser.add_argument(
        '--skip-post-validation',
        action='store_true',
        help='Skip post-processing validation'
    )

    args = parser.parse_args()

    # Print header
    print("\n" + "=" * 80)
    print("CAD DATA CORRECTION FRAMEWORK")
    print("=" * 80)
    print(f"Version: 1.0.0")
    print(f"Configuration: {args.config}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'TEST' if args.test_mode else 'PRODUCTION'}")
    print("=" * 80)

    # Verify config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"\nERROR: Configuration file not found: {config_path}")
        print("Please create a configuration file or specify a valid path with --config")
        return 1

    # Track overall success
    success = True

    # Step 1: Pre-processing validation
    if not args.skip_validation:
        validation_success = run_validation_harness(str(config_path))

        if not validation_success:
            print("\n" + "!" * 80)
            print("PRE-VALIDATION FAILED")
            print("Please fix the errors above before running the pipeline.")
            print("To skip validation (NOT RECOMMENDED), use --skip-validation")
            print("!" * 80)
            return 1

        print("\n✓ Pre-validation passed")
    else:
        print("\n⚠ SKIPPING PRE-VALIDATION (not recommended)")

    # Step 2: Run correction pipeline (unless validate-only mode)
    if not args.validate_only:
        pipeline_success = run_correction_pipeline(str(config_path), test_mode=args.test_mode)

        if not pipeline_success:
            print("\n" + "!" * 80)
            print("PIPELINE EXECUTION FAILED")
            print("Check the logs above for details.")
            print("!" * 80)
            return 1

        print("\n✓ Pipeline execution completed")

        # Step 3: Post-processing validation
        if not args.skip_post_validation:
            post_validation_success = run_post_validation(str(config_path))

            if not post_validation_success:
                print("\n" + "!" * 80)
                print("POST-VALIDATION FAILED")
                print("Data was processed but validation checks failed.")
                print("Review the validation results above.")
                print("!" * 80)
                return 1

            print("\n✓ Post-validation passed")
        else:
            print("\n⚠ SKIPPING POST-VALIDATION")

    else:
        print("\n✓ Validation-only mode complete")

    # Success summary
    print("\n" + "=" * 80)
    print("✓ ALL STEPS COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not args.validate_only:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        print(f"\nOutput Files:")
        print(f"  Corrected Data: {config['paths']['output_file']}")
        print(f"  Audit Trail: {config['paths']['audit_file']}")
        print(f"  Log File: {config['paths']['log_file']}")

        if config['export']['export_flagged_records']:
            print(f"  Manual Review: {config['paths']['manual_review_file']}")

    print("\n" + "=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
