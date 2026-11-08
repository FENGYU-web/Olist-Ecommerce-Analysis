import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path


# 1. 页面设置与业务背景

# st.set_page_config(page_title="全盘履约概览", page_icon="🌍", layout="wide")
st.title("🌍 全平台订单履约概览")

st.markdown("""
### 业务目标 (Business Objective)
监控平台整体订单履约表现，并从州级维度比较配送时效与准时率，识别表现较好和需要重点关注的地区，为后续物流运营优化提供数据依据。
""")
st.divider()


# 2. 动态获取数据

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

@st.cache_data
def load_data():
    df_kpi = pd.read_csv(DATA_DIR / 'overall_delivery_kpi.csv')
    df_state = pd.read_csv(DATA_DIR / 'state_delivery_performance.csv')
    return df_kpi, df_state

try:
    df_kpi, df_state = load_data()
except FileNotFoundError as e:
    st.error(f"找不到数据文件：{e.filename}。请确保 CSV 都在 data/processed 目录下。")
    st.stop()

if df_kpi.empty:
    st.error("KPI 数据为空，请检查 overall_delivery_kpi.csv。")
    st.stop()

kpi = df_kpi.iloc[0]


# 3. 顶部 KPI 指标卡

col1, col2, col3, col4 = st.columns(4)
col1.metric("总有效送达订单", f"{int(kpi['delivered_orders']):,}")
col2.metric("平均配送时长", f"{kpi['avg_delivery_days']:.2f} 天")
col3.metric("准时交付率（目标：95%）", f"{kpi['on_time_rate']:.2f}%")
col4.metric("延迟订单总数", f"{int(kpi['delayed_orders']):,}")

st.divider()


# 4. 侧边栏：数据过滤

st.sidebar.header("⚙️ 州级数据筛选")
min_state_orders = st.sidebar.slider("最低订单量", min_value=1, max_value=5000, value=500, step=100)

state_filtered = df_state[
    df_state['delivered_orders'] >= min_state_orders
].dropna(subset=['on_time_rate', 'avg_delivery_days'])

if state_filtered.empty:
    st.warning("当前筛选条件下没有符合要求的州，请降低最低订单量。")
    st.stop()

med_on_time = state_filtered['on_time_rate'].median()
med_days = state_filtered['avg_delivery_days'].median()


# 5. 核心图表：州级物流履约矩阵

st.subheader("01 | 各州物流履约表现矩阵")
st.caption(f"十字线分别代表当前筛选州的准时率中位数 ({med_on_time:.2f}%) 和平均配送时长中位数 ({med_days:.2f} 天)。气泡大小代表该州的订单量。")

fig_matrix = px.scatter(
    state_filtered, x='on_time_rate', y='avg_delivery_days', size='delivered_orders',
    color='on_time_rate', color_continuous_scale='RdYlGn', hover_name='customer_state',
    hover_data={'delivered_orders': ':,.0f', 'on_time_rate': ':.2f', 'avg_delivery_days': ':.2f'},
    labels={
        'on_time_rate': '准时交付率 (%)',
        'avg_delivery_days': '平均配送天数',
        'delivered_orders': '订单量',
        'customer_state': '州'
    },
    size_max=50, opacity=0.8
)

fig_matrix.add_vline(x=med_on_time, line_dash="dash", line_color="gray", opacity=0.6)
fig_matrix.add_hline(y=med_days, line_dash="dash", line_color="gray", opacity=0.6)

fig_matrix.add_annotation(x=state_filtered['on_time_rate'].max(), y=state_filtered['avg_delivery_days'].min(), text="高准时率、短配送时长", showarrow=False, font=dict(color="green", size=11), xanchor="right", yanchor="bottom")
fig_matrix.add_annotation(x=state_filtered['on_time_rate'].max(), y=state_filtered['avg_delivery_days'].max(), text="高准时率、长配送时长", showarrow=False, font=dict(color="blue", size=11), xanchor="right", yanchor="top")
fig_matrix.add_annotation(x=state_filtered['on_time_rate'].min(), y=state_filtered['avg_delivery_days'].min(), text="低准时率、短配送时长", showarrow=False, font=dict(color="orange", size=11), xanchor="left", yanchor="bottom")
fig_matrix.add_annotation(x=state_filtered['on_time_rate'].min(), y=state_filtered['avg_delivery_days'].max(), text="低准时率、长配送时长", showarrow=False, font=dict(color="red", size=11), xanchor="left", yanchor="top")

fig_matrix.update_layout(template="plotly_white", height=600, coloraxis_showscale=False)
st.plotly_chart(fig_matrix, use_container_width=True)

st.info(f"💡 **洞察**：中位准时率为 {med_on_time:.2f}%，中位配送天数为 {med_days:.2f} 天。右下角（高准时率、短配送时长）是优质区域，左上角（低准时率、长配送时长）是需要重点关注和排查的区域。")
st.divider()


# 6. 双榜对比

st.subheader("02 | 州级物流表现")
st.caption("准时率最低（左）与准时率最高（右）的 10 个州对比。")

col_bottom, col_top = st.columns(2)

with col_bottom:
    bottom_states = state_filtered.sort_values('on_time_rate', ascending=True).head(10)
    fig_bottom = px.bar(
        bottom_states, x='on_time_rate', y='customer_state', orientation='h',
        text='on_time_rate', color='on_time_rate', color_continuous_scale='Reds',
        title="准时率最低 Top 10",
        labels={'on_time_rate': '准时率 (%)', 'customer_state': '州'}
    )
    fig_bottom.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig_bottom.update_layout(template="plotly_white", height=400, coloraxis_showscale=False, yaxis_title="州", xaxis_title="准时率 (%)")
    st.plotly_chart(fig_bottom, use_container_width=True)

with col_top:
    top_states = state_filtered.sort_values('on_time_rate', ascending=False).head(10)
    fig_top = px.bar(
        top_states, x='on_time_rate', y='customer_state', orientation='h',
        text='on_time_rate', color='on_time_rate', color_continuous_scale='Greens',
        title="准时率最高 Top 10",
        labels={'on_time_rate': '准时率 (%)', 'customer_state': '州'}
    )
    fig_top.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig_top.update_layout(template="plotly_white", height=400, coloraxis_showscale=False, yaxis_title="州", xaxis_title="准时率 (%)")
    st.plotly_chart(fig_top, use_container_width=True)

st.divider()


# 7. 数据明细下钻

with st.expander("📊 查看各州底层数据明细"):
    st.dataframe(state_filtered.sort_values('on_time_rate', ascending=True), use_container_width=True, hide_index=True)

st.caption("Olist 电商数据分析项目 | 全盘履约概览")