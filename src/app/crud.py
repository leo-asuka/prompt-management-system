# src/app/crud.py
from sqlalchemy.orm import Session
from .models import Prompt
from .schemas import PromptCreate, PromptUpdate

def create_prompt(db: Session, prompt: PromptCreate):
    """
    在数据库中创建一个新的 Prompt 记录。
    :param db: 数据库 Session。
    :param prompt: Pydantic 模型，包含创建所需的数据。
    :return: 创建好的 SQLAlchemy Prompt 模型实例。
    """
    # 将 Pydantic 模型 (prompt) 转换为 SQLAlchemy 模型 (db_prompt)
    db_prompt = Prompt(
        title=prompt.title,
        content=prompt.content,
        category=prompt.category
    )
    db.add(db_prompt)  # 将新对象添加到 Session 中（暂存）
    db.commit()      # 将暂存的更改提交到数据库
    db.refresh(db_prompt) # 刷新 db_prompt 对象，以获取数据库生成的值（如 id, created_at）
    return db_prompt

def get_prompts(db: Session, skip: int = 0, limit: int = 100):
    """从数据库中查询 Prompt 列表，支持分页。"""
    return db.query(Prompt).offset(skip).limit(limit).all()

def get_prompt(db: Session, prompt_id: int):
    """根据 ID 查询单个 Prompt。.first() 表示只返回第一条匹配的记录，如果没有找到则返回 None。"""
    return db.query(Prompt).filter(Prompt.id == prompt_id).first()

def update_prompt(db: Session, prompt_id: int, prompt_update: PromptUpdate):
    """更新一个已存在的 Prompt 记录。"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        return None
    # 它会生成一个只包含被显式设置过的字段的字典。
    # 比如，如果请求体只有 {"title": "new title"}，这个字典就是 {"title": "new title"}。
    # 这对于实现部分更新 (PATCH) 非常有用。
    update_data = prompt_update.model_dump(exclude_unset=True)
    # 遍历更新数据，并使用 setattr 更新 SQLAlchemy 模型对象的属性
    for field, value in update_data.items():
        setattr(prompt, field, value)

    db.commit()
    db.refresh(prompt)
    return prompt

def delete_prompt(db: Session, prompt_id: int):
    """根据 ID 删除一个 Prompt 记录。"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        return None

    db.delete(prompt)
    db.commit()
    return None
