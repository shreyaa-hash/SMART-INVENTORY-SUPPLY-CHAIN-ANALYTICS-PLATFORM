import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import KpiCard from "../components/KpiCard.jsx";
import Panel, { EmptyChart } from "../components/Panel.jsx";

export default function SupplierAnalytics({ suppliers }) {
  const avgLead = suppliers.length ? suppliers.reduce((sum, row) => sum + row.average_lead_time_days, 0) / suppliers.length : null;
  const avgOnTime = suppliers.length ? suppliers.reduce((sum, row) => sum + row.on_time_delivery_pct, 0) / suppliers.length : null;
  const delayed = suppliers.reduce((sum, row) => sum + row.deliveries * (1 - row.on_time_delivery_pct / 100), 0);
  const sorted = [...suppliers].sort((a, b) => a.on_time_delivery_pct - b.on_time_delivery_pct);
  return (
    <>
      <div className="kpi-grid kpi-grid-three">
        <KpiCard label="Suppliers" value={suppliers.length.toLocaleString()} note="Synthetic demonstration entities" icon="♧" />
        <KpiCard label="Average lead time" value={avgLead == null ? "—" : `${avgLead.toFixed(1)} days`} note="Generated delivery records" icon="◷" />
        <KpiCard label="On-time delivery" value={avgOnTime == null ? "—" : `${avgOnTime.toFixed(1)}%`} note="Synthetic promised vs actual dates" icon="✓" />
      </div>
      <div className="chart-grid">
        <Panel title="Supplier reliability ranking" subtitle="Lower on-time rate appears first">
          {sorted.length ? <ResponsiveContainer width="100%" height={350}><BarChart data={sorted} layout="vertical" margin={{ left: 30 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" domain={[0, 100]} unit="%" /><YAxis type="category" dataKey="supplier_name" width={190} tick={{ fontSize: 10 }} /><Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} /><Bar dataKey="on_time_delivery_pct" name="On-time rate" fill="#3157d5" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer> : <EmptyChart />}
        </Panel>
        <Panel title="Average lead time" subtitle="Synthetic supplier delivery history">
          {sorted.length ? <ResponsiveContainer width="100%" height={350}><BarChart data={sorted}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="supplier_id" tick={{ fontSize: 10 }} /><YAxis unit=" days" /><Tooltip formatter={(value) => `${Number(value).toFixed(1)} days`} /><Bar dataKey="average_lead_time_days" name="Average lead time" fill="#e29a37" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer> : <EmptyChart />}
        </Panel>
        <Panel title="Delivery delays" subtitle="Generated counts; not observed supplier performance">
          <div className="supplier-table">
            <div className="table-header"><span>Supplier</span><span>On-time</span><span>Lead time</span><span>Deliveries</span></div>
            {sorted.map((supplier) => <div className="table-row" key={supplier.supplier_id}><span>{supplier.supplier_name}</span><b className={supplier.on_time_delivery_pct < 80 ? "text-danger" : ""}>{supplier.on_time_delivery_pct.toFixed(1)}%</b><span>{supplier.average_lead_time_days.toFixed(1)}d</span><span>{supplier.deliveries}</span></div>)}
          </div>
          <p className="small-note">Estimated delayed delivery count across this demo: {Math.round(delayed).toLocaleString()}.</p>
        </Panel>
      </div>
      <div className="notice-strip warning"><strong>Demo only</strong><span>Supplier names, lead times, promised dates, and delivery outcomes are synthetic. Replace with procurement-system history before supplier decisions.</span></div>
    </>
  );
}
