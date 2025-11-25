import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Cleaning_Engine")
CAD_PATH = BASE / "data" / "ESRI_CADExport" / "CAD_ESRI_Final_20251117_v2.xlsx"
RMS_PATH = BASE / "data" / "rms" / "2019_2025_11_16_16_57_00_ALL_RMS_Export.xlsx"

# Paste your ReportNumberNew list here
case_numbers = [
    "19-053901", "19-054558", "19-054562",  # ...
]

cad = pd.read_excel(CAD_PATH, dtype=str)
rms = pd.read_excel(RMS_PATH, dtype=str)

rms_lookup = rms.set_index("Case Number")["Incident Type_1"]

rows = []
for case in case_numbers:
    cad_rows = cad[cad["ReportNumberNew"] == case]
    rms_incident = rms_lookup.get(case, "")
    rows.append({
        "ReportNumberNew": case,
        "CAD_Incident": "; ".join(cad_rows["Incident"].dropna().unique()) if not cad_rows.empty else "",
        "RMS_Incident_Type_1": rms_incident,
    })

out = pd.DataFrame(rows)
out.to_csv(BASE / "data" / "02_reports" / "null_incidents_vs_rms.csv", index=False)
print("Wrote null_incidents_vs_rms.csv")