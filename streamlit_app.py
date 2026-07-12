"""Streamlit dashboard for the Australia weather pipeline.

Reads data/weather_daily.csv from the repo, so every daily commit from
GitHub Actions flows into the app automatically.
"""
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Australia Weather", page_icon="🌏",
                   layout="wide")

CSV_URL = "data/weather_daily.csv"


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_URL, parse_dates=["date"])
    return df


df = load_data()
hist = df[df["source"] == "history"]
fc = df[df["source"] == "forecast"]

st.title("🌏 Australia Weather Dashboard")
st.caption(
    f"Daily weather for 8 capital cities · {df['date'].min():%d %b %Y} to "
    f"{df['date'].max():%d %b %Y} · {len(df):,} rows · Source: Open-Meteo, "
    "refreshed daily by GitHub Actions")

# Sidebar filters
cities = sorted(df["city"].unique())
sel = st.sidebar.multiselect("Cities", cities, default=cities)
months = st.sidebar.slider("Months of history", 1, 12, 12)
cutoff = hist["date"].max() - pd.DateOffset(months=months)
h = hist[hist["city"].isin(sel) & (hist["date"] >= cutoff)]
f = fc[fc["city"].isin(sel)]

# KPIs from the filtered window
summary = (h.groupby("city")
             .agg(avg_temp=("temp_mean", "mean"),
                  record_high=("temp_max", "max"),
                  record_low=("temp_min", "min"),
                  precip=("precip_mm", "sum"),
                  rainy_days=("precip_mm", lambda s: (s >= 1).sum()),
                  avg_wind=("wind_max_kmh", "mean"))
             .round(1).reset_index())
if len(summary):
    hot = summary.loc[summary["avg_temp"].idxmax()]
    wet = summary.loc[summary["precip"].idxmax()]
    cold = summary.loc[summary["record_low"].idxmin()]
    windy = summary.loc[summary["avg_wind"].idxmax()]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Warmest on average", f"{hot.avg_temp} °C", hot.city)
    c2.metric("Record low", f"{cold.record_low} °C", cold.city)
    c3.metric("Most rainfall", f"{wet.precip:,.0f} mm", wet.city)
    c4.metric("Windiest on average", f"{windy.avg_wind} km/h", windy.city)

st.subheader("Daily mean temperature (°C)")
fig = px.line(h, x="date", y="temp_mean", color="city",
              labels={"temp_mean": "°C", "date": ""})
fig.update_layout(height=380, legend_title_text="")
st.plotly_chart(fig, width="stretch")

left, right = st.columns(2)
with left:
    st.subheader("Monthly rainfall (mm)")
    m = (h.assign(month=h["date"].dt.to_period("M").dt.to_timestamp())
           .groupby(["month", "city"])["precip_mm"].sum().reset_index())
    fig = px.bar(m, x="month", y="precip_mm", color="city",
                 labels={"precip_mm": "mm", "month": ""})
    fig.update_layout(height=360, legend_title_text="")
    st.plotly_chart(fig, width="stretch")
with right:
    st.subheader("Next 7 days: temperature range (°C)")
    r = (f.groupby("city")
           .agg(lo=("temp_min", "min"), hi=("temp_max", "max"))
           .reset_index())
    fig = px.bar(r, y="city", x=r["hi"] - r["lo"], base="lo",
                 orientation="h", labels={"x": "°C", "city": ""})
    fig.update_layout(height=360, showlegend=False)
    st.plotly_chart(fig, width="stretch")

st.subheader("City summary for the selected window")
st.dataframe(summary.rename(columns={
    "city": "City", "avg_temp": "Avg temp °C", "record_high": "High °C",
    "record_low": "Low °C", "precip": "Rain mm", "rainy_days": "Rainy days",
    "avg_wind": "Avg max wind km/h"}), width="stretch",
    hide_index=True)

with st.expander("About this project"):
    st.markdown(
        "An end to end data pipeline: GitHub Actions fetches Open-Meteo "
        "data every day, merges it into a CSV in the repo, rebuilds a "
        "DuckDB warehouse, and this app reads the fresh CSV on each "
        "deploy. Weather data by Open-Meteo, CC BY 4.0.")
