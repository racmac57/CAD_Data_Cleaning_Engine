# Manual Data Quality Editing Checklist

**File to Edit:** `data/ESRI_CADExport/CAD_ESRI_Final_20251121.xlsx`  
**Total Records:** 702,436  
**Last Updated:** 2025-11-24

---

## 🔴 CRITICAL PRIORITY (Must Fix Before ESRI Submission)

### 1. Hour Field Format ❌ **CRITICAL**
- **Issue:** Hour field contains `HH:mm` format (e.g., "00:04") instead of `HH:00` format (e.g., "00:00")
- **Impact:** 689,467 records (98.2%)
- **Fix:** Round all Hour values to nearest hour bucket
- **Action:** Use automated script OR manually edit in Excel
- **File:** See `manual_corrections/hour_field_corrections.csv` for sample records
- **Status:** ⬜ Not Started

### 2. How Reported Standardization ❌ **CRITICAL**
- **Issue:** 806 records with invalid values, 729 records with null values
- **Invalid Values Found:**
  - `phone` → Should be `Phone`
  - `radio` → Should be `Radio`
  - `911` → Should be `9-1-1`
  - `self` → Should be `Self-Initiated`
  - `fax` → Should be `Fax`
  - `email` → Should be `eMail`
  - `walk-In` → Should be `Walk-In`
  - `other - See Notes` → Should be `Other - See Notes`
  - Various single characters/abbreviations
- **Valid Values (Case-Sensitive):**
  - `9-1-1`
  - `Walk-In`
  - `Phone`
  - `Self-Initiated`
  - `Radio`
  - `Teletype`
  - `Fax`
  - `Other - See Notes`
  - `eMail`
  - `Mail`
  - `Virtual Patrol`
  - `Canceled Call`
- **Action:** Edit `manual_corrections/how_reported_corrections.csv` with corrections
- **Status:** ⬜ Not Started

### 3. Disposition Null Values ❌ **CRITICAL**
- **Issue:** 18,582 records (2.65%) with null Disposition
- **Action:** Review records and populate Disposition field
- **Common Valid Disposition Values:**
  - `Complete`
  - `Assisted`
  - `See Report`
  - `Record Only`
  - `Advised`
  - `Tot - See Notes`
  - `Checked OK`
  - `Issued`
  - `Cancelled`
  - `See Oca# (In Notes)`
- **File:** Edit `manual_corrections/disposition_corrections.csv`
- **Status:** ⬜ Not Started

### 4. ReportNumberNew Invalid Formats ❌ **CRITICAL**
- **Issue:** 14 records with invalid case number formats
- **Valid Format:** `YY-XXXXXX[suffix]` (e.g., `25-000123`, `25-000123A`)
- **Invalid Examples Found:**
  - `10-16275` (should be `10-016275` - missing leading zeros)
  - `23-0698` (should be `23-000698`)
  - `24-00053` (should be `24-000053`)
  - `24-10672` (should be `24-010672`)
  - `5` (invalid - needs full format)
  - `c` (invalid)
  - `24-058314q` (invalid suffix format)
  - `24ol.-065242` (invalid characters)
  - `24-` (incomplete)
  - Records with newlines/quotes
- **Action:** Edit `manual_corrections/case_number_corrections.csv`
- **Status:** ⬜ Not Started

---

## 🟡 HIGH PRIORITY (Should Fix)

### 5. FullAddress2 Validation ⚠️
- **Issue:** 57,623 records missing full street type, 36 records with no street number, 4 generic text entries
- **Valid Formats:**
  - Standard: `[Number] [Street Name] [Street Type] , [City], [State] [ZIP]`
  - Intersection: `[Street1] & [Street2] , [City], [State] [ZIP]`
- **Common Issues:**
  - Missing street type words (e.g., "Avenue" vs "AVE")
  - Intersections with incomplete second street (e.g., "Central Avenue & ,")
  - Generic locations (e.g., "home &")
- **Action:** Review `manual_corrections/address_corrections.csv`
- **Status:** ⬜ Not Started

### 6. Grid/PDZone Null Values ⚠️
- **Issue:** 499,975 Grid nulls (71.2%), 506,089 PDZone nulls (72.1%)
- **Valid Grids:** E1, E2, E3, F1-F3, G1-G5, H1-H5, I1-I6
- **Valid PDZones:** 5, 6, 7, 8, 9, 9A
- **Action:** Backfill from address/geography if possible
- **Status:** ⬜ Not Started

---

## 🟢 MEDIUM PRIORITY (Nice to Have)

### 7. Officer Format Standardization ⚠️
- **Issue:** Only 28,306 records (4.03%) match strict format
- **Expected Format:** `RANK FirstName LastName BadgeNumber`
- **Example:** `P.O. Cristobal Lara-Nunez 341`
- **Action:** Low priority for ESRI submission
- **Status:** ⬜ Not Started

### 8. Case Number Duplicates Review ⚠️
- **Issue:** 282,241 duplicate case numbers
- **Note:** Duplicates are expected for:
  - Supplemental reports (e.g., `25-000123A`, `25-000123B`)
  - Backup calls (same case, multiple officers)
- **Action:** Verify duplicates are legitimate
- **Status:** ⬜ Not Started

---

## ✅ PASSED VALIDATION (No Action Needed)

- ✅ **Schema** - All 17 required columns present
- ✅ **Response_Type** - 99.55% coverage (exceeds 99% threshold)
- ✅ **Incident** - Only 271 null values (0.04%), well below 1% threshold
- ✅ **TimeOfCall** - All records have valid datetime format
- ✅ **Latitude/Longitude** - 100% null (expected - geocoding pending)

---

## How to Use This Checklist

1. **Start with Critical Priority items** (1-4)
2. **Open the corresponding CSV file** in `manual_corrections/` folder
3. **Add corrections** in the `Corrected_Value` column
4. **Save the CSV file**
5. **Run the apply_corrections.py script** to apply changes to the main file
6. **Check off items** as you complete them (change ⬜ to ✅)

---

## Progress Tracking

- **Critical Items Completed:** 0 / 4
- **High Priority Items Completed:** 0 / 2
- **Medium Priority Items Completed:** 0 / 2
- **Overall Progress:** 0%

---

## Notes

- Always backup the original file before making corrections
- Test corrections on a small sample before applying to full dataset
- Keep track of changes in the correction CSV files for audit purposes
- Re-run validation after applying corrections

