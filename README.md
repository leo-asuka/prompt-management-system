# LLM Prompt 管理系统

![CI Status](https://github.com/leo-asuka/prompt-management-system/actions/workflows/test.yml/badge.svg)
![Coverage](https://img.shields.io/badge/Coverage-89%25-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688)

基于 FastAPI + PostgreSQL + Redis 的 Prompt 管理后端，支持提示词的创建、模板化执行、评分、版本管理与标签体系，并内置 LLM 调用、缓存、日志与监控。项目通过 Docker Compose 一键拉起（含 Postgres / Redis / Prometheus），配套完善的 pytest 用例与 CI 流水线，便于在课程作业或个人项目中直接复用。

## 功能亮点

- 提示词全流程：CRUD、分页检索、按标签过滤、按评分排序，记录平均分与使用次数
- LLM 执行链路：Jinja2 变量替换 + OpenAI Chat 接口（可配 `base_url`），自动落库执行记录与 token 计数
- 用户与权限：`X-User-ID` 请求头标识用户；仅作者可改/删/打标签/回滚，其余受限；用户可查看自己的 prompts
- 标签体系：独立标签管理，提示词-标签多对多绑定与解绑
- 评分系统：用户对他人提示词单次评分，自动计算平均分并支持按评分排序
- 版本管理：更新即生成新版本，提供版本列表、单版详情与回滚（回滚会产生新版本）
- 缓存与性能：Redis 缓存热门提示词详情（默认 5 分钟），更新/删除自动失效；核心字段建索引
- 观测性：JSON 结构化请求日志中间件；`/metrics` 暴露 Prometheus 指标，Prometheus 服务默认挂载在 9090
- 测试与 CI：集成/单测覆盖主要模块，`./test.sh` 汇总运行，GitHub Actions 自动执行 lint + pytest + 覆盖率（当前约 89%）

## 技术栈

- 后端框架：FastAPI、Pydantic v2、SQLAlchemy 2.0
- 数据与缓存：PostgreSQL 16 (Alpine)、Redis
- LLM：OpenAI SDK（默认 `gpt-3.5-turbo`，支持自定义 `base_url`）
- 运维：Docker / Docker Compose、Prometheus、python-json-logger
- 质量保障：pytest、pytest-cov、flake8、black、GitHub Actions

## 快速开始（Docker Compose）

1) **前置：安装 Docker / Docker Compose**
2) **克隆仓库**

    ```bash
    git clone https://github.com/leo-asuka/prompt-management-system
    ```

3) **复制环境变量并填写 OpenAI Key（可用自定义代理 `base_url`）**

    ```bash
    cd prompt-management-system
    cp .env.example .env
    # 编辑 .env，填入 OPENAI_API_KEY，如无 Key 仍可调用接口但 LLM 返回失败提示
    ```

    *通常情况下，你无需修改 `.env` 文件中的默认值即可在 Docker 环境中运行。*

4) **构建并启动**

    ```bash
    docker compose up --build
    ```

5) **访问**

- API 基础地址：`http://localhost:8002`
- Swagger 文档：`http://localhost:8002/docs`
- Prometheus 指标：`http://localhost:8002/metrics`
- Prometheus UI：`http://localhost:9090`

## 简易认证与用户创建

- 认证方式：在需要认证的接口头部携带 `X-User-ID: <用户ID>`。创建、更新、删除、打标签、执行、评分、回滚等均需该头。
- 创建用户

```bash
curl -X POST http://localhost:8002/users \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo123"}'
# 返回的 id 即为后续请求的 X-User-ID
```

## 运行测试

```bash
chmod +x test.sh
# 先确保 docker compose 已启动（Postgres/Redis 就绪）
./test.sh
```

- 脚本包含：对运行中容器的集成测试 + 覆盖率统计的单元/扩展测试。全部通过后会输出 “All tests passed with Coverage Report!”。

## API 端点速览

**健康与监控**  

- `GET /` 欢迎页
- `GET /health` 服务健康检查
- `GET /db_health` 数据库连通性检查
- `GET /metrics` Prometheus 指标

**用户**  

- `POST /users` 创建用户
- `GET /users/{user_id}/prompts` 查看用户的提示词

**提示词**  

- `POST /prompts` 创建（需 `X-User-ID`）
- `GET /prompts` 列表，参数：`skip`/`limit`、`tags=tag1,tag2`、`sort=rating`
- `GET /prompts/{id}` 详情（带平均评分，命中缓存时从 Redis 读取）
- `PUT /prompts/{id}` 更新并生成新版本（仅作者）
- `DELETE /prompts/{id}` 删除（仅作者）

**标签**  

- `POST /tags` 创建标签（需认证，去重）
- `GET /tags` 标签列表
- `POST /prompts/{id}/tags/{tag_id}` 绑定标签（仅作者）
- `DELETE /prompts/{id}/tags/{tag_id}` 解绑标签（仅作者）

**执行与历史**  

- `POST /prompts/{id}/execute` 执行 LLM（需认证），请求体示例：

```json
{ "variables": { "product_name": "智能耳机", "market_sector": "消费电子" } }
```

- `GET /prompts/{id}/executions` 查看执行历史（含 token 使用、错误信息）

**评分**  

- `POST /prompts/{id}/ratings` 为他人提示词评分（1-5 分，单用户单提示词仅一次）
- `GET /prompts/{id}/ratings` 查看评分列表

**版本管理**  

- `GET /prompts/{id}/versions` 版本列表
- `GET /prompts/{id}/versions/{version}` 查看指定版本
- `POST /prompts/{id}/rollback/{version}` 回滚到旧版本（会生成新版本，需作者权限）

## 环境变量

所有配置项都通过 `.env` 文件管理，由 Pydantic 在 `src/app/config.py` 中加载。

| 变量                | 说明                               | 示例                   |
| ------------------- | ---------------------------------- | ---------------------- |
| `POSTGRES_USER`     | Postgres 用户名                    | `myuser`               |
| `POSTGRES_PASSWORD` | Postgres 密码                      | `mypassword123`        |
| `POSTGRES_SERVER`   | 数据库主机（Compose 内使用服务名） | `db`                   |
| `POSTGRES_PORT`     | 数据库端口                         | `5432`                 |
| `POSTGRES_DB`       | 数据库名称                         | `ai_eng_db`            |
| `OPENAI_API_KEY`    | OpenAI Key（可用代理或直连）       | `sk-xxxx`              |
| `REDIS_URL`         | Redis 连接串                       | `redis://redis:6379/0` |

## 进阶功能完成度（对应作业选项）

- 选项 1：用户与权限 ✅ 简易认证头、作者权限校验、用户维度查询
- 选项 2：标签系统 ✅ 标签 CRUD、提示词打标/解绑、按标签过滤
- 选项 3：LLM API 集成 ✅ Jinja2 模板替换 + OpenAI Chat 调用 + 执行历史/用量记录
- 选项 4：评分系统 ✅ 唯一评分约束、平均分计算、按评分排序
- 选项 5：Prompt 版本管理 ✅ 自动版本快照、版本查询、回滚生成新版本
- 选项 6：性能优化与缓存 ✅ Redis 缓存提示词详情、更新/删除失效、核心索引；（未实现：游标分页）
- 选项 7：高级测试 ✅ 覆盖率 ~89%，涵盖 CRUD/LLM/缓存/数据库/性能
- 选项 8：CI/CD ✅ GitHub Actions 持续集成，包含 black/flake8 + docker-compose + pytest + 覆盖率
- 选项 9：监控与日志 ✅ JSON 请求日志中间件、关键操作打点、Prometheus 指标暴露及配置模板
- 选项 10：自定义功能 暂未添加，可按需扩展（如 Prompt Chain、推荐等）

## GitHub Flow 实践

在您自己的项目中，请务必遵循 GitHub Flow：

1. `git checkout -b feature/add-new-endpoint`
2. (进行代码修改, e.g., 添加一个新的 `/v1/chat` 端点)
3. `git commit -m "feat: add /v1/chat endpoint"`
4. `git push origin feature/add-new-endpoint`
5. 在 GitHub 上创建 Pull Request (PR) 并合并到 `main`。
