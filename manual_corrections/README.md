# Manual Corrections Guide

This folder contains CSV files for manual data quality corrections. Follow the checklist in `doc/MANUAL_EDITING_CHECKLIST.md` for priority order.

---

## Files in This Folder

### 1. `how_reported_corrections.csv` 🔴 **CRITICAL**
- **Issue:** 806 invalid values + 729 null values
- **Columns:**
  - `ReportNumberNew` - Case number (key field)
  - `TimeOfCall` - For reference
  - `How Reported` - Current (incorrect) value
  - `Incident` - For context
  - `Corrected_Value` - **FILL THIS IN** with valid value
  - `Notes` - Optional notes
  - `Issue_Type` - Invalid Value or Null Value
- **Valid Values (Case-Sensitive):**
  - `9-1-1` (for "911", "phone" when emergency)
  - `Phone` (for "phone", "PHONE")
  - `Radio` (for "radio", "RADIO", "r", "rs")
  - `Self-Initiated` (for "self", "SI")
  - `Fax` (for "fax")
  - `eMail` (for "email", "EMAIL")
  - `Walk-In` (for "walk-In")
  - `Other - See Notes` (for "other - See Notes")
  - `Teletype`, `Mail`, `Virtual Patrol`, `Canceled Call`
- **How to Fix:**
  1. Open in Excel
  2. Review each row
  3. Enter correct value in `Corrected_Value` column
  4. Save file

### 2. `disposition_corrections.csv` 🔴 **CRITICAL**
- **Issue:** 18,582 null Disposition values
- **Columns:**
  - `ReportNumberNew` - Case number (key field)
  - `TimeOfCall` - For reference
  - `Incident` - For context
  - `How Reported` - For context
  - `Disposition` - Current (null) value
  - `Corrected_Value` - **FILL THIS IN** with appropriate disposition
  - `Notes` - Optional notes
- **Common Valid Disposition Values:**
  - `Complete` - Most common (43.86%)
  - `Assisted` - Second most common (16.17%)
  - `See Report` - Third most common (11.42%)
  - `Record Only`, `Advised`, `Tot - See Notes`, `Checked OK`, `Issued`, `Cancelled`
- **Note:** This file contains 2,000 sample records. Total nulls: 18,582. You may need to process in batches.

### 3. `case_number_corrections.csv` 🔴 **CRITICAL**
- **Issue:** 14 records with invalid case number formats
- **Columns:**
  - `ReportNumberNew` - Current (incorrect) case number
  - `TimeOfCall` - For reference
  - `Incident` - For context
  - `Corrected_Value` - **FILL THIS IN** with corrected format
  - `Notes` - Optional notes
- **Valid Format:** `YY-XXXXXX[suffix]`
  - `YY` = 2-digit year (19, 20, 21, 22, 23, 24, 25)
  - `XXXXXX` = 6-digit zero-padded sequence
  - `[suffix]` = Optional letter (A, B, C, etc.) for supplements
- **Examples:**
  - `10-16275` → `10-016275` (add leading zeros)
  - `23-0698` → `23-000698` (add leading zeros)
  - `24-058314q` → `24-058314Q` (uppercase suffix)
  - `24ol.-065242` → `24-065242` (remove invalid chars)
  - `5` → Need to determine correct case number from context

### 4. `address_corrections.csv` 🟡 **HIGH PRIORITY**
- **Issue:** Addresses missing street types or with generic text
- **Columns:**
  - `ReportNumberNew` - Case number (key field)
  - `TimeOfCall` - For reference
  - `FullAddress2` - Current address
  - `Incident` - For context
  - `Corrected_Value` - **FILL THIS IN** with corrected address
  - `Issue_Type` - Type of issue
  - `Notes` - Optional notes
- **Valid Formats:**
  - Standard: `[Number] [Street Name] [Street Type] , [City], [State] [ZIP]`
  - Intersection: `[Street1] & [Street2] , [City], [State] [ZIP]`
- **Common Fixes:**
  - `Central Avenue & ,` → `Central Avenue & [Second Street] , Hackensack, NJ 07601`
  - `home & ,` → Need to determine actual location
  - Missing street type → Add full word (STREET, AVENUE, etc.)

### 5. `hour_field_corrections.csv` 🔴 **CRITICAL (Reference Only)**
- **Issue:** Hour field in `HH:mm` format instead of `HH:00`
- **Note:** This file shows examples. The fix will be applied automatically by the script.
- **Fix Logic:** Round to nearest hour (e.g., `00:04` → `00:00`, `14:35` → `14:00`)

### 6. `master_corrections_template.csv` 📋 **Template**
- Use this for any additional corrections not covered above
- **Columns:**
  - `ReportNumberNew` - Case number
  - `TimeOfCall` - For reference
  - `Field_Name` - Which field to correct
  - `Current_Value` - Current value
  - `Corrected_Value` - **FILL THIS IN**
  - `Issue_Type` - Type of issue
  - `Notes` - Optional notes
  - `Status` - Track progress (Not Started, In Progress, Complete)

---

## Workflow

### Step 1: Open Files in Excel
1. Open each CSV file in Excel
2. Review the data
3. Understand the issue type

### Step 2: Make Corrections
1. Fill in the `Corrected_Value` column for each record
2. Add notes if needed for future reference
3. Save each file after making corrections

### Step 3: Apply Corrections
Run the apply script:
```bash
python scripts/apply_manual_corrections.py
```

This will:
- Read all correction CSV files
- Apply corrections to the main ESRI export file
- Create a new corrected file: `CAD_ESRI_Final_YYYYMMDD_corrected.xlsx`

### Step 4: Validate
Re-run validation to verify corrections:
```bash
python scripts/esri_final_validation.py
```

---

## Tips

1. **Start with Critical Items:** Focus on How Reported, Disposition, and Case Numbers first
2. **Work in Batches:** For large files (like Disposition with 18K+ records), work in batches of 500-1000
3. **Use Find/Replace:** For common patterns (e.g., all "phone" → "Phone"), use Excel Find/Replace
4. **Backup:** Always backup original files before applying corrections
5. **Track Progress:** Use the checklist in `doc/MANUAL_EDITING_CHECKLIST.md` to track what's done

---

## Priority Order

1. ✅ Hour Field (automated - script will fix)
2. 🔴 How Reported (806 + 729 records)
3. 🔴 Disposition (18,582 records)
4. 🔴 Case Numbers (14 records - quick fix)
5. 🟡 Addresses (sample of 1,000 - can expand if needed)

---

## Questions?

Refer to:
- `doc/MANUAL_EDITING_CHECKLIST.md` - Detailed checklist
- `doc/ESRI_FINAL_VALIDATION_PROMPT.md` - Validation standards
- `ce8447de-121e-4977-be34-f386cbcec5f8_ExportBlock-bc992ba2-3ef5-4013-a83b-a3303cc341fd/CAD_Data_Cleaning_Engine.md` - Project standards

