CREATE TABLE IF NOT EXISTS categories (
  category_id VARCHAR(20) PRIMARY KEY,
  category_name VARCHAR(100) NOT NULL UNIQUE,
  data_source VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS suppliers (
  supplier_id VARCHAR(20) PRIMARY KEY,
  supplier_name VARCHAR(150) NOT NULL,
  data_source VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS warehouses (
  warehouse_id VARCHAR(20) PRIMARY KEY,
  warehouse_name VARCHAR(100) NOT NULL,
  region VARCHAR(50) NOT NULL,
  data_source VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS products (
  product_id VARCHAR(30) PRIMARY KEY,
  description VARCHAR(255) NOT NULL,
  category_id VARCHAR(20) NOT NULL,
  supplier_id VARCHAR(20) NOT NULL,
  unit_price DECIMAL(12,2) NOT NULL,
  estimated_unit_cost DECIMAL(12,2) NOT NULL,
  data_source VARCHAR(100) NOT NULL,
  CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories(category_id),
  CONSTRAINT fk_products_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
  CONSTRAINT ck_products_price CHECK (unit_price >= 0),
  CONSTRAINT ck_products_cost CHECK (estimated_unit_cost >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS orders (
  order_id VARCHAR(30) PRIMARY KEY,
  order_date DATETIME NOT NULL,
  customer_country VARCHAR(100) NOT NULL,
  warehouse_id VARCHAR(20) NOT NULL,
  data_source VARCHAR(100) NOT NULL,
  CONSTRAINT fk_orders_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS order_items (
  order_item_id BIGINT PRIMARY KEY,
  order_id VARCHAR(30) NOT NULL,
  product_id VARCHAR(30) NOT NULL,
  quantity INT NOT NULL,
  unit_price DECIMAL(12,2) NOT NULL,
  line_revenue DECIMAL(14,2) NOT NULL,
  estimated_cogs DECIMAL(14,2) NOT NULL,
  data_source VARCHAR(100) NOT NULL,
  CONSTRAINT fk_items_order FOREIGN KEY (order_id) REFERENCES orders(order_id),
  CONSTRAINT fk_items_product FOREIGN KEY (product_id) REFERENCES products(product_id),
  CONSTRAINT ck_items_quantity CHECK (quantity > 0),
  CONSTRAINT ck_items_price CHECK (unit_price >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS inventory (
  product_id VARCHAR(30) NOT NULL,
  warehouse_id VARCHAR(20) NOT NULL,
  as_of_date DATE NOT NULL,
  quantity_on_hand INT NOT NULL,
  estimated_unit_cost DECIMAL(12,2) NOT NULL,
  data_source VARCHAR(120) NOT NULL,
  PRIMARY KEY (product_id, warehouse_id, as_of_date),
  CONSTRAINT fk_inventory_product FOREIGN KEY (product_id) REFERENCES products(product_id),
  CONSTRAINT fk_inventory_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
  CONSTRAINT ck_inventory_quantity CHECK (quantity_on_hand >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS supplier_deliveries (
  delivery_id VARCHAR(30) PRIMARY KEY,
  supplier_id VARCHAR(20) NOT NULL,
  order_date DATE NOT NULL,
  promised_date DATE NOT NULL,
  actual_delivery_date DATE NOT NULL,
  lead_time_days INT NOT NULL,
  on_time BOOLEAN NOT NULL,
  data_source VARCHAR(100) NOT NULL,
  CONSTRAINT fk_delivery_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
  CONSTRAINT ck_delivery_lead CHECK (lead_time_days >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS daily_sales (
  product_id VARCHAR(30) NOT NULL,
  warehouse_id VARCHAR(20) NOT NULL,
  sales_date DATE NOT NULL,
  units_sold INT NOT NULL,
  revenue DECIMAL(14,2) NOT NULL,
  estimated_cogs DECIMAL(14,2) NOT NULL,
  data_source VARCHAR(100) NOT NULL,
  PRIMARY KEY (product_id, warehouse_id, sales_date),
  CONSTRAINT fk_daily_product FOREIGN KEY (product_id) REFERENCES products(product_id),
  CONSTRAINT fk_daily_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
  CONSTRAINT ck_daily_units CHECK (units_sold > 0)
) ENGINE=InnoDB;
