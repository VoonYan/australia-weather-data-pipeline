"""Extract step: fetch daily weather from Open-Meteo and save raw JSON.

The fetch is incremental. On the first run it backfills a full year of
history. After that it only re-fetches the last OVERLAP_DAYS of history
plus the forecast, so the daily job stays fast and light on the API.
Raw responses are archived to data/raw/ so a run can be replayed.
"""
import json
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from config import (ARCHIVE_LAG_DAYS, ARCHIVE_URL, CITIES, CSV_PATH,
                    DAILY_VARS, FORECAST_DAYS, FORECAST_URL, HISTORY_DAYS,
                    OVERLAP_DAYS, RAW_DIR)


def fetch(url: str, params: dict, retries: int = 3) -> list:
    """GET with basic retry and backoff. Returns a list (one dict per city)."""
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else [data]
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def determine_start_date() -> date:
    """First run: full backfill. Later runs: small overlap window."""
    end_hist = date.today() - timedelta(days=ARCHIVE_LAG_DAYS)
    if CSV_PATH.exists():
        existing = pd.read_csv(CSV_PATH, usecols=["date", "source"])
        hist_dates = existing.loc[existing["source"] == "history", "date"]
        if len(hist_dates) > 0:
            latest = date.fromisoformat(hist_dates.max())
            return max(latest - timedelta(days=OVERLAP_DAYS),
                       end_hist - timedelta(days=HISTORY_DAYS))
    return end_hist - timedelta(days=HISTORY_DAYS)


def run() -> Path:
    """Fetch all cities in two batched requests, write one raw file per day."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    names = list(CITIES)
    common = {
        "latitude": ",".join(str(CITIES[n]["lat"]) for n in names),
        "longitude": ",".join(str(CITIES[n]["lon"]) for n in names),
        "daily": ",".join(DAILY_VARS),
        "timezone": "auto",
    }
    start_hist = determine_start_date()
    end_hist = date.today() - timedelta(days=ARCHIVE_LAG_DAYS)

    print(f"  history window: {start_hist} to {end_hist}")
    history = fetch(ARCHIVE_URL, {
        **common,
        "start_date": start_hist.isoformat(),
        "end_date": end_hist.isoformat(),
    })
    forecast = fetch(FORECAST_URL, {**common, "forecast_days": FORECAST_DAYS})

    payloads = [
        {"city": n, "state": CITIES[n]["state"],
         "history": history[i], "forecast": forecast[i]}
        for i, n in enumerate(names)
    ]
    out_path = RAW_DIR / f"weather_raw_{date.today().isoformat()}.json"
    out_path.write_text(json.dumps(payloads))
    print(f"  wrote {out_path.name} ({out_path.stat().st_size / 1e6:.1f} MB)")
    return out_path


if __name__ == "__main__":
    run()
