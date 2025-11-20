from datetime import datetime

from src.app import cache, schemas


class _FakeRedis:
    def __init__(self):
        self.store = {}
        self.deleted = set()

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value

    def delete(self, key):
        self.deleted.add(key)
        self.store.pop(key, None)


def _build_prompt_response(prompt_id: int = 1) -> schemas.PromptResponse:
    now = datetime.utcnow()
    owner = schemas.UserResponse(
        id=prompt_id, username=f"user-{prompt_id}", created_at=now
    )
    return schemas.PromptResponse(
        id=prompt_id,
        title=f"Prompt {prompt_id}",
        content="Hello world",
        category=None,
        usage_count=0,
        created_at=now,
        updated_at=now,
        owner=owner,
        tags=[],
        average_rating=None,
    )


def test_set_get_delete_prompt_cache(monkeypatch):
    fake_redis = _FakeRedis()
    monkeypatch.setattr(cache, "r", fake_redis)
    prompt = _build_prompt_response()

    cache.set_prompt_cache(prompt, ttl=10)
    assert f"prompt:{prompt.id}" in fake_redis.store

    cached = cache.get_prompt_cache(prompt.id)
    assert cached is not None
    assert cached.id == prompt.id
    assert cached.owner.username == prompt.owner.username

    cache.delete_prompt_cache(prompt.id)
    assert f"prompt:{prompt.id}" not in fake_redis.store
    assert f"prompt:{prompt.id}" in fake_redis.deleted


def test_cache_helpers_safely_handle_exceptions(monkeypatch):
    class _ErrorRedis:
        def get(self, key):
            raise RuntimeError("boom")

        def set(self, key, value, ex=None):
            raise RuntimeError("boom")

        def delete(self, key):
            raise RuntimeError("boom")

    monkeypatch.setattr(cache, "r", _ErrorRedis())
    prompt = _build_prompt_response(2)

    assert cache.get_prompt_cache(prompt.id) is None
    # These should not raise even though Redis fails under the hood
    cache.set_prompt_cache(prompt)
    cache.delete_prompt_cache(prompt.id)
