# src/app/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, JSON, UniqueConstraint
from sqlalchemy.orm import relationship  # 导入 relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

# Prompt 和 Tag 的多对多关联表
prompt_tag_association = Table('prompt_tag_association', Base.metadata,
    Column('prompt_id', Integer, ForeignKey('prompts.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

# Prompt 版本模型
class PromptVersion(Base):
    """
    存储 Prompt 的历史版本快照
    """
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    version_number = Column(Integer, nullable=False) # 版本号，如 1, 2, 3...
    
    # 快照数据
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    # (可选) 可以添加 commit_message 字段

    prompt = relationship("Prompt", back_populates="versions")

    def __repr__(self):
        return f"<PromptVersion(prompt_id={self.prompt_id}, v={self.version_number})>"

# 评分模型
class Rating(Base):
    __tablename__ = "ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    # 频繁用于 group by prompt_id
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False) # 例如：1 到 5 分
    created_at = Column(DateTime, default=datetime.utcnow)

    # 定义一个复合唯一约束
    __table_args__ = (
        UniqueConstraint('user_id', 'prompt_id', name='_user_prompt_uc'),
    )

    prompt = relationship("Prompt", back_populates="ratings")
    user = relationship("User")

    def __repr__(self):
        return f"<Rating(id={self.id}, prompt_id={self.prompt_id}, score={self.score})>"

class Tag(Base):
    """
    标签数据模型
    """
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)

    # 建立与 Prompt 的多对多关系
    prompts = relationship(
        "Prompt",
        secondary=prompt_tag_association,
        back_populates="tags"
    )

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}')>"

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

    # 外键，关联到 users 表的 id 字段
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # 建议：显式添加 index=True，虽然有些数据库会自动对外键建索引，但显式更好
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True) 

    # 建立与 User 模型的关系
    # 'owner' 是一个虚拟字段，可以让我们通过 prompt.owner 访问创建者 User 对象
    owner = relationship("User", back_populates="prompts")

    # 与 Tag 的多对多关系
    tags = relationship(
        "Tag",
        secondary=prompt_tag_association,
        back_populates="prompts"
    )

    owner = relationship("User", back_populates="prompts")

    executions = relationship("PromptExecution", back_populates="prompt", cascade="all, delete-orphan")

    ratings = relationship("Rating", back_populates="prompt", cascade="all, delete-orphan")
    
    versions = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan", order_by="desc(PromptVersion.version_number)")
    def __repr__(self):
        return f"<Prompt(id={self.id}, title='{self.title}', category='{self.category}')>"
    
# Prompt 执行历史模型
class PromptExecution(Base):
    """
    记录每一次 Prompt 执行的历史
    """
    __tablename__ = "prompt_executions"

    id = Column(Integer, primary_key=True, index=True)
    
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    request_data = Column(JSON, nullable=True)  # 存储用于变量替换的字典
    response_text = Column(Text, nullable=True) # 存储 LLM 返回的文本
    token_usage = Column(JSON, nullable=True) # 存储 token 使用情况，例如 {"prompt_tokens": 10, "completion_tokens": 20}
    
    error_message = Column(Text, nullable=True) # 如果执行出错，记录错误信息

    created_at = Column(DateTime, default=datetime.utcnow)

    # 建立关系
    prompt = relationship("Prompt", back_populates="executions")
    user = relationship("User") # 简单关系，不需要反向填充

    def __repr__(self):
        return f"<PromptExecution(id={self.id}, prompt_id={self.prompt_id})>"
