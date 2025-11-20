from types import SimpleNamespace

import pytest

from src.app import llm_client


def _fake_completion(content: str, usage: dict):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(model_dump=lambda: usage),
    )


def test_execute_prompt_success(monkeypatch):
    usage = {"total_tokens": 10}
    completion = _fake_completion("Hi there!", usage)
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: completion)
        )
    )
    monkeypatch.setattr(llm_client, "client", fake_client)

    result = llm_client.execute_prompt("Hello {{ name }}", {"name": "Alice"})

    assert result.success is True
    assert result.content == "Hi there!"
    assert result.usage == usage


def test_execute_prompt_handles_template_errors(monkeypatch):
    class BrokenTemplate:
        def __init__(self, *_args, **_kwargs):
            pass

        def render(self, *_args, **_kwargs):
            raise ValueError("template issue")

    monkeypatch.setattr(llm_client, "Template", lambda *_: BrokenTemplate())
    monkeypatch.setattr(llm_client, "client", object())  # ensure client check passes

    result = llm_client.execute_prompt("{{ broken", {})

    assert result.success is False
    assert "Template rendering failed" in result.error


def test_execute_prompt_returns_error_when_client_missing(monkeypatch):
    monkeypatch.setattr(llm_client, "client", None)
    result = llm_client.execute_prompt("Hello", {})
    assert result.success is False
    assert "not initialized" in result.error


@pytest.mark.parametrize(
    "exception_attr, message",
    [
        ("APITimeoutError", "request timed out"),
        ("APIConnectionError", "Failed to connect"),
        ("RateLimitError", "rate limit"),
    ],
)
def test_execute_prompt_handles_known_client_errors(monkeypatch, exception_attr, message):
    class FakeError(Exception):
        pass

    def _raise(*_args, **_kwargs):
        raise FakeError("boom")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_raise))
    )

    monkeypatch.setattr(llm_client, "client", fake_client)
    monkeypatch.setattr(llm_client, exception_attr, FakeError)

    result = llm_client.execute_prompt("Hello {{ name }}", {"name": "Bob"})

    assert result.success is False
    assert message.lower() in result.error.lower()
