"""Pipeline configuration."""
from pathlib import Path

BASE_DIR = Path(__file__).parent
RAW_DIR = BASE_DIR / "data" / "raw"
CSV_PATH = BASE_DIR / "data" / "weather_daily.csv"
DB_PATH = BASE_DIR / "data" / "weather.duckdb"
DASHBOARD_PATH = BASE_DIR / "dashboard.html"

# Australian capital cities
CITIES = {
    "Sydney":    {"lat": -33.87, "lon": 151.21, "state": "NSW"},
    "Melbourne": {"lat": -37.81, "lon": 144.96, "state": "VIC"},
    "Brisbane":  {"lat": -27.47, "lon": 153.03, "state": "QLD"},
    "Perth":     {"lat": -31.95, "lon": 115.86, "state": "WA"},
    "Adelaide":  {"lat": -34.93, "lon": 138.60, "state": "SA"},
    "Hobart":    {"lat": -42.88, "lon": 147.33, "state": "TAS"},
    "Darwin":    {"lat": -12.46, "lon": 130.84, "state": "NT"},
    "Canberra":  {"lat": -35.28, "lon": 149.13, "state": "ACT"},
}

# Open-Meteo endpoints
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

HISTORY_DAYS = 365   # backfill window on first ever run
OVERLAP_DAYS = 10    # re-fetch recent days so archive corrections flow in
ARCHIVE_LAG_DAYS = 2 # the archive API lags real time by about two days
FORECAST_DAYS = 7

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "rain_sum",
    "windspeed_10m_max",
    "shortwave_radiation_sum",
]
