import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path


# 1. 页面设置

# st.set_page_config(page_title="RFM 客户分析", page_icon="📊", layout="wide")

st.title("📊 RFM 客户价值分群")
st.caption("OLIST E-COMMERCE | 基于 RFM 模型的客户价值分析")

st.info("**口径说明：** 本模块展示的金额代表客户历史消费总额（即 Monetary 值），不代表平台的财务净利润或净收入。")


# 2. 动态获取数据

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

segment_order = ["Champions", "Loyal Customers", "Potential Loyalists", "At Risk", "Hibernating", "Other Customers"]
segment_colors = {
    "Champions": "#16A085", "Loyal Customers": "#3498DB", "Potential Loyalists": "#F39C12",
    "At Risk": "#E74C3C", "Hibernating": "#8E44AD", "Other Customers": "#95A5A6"
}

@st.cache_data
def load_data():
    data = pd.read_csv(DATA_DIR / 'rfm_scored.csv')
    data["customer_segment"] = data["customer_segment"].astype(str)
    return data

try:
    rfm = load_data()
except FileNotFoundError:
    st.error("找不到 rfm_scored.csv，请确保它在 data/processed 文件夹下。")
    st.stop()


# 3. 过滤与数据粒度检查

raw_customer_count = rfm["customer_unique_id"].nunique()
rfm = rfm[rfm["customer_segment"].isin(segment_order)].copy()
valid_customer_count = rfm["customer_unique_id"].nunique()

if raw_customer_count != valid_customer_count:
    st.warning(f"有 {raw_customer_count - valid_customer_count:,} 位客户未进入当前六个有效分群，已从分析中排除。")

if rfm.empty:
    st.error("没有找到有效的 RFM 客户分群数据。")
    st.stop()

if rfm["customer_unique_id"].duplicated().any():
    st.error("RFM 数据存在重复客户记录，请检查数据粒度（应当一位客户一行）。")
    st.stop()


# 4. 计算客户群体统计数据

segment_analysis = (
    rfm.groupby("customer_segment")
    .agg(
        customer_count=("customer_unique_id", "nunique"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        total_revenue=("monetary", "sum")
    )
    .reindex(segment_order)
    .dropna(subset=["customer_count"])
    .reset_index()
)

total_customers = segment_analysis["customer_count"].sum()
total_spend = segment_analysis["total_revenue"].sum() # 内部变量名不动，不影响展示
segment_analysis["customer_percentage"] = (segment_analysis["customer_count"] / total_customers * 100)
segment_analysis["revenue_percentage"] = (segment_analysis["total_revenue"] / total_spend * 100)


# 5. 顶部 KPI

repeat_customers = rfm.loc[rfm["frequency"] > 1, "customer_unique_id"].nunique()
repeat_rate = repeat_customers / total_customers * 100
avg_monetary = rfm["monetary"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("总客户数", f"{total_customers:,}")
col2.metric("复购客户率", f"{repeat_rate:.2f}%")
col3.metric("平均客单消费", f"R$ {avg_monetary:,.2f}")
col4.metric("总消费金额", f"R$ {total_spend:,.0f}")

st.divider()


# 6. 图一：Customer Value Map

st.subheader("01 | 客户价值气泡图")

fig_bubble = px.scatter(
    segment_analysis,
    x="avg_recency", y="avg_monetary", size="customer_count", color="customer_segment",
    size_max=75, color_discrete_map=segment_colors, hover_name="customer_segment",
    hover_data={
        "customer_count": ":,", "customer_percentage": ":.2f",
        "avg_recency": ":.2f", "avg_frequency": ":.2f", "avg_monetary": ":.2f",
        "total_revenue": ":,.2f", "revenue_percentage": ":.2f"
    },
    labels={
        "avg_recency": "平均最近一次消费间隔 (天)",
        "avg_monetary": "平均消费金额 (BRL)",
        "customer_count": "客户数量",
        "customer_segment": "客户分群",
        "customer_percentage": "客户占比 (%)",
        "avg_frequency": "平均购买频次",
        "total_revenue": "总消费金额 (BRL)",
        "revenue_percentage": "消费金额占比 (%)"
    }
)

fig_bubble.update_xaxes(autorange="reversed")
fig_bubble.update_traces(marker=dict(opacity=0.8, line=dict(color="white", width=2)))
fig_bubble.update_layout(template="plotly_white", height=570, legend_title_text="客户分群")

st.plotly_chart(fig_bubble, use_container_width=True)
st.caption("气泡大小代表客户规模。鼠标悬停可查看各分群详细指标。")
st.divider()


# 7. 图二：RFM Radar Chart

st.subheader("02 | RFM 客户特征雷达图")

radar_data = (
    rfm.groupby("customer_segment")[["R_score", "F_score", "M_score"]]
    .mean()
    .reindex(segment_order)
)

fig_radar = go.Figure()
radar_categories = ["最近消费 (R)", "购买频次 (F)", "消费金额 (M)"]

for segment in radar_data.dropna().index:
    values = radar_data.loc[segment].tolist()
    fig_radar.add_trace(
        go.Scatterpolar(
            r=values + [values[0]], theta=radar_categories + [radar_categories[0]],
            fill="toself", name=segment, line=dict(color=segment_colors[segment]), opacity=0.8
        )
    )

fig_radar.update_layout(
    template="plotly_white", height=600,
    polar=dict(radialaxis=dict(visible=True, range=[0, 5], tickvals=[1, 2, 3, 4, 5])),
    legend=dict(orientation="h", yanchor="bottom", y=-0.2)
)

st.plotly_chart(fig_radar, use_container_width=True)
st.caption("评分越高代表客户特征越优质；R 评分为反向打分，得分越高代表最近购买时间越近。")
st.divider()


# 8. 图三：Customer Share vs Revenue Share

st.subheader("03 | 客户占比 vs 消费金额占比")

dumbbell_data = segment_analysis.sort_values("customer_percentage").reset_index(drop=True)
fig_dumbbell = go.Figure()

for i, row in dumbbell_data.iterrows():
    fig_dumbbell.add_trace(
        go.Scatter(
            x=[row["customer_percentage"], row["revenue_percentage"]],
            y=[row["customer_segment"]] * 2, mode="lines",
            line=dict(color="#B8B8B8", width=3), showlegend=False, hoverinfo="skip"
        )
    )

fig_dumbbell.add_trace(
    go.Scatter(
        x=dumbbell_data["customer_percentage"], y=dumbbell_data["customer_segment"],
        mode="markers", name="客户占比", marker=dict(color="#3498DB", size=13),
        hovertemplate="%{y}<br>客户占比: %{x:.2f}%<extra></extra>"
    )
)

fig_dumbbell.add_trace(
    go.Scatter(
        x=dumbbell_data["revenue_percentage"], y=dumbbell_data["customer_segment"],
        mode="markers", name="消费金额占比", marker=dict(color="#E67E22", size=13, symbol="diamond"),
        hovertemplate="%{y}<br>消费金额占比: %{x:.2f}%<extra></extra>"
    )
)

fig_dumbbell.update_layout(
    template="plotly_white", height=500,
    xaxis_title="百分比 (%)", yaxis_title="",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0)
)

st.plotly_chart(fig_dumbbell, use_container_width=True)
st.caption("消费金额占比高于客户占比的分群，代表该群体的人均消费价值高于平均水平。")
st.divider()


# 9. 图四：Revenue Contribution

st.subheader("04 | 各分群消费金额贡献")

revenue_data = segment_analysis.sort_values("total_revenue", ascending=True)

fig_revenue = px.bar(
    revenue_data, x="total_revenue", y="customer_segment",
    orientation="h", color="customer_segment", color_discrete_map=segment_colors, text="total_revenue",
    hover_data={"customer_count": ":,", "total_revenue": ":,.2f", "revenue_percentage": ":.2f"},
    labels={
        "total_revenue": "总消费金额 (BRL)",
        "customer_segment": "客户分群",
        "customer_count": "客户数量",
        "revenue_percentage": "消费金额占比 (%)"
    }
)

fig_revenue.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside", showlegend=False)
fig_revenue.update_layout(template="plotly_white", height=480, xaxis_title="总消费金额 (BRL)", yaxis_title="")
st.plotly_chart(fig_revenue, use_container_width=True)


# 10. 客户群体明细表

with st.expander("查看客户分群底层数据明细"):
    display_data = segment_analysis.copy()
    st.dataframe(display_data, use_container_width=True, hide_index=True)

    csv = display_data.to_csv(index=False).encode("utf-8-sig")
    st.download_button("下载分群分析数据 (CSV)", data=csv, file_name="customer_segment_analysis.csv", mime="text/csv")

st.divider()
st.caption("Olist 电商数据分析项目 | 基于 RFM 的客户价值分析")