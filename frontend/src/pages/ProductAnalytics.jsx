import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Panel, { EmptyChart } from "../components/Panel.jsx";

const money = (value) => new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 }).format(value || 0);

export default function ProductAnalytics({ topProducts = [], categories = [] }) {
  const products = [...(topProducts || [])].slice(0, 10);
  const categoryData = [...(categories || [])].slice(0, 12);

  return (
    <div className="chart-grid">
      <Panel title="Top products by revenue" subtitle="Observed product revenue from cleaned transactions">
        {products.length ? (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={products} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tickFormatter={(value) => `${Math.round(value / 1000)}k`} />
              <YAxis type="category" dataKey="description" width={100} tick={{ fontSize: 10 }} />
              <Tooltip formatter={(value) => money(value)} />
              <Bar dataKey="revenue" name="Revenue" fill="#3157d5" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : <EmptyChart />}
      </Panel>

      <Panel title="Revenue by category" subtitle="Observed sales grouped by inferred product category">
        {categoryData.length ? (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={categoryData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="category_name" tick={{ fontSize: 10 }} />
              <YAxis tickFormatter={(value) => `${Math.round(value / 1000)}k`} />
              <Tooltip formatter={(value) => money(value)} />
              <Bar dataKey="revenue" name="Revenue" fill="#159a82" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : <EmptyChart />}
      </Panel>

      <Panel title="Product ranking" subtitle="Top products by units sold">
        {products.length ? (
          <div className="risk-list">
            {products.map((item) => (
              <div className="risk-row" key={item.product_id}>
                <span>
                  <strong>{item.description}</strong>
                  <small>{item.product_id}</small>
                </span>
                <b>{Number(item.units || 0).toLocaleString()} units</b>
              </div>
            ))}
          </div>
        ) : <EmptyChart />}
      </Panel>
    </div>
  );
}
