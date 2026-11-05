-- Revenue: monthly and quarterly observed sales (GBP).
SELECT DATE_FORMAT(o.order_date, '%Y-%m') AS sales_month, SUM(i.line_revenue) AS revenue
FROM orders o JOIN order_items i ON i.order_id = o.order_id
GROUP BY DATE_FORMAT(o.order_date, '%Y-%m') ORDER BY sales_month;

SELECT CONCAT(YEAR(o.order_date), '-Q', QUARTER(o.order_date)) AS sales_quarter,
       SUM(i.line_revenue) AS revenue
FROM orders o JOIN order_items i ON i.order_id = o.order_id
GROUP BY YEAR(o.order_date), QUARTER(o.order_date) ORDER BY YEAR(o.order_date), QUARTER(o.order_date);

SELECT c.category_name, SUM(i.line_revenue) AS revenue
FROM categories c JOIN products p ON p.category_id = c.category_id
JOIN order_items i ON i.product_id = p.product_id
GROUP BY c.category_id, c.category_name ORDER BY revenue DESC;

SELECT p.product_id, p.description, SUM(i.line_revenue) AS revenue, SUM(i.quantity) AS units
FROM products p JOIN order_items i ON i.product_id = p.product_id
GROUP BY p.product_id, p.description ORDER BY revenue DESC;

-- Warehouse revenue is observed sales allocated to synthetic warehouse assignments.
SELECT w.warehouse_name, SUM(s.revenue) AS allocated_revenue
FROM warehouses w JOIN daily_sales s ON s.warehouse_id = w.warehouse_id
GROUP BY w.warehouse_id, w.warehouse_name ORDER BY allocated_revenue DESC;

-- Current stock and 90-day run rate; inventory and reorder point are synthetic estimates.
WITH demand AS (
  SELECT product_id, SUM(units_sold) / 90.0 AS average_daily_demand
  FROM daily_sales WHERE sales_date >= (SELECT MAX(sales_date) FROM daily_sales) - INTERVAL 89 DAY
  GROUP BY product_id
), stock AS (
  SELECT product_id, SUM(quantity_on_hand) AS on_hand
  FROM inventory GROUP BY product_id
)
SELECT p.product_id, p.description, COALESCE(s.on_hand, 0) AS on_hand,
       COALESCE(d.average_daily_demand, 0) AS average_daily_demand,
       CASE WHEN COALESCE(d.average_daily_demand, 0) = 0 THEN NULL
            ELSE s.on_hand / d.average_daily_demand END AS days_of_cover
FROM products p LEFT JOIN stock s ON s.product_id = p.product_id
LEFT JOIN demand d ON d.product_id = p.product_id;

-- Low inventory and overstock lists use configurable target values in the application.
WITH demand AS (
  SELECT product_id, SUM(units_sold) / 90.0 AS daily_demand
  FROM daily_sales WHERE sales_date >= (SELECT MAX(sales_date) FROM daily_sales) - INTERVAL 89 DAY
  GROUP BY product_id
), stock AS (
  SELECT product_id, SUM(quantity_on_hand) AS on_hand
  FROM inventory GROUP BY product_id
)
SELECT p.product_id, p.description, s.on_hand, d.daily_demand,
       (d.daily_demand * 14) AS demo_low_stock_threshold
FROM products p JOIN stock s ON s.product_id = p.product_id
JOIN demand d ON d.product_id = p.product_id
WHERE d.daily_demand > 0 AND s.on_hand <= d.daily_demand * 14;

-- Estimated inventory turnover, DIO, and gross profit.
WITH cost_of_sales AS (
  SELECT SUM(estimated_cogs) AS cogs, SUM(line_revenue) AS revenue FROM order_items
), stock_value AS (
  SELECT SUM(quantity_on_hand * estimated_unit_cost) AS value FROM inventory
)
SELECT c.cogs / NULLIF(v.value, 0) AS estimated_turnover,
       v.value * 365 / NULLIF(c.cogs, 0) AS estimated_dio_days,
       c.revenue - c.cogs AS estimated_gross_profit
FROM cost_of_sales c CROSS JOIN stock_value v;

-- Supplier metrics are synthetic demonstration deliveries, not actual supplier history.
SELECT s.supplier_id, s.supplier_name, AVG(d.lead_time_days) AS average_lead_time_days,
       100.0 * AVG(d.on_time) AS on_time_pct, COUNT(*) AS deliveries
FROM suppliers s JOIN supplier_deliveries d ON d.supplier_id = s.supplier_id
GROUP BY s.supplier_id, s.supplier_name ORDER BY on_time_pct DESC;

SELECT s.supplier_name, d.delivery_id, DATEDIFF(d.actual_delivery_date, d.promised_date) AS delay_days,
       RANK() OVER (ORDER BY DATEDIFF(d.actual_delivery_date, d.promised_date) DESC) AS delay_rank
FROM supplier_deliveries d JOIN suppliers s ON s.supplier_id = d.supplier_id;

-- Product performance and revenue share.
WITH product_revenue AS (
  SELECT p.product_id, p.description, SUM(i.line_revenue) AS revenue
  FROM products p JOIN order_items i ON i.product_id = p.product_id
  GROUP BY p.product_id, p.description
)
SELECT product_id, description, revenue,
       revenue / NULLIF(SUM(revenue) OVER (), 0) AS revenue_contribution,
       DENSE_RANK() OVER (ORDER BY revenue DESC) AS revenue_rank
FROM product_revenue ORDER BY revenue DESC LIMIT 10;

WITH monthly AS (
  SELECT DATE_FORMAT(o.order_date, '%Y-%m') AS month, SUM(i.line_revenue) AS revenue
  FROM orders o JOIN order_items i ON i.order_id = o.order_id
  GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
)
SELECT month, revenue, LAG(revenue) OVER (ORDER BY month) AS previous_month,
       (revenue - LAG(revenue) OVER (ORDER BY month)) / NULLIF(LAG(revenue) OVER (ORDER BY month), 0) AS growth_rate
FROM monthly ORDER BY month;

-- ABC based on estimated annual consumption value; limited to available historical window.
WITH annual AS (
  SELECT p.product_id, SUM(s.estimated_cogs) AS consumption_value
  FROM products p JOIN daily_sales s ON s.product_id = p.product_id
  WHERE s.sales_date >= (SELECT MAX(sales_date) FROM daily_sales) - INTERVAL 364 DAY
  GROUP BY p.product_id
), shares AS (
  SELECT product_id, consumption_value,
         SUM(consumption_value) OVER (ORDER BY consumption_value DESC) /
         NULLIF(SUM(consumption_value) OVER (), 0) AS cumulative_share
  FROM annual
)
SELECT product_id, consumption_value,
       CASE WHEN cumulative_share <= 0.80 THEN 'A'
            WHEN cumulative_share <= 0.95 THEN 'B' ELSE 'C' END AS abc_class
FROM shares ORDER BY consumption_value DESC;

-- Dead stock: no observed sale in 180 days; snapshot stock itself is synthetic.
SELECT p.product_id, p.description, SUM(i.quantity_on_hand) AS stock
FROM products p JOIN inventory i ON i.product_id = p.product_id
WHERE NOT EXISTS (
  SELECT 1 FROM daily_sales d
  WHERE d.product_id = p.product_id AND d.sales_date >= (SELECT MAX(sales_date) FROM daily_sales) - INTERVAL 179 DAY
)
GROUP BY p.product_id, p.description HAVING SUM(i.quantity_on_hand) > 0;

-- 7-day moving average.
SELECT product_id, sales_date, units_sold,
       AVG(units_sold) OVER (PARTITION BY product_id ORDER BY sales_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg_7d
FROM daily_sales ORDER BY product_id, sales_date;
