"""
Basic Usage Examples for CAD Data Correction Framework

This file demonstrates common usage patterns for the framework.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from processors.cad_data_processor import CADDataProcessor
from validators.validation_harness import ValidationHarness
from validators.validate_full_pipeline import PipelineValidator


def example_1_basic_pipeline():
    """Example 1: Run complete pipeline with default config."""
    print("=" * 80)
    print("Example 1: Basic Pipeline Execution")
    print("=" * 80)

    # Initialize processor
    processor = CADDataProcessor('config/config.yml')

    # Load data
    processor.load_data()

    # Run all corrections
    processor.run_all_corrections()

    # Export results
    processor.export_corrected_data()

    # Get summary
    summary = processor.get_processing_summary()
    print(f"\nProcessing Summary:")
    print(f"  Records: {summary['processing_stats']['records_output']:,}")
    print(f"  Corrections: {summary['processing_stats']['corrections_applied']:,}")
    print(f"  Quality Score: {summary['quality_metrics']['average_quality_score']:.1f}/100")


def example_2_validation_only():
    """Example 2: Run validation checks without processing."""
    print("\n" + "=" * 80)
    print("Example 2: Validation Only")
    print("=" * 80)

    # Run pre-validation
    harness = ValidationHarness('config/config.yml')
    result = harness.run_all_validations()

    if result:
        print("\n✓ All validations passed - ready to process")
    else:
        print("\n✗ Validation failed - fix errors before processing")


def example_3_custom_corrections():
    """Example 3: Apply specific corrections only."""
    print("\n" + "=" * 80)
    print("Example 3: Custom Corrections")
    print("=" * 80)

    processor = CADDataProcessor('config/config.yml')
    processor.load_data()

    # Validate schema
    processor.validate_schema()

    # Apply only address corrections
    processor._apply_address_corrections()

    # Calculate quality scores
    processor.calculate_quality_scores()

    # Flag low quality records for review
    processor.flag_for_manual_review()

    print(f"\nFlagged {processor.processing_stats['manual_review_flagged']:,} records for manual review")


def example_4_manual_review_query():
    """Example 4: Flag records with custom criteria."""
    print("\n" + "=" * 80)
    print("Example 4: Custom Manual Review Criteria")
    print("=" * 80)

    processor = CADDataProcessor('config/config.yml')
    processor.load_data()

    # Flag records with unknown addresses OR low quality scores
    processor.flag_for_manual_review(
        "FullAddress2.str.contains('UNKNOWN', case=False, na=False) | (quality_score < 30)"
    )

    # Export flagged records
    processor._export_flagged_records()

    print(f"\nFlagged {processor.processing_stats['manual_review_flagged']:,} records")


def example_5_post_validation():
    """Example 5: Validate pipeline output."""
    print("\n" + "=" * 80)
    print("Example 5: Post-Processing Validation")
    print("=" * 80)

    validator = PipelineValidator(
        input_file='data/input/CAD_ESRI_Final_20251117_v3.xlsx',
        output_file='data/output/CAD_CLEANED.xlsx',
        audit_file='data/audit/audit_log.csv',
        config_path='config/config.yml'
    )

    result = validator.run_all_validations()

    if result:
        print("\n✓ Pipeline output validated successfully")
    else:
        print("\n✗ Pipeline validation failed")


def example_6_batch_processing():
    """Example 6: Process data in chunks for large datasets."""
    print("\n" + "=" * 80)
    print("Example 6: Batch Processing")
    print("=" * 80)

    processor = CADDataProcessor('config/config.yml')
    processor.load_data()

    # Process in chunks of 10,000 records
    chunk_size = 10000
    total_records = len(processor.df)

    print(f"Processing {total_records:,} records in chunks of {chunk_size:,}")

    for i in range(0, total_records, chunk_size):
        chunk_end = min(i + chunk_size, total_records)
        print(f"  Processing records {i:,} to {chunk_end:,}...")

        # Process chunk (simplified - in production you'd process each chunk separately)
        chunk_df = processor.df.iloc[i:chunk_end].copy()

        # Apply corrections to chunk
        # ... (chunk processing logic)

    print("✓ Batch processing complete")


def example_7_audit_trail_analysis():
    """Example 7: Analyze audit trail after processing."""
    print("\n" + "=" * 80)
    print("Example 7: Audit Trail Analysis")
    print("=" * 80)

    import pandas as pd

    # Load audit trail
    audit_df = pd.read_csv('data/audit/audit_log.csv', encoding='utf-8-sig')

    print(f"Total corrections: {len(audit_df):,}")

    # Group by correction type
    by_type = audit_df['correction_type'].value_counts()
    print("\nCorrections by type:")
    for corr_type, count in by_type.items():
        print(f"  {corr_type}: {count:,}")

    # Group by field
    by_field = audit_df['field'].value_counts()
    print("\nCorrections by field:")
    for field, count in by_field.head(10).items():
        print(f"  {field}: {count:,}")


def example_8_quality_metrics():
    """Example 8: Analyze quality metrics after processing."""
    print("\n" + "=" * 80)
    print("Example 8: Quality Metrics Analysis")
    print("=" * 80)

    processor = CADDataProcessor('config/config.yml')
    processor.load_data()

    # Calculate quality scores
    processor.calculate_quality_scores()

    # Analyze quality distribution
    import pandas as pd
    df = processor.df

    total = len(df)
    high_quality = (df['quality_score'] >= 80).sum()
    medium_quality = ((df['quality_score'] >= 50) & (df['quality_score'] < 80)).sum()
    low_quality = (df['quality_score'] < 50).sum()

    print(f"\nQuality Distribution:")
    print(f"  High (≥80):   {high_quality:,} ({high_quality/total*100:.1f}%)")
    print(f"  Medium (50-79): {medium_quality:,} ({medium_quality/total*100:.1f}%)")
    print(f"  Low (<50):    {low_quality:,} ({low_quality/total*100:.1f}%)")

    # Show average by year
    if 'Time of Call' in df.columns:
        df['Year'] = pd.to_datetime(df['Time of Call']).dt.year
        by_year = df.groupby('Year')['quality_score'].mean()

        print(f"\nAverage Quality by Year:")
        for year, avg_score in by_year.items():
            print(f"  {year}: {avg_score:.1f}/100")


if __name__ == "__main__":
    """
    Run examples.

    Comment/uncomment examples as needed.
    """

    # Example 1: Basic pipeline (full processing)
    # example_1_basic_pipeline()

    # Example 2: Validation only (no processing)
    example_2_validation_only()

    # Example 3: Custom corrections
    # example_3_custom_corrections()

    # Example 4: Custom manual review criteria
    # example_4_manual_review_query()

    # Example 5: Post-processing validation
    # example_5_post_validation()

    # Example 6: Batch processing
    # example_6_batch_processing()

    # Example 7: Audit trail analysis
    # example_7_audit_trail_analysis()

    # Example 8: Quality metrics analysis
    # example_8_quality_metrics()

    print("\n" + "=" * 80)
    print("Examples completed")
    print("=" * 80)
