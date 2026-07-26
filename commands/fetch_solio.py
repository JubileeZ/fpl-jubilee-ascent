import json
import logging
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

# Set up path to include root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import load_env, configure_utf8_stdio
load_env()
configure_utf8_stdio()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOLIO_API_URL = "https://fpl.solioanalytics.com/api/data/latest.json"

def fetch_solio_data() -> dict:
    """Fetch latest public projection data from Solio Analytics endpoint."""
    logger.info("Fetching projections from Solio Analytics endpoint (%s)...", SOLIO_API_URL)
    req = urllib.request.Request(SOLIO_API_URL, headers={"User-Agent": "Mozilla/5.0 (FPL-Jubilee-Ascent Agent)"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data

def parse_solio_dataframe(solio_data: dict) -> pd.DataFrame:
    """Parse raw Solio JSON payload into a standardized flat DataFrame."""
    gw = solio_data.get("gameweek", 1)
    fetched_at = datetime.now(timezone.utc).isoformat()
    
    top_projected = solio_data.get("topProjected", [])
    if not top_projected:
        return pd.DataFrame()
        
    records = []
    for item in top_projected:
        opponents = item.get("opponents", [])
        opp_str = opponents[0].get("opponent", "") if opponents else ""
        is_home = opponents[0].get("isHome", True) if opponents else True
        
        records.append({
            "name": item.get("name"),
            "team": item.get("team"),
            "position": item.get("position"),
            "price_m": float(item.get("price", 0)) / 10.0,
            "gameweek": gw,
            "solio_xp": float(item.get("prPoints", 0.0)),
            "opponent": opp_str,
            "is_home": is_home,
            "ownership_pct": float(item.get("ownership", 0.0)),
            "fetched_at": fetched_at
        })
        
    return pd.DataFrame(records)

def main():
    try:
        solio_data = fetch_solio_data()
    except Exception as e:
        logger.error("Failed to fetch data from Solio Analytics: %s", e)
        sys.exit(1)

    gw = solio_data.get("gameweek")
    gen_time = solio_data.get("generatedAt", "")
    
    if gw is None or not (1 <= gw <= 38):
        logger.info("No active Gameweek (GW%s) or season has ended. Exiting safely.", gw)
        sys.exit(0)

    logger.info("Solio Analytics GW%s data loaded (Generated: %s)", gw, gen_time)

    df_solio = parse_solio_dataframe(solio_data)
    if df_solio.empty:
        logger.warning("No projection data available to export.")
        sys.exit(0)

    data_dir = PROJECT_ROOT / "data"
    archive_dir = data_dir / "archive" / "solio"
    data_dir.mkdir(exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save raw JSON snapshot
    with open(data_dir / "solio_raw.json", "w", encoding="utf-8") as f:
        json.dump(solio_data, f, indent=2)

    # 2. Save CSV and Parquet latest files
    df_solio.to_csv(data_dir / "solio_projections.csv", index=False)
    df_solio.to_parquet(data_dir / "solio_latest.parquet", index=False)
    logger.info("Saved latest Solio projections to %s", data_dir / "solio_latest.parquet")

    # 3. Save Gameweek Frozen Archive Snapshot
    archive_parquet = archive_dir / f"solio_gw{gw}.parquet"
    df_solio.to_parquet(archive_parquet, index=False)
    logger.info("Archived GW%s snapshot to %s", gw, archive_parquet)

    # Load local metrics_component_hybrid projections if present for cross-check
    local_csv = data_dir / "metrics_component_hybrid.csv"
    if local_csv.exists():
        df_local = pd.read_csv(local_csv)
        gw_col = f"{gw}_Pts" if f"{gw}_Pts" in df_local.columns else "1_Pts"
        
        merged = df_solio.merge(df_local, left_on="name", right_on="Name", suffixes=("_solio", "_local"))
        merged["diff"] = merged["solio_xp"] - merged[gw_col]
        
        print("\n================ Solio Analytics vs Local Model Cross-Check (GW1) ================")
        print(f"{'Player':18s} {'Team':5s} {'Pos':4s} {'Price':6s} {'Solio xP':10s} {'Local xP':10s} {'Diff':8s}")
        print("-" * 68)
        for _, row in merged.head(20).iterrows():
            print(f"{row['name']:18s} {row['team']:5s} {row['position']:4s} £{row['price_m']:<4.1f}m {row['solio_xp']:<10.2f} {row[gw_col]:<10.2f} {row['diff']:+8.2f}")
        print("=" * 68)

if __name__ == "__main__":
    main()
