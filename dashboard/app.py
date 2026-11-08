import streamlit as st
from pathlib import Path

# 1. 全局页面配置
st.set_page_config(
    page_title="Olist 数据中枢",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 获取 dashboard 文件夹路径
BASE_DIR = Path(__file__).resolve().parent

# 3. 侧边栏 Logo/介绍
st.sidebar.markdown("""
# 🚀 **Olist 数据中枢**
*巴西电商全链路分析*
---
""")

# 4. 定义完全并列的页面导航
# 使用列表结构，所有页面处于同一层级，首页设为默认
pages = [
    st.Page(str(BASE_DIR / "Home.py"), title="项目首页 (Home)", icon="🏠", default=True),
    st.Page(str(BASE_DIR / "overview_app.py"), title="全盘履约概览", icon="🌍"),
    st.Page(str(BASE_DIR / "delivery_app.py"), title="物流与评价追踪", icon="🚚"),
    st.Page(str(BASE_DIR / "rfm_app.py"), title="客户价值分析", icon="👥"),
    st.Page(str(BASE_DIR / "seller_app.py"), title="卖家经营表现", icon="📦"),
    st.Page(str(BASE_DIR / "category_app.py"), title="商品品类战略", icon="🛍️"),
]

# 5. 启动导航 & 运行
pg = st.navigation(pages)
pg.run()