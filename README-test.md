# LLM-X-S2-L1

LLM-X 课程第二季-第一节课

## 🎯 业务目标

本项目是一个 **LLM 提示词管理系统 (Prompt Management System)**，用于演示现代 AI 工程项目的完整开发流程。

**核心功能：**

- 📝 创建和管理 LLM 提示词模板
- 🔍 搜索和检索提示词
- 📊 跟踪提示词使用统计
- 🏷️ 提示词分类管理

**学习目标：**
这是一个结构化的、最小可行的项目模板，它精确地对应了我们PPT中讨论的所有工程实践：PDM + `src`布局、生产优化的`Dockerfile`、用于编排FastAPI和PostgreSQL的`docker-compose.yml`，以及配套的配置和说明文件。

## 📡 API 端点

| 方法   | 端点                          | 功能           |
| ------ | ----------------------------- | -------------- |
| GET    | `/`                           | 欢迎页面       |
| GET    | `/health`                     | API 健康检查   |
| GET    | `/db_health`                  | 数据库连接检查 |
| POST   | `/prompts`                    | 创建新提示词   |
| GET    | `/prompts`                    | 列出所有提示词 |
| GET    | `/prompts/{id}`               | 获取特定提示词 |
| PUT    | `/prompts/{id}`               | 更新提示词     |
| DELETE | `/prompts/{id}`               | 删除提示词     |
| GET    | `/prompts/search?keyword=xxx` | 搜索提示词     |

## 🚀 快速开始

### 前置条件

- Docker 和 Docker Compose
- Git

### 启动项目

```bash
# 1. 克隆仓库
git clone https://github.com/sawyerbutton/LLM-X-S2-L1.git
cd LLM-X-S2-L1

# 2. 启动服务
docker compose up --build

# 3. 运行自动化测试（新终端）
./test.sh
```

### 访问服务

- **API 地址**: <http://localhost:8000>
- **交互式文档**: <http://localhost:8000/docs>
- **ReDoc 文档**: <http://localhost:8000/redoc>

### 完整测试指南

详细的测试步骤和说明请查看 **[TESTING.md](TESTING.md)**，包括：

- 详细的 API 端点测试
- 数据库连接测试
- 热重载测试
- 数据持久化验证
- 故障排查指南

-----

### 课程代码：AI工程项目模板 (Week 1)

**项目目录结构：**

```
prompt-management-system/
├── src/app/
│       ├── __init__.py
│       ├── config.py     # 使用 Pydantic 管理环境变量
│       ├── crud.py       # 数据库操作
│       ├── database.py   # 数据库连接
│       ├── main.py       # FastAPI 应用入口
│       ├── models.py     # 数据模型
│       └── schemas.py    # Pydantic Schemas
├── tests/
│   └── test_prompts.py   # 基础测试
├── .dockerignore         # 应用容器配置
├── .env.example          # 环境变量模板
├── .gitignore            # Git 忽略文件
├── docker-compose.yml    # 服务编排
├── Dockerfile            # 应用容器配置
├── pyproject.toml        # 依赖
└── README.md             # 项目说明
```

-----

### 文件详细内容

#### 1\. `pyproject.toml`

(PDM项目定义与依赖管理)

```toml
[project]
name = "llm-prompt-manager"
version = "0.1.0"
description = "LLM Prompt Management System - Week 1 demo project for AI Engineering course."
authors = [
    {name = "LLM-X Course", email = "course@example.com"},
]
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.1",
    "pydantic-settings>=2.3.4",  # 用于从.env读取配置
    "psycopg2-binary>=2.9.9",    # PostgreSQL驱动
    "sqlalchemy>=2.0.31",        # ORM
]
requires-python = ">=3.11"
readme = "README.md"
license = {text = "MIT"}

[tool.pdm.scripts]
# 脚本别名，方便本地开发
# dev = "uvicorn src.main.app:app --reload --host 0.0.0.0 --port 8000"
dev = "uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000"

[dependency-groups]
dev = [
    "pytest>=9.0.1",
    "httpx>=0.28.1",
    "pytest-depends>=1.0.1",
]
```

#### 2\. `src/main/config.py`

(使用Pydantic-Settings管理环境变量)

```python
# src/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    使用 Pydantic 管理环境变量，这个类会自动读取环境变量，并根据类型注解进行验证和转换。
    SettingsConfigDict 会自动查找 .env 文件
    """
    # model_config 指向一个配置字典，告诉 Pydantic 如何加载设置。
    # env_file='.env' 指定了从哪个文件加载环境变量。
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # PostgreSQL 数据库配置
    # Pydantic 会自动查找并加载名为 POSTGRES_USER, POSTGRES_PASSWORD等的环境变量。
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    @property
    def database_url(self) -> str:
        """
        生成 SQLAlchemy 兼容的数据库连接字符串
        """
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


@lru_cache()  # 缓存配置实例，避免重复读取.env
def get_settings() -> Settings:
    """
    这个函数用于创建并返回 Settings 的单例。
    lru_cache 会确保 Settings() 只被调用一次，后续调用会直接返回缓存的结果。
    这避免了在每次需要配置时都重复读取和解析 .env 文件，提高了效率。
    """
    return Settings()


# 创建一个全局可用的 settings 实例，方便在应用各处导入和使用。
settings = get_settings()

```

#### 3\. `src/app/main.py`

(FastAPI应用主文件)

```python
# src/app/main.py
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text, func
from sqlalchemy.exc import OperationalError
from typing import Annotated
from . import models
from .database import lifespan, get_db
from . import crud
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

DBSession = Annotated[Session, Depends(get_db)]

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
async def create_prompt_endpoint(prompt: PromptCreate, db: DBSession):
    """
    创建一个新的提示词模板。FastAPI 会自动处理：
    1. 校验请求体是否符合 PromptCreate schema。
    2. 调用 get_db() 获取数据库 session，并注入到 db 参数。
    3. 将返回值（SQLAlchemy对象）通过 PromptResponse schema 转换为 JSON 响应。

    - **title**: 提示词标题（必填）
    - **content**: 提示词内容（必填）
    - **category**: 提示词分类（可选）
    """
    return crud.create_prompt(db=db, prompt=prompt)

@app.get("/prompts", response_model=PromptList, summary="列出所有提示词")
async def list_prompts_endpoint(
    db: DBSession,
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的最大记录数")
):
    """
    获取所有提示词列表（支持分页）

    - **skip**: 跳过的记录数（默认0）
    - **limit**: 返回的最大记录数（默认100，最大100）
    """
    prompts = crud.get_prompts(db, skip, limit)
    # 【优化点】计算数据库中 prompt 的总数，用于分页
    total_count = db.query(func.count(models.Prompt.id)).scalar()
    return {"total": total_count, "prompts": prompts}

@app.get("/prompts/{prompt_id}", response_model=PromptResponse, summary="获取特定提示词")
async def get_prompt_endpoint(prompt_id: int, db: DBSession):
    """
    根据ID获取特定的提示词详情

    - **prompt_id**: 提示词ID
    """
    prompt = crud.get_prompt(db, prompt_id)
    if not prompt:
        # 如果 CRUD 函数返回 None，说明记录不存在，抛出 404 异常。
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt

@app.put("/prompts/{prompt_id}", response_model=PromptResponse, summary="更新提示词")
async def update_prompt_endpoint(prompt_id: int, prompt_update: PromptUpdate, db: DBSession):
    """
    更新指定ID的提示词

    - **prompt_id**: 提示词ID
    - **title**: 新的标题（可选）
    - **content**: 新的内容（可选）
    - **category**: 新的分类（可选）
    """
    prompt = crud.update_prompt(db, prompt_id, prompt_update)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt

@app.delete("/prompts/{prompt_id}", status_code=204, summary="删除提示词")
async def delete_prompt_endpoint(prompt_id: int, db: DBSession):
    """
    删除指定ID的提示词

    - **prompt_id**: 提示词ID
    """
    # 首先调用 CRUD 函数执行删除操作
    # 【优化】可以检查一下返回值，如果 prompt 不存在，可以返回 404
    db_prompt = crud.get_prompt(db, prompt_id)
    if db_prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    crud.delete_prompt(db, prompt_id)
    
    # 【修复】对于 204 No Content，我们应该返回 None。
    # FastAPI 会自动处理，生成一个没有 body 的正确 HTTP 响应。
    return None
```

#### 4\. `.env`

(环境变量 - 必须与`docker-compose.yml`匹配)

**\!\!\! 警告：此文件包含密钥，绝不能提交到Git。**
**请确保将 `.env` 添加到 `.gitignore` 文件中。**

```ini
# PostgreSQL 数据库配置
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword123
POSTGRES_DB=ai_eng_db
POSTGRES_SERVER=db  # 这是 docker-compose.yml 中数据库服务的名称
POSTGRES_PORT=5432
```

#### 5\. `Dockerfile`

(生产优化的Dockerfile)

```dockerfile
# -----------------
# 阶段 1: 构建 (Build Stage)
# -----------------
# 使用轻量级的 Python 3.11-slim-bookworm 作为基础镜像
FROM python:3.11-slim-bookworm AS builder

# 设置工作目录
WORKDIR /app

# 安装 PDM (包管理器)
RUN pip install --upgrade pip
RUN pip install pdm

# (核心优化) 1. 仅拷贝依赖配置文件
COPY pyproject.toml pdm.lock ./

# (核心优化) 2. 安装生产依赖
# --prod: 不安装 dev 依赖
# --no-lock: 依赖已锁定，无需重新生成 lock 文件
RUN pdm install --prod --no-lock --no-editable

# (核心优化) 3. 最后拷贝项目源代码
# 这样，如果只修改 src，前面的依赖安装层缓存不会失效
COPY ./src ./src


# -----------------
# 阶段 2: 运行 (Final Stage)
# -----------------
# 再次使用轻量级镜像，减小最终镜像体积
FROM python:3.11-slim-bookworm AS final

# 设置工作目录
WORKDIR /app

# (安全实践) 创建一个非 root 用户来运行应用
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app
USER appuser

# 从 'builder' 阶段拷贝已安装的虚拟环境
COPY --from=builder /app/.venv ./.venv

# 从 'builder' 阶段拷贝应用源代码
COPY --from=builder /app/src ./src

# 将虚拟环境的 bin 目录添加到 PATH
ENV PATH="/home/appuser/app/.venv/bin:$PATH"

# 暴露 FastAPI 运行的端口
EXPOSE 8000

# 容器启动命令
CMD ["uvicorn", "src.main.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 6\. `docker-compose.yml`

(多服务编排文件)

```yaml
version: '3.8'

services:
  # 1. API 服务 (我们的 FastAPI 应用)
  api:
    build:
      context: .  # 使用当前目录的 Dockerfile
      dockerfile: Dockerfile
    ports:
      - "8002:8000"  # 将主机的8002端口映射到容器的8000端口
    volumes:
      # 挂载 src 目录以实现热重载 (仅在开发时推荐)
      # 容器内的路径必须与 Dockerfile 中的 WORKDIR 匹配
      - ./src:/home/appuser/app/src
    env_file:
      - .env  # 从 .env 文件加载环境变量
    command: uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      db:
        condition: service_healthy   # 依赖 db 服务，并且要等 db 服务健康检查通过后才启动
    restart: unless-stopped

  # 2. 数据库服务 (PostgreSQL)
  db:
    image: postgres:16-alpine  # 使用轻量级的 alpine 版 postgres
    ports:
    #   (可选) 如果您想从主机直接访问数据库，请取消注释下一行
      - "5432:5432" # 将主机的 5432 端口映射到容器，方便使用外部工具连接数据库
    volumes:
      # 'postgres_data' 是一个具名卷，用于持久化数据库数据
      - postgres_data:/var/lib/postgresql/data/
    env_file:
      - .env  # 从 .env 文件加载 POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"] # 健康检查
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

# 定义具名卷，用于数据持久化
volumes:
  postgres_data: # 定义一个命名的 volume 用于数据持久化
```

#### 7\. `.dockerignore`

(告诉Docker在构建时忽略这些文件)

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
.venv/
venv/
env/
ENV/

# PDM
.pdm-cache/
.pdm.toml
pdm.lock

# Environment variables
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Docker
postgres_data/

# Testing
.pytest_cache/
.coverage
htmlcov/

# Logs
*.log
```

#### 8\. `README.md`

*(项目说明文档)*

````md
# AI工程：第1周 课程代码

本项目是一个最小可行的演示，用于展示如何使用 PDM、Docker 和 Docker Compose 搭建一个生产就绪的开发环境。

该环境包含一个 FastAPI (API 服务) 和一个 PostgreSQL (数据库服务)。

## 技术栈

* **Python 框架:** FastAPI
* **依赖管理:** PDM
* **项目布局:** `src` 布局
* **容器化:** Docker
* **服务编排:** Docker Compose
* **数据库:** PostgreSQL 16 (Alpine)

## 先决条件

* Docker
* Docker Compose (通常随 Docker Desktop 一起安装)
* PDM (可选, 仅用于本地非Docker开发)

## 🚀 如何一键启动

1.  **克隆仓库** (或下载文件)。
2.  **创建 `.env` 文件**:
    在项目根目录(与 `docker-compose.yml` 同级)创建一个名为 `.env` 的文件，并复制以下内容：
    ```ini
    POSTGRES_USER=myuser
    POSTGRES_PASSWORD=mypassword123
    POSTGRES_DB=ai_eng_db
    POSTGRES_SERVER=db
    POSTGRES_PORT=5432
    ```
3.  **构建并启动服务**:
    在项目根目录运行：
    ```bash
    docker-compose up --build
    ```
    * `--build` 会强制 Docker 使用 `Dockerfile` 重新构建您的 `api` 镜像。

## 验证服务

启动完成后，您可以测试以下端点：

1.  **API 健康检查**:
    在终端中运行：
    ```bash
    curl http://localhost:8000/health
    ```
    *预期响应:* `{"status":"ok"}`

2.  **数据库连接健康检查**:
    这是关键测试，验证 `api` 服务是否能成功连接到 `db` 服务：
    ```bash
    curl http://localhost:8000/db_health
    ```
    *预期响应:* `{"status":"ok","database_connection":"successful"}`

3.  **代码热重载 (Hot Reloading)**:
    * 服务运行时，尝试修改 `src/app/main.py` 中根路径 `@app.get("/")` 的 `message`。
    * 保存文件。
    * 您将在 `docker-compose up` 的日志中看到 Uvicorn 自动重启。
    * 再次访问 `http://localhost:8000/`，您将看到修改后的消息。

## GitHub Flow 实践 (作业提醒)

在您自己的项目中，请务必遵循 GitHub Flow：

1.  `git checkout -b feature/add-new-endpoint`
2.  (进行代码修改, e.g., 添加一个新的 `/v1/chat` 端点)
3.  `git commit -m "feat: add /v1/chat endpoint"`
4.  `git push origin feature/add-new-endpoint`
5.  在 GitHub 上创建 Pull Request (PR) 并合并到 `main`。
````

-----
