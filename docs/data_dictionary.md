# Data dictionary

## Provenance

The source is UCI Online Retail II (https://archive.ics.uci.edu/dataset/502/online+retail+ii), a historical UK-based online retail transaction workbook. The source has 1,067,371 rows in two sheets. Its fields describe invoice lines, product codes/descriptions, positive or negative quantities, invoice timestamps, unit prices, optional customer IDs, and country. There are no observed stock balances, warehouse locations, product categories, supplier identities, supplier lead times, purchase costs, or stockout events.

The ETL keeps observed positive sales and removes cancellation/return rows, non-positive quantities/prices, invalid keys/dates, and exact duplicates. The original workbook is never rewritten. Synthetic fields are generated with seed `42`; their `data_source` columns identify the demonstration provenance.

## Relational tables

| Table | Grain / primary key | Important fields and provenance |
|---|---|---|
| `categories` | One inferred category; `category_id` | Description-keyword category inference; **synthetic** |
| `suppliers` | One demonstration supplier; `supplier_id` | Generated supplier labels; **synthetic** |
| `warehouses` | One demonstration warehouse; `warehouse_id` | Generated names and regions; **synthetic** |
| `products` | One observed `StockCode`; `product_id` | `description`, median observed `unit_price`; inferred `category_id`, assigned `supplier_id`, estimated unit cost are **synthetic** |
| `orders` | One observed invoice; `order_id` | `order_date`, `customer_country` observed; warehouse allocation **synthetic** |
| `order_items` | One cleaned observed invoice line; `order_item_id` | Product, positive quantity, price, line revenue observed; estimated COGS **synthetic** |
| `inventory` | Product × warehouse × snapshot date | Quantity on hand, unit cost, snapshot, and warehouse distribution **synthetic** |
| `supplier_deliveries` | One generated delivery; `delivery_id` | Order/promise/actual dates, lead time, and on-time flag **synthetic** |
| `daily_sales` | Product × warehouse × calendar date | Units and line revenue observed; warehouse allocation and estimated COGS **synthetic** |

`inventory` is a generated snapshot referenced to the latest date in the historical dataset, not to today's date. Product, category, supplier, and warehouse foreign keys are enforced by the schema.

## Source workbook fields and expected types

| Workbook column | Observed type | Meaning |
|---|---|---|
| `Invoice` | Text/object | Invoice identifier; values beginning with `C` indicate cancellations |
| `StockCode` | Text/object | Product code |
| `Description` | Text/object, can be missing | Product description |
| `Quantity` | Integer | Units on invoice; returns may be negative |
| `InvoiceDate` | Date/time | Invoice timestamp |
| `Price` | Float | Observed unit price in GBP |
| `Customer ID` | Float, frequently missing | Optional customer identifier |
| `Country` | Text | Customer country |

## Derived dataset files

- `cleaned_transactions.csv`: observed cleaned invoice lines; includes `line_revenue = quantity × unit_price`.
- `categories.csv`, `products.csv`, `warehouses.csv`, `suppliers.csv`, `orders.csv`, `order_items.csv`, `inventory.csv`, `supplier_deliveries.csv`, `daily_sales.csv`: load-ready relational extracts, with generated fields explicitly labeled.
- `forecasts.csv`: optional model outputs; future actual demand is null because it is not present in the source.
- `reports/data_quality.json`: source shape, missing values, dtypes, duplicate/invalid counts, outlier flags, and cleaning actions.
