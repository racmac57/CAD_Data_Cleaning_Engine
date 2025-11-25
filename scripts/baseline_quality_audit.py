"""
CAD Data Baseline Quality Audit
Generates a comprehensive admin report on raw CAD data quality

Author: Claude Code
Date: 2025-11-22
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime
from collections import Counter

# ============================================================================
# CONFIGURATION
# ============================================================================

# Input files
CAD_SAMPLE = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\data\01_raw\sample\2024_CAD_ALL_SAMPLE_1000.csv"
CALL_TYPE_REF = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\ref\RAW_CAD_CALL_TYPE_EXPORT.xlsx"

# Output files
CSV_REPORT = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\data\02_reports\cad_validation\CAD_Baseline_Quality_Report.csv"
MD_REPORT = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\data\02_reports\cad_validation\CAD_Baseline_Quality_Admin_Report.md"

# ============================================================================
# FIELD VALIDATION FUNCTIONS
# ============================================================================

def is_blank_or_malformed(value):
    """Check if value is blank, null, or malformed"""
    if pd.isna(value):
        return True
    if str(value).strip() == '':
        return True
    if str(value).lower() in ['nan', 'none', 'null', 'n/a', 'na']:
        return True
    return False

def validate_case_number(case_num):
    """Validate ReportNumberNew format (YY-NNNNNN)"""
    if is_blank_or_malformed(case_num):
        return False, "Blank/Empty"

    pattern = r'^\d{2}-\d{6}$'
    if not re.match(pattern, str(case_num)):
        return False, "Invalid Format"

    return True, "Valid"

def validate_time_of_call(time_val):
    """Validate Time of Call format"""
    if is_blank_or_malformed(time_val):
        return False, "Blank/Empty"

    try:
        pd.to_datetime(time_val)
        return True, "Valid"
    except:
        return False, "Invalid Format"

def has_incomplete_intersection(address):
    """Check if address is an incomplete intersection (ends with & ,)"""
    if is_blank_or_malformed(address):
        return False
    return bool(re.search(r'&\s*,', str(address)))

def is_legacy_burglary(incident):
    """Check if incident uses legacy burglary classification"""
    if is_blank_or_malformed(incident):
        return False

    incident_str = str(incident).strip()
    legacy_patterns = [
        r'^Burglary\s+2C:18-2$',
        r'^Burglary\s*$',
        r'^Attempted Burglary\s+2C:18-2$'
    ]

    for pattern in legacy_patterns:
        if re.match(pattern, incident_str, re.IGNORECASE):
            return True
    return False

def is_generic_taps(incident):
    """Check if incident is generic TAPS (not enhanced)"""
    if is_blank_or_malformed(incident):
        return False

    incident_str = str(incident).strip()
    return incident_str == "Targeted Area Patrol"

# ============================================================================
# BASELINE QUALITY ANALYSIS
# ============================================================================

def analyze_field_quality(df, field_name):
    """Analyze quality of a specific field"""
    total = len(df)
    blank_count = df[field_name].apply(is_blank_or_malformed).sum()
    blank_pct = (blank_count / total) * 100

    return {
        'field': field_name,
        'total_records': total,
        'blank_count': blank_count,
        'blank_percentage': blank_pct,
        'valid_count': total - blank_count,
        'valid_percentage': 100 - blank_pct
    }

def generate_baseline_metrics(df):
    """Generate baseline quality metrics for all key fields"""
    fields_to_check = [
        'Incident',
        'FullAddress2',
        'Time of Call',
        'Disposition',
        'ReportNumberNew',
        'Officer'
    ]

    metrics = []
    for field in fields_to_check:
        if field in df.columns:
            metrics.append(analyze_field_quality(df, field))
        else:
            metrics.append({
                'field': field,
                'total_records': len(df),
                'blank_count': len(df),
                'blank_percentage': 100.0,
                'valid_count': 0,
                'valid_percentage': 0.0
            })

    return pd.DataFrame(metrics)

# ============================================================================
# TOP ISSUES IDENTIFICATION
# ============================================================================

def identify_top_issues(df):
    """Identify top 10 data quality issues"""
    issues = []
    total = len(df)

    # Issue 1: Incomplete intersections
    incomplete_intersections = df['FullAddress2'].apply(has_incomplete_intersection)
    incomplete_count = incomplete_intersections.sum()
    if incomplete_count > 0:
        issues.append({
            'issue': 'Incomplete Intersections',
            'description': 'Addresses ending with "& ," (missing cross street)',
            'count': incomplete_count,
            'percentage': (incomplete_count / total) * 100,
            'severity': 'HIGH',
            'example': df[incomplete_intersections]['FullAddress2'].iloc[0] if incomplete_count > 0 else 'N/A'
        })

    # Issue 2: Blank Incidents
    blank_incidents = df['Incident'].apply(is_blank_or_malformed)
    blank_incident_count = blank_incidents.sum()
    if blank_incident_count > 0:
        issues.append({
            'issue': 'Blank Incident Field',
            'description': 'Records with missing incident type',
            'count': blank_incident_count,
            'percentage': (blank_incident_count / total) * 100,
            'severity': 'CRITICAL',
            'example': 'N/A'
        })

    # Issue 3: Legacy Burglary Classifications
    legacy_burglary = df['Incident'].apply(is_legacy_burglary)
    legacy_count = legacy_burglary.sum()
    if legacy_count > 0:
        issues.append({
            'issue': 'Legacy Burglary Classifications',
            'description': 'Using outdated "Burglary 2C:18-2" instead of enhanced types',
            'count': legacy_count,
            'percentage': (legacy_count / total) * 100,
            'severity': 'MEDIUM',
            'example': df[legacy_burglary]['Incident'].iloc[0] if legacy_count > 0 else 'N/A'
        })

    # Issue 4: Generic TAPS
    generic_taps = df['Incident'].apply(is_generic_taps)
    generic_taps_count = generic_taps.sum()
    if generic_taps_count > 0:
        issues.append({
            'issue': 'Generic TAPS Incidents',
            'description': 'Using "Targeted Area Patrol" instead of enhanced TAPS-ESU types',
            'count': generic_taps_count,
            'percentage': (generic_taps_count / total) * 100,
            'severity': 'MEDIUM',
            'example': 'Targeted Area Patrol'
        })

    # Issue 5: Blank FullAddress2
    blank_address = df['FullAddress2'].apply(is_blank_or_malformed)
    blank_address_count = blank_address.sum()
    if blank_address_count > 0:
        issues.append({
            'issue': 'Blank Address Field',
            'description': 'Records with missing address information',
            'count': blank_address_count,
            'percentage': (blank_address_count / total) * 100,
            'severity': 'CRITICAL',
            'example': 'N/A'
        })

    # Issue 6: Blank PDZone
    if 'PDZone' in df.columns:
        blank_pdzone = df['PDZone'].apply(is_blank_or_malformed)
        blank_pdzone_count = blank_pdzone.sum()
        if blank_pdzone_count > 0:
            issues.append({
                'issue': 'Missing PDZone',
                'description': 'Records without police district zone assignment',
                'count': blank_pdzone_count,
                'percentage': (blank_pdzone_count / total) * 100,
                'severity': 'MEDIUM',
                'example': 'N/A'
            })

    # Issue 7: Blank Grid
    if 'Grid' in df.columns:
        blank_grid = df['Grid'].apply(is_blank_or_malformed)
        blank_grid_count = blank_grid.sum()
        if blank_grid_count > 0:
            issues.append({
                'issue': 'Missing Grid',
                'description': 'Records without grid assignment',
                'count': blank_grid_count,
                'percentage': (blank_grid_count / total) * 100,
                'severity': 'LOW',
                'example': 'N/A'
            })

    # Issue 8: Malformed Case Numbers
    malformed_cases = []
    for idx, row in df.iterrows():
        valid, reason = validate_case_number(row['ReportNumberNew'])
        if not valid:
            malformed_cases.append(row['ReportNumberNew'])

    if len(malformed_cases) > 0:
        issues.append({
            'issue': 'Malformed Case Numbers',
            'description': 'Invalid case number format (should be YY-NNNNNN)',
            'count': len(malformed_cases),
            'percentage': (len(malformed_cases) / total) * 100,
            'severity': 'HIGH',
            'example': malformed_cases[0] if malformed_cases else 'N/A'
        })

    # Issue 9: Blank Disposition
    blank_disposition = df['Disposition'].apply(is_blank_or_malformed)
    blank_disposition_count = blank_disposition.sum()
    if blank_disposition_count > 0:
        issues.append({
            'issue': 'Blank Disposition',
            'description': 'Records without case disposition',
            'count': blank_disposition_count,
            'percentage': (blank_disposition_count / total) * 100,
            'severity': 'MEDIUM',
            'example': 'N/A'
        })

    # Issue 10: Blank Officer
    blank_officer = df['Officer'].apply(is_blank_or_malformed)
    blank_officer_count = blank_officer.sum()
    if blank_officer_count > 0:
        issues.append({
            'issue': 'Missing Officer Assignment',
            'description': 'Records without assigned officer',
            'count': blank_officer_count,
            'percentage': (blank_officer_count / total) * 100,
            'severity': 'MEDIUM',
            'example': 'N/A'
        })

    # Sort by count descending and take top 10
    issues_df = pd.DataFrame(issues)
    if len(issues_df) > 0:
        issues_df = issues_df.sort_values('count', ascending=False).head(10)

    return issues_df

# ============================================================================
# MARKDOWN REPORT GENERATION
# ============================================================================

def generate_markdown_report(baseline_metrics, issues_df, total_records):
    """Generate comprehensive markdown admin report"""

    report_date = datetime.now().strftime('%Y-%m-%d')

    md = f"""# CAD Data Baseline Quality Audit Report

**Report Generated:** {report_date}
**Source Dataset:** `2024_CAD_ALL_SAMPLE_1000.csv`
**Total Records Analyzed:** {total_records:,}
**Data Period:** 2024 CAD Records (Sample)

---

## 📊 Section 1: Baseline Audit Summary

This report summarizes the quality of the **RAW CAD sample data BEFORE any data cleanup or mapping**.

### Field-Level Quality Metrics

| Field | Total Records | Blank/Malformed | Valid Records | Quality Score |
|-------|--------------|-----------------|---------------|---------------|
"""

    for _, row in baseline_metrics.iterrows():
        md += f"| **{row['field']}** | {row['total_records']:,} | {row['blank_count']:,} ({row['blank_percentage']:.1f}%) | {row['valid_count']:,} ({row['valid_percentage']:.1f}%) | {'✅' if row['blank_percentage'] < 5 else '⚠️' if row['blank_percentage'] < 20 else '❌'} |\n"

    md += f"""
### Summary Statistics

"""

    # Calculate overall quality score
    avg_blank_pct = baseline_metrics['blank_percentage'].mean()
    overall_quality = 100 - avg_blank_pct

    md += f"""- **Overall Data Quality Score:** {overall_quality:.1f}% (Average across all fields)
- **Best Field:** {baseline_metrics.loc[baseline_metrics['blank_percentage'].idxmin(), 'field']} ({baseline_metrics['blank_percentage'].min():.1f}% blank)
- **Worst Field:** {baseline_metrics.loc[baseline_metrics['blank_percentage'].idxmax(), 'field']} ({baseline_metrics['blank_percentage'].max():.1f}% blank)

### Quality Report CSV

📁 **Full report saved to:** `data/02_reports/cad_validation/CAD_Baseline_Quality_Report.csv`

---

## ❗ Section 2: Top 10 Most Common Data Quality Issues

"""

    if len(issues_df) > 0:
        for idx, (i, issue) in enumerate(issues_df.iterrows(), 1):
            severity_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }.get(issue['severity'], '⚪')

            md += f"""### {idx}. {severity_emoji} {issue['issue']} ({issue['severity']})

**Description:** {issue['description']}
**Occurrences:** {issue['count']:,} records ({issue['percentage']:.1f}% of sample)
**Example:** `{issue['example']}`

"""
    else:
        md += "**No major data quality issues identified in this sample.**\n\n"

    md += """---

## 📌 Section 3: Recommendations

Based on this baseline audit, here are key recommendations for the admin team:

### ✅ Data Quality Improvements After Cleanup

"""

    # Calculate improvement potential
    if len(issues_df) > 0:
        total_issues = issues_df['count'].sum()
        md += f"""- **{total_issues:,} records** ({(total_issues/total_records)*100:.1f}% of sample) have at least one data quality issue
- After applying data cleanup, mapping, and backfill processes, estimated improvement: **{min((total_issues/total_records)*100, 95):.0f}%**
- Priority should be given to **CRITICAL** and **HIGH** severity issues first

"""

    md += """### 🎯 Where Issues Are Concentrated

"""

    if len(issues_df) > 0:
        # Group by severity
        critical_issues = issues_df[issues_df['severity'] == 'CRITICAL']
        high_issues = issues_df[issues_df['severity'] == 'HIGH']

        if len(critical_issues) > 0:
            md += f"**CRITICAL Issues ({len(critical_issues)}):**\n"
            for _, issue in critical_issues.iterrows():
                md += f"- {issue['issue']}: {issue['count']:,} records\n"
            md += "\n"

        if len(high_issues) > 0:
            md += f"**HIGH Priority Issues ({len(high_issues)}):**\n"
            for _, issue in high_issues.iterrows():
                md += f"- {issue['issue']}: {issue['count']:,} records\n"
            md += "\n"

    md += """### 📍 Specific Problem Areas

1. **Address Data Quality**
   - Incomplete intersections (missing cross streets)
   - Generic location placeholders (parks, "Home", etc.)
   - **Action:** Apply FullAddress2 correction rules and RMS backfill

2. **Incident Classification Drift**
   - Legacy burglary classifications need enhancement
   - Generic TAPS incidents need to be reclassified to specific ESU types
   - **Action:** Use incident type mapping and possibly integrate `classify_burglary_ollama.py`

3. **Missing Metadata Fields**
   - PDZone and Grid assignments incomplete
   - **Action:** Backfill from RMS or GIS lookup based on address

### 🔄 Ongoing Monitoring

**Recommendations:**
- ✅ **Rerun this quality audit monthly** to monitor data drift
- ✅ **Track quality score trends** over time (target: >95% overall quality)
- ✅ **Set up automated alerts** when critical fields exceed 10% blank rate
- ✅ **Compare 2019 vs 2024+ data** to identify classification drift patterns

---

## 🔍 Section 4: Follow-up Checks

### Burglary Classification Tool

**Question:** Was `classify_burglary_ollama.py` used on this dataset?
**Answer:** ❌ **No** - This is raw baseline data before any classification

**Question:** Is it needed?
**Answer:** ⚠️ **Possibly Yes** - Based on findings:

"""

    legacy_burglary_count = issues_df[issues_df['issue'] == 'Legacy Burglary Classifications']['count'].sum()
    if legacy_burglary_count > 0:
        md += f"""- **{legacy_burglary_count:,} records** use legacy burglary classification `2C:18-2`
- These need to be enhanced to:
  - `Burglary - Auto - 2C:18-2`
  - `Burglary - Commercial - 2C: 18-2`
  - `Burglary - Residence - 2C: 18-2`

**Recommendation:** Integrate `classify_burglary_ollama.py` OR create manual mapping rules for these {legacy_burglary_count:,} cases.

"""
    else:
        md += """- ✅ No legacy burglary classifications found in this sample
- May still need to check older data (2019-2023)

"""

    md += """### Incident Code Validation

**Recommendation:** Flag unmapped incident codes for review:
- Any incident starting with `2C:` (NJ statute code) should be validated against reference mapping
- Create exception list for codes that don't map cleanly
- Escalate to admin team for manual classification

### TAPS/ESU Enhancement Status

"""

    generic_taps_count = issues_df[issues_df['issue'] == 'Generic TAPS Incidents']['count'].sum()
    if generic_taps_count > 0:
        md += f"""- **{generic_taps_count:,} records** use generic "Targeted Area Patrol"
- Should be enhanced to specific types:
  - TAPS - Business
  - TAPS - ESU - Business
  - TAPS - ESU - Medical Facility
  - TAPS - ESU - Park
  - TAPS - ESU - Parking Garage
  - TAPS - ESU - Religious Facility
  - TAPS - ESU - School
  - TAPS - Housing
  - (and other enhanced variants)

**Recommendation:** Review CAD notes or location context to properly classify these generic TAPS records.

"""
    else:
        md += """- ✅ No generic TAPS records found in this sample
- TAPS classification appears to be properly enhanced

"""

    md += """---

## 📈 Next Steps

1. **Apply Data Cleanup Pipeline**
   - Run incident type mapping
   - Apply FullAddress2 corrections
   - Backfill missing fields from RMS

2. **Re-run Quality Audit**
   - Compare before/after metrics
   - Validate that cleanup addressed major issues

3. **Establish Quality Baselines**
   - Set target thresholds for each field (e.g., <2% blank rate)
   - Create dashboard for ongoing monitoring

4. **Address Remaining Gaps**
   - Manual review of unfixable issues
   - Document exceptions and edge cases

---

**Report Generation Script:** `scripts/baseline_quality_audit.py`
**Can be rerun on:** Any CAD sample or full dataset

---

*Generated by CAD Data Quality Audit System*
*Hackensack Police Department - Data Engineering Team*
"""

    return md

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("=" * 80)
    print("CAD DATA BASELINE QUALITY AUDIT")
    print("=" * 80)
    print()

    # Load CAD sample
    print(f"Loading CAD sample from: {CAD_SAMPLE}")
    df = pd.read_csv(CAD_SAMPLE, encoding='utf-8-sig')
    total_records = len(df)
    print(f"  [OK] Loaded {total_records:,} records")
    print()

    # Generate baseline metrics
    print("Analyzing field-level quality...")
    baseline_metrics = generate_baseline_metrics(df)
    print("  [OK] Field analysis complete")
    print()

    # Identify top issues
    print("Identifying top data quality issues...")
    issues_df = identify_top_issues(df)
    print(f"  [OK] Identified {len(issues_df)} major issues")
    print()

    # Generate markdown report
    print("Generating markdown admin report...")
    md_report = generate_markdown_report(baseline_metrics, issues_df, total_records)

    # Save markdown report
    print(f"Saving markdown report to: {MD_REPORT}")
    with open(MD_REPORT, 'w', encoding='utf-8') as f:
        f.write(md_report)
    print("  [OK] Markdown report saved")
    print()

    # Save CSV report
    print(f"Saving CSV report to: {CSV_REPORT}")
    baseline_metrics.to_csv(CSV_REPORT, index=False, encoding='utf-8-sig')
    print("  [OK] CSV report saved")
    print()

    # Display summary
    print("=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    print(f"Total Records: {total_records:,}")
    print(f"Overall Quality Score: {100 - baseline_metrics['blank_percentage'].mean():.1f}%")
    print(f"Major Issues Identified: {len(issues_df)}")
    print()
    print("Reports generated:")
    print(f"  - Markdown: {MD_REPORT}")
    print(f"  - CSV: {CSV_REPORT}")
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
