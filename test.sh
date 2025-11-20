#!/bin/bash

# ==========================================================
# LLM Prompt Management System - Automated Test Runner
# ==========================================================
#
# 这个脚本会自动运行 pytest 测试套件。
#
# 使用方法:
# 1. 确保你的 Docker Compose 服务正在运行。
#    在第一个终端中执行: docker compose up
#
# 2. 在第二个终端中，给这个脚本执行权限:
#    chmod +x test.sh
#
# 3. 运行此脚本:
#    ./test.sh
#
# ==========================================================

# 统一编码，避免终端输出 emoji 时失败
export PYTHONIOENCODING="utf-8"
# 限定 anyio 仅使用 asyncio 后端
export ANYIO_BACKEND="asyncio"

# 设置 PYTEST_OPTS 环境变量，增加 -v (verbose) 和 -s (show prints) 选项
export PYTEST_OPTS="-v -s"

echo "--- 🚀 Starting Advanced Tests ---"
echo "--- Target URL: http://localhost:8002 ---"

# # 运行 pytest
# # pytest 会自动发现 tests/ 目录下的 test_*.py 文件
# # --verbose 参数让输出更详细
# # -s 参数可以显示测试函数中的 print() 输出
# # 运行 pytest，并将脚本的所有参数 ($@) 传递给 pytest 命令
# # 如果没有提供参数，$@ 就是空的，pytest 会像以前一样运行所有测试
# # ./test.sh tests/test_users_and_auth.py
# pytest --verbose -s "$@"

# # 检查 pytest 的退出码
# if [ $? -eq 0 ]; then
#   echo ""
#   echo "--- ✅ All tests passed successfully! ---"
# else
#   echo ""
#   echo "--- ❌ Some tests failed. Please check the output above. ---"
#   exit 1
# fi

# exit 0

# 1. 运行集成测试 (针对 Docker 容器)
echo "--- 1. Running Integration Tests (against Docker) ---"
# 注意：这里假设 Docker 容器已经启动
pytest tests/test_all_func.py $PYTEST_OPTS
INTEGRATION_EXIT_CODE=$?

# 2. 运行单元测试 & 生成覆盖率报告 (针对本地代码 + 内存数据库)
echo "--- 2. Running Unit Tests & Coverage Report ---"
# --cov=src/app: 统计 src/app 目录的覆盖率
# --cov-report=term-missing: 在终端显示报告，并列出未覆盖的行号
# tests/test_crud_unit.py: 只对单元测试运行覆盖率统计，或者你可以包含所有
pytest --cov=src/app --cov-report=term-missing \
  tests/test_crud_unit.py \
  tests/test_api_unit.py \
  tests/test_cache_unit.py \
  tests/test_database_unit.py \
  tests/test_llm_client_unit.py \
  tests/test_api_extended.py \
  tests/test_all_func.py \
  $PYTEST_OPTS
UNIT_EXIT_CODE=$?

# 检查结果
if [ $INTEGRATION_EXIT_CODE -eq 0 ] && [ $UNIT_EXIT_CODE -eq 0 ]; then
  echo ""
  echo "--- ✅ All tests passed with Coverage Report! ---"
else
  echo ""
  echo "--- ❌ Tests failed. ---"
  exit 1
fi
