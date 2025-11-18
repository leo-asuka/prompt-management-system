# main.py
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text, func
from sqlalchemy.exc import OperationalError
from typing import Annotated
from . import models
from .database import lifespan, get_db
from .crud import (
    create_prompt,
    get_prompts,
    get_prompt,
    update_prompt,
    delete_prompt
)
from .schemas import PromptCreate, PromptUpdate, PromptResponse, PromptList
from .config import settings

# 确保在 FastAPI 启动前，数据库表已经通过 Base.metadata 注册
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LLM Prompt Management System",
    description="一个用于管理 LLM 提示词的 API 系统",
    version="0.1.0",
    lifespan=lifespan
)

DBSession = Annotated[Session, Depends(lambda: get_db(app))]

# ==================== 健康检查端点 ====================

@app.get("/", summary="根路径-验证热重载")
async def read_root():
    """
    欢迎页面，返回系统信息
    """
    return {
        "message": "Welcome to the NEW and IMPROVED LLM Prompt Management System!", # 修改这里
        "version": "0.1.0",
        "description": "API for managing LLM prompt templates"
    }

@app.get("/health", summary="服务健康检查")
async def health_check():
    """
    检查API服务是否正常运行
    """
    return {"status": "ok"}

@app.get("/db_health", summary="数据库连接健康检查")
async def db_health_check(db: DBSession):
    """
    检查API服务是否能成功连接到PostgreSQL数据库
    """
    try:
        result = db.execute(text("SELECT 1")).fetchone()
        if result and result[0] == 1:
            return {"status": "ok", "database_connection": "successful"}
        else:
            raise HTTPException(status_code=500, detail="Database query failed.")
    except OperationalError as e:
        print(f"数据库操作错误: {e}")
        raise HTTPException(status_code=503, detail=f"Database connection error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

# ==================== 提示词 CRUD 端点 ====================

@app.post("/prompts", response_model=PromptResponse, status_code=201, summary="创建新提示词")
async def create_prompt(prompt: PromptCreate, db: DBSession):
    """
    创建一个新的提示词模板。FastAPI 会自动处理：
    1. 校验请求体是否符合 PromptCreate schema。
    2. 调用 get_db() 获取数据库 session，并注入到 db 参数。
    3. 将返回值（SQLAlchemy对象）通过 PromptResponse schema 转换为 JSON 响应。

    - **title**: 提示词标题（必填）
    - **content**: 提示词内容（必填）
    - **category**: 提示词分类（可选）
    """
    return create_prompt(db, prompt)

@app.get("/prompts", response_model=PromptList, summary="列出所有提示词")
async def list_prompts(
    db: DBSession,
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的最大记录数")
):
    """
    获取所有提示词列表（支持分页）

    - **skip**: 跳过的记录数（默认0）
    - **limit**: 返回的最大记录数（默认100，最大100）
    """
    prompts = get_prompts(db, skip, limit)
    # 【优化点】计算数据库中 prompt 的总数，用于分页
    total_count = db.query(func.count(models.Prompt.id)).scalar()
    return {"total": total_count, "prompts": prompts}

@app.get("/prompts/{prompt_id}", response_model=PromptResponse, summary="获取特定提示词")
async def get_prompt(prompt_id: int, db: DBSession):
    """
    根据ID获取特定的提示词详情

    - **prompt_id**: 提示词ID
    """
    prompt = get_prompt(db, prompt_id)
    if not prompt:
        # 如果 CRUD 函数返回 None，说明记录不存在，抛出 404 异常。
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt

@app.put("/prompts/{prompt_id}", response_model=PromptResponse, summary="更新提示词")
async def update_prompt(prompt_id: int, prompt_update: PromptUpdate, db: DBSession):
    """
    更新指定ID的提示词

    - **prompt_id**: 提示词ID
    - **title**: 新的标题（可选）
    - **content**: 新的内容（可选）
    - **category**: 新的分类（可选）
    """
    prompt = update_prompt(db, prompt_id, prompt_update)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt

@app.delete("/prompts/{prompt_id}", status_code=204, summary="删除提示词")
async def delete_prompt(prompt_id: int, db: DBSession):
    """
    删除指定ID的提示词

    - **prompt_id**: 提示词ID
    """
    delete_prompt(db, prompt_id)
    return JSONResponse(status_code=204)
