import pandas as pd
from pathlib import Path
from sqlalchemy import text

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"

files = list(DATA_DIR.glob("*.csv"))

for file in files:
    df = pd.read_csv(file)

    print("=" * 50)
    print("文件:", file.name)
    print("行数:", len(df))
    print("列数:", len(df.columns))
    print(df.head(3))
    print(df.info())


TABLE_CONFIG = {

    "customers": {
        "file": "olist_customers_dataset.csv",
        "columns": [
            "customer_id",
            "customer_unique_id",
            "customer_city",
            "customer_state"
        ],
        "id_columns": [
            "customer_id",
            "customer_unique_id"
        ],
        "date_columns": [],
        "numeric_columns": []
    },

    "sellers": {
        "file": "olist_sellers_dataset.csv",
        "columns": [
            "seller_id",
            "seller_city",
            "seller_state"
        ],
        "id_columns": [
            "seller_id"
        ],
        "date_columns": [],
        "numeric_columns": []
    },

    "products": {
        "file": "olist_products_dataset.csv",
        "columns": [
            "product_id",
            "product_category_name",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm"
        ],
        "id_columns": [
            "product_id"
        ],
        "date_columns": [],
        "numeric_columns": [
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm"
        ]
    },

    "category_translation": {
        "file": "product_category_name_translation.csv",
        "columns": [
            "product_category_name",
            "product_category_name_english"
        ],
        "id_columns": [],
        "date_columns": [],
        "numeric_columns": []
    },

    "orders": {
        "file": "olist_orders_dataset.csv",
        "columns": [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date"
        ],
        "id_columns": [
            "order_id",
            "customer_id"
        ],
        "date_columns": [
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date"
        ],
        "numeric_columns": []
    },

    "order_items": {
        "file": "olist_order_items_dataset.csv",
        "columns": [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value"
        ],
        "id_columns": [
            "order_id",
            "product_id",
            "seller_id"
        ],
        "date_columns": [
            "shipping_limit_date"
        ],
        "numeric_columns": [
            "order_item_id",
            "price",
            "freight_value"
        ]
    },

    "order_payments": {
        "file": "olist_order_payments_dataset.csv",
        "columns": [
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value"
        ],
        "id_columns": [
            "order_id"
        ],
        "date_columns": [],
        "numeric_columns": [
            "payment_sequential",
            "payment_installments",
            "payment_value"
        ]
    },

    "order_reviews": {
        "file": "olist_order_reviews_dataset.csv",
        "columns": [
            "review_id",
            "order_id",
            "review_score",
            "review_creation_date",
            "review_answer_timestamp"
        ],
        "id_columns": [
            "review_id",
            "order_id"
        ],
        "date_columns": [
            "review_creation_date",
            "review_answer_timestamp"
        ],
        "numeric_columns": [
            "review_score"
        ]
    }
}

def load_csv(table_name, config):

    file_path = DATA_DIR / config["file"]

    print(f"\n正在读取：{config['file']}")


    df = pd.read_csv(
        file_path,
        usecols=config["columns"],
        dtype={col: "string" for col in config["id_columns"]},
        low_memory=False
            )

    for col in config["date_columns"]:
        df[col] = pd.to_datetime(
            df[col],
            errors="coerce"
        )


    for col in config["numeric_columns"]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"

        )

    print(f"读取完成：{len(df):,} 行，{len(df.columns)} 列")

    return df


def import_table(table_name, config):

    df = load_csv(table_name, config)

    print(f"正在导入 MySQL 表：{table_name}")


    df.to_sql(
        name=table_name,
        con=engine,
        if_exists="append",
        index=False,
        chunksize=500,
        method="multi"
    )

    print(f"导入成功：{table_name}")


# 4. 检查数据库连接

from connect_sql import engine

def test_connection():

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT DATABASE()")
        )

        print("数据库连接成功：", result.scalar())


def main():

    test_connection()

    # 先导入被其他表引用的父表
    import_order = [
        "customers",
        "sellers",
        "products",
        "category_translation",

        # 再导入订单主表
        "orders",

        # 最后导入订单关联表
        "order_items",
        "order_payments",
        "order_reviews"
    ]

    for table_name in import_order:

        config = TABLE_CONFIG[table_name]

        import_table(table_name, config)

    print("\n所有数据导入完成！")


if __name__ == "__main__":
    main()