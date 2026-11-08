#建立MySQL数据库
create database if not exists ecommerce character set utf8mb4 collate utf8mb4_unicode_ci;
use ecommerce;
show tables;


#创建所需的9张表
-- =====================================
-- 1. customers：客户信息表
-- =====================================

CREATE TABLE customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_city VARCHAR(100),
    customer_state CHAR(2),

    INDEX idx_customer_unique_id (customer_unique_id),
    INDEX idx_customer_state (customer_state)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =====================================
-- 2. sellers：卖家信息表
-- =====================================

CREATE TABLE sellers (
    seller_id VARCHAR(32) PRIMARY KEY,
    seller_city VARCHAR(100),
    seller_state CHAR(2),

    INDEX idx_seller_state (seller_state)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =====================================
-- 3. products：商品信息表
-- =====================================

CREATE TABLE products (
    product_id VARCHAR(32) PRIMARY KEY,
    product_category_name VARCHAR(100),
    product_weight_g DECIMAL(10,2),
    product_length_cm DECIMAL(10,2),
    product_height_cm DECIMAL(10,2),
    product_width_cm DECIMAL(10,2),

    INDEX idx_product_category (product_category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =====================================
-- 4. category_translation：商品类别翻译表
-- =====================================

CREATE TABLE category_translation (
    product_category_name VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =====================================
-- 5. orders：订单信息表
-- =====================================

CREATE TABLE orders (
    order_id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL,
    order_status VARCHAR(30),

    order_purchase_timestamp DATETIME,
    order_approved_at DATETIME,
    order_delivered_carrier_date DATETIME,
    order_delivered_customer_date DATETIME,
    order_estimated_delivery_date DATETIME,

    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id),

    INDEX idx_orders_customer (customer_id),
    INDEX idx_orders_purchase_time (order_purchase_timestamp),
    INDEX idx_orders_status (order_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =====================================
-- 6. order_items：订单商品明细表
-- =====================================

CREATE TABLE order_items (
    order_id VARCHAR(32) NOT NULL,
    order_item_id INT NOT NULL,
    product_id VARCHAR(32),
    seller_id VARCHAR(32),

    shipping_limit_date DATETIME,
    price DECIMAL(12,2),
    freight_value DECIMAL(12,2),

    PRIMARY KEY (order_id, order_item_id),

    CONSTRAINT fk_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    CONSTRAINT fk_items_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id),

    CONSTRAINT fk_items_seller
        FOREIGN KEY (seller_id)
        REFERENCES sellers(seller_id),

    INDEX idx_items_product (product_id),
    INDEX idx_items_seller (seller_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =====================================
-- 7. order_payments：支付信息表
-- =====================================

CREATE TABLE order_payments (
    order_id VARCHAR(32) NOT NULL,
    payment_sequential INT NOT NULL,
    payment_type VARCHAR(30),
    payment_installments INT,
    payment_value DECIMAL(12,2),

    PRIMARY KEY (order_id, payment_sequential),

    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    INDEX idx_payment_type (payment_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =====================================
-- 8. order_reviews：订单评价表
-- =====================================

CREATE TABLE order_reviews (
    review_id VARCHAR(32) NOT NULL,
    order_id VARCHAR(32) NOT NULL,
    review_score TINYINT,

    review_creation_date DATETIME,
    review_answer_timestamp DATETIME,

    PRIMARY KEY (review_id, order_id),

    CONSTRAINT fk_reviews_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    INDEX idx_reviews_order (order_id),
    INDEX idx_reviews_score (review_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


#在Pycharm中连接MYSQL，并将九个数据导入创建的表中

#检查导入情况
#检查八张表的行数
SELECT 'customers' AS table_name, COUNT(*) AS total_rows
FROM customers
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL
SELECT 'order_reviews', COUNT(*) FROM order_reviews
UNION ALL
SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL
SELECT 'category_translation', COUNT(*) FROM category_translation;
#customers和orders行数一致，每产生一个订单，系统就生成一个 customer_id。如果同一个人买了 3 次，customers 表里就会有 3 行，对应 3 个不同的 customer_id
#order_items比orders多很多行，说明一单多买，一个订单可能会有多个商品
#order_payments行比orders多。意味着存在“组合支付”或“多次支付”（比如一张信用卡付一半，加上代金券付一半，会产生 2 行记录）。因此做金额统计时，不能直接把订单表和支付表连起来查，必须先按 order_id 把支付金额加总。
#order_reviews行比orders少，且内部有重复，说明有些订单没有评价，且存在一单多评（如返评）


#检查订单的时间字段
SELECT
    COUNT(*) AS total_orders,

    SUM(order_purchase_timestamp IS NULL)
        AS missing_purchase_time,

    SUM(order_delivered_customer_date IS NULL)
        AS missing_delivery_time,

    SUM(order_estimated_delivery_date IS NULL)
        AS missing_estimated_time

FROM orders;


#送达客户时间order_delivered_customer_date有大量空值，只有order_status为 delivered 状态才有这个送达时间,下面8条异常数据除外
select * from orders where order_status = 'delivered' and order_delivered_customer_date is null;


#查看不同状态的订单是否有送达时间，理论上状态为delivered的订单都有送达时间，而非delivered的则无
SELECT
    order_status,
    COUNT(*) AS total_orders,
    SUM(order_delivered_customer_date IS NULL)
        AS missing_delivery_date
FROM orders
GROUP BY order_status
ORDER BY total_orders DESC;
#存在两处异常
#1.并非所有delivered的订单都有delivery_date，有8笔异常订单
#进一步排查
SELECT
    order_id,
    order_status,
    order_purchase_timestamp,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date
FROM orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NULL;


#2.并非所有canceled的订单都无delivery_date，有6笔异常订单
#进一步排查
SELECT
    order_id,
    order_status,
    order_purchase_timestamp,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date
FROM orders
WHERE order_status = 'canceled'
  AND order_delivered_customer_date IS NOT NULL;


#一个订单有可能有多条数据
SELECT
    COUNT(*) AS total_reviews,
    COUNT(DISTINCT order_id) AS reviewed_orders
FROM order_reviews;


#订单评级中所有订单都来自于订单表中订单，即评价表中的订单都能在订单主表中找到
SELECT
    COUNT(*) AS unmatched_reviews
FROM order_reviews r
LEFT JOIN orders o
    ON r.order_id = o.order_id
WHERE o.order_id IS NULL;