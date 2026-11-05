import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import KpiCard from "../components/KpiCard.jsx";
import Panel, { EmptyChart } from "../components/Panel.jsx";

const money = (value) => new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 }).format(value || 0);
const colors = ["#3157d5", "#159a82", "#f0a03b", "#7255ce"];

export default function InventoryAnalytics({ summary, products, warehouses }) {
  const stockBuckets = [
    { name: "0", count: products.filter((item) => item.quantity_on_hand === 0).length },
    { name: "1–20", count: products.filter((item) => item.quantity_on_hand > 0 && item.quantity_on_hand <= 20).length },
    { name: "21–100", count: products.filter((item) => item.quantity_on_hand > 20 && item.quantity_on_hand <= 100).length },
    { name: "101+", count: products.filter((item) => item.quantity_on_hand > 100).length },
  ];
  const abc = ["A", "B", "C"].map((name) => {
    const rows = products.filter((item) => item.abc_class === name);
    return { name, products: rows.length, value: rows.reduce((sum, item) => sum + item.annual_consumption_value, 0) };
  });
  const highestStock = [...products].sort((a, b) => b.quantity_on_hand - a.quantity_on_hand).slice(0, 10);
  return (
    <>
      <div className="kpi-grid kpi-grid-five">
        <KpiCard label="Available stock" value={Number(summary?.available_stock || 0).toLocaleString()} note="Synthetic snapshot units" icon="▦" />
        <KpiCard label="Low-stock products" value={Number(summary?.low_stock_products || 0).toLocaleString()} note={`At or below ${summary?.low_stock_coverage_days ?? 14} days' run rate`} icon="!" />
        <KpiCard label="Overstock products" value={Number(summary?.overstock_products || 0).toLocaleString()} note="Coverage above configured target" icon="↑" />
        <KpiCard label="Dead-stock value" value={money(summary?.dead_stock_value)} note="Synthetic stock, no recent observed sales" icon="◌" />
        <KpiCard label="Inventory turnover" value={summary?.inventory_turnover_estimated == null ? "—" : `${summary.inventory_turnover_estimated.toFixed(2)}×`} note="Estimated COGS / demo stock value" icon="⟳" />
        <KpiCard label="Annual holding cost" value={money(summary?.holding_cost_estimated_annual)} note="Configurable carrying-cost estimate" icon="£" />
      </div>
      <div className="chart-grid">
        <Panel title="Stock distribution" subtitle="Synthetic on-hand units by product">
          {products.length ? <ResponsiveContainer width="100%" height={260}><BarChart data={stockBuckets}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" name="Products" fill="#3157d5" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer> : <EmptyChart />}
        </Panel>
        <Panel title="ABC consumption value" subtitle="Annual estimated cost of observed units sold">
          {abc.some((item) => item.products) ? <ResponsiveContainer width="100%" height={260}><PieChart><Pie data={abc.filter((item) => item.products)} dataKey="value" nameKey="name" innerRadius={62} outerRadius={94} paddingAngle={4} label={({ name }) => name}>{abc.map((item, index) => <Cell key={item.name} fill={colors[index]} />)}</Pie><Tooltip formatter={(value) => money(value)} /></PieChart></ResponsiveContainer> : <EmptyChart />}
        </Panel>
        <Panel title="Inventory by warehouse" subtitle="Synthetic inventory allocation">
          {warehouses.length ? <ResponsiveContainer width="100%" height={260}><BarChart data={warehouses}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="warehouse_name" tick={{ fontSize: 11 }} /><YAxis /><Tooltip /><Bar dataKey="stock" name="Stock units" fill="#159a82" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer> : <EmptyChart />}
        </Panel>
        <Panel title="Largest product positions" subtitle="Estimated inventory value based on synthetic costs">
          {highestStock.length ? <ResponsiveContainer width="100%" height={320}><BarChart data={highestStock} layout="vertical" margin={{ left: 5 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" /><YAxis type="category" dataKey="product_id" width={70} /><Tooltip formatter={(value, key, props) => key === "Stock" ? value : money(value)} /><Bar dataKey="quantity_on_hand" name="Stock" fill="#7255ce" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer> : <EmptyChart />}
        </Panel>
        <Panel title="Stockout risk" subtitle={`Products with less than ${summary?.stockout_risk_coverage_days ?? 30} days of recent observed demand`}>
          {products.length ? <div className="risk-list">{products.filter((item) => item.stockout_risk).slice(0, 12).map((item) => <div className="risk-row" key={item.product_id}><span><strong>{item.product_name}</strong><small>{item.product_id}</small></span><b>{item.quantity_on_hand.toLocaleString()} units</b></div>)}</div> : <EmptyChart />}
        </Panel>
      </div>
      <div className="notice-strip"><strong>Assumption</strong><span>The stock snapshot, replenishment scenarios, and unit costs are synthetic; use this view to demonstrate analytics only until real stock and purchasing history are loaded.</span></div>
    </>
  );
}
