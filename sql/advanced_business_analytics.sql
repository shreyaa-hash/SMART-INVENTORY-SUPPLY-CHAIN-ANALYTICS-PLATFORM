-- Advanced business analytics for Smart Inventory
-- Uses observed transaction revenue and avoids duplicate revenue by aggregating
-- at the order_item level before joining to products, customers, or countries.
-- Synthetic inventory and supplier data are excluded from these analyses unless
-- explicitly labeled as such in the query comments.

-- Query 1: Which products generate the highest revenue?
SELECT
    p.product_id,
    p.description,
    ROUND(SUM(oi.line_revenue), 2) AS total_revenue,
    ROUND(AVG(oi.unit_price), 2) AS avg_selling_price,
    SUM(oi.quantity) AS units_sold
FROM products p
INNER JOIN order_items oi
    ON oi.product_id = p.product_id
GROUP BY p.product_id, p.description
HAVING SUM(oi.line_revenue) > 0
ORDER BY total_revenue DESC;

-- Query 2: Which products have the highest sales volume?
SELECT
    p.product_id,
    p.description,
    SUM(oi.quantity) AS total_units,
    ROUND(SUM(oi.line_revenue), 2) AS revenue
FROM products p
INNER JOIN order_items oi
    ON oi.product_id = p.product_id
GROUP BY p.product_id, p.description
HAVING SUM(oi.quantity) > 0
ORDER BY total_units DESC;

-- Query 3: What are the monthly revenue trends?
SELECT
    DATE_FORMAT(o.order_date, '%Y-%m') AS month_key,
    ROUND(SUM(oi.line_revenue), 2) AS monthly_revenue,
    LAG(ROUND(SUM(oi.line_revenue), 2)) OVER (ORDER BY DATE_FORMAT(o.order_date, '%Y-%m')) AS previous_month_revenue,
    CASE
        WHEN LAG(ROUND(SUM(oi.line_revenue), 2)) OVER (ORDER BY DATE_FORMAT(o.order_date, '%Y-%m')) IS NULL THEN NULL
        WHEN LAG(ROUND(SUM(oi.line_revenue), 2)) OVER (ORDER BY DATE_FORMAT(o.order_date, '%Y-%m')) = 0 THEN NULL
        ELSE (
            ROUND(SUM(oi.line_revenue), 2) - LAG(ROUND(SUM(oi.line_revenue), 2)) OVER (ORDER BY DATE_FORMAT(o.order_date, '%Y-%m'))
        ) / LAG(ROUND(SUM(oi.line_revenue), 2)) OVER (ORDER BY DATE_FORMAT(o.order_date, '%Y-%m'))
    END AS month_over_month_growth
FROM orders o
INNER JOIN order_items oi
    ON oi.order_id = o.order_id
GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
ORDER BY month_key;

-- Query 4: Which countries contribute the most revenue?
SELECT
    o.customer_country AS country,
    ROUND(SUM(oi.line_revenue), 2) AS revenue,
    ROUND(100.0 * SUM(oi.line_revenue) / NULLIF((
        SELECT SUM(line_revenue) FROM order_items
    ), 0), 2) AS revenue_pct
FROM orders o
INNER JOIN order_items oi
    ON oi.order_id = o.order_id
GROUP BY o.customer_country
HAVING SUM(oi.line_revenue) > 0
ORDER BY revenue DESC;

-- Query 5: What percentage of revenue comes from the top 10 products?
WITH product_revenue AS (
    SELECT
        p.product_id,
        p.description,
        ROUND(SUM(oi.line_revenue), 2) AS revenue
    FROM products p
    INNER JOIN order_items oi
        ON oi.product_id = p.product_id
    GROUP BY p.product_id, p.description
), ranked AS (
    SELECT
        *,
        SUM(revenue) OVER (ORDER BY revenue DESC) AS cumulative_revenue,
        SUM(revenue) OVER () AS total_revenue
    FROM product_revenue
), top10 AS (
    SELECT *
    FROM ranked
    ORDER BY revenue DESC
    LIMIT 10
)
SELECT
    ROUND((SELECT SUM(revenue) FROM top10), 2) AS top10_revenue,
    ROUND(100.0 * (SELECT SUM(revenue) FROM top10) / NULLIF((SELECT SUM(revenue) FROM product_revenue), 0), 2) AS top10_revenue_pct,
    ROUND((SELECT total_revenue FROM ranked LIMIT 1), 2) AS total_observed_revenue;

-- Query 6: Which customers generate the highest monetary value?
SELECT
    o.customer_id,
    ROUND(SUM(oi.line_revenue), 2) AS customer_revenue,
    COUNT(DISTINCT o.order_id) AS order_count,
    ROUND(AVG(oi.line_revenue), 2) AS avg_order_value
FROM orders o
INNER JOIN order_items oi
    ON oi.order_id = o.order_id
WHERE o.customer_id IS NOT NULL
GROUP BY o.customer_id
HAVING COUNT(DISTINCT o.order_id) > 0
ORDER BY customer_revenue DESC
LIMIT 20;

-- Query 7: What is the repeat purchase rate?
WITH customer_order_counts AS (
    SELECT
        o.customer_id,
        COUNT(DISTINCT o.order_id) AS order_count,
        ROUND(SUM(oi.line_revenue), 2) AS total_revenue
    FROM orders o
    INNER JOIN order_items oi
        ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id
)
SELECT
    ROUND(100.0 * SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS repeat_purchase_rate_pct,
    SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    COUNT(*) AS identifiable_customers
FROM customer_order_counts;

-- Query 8: Which customer segments contribute the most revenue?
WITH customer_rfm AS (
    SELECT
        o.customer_id,
        DATEDIFF((SELECT MAX(order_date) FROM orders), MAX(o.order_date)) AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency,
        ROUND(SUM(oi.line_revenue), 2) AS monetary
    FROM orders o
    INNER JOIN order_items oi
        ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id
), scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        CASE
            WHEN recency_days <= 30 AND frequency >= 4 AND monetary >= 1000 THEN 'Champions'
            WHEN recency_days <= 60 AND frequency >= 2 AND monetary >= 500 THEN 'Loyal Customers'
            WHEN recency_days <= 90 AND frequency >= 1 AND monetary >= 250 THEN 'Potential Loyalists'
            WHEN recency_days <= 30 AND frequency >= 1 THEN 'New Customers'
            WHEN recency_days BETWEEN 60 AND 180 AND frequency <= 2 THEN 'At Risk'
            WHEN recency_days BETWEEN 90 AND 365 AND frequency <= 1 THEN 'Hibernating'
            WHEN recency_days >= 180 AND frequency <= 1 THEN 'Lost Customers'
            ELSE 'Loyal Customers'
        END AS segment
    FROM customer_rfm
), segment_revenue AS (
    SELECT
        s.segment,
        ROUND(SUM(oi.line_revenue), 2) AS segment_revenue,
        COUNT(DISTINCT s.customer_id) AS segment_customers
    FROM scored s
    INNER JOIN orders o
        ON o.customer_id = s.customer_id
    INNER JOIN order_items oi
        ON oi.order_id = o.order_id
    GROUP BY s.segment
)
SELECT
    segment,
    segment_revenue,
    segment_customers,
    ROUND(100.0 * segment_revenue / NULLIF((SELECT SUM(segment_revenue) FROM segment_revenue), 0), 2) AS revenue_share_pct
FROM segment_revenue
ORDER BY segment_revenue DESC;

-- Query 9: Which products show declining demand?
WITH monthly_product_revenue AS (
    SELECT
        DATE_FORMAT(o.order_date, '%Y-%m') AS month_key,
        oi.product_id,
        ROUND(SUM(oi.quantity), 2) AS units_sold,
        ROUND(SUM(oi.line_revenue), 2) AS revenue
    FROM orders o
    INNER JOIN order_items oi
        ON oi.order_id = o.order_id
    GROUP BY DATE_FORMAT(o.order_date, '%Y-%m'), oi.product_id
), ranked_demand AS (
    SELECT
        product_id,
        month_key,
        units_sold,
        revenue,
        LAG(units_sold) OVER (PARTITION BY product_id ORDER BY month_key) AS prev_month_units,
        LEAD(units_sold) OVER (PARTITION BY product_id ORDER BY month_key) AS next_month_units,
        ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY month_key DESC) AS latest_month_rank
    FROM monthly_product_revenue
)
SELECT
    product_id,
    month_key,
    units_sold,
    prev_month_units,
    next_month_units,
    CASE
        WHEN prev_month_units IS NULL THEN 'New product'
        WHEN units_sold < prev_month_units THEN 'Declining demand'
        WHEN units_sold = prev_month_units THEN 'Stable demand'
        ELSE 'Growing demand'
    END AS demand_signal
FROM ranked_demand
WHERE latest_month_rank = 1
HAVING units_sold > 0
ORDER BY units_sold ASC, product_id;

-- Query 10: How does revenue change month over month?
WITH monthly_revenue AS (
    SELECT
        DATE_FORMAT(o.order_date, '%Y-%m') AS month_key,
        ROUND(SUM(oi.line_revenue), 2) AS revenue
    FROM orders o
    INNER JOIN order_items oi
        ON oi.order_id = o.order_id
    GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
)
SELECT
    month_key,
    revenue,
    LAG(revenue) OVER (ORDER BY month_key) AS previous_month_revenue,
    ROUND(revenue - LAG(revenue) OVER (ORDER BY month_key), 2) AS absolute_delta,
    CASE
        WHEN LAG(revenue) OVER (ORDER BY month_key) IS NULL THEN NULL
        WHEN LAG(revenue) OVER (ORDER BY month_key) = 0 THEN NULL
        ELSE ROUND((revenue - LAG(revenue) OVER (ORDER BY month_key)) / LAG(revenue) OVER (ORDER BY month_key), 4)
    END AS pct_change
FROM monthly_revenue
ORDER BY month_key;

-- Additional query: Revenue by product category using LEFT JOIN and a category base table.
SELECT
    c.category_name,
    ROUND(SUM(oi.line_revenue), 2) AS category_revenue,
    SUM(oi.quantity) AS category_units,
    DENSE_RANK() OVER (ORDER BY SUM(oi.line_revenue) DESC) AS revenue_rank
FROM categories c
LEFT JOIN products p
    ON p.category_id = c.category_id
LEFT JOIN order_items oi
    ON oi.product_id = p.product_id
GROUP BY c.category_id, c.category_name
HAVING SUM(oi.line_revenue) > 0
ORDER BY category_revenue DESC;

-- Additional query: Customer-level month-over-month revenue trend using window functions.
WITH customer_monthly AS (
    SELECT
        o.customer_id,
        DATE_FORMAT(o.order_date, '%Y-%m') AS month_key,
        ROUND(SUM(oi.line_revenue), 2) AS revenue
    FROM orders o
    INNER JOIN order_items oi
        ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id, DATE_FORMAT(o.order_date, '%Y-%m')
)
SELECT
    customer_id,
    month_key,
    revenue,
    LAG(revenue) OVER (PARTITION BY customer_id ORDER BY month_key) AS previous_month_revenue,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY month_key DESC) AS recent_month_rank
FROM customer_monthly
ORDER BY customer_id, month_key;

-- Additional query: Sales outlier check for negative or suspiciously low margins.
WITH product_margin AS (
    SELECT
        p.product_id,
        p.description,
        ROUND(AVG(oi.unit_price), 2) AS avg_selling_price,
        ROUND(AVG(p.estimated_unit_cost), 2) AS avg_estimated_cost,
        ROUND(AVG(oi.unit_price) - AVG(p.estimated_unit_cost), 2) AS avg_margin_per_unit
    FROM products p
    INNER JOIN order_items oi
        ON oi.product_id = p.product_id
    GROUP BY p.product_id, p.description
)
SELECT *
FROM product_margin
WHERE avg_margin_per_unit < 0
ORDER BY avg_margin_per_unit ASC;
