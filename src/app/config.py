# src/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    使用 Pydantic 管理环境变量，这个类会自动读取环境变量，并根据类型注解进行验证和转换。
    SettingsConfigDict 会自动查找 .env 文件
    """
    # model_config 指向一个配置字典，告诉 Pydantic 如何加载设置。
    # env_file='.env' 指定了从哪个文件加载环境变量。
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # PostgreSQL 数据库配置
    # Pydantic 会自动查找并加载名为 POSTGRES_USER, POSTGRES_PASSWORD等的环境变量。
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    # OpenAI API Key
    OPENAI_API_KEY: str

    # --- 新增 ---
    REDIS_URL: str = "redis://localhost:6379/0" # 默认值，防止本地运行报错

    @property
    def database_url(self) -> str:
        """
        生成 SQLAlchemy 兼容的数据库连接字符串
        """
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


@lru_cache()  # 缓存配置实例，避免重复读取.env
def get_settings() -> Settings:
    """
    这个函数用于创建并返回 Settings 的单例。
    lru_cache 会确保 Settings() 只被调用一次，后续调用会直接返回缓存的结果。
    这避免了在每次需要配置时都重复读取和解析 .env 文件，提高了效率。
    """
    return Settings()


# 创建一个全局可用的 settings 实例，方便在应用各处导入和使用。
settings = get_settings()
