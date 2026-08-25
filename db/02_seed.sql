-- 02_seed.sql — demo data for the e-commerce schema.
-- Dates are relative to CURDATE() so demo questions like "last month"
-- and "longer than 5 years" stay correct no matter when the demo runs.

USE demo;

INSERT INTO customers (name, email, region, signup_date) VALUES
  ('Alice Johnson',     'alice@example.com',    'North America', DATE_SUB(CURDATE(), INTERVAL 24 MONTH)),
  ('Bob Martinez',      'bob@example.com',      'North America', DATE_SUB(CURDATE(), INTERVAL 20 MONTH)),
  ('Chen Wei',          'chen@example.com',     'Asia Pacific',  DATE_SUB(CURDATE(), INTERVAL 18 MONTH)),
  ('Diana Smith',       'diana@example.com',    'Europe',        DATE_SUB(CURDATE(), INTERVAL 15 MONTH)),
  ('Elena Rodriguez',   'elena@example.com',    'Europe',        DATE_SUB(CURDATE(), INTERVAL 12 MONTH)),
  ('Fatima Al-Sayed',   'fatima@example.com',   'Europe',        DATE_SUB(CURDATE(), INTERVAL 10 MONTH)),
  ('George Okafor',     'george@example.com',   'Africa',        DATE_SUB(CURDATE(), INTERVAL 8 MONTH)),
  ('Hannah Lee',        'hannah@example.com',   'Asia Pacific',  DATE_SUB(CURDATE(), INTERVAL 6 MONTH)),
  ('Ivan Petrov',       'ivan@example.com',     'Europe',        DATE_SUB(CURDATE(), INTERVAL 4 MONTH)),
  ('Julia Brown',       'julia@example.com',    'South America', DATE_SUB(CURDATE(), INTERVAL 2 MONTH));

INSERT INTO products (name, category, price, stock_quantity) VALUES
  ('Wireless Mouse',                 'Electronics',     24.99,  150),
  ('Mechanical Keyboard',            'Electronics',     89.99,   42),
  ('27" 4K Monitor',                 'Electronics',    349.00,   18),
  ('USB-C Hub',                      'Electronics',     45.50,    8),
  ('Noise-Cancelling Headphones',    'Electronics',    199.99,   25),
  ('Cast Iron Skillet',              'Home & Kitchen',  39.99,   60),
  ('Espresso Machine',               'Home & Kitchen', 299.00,   12),
  ('Chef''s Knife Set',              'Home & Kitchen',  79.99,    5),
  ('Cotton T-Shirt (Pack of 3)',     'Clothing',        29.99,  200),
  ('Running Shoes',                  'Clothing',       120.00,   35),
  ('Denim Jacket',                   'Clothing',        89.50,   15),
  ('Dune (Hardcover)',               'Books',           18.99,  120),
  ('The Pragmatic Programmer',       'Books',           39.99,    3),
  ('Yoga Mat',                       'Sports',          25.00,   90),
  ('Dumbbell Set (20 lbs)',          'Sports',          59.99,   22),
  ('Resistance Bands',               'Sports',          14.99,  300);

INSERT INTO orders (customer_id, order_date, status) VALUES
  -- Last month (1 month ago)
  (1,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 3 DAY),  'completed'),
  (2,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 5 DAY),  'completed'),
  (3,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 6 DAY),  'completed'),
  (4,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 8 DAY),  'completed'),
  (5,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 9 DAY),  'completed'),
  (6,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 10 DAY), 'completed'),
  (7,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 12 DAY), 'pending'),
  (8,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 14 DAY), 'completed'),
  (9,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 15 DAY), 'completed'),
  (10, DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 16 DAY), 'completed'),
  (2,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 18 DAY), 'completed'),
  (3,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 19 DAY), 'completed'),
  (1,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 20 DAY), 'completed'),
  (5,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 21 DAY), 'completed'),
  (6,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 22 DAY), 'pending'),
  (8,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 24 DAY), 'completed'),
  (10, DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 25 DAY), 'completed'),
  (4,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), INTERVAL 27 DAY), 'cancelled'),
  -- 2 months ago
  (1,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 2 MONTH), INTERVAL 4 DAY),  'completed'),
  (5,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 2 MONTH), INTERVAL 7 DAY),  'completed'),
  (8,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 2 MONTH), INTERVAL 9 DAY),  'completed'),
  (2,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 2 MONTH), INTERVAL 11 DAY), 'completed'),
  (3,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 2 MONTH), INTERVAL 15 DAY), 'completed'),
  (7,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 2 MONTH), INTERVAL 18 DAY), 'pending'),
  (10, DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 2 MONTH), INTERVAL 21 DAY), 'completed'),
  -- 3 months ago
  (2,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), INTERVAL 3 DAY),  'completed'),
  (1,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), INTERVAL 6 DAY),  'completed'),
  (6,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), INTERVAL 10 DAY), 'completed'),
  (5,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), INTERVAL 13 DAY), 'completed'),
  (8,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), INTERVAL 16 DAY), 'completed'),
  (9,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), INTERVAL 19 DAY), 'pending'),
  (4,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), INTERVAL 22 DAY), 'completed'),
  -- 4 months ago
  (1,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 4 MONTH), INTERVAL 2 DAY),  'completed'),
  (8,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 4 MONTH), INTERVAL 5 DAY),  'completed'),
  (3,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 4 MONTH), INTERVAL 8 DAY),  'completed'),
  (5,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 4 MONTH), INTERVAL 12 DAY), 'completed'),
  (2,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 4 MONTH), INTERVAL 17 DAY), 'completed'),
  (10, DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 4 MONTH), INTERVAL 20 DAY), 'completed'),
  -- 5 months ago
  (5,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), INTERVAL 4 DAY),  'completed'),
  (1,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), INTERVAL 7 DAY),  'completed'),
  (9,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), INTERVAL 11 DAY), 'completed'),
  (7,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), INTERVAL 15 DAY), 'completed'),
  (8,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), INTERVAL 18 DAY), 'completed'),
  (2,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), INTERVAL 21 DAY), 'completed'),
  (6,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), INTERVAL 24 DAY), 'cancelled'),
  -- 6 months ago
  (3,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 6 MONTH), INTERVAL 3 DAY),  'completed'),
  (5,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 6 MONTH), INTERVAL 6 DAY),  'completed'),
  (8,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 6 MONTH), INTERVAL 9 DAY),  'completed'),
  (1,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 6 MONTH), INTERVAL 13 DAY), 'completed'),
  (4,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 6 MONTH), INTERVAL 17 DAY), 'completed'),
  (10, DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 6 MONTH), INTERVAL 20 DAY), 'completed'),
  -- 7 months ago
  (2,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 7 MONTH), INTERVAL 2 DAY),  'completed'),
  (8,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 7 MONTH), INTERVAL 8 DAY),  'completed'),
  (6,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 7 MONTH), INTERVAL 14 DAY), 'pending'),
  (5,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 7 MONTH), INTERVAL 19 DAY), 'completed'),
  (1,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 7 MONTH), INTERVAL 23 DAY), 'completed'),
  -- 8 months ago
  (3,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 8 MONTH), INTERVAL 5 DAY),  'completed'),
  (1,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 8 MONTH), INTERVAL 10 DAY), 'completed'),
  (9,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 8 MONTH), INTERVAL 16 DAY), 'completed'),
  (5,  DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 8 MONTH), INTERVAL 20 DAY), 'completed');

-- Order items; unit_price is copied from the product price at seed time.
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT v.order_id, v.product_id, v.quantity, p.price
FROM (
  SELECT 1 AS order_id, 3 AS product_id, 1 AS quantity
  UNION ALL SELECT 1, 7, 1
  UNION ALL SELECT 2, 1, 1
  UNION ALL SELECT 2, 4, 1
  UNION ALL SELECT 3, 9, 1
  UNION ALL SELECT 3, 10, 1
  UNION ALL SELECT 4, 12, 1
  UNION ALL SELECT 4, 13, 1
  UNION ALL SELECT 5, 5, 1
  UNION ALL SELECT 5, 15, 1
  UNION ALL SELECT 6, 14, 1
  UNION ALL SELECT 6, 16, 2
  UNION ALL SELECT 7, 2, 1
  UNION ALL SELECT 8, 6, 1
  UNION ALL SELECT 8, 8, 1
  UNION ALL SELECT 9, 11, 1
  UNION ALL SELECT 10, 1, 2
  UNION ALL SELECT 10, 16, 1
  UNION ALL SELECT 11, 5, 1
  UNION ALL SELECT 11, 10, 1
  UNION ALL SELECT 12, 9, 2
  UNION ALL SELECT 12, 14, 1
  UNION ALL SELECT 13, 3, 1
  UNION ALL SELECT 14, 15, 1
  UNION ALL SELECT 14, 16, 2
  UNION ALL SELECT 15, 12, 1
  UNION ALL SELECT 16, 7, 1
  UNION ALL SELECT 16, 9, 1
  UNION ALL SELECT 17, 1, 1
  UNION ALL SELECT 18, 13, 1
  UNION ALL SELECT 19, 2, 1
  UNION ALL SELECT 19, 4, 1
  UNION ALL SELECT 20, 5, 1
  UNION ALL SELECT 21, 10, 1
  UNION ALL SELECT 21, 11, 1
  UNION ALL SELECT 22, 6, 1
  UNION ALL SELECT 22, 14, 1
  UNION ALL SELECT 23, 9, 2
  UNION ALL SELECT 24, 1, 1
  UNION ALL SELECT 25, 16, 3
  UNION ALL SELECT 26, 7, 1
  UNION ALL SELECT 26, 15, 1
  UNION ALL SELECT 27, 3, 1
  UNION ALL SELECT 27, 4, 1
  UNION ALL SELECT 28, 14, 2
  UNION ALL SELECT 29, 5, 1
  UNION ALL SELECT 29, 16, 1
  UNION ALL SELECT 30, 8, 1
  UNION ALL SELECT 30, 13, 1
  UNION ALL SELECT 31, 2, 1
  UNION ALL SELECT 32, 12, 2
  UNION ALL SELECT 33, 3, 1
  UNION ALL SELECT 33, 10, 1
  UNION ALL SELECT 34, 9, 2
  UNION ALL SELECT 34, 6, 1
  UNION ALL SELECT 35, 11, 1
  UNION ALL SELECT 35, 12, 1
  UNION ALL SELECT 36, 5, 1
  UNION ALL SELECT 36, 15, 1
  UNION ALL SELECT 37, 1, 2
  UNION ALL SELECT 37, 14, 1
  UNION ALL SELECT 38, 16, 2
  UNION ALL SELECT 39, 7, 1
  UNION ALL SELECT 40, 2, 1
  UNION ALL SELECT 40, 3, 1
  UNION ALL SELECT 41, 13, 1
  UNION ALL SELECT 42, 1, 1
  UNION ALL SELECT 42, 9, 1
  UNION ALL SELECT 43, 10, 1
  UNION ALL SELECT 43, 15, 1
  UNION ALL SELECT 44, 5, 1
  UNION ALL SELECT 44, 6, 1
  UNION ALL SELECT 45, 12, 1
  UNION ALL SELECT 46, 9, 2
  UNION ALL SELECT 46, 16, 1
  UNION ALL SELECT 47, 14, 1
  UNION ALL SELECT 47, 15, 1
  UNION ALL SELECT 48, 8, 1
  UNION ALL SELECT 49, 3, 1
  UNION ALL SELECT 49, 7, 1
  UNION ALL SELECT 50, 10, 1
  UNION ALL SELECT 51, 1, 1
  UNION ALL SELECT 51, 16, 1
  UNION ALL SELECT 52, 2, 1
  UNION ALL SELECT 53, 9, 1
  UNION ALL SELECT 53, 11, 1
  UNION ALL SELECT 54, 14, 1
  UNION ALL SELECT 55, 5, 1
  UNION ALL SELECT 56, 6, 1
  UNION ALL SELECT 56, 15, 1
  UNION ALL SELECT 57, 12, 1
  UNION ALL SELECT 57, 13, 1
  UNION ALL SELECT 58, 3, 1
  UNION ALL SELECT 59, 9, 1
  UNION ALL SELECT 60, 16, 2
) v
JOIN products p ON p.product_id = v.product_id;

INSERT INTO employees (name, department, hire_date) VALUES
  ('Sarah Connor',  'Engineering', DATE_SUB(CURDATE(), INTERVAL 8 YEAR)),
  ('Marcus Bell',   'Sales',       DATE_SUB(CURDATE(), INTERVAL 7 YEAR)),
  ('Priya Sharma',  'Engineering', DATE_SUB(CURDATE(), INTERVAL 6 YEAR)),
  ('Tom O''Reilly', 'Marketing',   DATE_SUB(DATE_SUB(CURDATE(), INTERVAL 5 YEAR), INTERVAL 6 MONTH)),
  ('Nina Kowalski', 'Operations',  DATE_SUB(CURDATE(), INTERVAL 4 YEAR)),
  ('David Chen',    'Sales',       DATE_SUB(CURDATE(), INTERVAL 3 YEAR)),
  ('Aisha Bello',   'Engineering', DATE_SUB(CURDATE(), INTERVAL 2 YEAR)),
  ('Liam Walsh',    'Marketing',   DATE_SUB(CURDATE(), INTERVAL 6 MONTH));
