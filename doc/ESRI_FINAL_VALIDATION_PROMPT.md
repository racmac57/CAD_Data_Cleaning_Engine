# Claude Code Prompt: CAD ESRI Final Export Quality Validation

Use this prompt to validate the CAD ESRI final export file against the project standards defined in `CAD_Data_Cleaning_Engine.md`.

---

## Prompt Text

```
Please validate the CAD ESRI final export file against the standards defined in @CAD_Data_Cleaning_Engine.md.

**Input File:** `data/ESRI_CADExport/CAD_ESRI_Final_20251121.xlsx` (or specify the most recent version)

**Validation Requirements:**

1. **Schema Validation**
   - Verify all required ESRI columns are present: TimeOfCall, cYear, cMonth, Hour, DayofWeek, Incident, Response_Type, How Reported, FullAddress2, Grid, PDZone, Officer, Disposition, ReportNumberNew, Latitude, Longitude, data_quality_flag
   - Check for any unexpected columns
   - Verify data types match specifications

2. **TimeOfCall Validation**
   - Format must be: `MM/dd/yyyy HH:mm:ss`
   - No null values allowed
   - Verify cYear, cMonth, Hour, DayofWeek are correctly derived from TimeOfCall
   - cYear: integer format (yyyy)
   - cMonth: full month name (January, February, etc.)
   - Hour: text format `HH:00` (e.g., `14:00`)
   - DayofWeek: full weekday name (Monday through Sunday)

3. **Response_Type Validation**
   - Must be one of: Emergency, Urgent, Routine, or Administrative
   - Coverage must be >= 99% (no nulls or invalid values)
   - Report distribution percentages

4. **How Reported Validation**
   - Must match exactly one of these values (case-sensitive):
     * 9-1-1
     * Walk-In
     * Phone
     * Self-Initiated
     * Radio
     * Teletype
     * Fax
     * Other - See Notes
     * eMail
     * Mail
     * Virtual Patrol
     * Canceled Call
   - No null values allowed
   - Report count of invalid values

5. **FullAddress2 Validation**
   - Must follow one of two valid formats:
     a) **Standard Address:** `[Street number] [Street name] [Street type] , [City], [State] [ZIP]`
        - Example: `123 MAIN STREET, HACKENSACK, NJ 07601`
        - Must start with a number
        - Street type must be full word (STREET, AVENUE, ROAD, DRIVE, COURT, LANE, etc.)
     b) **Intersection:** `[Street1] & [Street2] , [City], [State] [ZIP]`
        - Example: `HUDSON STREET & MOONACHIE ROAD, HACKENSACK, NJ 07601`
        - Must use single `&` separator
        - Both streets must have full street type words
   - Invalid formats to flag:
     * Street name with no number (non-intersection)
     * Street name with no street type word
     * City and state only
     * PO BOX entries
     * Generic text (VARIOUS, UNKNOWN, REAR LOT, PARKING GARAGE, HOME, etc.)
   - Report count of invalid addresses and sample invalid records

6. **ReportNumberNew Validation**
   - Format: `YY-XXXXXX[suffix]` where:
     * YY = last two digits of calendar year
     * XXXXXX = six digit, zero-padded sequence number
     * [suffix] = optional single letter for supplements (A, B, C, etc.)
   - Examples: `25-000123`, `25-000123A`, `25-000123B`
   - Verify sequence numbers are unique within each year
   - Check for proper zero-padding
   - Report any format violations

7. **Officer Validation**
   - Format: `RANK FirstName LastName BadgeNumber`
   - Example: `P.O. Cristobal Lara-Nunez 341`
   - Components:
     * Rank: uppercase with period (P.O., SPO., Sgt., Lt., Capt.)
     * FirstName: single given name, first letter uppercase
     * LastName: single surname (hyphenated allowed)
     * BadgeNumber: 2-4 digits, stored as text
   - Verify single spaces between components
   - Report count of invalid formats and sample records

8. **Disposition Validation**
   - No null values allowed
   - Check for common valid values: COMPLETE, ADVISED, ARREST, UNFOUNDED, CANCELLED, GOA, UTL, SEE REPORT, REFERRED
   - Report null count and distribution of values

9. **Grid and PDZone Validation**
   - Grid: Should match valid Beat values (E1, E2, E3, F1-F3, G1-G5, H1-H5, I1-I6)
   - PDZone: Should be one of: 5, 6, 7, 8, 9, 9A
   - Verify Grid to PDZone mapping matches the defined Beat-to-PDZone mapping
   - Report invalid values

10. **Incident Validation**
    - Check for null values (should be minimal after RMS backfill)
    - Verify incident types are normalized (no case sensitivity duplicates)
    - Check for mojibake characters or encoding issues
    - Report null count and top unmapped incidents

11. **Latitude/Longitude Validation**
    - Should be numeric values
    - Valid ranges: Latitude (-90 to 90), Longitude (-180 to 180)
    - For Hackensack, NJ: approximately Lat 40.88, Lon -74.04
    - Report count of null coordinates and out-of-range values

12. **Data Quality Flags**
    - Check data_quality_flag column for any flagged records
    - Report distribution of flag values
    - Identify records needing manual review

**Output Requirements:**

Generate a comprehensive validation report in markdown format with:
- Executive summary (pass/fail status)
- Detailed findings for each validation category
- Counts and percentages for each check
- Sample records for any violations
- Recommendations for fixes
- Overall data quality score

Save the report to: `data/02_reports/esri_final_validation_[timestamp].md`

Also generate CSV files for:
- Invalid FullAddress2 records: `data/02_reports/invalid_addresses_[timestamp].csv`
- Invalid Officer formats: `data/02_reports/invalid_officers_[timestamp].csv`
- Invalid ReportNumberNew formats: `data/02_reports/invalid_case_numbers_[timestamp].csv`
- Records with null critical fields: `data/02_reports/null_critical_fields_[timestamp].csv`
```

---

## Usage Instructions

1. Open the CAD ESRI final export file in your workspace
2. Ensure the `CAD_Data_Cleaning_Engine.md` standards document is accessible
3. Copy the prompt text above and provide it to Claude Code
4. Claude will generate a comprehensive validation report and CSV files for review
5. Review the findings and address any critical issues before ESRI submission

## Expected Outputs

- **Validation Report:** `data/02_reports/esri_final_validation_[timestamp].md`
- **Invalid Addresses:** `data/02_reports/invalid_addresses_[timestamp].csv`
- **Invalid Officers:** `data/02_reports/invalid_officers_[timestamp].csv`
- **Invalid Case Numbers:** `data/02_reports/invalid_case_numbers_[timestamp].csv`
- **Null Critical Fields:** `data/02_reports/null_critical_fields_[timestamp].csv`

## Quality Thresholds

Based on the deployment report, acceptable thresholds:
- **Response_Type Coverage:** >= 99%
- **Data Quality Score:** >= 95%
- **Critical Field Nulls:** < 1% (Incident, How Reported, Disposition)
- **Address Validity:** >= 90% (some generic locations acceptable)

