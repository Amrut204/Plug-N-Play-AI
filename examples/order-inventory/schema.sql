-- =============================================================================
-- E-Commerce, Warehouse & Inventory Operations Database Schema
-- Compatible with PostgreSQL and SQLite
-- =============================================================================

CREATE TABLE IF NOT EXISTS categories (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(64) PRIMARY KEY,
    category_id VARCHAR(64) REFERENCES categories(id),
    sku VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    price_cents INTEGER NOT NULL,
    cost_cents INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'active' -- active, archived, out_of_stock
);

CREATE TABLE IF NOT EXISTS warehouses (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location_code VARCHAR(50) NOT NULL,
    capacity_pallets INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    id VARCHAR(64) PRIMARY KEY,
    product_id VARCHAR(64) REFERENCES products(id),
    warehouse_id VARCHAR(64) REFERENCES warehouses(id),
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    quantity_reserved INTEGER NOT NULL DEFAULT 0,
    reorder_threshold INTEGER NOT NULL DEFAULT 20
);

CREATE TABLE IF NOT EXISTS customers (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    loyalty_tier VARCHAR(50) DEFAULT 'bronze', -- bronze, silver, gold, vip
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR(64) PRIMARY KEY,
    customer_id VARCHAR(64) REFERENCES customers(id),
    order_number VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'processing', -- pending, processing, shipped, delivered, cancelled, returned
    total_amount_cents INTEGER NOT NULL,
    shipping_carrier VARCHAR(50), -- FedEx, UPS, DHL, USPS
    tracking_number VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id VARCHAR(64) PRIMARY KEY,
    order_id VARCHAR(64) REFERENCES orders(id),
    product_id VARCHAR(64) REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL
);

-- Seed Data
INSERT INTO categories (id, name, description) VALUES
('cat_001', 'Electronics', 'Smart hardware, monitors, and accessories'),
('cat_002', 'Office Furniture', 'Ergonomic chairs, standing desks');

INSERT INTO products (id, category_id, sku, title, price_cents, cost_cents, status) VALUES
('prod_101', 'cat_001', 'SKU-MON-4K', 'UltraHD 27-inch 4K Monitor', 34900, 21000, 'active'),
('prod_102', 'cat_001', 'SKU-MOU-WL', 'Wireless Ergonomic Mouse', 5900, 2200, 'active'),
('prod_103', 'cat_002', 'SKU-DSK-STD', 'Motorized Dual-Motor Standing Desk', 49900, 31000, 'active'),
('prod_104', 'cat_002', 'SKU-CHR-ERG', 'High-Back Mesh Ergonomic Chair', 28900, 16000, 'out_of_stock');

INSERT INTO warehouses (id, name, location_code, capacity_pallets) VALUES
('wh_east', 'East Coast Distribution Center', 'NJ-01', 5000),
('wh_west', 'Pacific Logistics Hub', 'CA-02', 7500);

INSERT INTO inventory (id, product_id, warehouse_id, quantity_on_hand, quantity_reserved, reorder_threshold) VALUES
('inv_1', 'prod_101', 'wh_east', 45, 5, 20),
('inv_2', 'prod_101', 'wh_west', 80, 12, 25),
('inv_3', 'prod_102', 'wh_east', 12, 4, 30), -- Below threshold
('inv_4', 'prod_103', 'wh_west', 22, 3, 15),
('inv_5', 'prod_104', 'wh_east', 0, 0, 20);  -- Out of stock

INSERT INTO customers (id, email, full_name, loyalty_tier) VALUES
('cust_01', 'marcus.v@apex.co', 'Marcus Vance', 'vip'),
('cust_02', 'lisa.k@techlabs.com', 'Lisa Kim', 'gold'),
('cust_03', 'dave.b@gmail.com', 'David Miller', 'bronze');

INSERT INTO orders (id, customer_id, order_number, status, total_amount_cents, shipping_carrier, tracking_number) VALUES
('ord_501', 'cust_01', 'ORD-2026-9021', 'shipped', 70700, 'FedEx', 'FDX-998822110'),
('ord_502', 'cust_02', 'ORD-2026-9022', 'processing', 34900, 'UPS', 'UPS-44332211'),
('ord_503', 'cust_03', 'ORD-2026-9023', 'delivered', 5900, 'USPS', 'USPS-11223344');

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price_cents) VALUES
('oi_1', 'ord_501', 'prod_101', 1, 34900),
('oi_2', 'ord_501', 'prod_103', 1, 49900),
('oi_3', 'ord_502', 'prod_101', 1, 34900),
('oi_4', 'ord_503', 'prod_102', 1, 5900);
