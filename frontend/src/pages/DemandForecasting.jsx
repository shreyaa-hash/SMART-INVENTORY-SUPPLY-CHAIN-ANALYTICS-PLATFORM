import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet } from "../services/api.js";
import Panel, { EmptyChart } from "../components/Panel.jsx";

export default function DemandForecasting({ products }) {
  const [productId, setProductId] = useState("");
  const [forecast, setForecast] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!productId && products.length) setProductId(products[0].product_id);
  }, [products, productId]);
  useEffect(() => {
    if (!productId) return;
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([apiGet(`/api/forecast/${encodeURIComponent(productId)}`, { horizon_days: 90 }), apiGet(`/api/sales/history/${encodeURIComponent(productId)}`, { days: 180 })])
      .then(([nextForecast, nextHistory]) => { if (active) { setForecast(nextForecast); setHistory(nextHistory); } })
      .catch((reason) => { if (active) setError(reason.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [productId]);

  const total = (days) => forecast?.forecasts?.slice(0, days).reduce((sum, row) => sum + row.predicted_demand, 0) ?? 0;
  const chartData = [...history.slice(-30).map((row) => ({ date: row.sales_date, actual: row.units_sold })), ...(forecast?.forecasts || []).map((row) => ({ date: row.forecast_date, forecast: row.predicted_demand }))];
  return (
    <>
      <div className="filter-row">
        <label htmlFor="forecast-product">Product</label>
        <select id="forecast-product" value={productId} onChange={(event) => setProductId(event.target.value)}>{products.map((item) => <option key={item.product_id} value={item.product_id}>{item.product_id} · {item.description}</option>)}</select>
        {forecast?.model_name && <span className="model-badge">Selected: {forecast.model_name}</span>}
      </div>
      {loading && <div className="loading-inline">Training and validating forecast…</div>}
      {error && <div className="error-banner" role="alert">{error}</div>}
      {forecast?.warning && <div className="notice-strip warning"><strong>Insufficient history</strong><span>{forecast.warning}</span></div>}
      <div className="kpi-grid kpi-grid-three">
        {[7, 30, 90].map((days) => <article className="kpi-card" key={days}><div className="kpi-top"><span className="kpi-label">Next {days} days</span><span className="kpi-icon">⌁</span></div><strong className="kpi-value">{forecast?.warning || !forecast ? "—" : total(days).toFixed(0)}</strong><span className="kpi-note">Forecast units · selected product</span></article>)}
      </div>
      <div className="chart-grid">
        <Panel title="Observed and forecast demand" subtitle="Chronological holdout comparison; future forecasts are recursive">
          {chartData.length ? <ResponsiveContainer width="100%" height={330}><LineChart data={chartData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={30} /><YAxis /><Tooltip /><Legend /><Line type="monotone" dataKey="actual" name="Observed units" stroke="#3157d5" dot={false} connectNulls /><Line type="monotone" dataKey="forecast" name="Predicted units" stroke="#e29a37" strokeWidth={2} dot={false} connectNulls /></LineChart></ResponsiveContainer> : <EmptyChart />}
        </Panel>
        <Panel title="Validation model comparison" subtitle="Chronological holdout; MAPE ignores zero-demand days">
          {forecast?.validation_metrics ? <ResponsiveContainer width="100%" height={330}><BarChart data={Object.entries(forecast.validation_metrics).map(([name, values]) => ({ name, MAE: values.mae, RMSE: values.rmse }))}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis /><Tooltip /><Legend /><Bar dataKey="MAE" fill="#159a82" /><Bar dataKey="RMSE" fill="#7255ce" /></BarChart></ResponsiveContainer> : <EmptyChart text={forecast?.warning || "Select a product to train and compare models."} />}
        </Panel>
      </div>
      {forecast?.uncertainty && <div className="notice-strip"><strong>Approximate uncertainty</strong><span>Empirical 95% residual quantiles from {forecast.uncertainty.validation_days} chronological validation days; {forecast.uncertainty.method}. Not a calibrated prediction interval.</span></div>}
      <Panel title="Forecast output" subtitle="Actual future demand is not available in the source dataset">
        <div className="supplier-table"><div className="table-header"><span>Forecast date</span><span>Predicted demand</span><span>Actual</span><span>Model</span></div>{(forecast?.forecasts || []).slice(0, 12).map((row) => <div className="table-row" key={row.forecast_date}><span>{row.forecast_date}</span><b>{row.predicted_demand.toFixed(2)}</b><span>Not available</span><span>{row.model_name}</span></div>)}</div>
      </Panel>
    </>
  );
}
