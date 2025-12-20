# Quick Start: Enhanced Pipeline

## Windows Command Prompt

### Option 1: Use the Batch File (Easiest)

```cmd
cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"
scripts\run_enhanced_pipeline.bat
```

Or with custom paths:
```cmd
scripts\run_enhanced_pipeline.bat "data\01_raw\19_to_25_12_18_CAD_Data.xlsx" "data\ESRI_CADExport"
```

### Option 2: Single Line Command

From the **project root** directory:

```cmd
python scripts\master_pipeline.py --input "data\01_raw\19_to_25_12_18_CAD_Data.xlsx" --output-dir "data\ESRI_CADExport" --base-filename "CAD_ESRI" --format excel
```

### Option 3: Multi-Line Command (Windows CMD)

From the **project root** directory:

```cmd
python scripts\master_pipeline.py ^
    --input "data\01_raw\19_to_25_12_18_CAD_Data.xlsx" ^
    --output-dir "data\ESRI_CADExport" ^
    --base-filename "CAD_ESRI" ^
    --format excel
```

**Note**: In Windows CMD, use `^` for line continuation, not `\`

## Common Mistakes

### ❌ Wrong: Running from scripts directory
```cmd
cd scripts
python scripts\master_pipeline.py  # WRONG - scripts\scripts\master_pipeline.py doesn't exist
```

### ✅ Correct: Run from project root
```cmd
cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"
python scripts\master_pipeline.py --input "data\01_raw\19_to_25_12_18_CAD_Data.xlsx" ...
```

### ❌ Wrong: Using backslash for line continuation
```cmd
python scripts\master_pipeline.py \
    --input "..."  # WRONG - \ doesn't work in Windows CMD
```

### ✅ Correct: Use caret for line continuation
```cmd
python scripts\master_pipeline.py ^
    --input "..."  # CORRECT - ^ works in Windows CMD
```

## PowerShell

If you're using PowerShell instead of CMD:

```powershell
cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"
python scripts\master_pipeline.py `
    --input "data\01_raw\19_to_25_12_18_CAD_Data.xlsx" `
    --output-dir "data\ESRI_CADExport" `
    --base-filename "CAD_ESRI" `
    --format excel
```

**Note**: PowerShell uses backtick `` ` `` for line continuation

## Verify It's Working

After running, you should see:
- ✅ Output files in `data\ESRI_CADExport\`
- ✅ Null value reports in `data\02_reports\data_quality\`
- ✅ Processing summary markdown file

## Troubleshooting

### "No such file or directory"
- Make sure you're in the **project root** directory
- Check that the input file path is correct (use `dir` to verify)

### "Module not found"
- Make sure you're in the project root
- Check that all required Python packages are installed: `pip install -r requirements.txt`

### "Permission denied"
- Close Excel if the output file is open
- Check file permissions

