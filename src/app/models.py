# src/app/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship  # 导入 relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    """
    用户数据模型
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False) # 存储哈希后的密码
    created_at = Column(DateTime, default=datetime.utcnow)

    # 建立与 Prompt 模型的关系
    # 'prompts' 是一个虚拟字段，可以让我们通过 user.prompts 访问该用户的所有 prompts
    # back_populates="owner" 指定了反向关系，在 Prompt 模型中名为 'owner'
    prompts = relationship("Prompt", back_populates="owner")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Prompt(Base):
    """
    Prompt 数据模型 (对应数据库中的 'prompts' 表)
    这个类定义了 'prompts' 表的结构
    """
    # __tablename__ 告诉 SQLAlchemy 这个模型对应数据库中的表名
    __tablename__ = "prompts"

    # 定义表的字段 (列)
    # id: 主键，自增
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # title: Prompt 标题，最大长度 200，非空
    title = Column(String(200), nullable=False, index=True)
    # content: Prompt 内容，Text 类型表示可以存储长文本
    content = Column(Text, nullable=False)
    # category: 分类，可选字段
    category = Column(String(100), nullable=True, index=True)
    # created_at: 创建时间，默认值为当前数据库服务器时间
    usage_count = Column(Integer, default=0)
    # updated_at: 更新时间，默认值为当前时间，并在每次更新记录时自动刷新
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 新增字段：外键，关联到 users 表的 id 字段
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 建立与 User 模型的关系
    # 'owner' 是一个虚拟字段，可以让我们通过 prompt.owner 访问创建者 User 对象
    owner = relationship("User", back_populates="prompts")

    def __repr__(self):
        return f"<Prompt(id={self.id}, title='{self.title}', category='{self.category}')>"
