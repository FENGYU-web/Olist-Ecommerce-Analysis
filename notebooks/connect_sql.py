from sqlalchemy import create_engine
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_NAME

# 动态拼接连接字符串
engine = create_engine(
    f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}?charset=utf8'
)

with engine.connect() as conn:
    print("MySQL connection successful!")