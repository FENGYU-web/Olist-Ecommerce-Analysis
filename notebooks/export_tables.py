import pandas as pd
from pathlib import Path
from connect_sql import engine  

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

DATA_DIR.mkdir(parents=True, exist_ok=True)

tables_to_export = [
    # 模块一
    "overall_delivery_kpi",
    "state_delivery_performance",
    # 模块二
    "delivery_vs_score",
    "delay_gradient",
    "score_vs_delay",
    "response_time_hours",
    "response_time_days",
    "score_vs_response_time",
    # 模块三
    "rfm_scored",
    "customer_rfm",
    # 模块四
    "seller_performance",
    "seller_revenue_ranking",
    # 模块五
    "category_sales_contribution",
    "category_internal_concentration",
    "category_order_penetration"
]

print("开始从 MySQL 导出数据到 CSV...\n")

for table_name in tables_to_export:
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

        file_path = DATA_DIR / f"{table_name}.csv"

        df.to_csv(file_path, index=False, encoding="utf-8-sig")

        print(f"✅ 成功导出: {table_name}.csv (共 {len(df):,} 行)")

    except Exception as e:
        print(f"❌ 导出 {table_name} 失败: {e}")

print("\n🎉 所有表导出完成！你现在可以去 data/processed 文件夹检查了。")