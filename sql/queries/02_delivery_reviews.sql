#  板块二：客户满意度与配送延迟分析

use ecommerce;

#1.针对送达的订单，判断每个订单是否准时送达
SELECT
        order_id,

        CASE
            WHEN order_delivered_customer_date
                 <= order_estimated_delivery_date
            THEN 'On-time'
            ELSE 'Delayed'
        END AS delivery_status

    FROM orders

    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL;


#2.查看延迟订单和准时订单平均评分有无区别
#先将订单分为两组：准时和延迟，然后比较两组客户的平均评分
WITH delivery_status AS (
    SELECT
        order_id,

        CASE
            WHEN order_delivered_customer_date
                 <= order_estimated_delivery_date
            THEN 'On-time'
            ELSE 'Delayed'
        END AS delivery_status

    FROM orders

    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
)

SELECT
    d.delivery_status,

    COUNT(*) AS review_count,

    COUNT(DISTINCT r.order_id) AS reviewed_orders,
    #一个订单可能会有多条评论，内连接会导致可能一个订单出现多行，因此要去重

    ROUND(AVG(r.review_score), 2) AS avg_review_score,
    #评论均分，小数点后保留两位

    ROUND(
        AVG(
            CASE
                WHEN r.review_score <= 2 THEN 1
                ELSE 0
            END
        ) * 100,
        2
    ) AS low_rating_rate
    #差评率，对评分≤2的评论看作差评，avg（）*100计算差评率，小数点后保留两位

FROM delivery_status d

#内连接，只有那些在 order_reviews 表里能找到评价记录的订单且已送达的订单，才会被保留下来。
#如果某个已送达的订单客户没有给评价，这个订单就会被直接丢弃

    JOIN order_reviews r
    ON d.order_id = r.order_id

GROUP BY d.delivery_status

ORDER BY avg_review_score;
#分析结果可知：准时送达的订单评分明显高于延迟抵达的订单评分


#3.是否延迟越严重，客户评分越低？研究延迟程度和客户评分之间是否存在梯度关系
#将订单按照延迟程度分为4组
WITH review_data AS (
    #定义临时表 review_data
    SELECT
        o.order_id,
        r.review_id,
        r.review_score,
        #order_id可能会重复，一个订单可能会有多个review_id

        DATEDIFF(
            o.order_delivered_customer_date,
            o.order_estimated_delivery_date
        ) AS delay_days
        #送达时间-预估时间=延迟时间，为负数即为按时送达

    FROM orders o

    JOIN order_reviews r
        ON o.order_id = r.order_id
    #内连接，只研究送达的且有评分的订单

    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
),

delay_groups AS (
    #定义临时表 delay_groups
    SELECT
        order_id,
        review_id,
        review_score,
        delay_days,

        CASE
            WHEN delay_days <= 0 THEN 'On-time'
            WHEN delay_days BETWEEN 1 AND 3 THEN '1-3 days'
            WHEN delay_days BETWEEN 4 AND 7 THEN '4-7 days'
            ELSE 'More than 7 days'
        END AS delay_group
        #按照延迟程度分组

    FROM review_data
)

SELECT
    delay_group,

    COUNT(*) AS review_count,

    ROUND(AVG(review_score), 2) AS avg_review_score,

    ROUND(
        AVG(
            CASE
                WHEN review_score <= 2 THEN 1
                ELSE 0
            END
        ) * 100,
        2
    ) AS low_rating_rate

FROM delay_groups

GROUP BY delay_group

ORDER BY
    #给每个文本赋予了一个数字权重（1, 2, 3, 4），然后再按这个权重排序，呈现结果更符合实际
    CASE delay_group
        WHEN 'On-time' THEN 1
        WHEN '1-3 days' THEN 2
        WHEN '4-7 days' THEN 3
        ELSE 4
    END;
#显然，延迟程度越高，评分越低


#4.不同评分的订，延迟比例分别是多少
#前两个查询是从配送情况出发，看评分如何变化，现在反过来从评分出发，看低分订单中有多少是延迟订单

WITH review_data AS (
    SELECT
        r.review_id,
        r.order_id,
        r.review_score,

        CASE
            WHEN o.order_delivered_customer_date
                 > o.order_estimated_delivery_date
            THEN 'Delayed'
            ELSE 'On-time'
        END AS delivery_status
        #定义按时送达和延迟送达

    FROM order_reviews r

    JOIN orders o
        ON r.order_id = o.order_id
    #内连接，只查询已送达的且有评分的订单
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
)

SELECT
    review_score,

    COUNT(*) AS review_count,

    SUM(
        CASE
            WHEN delivery_status = 'Delayed' THEN 1
            ELSE 0
        END
    ) AS delayed_reviews,
    #对应组中延迟订单数量

    ROUND(
        AVG(
            CASE
                WHEN delivery_status = 'Delayed' THEN 1
                ELSE 0
            END
        ) * 100,
        2
    ) AS delayed_rate
    #订单延迟率

FROM review_data

GROUP BY review_score
#按照评分分组

ORDER BY review_score;
#评分越低的组的订单延迟率越高,即低分评价对应的订单更容易出现配送延迟


# 板块二附加：客户评价相应行为分析

#1.时间字段质量检查
#评价创建时间可能只有日期，而没有准确的调查发送时刻，很多记录的时间都是00：00：00，后续研究时间差的单位就需要特别注意
SELECT
    COUNT(*) AS total_reviews,

    SUM(
        TIME(review_creation_date) = '00:00:00'
    ) AS midnight_records,

    ROUND(
        AVG(
            TIME(review_creation_date) = '00:00:00'
        ) * 100, 2
    ) AS midnight_percentage

FROM order_reviews;


#2.从实际收货到提交评价的时间（响应时间）与评分的关系
#按照响应时间分组，查询每组的差评率
SELECT
    CASE
        WHEN response_hours < 24 THEN 'Less than 1 day'
        WHEN response_hours < 72 THEN '1-3 days'
        WHEN response_hours < 168 THEN '3-7 days'
        ELSE 'More than 7 days'
    END AS response_group,
    #针对响应时间分组

    COUNT(*) AS review_count,

    ROUND(AVG(review_score), 2) AS avg_review_score,

    ROUND(
        SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END)
        / COUNT(*) * 100,
        2
    ) AS low_rating_rate

FROM (
    SELECT
        r.review_score,
        TIMESTAMPDIFF(
            HOUR,
            o.order_delivered_customer_date,
            r.review_answer_timestamp
        ) AS response_hours
        #响应时间=评价时间-送达时间，单位为小时
        #因为客户评价时间和送达时间都精确到具体时刻了

    FROM order_reviews r
    JOIN orders o
        ON r.order_id = o.order_id

    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND r.review_answer_timestamp IS NOT NULL
      AND r.review_answer_timestamp >= o.order_delivered_customer_date
      #过滤脏数据
) AS delivery_response

GROUP BY response_group
ORDER BY
    CASE response_group
        WHEN 'Less than 1 day' THEN 1
        WHEN '1-3 days' THEN 2
        WHEN '3-7 days' THEN 3
        ELSE 4
    END;
#极端情绪驱动：<1天的差评率都显著高于中间组。客户通常不会无缘无故守着电脑等问卷。收到问卷立刻填写的，大概率是两种情况：极度满意（超出预期，立刻给 5 星）。极度愤怒（物流严重延误、收到烂货、或者被客服气到了，立刻去填差评发泄）。
#黄金沉淀期（1-3 天）：1-3 days 的组人数最多（53,477 人），且差评率最低（9.06%），平均分最高（4.30）。原因：这批客户是“理智型消费者”。他们收到货，用了一两天，觉得没问题，顺手给个好评。这代表了平台的“基盘健康度”。
#拖延症与反悔期（>7 天）：拖了 7 天以上才评价的，差评率再次攀升（12.21% - 16.58%）。原因：客户本来不想评价，系统可能发了催评邮件才来填。或者商品用了几天后出现了质量问题（比如衣服洗坏了），导致他们回来给差评。


#3.不同响应时间区间的评分差异
#按评价响应时长分组，看每组的差评率
SELECT
    CASE
        WHEN response_days = 0 THEN 'Same day'
        WHEN response_days BETWEEN 1 AND 3 THEN '1-3 days'
        WHEN response_days BETWEEN 4 AND 7 THEN '4-7 days'
        ELSE 'More than 7 days'
    END AS response_group,

    COUNT(*) AS review_count,

    ROUND(AVG(review_score), 2) AS avg_review_score,

    ROUND(
        SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END)
        / COUNT(*) * 100,
        2
    ) AS low_rating_rate

FROM (
    SELECT
        review_score,
        DATEDIFF(review_answer_timestamp, review_creation_date)
        #评价相应时长=评价时间-问卷发出时间，单位为天
            AS response_days
    FROM order_reviews
    WHERE review_creation_date IS NOT NULL
      AND review_answer_timestamp IS NOT NULL
      AND DATE(review_answer_timestamp) >= DATE(review_creation_date)
) AS review_response

GROUP BY response_group
ORDER BY
    CASE response_group
        WHEN 'Same day' THEN 1
        WHEN '1-3 days' THEN 2
        WHEN '4-7 days' THEN 3
        ELSE 4
    END;
#当天评价的人中，有五分之一给了 1-2 分的差评。这说明负面情绪往往比正面情绪更能驱动客户“马上行动”
#拖了 7 天以上才评价的，差评率再次攀升（12.21% - 16.58%）。原因：客户本来不想评价，系统可能发了催评邮件才来填。或者商品用了几天后出现了质量问题（比如衣服洗坏了），导致他们回来给差评。


#4.不同评分的平均评价响应时间
#按照评分分组，看每组的平均评论响应时长
SELECT
    review_score,
    COUNT(*) AS review_count,
    ROUND(
        AVG(DATEDIFF(review_answer_timestamp, review_creation_date)),
        2
    ) AS avg_response_days
FROM order_reviews
WHERE review_creation_date IS NOT NULL
  AND review_answer_timestamp IS NOT NULL
  AND DATE(review_answer_timestamp) >= DATE(review_creation_date)
GROUP BY review_score
ORDER BY review_score;


# 建表保存：供交互大屏读取 (对应 6 个 CSV 文件)

DROP TABLE IF EXISTS delivery_vs_score;
CREATE TABLE delivery_vs_score AS
WITH delivery_status AS (
    SELECT order_id, CASE WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN 'On-time' ELSE 'Delayed' END AS delivery_status
    FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL AND order_estimated_delivery_date IS NOT NULL
)
SELECT d.delivery_status, COUNT(*) AS review_count, COUNT(DISTINCT r.order_id) AS reviewed_orders,
       ROUND(AVG(r.review_score), 2) AS avg_review_score,
       ROUND(AVG(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END) * 100, 2) AS low_rating_rate
FROM delivery_status d JOIN order_reviews r ON d.order_id = r.order_id GROUP BY d.delivery_status;

DROP TABLE IF EXISTS delay_gradient;
CREATE TABLE delay_gradient AS
WITH review_data AS (
    SELECT o.order_id, r.review_score, DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) AS delay_days
    FROM orders o JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL AND o.order_estimated_delivery_date IS NOT NULL
),
delay_groups AS (
    SELECT review_score, CASE
        WHEN delay_days <= 0 THEN 'On-time'
        WHEN delay_days BETWEEN 1 AND 3 THEN '1-3 days'
        WHEN delay_days BETWEEN 4 AND 7 THEN '4-7 days'
        ELSE 'More than 7 days' END AS delay_group
    FROM review_data
)
SELECT delay_group, COUNT(*) AS review_count, ROUND(AVG(review_score), 2) AS avg_review_score,
       ROUND(AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) * 100, 2) AS low_rating_rate
FROM delay_groups GROUP BY delay_group;

DROP TABLE IF EXISTS score_vs_delay;
CREATE TABLE score_vs_delay AS
WITH review_data AS (
    SELECT r.review_score, CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 'Delayed' ELSE 'On-time' END AS delivery_status
    FROM order_reviews r JOIN orders o ON r.order_id = o.order_id
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL AND o.order_estimated_delivery_date IS NOT NULL
)
SELECT review_score, COUNT(*) AS review_count,
       SUM(CASE WHEN delivery_status = 'Delayed' THEN 1 ELSE 0 END) AS delayed_reviews,
       ROUND(AVG(CASE WHEN delivery_status = 'Delayed' THEN 1 ELSE 0 END) * 100, 2) AS delayed_rate
FROM review_data GROUP BY review_score;

DROP TABLE IF EXISTS response_time_hours;
CREATE TABLE response_time_hours AS
SELECT
    CASE
        WHEN response_hours < 24 THEN 'Less than 1 day'
        WHEN response_hours < 72 THEN '1-3 days'
        WHEN response_hours < 168 THEN '3-7 days'
        ELSE 'More than 7 days' END AS response_group,
    COUNT(*) AS review_count, ROUND(AVG(review_score), 2) AS avg_review_score,
    ROUND(SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS low_rating_rate
FROM (
    SELECT r.review_score, TIMESTAMPDIFF(HOUR, o.order_delivered_customer_date, r.review_answer_timestamp) AS response_hours
    FROM order_reviews r JOIN orders o ON r.order_id = o.order_id
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
      AND r.review_answer_timestamp IS NOT NULL AND r.review_answer_timestamp >= o.order_delivered_customer_date
) AS delivery_response GROUP BY response_group;

DROP TABLE IF EXISTS response_time_days;
CREATE TABLE response_time_days AS
SELECT
    CASE
        WHEN response_days = 0 THEN 'Same day'
        WHEN response_days BETWEEN 1 AND 3 THEN '1-3 days'
        WHEN response_days BETWEEN 4 AND 7 THEN '4-7 days'
        ELSE 'More than 7 days' END AS response_group,
    COUNT(*) AS review_count, ROUND(AVG(review_score), 2) AS avg_review_score,
    ROUND(SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS low_rating_rate
FROM (
    SELECT review_score, DATEDIFF(review_answer_timestamp, review_creation_date) AS response_days
    FROM order_reviews WHERE review_creation_date IS NOT NULL AND review_answer_timestamp IS NOT NULL
      AND DATE(review_answer_timestamp) >= DATE(review_creation_date)
) AS review_response GROUP BY response_group;

DROP TABLE IF EXISTS score_vs_response_time;
CREATE TABLE score_vs_response_time AS
SELECT review_score, COUNT(*) AS review_count,
       ROUND(AVG(DATEDIFF(review_answer_timestamp, review_creation_date)), 2) AS avg_response_days
FROM order_reviews
WHERE review_creation_date IS NOT NULL AND review_answer_timestamp IS NOT NULL
  AND DATE(review_answer_timestamp) >= DATE(review_creation_date)
GROUP BY review_score;