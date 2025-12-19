# CAD Call Type Normalization & Mapping Project

## Executive Summary

The CAD system exports incident types with inconsistent capitalization, spacing, and formatting (about 505 unique variants). This creates reporting errors and blocks accurate trend analysis.
This project standardizes incident types and related fields for all CAD exports from 2019 to present.
The cleaned dataset will feed an ESRI Crime Reduction dashboard, updated daily from the CAD provider.

---

## Project Goals

### Primary objectives

* [ ] Create master incident type mapping file `CallType_Master_Mapping.csv`
* [ ] Normalize 505+ raw CAD incident variants to about 400 standard types
* [ ] Ensure 100% Response Type coverage (Emergency / Routine / Administrative)
* [ ] Backfill historical CAD data (2019–present) with normalized incident types
* [ ] Create master “How Reported” mapping
* [ ] Ensure Disposition has no missing values
* [ ] Ensure “How Reported” is populated for every record and matches `how_reported.csv` values:

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
* [ ] Ensure cleaned data matches the schema used in the Google Sheets crime dashboard schema
* [ ] Implement the `ReportNumberNew` case / report number logic
* [ ] Enforce FullAddress2 formatting rules for addresses and intersections
* [ ] Align GRID, Beat, and PDZone to accurate patrol geography
* [ ] Prepare data for geocoding with the NJ Geocode service and store latitude / longitude

---

## Core Business Logic

### Case number logic (`ReportNumberNew`)

**Base format**

Pattern:
`YY-XXXXXX[suffix]`

* `YY` = last two digits of calendar year
* `XXXXXX` = six digit, zero padded sequence number
* `[suffix]` = optional single letter for supplements

**Examples**

* New case: `25-000123`
* First supplement: `25-000123A`
* Second supplement: `25-000123B`

#### 1. New case reports

Inputs:

* `report_date`
* `report_type = "NEW"`

Rules:

* Derive year from `report_date`
* Take last two digits of year for `YY`
* Look up next available sequence number for that `YY`
* Pad sequence number to six digits
* Build case number as
  `YY + "-" + sequence_number_six_digits`

Example:
First case of 2025 becomes `25-000001`.

#### 2. Supplemental reports

Inputs:

* `report_date`
* `report_type = "SUPPLEMENT"`
* `original_case_number`

Rules:

* Use original case number as base
  Example base: `25-000123`
* Find all existing supplements for that base
  Example: `25-000123A`, `25-000123B`
* Determine next suffix letter:

  * No prior supplements: `A`
  * Existing `A`: next `B`
  * Existing `A` and `B`: next `C`
* Final supplemental case number:
  `BaseNumber + NextLetter`
  Example: `25-000123C`

#### 3. Year handling

* Sequence restarts at `000001` on January 1 for each year
* Sequence numbers stay unique within each year

Example: `25-000123` and `25-000124` are two different 2025 cases.

#### 4. Summary logic for implementation

Inputs:

* `report_date`
* `report_type` (`NEW` or `SUPPLEMENT`)
* `original_case_number` (only for `SUPPLEMENT`)

Process (high level):

* Compute `YY = report_date.year % 100`
* If `report_type = "NEW"`:

  * Get next sequence number for `YY`
  * Zero pad to six digits
  * `CaseNumber = f"{YY:02d}-{seq:06d}"`
* If `report_type = "SUPPLEMENT"`:

  * `BaseNumber` = original case number without trailing letter
  * Look up existing supplements with `BaseNumber` prefix and trailing letter
  * Order suffix letters
  * Pick next letter
  * `CaseNumber = BaseNumber + NextLetter`

---

### Location logic (`FullAddress2`)

`FullAddress2` supports two valid formats: standard address and intersection.

#### 1. Standard address format

Pattern:

`[Street number] [Street name] [Street type] , [City], [State] [ZIP]`

Examples:

* `123 MAIN STREET, HACKENSACK, NJ 07601`
* `45 RIVER AVENUE APT 2B, HACKENSACK, NJ 07601`

Rules:

* Starts with a number
* Then street name plus full street type word

  * Examples: STREET, AVENUE, ROAD, DRIVE, COURT, LANE
* Optional apartment or unit info
* Ends with city, two-letter state code, and five digit ZIP

#### 2. Intersection format

Two full street names with full street type, joined by `&`, followed by city, state, ZIP.

Examples:

* `HUDSON STREET & MOONACHIE ROAD, HACKENSACK, NJ 07601`
* `MAIN STREET & RIVER AVENUE, HACKENSACK, NJ 07601`

Rules:

* First street: full name with full street type word
* A single `&`
* Second street: full name with full street type word
* Then city, state, ZIP

#### 3. Valid vs invalid addresses

Treat a record as a valid full address only when location matches one of the two forms above.

Do not treat as valid:

* Street name with no number
* Street name with no street type word
* City and state only
* PO BOX entries
* Highway descriptions with no clear cross street
* Generic text such as VARIOUS, UNKNOWN, REAR LOT, PARKING GARAGE, HOME, or similar

---

### GRID, Beat, and PDZone

A GRID defines the primary geographic area of responsibility for a patrol officer.
A GRID subdivides a larger PD Zone (Post).
The CAD system matches a 9-1-1 call location to a GRID to select the assigned officer.
GRIDs follow call volume and natural boundaries, so geographic accuracy matters for operations.

Beat to PDZone mapping:

```text
Beat    PDZone
E1      5
E2      5
E3      5
F1      6
F2      6
F3      6
G1      7
G2      7
G3      7
G4      7
G5      7
H1      8
H2      8
H3      8
H4      8
H5      8
I1      9
I2      9
I3      9
I4      9A
I5      9
I6      9
```

Post geography (patrol posts):

| Post_ID | Post_Name  | Notes                                                                                                                                                                                                  |
| :------ | :--------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1       | Post 1     | Little Ferry and South Hackensack on the south to Susquehanna Railroad on the north. New Jersey Transit Railroad on the west to Hackensack River on the east.                                          |
| 2       | Post 2     | Hasbrouck Heights and Lodi on the south to Susquehanna Railroad on the north. New Jersey Transit Railroad on the east to Maywood and Lodi on the west.                                                 |
| 3       | Post 3     | Susquehanna Railroad on the south to Anderson Street on the north. Hackensack River on the east to Maywood on the west.                                                                                |
| 4       | Post 4     | Anderson Street on the south to River Edge and Paramus on the north. Hackensack River on the east to Maywood and Paramus on the west.                                                                  |
| 5       | Post 5     | Little Ferry and South Hackensack on the south to Essex Street on the north. Hackensack River on the east to South State Street on the west.                                                           |
| 6       | Post 6     | South Hackensack, Hasbrouck Heights and Lodi on the south to Essex Street on the north. South State Street on the east to Lodi on the west.                                                            |
| 7       | Post 7     | Essex Street on the south to Central Avenue on the north, following State Street to Susquehanna Railroad and then east to the Hackensack River. Hackensack River on the east to Maywood on the west.   |
| 8       | Post 8     | Central Avenue on the south, following State Street to the Susquehanna Railroad and east to the Hackensack River to Anderson Street on the north. Hackensack River on the east to Maywood on the west. |
| 9       | Post 9     | Anderson Street on the south to Paramus and River Edge on the north. Hackensack River on the east to Maywood and Paramus on the west.                                                                  |
| 7&8     | Post 7&8   | Essex Street on the south and Anderson Street on the north. Hackensack River on the east and city line on the west.                                                                                    |
| 1&2     | Post 1&2   | Susquehanna Railroad on the north and city line on the south. Hackensack River on the east and city line on the west.                                                                                  |
| 3&4     | Post 3&4   | Susquehanna Railroad on the south and city line on the north. Hackensack River on the east and city line on the west.                                                                                  |
| 13-16   | Post 13-16 | Essex Street on the south to Anderson Street on the north. State Street on the west to the Hackensack River on the east.                                                                               |
| 19-22   | Post 19-22 | Essex Street on the south and Clinton Place on the north. First Street and Linden Street on the east and Maywood border on the west.                                                                   |
| 10-18   | Post 10-18 | North: Anderson Street. South: Essex Street. East: Union Street. West: First Street to American Legion Drive to Second Street to Passaic Street to Clarendon Place.                                    |
| 10      | Post 10    | North: Anderson Street. South: Susquehanna Railroad. East: Union Street. West: Second Street to Passaic Street to Clarendon Place.                                                                     |
| 11      | Post 11    | South Hackensack and Little Ferry on the south, Route 80 on the north, South State Street and South Hackensack on the west, South River Street on the east.                                            |
| 12      | Post 12    | Route 80 on the south, Essex Street on the north, South State Street and South Hackensack on the west, South River Street on the east.                                                                 |
| 13      | Post 13    | Essex Street to Demarest Place, State Street to Hackensack River.                                                                                                                                      |
| 14      | Post 14    | Demarest Place to Salem Street, State Street to Hackensack River.                                                                                                                                      |
| 15      | Post 15    | Salem Street to Passaic Street, State Street to Hackensack River.                                                                                                                                      |
| 16      | Post 16    | Passaic Street to Anderson Street, Linden Street to Hackensack River.                                                                                                                                  |
| 17      | Post 17    | Passaic Street on the south and Maple Avenue on the north, Linden Street on the west and Main Street on the east.                                                                                      |
| 18      | Post 18    | North: Central Avenue. South: Essex Street. East: Union Street. West: First Street.                                                                                                                    |
| 19      | Post 19    | Essex Street on the south and American Legion Drive on the north, Summit Avenue on the west and First Street on the east.                                                                              |
| 20      | Post 20    | Passaic Street on the south and Clinton Place on the north, Prospect Avenue on the west and Linden Street on the east.                                                                                 |
| 21      | Post 21    | Passaic Street on the south and Clinton Place on the north, Linden Street on the west and State Street, Union Street, and Pangborn Place on the east.                                                  |
| 22      | Post 22    | Essex Street on the south and Beech Street and Buckingham Drive on the north, Maywood border on the west and Summit Avenue on the east.                                                                |
| 23      | Post 23    | Essex Street on the north and Mary Street on the south, Polifly Road on the east and South Summit Avenue on the west.                                                                                  |

---

## CAD Field Definitions

These definitions describe the cleaned schema for the ESRI dashboard model.

#### TimeOfCall

* Type: Datetime
* Format: `MM/dd/yyyy HH:mm:ss`
* Meaning: Original CAD date and time when the call was created or received.

#### cYear

* Type: Integer
* Format: `yyyy`
* Meaning: Calendar year extracted from `TimeOfCall` for grouping and filters.

#### cMonth

* Type: Text
* Format: Full month name (January, February, etc.)
* Meaning: Month label derived from `TimeOfCall`.

#### Hour_Calc

* Type: Integer
* Format: 0–23
* Meaning: Hour of day in 24-hour format from `TimeOfCall`, for numeric analysis.

#### Hour

* Type: Text
* Format: `HH:00` (for example `14:00`)
* Meaning: Hour bucket label for charts.

#### DayofWeek

* Type: Text
* Format: Full weekday name
* Meaning: Day name derived from `TimeOfCall` (Monday through Sunday).

#### TimeDispatched

* Type: Datetime
* Format: `MM/dd/yyyy HH:mm:ss`
* Meaning: Date and time when units were dispatched to the call.

#### TimeOut

* Type: Datetime
* Format: `MM/dd/yyyy HH:mm:ss`
* Meaning: Date and time when the primary unit went en route or arrived.

#### TimeIn

* Type: Datetime
* Format: `MM/dd/yyyy HH:mm:ss`
* Meaning: Date and time when the primary unit cleared the call and returned to service.

#### TimeSpent

* Type: Duration
* Format: `HH:mm` (hours:minutes)
* Meaning: Elapsed time for call handling or on scene time.
* Logic: `TimeSpent = TimeIn - TimeOut`.

#### TimeResponse

* Type: Duration
* Format: `HH:mm` (hours:minutes)
* Meaning: Elapsed time from dispatch to arrival or en route.
* Logic: `TimeResponse = TimeOut - TimeDispatched`.

#### Officer

Physical type:

* Text string

Stored format:

`RANK FirstName LastName BadgeNumber`

Examples:

* `P.O. Cristobal Lara-Nunez 341`
* `SPO. Bobby Rivera 826`
* `P.O. Luis Furcal 157`
* `P.O. Benjamin Estrada 350`
* `P.O. Aaron Rios 337`
* `P.O. Raymond Donnerstag 333`

Logical parts:

* `Rank`

  * Text, examples: `P.O.`, `SPO.`, `Sgt.`, `Lt.`, `Capt.`
  * Uppercase with period, single space after
* `FirstName`

  * Single given name, first letter uppercase, remaining letters lowercase
* `LastName`

  * Single surname, hyphenated or multi-part allowed
  * Examples: `Lara-Nunez`, `Donnerstag`, `Estrada`
* `BadgeNumber`

  * Integer stored as text
  * Two to four digits, no leading zeros in samples

Recommended standardization:

* Single space between Rank, FirstName, LastName, BadgeNumber
* No leading or trailing spaces
* Rank uppercase with period
* BadgeNumber stored as text for joins, treated as integer for analysis

Suggested regex:

```text
^([A-Z]{2,4}\.)\s+([A-Z][a-z]+)\s+([A-Za-z-]+(?:\s[A-Za-z-]+)*)\s+(\d{2,4})$
```

Groups map to Rank, FirstName, LastName, BadgeNumber.
No middle name or middle initial in this schema.

#### Disposition

* Type: Text
* Format: Free text code or phrase
* Examples: `See Report`, `Record Only`, `Dispersed`, `Unable to Locate`
* Meaning: Final outcome or handling of the call.

#### Latitude and Longitude

* Latitude / Longitude stored as numeric fields
* Plan: use `NJ_Geocode` service via ArcGIS Pro / ArcPy to geocode valid `FullAddress2` records
* Goal: fill or improve coordinates for all valid address and intersection records

---

## Deliverables

### Final outputs

1. **CallType_Master_Mapping.csv**

   * Columns:
     `Raw_Value`, `Incident_Norm`, `Category_Type`, `Response_Type`, `Statute`, `Status`
   * All 505+ variants mapped
   * No blanks in `Incident_Norm` or `Response_Type`

2. **Review CSVs** (from `build_calltype_master.py`)

   * `duplicates_review.csv` – manual merge decisions
   * `unmapped_incidents.csv` – records that need mapping
   * `anomalies.csv` – formatting problems to fix
   * `mapping_changes.csv` – before / after audit trail

3. **Validation reports**

   * JSON reports with data quality scores
   * Sample CSVs for ESRI and Power BI testing

4. **Documentation**

   * This markdown outline
   * Mapping rules reference sheet
   * Change log for master mapping updates

---

## Open Questions and Decisions

### Technical decisions

1. Fuzzy matching threshold

   * Example recommendation:

     * Auto-approve: score ≥ 90
     * Manual review queue: 70–89

2. Statute handling

   * Keep separate vs merged forms, for example:

     * `Theft`
     * `Theft - 2C:20-3`

3. Historical backfill strategy

   * Apply mapping to 2019–present in one run
   * Or process in staged windows (per year or per quarter)

### Data quality decisions

1. Handling unmapped incidents

   Options:

   * Map to `Unknown` category and track count
   * Block export until mapping exists
   * Flag in a queue for manual review

2. Category_Type taxonomy

   Examples:

   * Part I Crime, Part II Crime, Service, Administrative
   * Or a custom grouping that matches local practice

---

## Current Blockers and Issues

### Immediate blockers

1. **CallType_Categories.csv contains 505 raw variants**

   * Impact: Master mapping incomplete
   * Needed: Normalize all variants and align to `Incident_Norm` values
   * Priority: High

2. **Hardcoded file paths in scripts**

   * Impact: Scripts fail on different machines or environments
   * Needed: Central configuration (`config_enhanced.json` or similar)
   * Priority: Medium

3. **Incident column gaps**

   * 249 records with null `Incident` values
   * Need mapping between CAD `ReportNumberNew` and RMS `Case Number`
   * Cross-check CAD `Officer` with RMS `Officer of Record`
   * Use `FullAddress2` vs RMS `FullAddress` when helpful
   * Goal: backfill `Incident` from RMS `Incident Type_1`

4. **Service of TRO / FRO aggregation**

   * 1816 records with combined values such as `Service of TRO / FRO` or `Violation: TRO / FRO 2C:25-31`
   * New raw call type export separates these into:

     * `Service of TRO`, `Service of FRO`, `Violation: TRO`, `Violation: FRO`
   * Open problem: decide how to split historical combined records and how to reflect that in reports

---

## Timeline and Milestones

* [ ] **Phase 1: Data assessment**

  * Catalog all current data sources
  * Document quality issues
  * Finalize normalization rules

* [ ] **Phase 2: Master build**

  * Generate normalized mappings
  * Review and approve suggested matches
  * Build `CallType_Master_Mapping.csv`

* [ ] **Phase 3: Validation**

  * Run validation scripts on historical data
  * Generate sample exports
  * QA in Power BI and ESRI

* [ ] **Phase 4: Production**

  * Deploy to CAD export pipeline
  * Monitor for new unmapped incidents
  * Run quarterly master review

---

## File Locations and Paths

### Reference files

* Call type reference:
  `C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\Classifications\CallTypes\CallType_Categories.csv`

* Historical CAD exports:
  `C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine\data\01_raw\2019_2025_11_14_cad.xlsx`

* Geographic data:
  `C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\GeographicData`

* Legal codes:
  `C:\Users\carucci_r\OneDrive - City of Hackensack\09_Reference\LegalCodes`

### Output directories

* Master mapping:
  `/ref/CallType_Master_Mapping.csv`

* Review files:
  `/ref/duplicates_review.csv`
  `/ref/unmapped_incidents.csv`
  `/ref/anomalies.csv`

* Validation reports:
  `/data/02_reports/cad_validation/`

---

## Current State Assessment

### Data sources

Project directory:
`C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine`

Key file:

* `2019_2025_11_14_cad.xlsx` – current combined CAD export

### Known data quality issues

1. **Case sensitivity duplicates**

   * Example: `Alarm - fire` vs `Alarm - Fire` vs `alarm - Fire`
   * Impact: Inflated unique counts and broken grouping

2. **Excel date conversion artifacts**

   * Example: `9-1-1` misread as date
   * Impact: Emergency calls misclassified
   * Fix: handled in `normalize_how_reported_value()`

3. **Statute formatting**

   * Example: `Theft 2C:20-3`, `Theft - 2C:20-3`, `Theft 2c:20 - 3`
   * Impact: Duplicate UCR codes and inconsistent reporting

4. **Mojibake (encoding)**

   * Example: `Motor Vehicle Crash â€" Pedestrian`
   * Impact: Broken matching logic and unprofessional labels
   * Fix: handled in `fix_mojibake()`

5. **Incident column nulls**

   * 249 records with null `Incident`
   * Plan: backfill using RMS mapping described in blockers section

6. **Combined TRO/FRO values**

   * 1816 records with combined TRO/FRO values
   * Needs a policy decision and possibly separate derived fields

---

## Normalization Rules

### 1. Text cleaning

* [ ] Trim leading, trailing, and extra internal spaces
* [ ] Remove zero-width and non-breaking spaces
* [ ] Replace em and en dashes with a simple hyphen
* [ ] Fix mojibake encoding artifacts

### 2. Capitalization standards

General rules:

* General text: Title Case

  * Example: `Motor Vehicle Crash`
* Abbreviations: all caps

  * Examples: `ABC`, `ESU`, `ERPO`, `FRO`, `TRO`, `TERPO`, `EMS`, `DOA`
* Legal codes: preserve correct format

  * Example: `9-1-1` stays `9-1-1`

Parentheticals:

* Use Title Case inside parentheses

  * Example: `(Backup)`

---

## Notes and Context

### Why this project matters

The cleaned CAD dataset will drive the ESRI Crime Problem dashboard.
Current dashboards rely on non-standardized fields and incomplete data, which reduces trust in the numbers.

Accurate incident classification supports:

* FBI UCR reporting
* Strategic crime reduction work (SCRPA cycles)
* Patrol resource allocation
* Grant applications that require clean supporting data
* Executive dashboards and CompStat style meetings
* Tactical and strategic deployment of personnel and tools

### Historical context

* For several years, many CAD fields allowed free text in dropdowns. Data from 2025 looks cleaner, but prior years show large variation.
* Previous cleanups supported specific, one-off requests, not a full historical normalization.
* This project standardizes several hundred thousand CAD records to support long-term reporting and mapping.

---

## Appendix

### Sample data issues

**Example 1: Em dash**

`Motor Vehicle Crash – Hit and Run`
Corrected form: `Motor Vehicle Crash - Hit and Run`

**Example 2: Inconsistent Incident values**

Incident should be `Theft - 2C:20-3` but appears as:

* `Theft  2C:20-3`
* `THEFT 2C:20-3`

**Example 3: Inconsistent casing**

Correct value: `Group`

Examples:

* `Group`
* `group`

**Example 4: Address problems**

Examples of issues:

* Wrong separator: `" / "` instead of `" & "`
* Missing street number or missing cross street
* Generic locations such as `home, Hackensack, NJ, 07601`
* Park names with no valid address
* Mis-spelled or abbreviated street types (`St` vs `Street`)
* Double entry for first street (for example `Central Avenue & Central Ave / First St`)

**Example 5: Inconsistent alarm values**

* `Alarm - fire`
* `Alarm - Fire`
* `alarm - Burglar`

Target: one normalized form per logical incident type.

### Reference links

* FBI UCR Handbook
* NJSP UCR Quick Reference Guide
* Project GitHub repo: `https://github.com/racmac57/CAD_Data_Cleaning_Engine.git`

---

## How to use this outline with AI tools

* Paste this markdown into the Notion page for `CAD_Data_Cleaning_Engine`.
* When working with an AI assistant:

  * Point to this outline as the source of project rules.
  * Ask for code or checks that respect the case number logic, address rules, and field definitions.
  * Use the “Open Questions and Decisions” section to drive focused help.

Source reference for this outline 
