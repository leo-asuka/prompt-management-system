# src/app/schemas.py
from pydantic import BaseModel, Field, Json
from typing import Optional, List, Dict, Any
from datetime import datetime

# ==================== Tag Schemas ====================

class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="标签名称")

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: int

    class Config:
        from_attributes = True

# ==================== User Schemas ====================

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="用户密码")

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ==================== Prompt Schemas ====================

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


# 在返回 Prompt 信息时，也一并返回创建者的基本信息
class PromptResponse(PromptBase):
    """返回提示词数据时的模式"""
    id: int
    usage_count: int
    created_at: datetime
    updated_at: datetime
    owner: UserResponse  # 嵌套 UserResponse Schema
    # --- 新增：在返回 Prompt 时，包含其所有标签 ---
    tags: List[TagResponse] = []

    # Pydantic V2 的配置项
    class Config:
        # from_attributes = True 告诉 Pydantic 模型可以从 ORM 对象（数据库模型实例）中读取数据。
        # 这样就可以直接把 SQLAlchemy 的 Prompt 对象传给 PromptResponse 来创建响应。
        from_attributes = True  # 允许从 ORM 模型创建


class PromptList(BaseModel):
    """提示词列表响应"""
    total: int
    prompts: list[PromptResponse]

# Prompt 执行相关的 Schemas

class PromptExecuteRequest(BaseModel):
    """
    执行 Prompt 时的请求体
    variables 是一个字典，用于替换 Prompt 内容中的模板变量
    """
    variables: Dict[str, Any] = Field({}, description="用于替换提示词模板中变量的键值对")

class PromptExecutionResponse(BaseModel):
    """
    返回 Prompt 执行历史的 Schema
    """
    id: int
    prompt_id: int
    user_id: int
    request_data: Optional[Dict[str, Any]] = None
    response_text: Optional[str] = None

    # 修改这一行
    # 从: token_usage: Optional[Dict[str, int]] = None
    token_usage: Optional[Dict[str, Any]] = None # 或者 Optional[dict]
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True