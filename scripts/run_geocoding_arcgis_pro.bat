@echo off
REM Quick script to run geocoding using ArcGIS Pro locator
REM Uses the "NJ_Geocode" locator registered in ArcGIS Pro

cd "C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine"

python scripts/geocode_nj_locator.py ^
    --input "data\ESRI_CADExport\CAD_ESRI_POLISHED_20251219_131114.xlsx" ^
    --locator "NJ_Geocode" ^
    --use-web-service ^
    --format excel ^
    --batch-size 1000

pause

