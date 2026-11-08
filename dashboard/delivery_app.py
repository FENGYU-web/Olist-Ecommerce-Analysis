import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path


# 1. 页面设置与业务背景

# st.set_page_config(page_title="物流与评价", page_icon="🚚", layout="wide")
st.title("🚚 物流时效与客户评价行为分析")

st.markdown("""
### 业务目标 (Business Objective)
分析配送准时性与客户评价之间的关联，评估不同延迟程度下的客户评分差异；
同时研究客户收到评价问卷后的响应时间分布，以及不同评分客户的评价响应行为，
为平台物流服务改善和客户体验管理提供数据依据。
""")
st.divider()


# 2. 动态获取数据

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"


@st.cache_data
def load_data():
    df_status = pd.read_csv(DATA_DIR / 'delivery_vs_score.csv')
    df_gradient = pd.read_csv(DATA_DIR / 'delay_gradient.csv')
    df_score_delay = pd.read_csv(DATA_DIR / 'score_vs_delay.csv')
    df_resp_hours = pd.read_csv(DATA_DIR / 'response_time_hours.csv')
    df_resp_days = pd.read_csv(DATA_DIR / 'response_time_days.csv')
    df_score_resp = pd.read_csv(DATA_DIR / 'score_vs_response_time.csv')
    return df_status, df_gradient, df_score_delay, df_resp_hours, df_resp_days, df_score_resp


try:
    df_status, df_gradient, df_score_delay, df_resp_hours, df_resp_days, df_score_resp = load_data()
except FileNotFoundError as e:
    st.error(f"找不到数据文件：{e.filename}。请确保所有 CSV 都在 data/processed 目录下。")
    st.stop()


# 3. 分页签展示

tab1, tab2 = st.tabs(["📦 物流延迟与评分", "💬 评价响应行为"])


# TAB 1: 物流延迟对评分的影响

with tab1:
    st.subheader("01 | 准时 vs 延迟：评分差异与低评分率")

    required_status = {'On-time', 'Delayed'}
    available_status = set(df_status['delivery_status'].dropna())
    if not required_status.issubset(available_status):
        st.error("准时与延迟订单数据不完整，请检查数据源。")
        st.stop()

    on_time_data = df_status[df_status['delivery_status'] == 'On-time'].iloc[0]
    delayed_data = df_status[df_status['delivery_status'] == 'Delayed'].iloc[0]

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig_gauge_on = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=on_time_data['avg_review_score'],
            title={'text': "准时送达平均分", 'font': {'size': 20}},
            gauge={'axis': {'range': [0, 5]}, 'bar': {'color': "#2ECC71"}},
            delta={'reference': delayed_data['avg_review_score'], 'increasing': {'color': "green"}}
        ))
        fig_gauge_on.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_gauge_on, use_container_width=True)

    with col_g2:
        fig_gauge_delay = go.Figure(go.Indicator(
            mode="gauge+number",
            value=delayed_data['avg_review_score'],
            title={'text': "延迟送达平均分", 'font': {'size': 20}},
            gauge={'axis': {'range': [0, 5]}, 'bar': {'color': "#E74C3C"}}
        ))
        fig_gauge_delay.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_gauge_delay, use_container_width=True)

    st.caption(
        f"样本量说明：准时订单评价数量 {int(on_time_data.get('review_count', 0)):,}，延迟订单评价数量 {int(delayed_data.get('review_count', 0)):,}。")

    st.info(
        f"💡 **核心发现：** 延迟订单的平均评分为 {delayed_data['avg_review_score']:.2f}，明显低于准时订单的 {on_time_data['avg_review_score']:.2f}。"
        f"延迟订单低评分率为 {delayed_data['low_rating_rate']:.2f}%，而准时订单为 {on_time_data['low_rating_rate']:.2f}%。"
        f"两组差异表明，配送延迟与客户负面评价存在明显关联。"
    )

    st.divider()

    st.subheader("02 | 延迟程度与评分的阶梯变化")

    order_gradient = ['On-time', '1-3 days', '4-7 days', 'More than 7 days']
    df_gradient_plot = df_gradient.copy()
    df_gradient_plot['delay_group'] = pd.Categorical(df_gradient_plot['delay_group'], categories=order_gradient,
                                                     ordered=True)
    df_gradient_plot = df_gradient_plot.sort_values('delay_group')

    fig_gradient = go.Figure()
    fig_gradient.add_trace(go.Scatter(
        x=df_gradient_plot['delay_group'], y=df_gradient_plot['avg_review_score'],
        mode='lines+markers+text', text=df_gradient_plot['avg_review_score'], textposition='top center',
        line=dict(color='#8E44AD', width=4, shape='spline'), marker=dict(size=12, color='#8E44AD'),
        fill='tozeroy', fillcolor='rgba(142, 68, 173, 0.2)'
    ))
    fig_gradient.update_layout(
        template='plotly_white', height=400,
        yaxis=dict(range=[0, 5], title='平均评分'),
        xaxis=dict(title='延迟程度')
    )
    st.plotly_chart(fig_gradient, use_container_width=True)
    st.success("💡 **核心发现：** 随着配送延迟程度增加，各组平均评分呈明显下降趋势，其中延迟超过 7 天的订单评分最低。")

    st.divider()

    st.subheader("03 | 不同评分等级对应的订单延迟率")

    df_score_delay_plot = df_score_delay.dropna(subset=['review_score', 'delayed_rate']).copy()
    if not df_score_delay_plot.empty:
        max_delay = df_score_delay_plot['delayed_rate'].max()

        fig_score_delay = go.Figure()
        for i, row in df_score_delay_plot.iterrows():
            fig_score_delay.add_shape(type="line", x0=0, y0=row['review_score'], x1=row['delayed_rate'],
                                      y1=row['review_score'], line=dict(color="gray", width=2))
        fig_score_delay.add_trace(go.Scatter(
            x=df_score_delay_plot['delayed_rate'], y=df_score_delay_plot['review_score'],
            mode='markers+text', text=df_score_delay_plot['delayed_rate'], textposition='middle right',
            marker=dict(color='#E74C3C', size=16), showlegend=False
        ))
        fig_score_delay.update_layout(
            template='plotly_white', height=350,
            xaxis=dict(title='延迟率 (%)', range=[0, max_delay * 1.2]),
            yaxis=dict(title='评价分数', tickvals=[1, 2, 3, 4, 5])
        )
        st.plotly_chart(fig_score_delay, use_container_width=True)
        st.info(
            "💡 **核心发现：** 低评分订单对应的配送延迟率明显较高，其中 1 星评价的订单延迟率最高。这进一步说明配送履约表现与客户满意度密切相关。")
    else:
        st.warning("评分与延迟率数据缺失，无法绘制图表。")


# TAB 2: 评价响应行为分析

with tab2:
    st.subheader("01 | 评价响应时长与低评分率")

    resp_view = st.radio(
        "请选择评价响应时间的基准：",
        ["按问卷发出时间计算 (天)", "按实际收货时间计算 (小时)"],
        horizontal=True
    )

    if resp_view == "按问卷发出时间计算 (天)":
        df_plot = df_resp_days.copy()
        order_resp = ['Same day', '1-3 days', '4-7 days', 'More than 7 days']
        bar_colors = ['#3498DB', '#2ECC71', '#F39C12', '#E74C3C']
    else:
        df_plot = df_resp_hours.copy()
        order_resp = ['Less than 1 day', '1-3 days', '3-7 days', 'More than 7 days']
        bar_colors = ['#3498DB', '#2ECC71', '#F39C12', '#E74C3C']

    if not set(df_plot['response_group'].dropna()).issubset(set(order_resp)):
        st.warning("CSV 中的分组名称与预设不一致，可能导致分类排序异常。")

    df_plot['response_group'] = pd.Categorical(df_plot['response_group'], categories=order_resp, ordered=True)
    df_plot = df_plot.sort_values('response_group')

    fig_resp = px.bar(
        df_plot,
        x='response_group',
        y='low_rating_rate',
        color='response_group',
        color_discrete_sequence=bar_colors,
        text='low_rating_rate',
        labels={
            'response_group': '评价响应时间',
            'low_rating_rate': '低评分率 (%)'
        },
        title='不同评价响应时间组的低评分率'
    )
    fig_resp.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig_resp.update_layout(
        template='plotly_white',
        height=450,
        showlegend=False,
        xaxis_title='评价响应时间',
        yaxis_title='低评分率 (%)'
    )
    st.plotly_chart(fig_resp, use_container_width=True)

    st.info("""
    **💡 核心发现与业务假设：**
    1. **两端偏高现象**：极短时间（如当天/24小时内）和极长时间（7天以上）提交评价的订单，其低评分率均高于中间组。
    2. **合理假设**：极短时间评价通常由极端的体验（特别好或特别差）驱动；而极长时间评价，可能是因为商品在使用几天后暴露出质量问题，或者是被平台的催评机制反复触达才补交的。
    3. **行动建议**：建议运营团队针对“极速差评”排查是否有集中性的物流或错发漏发问题；针对“超长延迟评价”，可结合具体差评内容分析是否为产品耐久度问题。
    """)

    st.divider()

    st.subheader("02 | 不同评分等级的平均评价响应时间")

    df_score_resp_plot = df_score_resp.dropna(subset=['avg_response_days', 'review_score']).copy()

    if not df_score_resp_plot.empty:
        df_score_resp_plot = df_score_resp_plot.sort_values('avg_response_days', ascending=True)

        fig_score_resp = go.Figure()
        fig_score_resp.add_trace(go.Bar(
            x=df_score_resp_plot['avg_response_days'], y=df_score_resp_plot['review_score'].astype(str),
            orientation='h', marker_color='rgba(52, 152, 219, 0.3)', width=0.4, showlegend=False
        ))
        for i, row in df_score_resp_plot.iterrows():
            fig_score_resp.add_shape(type="line", y0=str(row['review_score']), y1=str(row['review_score']), x0=0,
                                     x1=row['avg_response_days'],
                                     line=dict(color="#2C3E50", width=4))

        fig_score_resp.update_layout(
            template='plotly_white', height=350,
            xaxis=dict(title='平均响应天数'),
            yaxis=dict(title='评价分数', type='category')
        )
        st.plotly_chart(fig_score_resp, use_container_width=True)

        st.info("""
        **💡 核心发现与业务假设：**
        1. **差评反馈更迅速**：低评分（1-2星）客户的评价响应时间普遍短于高评分（5星）客户。
        2. **合理假设**：负面体验更容易促使客户主动且快速地采取反馈行动；而满意的客户往往缺乏立即评价的动力，需要依赖系统提醒。
        3. **行动建议**：对于低评分订单，客服部门应尽量在评价提交后的“黄金24小时”内进行跟进与安抚，以挽回客户；同时，可以通过优化激励手段，提升高满意度客户主动评价的意愿。
        """)
    else:
        st.warning("平均响应天数数据缺失，无法绘制图表。")