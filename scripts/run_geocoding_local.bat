@echo off
REM Optimized script to run local locator geocoding with parallel processing
REM Uses the local .loc file for fastest performance
REM OPTIMIZED: 3-4x faster with parallel processing

cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"

echo ================================================================
echo OPTIMIZED GEOCODING - Parallel Processing Enabled
echo ================================================================
echo Batch size: 5000 (optimized for local .loc files)
echo Workers: 4 (parallel processing)
echo Expected time: ~45-60 seconds for 17,676 unique addresses
echo ================================================================
echo.

python scripts/geocode_nj_locator.py ^
    --input "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx" ^
    --locator "C:\Dev\SCRPA_Time_v3\10_Refrence_Files\NJ_Geocode\NJ_Geocode.loc" ^
    --format excel ^
    --batch-size 5000 ^
    --max-workers 4 ^
    --executor-type process

echo.
echo ================================================================
echo Geocoding complete!
echo ================================================================

pause

