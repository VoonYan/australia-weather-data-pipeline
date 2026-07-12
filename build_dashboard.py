"""Generate a self-contained HTML dashboard from the DuckDB warehouse."""
import json

import duckdb

from config import DASHBOARD_PATH, DB_PATH


def q(con, sql):
    df = con.execute(sql).fetchdf()
    return json.loads(df.to_json(orient="records", date_format="iso"))


def run():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    summary = q(con, "SELECT * FROM mart_city_summary ORDER BY avg_temp DESC")
    monthly = q(con, "SELECT * FROM mart_monthly ORDER BY month")
    daily = q(con, """
        SELECT city, date, temp_mean, precip_mm, source
        FROM fact_weather_daily ORDER BY date
    """)
    forecast = q(con, """
        SELECT city, date, temp_max, temp_min, precip_mm
        FROM fact_weather_daily WHERE source='forecast' ORDER BY date
    """)
    meta = con.execute("""
        SELECT min(date), max(date), count(*) FROM fact_weather_daily
    """).fetchone()
    con.close()

    html = HTML_TEMPLATE.replace("__SUMMARY__", json.dumps(summary)) \
        .replace("__MONTHLY__", json.dumps(monthly)) \
        .replace("__DAILY__", json.dumps(daily)) \
        .replace("__FORECAST__", json.dumps(forecast)) \
        .replace("__META__", json.dumps({
            "start": str(meta[0]), "end": str(meta[1]), "rows": meta[2]}))
    DASHBOARD_PATH.write_text(html, encoding="utf-8")
    print(f"  wrote {DASHBOARD_PATH.name}")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Australia Weather Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root { --bg:#0f172a; --card:#1e293b; --text:#e2e8f0; --muted:#94a3b8; --accent:#38bdf8; }
  * { margin:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:'Segoe UI',system-ui,sans-serif; padding:24px; }
  h1 { font-size:1.6rem; margin-bottom:4px; }
  .sub { color:var(--muted); margin-bottom:20px; font-size:.9rem; }
  .kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin-bottom:20px; }
  .kpi { background:var(--card); border-radius:10px; padding:14px 16px; }
  .kpi .v { font-size:1.5rem; font-weight:600; color:var(--accent); }
  .kpi .l { color:var(--muted); font-size:.8rem; margin-top:2px; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  .card { background:var(--card); border-radius:10px; padding:16px; }
  .card h2 { font-size:1rem; margin-bottom:10px; color:var(--muted); font-weight:500; }
  .full { grid-column:1/-1; }
  select { background:var(--bg); color:var(--text); border:1px solid #334155; border-radius:6px; padding:4px 8px; margin-left:8px; }
  table { width:100%; border-collapse:collapse; font-size:.85rem; }
  th,td { text-align:right; padding:6px 8px; border-bottom:1px solid #334155; }
  th:first-child,td:first-child { text-align:left; }
  th { color:var(--muted); font-weight:500; }
  @media (max-width:800px){ .grid{grid-template-columns:1fr;} }
</style>
</head>
<body>
<h1>🌏 Australia Weather Dashboard</h1>
<div class="sub" id="meta"></div>
<div class="kpis" id="kpis"></div>
<div class="grid">
  <div class="card full">
    <h2>Daily mean temperature (°C) <select id="citySel"></select></h2>
    <canvas id="tempChart" height="80"></canvas>
  </div>
  <div class="card"><h2>Monthly rainfall (mm)</h2><canvas id="rainChart"></canvas></div>
  <div class="card"><h2>7-day forecast: temp range (°C)</h2><canvas id="fcChart"></canvas></div>
  <div class="card full"><h2>City summary (last 12 months)</h2><div id="tbl"></div></div>
</div>
<script>
const SUMMARY=__SUMMARY__, MONTHLY=__MONTHLY__, DAILY=__DAILY__, FORECAST=__FORECAST__, META=__META__;
const CITIES=[...new Set(DAILY.map(d=>d.city))].sort();
const COLORS=['#38bdf8','#f87171','#4ade80','#facc15','#c084fc','#fb923c','#2dd4bf','#f472b6'];
Chart.defaults.color='#94a3b8'; Chart.defaults.borderColor='#334155';

document.getElementById('meta').textContent=
  `Data: ${META.start} → ${META.end} · ${META.rows.toLocaleString()} rows · 8 cities · Source: Open-Meteo`;

// KPIs
const hot=SUMMARY[0], wet=[...SUMMARY].sort((a,b)=>b.annual_precip_mm-a.annual_precip_mm)[0];
const cold=[...SUMMARY].sort((a,b)=>a.record_low-b.record_low)[0];
const windy=[...SUMMARY].sort((a,b)=>b.avg_wind_max-a.avg_wind_max)[0];
document.getElementById('kpis').innerHTML=[
  [hot.avg_temp+'°C','Warmest avg — '+hot.city],
  [cold.record_low+'°C','Record low — '+cold.city],
  [wet.annual_precip_mm+' mm','Wettest — '+wet.city],
  [windy.avg_wind_max+' km/h','Windiest avg — '+windy.city],
].map(([v,l])=>`<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('');

// Temp chart with city selector
const sel=document.getElementById('citySel');
sel.innerHTML='<option value="ALL">All cities</option>'+CITIES.map(c=>`<option>${c}</option>`).join('');
let tempChart;
function drawTemp(city){
  const sets=(city==='ALL'?CITIES:[city]).map((c,i)=>{
    const rows=DAILY.filter(d=>d.city===c&&d.source==='history');
    return {label:c,data:rows.map(d=>({x:d.date.slice(0,10),y:d.temp_mean})),
      borderColor:COLORS[CITIES.indexOf(c)%8],borderWidth:1.2,pointRadius:0,tension:.3};
  });
  if(tempChart)tempChart.destroy();
  tempChart=new Chart(document.getElementById('tempChart'),{type:'line',
    data:{datasets:sets},
    options:{scales:{x:{type:'category',ticks:{maxTicksLimit:12}}},
      plugins:{legend:{labels:{boxWidth:12}}},interaction:{mode:'nearest',intersect:false}}});
}
sel.onchange=()=>drawTemp(sel.value); drawTemp('ALL');

// Monthly rainfall (stacked by city)
const months=[...new Set(MONTHLY.map(m=>m.month.slice(0,7)))].sort();
new Chart(document.getElementById('rainChart'),{type:'bar',
  data:{labels:months,datasets:CITIES.map((c,i)=>({label:c,
    data:months.map(mo=>{const r=MONTHLY.find(m=>m.city===c&&m.month.slice(0,7)===mo);return r?r.total_precip_mm:0;}),
    backgroundColor:COLORS[i%8]}))},
  options:{scales:{x:{stacked:true},y:{stacked:true}},plugins:{legend:{labels:{boxWidth:12}}}}});

// Forecast range chart (floating bars, avg across range per city)
const fcDates=[...new Set(FORECAST.map(f=>f.date.slice(0,10)))].sort();
new Chart(document.getElementById('fcChart'),{type:'bar',
  data:{labels:CITIES,datasets:[{label:'min→max over next 7 days',
    data:CITIES.map(c=>{const r=FORECAST.filter(f=>f.city===c);
      return [Math.min(...r.map(x=>x.temp_min)),Math.max(...r.map(x=>x.temp_max))];}),
    backgroundColor:'#38bdf8'}]},
  options:{indexAxis:'y',plugins:{legend:{display:false}}}});

// Summary table
document.getElementById('tbl').innerHTML='<table><tr><th>City</th><th>State</th><th>Avg temp</th><th>Record high</th><th>Record low</th><th>Rain (mm/yr)</th><th>Rainy days</th></tr>'+
  SUMMARY.map(s=>`<tr><td>${s.city}</td><td>${s.state}</td><td>${s.avg_temp}°C</td><td>${s.record_high}°C</td><td>${s.record_low}°C</td><td>${s.annual_precip_mm}</td><td>${s.rainy_days}</td></tr>`).join('')+'</table>';
</script>
</body>
</html>
"""

if __name__ == "__main__":
    run()
