# AI工程：第1周 课程代码 LLM Prompt 管理系统 (LLM Prompt Management System)

本项目是一个基于 FastAPI 和 PostgreSQL 的后端服务，旨在提供一个功能完整、易于扩展的 LLM (大型语言模型) Prompt 管理系统。通过 RESTful API，用户可以对 Prompt 进行创建、读取、更新和删除 (CRUD) 操作。

该项目是作为 AI 工程课程第一周的实战作业，重点在于学习和实践结构化的 Python 项目开发、Docker 容器化、Docker Compose 服务编排以及规范的 Git 版本控制流程。

## ✨ 主要功能

* **Prompt 管理**: 提供完整的 CRUD API 用于管理 Prompt 模板。
* **容器化部署**: 使用 Docker 和 Docker Compose 实现一键启动开发环境。
* **数据库集成**: 使用 SQLAlchemy ORM 与 PostgreSQL 数据库进行交互。
* **数据校验**: 使用 Pydantic 进行严格的 API 请求和响应数据校验。
* **热重载**: 开发环境下支持代码热重载，提升开发效率。
* **自动化测试**: 配备 `pytest` 测试套件，确保 API 的稳定性和正确性。

## 🛠️ 技术栈

* **后端框架**: FastAPI
* **数据库**: PostgreSQL 16 (Alpine)
* **ORM**: SQLAlchemy 2.0
* **数据模型**: Pydantic
* **容器化**: Docker
* **服务编排**: Docker Compose
* **依赖管理**: PDM / Pip

## 🚀 本地运行指南

请确保你的机器上已经安装了 Docker 和 Docker Compose (通常随 Docker Desktop 一起安装)。

1. **克隆仓库**

    ```bash
    git clone <your-repository-url>
    cd prompt-management-system
    ```

2. **配置环境变量**
    复制环境变量示例文件，创建一个 `.env` 文件。

    ```bash
    cp .env.example .env
    ```

    *通常情况下，你无需修改 `.env` 文件中的默认值即可在 Docker 环境中运行。*

3. **构建并启动服务**
    在项目根目录运行以下命令：

    ```bash
    docker compose up --build
    ```

    * `--build` 参数会强制 Docker 根据 `Dockerfile` 重新构建 API 镜像。
    * 服务启动后，API 将在 `http://localhost:8002` 上可用。

## 📝 API 端点列表

应用启动后，你可以在 **[http://localhost:8002/docs](http://localhost:8002/docs)** 访问交互式的 Swagger UI 文档。

以下是核心的 API 端点：

### Health Checks

| 方法  | 路径         | 描述                   |
| :---- | :----------- | :--------------------- |
| `GET` | `/health`    | 检查 API 服务是否存活  |
| `GET` | `/db_health` | 检查数据库连接是否正常 |

### Prompt Management

| 方法     | 路径            | 描述                                           |
| :------- | :-------------- | :--------------------------------------------- |
| `POST`   | `/prompts`      | 创建一个新的 Prompt。                          |
| `GET`    | `/prompts`      | 获取 Prompt 列表，支持分页 (`skip`, `limit`)。 |
| `GET`    | `/prompts/{id}` | 根据 ID 获取单个 Prompt 的详细信息。           |
| `PUT`    | `/prompts/{id}` | 根据 ID 更新一个已有的 Prompt。                |
| `DELETE` | `/prompts/{id}` | 根据 ID 删除一个 Prompt。                      |

#### 示例：创建一个 Prompt

**Request:** `POST /prompts`

```json
{
  "title": "市场分析报告生成器",
  "content": "请为我分析 {{product_name}} 在 {{market_sector}} 市场的竞争格局，并生成一份包含优势、劣势、机会和威胁（SWOT分析）的报告。",
  "category": "Marketing"
}
```

**Response:**

```json
{
  "title": "市场分析报告生成器",
  "content": "请为我分析 {{product_name}} 在 {{market_sector}} 市场的竞争格局，并生成一份包含优势、劣势、机会和威胁（SWOT分析）的报告。",
  "category": "Marketing",
  "id": 1,
  "usage_count": 0,
  "created_at": "2025-11-19T12:00:00.000Z",
  "updated_at": "2025-11-19T12:00:00.000Z"
}
```

## ⚙️ 环境变量说明

所有配置项都通过 `.env` 文件管理，由 Pydantic 在 `src/app/config.py` 中加载。

| 变量                | 描述                                                           | 示例值          |
| :------------------ | :------------------------------------------------------------- | :-------------- |
| `POSTGRES_USER`     | PostgreSQL 数据库的用户名。                                    | `myuser`        |
| `POSTGRES_PASSWORD` | PostgreSQL 数据库的密码。                                      | `mypassword123` |
| `POSTGRES_DB`       | 要在 PostgreSQL 中创建或连接的数据库名称。                     | `ai_eng_db`     |
| `POSTGRES_SERVER`   | 数据库服务的主机名。在 Docker Compose 网络中，这应该是服务名。 | `db`            |
| `POSTGRES_PORT`     | 数据库服务监听的端口。                                         | `5432`          |

## ✅ 运行测试

项目包含一套自动化测试，用于验证 API 端点的功能。

1. **确保服务正在运行**:

    ```bash
    docker compose up
    ```

2. **API 健康检查**:
    在终端中运行：

    ```bash
    curl http://localhost:8000/health
    ```

3. **在另一个终端中运行测试脚本**:
    *首先给脚本执行权限（仅需一次）：*

    ```bash
    chmod +x test.sh
    ```

    *然后运行测试：*

    ```bash
    ./test.sh
    ```

    *预期响应:* `...--- ✅ All tests passed successfully! ---

## GitHub Flow 实践 (作业提醒)

在您自己的项目中，请务必遵循 GitHub Flow：

1. `git checkout -b feature/add-new-endpoint`
2. (进行代码修改, e.g., 添加一个新的 `/v1/chat` 端点)
3. `git commit -m "feat: add /v1/chat endpoint"`
4. `git push origin feature/add-new-endpoint`
5. 在 GitHub 上创建 Pull Request (PR) 并合并到 `main`。
