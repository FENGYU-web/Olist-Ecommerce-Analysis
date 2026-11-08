import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path


# 1. 页面设置与业务背景

# st.set_page_config(page_title="商品品类分析", layout="wide")
st.title("🛍️ 商品品类深度分析")
st.caption("分析口径：仅统计已送达订单；金额为商品金额之和（BRL），不含运费，不代表利润。")

st.markdown("""
### 业务目标 (Business Objective)
从收入贡献、商品级收入集中度、以及市场覆盖三个维度评估商品品类的表现。旨在识别对平台收入贡献最大的品类，并理解每个品类内部收入在商品之间的分布情况。
""")


# 2. 动态获取数据路径 & 完整品类中文化

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

# 完整版品类中英对照字典
CATEGORY_MAPPING = {
    "health_beauty": "健康与美容",
    "watches_gifts": "手表与礼品",
    "bed_bath_table": "床品与卫浴",
    "sports_leisure": "运动与休闲",
    "computers_accessories": "电脑配件",
    "furniture_decor": "家具与装饰",
    "housewares": "家居用品",
    "cool_stuff": "酷玩物品",
    "auto": "汽车用品",
    "toys": "玩具",
    "garden_tools": "园艺工具",
    "baby": "母婴用品",
    "perfumery": "香水",
    "telephony": "手机与通讯",
    "office_furniture": "办公家具",
    "stationery": "文具",
    "computers": "电脑",
    "pet_shop": "宠物用品",
    "musical_instruments": "乐器",
    "small_appliances": "小家电",
    "Unknown": "未知品类",
    "electronics": "电子产品",
    "fashion_bags_accessories": "时尚箱包与配饰",
    "consoles_games": "游戏与主机",
    "construction_tools_construction": "建筑工具",
    "luggage_accessories": "行李箱与配件",
    "home_appliances_2": "家用电器 (2)",
    "home_construction": "家居建材",
    "home_appliances": "家用电器",
    "agro_industry_and_commerce": "农业与工业商业",
    "furniture_living_room": "客厅家具",
    "home_confort": "家居舒适用品",
    "fixed_telephony": "固定电话",
    "air_conditioning": "空调",
    "audio": "音频设备",
    "small_appliances_home_oven_and_coffee": "烤箱与咖啡机",
    "kitchen_dining_laundry_garden_furniture": "厨房餐厅洗衣与花园家具",
    "books_general_interest": "大众图书",
    "construction_tools_lights": "建筑工具与照明",
    "construction_tools_safety": "建筑工具与安全",
    "industry_commerce_and_business": "工业与商业用品",
    "food": "食品",
    "market_place": "市场集市",
    "costruction_tools_garden": "建筑工具与园艺",  # 原数据拼写错误
    "art": "艺术品",
    "fashion_shoes": "时尚鞋履",
    "drinks": "饮料",
    "signaling_and_security": "信号与安全",
    "furniture_bedroom": "卧室家具",
    "books_technical": "专业图书",
    "costruction_tools_tools": "建筑工具",  # 原数据拼写错误
    "food_drink": "食品与饮料",
    "fashion_male_clothing": "男装",
    "fashion_underwear_beach": "内衣与沙滩装",
    "christmas_supplies": "圣诞用品",
    "tablets_printing_image": "平板电脑与打印影像",
    "cine_photo": "影视与摄影",
    "music": "音乐",
    "dvds_blu_ray": "DVD与蓝光",
    "party_supplies": "派对用品",
    "books_imported": "进口图书",
    "furniture_mattress_and_upholstery": "床垫与软包家具",
    "portateis_cozinha_e_preparadores_de_alimentos": "便携厨具与食品加工机",
    "fashio_female_clothing": "女装",  # 原数据拼写错误
    "fashion_sport": "运动时尚",
    "la_cuisine": "厨具",
    "arts_and_craftmanship": "艺术与手工艺",
    "diapers_and_hygiene": "尿布与卫生用品",
    "pc_gamer": "游戏电脑",
    "flowers": "鲜花",
    "home_comfort_2": "家居舒适用品 (2)",
    "cds_dvds_musicals": "音乐CD与DVD",
    "fashion_childrens_clothes": "童装",
    "security_and_services": "安全与服务"
}


@st.cache_data
def load_data():
    df_sales = pd.read_csv(DATA_DIR / "category_sales_contribution.csv")
    df_conc = pd.read_csv(DATA_DIR / "category_internal_concentration.csv")
    df_pen = pd.read_csv(DATA_DIR / "category_order_penetration.csv")

    # 清理列名
    for df in [df_sales, df_conc, df_pen]:
        df.columns = df.columns.str.strip()
        # 应用完整翻译字典
        df['category_name'] = df['category_name'].map(lambda x: CATEGORY_MAPPING.get(x, x))

    return df_sales, df_conc, df_pen


try:
    df_sales, df_conc, df_pen = load_data()
except FileNotFoundError as e:
    st.error(f"找不到数据文件：{e.filename}。请检查数据是否放在了 data/processed 目录下。")
    st.stop()


# 3. 顶部 KPI

total_categories = df_sales['category_name'].nunique()
total_revenue = df_sales['total_revenue'].sum()
top10_revenue = df_sales.sort_values('total_revenue', ascending=False).head(10)['total_revenue'].sum()
top10_share = top10_revenue / total_revenue * 100

st.subheader("核心指标 (Key Metrics)")
col1, col2, col3 = st.columns(3)
col1.metric("覆盖品类数量", f"{total_categories:,}")
col2.metric("商品销售总金额", f"BRL {total_revenue:,.0f}")
col3.metric("Top 10 品类金额占比", f"{top10_share:.2f}%")
st.divider()


# 侧边栏筛选

st.sidebar.header("⚙️ 筛选")
min_products = st.sidebar.slider("过滤商品数较少的品类 (SKU门槛)", 1, 100, 20)
st.sidebar.caption("该筛选仅影响商品收入集中度图表。")
conc_filtered = df_conc[df_conc['total_products'] >= min_products]
st.divider()


# 图一：Treemap 矩形树图

st.subheader("01 | 各品类收入贡献 (矩形树图)")
st.markdown("此树图展示了各品类的收入贡献。较大的矩形代表商品销售金额较高的品类。")

top_sales = df_sales.sort_values('total_revenue', ascending=False).head(40)

fig_tree = px.treemap(
    top_sales, path=['category_name'], values='total_revenue',
    color='revenue_share', color_continuous_scale='Blues',
)
# 使用 hovertemplate 屏蔽 parent 和 id
fig_tree.update_traces(
    hovertemplate="<b>%{label}</b><br><br>总金额: R$ %{value:,.2f}<br>收入占比: %{color:.2f}%<extra></extra>"
)

fig_tree.update_layout(template="plotly_white", margin=dict(t=30, l=10, r=10, b=10))
st.plotly_chart(fig_tree, use_container_width=True)
st.divider()


# 图二：100% 堆叠条形图

st.subheader("02 | 品类内部商品收入集中度")
st.markdown(
    "此图表按商品排名拆解了各品类的金额。它比较了 Top 1、Top 2-5、Top 6-10 以及其余商品的金额贡献。Top 商品份额越高，表明金额越集中在少数商品上。")

conc_stack = conc_filtered.copy()
conc_stack['Top 1'] = conc_stack['top1_product_share']
conc_stack['Top 2-5'] = conc_stack['top5_products_share'] - conc_stack['top1_product_share']
conc_stack['Top 6-10'] = conc_stack['top10_products_share'] - conc_stack['top5_products_share']
conc_stack['Top 11+ (长尾)'] = 100 - conc_stack['top10_products_share']

top20_conc = conc_stack.sort_values('total_revenue', ascending=False).head(20)

top20_melted = top20_conc.melt(
    id_vars=['category_name'],
    value_vars=['Top 1', 'Top 2-5', 'Top 6-10', 'Top 11+ (长尾)'],
    var_name='商品梯队', value_name='份额'
)

fig_stack = px.bar(
    top20_melted, x='份额', y='category_name', color='商品梯队', orientation='h',
    color_discrete_sequence=['#E74C3C', '#F39C12', '#3498DB', '#BDC3C7'],
    labels={'份额': '金额占比 (%)', 'category_name': '品类'}
)
fig_stack.update_layout(
    template="plotly_white", barmode='stack',
    xaxis_title="累计金额占比 (%)", yaxis_title="", height=650, legend_title="商品梯队"
)
st.plotly_chart(fig_stack, use_container_width=True)
st.caption("Top 1 占比较高说明该品类金额越集中于单一商品；Top 11+ 占比较高说明排名靠后的商品贡献了更多金额。")
st.divider()


# 图三：战略四象限矩阵

st.subheader("03 | 品类市场覆盖与价格定位")
st.markdown(
    "此矩阵根据订单渗透率和平均商品价格对品类进行比较。气泡大小代表品类总金额。中位数线将品类分为四组，以便进行描述性比较。")

matrix_data = pd.merge(
    df_pen[['category_name', 'order_penetration_rate']],
    df_sales[['category_name', 'avg_item_price', 'total_revenue']],
    on='category_name', how='inner'
)
matrix_data = matrix_data.dropna(subset=['order_penetration_rate', 'avg_item_price', 'total_revenue'])
if matrix_data.empty:
    st.warning("没有可用于绘制品类战略矩阵的数据。")
    st.stop()

med_pen = matrix_data['order_penetration_rate'].median()
med_price = matrix_data['avg_item_price'].median()

fig_matrix = px.scatter(
    matrix_data, x='order_penetration_rate', y='avg_item_price', size='total_revenue',
    color='order_penetration_rate', color_continuous_scale='Viridis', hover_name='category_name',
    labels={'order_penetration_rate': '订单渗透率 (%) -> 市场广度', 'avg_item_price': '平均商品价格 (BRL) -> 价值深度',
            'total_revenue': '总金额 (BRL)'},
    size_max=40, opacity=0.8
)

fig_matrix.add_vline(x=med_pen, line_dash="dash", line_color="gray", opacity=0.6)
fig_matrix.add_hline(y=med_price, line_dash="dash", line_color="gray", opacity=0.6)

fig_matrix.add_annotation(x=matrix_data['order_penetration_rate'].max(), y=matrix_data['avg_item_price'].max(),
                          text="高渗透率 · 高价格", showarrow=False, font=dict(color="green", size=12), xanchor="right")
fig_matrix.add_annotation(x=matrix_data['order_penetration_rate'].max(), y=matrix_data['avg_item_price'].min(),
                          text="高渗透率 · 低价格", showarrow=False, font=dict(color="blue", size=12), xanchor="right")
fig_matrix.add_annotation(x=matrix_data['order_penetration_rate'].min(), y=matrix_data['avg_item_price'].max(),
                          text="低渗透率 · 高价格", showarrow=False, font=dict(color="purple", size=12), xanchor="left")
fig_matrix.add_annotation(x=matrix_data['order_penetration_rate'].min(), y=matrix_data['avg_item_price'].min(),
                          text="低渗透率 · 低价格", showarrow=False, font=dict(color="gray", size=12), xanchor="left")

fig_matrix.update_layout(template="plotly_white", height=650, coloraxis_showscale=False)
st.plotly_chart(fig_matrix, use_container_width=True)
st.caption(
    "虚线分别表示品类订单渗透率和平均商品价格的中位数。气泡大小代表品类总金额。该矩阵用于比较品类的市场覆盖与价格特征，不代表利润水平或品类淘汰建议。")


# 核心发现与业务启示

st.divider()
st.subheader("核心发现与业务启示 (Key Findings & Business Implications)")
st.markdown("""
**核心发现：**
* 前 10 名品类贡献了总计 **62.43%** 的商品金额，表明平台金额集中在相对较小的一组品类中。
* 健康与美容 是最大的金额贡献者，而床品与卫浴 的订单渗透率最高。
* 手表与礼品 的平均商品价格较高，这解释了为何其金额排名高于其订单渗透率排名。
* 各品类的金额集中度差异很大：一些品类严重依赖少数商品，而另一些品类的金额结构则更为分散。

**业务启示：**
* 优先监控主要创收品类，因为这些品类的表现变化可能会对平台总金额产生实质性影响。
* 在评估品类表现时，应结合商品结构和金额集中度进行综合考量。
* 在比较品类定位时，应同时考虑订单覆盖率和平均商品价格，而不是仅仅依赖金额排名。
""")

st.divider()
st.caption("Olist 电商数据分析项目 | 商品品类深度分析")