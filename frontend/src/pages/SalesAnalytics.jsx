import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Panel, { EmptyChart } from "../components/Panel.jsx";

const money = (value) => new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 }).format(value || 0);

export default function SalesAnalytics({ monthly, categories, topProducts, regions }) {
  return (
    <div className="chart-grid">
      <Panel title="Daily history, monthly view" subtitle="Observed transaction sales and units">
        {monthly.length ? <ResponsiveContainer width="100%" height={310}><LineChart data={monthly}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" tick={{ fontSize: 11 }} /><YAxis yAxisId="left" tickFormatter={(value) => `${Math.round(value / 1000)}k`} /><YAxis yAxisId="right" orientation="right" unit="%" /><Tooltip formatter={(value, name) => name.includes("GBP") ? money(value) : `${Number(value).toFixed(1)}%`} /><Legend /><Line yAxisId="left" type="monotone" dataKey="revenue" name="Revenue (GBP)" stroke="#3157d5" strokeWidth={2} dot={false} /><Line yAxisId="right" type="monotone" dataKey="revenue_growth_pct" name="Revenue growth (%)" stroke="#159a82" dot={false} /></LineChart></ResponsiveContainer> : <EmptyChart />}
      </Panel>
      <Panel title="Category comparison" subtitle="Observed revenue; category names are inferred">
        {categories.length ? <ResponsiveContainer width="100%" height={310}><BarChart data={categories}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="category_name" tick={{ fontSize: 10 }} /><YAxis tickFormatter={(value) => `${Math.round(value / 1000)}k`} /><Tooltip formatter={(value) => money(value)} /><Bar dataKey="revenue" name="Revenue (GBP)" fill="#159a82" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer> : <EmptyChart />}
      </Panel>
      <Panel title="Top products" subtitle="Observed units sold">
        {topProducts.length ? <ResponsiveContainer width="100%" height={310}><BarChart data={topProducts.slice(0, 12)} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" /><YAxis type="category" dataKey="product_id" width={70} /><Tooltip /><Bar dataKey="units" name="Units" fill="#7255ce" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer> : <EmptyChart />}
      </Panel>
      <Panel title="Customer regions" subtitle="Observed invoice country · highest revenue first">
        {regions.length ? <ResponsiveContainer width="100%" height={310}><BarChart data={regions.slice(0, 12)} layout="vertical" margin={{ left: 10 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" tickFormatter={(value) => `${Math.round(value / 1000)}k`} /><YAxis type="category" dataKey="country" width={115} tick={{ fontSize: 10 }} /><Tooltip formatter={(value) => money(value)} /><Bar dataKey="revenue" name="Revenue (GBP)" fill="#e29a37" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer> : <EmptyChart />}
      </Panel>
      <div className="notice-strip"><strong>Revenue growth</strong><span>Monthly values come from observed positive invoice lines after cleaning. The date-range selector above applies to the executive trend and is reflected in the API query.</span></div>
    </div>
  );
}
