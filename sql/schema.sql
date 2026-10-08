-- =====================================================================
--  MAMA EARTH CAPSTONE  |  PART 1: SQL
--  File: sql/schema.sql  ->  database structure (the "cabinet" design)
-- ---------------------------------------------------------------------
--  Three tables: customers, products, orders.
--
--  Constraints used:
--    PRIMARY KEY  -> unique row id (no duplicates possible)
--    FOREIGN KEY  -> an order's customer/product must exist in its table
--    NOT NULL     -> the column cannot be left empty
--    CHECK        -> the value must sit inside an allowed range
--
--  NOTE ON SQLITE: foreign key enforcement is OFF by default. The line
--  "PRAGMA foreign_keys = ON;" is placed here AND at the top of
--  seed_data.sql, because the pragma is per-connection.
--
--  Run this file first, then seed_data.sql, then reports.sql.
-- =====================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

-- ---------------------------------------------------------------------
-- TABLE 1: customers  (45 rows)  <- data/customers.csv
-- CSV column order: customer_id, name, city, city_tier,
--                   signup_date, acquisition_source
-- ---------------------------------------------------------------------
CREATE TABLE customers (
    customer_id        TEXT    PRIMARY KEY,
    name               TEXT    NOT NULL,
    city               TEXT,
    city_tier          INTEGER CHECK (city_tier IN (1, 2)),
    signup_date        DATE,
    acquisition_source TEXT    CHECK (acquisition_source IN
                                   ('Ad', 'Organic', 'Referral', 'Social'))
);

-- ---------------------------------------------------------------------
-- TABLE 2: products  (16 rows)  <- data/products.csv
-- CSV column order: product_id, product_name, category, price
-- ---------------------------------------------------------------------
CREATE TABLE products (
    product_id   TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     TEXT CHECK (category IN
                     ('Haircare', 'Skincare', 'Babycare', 'PersonalCare')),
    price        REAL NOT NULL CHECK (price > 0)
);

-- ---------------------------------------------------------------------
-- TABLE 3: orders  (180 rows)  <- data/orders.csv
-- CSV column order: order_id, customer_id, product_id, order_date,
--                   quantity, discount_pct, payment_method, rating, returned
--
-- rating and discount_pct are blank in the raw CSV (15 and 12 rows),
-- so those cells were loaded as real NULLs - blank is not the same as 0.
--
-- payment_method is stored exactly as it appears in the CSV
-- (Card / CARD / card ...). Cleaning is Part 2's job (Python), so the
-- reports below normalise it defensively with UPPER(TRIM(...)).
-- ---------------------------------------------------------------------
CREATE TABLE orders (
    order_id       TEXT    PRIMARY KEY,
    customer_id    TEXT    NOT NULL,
    product_id     TEXT    NOT NULL,
    order_date     DATE    NOT NULL,
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    discount_pct   INTEGER CHECK (discount_pct BETWEEN 0 AND 100),
    payment_method TEXT,
    rating         INTEGER CHECK (rating BETWEEN 1 AND 5),
    returned       INTEGER NOT NULL CHECK (returned IN (0, 1)),
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
    FOREIGN KEY (product_id)  REFERENCES products  (product_id)
);

-- Indexes on the columns used by JOIN / GROUP BY -> faster reports.
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_orders_product  ON orders (product_id);
CREATE INDEX idx_orders_date     ON orders (order_date);
