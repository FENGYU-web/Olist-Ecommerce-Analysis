# 板块一：订单履约分析

use ecommerce;

#1.订单履约率
#针对已送达的订单，分别计算订单商品的平均配送时长、准时交付率，延迟订单数
SELECT
    COUNT(*) AS delivered_orders,

    ROUND(
        AVG(
            DATEDIFF(
                order_delivered_customer_date,
                order_purchase_timestamp
            )
        ), 2
    ) AS avg_delivery_days,

    ROUND(
        AVG(
            CASE
                WHEN order_delivered_customer_date
                     <= order_estimated_delivery_date
                THEN 1
                ELSE 0
            END
        ) * 100, 2
    ) AS on_time_rate,

    SUM(
        CASE
            WHEN order_delivered_customer_date
                 > order_estimated_delivery_date
            THEN 1
            ELSE 0
        END
    ) AS delayed_orders

FROM orders

#前提是针对已送达的订单，且送达时间和预估送达时间非空
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
  AND order_estimated_delivery_date IS NOT NULL;
#对于96470个已送达订单来说，平均配送时长为12.5天，准时交付率91.89%，延迟订单数7826单


#2.将orders和customers两张表连起来
#即将顾客和订单按照顾客id连接起来，按顾客所在州分组，查看每个州的配送订单数量、平均配送时长以及准时交付率，并按准时交付率升序排列
SELECT
    c.customer_state,

    COUNT(*) AS delivered_orders,

    ROUND(
        AVG(
            DATEDIFF(
                o.order_delivered_customer_date,
                o.order_purchase_timestamp
            )
        ), 2
    ) AS avg_delivery_days,

    ROUND(
        AVG(
            CASE
                WHEN o.order_delivered_customer_date
                     <= o.order_estimated_delivery_date
                THEN 1
                ELSE 0
            END
        ) * 100, 2
    ) AS on_time_rate

FROM orders o

JOIN customers c
    ON o.customer_id = c.customer_id

WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL

GROUP BY c.customer_state

ORDER BY on_time_rate ASC;
#由结果分析可知，AL、MA的配送效率较低，RO、AC的配送效率较高


# =====================================
# 建表保存：供交互大屏读取 (对应 overall_delivery_kpi.csv 和 state_delivery_performance.csv)
# =====================================
DROP TABLE IF EXISTS overall_delivery_kpi;
CREATE TABLE overall_delivery_kpi AS
SELECT
    COUNT(*) AS delivered_orders,
    ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)), 2) AS avg_delivery_days,
    ROUND(AVG(CASE WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN 1 ELSE 0 END) * 100, 2) AS on_time_rate,
    SUM(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END) AS delayed_orders
FROM orders
WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL AND order_estimated_delivery_date IS NOT NULL;

DROP TABLE IF EXISTS state_delivery_performance;
CREATE TABLE state_delivery_performance AS
SELECT
    c.customer_state,
    COUNT(*) AS delivered_orders,
    ROUND(AVG(DATEDIFF(o.order_delivered_customer_date, o.order_purchase_timestamp)), 2) AS avg_delivery_days,
    ROUND(AVG(CASE WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date THEN 1 ELSE 0 END) * 100, 2) AS on_time_rate
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL AND o.order_estimated_delivery_date IS NOT NULL
GROUP BY c.customer_state;