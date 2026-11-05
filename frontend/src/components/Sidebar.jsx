const pages = [
  ["overview", "Executive overview", "01"],
  ["inventory", "Inventory analytics", "02"],
  ["sales", "Sales analytics", "03"],
  ["suppliers", "Supplier analytics", "04"],
  ["forecast", "Demand forecasting", "05"],
  ["recommendations", "Recommendations", "06"],
];

export default function Sidebar({ active, onChange }) {
  return (
    <aside className="sidebar">
      <a className="brand" href="#" onClick={(event) => { event.preventDefault(); onChange("overview"); }}>
        <span className="brand-mark">S</span>
        <span><strong>Stockwise</strong><small>Inventory intelligence</small></span>
      </a>
      <div className="nav-caption">WORKSPACE</div>
      <nav aria-label="Dashboard pages">
        {pages.map(([id, name, number]) => (
          <button key={id} className={`nav-item ${active === id ? "active" : ""}`} onClick={() => onChange(id)}>
            <span className="nav-number">{number}</span><span>{name}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <span className="status-dot" /> Local analytics workspace
        <small>Observed retail + synthetic operations</small>
      </div>
    </aside>
  );
}
