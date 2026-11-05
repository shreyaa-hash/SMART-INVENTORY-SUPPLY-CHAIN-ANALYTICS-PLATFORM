import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import KpiCard from "../components/KpiCard.jsx";
import Panel, { EmptyChart } from "../components/Panel.jsx";

const money = (value) => new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 }).format(value || 0);

export default function ExecutiveOverview({ overview, monthly, categories, topProducts, warehouses }) {
  return (
    <>
      <div className="kpi-grid">
        <KpiCard label="Observed revenue" value={money(overview?.revenue)} note="Recorded transaction lines · GBP" icon="£" />
        <KpiCard label="Orders" value={Number(overview?.orders || 0).toLocaleString()} note="Distinct invoices in source" icon="↗" />
        <KpiCard label="Products" value={Number(overview?.products || 0).toLocaleString()} note="Observed product codes" icon="▦" />
        <KpiCard label="Inventory value" value={money(overview?.inventory_value)} note="Synthetic stock & unit costs" icon="◈" />
        <KpiCard label="Inventory turnover" value={overview?.inventory_turnover_estimated == null ? "—" : `${overview.inventory_turnover_estimated.toFixed(2)}×`} note="Estimated COGS / demo stock value" icon="⟳" />
        <KpiCard label="Stock at zero" value={overview?.stockout_rate_proxy_pct == null ? "—" : `${overview.stockout_rate_proxy_pct.toFixed(1)}%`} note="Snapshot proxy, not observed stockouts" icon="!" />
        <KpiCard label="Gross profit" value={money(overview?.gross_profit_estimated)} note="Estimated costs; not source data" icon="◉" />
        <KpiCard label="Overstock value" value={money(overview?.overstock_value_estimated)} note="Synthetic inventory estimate" icon="▤" />
      </div>
      <div className="chart-grid">
        <Panel title="Revenue vs profit" subtitle="Observed revenue and synthetic-cost gross-profit estimate by month">
          {monthly.length ? <ResponsiveContainer width="100%" height={280}><ComposedChart data={monthly}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" tick={{ fontSize: 11 }} /><YAxis yAxisId="left" tickFormatter={(value) => `${Math.round(value / 1000)}k`} /><Tooltip formatter={(value) => money(value)} /><Legend /><Bar yAxisId="left" dataKey="revenue" name="Observed revenue (GBP)" fill="#3157d5" radius={[4, 4, 0, 0]} /><Line yAxisId="left" type="monotone" dataKey="estimated_gross_profit" name="Estimated gross profit (GBP)" stroke="#159a82" dot={false} /></ComposedChart></ResponsiveContainer> : <EmptyChart />}
        </Panel>
        <Panel title="Sales by inferred category" subtitle="Observed revenue grouped by synthetic description labels">
          {categories.length ? <ResponsiveContainer width="100%" height={280}><BarChart data={categories} layout="vertical" margin={{ left: 18 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" tickFormatter={(value) => `${Math.round(value / 1000)}k`} /><YAxis type="category" dataKey="category_name" width={125} tick={{ fontSize: 11 }} /><Tooltip formatter={(value) => money(value)} /><Bar dataKey="revenue" name="Revenue (GBP)" fill="#159a82" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer> : <EmptyChart />}
        </Panel>
        <Panel title="Top products" subtitle="Ranked by observed line revenue">
          {topProducts.length ? <ResponsiveContainer width="100%" height={300}><BarChart data={topProducts.slice(0, 8)} layout="vertical" margin={{ left: 12 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" tickFormatter={(value) => `${Math.round(value / 1000)}k`} /><YAxis type="category" dataKey="product_id" width={72} /><Tooltip formatter={(value) => money(value)} labelFormatter={(label) => topProducts.find((row) => row.product_id === label)?.description || label} /><Bar dataKey="revenue" name="Revenue (GBP)" fill="#7255ce" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer> : <EmptyChart />}
        </Panel>
        <Panel title="Warehouse allocation" subtitle="Synthetic assignment of observed order revenue">
          {warehouses.length ? <ResponsiveContainer width="100%" height={300}><BarChart data={warehouses}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="warehouse_name" tick={{ fontSize: 11 }} /><YAxis tickFormatter={(value) => `${Math.round(value / 1000)}k`} /><Tooltip formatter={(value) => money(value)} /><Bar dataKey="revenue" name="Allocated revenue (GBP)" radius={[4, 4, 0, 0]}>{warehouses.map((row, index) => <Cell key={row.warehouse_id} fill={["#3157d5", "#159a82", "#f0a03b", "#7255ce"][index % 4]} />)}</Bar></BarChart></ResponsiveContainer> : <EmptyChart />}
        </Panel>
      </div>
      <div className="notice-strip"><strong>Data provenance</strong><span>Revenue and units are observed UCI transactions. Costs, gross profit, inventory value, stock-zero proxy, inferred categories, and warehouse assignments include synthetic inputs.</span></div>
    </>
  );
}
