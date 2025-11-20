# src/app/cache.py
import redis
from .config import settings
from . import schemas

# 初始化 Redis 客户端
# decode_responses=True 让 redis 直接返回字符串而不是 bytes
r = redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_prompt_cache(prompt_id: int):
    """尝试从缓存获取 Prompt"""
    try:
        key = f"prompt:{prompt_id}"
        data = r.get(key)
        if data:
            # 反序列化：将 JSON 字符串转回 Pydantic 对象
            return schemas.PromptResponse.model_validate_json(data)
    except Exception as e:
        print(f"Redis read error: {e}")
    return None


def set_prompt_cache(prompt: schemas.PromptResponse, ttl: int = 300):
    """
    将 Prompt 写入缓存
    ttl: 过期时间，默认 300 秒 (5分钟)
    """
    try:
        key = f"prompt:{prompt.id}"
        # 序列化：将 Pydantic 对象转为 JSON 字符串
        json_data = prompt.model_dump_json()
        r.set(key, json_data, ex=ttl)
    except Exception as e:
        print(f"Redis write error: {e}")


def delete_prompt_cache(prompt_id: int):
    """删除缓存 (用于更新或删除时失效缓存)"""
    try:
        key = f"prompt:{prompt_id}"
        r.delete(key)
    except Exception as e:
        print(f"Redis delete error: {e}")
