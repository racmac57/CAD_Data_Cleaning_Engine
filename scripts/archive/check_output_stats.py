#!/usr/bin/env python
"""Quick stats check for processed outputs."""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
POLISHED = BASE_DIR / "data" / "ESRI_CADExport" / "CAD_ESRI_POLISHED_20251219_131114.xlsx"

df = pd.read_excel(POLISHED)
print("POLISHED OUTPUT STATISTICS")
print("="*60)
print(f"Total rows: {len(df):,}")
print(f"Total columns: {len(df.columns)}")
print(f"\nNull Values:")
print(f"  latitude: {df['latitude'].isna().sum():,} ({df['latitude'].isna().sum()/len(df)*100:.1f}%)")
print(f"  longitude: {df['longitude'].isna().sum():,} ({df['longitude'].isna().sum()/len(df)*100:.1f}%)")
print(f"  ZoneCalc: {df['ZoneCalc'].isna().sum():,} ({df['ZoneCalc'].isna().sum()/len(df)*100:.1f}%)")
print(f"  FullAddress2: {df['FullAddress2'].isna().sum():,} ({df['FullAddress2'].isna().sum()/len(df)*100:.1f}%)")
print(f"  Incident: {df['Incident'].isna().sum():,} ({df['Incident'].isna().sum()/len(df)*100:.1f}%)")
print(f"\nColumn Structure:")
print(f"  Matches ESRI required order: {list(df.columns) == ['ReportNumberNew', 'Incident', 'How Reported', 'FullAddress2', 'Grid', 'ZoneCalc', 'Time of Call', 'cYear', 'cMonth', 'Hour_Calc', 'DayofWeek', 'Time Dispatched', 'Time Out', 'Time In', 'Time Spent', 'Time Response', 'Officer', 'Disposition', 'latitude', 'longitude']}")

