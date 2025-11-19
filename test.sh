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

# 设置 PYTEST_OPTS 环境变量，增加 -v (verbose) 和 -s (show prints) 选项
export PYTEST_OPTS="-v -s --verbose"

echo "--- 🚀 Starting API tests against running Docker container ---"
echo "--- Target URL: http://localhost:8002 ---"

# 运行 pytest
# pytest 会自动发现 tests/ 目录下的 test_*.py 文件
# --verbose 参数让输出更详细
# -s 参数可以显示测试函数中的 print() 输出
# 运行 pytest，并将脚本的所有参数 ($@) 传递给 pytest 命令
# 如果没有提供参数，$@ 就是空的，pytest 会像以前一样运行所有测试
# ./test.sh tests/test_users_and_auth.py
pytest --verbose -s "$@"

# 检查 pytest 的退出码
if [ $? -eq 0 ]; then
  echo ""
  echo "--- ✅ All tests passed successfully! ---"
else
  echo ""
  echo "--- ❌ Some tests failed. Please check the output above. ---"
  exit 1
fi

exit 0