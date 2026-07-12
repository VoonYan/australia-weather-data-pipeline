"""Transform and load: merge new rows into the CSV, rebuild the warehouse.

The CSV at data/weather_daily.csv is the source of truth committed to git.
Each run merges new rows into it. History rows always win over forecast
rows for the same city and date, and newer fetches win over older ones.
The DuckDB warehouse and mart views are rebuilt from the CSV every run.
"""
import json
from pathlib import Path

import duckdb
import pandas as pd

from config import CITIES, CSV_PATH, DB_PATH, RAW_DIR

RENAMES = {
    "time": "date",
    "temperature_2m_max": "temp_max",
    "temperature_2m_min": "temp_min",
    "temperature_2m_mean": "temp_mean",
    "precipitation_sum": "precip_mm",
    "rain_sum": "rain_mm",
    "windspeed_10m_max": "wind_max_kmh",
    "shortwave_radiation_sum": "solar_mj",
}
COLUMNS = ["city", "state", "date", "source", "temp_max", "temp_min",
           "temp_mean", "precip_mm", "rain_mm", "wind_max_kmh", "solar_mj"]


def to_dataframe(payloads: list) -> pd.DataFrame:
    """Flatten raw API payloads into one tidy DataFrame."""
    frames = []
    for p in payloads:
        for source in ("history", "forecast"):
            df = pd.DataFrame(p[source]["daily"]).rename(columns=RENAMES)
            df["city"], df["state"], df["source"] = p["city"], p["state"], source
            frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    if "temp_mean" not in out.columns:
        out["temp_mean"] = pd.NA
    out["temp_mean"] = out["temp_mean"].fillna(
        (out["temp_max"] + out["temp_min"]) / 2)
    out = out.dropna(subset=["temp_max", "temp_min"])
    return out[COLUMNS]


def merge_into_csv(new: pd.DataFrame) -> pd.DataFrame:
    """Upsert new rows into the CSV. history > forecast, newer > older."""
    if CSV_PATH.exists():
        old = pd.read_csv(CSV_PATH)
        combined = pd.concat([old, new], ignore_index=True)
    else:
        combined = new.copy()
    # rank: forecast=0, history=1; stable sort keeps the later fetch last
    combined["_rank"] = (combined["source"] == "history").astype(int)
    combined = combined.sort_values(["city", "date", "_rank"], kind="stable")
    combined = combined.drop_duplicates(subset=["city", "date"], keep="last")
    combined = combined.drop(columns="_rank").sort_values(["city", "date"])
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(CSV_PATH, index=False)
    return combined


def load_warehouse(df: pd.DataFrame) -> None:
    """Rebuild DuckDB tables and mart views from the merged data."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    dim = pd.DataFrame([
        {"city": c, "state": m["state"], "lat": m["lat"], "lon": m["lon"]}
        for c, m in CITIES.items()
    ])
    con.execute("CREATE OR REPLACE TABLE dim_city AS SELECT * FROM dim")
    con.execute("""
        CREATE OR REPLACE TABLE fact_weather_daily AS
        SELECT city, CAST(date AS DATE) AS date, source,
               temp_max, temp_min, temp_mean, precip_mm, rain_mm,
               wind_max_kmh, solar_mj
        FROM df
    """)
    con.execute("""
        CREATE OR REPLACE VIEW mart_monthly AS
        SELECT city, date_trunc('month', date) AS month,
               round(avg(temp_mean), 1) AS avg_temp,
               round(max(temp_max), 1) AS hottest,
               round(min(temp_min), 1) AS coldest,
               round(sum(precip_mm), 1) AS total_precip_mm,
               count(*) FILTER (WHERE precip_mm >= 1.0) AS rainy_days
        FROM fact_weather_daily
        WHERE source = 'history'
        GROUP BY 1, 2
    """)
    con.execute("""
        CREATE OR REPLACE VIEW mart_city_summary AS
        SELECT f.city, d.state,
               round(avg(temp_mean), 1) AS avg_temp,
               round(max(temp_max), 1) AS record_high,
               round(min(temp_min), 1) AS record_low,
               round(sum(precip_mm), 0) AS annual_precip_mm,
               count(*) FILTER (WHERE precip_mm >= 1.0) AS rainy_days,
               round(avg(wind_max_kmh), 1) AS avg_wind_max
        FROM fact_weather_daily f
        JOIN dim_city d USING (city)
        WHERE source = 'history'
        GROUP BY 1, 2
    """)
    n = con.execute("SELECT count(*) FROM fact_weather_daily").fetchone()[0]
    print(f"  fact_weather_daily: {n} rows")
    con.close()

def run(raw_path: Path | None = None) -> None:
    if raw_path is None:
        raw_files = sorted(RAW_DIR.glob("weather_raw_*.json"))
        if raw_files:
            raw_path = raw_files[-1]
    if raw_path is not None:
        payloads = json.loads(Path(raw_path).read_text())
        new = to_dataframe(payloads)
        print(f"  transformed {len(new)} rows from {Path(raw_path).name}")
        merged = merge_into_csv(new)
    elif CSV_PATH.exists():
        print("  no raw file, rebuilding warehouse from existing CSV")
        merged = pd.read_csv(CSV_PATH)
    else:
        raise FileNotFoundError("no raw data and no existing CSV")
    load_warehouse(merged)


if __name__ == "__main__":
    run()
