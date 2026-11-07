import { useCallback, useEffect, useMemo, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import ExecutiveOverview from "./pages/ExecutiveOverview.jsx";
import InventoryAnalytics from "./pages/InventoryAnalytics.jsx";
import SalesAnalytics from "./pages/SalesAnalytics.jsx";
import ProductAnalytics from "./pages/ProductAnalytics.jsx";
import CustomerAnalytics from "./pages/CustomerAnalytics.jsx";
import SupplierAnalytics from "./pages/SupplierAnalytics.jsx";
import DemandForecasting from "./pages/DemandForecasting.jsx";
import Recommendations from "./pages/Recommendations.jsx";
import DataQuality from "./pages/DataQuality.jsx";
import { apiGet } from "./services/api.js";

const pageMeta = {
  overview: ["Executive overview", "Performance snapshot and commercial trends"],
  sales: ["Sales analytics", "Observed demand, products, categories, and customer regions"],
  products: ["Product analytics", "Revenue and mix by product and category"],
  customer: ["Customer analytics", "RFM segmentation and repeat-customer economics"],
  inventory: ["Inventory analytics", "Stock health, coverage, and replenishment exposure"],
  suppliers: ["Supplier analytics", "Demonstration lead-time and delivery reliability"],
  forecast: ["Demand forecasting", "Chronological model comparison and forward demand"],
  recommendations: ["Business recommendations", "Prioritized actions for inventory planners"],
  quality: ["Data quality and provenance", "Audit of observed, derived, and synthetic data"],
};

function queryDates(dates) {
  return { start_date: dates.start || undefined, end_date: dates.end || undefined };
}

export default function App() {
  const [activePage, setActivePage] = useState("overview");
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dateRange, setDateRange] = useState({ start: "", end: "" });

  const loadPage = useCallback(async (page, force = false) => {
    const rangeKey = `${dateRange.start}:${dateRange.end}`;
    if (!force && data[page] && (!["overview", "sales"].includes(page) || data[page]._range === rangeKey)) return;
    setLoading(true);
    setError("");
    try {
      let payload;
      if (page === "overview") {
        const dates = queryDates(dateRange);
        const [overview, monthly, categories, topProducts, warehouses] = await Promise.all([
          apiGet("/api/dashboard/overview", dates),
          apiGet("/api/sales/monthly", dates),
          apiGet("/api/sales/categories", dates),
          apiGet("/api/sales/products", { ...dates, limit: 20 }),
          apiGet("/api/warehouses", dates),
        ]);
        payload = { overview, monthly, categories, topProducts, warehouses };
      } else if (page === "inventory") {
        const [summary, products, warehouses] = await Promise.all([
          apiGet("/api/inventory/summary"),
          apiGet("/api/inventory/products", { limit: 5000 }),
          apiGet("/api/warehouses"),
        ]);
        payload = { summary, products, warehouses };
      } else if (page === "sales") {
        const dates = queryDates(dateRange);
        const [monthly, categories, topProducts, regions] = await Promise.all([
          apiGet("/api/sales/monthly", dates),
          apiGet("/api/sales/categories", dates),
          apiGet("/api/sales/products", { ...dates, limit: 20 }),
          apiGet("/api/sales/regions", { ...dates, limit: 20 }),
        ]);
        payload = { monthly, categories, topProducts, regions };
      } else if (page === "products") {
        const dates = queryDates(dateRange);
        const [topProducts, categories] = await Promise.all([
          apiGet("/api/sales/products", { ...dates, limit: 20 }),
          apiGet("/api/sales/categories", dates),
        ]);
        payload = { topProducts, categories };
      } else if (page === "customer") {
        const dates = queryDates(dateRange);
        payload = { customer: await apiGet("/api/customers/segments", dates) };
      } else if (page === "suppliers") {
        payload = { suppliers: await apiGet("/api/suppliers/performance") };
      } else if (page === "forecast") {
        payload = { products: (await apiGet("/api/products", { limit: 5000 })).items };
      } else if (page === "quality") {
        payload = { quality: await apiGet("/api/data-quality") };
      } else {
        payload = { recommendations: await apiGet("/api/recommendations", { limit: 5000 }) };
      }
      if (page === "overview" || page === "sales") payload._range = rangeKey;
      setData((current) => ({ ...current, [page]: payload }));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  }, [data, dateRange]);

  useEffect(() => {
    loadPage(activePage);
  }, [activePage, dateRange, loadPage]);

  const title = pageMeta[activePage][0];
  const dateFilters = useMemo(
    () => ["overview", "sales", "products", "customer"].includes(activePage),
    [activePage],
  );

  const refreshRecommendations = () => {
    setData((current) => ({ ...current, recommendations: undefined }));
    loadPage("recommendations", true);
  };

  return (
    <div className="app-shell">
      <Sidebar active={activePage} onChange={setActivePage} />
      <main className="main-content">
        <header className="topbar">
          <div className="page-title"><span>ANALYTICS WORKSPACE</span><h1>{title}</h1><p>{pageMeta[activePage][1]}</p></div>
          <div className="topbar-actions">
            {dateFilters && <div className="date-filter"><label>From <input type="date" value={dateRange.start} onChange={(event) => setDateRange((value) => ({ ...value, start: event.target.value }))} /></label><label>To <input type="date" value={dateRange.end} onChange={(event) => setDateRange((value) => ({ ...value, end: event.target.value }))} /></label></div>}
            <button className="button secondary refresh-button" onClick={() => loadPage(activePage, true)} aria-label="Refresh dashboard data">↻ Refresh</button>
          </div>
        </header>
        <div className="provenance-banner"><span className="banner-dot" /><span><b>PUBLIC RETAIL DATASET</b> · UCI Online Retail II</span><span className="banner-divider" /><span>Stock, cost, warehouse, supplier, and inferred category data are synthetic demonstrations.</span></div>
        {loading && <div className="loading-bar" aria-label="Loading data"><span /></div>}
        {error && <div className="error-banner" role="alert"><span>{error}</span><button className="button secondary" onClick={() => loadPage(activePage, true)}>Retry</button></div>}
        <div className="page-body">
          {activePage === "overview" && data.overview && <ExecutiveOverview {...data.overview} />}
          {activePage === "sales" && data.sales && <SalesAnalytics {...data.sales} />}
          {activePage === "products" && data.products && <ProductAnalytics {...data.products} />}
          {activePage === "customer" && data.customer && <CustomerAnalytics customer={data.customer} />}
          {activePage === "inventory" && data.inventory && <InventoryAnalytics {...data.inventory} />}
          {activePage === "suppliers" && data.suppliers && <SupplierAnalytics {...data.suppliers} />}
          {activePage === "forecast" && data.forecast && <DemandForecasting {...data.forecast} />}
          {activePage === "recommendations" && data.recommendations && <Recommendations {...data.recommendations} onRefresh={refreshRecommendations} />}
          {activePage === "quality" && data.quality && <DataQuality quality={data.quality} />}
          {!data[activePage] && !loading && !error && <div className="empty-page">Choose a page to load live analytics.</div>}
        </div>
        <footer className="app-footer"><span>Stockwise · Smart Inventory Analytics</span><span>Local data pipeline · FastAPI · MySQL-compatible</span></footer>
      </main>
    </div>
  );
}
