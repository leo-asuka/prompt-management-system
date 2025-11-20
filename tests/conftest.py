# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from src.app.database import get_db
from src.app.models import Base
from src.app.main import app

from unittest.mock import MagicMock

# ==========================================
# 1. 数据库 Fixture (用于单元测试)
# ==========================================

# 使用 SQLite 内存数据库进行快速、独立的单元测试
# check_same_thread=False 允许在多线程中使用 SQLite 连接
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    创建一个全新的数据库会话用于测试。
    每个测试函数执行前创建表，执行后清空表。
    """
    # 创建所有表结构
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # 删除所有表，确保测试隔离
        Base.metadata.drop_all(bind=engine)


# ==========================================
# 2. 集成测试 Fixture (可选，用于 API 测试)
# ==========================================
# 注意：之前的 integration tests (test_all_func.py) 使用的是 requests 直接请求 Docker 端口。
# 这种方式是 "端到端(E2E)" 风格的。
# 为了不破坏你现有的测试，我们这里只提供 DB fixture 用于新的单元测试。


# --- 新增：Mock Redis 缓存模块 ---
# 这会让所有单元测试在调用 cache.get/set 时什么都不做，而不是报错
@pytest.fixture(autouse=True)
def mock_redis_cache(monkeypatch):
    """
    自动 Mock 掉 src.app.cache 模块，防止单元测试尝试连接 Redis。
    """
    # 模拟 cache.py 中的函数
    mock_cache = MagicMock()
    mock_cache.get_prompt_cache.return_value = None  # 模拟缓存未命中
    mock_cache.set_prompt_cache.return_value = None
    mock_cache.delete_prompt_cache.return_value = None

    # 将 src.app.cache 替换为 mock 对象
    monkeypatch.setattr("src.app.crud.cache", mock_cache)


@pytest.fixture
def client_with_db(db_session):
    """
    提供绑定到内存数据库的 FastAPI 客户端。
    """
    client = TestClient(app)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    """
    Limit pytest-anyio to the asyncio backend to keep tests deterministic on Windows.
    """
    return "asyncio"
