# src/app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from .models import Prompt
from .schemas import PromptCreate, PromptUpdate
from typing import List, Optional
from . import models, schemas  # 导入 models 和 schemas
from . import llm_client # 导入 llm_client
import bcrypt

def _hash_password(password: str) -> str:
    """使用 bcrypt 生成一个哈希字符串，兼容当前依赖版本。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ==================== User CRUD ====================

def get_user_by_username(db: Session, username: str):
    """根据用户名查询用户"""
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    """创建新用户，并哈希密码"""
    hashed_password = _hash_password(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# ==================== Tag CRUD (New) ====================

def get_tag(db: Session, tag_id: int):
    """根据 ID 获取标签"""
    return db.query(models.Tag).filter(models.Tag.id == tag_id).first()

def get_tag_by_name(db: Session, name: str):
    """根据名称获取标签"""
    return db.query(models.Tag).filter(models.Tag.name == name).first()

def get_tags(db: Session, skip: int = 0, limit: int = 100):
    """获取标签列表"""
    return db.query(models.Tag).offset(skip).limit(limit).all()

def create_tag(db: Session, tag: schemas.TagCreate):
    """创建新标签"""
    db_tag = models.Tag(name=tag.name)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag

def add_tag_to_prompt(db: Session, db_prompt: models.Prompt, db_tag: models.Tag):
    """为 Prompt 添加一个标签"""
    if db_tag not in db_prompt.tags:
        db_prompt.tags.append(db_tag)
        db.commit()
        db.refresh(db_prompt)
    return db_prompt

def remove_tag_from_prompt(db: Session, db_prompt: models.Prompt, db_tag: models.Tag):
    """从 Prompt 移除一个标签"""
    if db_tag in db_prompt.tags:
        db_prompt.tags.remove(db_tag)
        db.commit()
        db.refresh(db_prompt)
    return db_prompt

# ==================== Prompt CRUD ====================
# 创建 Prompt 时需要知道是哪个用户创建的
def create_prompt(db: Session, prompt: schemas.PromptCreate, user_id: int):
    """
    在数据库中创建一个新的 Prompt 记录。
    :param db: 数据库 Session。
    :param prompt: Pydantic 模型，包含创建所需的数据。
    :return: 创建好的 SQLAlchemy Prompt 模型实例。
    """
    # 将 Pydantic 模型 (prompt) 转换为 SQLAlchemy 模型 (db_prompt)
    db_prompt = Prompt(
        # title=prompt.title,
        # content=prompt.content,
        # category=prompt.category
        **prompt.model_dump(),  # 使用 model_dump 简化代码
        user_id=user_id,
    )
    db.add(db_prompt)  # 将新对象添加到 Session 中（暂存）
    db.commit()      # 将暂存的更改提交到数据库
    db.refresh(db_prompt) # 刷新 db_prompt 对象，以获取数据库生成的值（如 id, created_at）
    return db_prompt

def get_prompts_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """获取指定用户的所有 Prompts"""
    return db.query(models.Prompt).filter(models.Prompt.user_id == user_id).offset(skip).limit(limit).all()

def get_prompts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    tags: Optional[List[str]] = None
):
    """
    从数据库中查询 Prompt 列表，支持分页和按标签筛选。
    如果提供了 tags 列表，则只返回包含所有指定标签的 Prompts。
    """
    query = db.query(models.Prompt)

    if tags:
        # 这个查询逻辑确保返回的 Prompt 必须拥有 *所有* 指定的标签
        for tag_name in tags:
            query = query.filter(models.Prompt.tags.any(name=tag_name))
            
    # 计算总数（在应用分页之前）
    total = query.count()
    
    # 应用分页
    prompts = query.offset(skip).limit(limit).all()
    
    return prompts, total

def get_prompt(db: Session, prompt_id: int):
    """根据 ID 查询单个 Prompt。.first() 表示只返回第一条匹配的记录，如果没有找到则返回 None。"""
    return db.query(Prompt).filter(Prompt.id == prompt_id).first()

def update_prompt(db: Session, db_prompt: models.Prompt, prompt_update: schemas.PromptUpdate):
    """更新一个已存在的 Prompt 记录。这个函数现在直接接收一个 SQLAlchemy 模型实例 (db_prompt)，而不是 prompt_id。"""
    update_data = prompt_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_prompt, field, value)

    db.add(db_prompt)  # 虽然 SQLAlchemy 跟踪了对象，但显式 add 更清晰
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

def delete_prompt(db: Session, db_prompt: models.Prompt):
    """删除一个 Prompt 记录。这个函数现在直接接收一个 SQLAlchemy 模型实例 (db_prompt)。"""
    db.delete(db_prompt)
    db.commit()
    # 删除后不需要返回任何东西
    return None

# ==================== PromptExecution CRUD (New) ====================

def create_prompt_execution(
    db: Session,
    prompt_id: int,
    user_id: int,
    request_data: dict,
    result: llm_client.LLMExecutionResult
) -> models.PromptExecution:
    """
    在数据库中创建一条 Prompt 执行记录。
    """
    db_execution = models.PromptExecution(
        prompt_id=prompt_id,
        user_id=user_id,
        request_data=request_data,
        response_text=result.content,
        token_usage=result.usage,
        error_message=result.error
    )
    db.add(db_execution)
    db.commit()
    db.refresh(db_execution)
    return db_execution

def get_prompt_executions(db: Session, prompt_id: int, skip: int = 0, limit: int = 100):
    """
    获取某个 Prompt 的所有执行历史记录。
    """
    return db.query(models.PromptExecution)\
             .filter(models.PromptExecution.prompt_id == prompt_id)\
             .order_by(models.PromptExecution.created_at.desc())\
             .offset(skip)\
             .limit(limit)\
             .all()