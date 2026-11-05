export default function KpiCard({ label, value, note, icon }) {
  return (
    <article className="kpi-card">
      <div className="kpi-top">
        <span className="kpi-label">{label}</span>
        <span className="kpi-icon" aria-hidden="true">{icon}</span>
      </div>
      <strong className="kpi-value">{value}</strong>
      {note && <span className="kpi-note">{note}</span>}
    </article>
  );
}
