# crud.py
from sqlalchemy.orm import Session
from .models import Prompt
from .schemas import PromptCreate, PromptUpdate

def create_prompt(db: Session, prompt: PromptCreate):
    db_prompt = Prompt(
        title=prompt.title,
        content=prompt.content,
        category=prompt.category
    )
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

def get_prompts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Prompt).offset(skip).limit(limit).all()

def get_prompt(db: Session, prompt_id: int):
    return db.query(Prompt).filter(Prompt.id == prompt_id).first()

def update_prompt(db: Session, prompt_id: int, prompt_update: PromptUpdate):
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        return None

    update_data = prompt_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prompt, field, value)

    db.commit()
    db.refresh(prompt)
    return prompt

def delete_prompt(db: Session, prompt_id: int):
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        return None

    db.delete(prompt)
    db.commit()
    return None
