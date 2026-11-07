const pages = [
  ["overview", "Executive overview", "01"],
  ["sales", "Sales analytics", "02"],
  ["products", "Product analytics", "03"],
  ["customer", "Customer analytics", "04"],
  ["inventory", "Inventory analytics", "05"],
  ["suppliers", "Supplier analytics", "06"],
  ["forecast", "Demand forecasting", "07"],
  ["recommendations", "Recommendations", "08"],
  ["quality", "Data quality", "09"],
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
