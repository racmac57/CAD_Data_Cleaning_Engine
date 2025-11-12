import pandas as pd
from pathlib import Path


SAMPLE = r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Pipeline\data\01_raw\sample\2024_CAD_ALL_SAMPLE_1000.csv"
OUTDIR = Path(r"C:\Users\carucci_r\OneDrive - City of Hackensack\02_ETL_Scripts\CAD_Data_Pipeline\data\02_reports\cad_validation")


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(SAMPLE, dtype=str).fillna("")
    miss = df[df['Response Type'].astype(str).str.strip() == ""]

    print("Unmapped incidents (top 50):")
    print(miss['Incident'].value_counts().head(50).to_string())

    seed = miss[['Incident']].drop_duplicates().assign(Incident_Norm="", Response_Type="")
    seed_path = OUTDIR / "missing_CallTypes_seed.csv"
    seed.to_csv(seed_path, index=False)
    print(f"\nSeed written: {seed_path}")


if __name__ == "__main__":
    main()

