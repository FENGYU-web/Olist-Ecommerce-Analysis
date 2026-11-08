#  板块四：卖家与商品品类经营表现分析

use ecommerce;

#1.卖家经营表现
WITH seller_order AS (
    -- 1. 计算每个卖家在每笔订单中的销售情况
    SELECT
        seller_id,
        order_id,
        COUNT(*) AS item_count,
        SUM(price) AS product_revenue,
        SUM(freight_value) AS freight_revenue
    FROM order_items
    GROUP BY seller_id, order_id
),

review_by_order AS (
    -- 2. 先将评价汇总到订单粒度
    SELECT
        order_id,
        COUNT(*) AS review_count,
        AVG(review_score) AS avg_review_score,
        SUM(
            CASE WHEN review_score <= 2 THEN 1 ELSE 0 END
        ) AS low_rating_count
    FROM order_reviews
    GROUP BY order_id
),

seller_order_detail AS (
    -- 3. 关联卖家订单、履约和评价信息
    SELECT
        so.seller_id,
        s.seller_city,
        s.seller_state,
        so.order_id,
        so.item_count,
        so.product_revenue,
        so.freight_revenue,

        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,

        r.review_count,
        r.avg_review_score,
        r.low_rating_count

    FROM seller_order so

    JOIN sellers s
        ON so.seller_id = s.seller_id

    JOIN orders o
        ON so.order_id = o.order_id

    LEFT JOIN review_by_order r
        ON so.order_id = r.order_id
    #并非所有的订单都有评价，以订单为主，无评论的订单评论记为null即可

    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
)

-- 4. 汇总每个卖家的经营表现
SELECT
    seller_id,
    seller_city,
    seller_state,

    COUNT(DISTINCT order_id) AS delivered_orders,
    #已送达订单数量（去重）

    SUM(item_count) AS total_items,
    #卖出商品总数

    ROUND(SUM(product_revenue), 2) AS total_product_revenue,
    #总收入

    ROUND(SUM(freight_revenue), 2) AS total_freight_revenue,
    #总运费

    ROUND(
        AVG(
            TIMESTAMPDIFF(
                HOUR,
                order_purchase_timestamp,
                order_delivered_customer_date
            ) / 24.0
        ),
        2
    ) AS avg_delivery_days,
    #平均配送天数

    SUM(
        CASE
            WHEN order_delivered_customer_date >
                 order_estimated_delivery_date
            THEN 1
            ELSE 0
        END
    ) AS delayed_orders,
    #延迟配送订单

    ROUND(
        100.0 * SUM(
            CASE
                WHEN order_delivered_customer_date >
                     order_estimated_delivery_date
                THEN 1
                ELSE 0
            END
        ) / COUNT(*),
        2
    ) AS delayed_rate,
    #延迟配送率

    COUNT(DISTINCT
        CASE
            WHEN review_count > 0 THEN order_id
        END
    ) AS reviewed_orders,
    #有评价的订单数量

    SUM(review_count) AS total_reviews,
    #评价总数（一个订单可能包含多个评价）

    ROUND(
    #   SUM( 每个订单的平均评分 * 该订单的评价数量)=该卖家的所有订单的评分总和
        SUM(avg_review_score * review_count) /
    #   /该卖家的所有评价数量
        NULLIF(SUM(review_count), 0),
        2
    ) AS avg_review_score,
    #平均评价分数

    ROUND(
        100.0 * SUM(low_rating_count) /
        NULLIF(SUM(review_count), 0),
        2
    ) AS low_rating_rate
    #差评率

FROM seller_order_detail

GROUP BY
    seller_id,
    seller_city,
    seller_state

ORDER BY total_product_revenue DESC;


#2。计算卖家商品收入排名及累计收入贡献
WITH seller_revenue AS (
    #筛选出已送达订单，按卖家分组
    SELECT
        oi.seller_id,
        COUNT(DISTINCT oi.order_id) AS delivered_orders,
        SUM(oi.price) AS total_revenue  #总商品收入（不含运费）
    FROM order_items oi
    JOIN orders o
        ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
    GROUP BY oi.seller_id
),

seller_ranking AS (
    SELECT
        seller_id,
        delivered_orders,
        total_revenue,

        #1.收入排名，按照卖家总收入降序排
        ROW_NUMBER() OVER (
            ORDER BY total_revenue DESC
        ) AS revenue_rank,

        #2.累计收入（从第一名一直累加到当前这名卖家）
        SUM(total_revenue) OVER (
            ORDER BY total_revenue DESC
            ROWS BETWEEN UNBOUNDED PRECEDING
            AND CURRENT ROW
        ) AS cumulative_revenue,

        #3.全平台总收入
        SUM(total_revenue) OVER () AS platform_revenue

    FROM seller_revenue
)

SELECT
    seller_id,
    delivered_orders,
    total_revenue,
    revenue_rank,

    #个人收入占比
    ROUND(
        total_revenue / platform_revenue * 100,
        2
    ) AS revenue_share,

    #累计收入占比
    ROUND(
        cumulative_revenue / platform_revenue * 100,
        2
    ) AS cumulative_revenue_share

FROM seller_ranking
ORDER BY revenue_rank;
#结果表明：卖家收入存在明显的头部集中现象，但并不是一家独大，而是有多个高收入卖家共同贡献


#3.计算卖家收入集中度
#评估平台上排名前 1%、前 5%、前 10%、前 20%、前 50% 的卖家，分别贡献了全平台百分之多少的总收入
WITH seller_revenue AS (
    #计算单个卖家的总收入
    SELECT
        oi.seller_id,
        SUM(oi.price) AS total_revenue
    FROM order_items oi
    JOIN orders o
        ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
    GROUP BY oi.seller_id
),

seller_ranking AS (
    SELECT
        seller_id,
        total_revenue,

        ROW_NUMBER() OVER (
        #给卖家排名，如果收入一样，就按卖家id排名
            ORDER BY total_revenue DESC, seller_id
        ) AS revenue_rank,

        COUNT(*) OVER () AS total_sellers,
        #卖家总数

        SUM(total_revenue) OVER () AS platform_revenue
        #平台总收入

    FROM seller_revenue
)

SELECT
    #计算前1%的收入贡献
    'Top 1%' AS seller_group,
    CEIL(MAX(total_sellers) * 0.01) AS seller_count,
    ROUND(
        SUM(CASE
            WHEN revenue_rank <= CEIL(total_sellers * 0.01)
            THEN total_revenue ELSE 0
        END) / MAX(platform_revenue) * 100, 2
    ) AS revenue_contribution
FROM seller_ranking

UNION ALL

SELECT
    #计算前5%的收入贡献
    'Top 5%',
    CEIL(MAX(total_sellers) * 0.05),
    ROUND(
        SUM(CASE
            WHEN revenue_rank <= CEIL(total_sellers * 0.05)
            THEN total_revenue ELSE 0
        END) / MAX(platform_revenue) * 100, 2
    )
FROM seller_ranking

UNION ALL

SELECT
    #计算前10%的收入贡献
    'Top 10%',
    CEIL(MAX(total_sellers) * 0.10),
    ROUND(
        SUM(CASE
            WHEN revenue_rank <= CEIL(total_sellers * 0.10)
            THEN total_revenue ELSE 0
        END) / MAX(platform_revenue) * 100, 2
    )
FROM seller_ranking

UNION ALL

SELECT
    #计算前20%的收入贡献
    'Top 20%',
    CEIL(MAX(total_sellers) * 0.20),
    ROUND(
        SUM(CASE
            WHEN revenue_rank <= CEIL(total_sellers * 0.20)
            THEN total_revenue ELSE 0
        END) / MAX(platform_revenue) * 100, 2
    )
FROM seller_ranking

UNION ALL

SELECT
    #计算前50%的收入贡献
    'Top 50%',
    CEIL(MAX(total_sellers) * 0.50),
    ROUND(
        SUM(CASE
            WHEN revenue_rank <= CEIL(total_sellers * 0.50)
            THEN total_revenue ELSE 0
        END) / MAX(platform_revenue) * 100, 2
    )
FROM seller_ranking;



# 建表保存：供交互大屏读取 (对应 seller_performance.csv 和 seller_revenue_ranking.csv)

DROP TABLE IF EXISTS seller_revenue_ranking;
CREATE TABLE seller_revenue_ranking AS
WITH seller_revenue AS (
    SELECT oi.seller_id, SUM(oi.price) AS total_revenue FROM order_items oi JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL GROUP BY oi.seller_id
),
seller_ranking AS (
    SELECT seller_id, total_revenue, ROW_NUMBER() OVER (ORDER BY total_revenue DESC, seller_id) AS revenue_rank,
           SUM(total_revenue) OVER (ORDER BY total_revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_revenue,
           SUM(total_revenue) OVER () AS platform_revenue
    FROM seller_revenue
)
SELECT seller_id, total_revenue, revenue_rank, ROUND(total_revenue / platform_revenue * 100, 2) AS revenue_share,
       ROUND(cumulative_revenue / platform_revenue * 100, 2) AS cumulative_revenue_share
FROM seller_ranking;
USE ecommerce;


DROP TABLE IF EXISTS seller_performance;
CREATE TABLE seller_performance AS
WITH seller_order AS (
    -- 1. 计算每个卖家在每笔订单中的销售情况
    SELECT
        seller_id,
        order_id,
        COUNT(*) AS item_count,
        SUM(price) AS product_revenue,
        SUM(freight_value) AS freight_revenue
    FROM order_items
    GROUP BY seller_id, order_id
),
review_by_order AS (
    -- 2. 先将评价汇总到订单粒度
    SELECT
        order_id,
        COUNT(*) AS review_count,
        AVG(review_score) AS avg_review_score,
        SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) AS low_rating_count
    FROM order_reviews
    GROUP BY order_id
),
seller_order_detail AS (
    -- 3. 关联卖家订单、履约和评价信息
    SELECT
        so.seller_id,
        s.seller_city,
        s.seller_state,
        so.order_id,
        so.item_count,
        so.product_revenue,
        so.freight_revenue,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        r.review_count,
        r.avg_review_score,
        r.low_rating_count
    FROM seller_order so
    JOIN sellers s
        ON so.seller_id = s.seller_id
    JOIN orders o
        ON so.order_id = o.order_id
    LEFT JOIN review_by_order r
        ON so.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
)
-- 4. 汇总每个卖家的经营表现
SELECT
    seller_id,
    seller_city,
    seller_state,
    COUNT(DISTINCT order_id) AS delivered_orders,
    SUM(item_count) AS total_items,
    ROUND(SUM(product_revenue), 2) AS total_product_revenue,
    ROUND(SUM(freight_revenue), 2) AS total_freight_revenue,
    ROUND(AVG(TIMESTAMPDIFF(HOUR, order_purchase_timestamp, order_delivered_customer_date) / 24.0), 2) AS avg_delivery_days,
    SUM(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END) AS delayed_orders,
    ROUND(100.0 * SUM(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END) / COUNT(*), 2) AS delayed_rate,
    COUNT(DISTINCT CASE WHEN review_count > 0 THEN order_id END) AS reviewed_orders,
    SUM(review_count) AS total_reviews,
    ROUND(SUM(avg_review_score * review_count) / NULLIF(SUM(review_count), 0), 2) AS avg_review_score,
    ROUND(100.0 * SUM(low_rating_count) / NULLIF(SUM(review_count), 0), 2) AS low_rating_rate
FROM seller_order_detail
GROUP BY
    seller_id,
    seller_city,
    seller_state
ORDER BY total_product_revenue DESC;