# src/app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PromptBase(BaseModel):
    """提示词基础模式"""
    title: str = Field(..., min_length=1, max_length=200, description="提示词标题")
    content: str = Field(..., min_length=1, description="提示词内容")
    category: Optional[str] = Field(None, max_length=100, description="提示词分类")


class PromptCreate(PromptBase):
    """创建提示词时的数据模式"""
    pass


class PromptUpdate(BaseModel):
    """更新提示词时的数据模式（所有字段可选）"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="新的 Prompt 标题")
    content: Optional[str] = Field(None, min_length=1, description="新的 Prompt 内容")
    category: Optional[str] = Field(None, max_length=50, description="新的 Prompt 分类")


class PromptResponse(PromptBase):
    """返回提示词数据时的模式"""
    id: int
    usage_count: int
    created_at: datetime
    updated_at: datetime

    # Pydantic V2 的配置项
    class Config:
        # from_attributes = True 告诉 Pydantic 模型可以从 ORM 对象（数据库模型实例）中读取数据。
        # 这样就可以直接把 SQLAlchemy 的 Prompt 对象传给 PromptResponse 来创建响应。
        from_attributes = True  # 允许从 ORM 模型创建


class PromptList(BaseModel):
    """提示词列表响应"""
    total: int
    prompts: list[PromptResponse]
