import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import spearmanr, kruskal
from pathlib import Path


# 1. 页面设置与业务背景

st.title("📦 卖家经营表现看板")

st.markdown("""
### 业务目标 (Business Objective)
分析平台卖家的收入集中度与履约表现。旨在识别核心收入贡献者，并探究卖家订单规模与物流延迟率之间是否存在关联。

### 核心发现 (Key Findings)
* 头部 1% 的卖家贡献了 25.93% 的平台卖家总收入。
* 头部 20% 的卖家贡献了 82.29% 的收入（典型的二八定律）。
* 不同规模卖家的配送延迟率相对接近。
""")
st.divider()


# 2. 数据加载与缓存

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

@st.cache_data
def load_performance_data():
    return pd.read_csv(DATA_DIR / 'seller_performance.csv')

@st.cache_data
def load_ranking_data():
    df = pd.read_csv(DATA_DIR / 'seller_revenue_ranking.csv')
    return df.sort_values("revenue_rank")

try:
    seller_all = load_performance_data().copy()
    df_ranking = load_ranking_data().copy()
except FileNotFoundError as e:
    st.error(f"找不到数据文件：{e.filename}。请确保 CSV 文件在 data/processed 目录下。")
    st.stop()


# 3. 侧边栏：交互过滤器

st.sidebar.header("⚙️ 数据筛选器")
min_orders = st.sidebar.slider("选择最小已送达订单量", min_value=20, max_value=100, value=20, step=1)
seller = seller_all[seller_all['delivered_orders'] >= min_orders].copy()

size_colors = {"Small": "#95A5A6", "Medium": "#F39C12", "Large": "#3498DB", "Top": "#16A085"}
group_colors = {"1-5": "#E74C3C", "6-10": "#E67E22", "11-20": "#F1C40F", "21-50": "#2ECC71", "51-100": "#3498DB", "100+": "#9B59B6"}

st.divider()


# 图一：卖家订单量分布 

st.subheader("01 | 卖家订单量分布")
st.caption(f"基于全平台 {len(seller_all):,} 个有有效送达订单的卖家。")

bins = [0, 5, 10, 20, 50, 100, float('inf')]
labels = ['1-5', '6-10', '11-20', '21-50', '51-100', '100+']
seller_all['order_group'] = pd.cut(seller_all['delivered_orders'], bins=bins, labels=labels)

order_distribution = seller_all.groupby('order_group', observed=False).size().reset_index(name='seller_count')
order_distribution['percentage'] = order_distribution['seller_count'] / len(seller_all) * 100

fig_dist = px.bar(
    order_distribution, x='order_group', y='seller_count', text='percentage',
    color='order_group', color_discrete_map=group_colors,
    labels={'order_group': '已送达订单量', 'seller_count': '卖家数量', 'percentage': '占比 (%)'} 
)
fig_dist.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
fig_dist.update_layout(template="plotly_white", height=450, showlegend=False)
st.plotly_chart(fig_dist, use_container_width=True)
st.divider()


# 图二：Pareto 图

st.subheader("02 | 卖家收入集中度 - 帕累托分析")
st.caption(f"展示全平台 {len(df_ranking):,} 个卖家的收入集中情况（不受侧边栏筛选影响）。")

if df_ranking["cumulative_revenue_share"].max() <= 1:
    df_ranking["cumulative_revenue_share"] *= 100
if df_ranking["cumulative_revenue_share"].max() > 100.01:
    st.error("累计收入占比超过 100%，请检查数据源。")
    st.stop()

fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
fig_pareto.add_trace(go.Bar(x=df_ranking["revenue_rank"], y=df_ranking["total_revenue"], name="单卖家收入", marker_color="#5DADE2", opacity=0.8), secondary_y=False)
fig_pareto.add_trace(go.Scatter(x=df_ranking["revenue_rank"], y=df_ranking["cumulative_revenue_share"], name="累计收入占比 (%)", mode='lines', line=dict(color="#E74C3C", width=2.5)), secondary_y=True)
fig_pareto.add_hline(y=80, line_dash="dash", line_color="#7F8C8D", secondary_y=True)

hit_80 = df_ranking.loc[df_ranking["cumulative_revenue_share"] >= 80]
if not hit_80.empty:
    hit_80_rank = int(hit_80.iloc[0]["revenue_rank"])
    fig_pareto.add_annotation(
        x=hit_80_rank, y=80, text=f'80% 收入由前 {hit_80_rank} 名卖家贡献',
        showarrow=True, arrowhead=2, arrowcolor="#2C3E50", ax=40, ay=40,
        font=dict(size=12, color="#2C3E50", weight="bold"),
        bgcolor="rgba(255, 255, 255, 0.8)", bordercolor="#2C3E50", borderwidth=1, borderpad=4, yref="y2"
    )

fig_pareto.update_layout(template="plotly_white", height=600, legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), margin=dict(t=50, b=50, l=50, r=50))
fig_pareto.update_xaxes(title_text="卖家收入排名", range=[1, len(df_ranking)])
fig_pareto.update_yaxes(title_text="卖家收入 (BRL)", secondary_y=False, tickfont=dict(color="#5DADE2"), title_font=dict(color="#5DADE2"))
fig_pareto.update_yaxes(title_text="累计收入占比 (%)", secondary_y=True, tickfont=dict(color="#E74C3C"), title_font=dict(color="#E74C3C"))
st.plotly_chart(fig_pareto, use_container_width=True)
st.divider()


# 数据拆分与图三：卖家履约表现气泡图 

plot_data = seller.copy()
plot_data['seller_size'] = pd.cut(plot_data['delivered_orders'], bins=[0, 50, 100, 500, float('inf')], labels=['Small', 'Medium', 'Large', 'Top'])
bubble_data = plot_data.dropna(subset=['delayed_rate', 'total_product_revenue'])
fulfillment_data = plot_data.dropna(subset=['delayed_rate'])

st.subheader("03 | 卖家规模与配送延迟率关系")
st.caption(f"基于订单量 >= {min_orders} 的 {len(seller):,} 个卖家。")

fig_bubble = px.scatter(
    bubble_data, x='delivered_orders', y='delayed_rate', size='total_product_revenue',
    color='seller_size', color_discrete_map=size_colors, hover_name='seller_id',
    hover_data={'seller_city': True, 'seller_state': True, 'delivered_orders': True, 'delayed_rate': ':.2f', 'avg_delivery_days': ':.1f', 'total_product_revenue': ':.2f'},
    log_x=True, size_max=35, opacity=0.7, title='卖家规模 vs 配送延迟率',
    labels={
        'delivered_orders': '已送达订单量 (对数轴)',
        'delayed_rate': '延迟率 (%)',
        'seller_size': '卖家规模',
        'total_product_revenue': '商品总收入 (BRL)',
        'seller_city': '卖家城市', 
        'seller_state': '卖家州', 
        'avg_delivery_days': '平均配送天数', 
        'seller_id': '卖家ID' 
    }
)

median_delay = fulfillment_data['delayed_rate'].median()
fig_bubble.add_hline(y=median_delay, line_dash='dash', line_color='gray', annotation_text=f'延迟率中位数: {median_delay:.2f}%')
fig_bubble.update_layout(template='plotly_white', title_x=0.5, height=650, legend_title='卖家规模')
st.plotly_chart(fig_bubble, use_container_width=True)
st.caption(f"气泡图展示 {len(bubble_data):,} 家具有有效收入和延迟率数据的卖家；箱线图和统计检验使用 {len(fulfillment_data):,} 家具有有效延迟率数据的卖家。")
st.divider()


# 图四：分组箱线图

st.subheader("04 | 不同规模卖家的延迟率分布")

fig_box = px.box(
    fulfillment_data, x='seller_size', y='delayed_rate', color='seller_size',
    color_discrete_map=size_colors, points='outliers',
    category_orders={'seller_size': ['Small', 'Medium', 'Large', 'Top']},
    title='不同规模卖家的延迟率分布',
    labels={'seller_size': '卖家规模', 'delayed_rate': '延迟率 (%)'}
)
fig_box.update_layout(template='plotly_white', title_x=0.5, height=550, showlegend=False)
st.plotly_chart(fig_box, use_container_width=True)
st.divider()


# 统计检验

st.subheader("05 | 统计学检验结论：规模会影响履约吗")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📈 检验一：单量与延迟率的相关性")
    st.caption("使用 Spearman 秩相关检验，探究卖家单量增加是否会导致延迟率单调上升/下降。")

    spearman_data = fulfillment_data[['delivered_orders', 'delayed_rate']].dropna()

    if len(spearman_data) >= 2:
        corr, p_value = spearmanr(spearman_data['delivered_orders'], spearman_data['delayed_rate'])

        if pd.notna(corr) and pd.notna(p_value):
            st.write(f"**有效样本量:** `{len(spearman_data):,}` 家卖家")
            st.write(f"**相关系数 (ρ):** `{corr:.4f}` | **P 值:** `{p_value:.6f}`")

            if p_value < 0.05:
                if abs(corr) < 0.1:
                    st.warning(f"""
                    **业务解读：** 虽然在统计学上“显著”（p<0.05），但相关系数仅为 {corr:.2f}。
                    这说明单量与延迟率之间**不存在实质性的业务关联**。单纯依靠扩大卖家规模，并不能解决物流延误问题，也不能认为单量大就一定会导致延迟。
                    """)
                else:
                    direction = "正相关" if corr > 0 else "负相关"
                    st.success(f"""
                    **业务解读：** 存在明显的{direction}关系（ρ={corr:.2f}）。
                    说明卖家规模与履约质量存在紧密关联，需进一步排查{direction}背后的具体原因。
                    """)
            else:
                st.info("**业务解读：** 未发现单量与延迟率之间有统计学意义的关联。")
        else:
            st.warning("数据无法计算有效的 Spearman 相关系数。")
    else:
        st.warning("有效样本不足，无法进行检验。")

with col2:
    st.markdown("#### ⚖️ 检验二：不同规模组的延迟率差异")
    st.caption("使用 Kruskal-Wallis H 检验，探究 Small/Medium/Large/Top 四个群体的延迟率分布是否不同。")

    small = fulfillment_data.loc[fulfillment_data['seller_size'] == 'Small', 'delayed_rate'].dropna()
    medium = fulfillment_data.loc[fulfillment_data['seller_size'] == 'Medium', 'delayed_rate'].dropna()
    large = fulfillment_data.loc[fulfillment_data['seller_size'] == 'Large', 'delayed_rate'].dropna()
    top = fulfillment_data.loc[fulfillment_data['seller_size'] == 'Top', 'delayed_rate'].dropna()
    groups = [small, medium, large, top]

    if all(len(g) > 0 for g in groups):
        stat, kw_p_value = kruskal(*groups)
        st.write(f"**H 统计量:** `{stat:.4f}` | **P 值:** `{kw_p_value:.6f}`")

        if kw_p_value < 0.05:
            st.success("""
            **业务解读：** 四个不同规模的卖家群体，在物流延迟率上存在显著的统计学差异。
            这意味着不同规模的卖家确实需要采用差异化的物流管理策略。
            """)
        else:
            st.info("""
            **业务解读：** 四个群体的延迟率没有显著差异（p>0.05）。
            **通俗来说：** 无论是头部卖家还是长尾卖家，物流延误情况其实“半斤八两”。
            平台整体的物流延误问题，并不是因为某类规模的卖家特别拉胯，而可能是受制于承运商效率、地理距离（如发往偏远州）等共性因素。
            """)
    else:
        st.warning("部分卖家规模组没有有效样本，无法进行检验。")

# 总结论
st.divider()
st.markdown("""
### 🎯 综合业务结论 (Takeaway)
**卖家规模大小，并不是决定物流延迟的核心因素。**
因此，运营团队在做物流时效优化时，不能简单地把考核指标压给“大卖家”或“小卖家”，而应该把精力放在**物流线路优化、承运商更换、以及收货地距离等更底层的因素上**。
""")

st.divider()
st.caption("Olist 电商数据分析项目 | 卖家经营表现分析")