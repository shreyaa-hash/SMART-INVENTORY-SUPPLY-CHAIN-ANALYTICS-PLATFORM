import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import KpiCard from "../components/KpiCard.jsx";
import Panel, { EmptyChart } from "../components/Panel.jsx";

const money = (value) => new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 }).format(value || 0);
const colors = ["#3157d5", "#159a82", "#f0a03b", "#7255ce", "#db5b66", "#7dadf5", "#8fcb9b"];

export default function CustomerAnalytics({ customer }) {
  const summary = customer?.summary ?? {};
  const segmentCounts = Object.entries(customer?.segment_counts ?? {}).map(([name, count]) => ({ name, count }));
  const segmentRevenue = Object.entries(customer?.segment_revenue ?? {}).map(([name, value]) => ({ name, value }));
  const topCustomers = customer?.top_customers ?? [];
  const rfmSummary = customer?.rfm_summary ?? [];

  return (
    <>
      <div className="kpi-grid kpi-grid-four">
        <KpiCard label="Identifiable customers" value={Number(summary.total_identifiable_customers || 0).toLocaleString()} note="Non-null customer IDs only" icon="👥" />
        <KpiCard label="Repeat customer rate" value={summary.repeat_customer_rate == null ? "—" : `${(summary.repeat_customer_rate * 100).toFixed(1)}%`} note="Customers with more than one order" icon="↻" />
        <KpiCard label="Avg customer value" value={summary.average_customer_monetary_value == null ? "—" : money(summary.average_customer_monetary_value)} note="Observed revenue per identifiable customer" icon="£" />
        <KpiCard label="Purchase frequency" value={summary.purchase_frequency == null ? "—" : summary.purchase_frequency.toFixed(2)} note="Average orders per customer" icon="◫" />
      </div>

      <div className="chart-grid">
        <Panel title="Customer segmentation distribution" subtitle="RFM-based customer segmentation using observed transaction history">
          {segmentCounts.length ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={segmentCounts}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" name="Customers" fill="#3157d5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <EmptyChart />}
        </Panel>

        <Panel title="Revenue by segment" subtitle="Observed transaction value by customer segment">
          {segmentRevenue.length ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={segmentRevenue} dataKey="value" nameKey="name" innerRadius={58} outerRadius={92} paddingAngle={4} label={({ name }) => name}>
                  {segmentRevenue.map((entry, index) => <Cell key={`${entry.name}-${index}`} fill={colors[index % colors.length]} />)}
                </Pie>
                <Tooltip formatter={(value) => money(value)} />
              </PieChart>
            </ResponsiveContainer>
          ) : <EmptyChart />}
        </Panel>

        <Panel title="Top customers" subtitle="Highest observed customer value">
          {topCustomers.length ? (
            <div className="risk-list">
              {topCustomers.map((customerRow) => (
                <div className="risk-row" key={customerRow.customer_id}>
                  <span>
                    <strong>Customer {customerRow.customer_id}</strong>
                    <small>{customerRow.segment}</small>
                  </span>
                  <b>{money(customerRow.monetary)}</b>
                </div>
              ))}
            </div>
          ) : <EmptyChart />}
        </Panel>

        <Panel title="RFM summary" subtitle="Recency, frequency, and monetary profile for identifiable customers">
          {rfmSummary.length ? (
            <div className="supplier-table">
              <div className="table-header">
                <span>Customer</span>
                <span>Recency</span>
                <span>Freq.</span>
                <span>Value</span>
              </div>
              {rfmSummary.slice(0, 8).map((row) => (
                <div className="table-row" key={row.customer_id}>
                  <span>{row.customer_id}</span>
                  <span>{row.recency_days}d</span>
                  <span>{row.frequency}</span>
                  <b>{money(row.monetary)}</b>
                </div>
              ))}
            </div>
          ) : <EmptyChart />}
        </Panel>
      </div>

      <div className="notice-strip">
        <strong>Provenance</strong>
        <span>{customer?.provenance || "Segments only include customers with a valid non-null customer ID in the cleaned sales data; missing IDs remain excluded from the customer view."}</span>
      </div>
    </>
  );
}
