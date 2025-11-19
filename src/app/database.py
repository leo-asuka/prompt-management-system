# src/app/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from fastapi import Request
from contextlib import asynccontextmanager
import time

from .config import settings

# 导入数据模型中定义的 Base
from .models import Base

# 数据库引擎和会话工厂
# 将 engine 和 SessionLocal 定义在模块级别，这样 get_db 就可以直接访问它们

# 创建 SQLAlchemy 引擎。引擎是与数据库进行通信的核心接口。
# settings.database_url 应该从环境变量中读取，例如："postgresql://user:password@db:5432/prompt_db"
# engine = create_engine(settings.DATABASE_URL)

# 创建一个 SessionLocal 类（会话工厂）。
# sessionmaker 返回一个类，其实例就是数据库会话（Session）。
# autocommit=False 和 autoflush=False 是推荐的默认设置。事务需要手动提交。
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
        # 可能需要引发异常来停止应用启动
        raise RuntimeError("Could not connect to the database.")

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
def get_db(request: Request):
    """FastAPI 依赖项：每个请求通过 request 获取当前 app 的 SessionLocal。"""
    db = request.app.state.SessionLocal()
    try:
        yield db
    finally:
        db.close()
