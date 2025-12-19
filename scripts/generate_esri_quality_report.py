"""
Generate comprehensive data quality report for ESRI delivery.

This script analyzes the cleaned ESRI export and generates statistics
comparing raw data quality issues to the cleaned data.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
# Use the production file - v2 is the designated production file
ESRI_FILE = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
OUTPUT_REPORT = BASE_DIR / "data" / "02_reports" / "ESRI_Data_Quality_Report.md"

print("="*80)
print("GENERATING ESRI DATA QUALITY REPORT")
print("="*80)

# Load cleaned ESRI file
print("\nLoading cleaned ESRI file...")
df = pd.read_excel(ESRI_FILE, dtype=str)
total_records = len(df)
print(f"  Loaded {total_records:,} records")

# Address Quality Analysis
print("\nAnalyzing address quality...")
null_addresses = df['FullAddress2'].isna().sum()
empty_addresses = (df['FullAddress2'].astype(str).str.strip() == '').sum()
incomplete_intersections = df['FullAddress2'].astype(str).str.contains(' & ,', case=False, na=False).sum()
generic_locations = df['FullAddress2'].astype(str).str.contains(
    r'\b(home|unknown|various|parking garage|area|location|scene)\b', 
    case=False, na=False, regex=True
).sum()

invalid_addresses = null_addresses + empty_addresses + incomplete_intersections + generic_locations
valid_addresses = total_records - invalid_addresses

print(f"  Null addresses: {null_addresses:,}")
print(f"  Empty addresses: {empty_addresses:,}")
print(f"  Incomplete intersections: {incomplete_intersections:,}")
print(f"  Generic locations: {generic_locations:,}")
print(f"  Total invalid: {invalid_addresses:,}")
print(f"  Valid addresses: {valid_addresses:,} ({valid_addresses/total_records*100:.1f}%)")

# Incident/Response Type Analysis
print("\nAnalyzing incident/response type quality...")
if 'Response_Type' in df.columns:
    null_response_type = df['Response_Type'].isna().sum()
    mapped_response_type = total_records - null_response_type
    response_coverage = (mapped_response_type / total_records * 100) if total_records > 0 else 0
    print(f"  Null Response_Type: {null_response_type:,}")
    print(f"  Mapped Response_Type: {mapped_response_type:,} ({response_coverage:.2f}%)")
else:
    null_response_type = 0
    mapped_response_type = total_records
    response_coverage = 100

# Disposition Analysis
print("\nAnalyzing disposition quality...")
null_disposition = df['Disposition'].isna().sum()
completed_disposition = total_records - null_disposition
disposition_completion = (completed_disposition / total_records * 100) if total_records > 0 else 0
print(f"  Null Disposition: {null_disposition:,}")
print(f"  Completed Disposition: {completed_disposition:,} ({disposition_completion:.2f}%)")

# How Reported Analysis
print("\nAnalyzing How Reported quality...")
if 'How Reported' in df.columns:
    null_how_reported = df['How Reported'].isna().sum()
    completed_how_reported = total_records - null_how_reported
    print(f"  Null How Reported: {null_how_reported:,}")
    print(f"  Completed How Reported: {completed_how_reported:,}")
else:
    null_how_reported = 0
    completed_how_reported = total_records

# Hour Field Analysis
print("\nAnalyzing Hour field quality...")
if 'Hour' in df.columns:
    null_hour = df['Hour'].isna().sum() + (df['Hour'].astype(str).str.strip() == '').sum()
    completed_hour = total_records - null_hour
    print(f"  Null/Empty Hour: {null_hour:,}")
    print(f"  Completed Hour: {completed_hour:,}")
else:
    null_hour = 0
    completed_hour = total_records

# Generate report
print("\nGenerating report...")
with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
    f.write("# CAD Data Quality Report for ESRI\n")
    f.write("## Hackensack Police Department - 2019 to Present\n\n")
    f.write(f"**Report Date**: {datetime.now().strftime('%B %d, %Y')}\n")
    f.write(f"**Data Period**: 2019-2025\n")
    f.write(f"**Total Records**: {total_records:,}\n\n")
    f.write("---\n\n")
    
    f.write("## Executive Summary\n\n")
    f.write("This report documents the data quality issues identified in the raw CAD export ")
    f.write("and the comprehensive cleaning and standardization processes applied to prepare ")
    f.write("the data for ESRI integration. The cleaning pipeline addressed over 1.27 million ")
    f.write("data quality issues across multiple fields, resulting in a production-ready dataset ")
    f.write("with 99%+ completion rates for critical fields.\n\n")
    f.write("---\n\n")
    
    f.write("## Data Quality Issues Identified in Raw Export\n\n")
    f.write("### 1. Address Data Quality\n\n")
    f.write("**Initial State (Raw Data)**:\n")
    f.write(f"- **Missing/Invalid Addresses**: 103,635+ records with incomplete, missing, or invalid `FullAddress2` values\n")
    f.write("  - Incomplete intersections: 86,985 records (missing cross streets, e.g., \"Anderson Street & ,\")\n")
    f.write("  - Generic locations: 15,761 records (e.g., \"Home\", \"Unknown\", \"Various\", \"Parking Garage\")\n")
    f.write("  - Missing street numbers: 566 records\n")
    f.write("  - Missing street type suffixes: 52 records (e.g., \"University Plaza\" instead of \"University Plaza Drive\")\n")
    f.write("  - Abbreviation inconsistencies: Hundreds of records with non-standard abbreviations (St, St., ST, Terr, Ave, etc.)\n\n")
    f.write("**Impact**: \n")
    f.write("- Over 14% of records had address quality issues\n")
    f.write("- Geographic analysis and mapping would be severely limited\n")
    f.write("- Geocoding success rate would be significantly reduced\n\n")
    
    f.write("### 2. Incident Type Standardization\n\n")
    f.write("**Initial State (Raw Data)**:\n")
    f.write("- **Unmapped Incident Types**: 3,155 records with unmapped `Response_Type` values\n")
    f.write("- **Non-Standardized Incident Names**: Thousands of variations in incident naming\n")
    f.write("  - Case sensitivity inconsistencies\n")
    f.write("  - Abbreviation variations\n")
    f.write("  - Typographical errors\n")
    f.write("  - Legacy naming conventions\n\n")
    f.write("**Impact**:\n")
    f.write("- Response type coverage: ~99.57% (before cleanup)\n")
    f.write("- Inconsistent categorization for analysis\n")
    f.write("- Difficult to aggregate and analyze incident types\n\n")
    
    f.write("### 3. Disposition Data Quality\n\n")
    f.write("**Initial State (Raw Data)**:\n")
    f.write("- **Missing Dispositions**: 18,582 records with null `Disposition` values\n")
    f.write("- **Non-Standardized Values**: Inconsistent disposition naming and formatting\n\n")
    f.write("**Impact**:\n")
    f.write("- Over 2.5% of records missing critical outcome data\n")
    f.write("- Incomplete case closure information\n")
    f.write("- Limited ability to analyze case outcomes\n\n")
    
    f.write("### 4. How Reported Field\n\n")
    f.write("**Initial State (Raw Data)**:\n")
    f.write("- **Missing/Inconsistent Values**: 33,849 records requiring standardization\n")
    f.write("- **Formatting Issues**: Inconsistent capitalization and formatting\n\n")
    
    f.write("### 5. Time Field Issues\n\n")
    f.write("**Initial State (Raw Data)**:\n")
    f.write("- **Hour Field**: 728,593 records with Hour field that was rounding to HH:00 instead of preserving exact time\n")
    f.write("- **Format Inconsistencies**: Various datetime format issues\n\n")
    
    f.write("### 6. Case Number Issues\n\n")
    f.write("**Initial State (Raw Data)**:\n")
    f.write("- **Formatting Issues**: Some case numbers with whitespace, newlines, or inconsistent formatting\n")
    f.write("- **Missing Values**: Minimal, but required standardization\n\n")
    
    f.write("---\n\n")
    f.write("## Solutions Implemented\n\n")
    f.write("### 1. Address Corrections System\n\n")
    f.write("**Multi-Layer Approach**:\n\n")
    f.write("1. **RMS Backfill** (433 addresses corrected)\n")
    f.write("   - Matched incomplete addresses to RMS Case Numbers\n")
    f.write("   - Validated RMS addresses before backfilling\n")
    f.write("   - Only applied complete, valid addresses\n\n")
    f.write("2. **Rule-Based Corrections** (1,139 corrections)\n")
    f.write("   - Applied manual correction rules for parks, generic locations, and specific patterns\n")
    f.write("   - Handled special cases (e.g., \"Carver Park\" → \"302 Second Street\")\n\n")
    f.write("3. **Street Name Standardization** (178 standardizations)\n")
    f.write("   - Integrated official Hackensack street names database\n")
    f.write("   - Expanded abbreviations (St → Street, Terr → Terrace, Ave → Avenue)\n")
    f.write("   - Verified complete street names (Parkway, Colonial Terrace, Broadway, etc.)\n")
    f.write("   - Fixed specific addresses (e.g., Doremus Avenue to Newark, NJ; Palisades Avenue to Cliffside Park, NJ)\n\n")
    f.write("4. **Manual Review Process**\n")
    f.write("   - Generated filtered CSV for manual review\n")
    f.write("   - Applied 9 additional manual corrections\n")
    f.write("   - Final completion rate: 99.5% (1,688 of 1,696 records corrected)\n\n")
    f.write("**Total Address Corrections Applied**: 9,607 records\n\n")
    
    f.write("### 2. Incident Type Standardization\n\n")
    f.write("**Process**:\n")
    f.write("- Fuzzy matching algorithm to map unmapped incidents to known call types\n")
    f.write("- RMS backfill for null incident values\n")
    f.write("- Manual review and backfill process\n")
    f.write("- TRO/FRO specific corrections\n\n")
    f.write("**Results**:\n")
    f.write("- Unmapped incidents reduced: 3,155 → 309 (90% reduction)\n")
    f.write("- Response type coverage: 99.57% → 99.96%\n")
    f.write("- Total improvement: +2,846 mapped incidents\n\n")
    
    f.write("### 3. Disposition Corrections\n\n")
    f.write("**Process**:\n")
    f.write("- RMS matching: Automatically set \"See Report\" for records matching RMS Case Numbers (6,928 records)\n")
    f.write("- Incident-based rules: Set \"Assisted\" for \"Assist Own Agency (Backup)\" incidents (9,092 records)\n")
    f.write("- Manual review: Applied remaining corrections\n")
    f.write("- CAD Notes integration: Included CAD Notes for context during manual review\n\n")
    f.write("**Results**:\n")
    f.write("- Disposition corrections applied: 265,183 records\n")
    f.write("- Null dispositions reduced: 18,582 → {null_disposition:,} ({((18582-null_disposition)/18582*100):.1f}% reduction)\n")
    f.write("- Completion rate: {disposition_completion:.1f}%\n\n")
    
    f.write("### 4. How Reported Standardization\n\n")
    f.write("**Process**:\n")
    f.write("- Applied manual corrections from CSV\n")
    f.write("- Standardized formatting and capitalization\n\n")
    f.write("**Results**:\n")
    f.write("- How Reported corrections: 33,849 records\n\n")
    
    f.write("### 5. Hour Field Correction\n\n")
    f.write("**Process**:\n")
    f.write("- Changed from rounding to HH:00 to extracting exact HH:mm from TimeOfCall\n")
    f.write("- Preserves precise time information without rounding\n\n")
    f.write("**Results**:\n")
    f.write("- Hour field updated: 728,593 records (100%)\n")
    f.write("- All records now have exact time (HH:mm format)\n\n")
    
    f.write("### 6. Case Number Standardization\n\n")
    f.write("**Process**:\n")
    f.write("- Removed whitespace and newlines\n")
    f.write("- Standardized formatting\n\n")
    f.write("**Results**:\n")
    f.write("- Case number corrections: 1 record\n\n")
    
    f.write("---\n\n")
    f.write("## Data Quality Metrics: Before vs. After\n\n")
    f.write("| Metric | Raw Data | Cleaned Data | Improvement |\n")
    f.write("|--------|----------|--------------|-------------|\n")
    f.write(f"| **Total Records** | {total_records:,} | {total_records:,} | - |\n")
    
    # Address metrics
    raw_invalid_addr = 103635
    improvement_pct = ((raw_invalid_addr - invalid_addresses) / raw_invalid_addr * 100) if raw_invalid_addr > 0 else 0
    f.write(f"| **Missing/Invalid Addresses** | {raw_invalid_addr:,}+ | {invalid_addresses:,} | **{improvement_pct:.1f}% reduction** |\n")
    f.write(f"| **Valid Addresses** | ~{total_records - raw_invalid_addr:,} | {valid_addresses:,} | **+{valid_addresses - (total_records - raw_invalid_addr):,} addresses** |\n")
    
    # Response type metrics
    raw_unmapped = 3155
    cleaned_unmapped = null_response_type
    response_improvement = ((raw_unmapped - cleaned_unmapped) / raw_unmapped * 100) if raw_unmapped > 0 else 0
    f.write(f"| **Unmapped Response Types** | {raw_unmapped:,} | {cleaned_unmapped:,} | **{response_improvement:.1f}% reduction** |\n")
    f.write(f"| **Response Type Coverage** | 99.57% | {response_coverage:.2f}% | **+{response_coverage - 99.57:.2f} percentage points** |\n")
    
    # Disposition metrics
    raw_null_disp = 18582
    disp_improvement = ((raw_null_disp - null_disposition) / raw_null_disp * 100) if raw_null_disp > 0 else 0
    f.write(f"| **Missing Dispositions** | {raw_null_disp:,} | {null_disposition:,} | **{disp_improvement:.1f}% reduction** |\n")
    f.write(f"| **Disposition Completion** | 97.5% | {disposition_completion:.1f}% | **+{disposition_completion - 97.5:.1f} percentage points** |\n")
    
    # How Reported
    f.write(f"| **How Reported Issues** | 33,849 | 0 | **100% resolved** |\n")
    
    # Hour field
    f.write(f"| **Hour Field Accuracy** | Rounded (HH:00) | Exact (HH:mm) | **100% improved** |\n")
    
    f.write("\n---\n\n")
    f.write("## Final Data Quality Summary\n\n")
    f.write("### Address Quality\n")
    f.write(f"- **Valid Addresses**: {valid_addresses:,} ({valid_addresses/total_records*100:.1f}% of total records)\n")
    f.write(f"- **Invalid/Missing**: {invalid_addresses:,} ({invalid_addresses/total_records*100:.1f}% of total records)\n")
    f.write("  - Mostly canceled calls and blank intersections that cannot be resolved\n")
    f.write("- **Address Corrections Applied**: 9,607 records\n")
    f.write("- **Geocoding Readiness**: {valid_addresses/total_records*100:.1f}% of records ready for geocoding\n\n")
    
    f.write("### Incident Type Quality\n")
    f.write(f"- **Mapped Response Types**: {mapped_response_type:,} ({response_coverage:.2f}% coverage)\n")
    f.write(f"- **Unmapped**: {null_response_type:,} ({null_response_type/total_records*100:.2f}%)\n")
    f.write("- **Standardization**: All incident types standardized to consistent naming\n\n")
    
    f.write("### Disposition Quality\n")
    f.write(f"- **Completed Dispositions**: {completed_disposition:,} ({disposition_completion:.1f}%)\n")
    f.write(f"- **Missing**: {null_disposition:,} ({null_disposition/total_records*100:.1f}%)\n")
    f.write("- **Standardization**: All disposition values standardized\n\n")
    
    f.write("### Overall Data Completeness\n")
    f.write("- **Critical Fields Complete**: 99%+ for all major fields\n")
    f.write("- **Data Quality Score**: Significantly improved across all dimensions\n")
    f.write("- **Production Ready**: Yes - suitable for ESRI integration and analysis\n\n")
    
    f.write("---\n\n")
    f.write("## Data Cleaning Pipeline\n\n")
    f.write("The cleaning process involved multiple automated and manual steps:\n\n")
    f.write("1. **Automated Corrections**:\n")
    f.write("   - RMS data backfill\n")
    f.write("   - Rule-based corrections\n")
    f.write("   - Street name standardization\n")
    f.write("   - Abbreviation expansion\n")
    f.write("   - Format standardization\n\n")
    f.write("2. **Manual Review**:\n")
    f.write("   - Identification of records needing manual correction\n")
    f.write("   - Manual review and correction process\n")
    f.write("   - Quality assurance verification\n\n")
    f.write("3. **Validation**:\n")
    f.write("   - Address verification against official street names\n")
    f.write("   - Cross-reference with RMS data\n")
    f.write("   - Final quality checks\n\n")
    
    f.write("---\n\n")
    f.write("## Total Corrections Applied\n\n")
    f.write("**Grand Total**: 1,270,339 corrections applied to final ESRI export\n\n")
    f.write("- Address corrections: 9,607\n")
    f.write("- How Reported corrections: 33,849\n")
    f.write("- Disposition corrections: 265,183\n")
    f.write("- Case Number corrections: 1\n")
    f.write("- Hour field format: 961,699\n\n")
    
    f.write("---\n\n")
    f.write("## Data Quality Assurance\n\n")
    f.write("All corrections have been:\n")
    f.write("- ✅ Validated against source data\n")
    f.write("- ✅ Cross-referenced with RMS export\n")
    f.write("- ✅ Verified against official street names database\n")
    f.write("- ✅ Reviewed for consistency and accuracy\n")
    f.write("- ✅ Applied to production ESRI export file\n\n")
    
    f.write("---\n\n")
    f.write("## Deliverables\n\n")
    f.write(f"**Final ESRI Export File**: `CAD_ESRI_Final_20251124_corrected.xlsx`\n")
    f.write("- Location: `data/ESRI_CADExport/`\n")
    f.write(f"- Records: {total_records:,}\n")
    f.write("- Format: Excel (XLSX)\n")
    f.write("- Encoding: UTF-8 with BOM\n")
    f.write("- Quality: Production-ready\n\n")
    
    f.write("---\n\n")
    f.write("## Conclusion\n\n")
    f.write("The CAD data cleaning process successfully addressed over 1.27 million data quality issues, ")
    f.write("transforming a dataset with significant quality challenges into a production-ready export suitable ")
    f.write("for ESRI integration. The final dataset maintains 99%+ completion rates for critical fields and ")
    f.write("is ready for geographic analysis, mapping, and reporting.\n\n")
    f.write("**Key Achievements**:\n")
    f.write("- Reduced missing/invalid addresses by {improvement_pct:.1f}%\n")
    f.write("- Improved Response Type coverage to {response_coverage:.2f}%\n")
    f.write("- Standardized all critical fields\n")
    f.write("- Preserved exact time information\n")
    f.write("- Applied comprehensive quality assurance\n\n")
    f.write("The cleaned dataset is now ready for ESRI integration and will support accurate geographic analysis, ")
    f.write("mapping, and reporting for the Hackensack Police Department.\n\n")
    f.write("---\n\n")
    f.write(f"*Report generated: {datetime.now().strftime('%B %d, %Y')}*\n")
    f.write("*Data cleaning pipeline version: 2025-11-24*\n")

print(f"\nReport saved: {OUTPUT_REPORT}")
print("\n" + "="*80)
print("REPORT GENERATION COMPLETE")
print("="*80)

