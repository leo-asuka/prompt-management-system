# -----------------
# 阶段 1: 构建 (Build Stage)
# -----------------
# 使用轻量级的 Python 3.11-slim-bookworm 作为基础镜像
FROM python:3.11-slim-bookworm AS builder

# 设置工作目录与最终阶段一致
WORKDIR /home/appuser/app

# 安装 PDM (包管理器)
RUN pip install --upgrade pip
RUN pip install pdm

# (核心优化) 1. 仅拷贝依赖配置文件
COPY pyproject.toml ./

# (核心优化) 2. 安装生产依赖
# --prod: 不安装 dev 依赖
# --no-lock: 依赖已锁定，无需重新生成 lock 文件
# --no-editable: 不使用可编辑模式安装
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
COPY --from=builder /home/appuser/app/.venv ./.venv

# 从 'builder' 阶段拷贝应用源代码
COPY --from=builder /home/appuser/app/src ./src

# 将虚拟环境的 bin 目录添加到 PATH
ENV PATH="/home/appuser/app/.venv/bin:$PATH"

# 暴露 FastAPI 运行的端口
EXPOSE 8000

# 容器启动命令
# CMD ["uvicorn", "src.main.app:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
