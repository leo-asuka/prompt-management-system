# src/app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from . import models, schemas, llm_client, cache
from .models import Prompt
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


def create_rating_for_prompt(
    db: Session, prompt_id: int, user_id: int, score: int
) -> Optional[models.Rating]:
    """为一个 Prompt 创建一条新的用户评分记录。"""
    db_rating = models.Rating(prompt_id=prompt_id, user_id=user_id, score=score)
    db.add(db_rating)
    try:
        db.commit()
        db.refresh(db_rating)
        return db_rating
    except IntegrityError:  # 捕获违反唯一约束的异常
        db.rollback()
        return None


def get_ratings_for_prompt(
    db: Session, prompt_id: int, skip: int = 0, limit: int = 100
):
    """获取指定 Prompt 的所有评分记录。"""
    return (
        db.query(models.Rating)
        .filter(models.Rating.prompt_id == prompt_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


# ==================== Prompt CRUD ====================
# 创建 Prompt 时需要知道是哪个用户创建的
def create_prompt(db: Session, prompt: schemas.PromptCreate, user_id: int):
    """
    在数据库中创建一个新的 Prompt 记录。自动创建版本 1
    :param db: 数据库 Session。
    :param prompt: Pydantic 模型，包含创建所需的数据。
    :return: 创建好的 SQLAlchemy Prompt 模型实例。
    """
    # 1. 创建主 Prompt 记录
    # 将 Pydantic 模型 (prompt) 转换为 SQLAlchemy 模型 (db_prompt)
    db_prompt = Prompt(
        # title=prompt.title,
        # content=prompt.content,
        # category=prompt.category
        **prompt.model_dump(),  # 使用 model_dump 简化代码
        user_id=user_id,
    )
    db.add(db_prompt)  # 将新对象添加到 Session 中（暂存）
    db.commit()  # 将暂存的更改提交到数据库
    db.refresh(
        db_prompt
    )  # 刷新 db_prompt 对象，以获取数据库生成的值（如 id, created_at）
    # 2. 创建版本 1 快照
    version = models.PromptVersion(
        prompt_id=db_prompt.id,
        version_number=1,
        title=db_prompt.title,
        content=db_prompt.content,
        category=db_prompt.category,
    )
    db.add(version)
    db.commit()
    return db_prompt


def get_prompts_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """获取指定用户的所有 Prompts"""
    return (
        db.query(models.Prompt)
        .filter(models.Prompt.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


# 更新：get_prompts 函数
def get_prompts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    tags: Optional[List[str]] = None,
    sort: Optional[str] = None,
):
    avg_rating = func.avg(models.Rating.score).label("average_rating")

    base_query = db.query(models.Prompt).outerjoin(models.Rating)

    if tags:
        for tag_name in tags:
            base_query = base_query.filter(models.Prompt.tags.any(name=tag_name))

    # 先计算总数
    total_query = base_query.group_by(models.Prompt.id)
    total = total_query.count()

    # 现在构建包含聚合和排序的主查询
    main_query = base_query.add_columns(avg_rating).group_by(models.Prompt.id)

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


# 1. 优化 get_prompt_with_average_rating (读操作)
def get_prompt_with_average_rating(db: Session, prompt_id: int):
    """获取单个 Prompt，并动态计算其平均分，带缓存支持。"""
    # --- 步骤 1: 尝试从缓存读取 ---
    cached_prompt = cache.get_prompt_cache(prompt_id)
    if cached_prompt:
        # 如果命中缓存，直接返回，不再连接数据库
        return cached_prompt
    # --- 步骤 2: 缓存未命中，查询数据库 ---
    avg_rating = func.avg(models.Rating.score).label("average_rating")
    result = (
        db.query(models.Prompt, avg_rating)
        .outerjoin(models.Rating)
        .filter(models.Prompt.id == prompt_id)
        .group_by(models.Prompt.id)
        .first()
    )

    if result:
        prompt, rating = result
        prompt.average_rating = rating if rating is not None else 0.0
        # --- 步骤 3: 写入缓存 ---
        # 我们需要先将其转换为 Pydantic Schema，因为我们的缓存函数只接受 Schema
        # 注意：这里需要手动构建一下 schema 对象，或者利用 from_attributes
        prompt_schema = schemas.PromptResponse.model_validate(prompt)
        cache.set_prompt_cache(prompt_schema)

        return prompt
    return None


# 2. 优化 update_prompt (写操作 - 缓存失效)
def update_prompt(
    db: Session, db_prompt: models.Prompt, prompt_update: schemas.PromptUpdate
):
    """
    更新一个已存在的 Prompt 记录。这个函数现在直接接收一个 SQLAlchemy 模型实例 (db_prompt)，而不是 prompt_id。
    更新 Prompt，并自动创建新版本，并清除缓存
    """
    # 1. 更新主表数据
    update_data = prompt_update.model_dump(exclude_unset=True)
    # 如果没有实际数据更新，直接返回
    if not update_data:
        return db_prompt

    for field, value in update_data.items():
        setattr(db_prompt, field, value)

    # 2. 计算下一个版本号
    # 查询当前最大的版本号
    last_version = (
        db.query(func.max(models.PromptVersion.version_number))
        .filter(models.PromptVersion.prompt_id == db_prompt.id)
        .scalar()
    )
    new_version_number = (last_version or 0) + 1

    # 3. 创建新版本快照
    new_version = models.PromptVersion(
        prompt_id=db_prompt.id,
        version_number=new_version_number,
        title=db_prompt.title,
        content=db_prompt.content,
        category=db_prompt.category,
    )

    db.add(db_prompt)  # 虽然 SQLAlchemy 跟踪了对象，但显式 add 更清晰
    db.add(new_version)
    db.commit()
    db.refresh(db_prompt)

    # 清除缓存，因为数据变了，旧的缓存已经脏了，必须删除
    cache.delete_prompt_cache(db_prompt.id)
    return db_prompt


def get_prompt_versions(db: Session, prompt_id: int):
    """获取 Prompt 的所有版本"""
    return (
        db.query(models.PromptVersion)
        .filter(models.PromptVersion.prompt_id == prompt_id)
        .order_by(desc(models.PromptVersion.version_number))
        .all()
    )


def get_prompt_version(db: Session, prompt_id: int, version_number: int):
    """获取特定版本"""
    return (
        db.query(models.PromptVersion)
        .filter(
            models.PromptVersion.prompt_id == prompt_id,
            models.PromptVersion.version_number == version_number,
        )
        .first()
    )


def rollback_prompt(db: Session, db_prompt: models.Prompt, version_number: int):
    """
    回滚到指定版本。
    策略：不是删除历史，而是将指定版本的内容复制出来，作为最新的更新（生成新版本）。
    这样保证了历史的线性向前，不会丢失“回滚”这一操作记录。
    """
    target_version = get_prompt_version(db, db_prompt.id, version_number)
    if not target_version:
        return None

    # 构造更新数据，覆盖当前 Prompt
    prompt_update = schemas.PromptUpdate(
        title=target_version.title,
        content=target_version.content,
        category=target_version.category,
    )

    # 复用 update_prompt 逻辑，它会自动处理“创建新版本”的逻辑
    return update_prompt(db, db_prompt, prompt_update)


# 3. 优化 delete_prompt (删操作 - 缓存失效)
def delete_prompt(db: Session, db_prompt: models.Prompt):
    """删除 Prompt 并清除缓存"""
    prompt_id = db_prompt.id  # 先记下 ID
    db.delete(db_prompt)
    db.commit()

    # --- 清除缓存 ---
    cache.delete_prompt_cache(prompt_id)

    return None


# ==================== PromptExecution CRUD (New) ====================


def create_prompt_execution(
    db: Session,
    prompt_id: int,
    user_id: int,
    request_data: dict,
    result: llm_client.LLMExecutionResult,
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
        error_message=result.error,
    )
    db.add(db_execution)
    db.commit()
    db.refresh(db_execution)
    return db_execution


def get_prompt_executions(db: Session, prompt_id: int, skip: int = 0, limit: int = 100):
    """
    获取某个 Prompt 的所有执行历史记录。
    """
    return (
        db.query(models.PromptExecution)
        .filter(models.PromptExecution.prompt_id == prompt_id)
        .order_by(models.PromptExecution.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
