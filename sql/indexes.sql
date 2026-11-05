CREATE INDEX idx_orders_warehouse_date ON orders(warehouse_id, order_date);
CREATE INDEX idx_order_items_product_order ON order_items(product_id, order_id);
CREATE INDEX idx_inventory_warehouse_date ON inventory(warehouse_id, as_of_date);
CREATE INDEX idx_delivery_supplier_promised ON supplier_deliveries(supplier_id, promised_date);
CREATE INDEX idx_daily_sales_date_product ON daily_sales(sales_date, product_id);
