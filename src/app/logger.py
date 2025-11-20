# src/app/logger.py
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """配置结构化日志"""
    logger = logging.getLogger()
    
    # 如果已经配置过（防止重复添加 handler），直接返回
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # 创建控制台 Handler
    handler = logging.StreamHandler(sys.stdout)
    
    # 定义 JSON 格式
    # 这里定义了日志中包含哪些字段
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(filename)s %(lineno)d"
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

# 初始化并导出一个单例 logger
logger = setup_logging()