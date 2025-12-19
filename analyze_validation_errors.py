"""
Quick Analysis of Validation Errors
Analyzes the error patterns to help prioritize fixes.
"""

import pandas as pd
from pathlib import Path
from collections import Counter

def main():
    base_path = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
    errors_file = base_path / "CAD_VALIDATION_ERRORS.csv"
    
    if not errors_file.exists():
        print(f"Error file not found: {errors_file}")
        return
    
    print("Loading validation errors...")
    df = pd.read_csv(errors_file)
    
    print(f"\nTotal errors: {len(df):,}")
    print(f"Fields with errors: {df['field'].nunique()}")
    
    # Analyze by field
    print("\n" + "="*80)
    print("ERRORS BY FIELD")
    print("="*80)
    field_counts = df['field'].value_counts()
    for field, count in field_counts.items():
        pct = (count / len(df)) * 100
        print(f"{field:30s} {count:>10,} ({pct:>5.1f}%)")
    
    # Analyze Incident errors (top patterns)
    print("\n" + "="*80)
    print("INCIDENT - Top 20 Values (without ' - ' separator)")
    print("="*80)
    incident_errors = df[df['field'] == 'Incident']['value'].value_counts().head(20)
    for value, count in incident_errors.items():
        print(f"{count:>8,}  {value}")
    
    # Analyze Disposition errors
    print("\n" + "="*80)
    print("DISPOSITION - Invalid Values (Full List)")
    print("="*80)
    disposition_errors = df[df['field'] == 'Disposition']['value'].value_counts()
    if len(disposition_errors) > 0:
        print(f"\nFound {len(disposition_errors)} unique invalid Disposition values:\n")
        for value, count in disposition_errors.items():
            print(f"{count:>8,}  {value}")
    else:
        print("No invalid Disposition values found!")
    
    # Analyze How Reported errors
    print("\n" + "="*80)
    print("HOW REPORTED - Invalid Values")
    print("="*80)
    how_reported_errors = df[df['field'] == 'How Reported']['value'].value_counts()
    if len(how_reported_errors) > 0:
        print(f"\nFound {len(how_reported_errors)} unique invalid How Reported values:\n")
        for value, count in how_reported_errors.items():
            print(f"{count:>8,}  {value}")
    else:
        print("No invalid How Reported values found!")
    
    # Analyze ReportNumberNew errors
    print("\n" + "="*80)
    print("REPORTNUMBERNEW - Error Patterns")
    print("="*80)
    report_num_errors = df[df['field'] == 'ReportNumberNew']
    print(f"\nTotal ReportNumberNew errors: {len(report_num_errors)}")
    
    # Group by message type
    msg_counts = report_num_errors['message'].value_counts()
    for msg, count in msg_counts.items():
        print(f"\n{msg}: {count} records")
        
        # Show examples
        examples = report_num_errors[report_num_errors['message'] == msg]['value'].head(10)
        for ex in examples:
            print(f"  - {ex}")
    
    # PDZone errors
    print("\n" + "="*80)
    print("PDZONE - Invalid Values")
    print("="*80)
    zone_errors = df[df['field'] == 'PDZone']['value'].value_counts()
    if len(zone_errors) > 0:
        print(f"\nFound {len(zone_errors)} unique invalid PDZone values:\n")
        for value, count in zone_errors.items():
            print(f"{count:>8,}  {value}")
    else:
        print("No invalid PDZone values found!")
    
    # Export unique invalid values for each field
    print("\n" + "="*80)
    print("EXPORTING UNIQUE INVALID VALUES")
    print("="*80)
    
    for field in df['field'].unique():
        field_errors = df[df['field'] == field]
        unique_values = field_errors['value'].value_counts().reset_index()
        unique_values.columns = ['value', 'count']
        
        safe_field_name = field.replace(' ', '_').replace('/', '_')
        output_file = base_path / f"Invalid_{safe_field_name}_Values.csv"
        unique_values.to_csv(output_file, index=False)
        print(f"  Exported: {output_file.name} ({len(unique_values)} unique values)")
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)

if __name__ == "__main__":
    main()

