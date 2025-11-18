from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Prompt(Base):
    """
    提示词模型
    用于存储 LLM 提示词模板
    """
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True, index=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Prompt(id={self.id}, title='{self.title}', category='{self.category}')>"
