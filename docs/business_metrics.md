# Business metric assumptions

All currency values are GBP as recorded in the source. Observed revenue is the sum of cleaned quantity × recorded unit price. Costs, stock values, inventory performance, and supplier performance are estimates or synthetic demonstration inputs.

| Metric | Formula | Qualification |
|---|---|---|
| Inventory turnover | COGS ÷ average inventory value over the same period | Uses the period-average inventory value; if the project only has a synthetic inventory snapshot, the result is explicitly called an estimate/proxy rather than a true historical average. Null when the denominator is zero. |
| Days inventory outstanding | Average inventory value ÷ COGS × days | 365-day convention, same period basis as the COGS calculation. If only a final snapshot exists, the metric is reported as an estimate/proxy. |
| Stockout rate | Stockout events ÷ demand events × 100 | True stockout events are unavailable. The UI shows a **zero-stock snapshot proxy** and never labels it as an observed stockout rate. |
| Sell-through | Units sold ÷ units available × 100 | Units available is estimated stock plus observed units in the chosen period. Null for zero availability. |
| Gross profit | Observed revenue − estimated COGS | COGS is generated at 42–72% of median observed product price using seed 42. Not accounting profit. |
| Reorder point | Average daily demand × supplier lead time + safety stock | Demand from the most recent 90 historical days, lead time from synthetic delivery records; thresholds configurable. |
| Safety stock | `z × sqrt(L × σd² + d̄² × σL²)` | Uses daily demand and lead-time variability only when demand history meets the configured minimum; `z` is configurable. |
| Holding cost | Average inventory value × annual holding-cost rate | Defaults to 25% annually, configurable; unit costs and stock are synthetic. |
| ABC | Cumulative annual estimated consumption value: A through 80%, B through 95%, C remainder | Consumption value uses generated product costs and available historical data (not a full current fiscal year). |
| XYZ | Coefficient of variation of product demand: X ≤ 0.5, Y ≤ 1, Z > 1 | Thresholds are starter segmentation choices, not universal policy. |
| Dead stock | Positive snapshot units with no observed sale during the preceding 180 days | Evaluated relative to the final date in the historical workbook. It is a stale-stock indicator, not a confirmed inventory write-off. |
| Forecast error | MAE, RMSE, WAPE, sMAPE, MAPE | Chronological holdout; WAPE and sMAPE are used to retain interpretable scale-aware error estimates when demand is intermittent; MAPE excludes zero actual days and is undefined when the full window has zero demand. Uncertainty is an approximate empirical residual range, not a calibrated interval. |

Important note: the project does not have a complete historical inventory ledger. Where metrics rely on inventory value and stock coverage, they are labeled as estimates or proxies based on the available synthetic snapshots, and the UI/API does not present them as true observed operational events.

`TARGET_COVERAGE_DAYS`, `RECOMMENDATION_STOCK_MULTIPLIER`, `LOW_STOCK_COVERAGE_DAYS`, `STOCKOUT_RISK_COVERAGE_DAYS`, `SLOW_MOVING_DAYS`, `DEAD_STOCK_DAYS`, `SAFETY_STOCK_Z`, `FORECAST_MIN_HISTORY_DAYS`, `FORECAST_VALIDATION_DAYS`, `HOLDING_COST_RATE`, and `SUPPLIER_ON_TIME_THRESHOLD_PCT` are configurable in `.env`.
