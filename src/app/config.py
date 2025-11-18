from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    使用 Pydantic 管理环境变量
    SettingsConfigDict 会自动查找 .env 文件
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # PostgreSQL 数据库配置
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    @property
    def database_url(self) -> str:
        """
        生成 SQLAlchemy 兼容的数据库连接字符串
        """
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


@lru_cache()  # 缓存配置实例，避免重复读取.env
def get_settings() -> Settings:
    return Settings()


# 实例化配置
settings = get_settings()
