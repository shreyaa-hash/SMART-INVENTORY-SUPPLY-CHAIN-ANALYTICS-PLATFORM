# Smart Inventory & Supply Chain Analytics

A locally runnable retail analytics workflow that ingests public sales transactions, validates and cleans the source, generates clearly labeled demonstration-only operational data, loads normalized relational tables, evaluates demand forecasts, and serves database-backed insights through FastAPI and React.

> **Important data limitation:** The selected public source does not include physical inventory, purchase costs, warehouse assignments, suppliers, delivery events, or product categories. Those fields are generated with fixed random seed `42` and marked `synthetic`. This is a working analytics demonstration, not a reconstruction of actual company operations. Replace synthetic attributes with the retailer's own operational records before using replenishment or margin recommendations.

## Business problem and objectives

The application demonstrates answers to questions about sales performance, low/high inventory, working capital, stock risk, supplier performance, and short-horizon demand. It is designed to help teams:

- Identify observed revenue and unit-sales trends by product, inferred category, country, and month.
- Estimate low-stock, overstock, coverage, ABC class, dead stock, and inventory value using the generated stock snapshot.
- Compare four daily-demand forecasting approaches using a chronological holdout.
- Generate configurable restock, future-risk, slow/dead-stock, increasing-demand, and supplier-risk suggestions.
- Explore the results in a responsive six-page dashboard or via a documented API.

## Features

- **Data ingestion:** Fetches the original UCI workbook; stores the original archive and workbook under `data/raw/`.
- **Provenance separation:** Synthetic-only entities are also written to `data/synthetic/`; database-ready observed facts and synthetic joins are in `data/processed/`.
- **Preprocessing:** Detects missing values, exact duplicates, invalid dates and keys, cancellations, non-positive quantities/prices, and IQR outliers. Outlier rows are flagged, not silently deleted.
- **Normalized database:** SQLAlchemy models and MySQL 8 DDL cover products, categories, orders, line items, inventory, warehouses, suppliers, deliveries, and daily sales; SQLite is used for zero-configuration local tests.
- **Analysis:** Revenue, supplier, inventory, ABC/XYZ, sell-through, gross-profit estimate, holding cost, and turnover calculations have explicit assumptions in [docs/business_metrics.md](./docs/business_metrics.md).
- **Forecasting:** Naive, 7-day moving-average, Random Forest, and Gradient Boosting models; chronological training/validation, MAE/RMSE/MAPE, recursive 7/30/90-day forecasts, insufficient-history warnings, and joblib model artifacts.
- **Recommendations:** Configurable coverage, service level, history, and supplier reliability thresholds.
- **Dashboard:** Executive overview, inventory, sales, supplier, forecasting, and action-queue pages. Charts query the backend; search, priority filtering, date filters, and CSV export are implemented.
- **Reports:** Machine-readable data quality/model evaluation, EDA charts, and evidence-based observations under `reports/`.

## Architecture

```mermaid
flowchart LR
  UCI["UCI Online Retail II<br/>observed transactions"] --> Raw["data/raw<br/>original workbook"]
  Raw --> ETL["Python preprocessing<br/>quality + feature engineering"]
  Synthetic["Seeded synthetic demo entities<br/>stock, costs, sites, suppliers"] --> ETL
  ETL --> CSV["data/processed<br/>cleaned CSV tables"]
  CSV --> DB["MySQL 8<br/>or local SQLite"]
  DB --> API["FastAPI + SQLAlchemy"]
  API --> UI["React + Vite + Recharts"]
  CSV --> EDA["EDA / reports"]
  DB --> Forecast["Chronological forecasting<br/>scikit-learn + joblib"]
  Forecast --> API
  API --> Rules["Configurable recommendations"]
```

## Technology stack

| Area | Tools |
|---|---|
| Data | Python, pandas, NumPy, SciPy, Matplotlib, Seaborn |
| Database | MySQL 8, SQLAlchemy 2, PyMySQL; SQLite for local tests |
| ML | scikit-learn Random Forest and Gradient Boosting, joblib |
| API | FastAPI, Pydantic, Uvicorn |
| Web | React 18, Vite, Recharts, plain responsive CSS |
| Tests | pytest, FastAPI TestClient, Node built-in test runner |

No paid API, database, or AI service is used. The UI has no external font/API dependency.

## Dataset source and findings

**UCI Online Retail II:** [dataset page](https://archive.ics.uci.edu/dataset/502/online+retail+ii), [download archive](https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip). The workbook contains two sheets with 525,461 and 541,910 rows. Observed columns are `Invoice`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `Price`, `Customer ID`, and `Country`; source types and missing counts are in [reports/data_quality.json](./reports/data_quality.json).

The inspected run contained 1,067,371 source rows, 34,335 exact duplicates, 25,123 excluded invalid/cancellation rows, and 1,007,913 cleaned positive sales lines. The cleaned observed line revenue is GBP 20,476,260.43 over 2009-12-01–2011-12-09. November 2011 has the highest observed monthly revenue in this cleaned run. Findings and charts are documented in [reports/business_insights.md](./reports/business_insights.md). These are computed from the downloaded workbook, not hardcoded dashboard data.

## Database schema and SQL

The relational DDL and index definitions live in [sql/schema.sql](./sql/schema.sql) and [sql/indexes.sql](./sql/indexes.sql). Run example MySQL 8 analyses from [sql/analytics_queries.sql](./sql/analytics_queries.sql), including monthly/quarterly revenue, category and product ranks, 90-day demand and stock cover, supplier reliability, monthly growth with `LAG`, ABC classification, dead-stock checks, and moving averages. Fields that depend on synthetic operations are explicitly identified in the SQL comments.

See [docs/data_dictionary.md](./docs/data_dictionary.md) for table grain, keys, source columns, and synthetic-vs-observed provenance.

## EDA and business insights

Run `python -m src.analytics.eda` to produce seven purpose-built charts (monthly trend, top products, inferred category revenue, stock vs observed sales, generated supplier reliability, seasonality, and sales correlations) and refresh `reports/business_insights.md`. The interpretations explain the business relevance and limits of each result. The inventory and supplier charts are demonstrations because the source has no actual operations data.

## Forecasting methodology and evaluation

Daily units are aggregated by product/date, absent dates are filled with zero, and lag/rolling/calendar predictors use only historical values. Validation is a trailing chronological holdout, never a shuffled split. Candidate models are the last-value naive baseline, 7-day mean baseline, Random Forest, and Gradient Boosting. MAPE excludes zero-actual days; MAE and RMSE are also recorded. The selected model is the lowest-validation-MAE model. Forecast confidence bounds, when shown, are only approximate empirical holdout residual quantiles; they are not calibrated.

Batch evaluation is intentionally limited to the ten highest-unit products by default; change `product_limit` when calling `run_batch`. Per-product model comparison and forecasts are written to `reports/model_evaluation.json` and `data/processed/forecasts.csv`; joblib files go to `models/`. The latest measured results are preserved in [reports/model_evaluation.json](./reports/model_evaluation.json). Data ends in 2011, so these are historical demonstration forecasts, not current-day demand plans.

On the current run, 9 of the selected 10 products met the 90-calendar-day minimum. Across those 9 products, unweighted mean validation MAE was 323.63 (Naive), 145.85 (Moving Average), 139.84 (Random Forest), and 98.07 (Gradient Boosting) units/day; the selected model differed by product. Average MAPE is high and sensitive to intermittent/low-volume demand (the stored report includes exact per-product scores), so this result must not be interpreted as a general guarantee that Gradient Boosting will outperform for a new retailer.

## Dashboard screenshots

Run the app locally to view the dashboard. EDA visual evidence is in [reports/figures/](./reports/figures/). Dashboard captures can be saved here after launching the local web UI; no pre-generated dashboard screenshot is represented as a live production result.

## Setup

### Prerequisites

- Python 3.10 or later.
- Node.js 20 or later and npm.
- MySQL 8 for the requested production database path (the MySQL service must be running).
- Internet access once to fetch the public dataset.

### 1. Install Python and download/process the source

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.download_dataset
python -m src.data_processing.pipeline
python -m src.analytics.eda
python -m src.forecasting.run_forecasts
```

The raw workbook is never edited. To rerun with a new seed, use `python -m src.data_processing.pipeline --seed 42` (42 is the documented default).

### 2. Configure MySQL 8

Create a database and least-privilege local application account using an administrative MySQL session. Choose your own password; do not commit it:

```sql
CREATE DATABASE smart_inventory CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'inventory_user'@'localhost' IDENTIFIED BY 'use-a-local-strong-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, ALTER ON smart_inventory.* TO 'inventory_user'@'localhost';
```

Copy `.env.example` to `.env`, replace the local database password, and keep `.env` untracked:

```powershell
Copy-Item .env.example .env
```

Then load the cleaned and synthetic tables into MySQL:

```powershell
python -m src.database.load_data
```

SQLAlchemy creates the normalized tables and keys. Alternatively, execute `sql/schema.sql` and `sql/indexes.sql` first using the configured database. The MySQL URL is configurable through `DATABASE_URL`.

**No-MySQL development option:** If `DATABASE_URL` is unset, the loader and API use `sqlite:///./data/smart_inventory.db`; this is for local evaluation, not the required MySQL deployment configuration. To force the option in PowerShell set `$env:DATABASE_URL = "sqlite:///./data/smart_inventory.db"` before running the loader/API.

### 3. Run the API

```powershell
python -m uvicorn backend.app.main:app --reload
```

Open `http://localhost:8000/docs` for interactive API documentation. API routes and parameters are listed in [docs/api.md](./docs/api.md).

### 4. Run the web dashboard

In another PowerShell terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). Configure `VITE_API_BASE_URL` at build time if the API is not at `http://localhost:8000`. The API allows both `localhost` and `127.0.0.1` Vite origins by default; configure `CORS_ORIGINS` for another local origin.

### 5. Run checks

```powershell
python -m pytest -q
Set-Location frontend
npm test
npm run build
```

## Data/API integration

The backend runs SQLAlchemy queries against the configured database. The React client obtains all KPI, table, and chart payloads from those API endpoints; there are no hardcoded business-value fixtures. Forecast calls fit and validate a selected product's historical demand on request, persist its joblib artifact, and return a clear warning when the minimum history requirement is not met. CSV export serializes the filtered recommendation records shown on screen.

## Limitations

- The source captures historical transactions through 2011 and has no current inventory/purchasing/supplier history.
- Returned invoices and cancellations are excluded from sales; customer IDs are optional and are not used in analytics.
- Product category is inferred from description keywords. A category without matching words is `General`.
- Warehouse allocation, current stock, supplier identities/deliveries, and costs are reproducible scenarios only.
- Gross profit, inventory value/turnover, supplier reliability, stock risk, and reorder proposals are illustrative until actual operational records replace those scenarios.
- The project demonstrates MySQL 8-compatible schema/driver integration. Provide a locally configured MySQL account to run the MySQL loading path; SQLite backs the automated local integration tests.
- Forecast accuracy is product-specific and may be weak; a validation metric is not a guarantee of future performance.

## Future improvements

- Replace synthetic entity generation with purchase orders, on-hand snapshots, costs, warehouse transfers, and supplier receipts from an ERP.
- Add inventory history and explicit stockout events to compute observed stockout rate and average inventory accurately.
- Add stronger category governance, supplier/product contracts, and source-system lineage.
- Tune reorder/service levels with carrying and shortage costs, and evaluate forecasts over several rolling-origin windows.
- Add user authentication and role-based access if exposing the API beyond a trusted local network.
- Add automated browser-based visual regression and scheduled retraining after sufficiently recent actual data is available.
