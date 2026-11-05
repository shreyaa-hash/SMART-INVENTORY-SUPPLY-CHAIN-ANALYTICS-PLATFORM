# Business metric assumptions

All currency values are GBP as recorded in the source. Observed revenue is the sum of cleaned quantity × recorded unit price. Costs, stock values, inventory performance, and supplier performance are estimates or synthetic demonstration inputs.

| Metric | Formula | Qualification |
|---|---|---|
| Inventory turnover | COGS ÷ average inventory value | COGS uses a generated unit-cost estimate; the available stock is a synthetic snapshot, not historical average stock. Null when the denominator is zero. |
| Days inventory outstanding | Average inventory value ÷ COGS × days | 365-day convention; same synthetic cost/stock limitation; null for zero COGS. |
| Stockout rate | Stockout events ÷ demand events × 100 | True events are unavailable. UI shows a **zero-stock snapshot proxy**, never labels it as observed stockout rate. |
| Sell-through | Units sold ÷ units available × 100 | Units available is estimated stock plus observed units in the chosen period. Null for zero availability. |
| Gross profit | Observed revenue − estimated COGS | COGS is generated at 42–72% of median observed product price using seed 42. Not accounting profit. |
| Reorder point | Average daily demand × supplier lead time + safety stock | Demand from the most recent 90 historical days, lead time from synthetic delivery records; thresholds configurable. |
| Safety stock | `z × sqrt(L × σd² + d̄² × σL²)` | Uses daily demand and lead-time variability only when demand history meets the configured minimum; `z` is configurable. |
| Holding cost | Average inventory value × annual holding-cost rate | Defaults to 25% annually, configurable; unit costs and stock are synthetic. |
| ABC | Cumulative annual estimated consumption value: A through 80%, B through 95%, C remainder | Consumption value uses generated product costs and available historical data (not a full current fiscal year). |
| XYZ | Coefficient of variation of product demand: X ≤ 0.5, Y ≤ 1, Z > 1 | Thresholds are starter segmentation choices, not universal policy. |
| Dead stock | Positive snapshot units with no observed sale during the preceding 180 days | Evaluated relative to the final date in the historical workbook. |
| Forecast error | MAE, RMSE, MAPE | Chronological holdout; MAPE excludes zero actual days. Uncertainty is an approximate empirical residual range, not a calibrated interval. |

`TARGET_COVERAGE_DAYS`, `RECOMMENDATION_STOCK_MULTIPLIER`, `LOW_STOCK_COVERAGE_DAYS`, `STOCKOUT_RISK_COVERAGE_DAYS`, `SLOW_MOVING_DAYS`, `DEAD_STOCK_DAYS`, `SAFETY_STOCK_Z`, `FORECAST_MIN_HISTORY_DAYS`, `FORECAST_VALIDATION_DAYS`, `HOLDING_COST_RATE`, and `SUPPLIER_ON_TIME_THRESHOLD_PCT` are configurable in `.env`.
