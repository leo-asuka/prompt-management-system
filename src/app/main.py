# src/app/main.py
import time
from fastapi import Request  # 导入 Request
from fastapi import FastAPI, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from typing import Annotated, Optional, List
from .database import lifespan, get_db
from . import models, crud, schemas
from .llm_client import execute_prompt
from .schemas import (
    PromptCreate,
    PromptUpdate,
    PromptResponse,
    UserResponse,
    UserCreate,
    PromptExecuteRequest,
    PromptExecutionResponse,
    RatingCreate,
    RatingResponse,
    PromptVersionResponse,
)

from prometheus_fastapi_instrumentator import Instrumentator
from .logger import logger

# 确保在 FastAPI 启动前，数据库表已经通过 Base.metadata 注册
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LLM Prompt Management System",
    description="一个用于管理 LLM 提示词的 API 系统",
    version="0.3.0",
    lifespan=lifespan,
)

# --- 1. Prometheus 监控集成 ---
# 自动为所有 API 端点添加 metrics 收集
Instrumentator().instrument(app).expose(app)


# --- 2. 请求日志中间件 ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # 处理请求
    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000

    # 记录结构化日志
    # extra 字段会被自动合并到 JSON 顶层，非常方便查询
    logger.info(
        "HTTP Request",
        extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time_ms": round(process_time, 2),
            "client_ip": request.client.host if request.client else "unknown",
        },
    )

    return response


DBSession = Annotated[Session, Depends(get_db)]
# CurrentUser = Annotated[models.User, Depends(crud.get_current_user)] # 使用 crud 中的函数


# 用户身份验证依赖项
async def get_current_user(x_user_id: Annotated[int, Header()], db: DBSession):
    """
    一个简单的依赖项，用于从请求头 X-User-ID 获取用户。
    在真实应用中，这里应该是复杂的 token 验证逻辑。
    """
    user = db.query(models.User).filter(models.User.id == x_user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user ID")
    return user


# 定义一个类型别名，方便在路径操作函数中使用
CurrentUser = Annotated[models.User, Depends(get_current_user)]

# ==================== 健康检查端点 ====================


@app.get("/", summary="根路径-验证热重载")
async def read_root():
    """
    欢迎页面，返回系统信息
    """
    return {
        "message": "Welcome to the NEW and IMPROVED LLM Prompt Management System!",
        "version": "0.1.0",
        "description": "API for managing LLM prompt templates",
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
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )


@app.post(
    "/prompts/{prompt_id}/ratings",
    response_model=RatingResponse,
    status_code=201,
    summary="为一个 Prompt 评分",
)
async def rate_prompt_endpoint(
    prompt_id: int, rating: RatingCreate, db: DBSession, current_user: CurrentUser
):
    """
    为一个 Prompt 提交评分。
    - 一个用户只能对同一个 Prompt 评分一次。
    - 分数必须在 1 到 5 之间。
    - 需要用户认证。
    """
    db_prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if not db_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # 防止用户给自己创建的 Prompt 评分
    if db_prompt.user_id == current_user.id:
        raise HTTPException(status_code=403, detail="You cannot rate your own prompt")

    db_rating = crud.create_rating_for_prompt(
        db, prompt_id=prompt_id, user_id=current_user.id, score=rating.score
    )

    if db_rating is None:
        # 409 Conflict 状态码表示请求与服务器当前状态冲突（这里指重复评分）
        raise HTTPException(
            status_code=409, detail="You have already rated this prompt"
        )

    return db_rating


@app.get(
    "/prompts/{prompt_id}/ratings",
    response_model=List[RatingResponse],
    summary="获取一个 Prompt 的所有评分",
)
async def get_prompt_ratings_endpoint(prompt_id: int, db: DBSession):
    """
    获取指定 Prompt 的所有评分记录。
    """
    db_prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if not db_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    return crud.get_ratings_for_prompt(db, prompt_id=prompt_id)


# ==================== Prompt Execution Endpoints ====================


@app.post(
    "/prompts/{prompt_id}/execute",
    response_model=PromptExecutionResponse,
    summary="执行提示词",
)
async def execute_prompt_endpoint(
    prompt_id: int,
    execute_request: PromptExecuteRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    执行一个提示词模板：
    1. 使用提供的变量替换模板内容。
    2. 调用 LLM API (例如 OpenAI) 获取结果。
    3. 将执行过程和结果存入历史记录。

    - **需要认证** (`X-User-ID` 请求头)。
    """
    db_prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if not db_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # 调用 llm_client 中的执行函数
    llm_result = execute_prompt(
        prompt_content=db_prompt.content, variables=execute_request.variables
    )

    # 无论成功与否，都创建一条执行记录
    execution_record = crud.create_prompt_execution(
        db=db,
        prompt_id=prompt_id,
        user_id=current_user.id,
        request_data=execute_request.variables,
        result=llm_result,
    )

    # 如果 LLM 调用失败，向客户端返回一个服务端错误
    if not llm_result.success:
        raise HTTPException(status_code=500, detail=llm_result.error)

    return execution_record


@app.get(
    "/prompts/{prompt_id}/executions",
    response_model=List[PromptExecutionResponse],
    summary="获取提示词执行历史",
)
async def list_prompt_executions_endpoint(
    prompt_id: int,
    db: DBSession,
    current_user: CurrentUser,  # 添加认证，确保用户能看到历史
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """
    获取指定提示词的所有执行历史记录。
    - 任何人都可以查看任何 Prompt 的执行历史（也可以添加权限，只让所有者查看）。
    """
    db_prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if not db_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    executions = crud.get_prompt_executions(
        db, prompt_id=prompt_id, skip=skip, limit=limit
    )
    return executions


# ==================== Tag Endpoints ====================


@app.post(
    "/tags", response_model=schemas.TagResponse, status_code=201, summary="创建新标签"
)
async def create_tag_endpoint(
    tag: schemas.TagCreate, db: DBSession, current_user: CurrentUser
):
    """
    创建一个新的标签。标签名必须是唯一的。
    需要认证。
    """
    db_tag = crud.get_tag_by_name(db, name=tag.name)
    if db_tag:
        raise HTTPException(status_code=400, detail="Tag with this name already exists")
    return crud.create_tag(db=db, tag=tag)


@app.get("/tags", response_model=List[schemas.TagResponse], summary="获取所有标签")
async def list_tags_endpoint(db: DBSession, skip: int = 0, limit: int = 100):
    """
    获取所有已创建的标签列表。
    """
    tags = crud.get_tags(db, skip=skip, limit=limit)
    return tags


# ==================== Prompt-Tag Association Endpoints (New) ====================


@app.post(
    "/prompts/{prompt_id}/tags/{tag_id}",
    response_model=schemas.PromptResponse,
    summary="为提示词添加标签",
)
async def add_tag_to_prompt_endpoint(
    prompt_id: int, tag_id: int, db: DBSession, current_user: CurrentUser
):
    """
    为一个提示词添加一个标签。
    - 只有提示词的所有者才能操作。
    """
    db_prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if not db_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    if db_prompt.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this prompt"
        )

    db_tag = crud.get_tag(db, tag_id=tag_id)
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    return crud.add_tag_to_prompt(db=db, db_prompt=db_prompt, db_tag=db_tag)


@app.delete(
    "/prompts/{prompt_id}/tags/{tag_id}",
    response_model=schemas.PromptResponse,
    summary="从提示词移除标签",
)
async def remove_tag_from_prompt_endpoint(
    prompt_id: int, tag_id: int, db: DBSession, current_user: CurrentUser
):
    """
    从一个提示词移除一个标签。
    - 只有提示词的所有者才能操作。
    """
    db_prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if not db_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    if db_prompt.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this prompt"
        )

    db_tag = crud.get_tag(db, tag_id=tag_id)
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    return crud.remove_tag_from_prompt(db=db, db_prompt=db_prompt, db_tag=db_tag)


# ==================== Versioning Endpoints (New) ====================


@app.get(
    "/prompts/{prompt_id}/versions",
    response_model=List[PromptVersionResponse],
    summary="查看所有版本",
)
async def list_prompt_versions_endpoint(
    prompt_id: int, db: DBSession, current_user: CurrentUser
):
    """获取指定 Prompt 的所有历史版本快照"""
    db_prompt = crud.get_prompt(db, prompt_id)
    if not db_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return crud.get_prompt_versions(db, prompt_id)


@app.get(
    "/prompts/{prompt_id}/versions/{version_number}",
    response_model=PromptVersionResponse,
    summary="查看特定版本",
)
async def get_prompt_version_endpoint(
    prompt_id: int, version_number: int, db: DBSession, current_user: CurrentUser
):
    """获取指定 Prompt 的特定版本详情"""
    version = crud.get_prompt_version(db, prompt_id, version_number)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@app.post(
    "/prompts/{prompt_id}/rollback/{version_number}",
    response_model=PromptResponse,
    summary="回滚到指定版本",
)
async def rollback_prompt_endpoint(
    prompt_id: int, version_number: int, db: DBSession, current_user: CurrentUser
):
    """
    将 Prompt 回滚到指定版本。
    注意：这不会删除历史，而是会基于目标版本的内容创建一个**最新**的版本。
    只有所有者可以执行此操作。
    """
    db_prompt = crud.get_prompt(db, prompt_id)
    if not db_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if db_prompt.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to rollback this prompt"
        )

    updated_prompt = crud.rollback_prompt(db, db_prompt, version_number)
    if not updated_prompt:
        raise HTTPException(status_code=404, detail="Target version not found")

    return updated_prompt


# ==================== 提示词 CRUD 端点 ====================


@app.post(
    "/prompts",
    response_model=PromptResponse,
    status_code=201,
    summary="创建新提示词 (需要认证)",
)
async def create_prompt_endpoint(
    prompt: PromptCreate, db: DBSession, current_user: CurrentUser
):
    """
    创建一个新的提示词模板。FastAPI 会自动处理：
    1. 校验请求体是否符合 PromptCreate schema。
    2. 调用 get_db() 获取数据库 session，并注入到 db 参数。
    3. 将返回值（SQLAlchemy对象）通过 PromptResponse schema 转换为 JSON 响应。

    - **title**: 提示词标题（必填）
    - **content**: 提示词内容（必填）
    - **category**: 提示词分类（可选）
    """
    return crud.create_prompt(db=db, prompt=prompt, user_id=current_user.id)


@app.get(
    "/prompts",
    response_model=schemas.PromptList,
    summary="列出所有提示词 (支持按标签筛选)",
)
async def list_prompts_endpoint(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    tags: Optional[str] = Query(
        None, description="用逗号分隔的标签名, e.g., 'marketing,sales'"
    ),
    sort: Optional[str] = Query(
        None, description="排序字段。使用 'rating' 按平均分排序。"
    ),
):
    """
    获取所有提示词列表（支持分页）

    - **skip**: 跳过的记录数（默认0）
    - **limit**: 返回的最大记录数（默认100，最大100）
    """
    tag_list = tags.split(",") if tags else None
    prompts, total = crud.get_prompts(
        db, skip=skip, limit=limit, tags=tag_list, sort=sort
    )
    return {"total": total, "prompts": prompts}


@app.get(
    "/prompts/{prompt_id}", response_model=PromptResponse, summary="获取特定提示词"
)
async def get_prompt_endpoint(prompt_id: int, db: DBSession):
    """
    根据ID获取特定的提示词详情

    - **prompt_id**: 提示词ID
    """
    prompt = crud.get_prompt_with_average_rating(db, prompt_id)
    if not prompt:
        # 如果 CRUD 函数返回 None，说明记录不存在，抛出 404 异常。
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@app.put(
    "/prompts/{prompt_id}",
    response_model=PromptResponse,
    summary="更新提示词 (需要认证和所有权)",
)
async def update_prompt_endpoint(
    prompt_id: int,
    prompt_update: PromptUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    更新指定ID的提示词

    - **只有提示词的所有者才能更新**。
    - **需要** 在请求头中提供 `X-User-ID`。
    - **prompt_id**: 提示词ID
    - **title**: 新的标题（可选）
    - **content**: 新的内容（可选）
    - **category**: 新的分类（可选）
    """
    db_prompt = crud.get_prompt(db, prompt_id)
    if not db_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # --- 权限检查 ---
    if db_prompt.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this prompt"
        )

    return crud.update_prompt(db=db, db_prompt=db_prompt, prompt_update=prompt_update)


@app.delete(
    "/prompts/{prompt_id}", status_code=204, summary="删除提示词 (需要认证和所有权)"
)
async def delete_prompt_endpoint(
    prompt_id: int, db: DBSession, current_user: CurrentUser
):
    """
    删除指定ID的提示词

    - **prompt_id**: 提示词ID
    """
    # 首先调用 CRUD 函数执行删除操作
    # 【优化】可以检查一下返回值，如果 prompt 不存在，可以返回 404
    db_prompt = crud.get_prompt(db, prompt_id)
    if db_prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if db_prompt.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this prompt"
        )

    crud.delete_prompt(db, db_prompt)

    # 【修复】对于 204 No Content，我们应该返回 None。
    # FastAPI 会自动处理，生成一个没有 body 的正确 HTTP 响应。
    return None


# ==================== 用户端点 ====================


@app.post("/users", response_model=UserResponse, status_code=201, summary="创建新用户")
async def create_user_endpoint(user: UserCreate, db: DBSession):
    """
    注册一个新用户。用户名必须是唯一的。
    """
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)


@app.get(
    "/users/{user_id}/prompts",
    response_model=list[PromptResponse],
    summary="获取用户的所有提示词",
)
async def get_user_prompts_endpoint(user_id: int, db: DBSession):
    """
    根据用户ID获取该用户创建的所有提示词列表。
    """
    # 检查用户是否存在
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prompts = crud.get_prompts_by_user(db=db, user_id=user_id)
    return prompts
