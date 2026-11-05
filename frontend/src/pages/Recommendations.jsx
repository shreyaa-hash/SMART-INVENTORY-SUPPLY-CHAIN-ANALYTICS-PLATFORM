import { useMemo, useState } from "react";
import { downloadCsv } from "../services/api.js";
import Panel from "../components/Panel.jsx";

const priorities = ["All priorities", "Critical", "High", "Medium", "Low"];

export default function Recommendations({ recommendations, onRefresh }) {
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("All priorities");
  const [page, setPage] = useState(0);
  const pageSize = 25;
  const rows = useMemo(() => recommendations.filter((item) =>
    (!search || `${item.product_name} ${item.product_id}`.toLowerCase().includes(search.toLowerCase()))
    && (priority === "All priorities" || item.priority === priority),
  ), [recommendations, search, priority]);
  const pageCount = Math.ceil(rows.length / pageSize);
  const visibleRows = rows.slice(page * pageSize, (page + 1) * pageSize);
  return (
    <Panel title="Action queue" subtitle="Rule-based actions from demo stock and observed product demand">
      <div className="filter-row recommendation-filters">
        <input aria-label="Search recommendations" placeholder="Search product or ID" value={search} onChange={(event) => { setSearch(event.target.value); setPage(0); }} />
        <select aria-label="Filter by priority" value={priority} onChange={(event) => { setPriority(event.target.value); setPage(0); }}>{priorities.map((item) => <option key={item}>{item}</option>)}</select>
        <button className="button secondary" onClick={onRefresh}>Refresh</button>
        <button className="button primary" onClick={() => downloadCsv("inventory-recommendations.csv", rows)} disabled={!rows.length}>Download CSV</button>
      </div>
      <div className="recommendation-list">
        {rows.length ? visibleRows.map((item) => <article className="recommendation-card" key={item.product_id}>
          <div className="recommendation-title"><span className={`priority priority-${item.priority.toLowerCase()}`}>{item.priority}</span><span><strong>{item.product_name}</strong><small>{item.product_id}</small></span><b className="recommendation-qty">{item.recommended_reorder_quantity.toLocaleString()}<small> suggested units</small></b></div>
          <p>{item.reason}</p>
          <div className="recommendation-metrics"><span>Stock <b>{item.current_stock == null ? "—" : item.current_stock.toLocaleString()}</b></span><span>30d demand <b>{item.predicted_demand_30d == null ? "—" : item.predicted_demand_30d.toFixed(1)}</b></span><span>Reorder point <b>{item.reorder_point == null ? "—" : item.reorder_point.toFixed(1)}</b></span><span>Coverage <b>{item.inventory_coverage_days == null ? "—" : `${item.inventory_coverage_days} days`}</b></span></div>
          <small className="provenance">{item.data_source}</small>
        </article>) : <div className="empty-chart">No recommendations match these filters.</div>}
      </div>
      {rows.length > 0 && <div className="pagination-controls">
        <span>Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, rows.length)} of {rows.length}</span>
        <div>
          <button className="button secondary" onClick={() => setPage((value) => Math.max(0, value - 1))} disabled={page === 0}>Previous</button>
          <button className="button secondary" onClick={() => setPage((value) => Math.min(pageCount - 1, value + 1))} disabled={page >= pageCount - 1}>Next</button>
        </div>
      </div>}
      <div className="notice-strip warning"><strong>Review before action</strong><span>Recommendations use synthetic on-hand stock, supplier lead times, and configurable demonstration thresholds. They are not purchase orders.</span></div>
    </Panel>
  );
}
