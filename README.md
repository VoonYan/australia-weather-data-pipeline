# Australia Weather Data Pipeline

A complete data engineering project that collects daily weather for the eight Australian capital cities, stores it as tidy data, builds a DuckDB warehouse with analytics views, and serves an interactive Streamlit dashboard. The data refreshes itself every day through GitHub Actions.

## How it works

The pipeline follows a classic extract, transform, load pattern:

1. **Extract** (`ingest.py`). Fetches daily weather from the free [Open-Meteo](https://open-meteo.com) API. Two batched requests cover all eight cities, one for history and one for the seven day forecast. The very first run backfills a full year. After that each run only refetches the last ten days, so the daily job stays quick and polite to the API. Raw responses are archived under `data/raw/` so any run can be replayed.

2. **Transform and load** (`transform_load.py`). Flattens the raw JSON into tidy rows, then upserts them into `data/weather_daily.csv`, which is the source of truth committed to git. When history and forecast overlap for the same city and date, history wins. The script then rebuilds the DuckDB warehouse (`data/weather.duckdb`) with a fact table, a city dimension, and two mart views: `mart_monthly` and `mart_city_summary`.

3. **Serve**. Two options come built in. `build_dashboard.py` renders a self contained `dashboard.html` you can open in any browser. `streamlit_app.py` is an interactive Streamlit app that reads the committed CSV, so it always shows the latest data.

`pipeline.py` runs the extract, transform, load and dashboard steps in order.

## Daily automation

`.github/workflows/daily.yml` runs the pipeline every day at 19:30 UTC, which is early morning in Australia after the archive API has updated. It commits the refreshed CSV and dashboard back to the repo.
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
streamlit run streamlit_app.py
```

You can also query the warehouse directly:

```python
import duckdb
con = duckdb.connect("data/weather.duckdb")
con.sql("SELECT * FROM mart_city_summary ORDER BY avg_temp DESC").show()
```

## Ideas to extend it

Add more cities in `config.py`, they flow through automatically. Swap the CSV for Parquet if the history grows large. Add data quality tests with a tool like Great Expectations. Or point a BI tool at the DuckDB file and build richer analytics on the mart views.

Weather data by [Open-Meteo](https://open-meteo.com), licensed under CC BY 4.0.
