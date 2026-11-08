#  板块五：商品品类分析

use ecommerce;

#1.计算各品类的销售贡献
WITH category_sales AS (
    SELECT
        COALESCE(
            ct.product_category_name_english,
            p.product_category_name,
            'Unknown'
        ) AS category_name,
        #COALESCE处理数据缺失。优先取英文类目名，如果没有英文名就取葡语原名，如果连名字都没有就标为 'Unknown'

        COUNT(*) AS total_items,

        COUNT(DISTINCT oi.order_id) AS total_orders,

        COUNT(DISTINCT oi.product_id) AS total_products,

        SUM(oi.price) AS total_revenue,

        AVG(oi.price) AS avg_item_price

    FROM order_items oi

    JOIN orders o
        ON oi.order_id = o.order_id

    #有些商品没有登记在products中，左连接保证所有卖出的订单明细都不丢失
    LEFT JOIN products p
        ON oi.product_id = p.product_id

    #有些商品名没有登记在品类翻译表中
    LEFT JOIN category_translation ct
        ON p.product_category_name = ct.product_category_name

    WHERE o.order_status = 'delivered'

    GROUP BY
        COALESCE(
            ct.product_category_name_english,
            p.product_category_name,
            'Unknown'
        )
),

category_ranking AS (
    SELECT
        *,

        ROW_NUMBER() OVER (
            ORDER BY total_revenue DESC
        ) AS revenue_rank,
        #row_number生成行号，商品收入排名

        SUM(total_revenue) OVER (
            ORDER BY total_revenue DESC
            ROWS BETWEEN UNBOUNDED PRECEDING
            AND CURRENT ROW
        ) AS cumulative_revenue,
        #计算累计收入，即从第一名一直加到当前品类

        SUM(total_revenue) OVER () AS platform_revenue
        #所有品类总收入

    FROM category_sales
)

SELECT
    revenue_rank,
    category_name,
    total_items,
    total_orders,
    total_products,

    ROUND(total_revenue, 2) AS total_revenue,

    ROUND(avg_item_price, 2) AS avg_item_price,

    ROUND(
        total_revenue / platform_revenue * 100,
        2
    ) AS revenue_share,
    #各品类收入占比

    ROUND(
        cumulative_revenue / platform_revenue * 100,
        2
    ) AS cumulative_revenue_share
    #各品类累计收入占比，即从第 1 名到当前这个品类，累计贡献了百分之几的营收

FROM category_ranking

ORDER BY revenue_rank;
#规模驱动型：bed_bath_table,health_beauty,sports_leisure,furniture_decor，销售规模较大，
#价格驱动型：watches_gifts，cool_stuff，auto，health_beauty

#2.品类内部的商品收入集中度
#探究每个品类的销售额，是有少数畅销商品贡献的，还是分散在大量商品中的

WITH category_product_sales AS (
    -- 第一步：计算每个品类中每个商品的销售额
    SELECT
        COALESCE(
            ct.product_category_name_english,
            p.product_category_name,
            'Unknown'
        ) AS category_name,

        oi.product_id,

        SUM(oi.price) AS product_revenue

    FROM order_items oi

    JOIN orders o
        ON oi.order_id = o.order_id

    LEFT JOIN products p
        ON oi.product_id = p.product_id

    LEFT JOIN category_translation ct
        ON p.product_category_name = ct.product_category_name

    WHERE o.order_status = 'delivered'

    GROUP BY
        COALESCE(
            ct.product_category_name_english,
            p.product_category_name,
            'Unknown'
        ),
        oi.product_id
),

ranked_products AS (
    -- 第二步：在每个品类内部进行商品收入排名
    SELECT
        category_name,
        product_id,
        product_revenue,

        #在每个品类内部，按照商品收入从高到低进行排名
        ROW_NUMBER() OVER (
            PARTITION BY category_name #组内排名
            ORDER BY product_revenue DESC, product_id
        ) AS product_rank,

        #在每个品类内部，把该品类下所有商品的收入加起来
        SUM(product_revenue) OVER (
            PARTITION BY category_name
        ) AS category_revenue

    FROM category_product_sales
)

-- 第三步：汇总各品类的商品收入集中度
SELECT
    category_name,

    COUNT(*) AS total_products,

    ROUND(MAX(category_revenue), 2) AS total_revenue,

    ROUND(
        MAX(CASE WHEN product_rank = 1
            THEN product_revenue END), 2
    ) AS top1_product_revenue,

    ROUND(
        SUM(CASE WHEN product_rank <= 1
            THEN product_revenue ELSE 0 END)
        / MAX(category_revenue) * 100,
        2
    ) AS top1_product_share,
    #前1名的商品收入占比

    ROUND(
        SUM(CASE WHEN product_rank <= 5
            THEN product_revenue ELSE 0 END)
        / MAX(category_revenue) * 100,
        2
    ) AS top5_products_share,
    #前5名的商品收入占比

    ROUND(
        SUM(CASE WHEN product_rank <= 10
            THEN product_revenue ELSE 0 END),
        2
    ) AS top10_products_revenue,
    #前10名的商品收入总和

    ROUND(
        SUM(CASE WHEN product_rank <= 10
            THEN product_revenue ELSE 0 END)
        / MAX(category_revenue) * 100,
        2
    ) AS top10_products_share
    #前10名的商品收入占比

FROM ranked_products

GROUP BY category_name

HAVING COUNT(*) >= 20

ORDER BY top10_products_share DESC;
#分析可得，前10收入品类的商品收入分布相对分散，而部分小品类可能高度依赖少数商品


#3.各商品品类的"订单渗透率"
#在所有成功送达的订单中，有多大比例的订单包含该品类商品
WITH delivered_orders AS (
    #1.提取所有状态为delivered的订单id
    SELECT DISTINCT order_id
    FROM orders
    WHERE order_status = 'delivered'
),

    #2.全平台有效订单
total_orders AS (
    SELECT COUNT(*) AS total_delivered_orders
    FROM delivered_orders
),

category_orders AS (
    SELECT
        COALESCE(
            ct.product_category_name_english,
            p.product_category_name
        ) AS category_name,
        COUNT(DISTINCT oi.order_id) AS category_order_count
        #一个订单可能包含同意品类下的多件商品，去重能精准算出”有多少不同的订单买过这个品类“

    FROM order_items oi
    JOIN delivered_orders d
        ON oi.order_id = d.order_id
    JOIN products p
        ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct
        ON p.product_category_name = ct.product_category_name
    WHERE p.product_category_name IS NOT NULL
    GROUP BY
        COALESCE(
            ct.product_category_name_english,
            p.product_category_name
        )
)

SELECT
    c.category_name,
    c.category_order_count,
    t.total_delivered_orders,
    ROUND(
        c.category_order_count * 100.0
        / t.total_delivered_orders,
        2
    ) AS order_penetration_rate
FROM category_orders c
CROSS JOIN total_orders t #相当于添加一列全是total_orders的列数据
ORDER BY order_penetration_rate DESC;



# 建表保存：供交互大屏读取 (对应 3 个 CSV 文件)

DROP TABLE IF EXISTS category_sales_contribution;
CREATE TABLE category_sales_contribution AS
WITH category_sales AS (
    SELECT COALESCE(ct.product_category_name_english, p.product_category_name, 'Unknown') AS category_name,
           COUNT(*) AS total_items, COUNT(DISTINCT oi.order_id) AS total_orders, COUNT(DISTINCT oi.product_id) AS total_products,
           SUM(oi.price) AS total_revenue, AVG(oi.price) AS avg_item_price
    FROM order_items oi JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
    WHERE o.order_status = 'delivered' GROUP BY 1
),
category_ranking AS (
    SELECT *, ROW_NUMBER() OVER (ORDER BY total_revenue DESC) AS revenue_rank,
           SUM(total_revenue) OVER (ORDER BY total_revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_revenue,
           SUM(total_revenue) OVER () AS platform_revenue FROM category_sales
)
SELECT revenue_rank, category_name, total_items, total_orders, total_products, ROUND(total_revenue, 2) AS total_revenue,
       ROUND(avg_item_price, 2) AS avg_item_price, ROUND(total_revenue / platform_revenue * 100, 2) AS revenue_share,
       ROUND(cumulative_revenue / platform_revenue * 100, 2) AS cumulative_revenue_share FROM category_ranking;

DROP TABLE IF EXISTS category_internal_concentration;
CREATE TABLE category_internal_concentration AS
WITH category_product_sales AS (
    SELECT COALESCE(ct.product_category_name_english, p.product_category_name, 'Unknown') AS category_name,
           oi.product_id, SUM(oi.price) AS product_revenue
    FROM order_items oi JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
    WHERE o.order_status = 'delivered' GROUP BY 1, 2
),
ranked_products AS (
    SELECT category_name, product_id, product_revenue, ROW_NUMBER() OVER (PARTITION BY category_name ORDER BY product_revenue DESC, product_id) AS product_rank,
           SUM(product_revenue) OVER (PARTITION BY category_name) AS category_revenue FROM category_product_sales
)
SELECT category_name, COUNT(*) AS total_products, ROUND(MAX(category_revenue), 2) AS total_revenue,
       ROUND(MAX(CASE WHEN product_rank = 1 THEN product_revenue END), 2) AS top1_product_revenue,
       ROUND(SUM(CASE WHEN product_rank <= 1 THEN product_revenue ELSE 0 END) / MAX(category_revenue) * 100, 2) AS top1_product_share,
       ROUND(SUM(CASE WHEN product_rank <= 5 THEN product_revenue ELSE 0 END) / MAX(category_revenue) * 100, 2) AS top5_products_share,
       ROUND(SUM(CASE WHEN product_rank <= 10 THEN product_revenue ELSE 0 END), 2) AS top10_products_revenue,
       ROUND(SUM(CASE WHEN product_rank <= 10 THEN product_revenue ELSE 0 END) / MAX(category_revenue) * 100, 2) AS top10_products_share
FROM ranked_products GROUP BY category_name HAVING COUNT(*) >= 20;

DROP TABLE IF EXISTS category_order_penetration;
CREATE TABLE category_order_penetration AS
WITH delivered_orders AS (
    SELECT DISTINCT order_id FROM orders WHERE order_status = 'delivered'
),
total_orders AS (
    SELECT COUNT(*) AS total_delivered_orders FROM delivered_orders
),
category_orders AS (
    SELECT COALESCE(ct.product_category_name_english, p.product_category_name) AS category_name, COUNT(DISTINCT oi.order_id) AS category_order_count
    FROM order_items oi JOIN delivered_orders d ON oi.order_id = d.order_id
    JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
    WHERE p.product_category_name IS NOT NULL GROUP BY 1
)
SELECT c.category_name, c.category_order_count, t.total_delivered_orders,
       ROUND(c.category_order_count * 100.0 / t.total_delivered_orders, 2) AS order_penetration_rate
FROM category_orders c CROSS JOIN total_orders t;