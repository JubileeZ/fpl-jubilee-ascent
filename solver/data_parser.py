import os
import sys
import pandas as pd
from solver.paths import DATA_DIR

def read_data(options, source=None):
    projections_path = options.get("projections_path")
    if projections_path:
        return pd.read_csv(projections_path, encoding="utf-8")
    source = options.get("datasource")
    list_of_files = [x for x in os.listdir(DATA_DIR) if x.endswith(".csv")]

    if not source:
        try:
            latest_file = max([DATA_DIR / f for f in list_of_files], key=os.path.getctime)
            print(f"No source specified, using most recent projection file: {latest_file}")
            return pd.read_csv(latest_file)
        except Exception:
            print("Cannot find projection data in /data/. Upload it to /data/ and make sure it is a .csv file")
            sys.exit(0)

    if f"{source}.csv" not in list_of_files:
        raise FileNotFoundError(f"Data file {source}.csv not found in /data/. Please generate it first.")

    filepath = DATA_DIR / f"{source}.csv"
    return pd.read_csv(filepath, encoding="utf-8")
