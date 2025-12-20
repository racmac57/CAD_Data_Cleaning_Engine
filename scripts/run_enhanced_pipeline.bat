@echo off
REM Enhanced ETL Pipeline Runner
REM Usage: run_enhanced_pipeline.bat [input_file] [output_dir]

setlocal

REM Set default paths
if "%~1"=="" (
    set INPUT_FILE=data\01_raw\19_to_25_12_18_CAD_Data.xlsx
) else (
    set INPUT_FILE=%~1
)

if "%~2"=="" (
    set OUTPUT_DIR=data\ESRI_CADExport
) else (
    set OUTPUT_DIR=%~2
)

REM Change to project root directory
cd /d "%~dp0\.."

REM Run the pipeline
python scripts\master_pipeline.py ^
    --input "%INPUT_FILE%" ^
    --output-dir "%OUTPUT_DIR%" ^
    --base-filename "CAD_ESRI" ^
    --format excel

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Pipeline completed successfully!
    echo ========================================
    echo.
    echo Check outputs in: %OUTPUT_DIR%
    echo Check reports in: data\02_reports\data_quality\
) else (
    echo.
    echo ========================================
    echo Pipeline failed with error code: %ERRORLEVEL%
    echo ========================================
)

endlocal

