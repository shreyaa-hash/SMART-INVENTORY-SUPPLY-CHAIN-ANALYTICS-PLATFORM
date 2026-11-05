# Business insights from observed retail transactions

## Scope and provenance
Observed measures come from the UCI Online Retail II public workbook (GBP prices, invoice lines, 2009–2011). Cancelled invoices, non-positive quantities/prices, invalid keys/dates, and exact duplicates were excluded. Inventory, unit costs, categories, suppliers, delivery events, and warehouse assignments are synthetic demonstrations and must not be interpreted as company history.

## Findings
- The cleaned dataset contains 1,007,913 positive, non-cancelled observed order lines from 2009-12-01 through 2011-12-09.
- Observed line revenue totals GBP 20,476,260.43; all amounts use the source's recorded unit prices and quantities.
- Monthly observed revenue peaks in 2011-11 at GBP 1,503,866.78; this is historical descriptive evidence, not a forward projection.
- The top 10 products contribute GBP 2,072,733.78 in observed line revenue. Product ranking is based on actual UCI transaction lines.
- Category labels are inferred from product descriptions for demonstration only; their revenue aggregates are observed transactions grouped by those synthetic labels.
- The synthetic inventory snapshot has 0 products with zero demo stock and 4,916 with positive demo stock; it is not measured company stock.
- Synthetic supplier on-time delivery rates range from 34.8% to 77.8%; these are reproducible scenarios, not measured supplier performance.
- Average line revenue is highest in calendar month 9; the two-year history is short, so seasonality should be treated as exploratory.
- The quantity/revenue correlation is 0.81 and price/revenue correlation is 0.25; correlations are descriptive, not causal.

## Visual evidence
- [category_revenue](./figures/category_revenue.png)
- [monthly_revenue](./figures/monthly_revenue.png)
- [monthly_seasonality](./figures/monthly_seasonality.png)
- [sales_correlation](./figures/sales_correlation.png)
- [stock_vs_sales](./figures/stock_vs_sales.png)
- [supplier_reliability](./figures/supplier_reliability.png)
- [top_products_revenue](./figures/top_products_revenue.png)

## Decisions to validate with real operational data
- Replace the synthetic stock snapshot, purchase costs, warehouse mapping, and supplier events before using reorder or margin recommendations operationally.
- Use actual purchasing and stockout-event history to calibrate safety stock and holding-cost assumptions.
- Use a chronological holdout and compare forecast errors by product before automating replenishment.
