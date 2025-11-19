# src/app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
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

# ==================== Tag CRUD====================

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

# ==================== Rating CRUD ====================

def create_rating_for_prompt(db: Session, prompt_id: int, user_id: int, score: int) -> Optional[models.Rating]:
    """为一个 Prompt 创建一条新的用户评分记录。"""
    db_rating = models.Rating(prompt_id=prompt_id, user_id=user_id, score=score)
    db.add(db_rating)
    try:
        db.commit()
        db.refresh(db_rating)
        return db_rating
    except IntegrityError: # 捕获违反唯一约束的异常
        db.rollback()
        return None

def get_ratings_for_prompt(db: Session, prompt_id: int, skip: int = 0, limit: int = 100):
    """获取指定 Prompt 的所有评分记录。"""
    return db.query(models.Rating)\
             .filter(models.Rating.prompt_id == prompt_id)\
             .offset(skip)\
             .limit(limit)\
             .all()

# ==================== Prompt CRUD 更新 ====================
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

# 更新：get_prompts 函数
def get_prompts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    tags: Optional[List[str]] = None,
    sort: Optional[str] = None
):
    avg_rating = func.avg(models.Rating.score).label("average_rating")
    
    base_query = db.query(models.Prompt)\
                   .outerjoin(models.Rating)

    if tags:
        for tag_name in tags:
            base_query = base_query.filter(models.Prompt.tags.any(name=tag_name))
    
    # 【修复】先计算总数
    total_query = base_query.group_by(models.Prompt.id)
    total = total_query.count()

    # 现在构建包含聚合和排序的主查询
    main_query = base_query.add_columns(avg_rating)\
                           .group_by(models.Prompt.id)

    if sort == "rating":
        main_query = main_query.order_by(avg_rating.desc().nullslast())
    else:
        main_query = main_query.order_by(models.Prompt.created_at.desc())

    results = main_query.offset(skip).limit(limit).all()
    
    prompts_with_ratings = []
    for prompt, rating in results:
        prompt.average_rating = rating if rating is not None else 0.0
        prompts_with_ratings.append(prompt)

    return prompts_with_ratings, total

def get_prompt(db: Session, prompt_id: int):
    """根据 ID 查询单个 Prompt。.first() 表示只返回第一条匹配的记录，如果没有找到则返回 None。"""
    return db.query(Prompt).filter(Prompt.id == prompt_id).first()

def get_prompt_with_average_rating(db: Session, prompt_id: int):
    """获取单个 Prompt，并动态计算其平均分。"""
    avg_rating = func.avg(models.Rating.score).label("average_rating")
    
    result = db.query(models.Prompt, avg_rating)\
               .outerjoin(models.Rating)\
               .filter(models.Prompt.id == prompt_id)\
               .group_by(models.Prompt.id)\
               .first()

    if result:
        prompt, rating = result
        prompt.average_rating = rating if rating is not None else 0.0
        return prompt
    return None

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
