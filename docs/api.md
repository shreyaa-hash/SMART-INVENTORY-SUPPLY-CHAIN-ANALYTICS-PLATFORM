# API

Run the API from the repository root with `python -m uvicorn backend.app.main:app --reload`. Interactive OpenAPI docs are served by FastAPI at `http://localhost:8000/docs`; OpenAPI JSON is at `/openapi.json`.

| Method / path | Purpose |
|---|---|
| `GET /api/health` | Database connectivity |
| `GET /api/dashboard/overview?start_date=&end_date=` | Revenue, invoices, product count, synthetic inventory/cost KPIs |
| `GET /api/sales/monthly?start_date=&end_date=` | Monthly observed revenue, units, estimated profit, and growth |
| `GET /api/sales/products?limit=20&start_date=&end_date=` | Product revenue and units; limit 1–100 |
| `GET /api/sales/categories?start_date=&end_date=` | Observed revenue grouped by inferred synthetic category |
| `GET /api/sales/regions?limit=20&start_date=&end_date=` | Revenue by observed customer country |
| `GET /api/sales/history/{product_id}?days=180` | Recent daily product demand; days 7–730 |
| `GET /api/customers/segments?start_date=&end_date=` | RFM summary, customer segmentation distribution, top-value customers |
| `GET /api/data-quality` | Data-cleaning validation, duplicate checks, missing IDs, and provenance summary |
| `GET /api/inventory/summary` | Demo stock summary, low/overstock counts, dead-stock estimate |
| `GET /api/inventory/products?limit=5000` | Product stock, value, ABC class, stock-risk proxy |
| `GET /api/inventory/low-stock?limit=100` | Stock at or below 14 days of recent demand |
| `GET /api/inventory/overstock?limit=100` | Stock above configured coverage threshold |
| `GET /api/suppliers/performance` | Synthetic delivery reliability and lead-time measures |
| `GET /api/forecast/{product_id}?horizon_days=90` | Product forecast, model validation, history warnings; horizon 7–90 |
| `GET /api/recommendations?search=&priority=&limit=100` | Replenishment, overstock, demand, dead-stock, and supplier-risk rules |
| `GET /api/products?search=&offset=0&limit=100` | Paginated product list; max page size 5,000 |
| `GET /api/warehouses?start_date=&end_date=` | Warehouse inventory/revenue on synthetic assignments |

Database failures return HTTP 503 with a logged server-side error; invalid filter values return HTTP 422. No credentials are returned by API responses.
