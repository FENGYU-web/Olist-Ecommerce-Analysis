import streamlit as st

st.title("🚀 Olist 巴西电商数据智能中枢")
st.markdown("### Olist E-Commerce Analytics Dashboard")
st.caption("基于 Olist 平台真实交易数据的全链路商业洞察")

st.divider()

st.markdown("""
### 🎯 业务背景 (Business Background)
Olist 是巴西最大的电子商务平台之一。本看板基于其公开的交易数据集，涵盖了从订单生成、支付、物流配送到客户评价的全生命周期数据。
本项目旨在通过多维度的数据分析，**评估平台整体运营健康状况**，并为物流优化、客户关系管理和商品战略提供数据驱动的决策支持。
""")

st.markdown("""
### 🧭 模块导航 (Module Navigation)
请点击左侧侧边栏进行探索，本看板包含以下五个核心分析模块：
*   **🌍 全盘履约概览**：监控平台整体订单时效与各州物流表现。
*   **🚚 物流与评价追踪**：探究配送延迟对客户评分的关联，以及客户的评价响应行为。
*   **👥 客户价值分析**：基于 RFM 模型进行客户分层，识别高价值与易流失客户。
*   **📦 卖家经营表现**：分析卖家收入集中度，探究卖家规模与履约质量的关系。
*   **🛍️ 商品品类战略**：洞察品类收入结构、商品集中度与市场覆盖率。
""")

st.divider()

st.markdown("### 🛠️ 技术栈 (Tech Stack)")
col1, col2, col3, col4 = st.columns(4)
col1.info("**数据库**\n\nMySQL\n\n(复杂 SQL / 窗口函数)")
col2.info("**数据处理**\n\nPython / Pandas\n\n(数据清洗与聚合)")
col3.info("**可视化**\n\nPlotly\n\n(交互式高级图表)")
col4.info("**前端框架**\n\nStreamlit\n\n(多页面数据大屏)")