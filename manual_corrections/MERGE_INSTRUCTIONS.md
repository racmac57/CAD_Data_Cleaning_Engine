# How to Merge Two Sheets in disposition_corrections Excel File

## Quick Answer: **YES, you should merge them into a single table**

The `apply_manual_corrections.py` script expects a single CSV file, not an Excel file with multiple sheets.

## Method 1: Automatic Merge (Recommended)

1. **Save your Excel file** as `disposition_corrections.xlsx` in the `manual_corrections` folder
2. **Run the merge script:**
   ```powershell
   python scripts/merge_disposition_corrections_sheets.py
   ```
3. The script will:
   - Read both sheets
   - Combine them
   - Remove duplicates (based on ReportNumberNew)
   - Save as a single CSV file

## Method 2: Manual Merge in Excel

### Step-by-Step Instructions:

1. **Open your Excel file** with both sheets (Table1 and remaining_records)

2. **Go to the "remaining_records" sheet**
   - Select all data (press `Ctrl+A`)
   - Copy (press `Ctrl+C`)

3. **Go to the first sheet (Table1)**
   - Scroll to the bottom to find the last row with data
   - Click on the cell directly below the last row in the first column (ReportNumberNew)

4. **Paste the data**
   - Press `Ctrl+V` to paste

5. **Remove duplicates** (IMPORTANT - prevents data loss/duplication):
   - Select all data in the sheet (press `Ctrl+A`)
   - Go to **Data** tab → **Remove Duplicates**
   - In the dialog box:
     - ✅ Check only **"ReportNumberNew"** (uncheck all other columns)
     - This ensures if a ReportNumberNew appears in both sheets, we keep only one
   - Click **OK**
   - Excel will show how many duplicates were removed

6. **Save as CSV:**
   - Go to **File** → **Save As**
   - Choose location: `manual_corrections` folder
   - File name: `disposition_corrections.csv`
   - File type: **CSV (Comma delimited) (*.csv)**
   - Click **Save**
   - If Excel warns about losing formatting, click **Yes** (CSV doesn't support formatting)

7. **Verify the merge:**
   - Open the CSV file
   - Check that all records from both sheets are present
   - Verify no duplicate ReportNumberNew values

## What the Script Does (Automatic Method)

The merge script:
- ✅ Reads both sheets
- ✅ Combines them into one DataFrame
- ✅ Removes duplicates based on ReportNumberNew (keeps first occurrence)
- ✅ Preserves all columns
- ✅ Shows statistics before/after merge
- ✅ Saves as CSV

## Safety Features

- **Duplicate Detection**: The script checks for duplicate ReportNumberNew values
- **Column Alignment**: If columns don't match, it aligns them automatically
- **Data Preservation**: All records from both sheets are included
- **Backup**: The original Excel file remains unchanged

## After Merging

Once merged, you can:
1. Run `python scripts/apply_manual_corrections.py` to apply corrections to the ESRI file
2. Delete or archive the Excel file (optional)
3. Continue working with the single CSV file

