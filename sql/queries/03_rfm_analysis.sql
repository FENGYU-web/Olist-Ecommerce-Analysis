#  板块3：RFM客户分析

use ecommerce;

#Recency 最近一次消费时间      Frequency 消费频率     Monetary 消费金额
#构建客户级RFM的基础数据，从客户的购买行为出发，识别哪些客户价值较高、哪些客户可能正在流失，以及平台应该重点维护哪些客户
WITH order_item_summary AS (
    -- 第一步：先计算每笔订单的商品金额和运费
    #一个订单可能包含多个商品，一个商品一个价格和运费
    SELECT
        order_id,
        SUM(price) AS order_amount,
        SUM(freight_value) AS order_freight
    FROM order_items
    GROUP BY order_id
),

delivered_orders AS (
    -- 第二步：筛选已送达订单，并关联客户信息
    SELECT
        o.order_id,
        c.customer_unique_id,
        #关联唯一客户信息，客户表中一个订单就有一个客户id，若一个客户有多个订单，则会产生多个订单id和客户id，customer_unique_id才是他的唯一的id

        o.order_purchase_timestamp,
        oi.order_amount,
        oi.order_freight
    FROM orders o
    JOIN customers c
        ON o.customer_id = c.customer_id
    JOIN order_item_summary oi
        ON o.order_id = oi.order_id
    #一个订单id对应一个客户id对应一个订单汇总id

    WHERE o.order_status = 'delivered'
),

reference_date AS (
    -- 第三步：确定 RFM 统计参考日期
    SELECT
        DATE_ADD(
            MAX(order_purchase_timestamp),
            INTERVAL 1 DAY
        ) AS analysis_date
    #在 delivered_orders（已送达的订单表）里，找出最晚的一笔下单时间，往后推一天
    FROM delivered_orders
)  #结果一行一列


-- 第四步：按照客户聚合，计算 R、F、M
SELECT
    d.customer_unique_id,

    DATEDIFF(
        r.analysis_date,
        MAX(d.order_purchase_timestamp)
    ) AS recency, #R 单位为天

    COUNT(DISTINCT d.order_id) AS frequency, #F 单位为频次
    #COUNT(d.order_id) AS frequency 也可以，订单id没重复

    ROUND(SUM(d.order_amount), 2) AS monetary, #M

    ROUND(SUM(d.order_freight), 2) AS total_freight

FROM delivered_orders d
CROSS JOIN reference_date r
#交叉连接，给每个客户都加上日期基准

GROUP BY
    d.customer_unique_id,
    r.analysis_date

ORDER BY monetary DESC;


#汇总RFM数据规模
WITH order_item_summary AS (
    SELECT
        order_id,
        SUM(price) AS order_amount
    FROM order_items
    GROUP BY order_id
),

customer_rfm AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(oi.order_amount) AS monetary,
        DATEDIFF(
            DATE_ADD(
                (SELECT MAX(order_purchase_timestamp)
                 FROM orders
                 WHERE order_status = 'delivered'
                   AND order_purchase_timestamp IS NOT NULL),
                INTERVAL 1 DAY
            ),
            MAX(o.order_purchase_timestamp)
        ) AS recency
    FROM orders o
    JOIN customers c
        ON o.customer_id = c.customer_id
    JOIN order_item_summary oi
        ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp IS NOT NULL
    GROUP BY c.customer_unique_id
)

SELECT
    COUNT(*) AS total_customers,
    ROUND(AVG(recency), 2) AS avg_recency,
    ROUND(AVG(frequency), 2) AS avg_frequency,
    ROUND(AVG(monetary), 2) AS avg_monetary,
    MAX(frequency) AS max_frequency,
    MAX(monetary) AS max_monetary
FROM customer_rfm;
#共有93358名客户，距今平均购买时长238.48天，平均购买频次1.03次，平均购买金额141.62BRL，最大购买频次15次，最大购买金额人13440BRL


#验证客户复购情况，有多少客户只购买过一次，有多少客户有复购？
WITH order_item_summary AS (
    SELECT
        order_id,
        SUM(price) AS order_amount
    FROM order_items
    GROUP BY order_id
),

customer_frequency AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS frequency
    FROM orders o
    JOIN customers c
        ON o.customer_id = c.customer_id
    JOIN order_item_summary oi
        ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp IS NOT NULL
    GROUP BY c.customer_unique_id
)

SELECT
    CASE
        WHEN frequency = 1 THEN 'One-time Customer'
        WHEN frequency BETWEEN 2 AND 3 THEN '2-3 Orders'
        WHEN frequency BETWEEN 4 AND 5 THEN '4-5 Orders'
        ELSE 'More than 5 Orders'
    END AS customer_group,
    #按购买频次分组

    COUNT(*) AS customer_count,

    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    ) AS customer_percentage
    #不同购买频次组的占比

FROM customer_frequency
GROUP BY customer_group
ORDER BY
    CASE customer_group
        WHEN 'One-time Customer' THEN 1
        WHEN '2-3 Orders' THEN 2
        WHEN '4-5 Orders' THEN 3
        ELSE 4
    END;
#1.客户复购现象非常少见   2.高频客户数量极少    3.需要关注客户留存



# 建表保存：供交互大屏读取 (对应 customer_rfm.csv、 rfm_scored.csv)

DROP TABLE IF EXISTS customer_rfm;
CREATE TABLE customer_rfm AS
WITH order_item_summary AS (
    SELECT
        order_id,
        SUM(price) AS order_amount
    FROM order_items
    GROUP BY order_id
)
SELECT
    c.customer_unique_id,
    COUNT(DISTINCT o.order_id) AS frequency,
    SUM(oi.order_amount) AS monetary,
    DATEDIFF(
        DATE_ADD(
            (SELECT MAX(order_purchase_timestamp)
             FROM orders
             WHERE order_status = 'delivered'
               AND order_purchase_timestamp IS NOT NULL),
            INTERVAL 1 DAY
        ),
        MAX(o.order_purchase_timestamp)
    ) AS recency
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_item_summary oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp IS NOT NULL
GROUP BY c.customer_unique_id;

DROP TABLE IF EXISTS rfm_scored;
CREATE TABLE rfm_scored AS
WITH order_item_summary AS (
    SELECT order_id, SUM(price) AS order_amount FROM order_items GROUP BY order_id
),
delivered_orders AS (
    SELECT o.order_id, c.customer_unique_id, o.order_purchase_timestamp, oi.order_amount
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_item_summary oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered' AND o.order_purchase_timestamp IS NOT NULL
),
reference_date AS (
    SELECT DATE_ADD(MAX(order_purchase_timestamp), INTERVAL 1 DAY) AS analysis_date FROM delivered_orders
),
rfm_base AS (
    SELECT d.customer_unique_id, DATEDIFF(r.analysis_date, MAX(d.order_purchase_timestamp)) AS recency,
           COUNT(DISTINCT d.order_id) AS frequency, SUM(d.order_amount) AS monetary
    FROM delivered_orders d CROSS JOIN reference_date r
    GROUP BY d.customer_unique_id, r.analysis_date
),
rfm_scores AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency ASC) AS R_score,
        NTILE(5) OVER (ORDER BY frequency ASC) AS F_score,
        NTILE(5) OVER (ORDER BY monetary ASC) AS M_score
    FROM rfm_base
)
SELECT
    customer_unique_id, recency, frequency, monetary, R_score, F_score, M_score,
    CASE
        WHEN R_score >= 4 AND F_score >= 4 AND M_score >= 4 THEN 'Champions'
        WHEN R_score >= 3 AND F_score >= 3 AND M_score >= 3 THEN 'Loyal Customers'
        WHEN R_score >= 4 AND F_score <= 2 AND M_score <= 2 THEN 'Potential Loyalists'
        WHEN R_score <= 2 AND F_score >= 3 AND M_score >= 3 THEN 'At Risk'
        WHEN R_score <= 2 AND F_score <= 2 AND M_score <= 2 THEN 'Hibernating'
        ELSE 'Other Customers'
    END AS customer_segment
FROM rfm_scores;