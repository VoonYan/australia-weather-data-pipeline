# Australia Weather Data Pipeline

A small but complete data engineering project that collects daily weather for the eight Australian capital cities, stores it as tidy data, builds a DuckDB warehouse with analytics views, and publishes an interactive dashboard. The whole thing refreshes itself every day through GitHub Actions.

Live dashboard: once GitHub Pages is enabled, your dashboard will be at `https://<your username>.github.io/<repo name>/`

## How it works

The pipeline follows a classic extract, transform, load pattern:

1. **Extract** (`ingest.py`). Fetches daily weather from the free [Open-Meteo](https://open-meteo.com) API. Two batched requests cover all eight cities, one for history and one for the seven day forecast. The very first run backfills a full year. After that each run only refetches the last ten days, so the daily job stays quick and polite to the API. Raw responses are archived under `data/raw/` so any run can be replayed.

2. **Transform and load** (`transform_load.py`). Flattens the raw JSON into tidy rows, then upserts them into `data/weather_daily.csv`, which is the source of truth committed to git. When history and forecast overlap for the same city and date, history wins. The script then rebuilds the DuckDB warehouse (`data/weather.duckdb`) with a fact table, a city dimension, and two mart views: `mart_monthly` and `mart_city_summary`.

3. **Dashboard** (`build_dashboard.py`). Queries the warehouse and renders a single self contained `dashboard.html` with temperature trends, monthly rainfall, a seven day forecast and a city summary table. No server needed, just open it in a browser.

`pipeline.py` runs all three steps in order.

## Daily automation

`.github/workflows/daily.yml` runs the pipeline every day at 19:30 UTC, which is early morning in Australia after the archive API has updated. It commits the refreshed CSV and dashboard back to the repo, then deploys the dashboard to GitHub Pages. You can also trigger it manually from the Actions tab thanks to `workflow_dispatch`.

## Data

| Column | Meaning |
| --- | --- |
| city, state | One of the eight capital cities |
| date | Calendar date in local time |
| source | `history` (observed) or `forecast` |
| temp_max, temp_min, temp_mean | Daily temperatures in °C |
| precip_mm, rain_mm | Daily precipitation and rain in mm |
| wind_max_kmh | Daily maximum wind speed in km/h |
| solar_mj | Daily shortwave radiation in MJ/m² |

The committed CSV starts with a full year of history, about 3,000 rows, and grows by a handful of rows per day.

## Run it locally

```bash
pip install -r requirements.txt
python pipeline.py            # full run: fetch, transform, load, dashboard
python pipeline.py --no-fetch # rebuild warehouse and dashboard from the CSV
```

Then open `dashboard.html` in your browser, or query the warehouse directly:

```python
import duckdb
con = duckdb.connect("data/weather.duckdb")
con.sql("SELECT * FROM mart_city_summary ORDER BY avg_temp DESC").show()
```

## Publish on GitHub

```bash
git init
git add .
git commit -m "Initial commit: weather data pipeline"
git branch -M main
git remote add origin https://github.com/<your username>/<repo name>.git
git push -u origin main
```

Then two small settings on github.com:

1. In your repo go to Settings, then Pages, and set the source to **GitHub Actions**.
2. Go to the Actions tab and enable workflows if prompted. You can start the first run right away with the "Run workflow" button on the Daily weather pipeline.

## Ideas to extend it

Add more cities in `config.py`, they flow through automatically. Swap the CSV for Parquet if the history grows large. Add data quality tests with a tool like Great Expectations. Or point a BI tool at the DuckDB file and build richer analytics on the mart views.

Weather data by [Open-Meteo](https://open-meteo.com), licensed under CC BY 4.0.
