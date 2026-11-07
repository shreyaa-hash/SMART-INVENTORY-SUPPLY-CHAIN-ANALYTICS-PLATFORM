import KpiCard from "../components/KpiCard.jsx";
import Panel, { EmptyChart } from "../components/Panel.jsx";

const pct = (value) => (value == null ? "—" : `${Number(value).toFixed(1)}%`);

export default function DataQuality({ quality }) {
  const metrics = quality ?? {};
  const checks = [
    { label: "Duplicate order IDs", value: metrics.duplicate_order_ids ?? 0, note: "Exact duplicates in order records" },
    { label: "Missing customer IDs", value: metrics.missing_customer_ids ?? 0, note: "Null customer records retained separately" },
    { label: "Invalid quantities", value: metrics.non_positive_quantity_rows ?? 0, note: "Rows with <= 0 quantity" },
    { label: "Invalid prices", value: metrics.negative_unit_price_rows ?? 0, note: "Rows with negative prices" },
    { label: "Return / cancelled rows", value: metrics.return_or_cancelled_rows_removed ?? 0, note: "Rows excluded from analytics" },
  ];

  return (
    <>
      <div className="kpi-grid kpi-grid-five">
        <KpiCard label="Observed orders" value={Number(metrics.observed_orders || 0).toLocaleString()} note="Valid cleaned transactions retained" icon="✓" />
        <KpiCard label="Data quality score" value={pct(metrics.data_quality_score_pct)} note="Post-cleaning quality check" icon="◌" />
        {checks.slice(0, 4).map((item) => (
          <KpiCard key={item.label} label={item.label} value={Number(item.value).toLocaleString()} note={item.note} icon="!" />
        ))}
      </div>

      <div className="chart-grid">
        <Panel title="Data-quality checks" subtitle="Validated values and exclusions from the cleaned retail dataset">
          {checks.length ? (
            <div className="risk-list">
              {checks.map((item) => (
                <div className="risk-row" key={item.label}>
                  <span>
                    <strong>{item.label}</strong>
                    <small>{item.note}</small>
                  </span>
                  <b>{Number(item.value).toLocaleString()}</b>
                </div>
              ))}
            </div>
          ) : <EmptyChart />}
        </Panel>

        <Panel title="Data provenance" subtitle="How observed, derived, and synthetic data are distinguished">
          <div className="risk-list">
            {(metrics.provenance || []).map((item, index) => (
              <div className="risk-row" key={`${item}-${index}`}>
                <span>
                  <strong>Note {index + 1}</strong>
                  <small>Audit trail</small>
                </span>
                <b>{item}</b>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </>
  );
}
