-- =====================================================================
--  MAMA EARTH CAPSTONE  |  PART 1: SQL
--  File: sql/reports.sql  ->  9 business questions, 9 answers
-- ---------------------------------------------------------------------
--  BUSINESS CONTEXT
--  Mama Earth ke 180 orders mein se 45 return hue = 25.0% return rate.
--  Har 4th order wapas aa raha hai, aur ye profit margin kha raha hai.
--  Ye 9 reports batati hain ki returns ASAL MEIN kahan se aate hain.
--
--  NOTE ON CLEANING
--  Part 1 deliberately reports on RAW data (duplicates and messy
--  payment_method included). The queries therefore normalise the
--  spelling defensively with UPPER(TRIM(...)) so Card/CARD/card group
--  into one row. Real cleaning happens in Part 2 (Python).
--
--  SQL techniques demonstrated
--    multi-table INNER JOIN .......... reports 1-8
--    GROUP BY + aggregate functions .. reports 2-9
--    HAVING (filter after grouping) .. report 4
--    CASE - bucketing values ......... report 8
--    COALESCE - NULL handling ........ reports 1-9
--    ROUND / SUM / AVG / COUNT ....... all reports
--    ORDER BY + LIMIT ................ report 4 and 7
--    date grouping with strftime ..... report 9
--    correlated subquery ............. seed_data.sql verification
--
--  FORMULAS USED
--    order line revenue = quantity * price * (1 - discount_pct / 100)
--    return rate %      = 100 * returned orders / total orders
--
--  Run order:  schema.sql  ->  seed_data.sql  ->  reports.sql
--  Every "Expected output" comment below was pasted from a real run.
-- =====================================================================

-- ===== REPORT 1: Headline numbers (total orders, revenue, AOV, return rate) =====
-- Business question: what does the raw data say before any cleaning?
SELECT COUNT(*)                                                        AS total_orders,
       COUNT(DISTINCT o.customer_id)                                   AS customers,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
                                                                       AS total_revenue,
       ROUND(AVG(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
                                                                       AS avg_order_value,
       SUM(o.returned)                                                 AS returned_orders,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 2)                    AS return_rate_pct
FROM orders o
JOIN products p ON p.product_id = o.product_id;

-- Expected output (from a real run of this file):
--   total_orders  customers  total_revenue  avg_order_value  returned_orders  return_rate_pct
--   ------------  ---------  -------------  ---------------  ---------------  ---------------
--   180           44         99860.2        554.78           45               25.0           

-- ===== REPORT 2: Returns by category (kaunsi category sabse zyada return hoti hai?) =====
-- Business question from the brief: "How many orders were returned by category?" 
SELECT p.category,
       COUNT(*)                                     AS total_orders,
       SUM(o.returned)                              AS returned_orders,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 2) AS return_rate_pct,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
                                                    AS revenue
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY p.category
ORDER BY return_rate_pct DESC;

-- Expected output (from a real run of this file):
--   category      total_orders  returned_orders  return_rate_pct  revenue
--   ------------  ------------  ---------------  ---------------  -------
--   Skincare      60            19               31.67            27346.0
--   Haircare      54            14               25.93            44956.1
--   Babycare      30            7                23.33            16805.0
--   PersonalCare  36            5                13.89            10753.1

-- ===== REPORT 3: Average order value by payment method (kis mode se bade orders?) =====
-- Business question from the brief: "What is the average order value by payment method?" 
SELECT UPPER(TRIM(o.payment_method))        AS payment_method,
       COUNT(*)                             AS total_orders,
       ROUND(AVG(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
                                            AS avg_order_value,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
                                            AS revenue,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 2) AS return_rate_pct
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY UPPER(TRIM(o.payment_method))
ORDER BY avg_order_value DESC;

-- Expected output (from a real run of this file):
--   payment_method  total_orders  avg_order_value  revenue  return_rate_pct
--   --------------  ------------  ---------------  -------  ---------------
--   COD             55            714.64           39305.2  43.64          
--   UPI             55            488.42           26863.2  20.0           
--   CARD            70            481.31           33691.8  14.29          

-- ===== REPORT 4: Top 10 customers by return rate (repeat returners ko pakdo) =====
-- Business question from the brief: "Which customers have the highest return rates?"
-- HAVING keeps out customers with fewer than 3 orders, because a rate built on
-- 1-2 orders is noise, not a pattern.
SELECT c.customer_id,
       c.name,
       c.city,
       c.acquisition_source,
       COUNT(*)                                     AS total_orders,
       SUM(o.returned)                              AS returned_orders,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 2) AS return_rate_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name, c.city, c.acquisition_source
HAVING COUNT(*) >= 3
ORDER BY return_rate_pct DESC, total_orders DESC
LIMIT 10;

-- Expected output (from a real run of this file):
--   customer_id  name     city       acquisition_source  total_orders  returned_orders  return_rate_pct
--   -----------  -------  ---------  ------------------  ------------  ---------------  ---------------
--   C028         Shreya   Bangalore  Ad                  5             4                80.0           
--   C025         Varun    Jaipur     Social              3             2                66.67          
--   C024         Riya     Lucknow    Referral            7             4                57.14          
--   C029         Tanish   Delhi      Social              6             3                50.0           
--   C041         Ayaan    Lucknow    Organic             4             2                50.0           
--   C042         Sanya    Mumbai     Social              7             3                42.86          
--   C026         Isha     Lucknow    Organic             5             2                40.0           
--   C035         Krishna  Jaipur     Ad                  5             2                40.0           
--   C008         Meera    Lucknow    Ad                  9             3                33.33          
--   C010         Sara     Mumbai     Organic             9             3                33.33          

-- ===== REPORT 5: City-wise performance (kis shehar se paisa aur returns?) =====
-- Pairs revenue with return rate so a "good" city cannot hide a bad return rate.
SELECT c.city,
       COUNT(DISTINCT c.customer_id)                AS customers,
       COUNT(*)                                     AS total_orders,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
                                                    AS revenue,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 2) AS return_rate_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products  p ON p.product_id  = o.product_id
GROUP BY c.city
ORDER BY revenue DESC;

-- Expected output (from a real run of this file):
--   city       customers  total_orders  revenue  return_rate_pct
--   ---------  ---------  ------------  -------  ---------------
--   Bangalore  9          33            28138.4  24.24          
--   Lucknow    11         49            27523.3  30.61          
--   Mumbai     12         56            25143.4  17.86          
--   Delhi      6          23            10151.7  17.39          
--   Jaipur     6          19            8903.4   42.11          

-- ===== REPORT 6: Acquisition channel ROI (kis channel ke customers wapas karte hain?) =====
-- Business question: which marketing channel brings customers who actually keep
-- the product? Three-table join, revenue normalised per customer.
SELECT c.acquisition_source,
       COUNT(*)                                     AS total_orders,
       COUNT(DISTINCT c.customer_id)                AS customers,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
                                                    AS revenue,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0))
             / COUNT(DISTINCT c.customer_id), 2)    AS revenue_per_customer,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 2) AS return_rate_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products  p ON p.product_id  = o.product_id
GROUP BY c.acquisition_source
ORDER BY revenue DESC;

-- Expected output (from a real run of this file):
--   acquisition_source  total_orders  customers  revenue  revenue_per_customer  return_rate_pct
--   ------------------  ------------  ---------  -------  --------------------  ---------------
--   Ad                  53            14         36674.7  2619.62               32.08          
--   Organic             62            13         32435.9  2495.07               17.74          
--   Social              35            9          15798.3  1755.37               28.57          
--   Referral            30            8          14951.3  1868.91               23.33          

-- ===== REPORT 7: Product-level returns + revenue lost (kaunsa product paisa kha raha hai?) =====
-- A high return rate and a big rupee loss are different problems: a cheap
-- product returning often can still cost less than an expensive one returning rarely.
-- That is why both columns are shown side by side.
SELECT p.product_id,
       p.product_name,
       p.category,
       p.price,
       COUNT(*)                                     AS total_orders,
       SUM(o.returned)                              AS returned_orders,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 2) AS return_rate_pct,
       ROUND(SUM(CASE WHEN o.returned = 1
                      THEN o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)
                      ELSE 0 END), 2)               AS revenue_lost_to_returns
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY p.product_id, p.product_name, p.category, p.price
ORDER BY return_rate_pct DESC, revenue_lost_to_returns DESC;

-- Expected output (from a real run of this file):
--   product_id  product_name            category      price  total_orders  returned_orders  return_rate_pct  revenue_lost_to_returns
--   ----------  ----------------------  ------------  -----  ------------  ---------------  ---------------  -----------------------
--   P12         Baby Shampoo            Babycare      249.0  6             4                66.67            1319.7                 
--   P04         Anti-Hairfall Serum     Haircare      649.0  7             3                42.86            1557.6                 
--   P08         Tea Tree Face Wash      Skincare      229.0  17            6                35.29            1763.3                 
--   P07         Vitamin C Serum         Skincare      699.0  12            4                33.33            3005.7                 
--   P10         Rice Sunscreen SPF50    Skincare      449.0  16            5                31.25            3771.6                 
--   P16         Aloe Vera Gel           PersonalCare  199.0  10            3                30.0             477.6                  
--   P06         Vitamin C Face Wash     Skincare      249.0  7             2                28.57            697.2                  
--   P02         Onion Shampoo           Haircare      399.0  11            3                27.27            1795.5                 
--   P03         Argan Hair Mask         Haircare      599.0  15            4                26.67            3594.0                 
--   P09         Ubtan Face Mask         Skincare      299.0  8             2                25.0             448.5                  
--   P05         Rice Water Conditioner  Haircare      349.0  10            2                20.0             837.6                  
--   P01         Onion Hair Oil          Haircare      349.0  11            2                18.18            593.3                  
--   P13         Baby Massage Oil        Babycare      279.0  7             1                14.29            558.0                  
--   P14         Charcoal Deodorant      PersonalCare  199.0  14            2                14.29            298.5                  
--   P11         Milky Soft Baby Lotion  Babycare      299.0  17            2                11.76            8073.0                 
--   P15         Tea Tree Body Wash      PersonalCare  349.0  12            0                0.0              0.0                    

-- ===== REPORT 8: Discount level vs return rate (zyada discount = zyada return?) =====
-- Tests the obvious-sounding theory that discounts attract returners.
-- CASE buckets the discount percentage into four named levels.
SELECT CASE
           WHEN COALESCE(o.discount_pct, 0) = 0 THEN '1. No discount (0%)'
           WHEN o.discount_pct <= 10            THEN '2. Low (1-10%)'
           WHEN o.discount_pct <= 20            THEN '3. Medium (11-20%)'
           ELSE                                      '4. High (21-30%)'
       END                                          AS discount_bucket,
       COUNT(*)                                     AS total_orders,
       SUM(o.returned)                              AS returned_orders,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 2) AS return_rate_pct,
       ROUND(AVG(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
                                                    AS avg_order_value
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY discount_bucket
ORDER BY discount_bucket;

-- Expected output (from a real run of this file):
--   discount_bucket      total_orders  returned_orders  return_rate_pct  avg_order_value
--   -------------------  ------------  ---------------  ---------------  ---------------
--   1. No discount (0%)  38            11               28.95            1023.61        
--   2. Low (1-10%)       41            11               26.83            459.02         
--   3. Medium (11-20%)   41            13               31.71            433.35         
--   4. High (21-30%)     60            10               16.67            406.27         

-- ===== REPORT 9: Monthly trend (business badh raha hai ya ghat raha hai?) =====
-- Revenue, units and return rate per month. Note: January looks like the best
-- month here - Part 2 shows that this comes from 2 bulk orders (outliers).
SELECT strftime('%Y-%m', o.order_date)             AS order_month,
       COUNT(*)                                    AS total_orders,
       SUM(o.quantity)                             AS units_sold,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2)
                                                   AS revenue,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 2) AS return_rate_pct
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY order_month
ORDER BY order_month;

-- Expected output (from a real run of this file):
--   order_month  total_orders  units_sold  revenue  return_rate_pct
--   -----------  ------------  ----------  -------  ---------------
--   2026-01      24            91          29582.1  20.83          
--   2026-02      32            42          13464.6  21.88          
--   2026-03      38            66          20731.1  36.84          
--   2026-04      27            32          9495.3   37.04          
--   2026-05      33            49          14727.4  15.15          
--   2026-06      26            40          11859.7  15.38          
