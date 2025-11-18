# database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from contextlib import asynccontextmanager
import time

from config import settings

# 在应用启动和关闭时执行的生命周期事件
@asynccontextmanager
async def lifespan(app):
    # --- 应用启动 ---
    # 创建数据库连接引擎
    app.state.engine = create_engine(settings.database_url)

    # 创建Session工厂
    app.state.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app.state.engine)

    # 尝试连接数据库，最多重试5次 (给数据库启动时间)
    max_retries = 5
    retries = 0
    while retries < max_retries:
        try:
            with app.state.engine.connect() as connection:
                print("--- 数据库连接成功 ---")
                break  # 连接成功，跳出循环
        except OperationalError:
            print(f"--- 数据库连接失败，正在重试 ({retries+1}/{max_retries})... ---")
            retries += 1
            time.sleep(3)  # 等待3秒重试

    if retries == max_retries:
        print("--- 无法连接到数据库，应用启动失败 ---")

    # 创建数据库表（如果不存在）
    try:
        from .models import Base
        Base.metadata.create_all(bind=app.state.engine)
        print("--- 数据库表创建成功 ---")
    except Exception as e:
        print(f"--- 数据库表创建失败: {e} ---")

    yield  # 应用在此处运行

    # --- 应用关闭 ---
    app.state.engine.dispose()
    print("--- 数据库连接已关闭 ---")


# 依赖项：获取数据库Session
def get_db(app):
    db = app.state.SessionLocal()
    try:
        yield db
    finally:
        db.close()
