from types import SimpleNamespace

import pytest

from src.app import main


def _create_user(client, username: str):
    response = client.post("/users", json={"username": username, "password": "secret1"})
    assert response.status_code == 201
    return response.json()


def _create_prompt(client, owner_id: int, title="Title", content="Content"):
    headers = {"X-User-ID": str(owner_id)}
    response = client.post("/prompts", json={"title": title, "content": content}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_rating_endpoints_flow(client_with_db):
    client = client_with_db
    owner = _create_user(client, "rating-owner")
    critic = _create_user(client, "rating-critic")
    prompt = _create_prompt(client, owner["id"])

    critic_headers = {"X-User-ID": str(critic["id"])}
    rate_resp = client.post(
        f"/prompts/{prompt['id']}/ratings",
        json={"score": 4},
        headers=critic_headers,
    )
    assert rate_resp.status_code == 201
    assert rate_resp.json()["score"] == 4

    duplicate = client.post(
        f"/prompts/{prompt['id']}/ratings",
        json={"score": 5},
        headers=critic_headers,
    )
    assert duplicate.status_code == 409

    owner_headers = {"X-User-ID": str(owner["id"])}
    owner_attempt = client.post(
        f"/prompts/{prompt['id']}/ratings",
        json={"score": 5},
        headers=owner_headers,
    )
    assert owner_attempt.status_code == 403

    list_resp = client.get(f"/prompts/{prompt['id']}/ratings")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_tag_management_and_association(client_with_db):
    client = client_with_db
    owner = _create_user(client, "tag-owner")
    prompt = _create_prompt(client, owner["id"])
    headers = {"X-User-ID": str(owner["id"])}

    tag_resp = client.post("/tags", json={"name": "productivity"}, headers=headers)
    assert tag_resp.status_code == 201
    tag_id = tag_resp.json()["id"]

    list_resp = client.get("/tags")
    assert list_resp.status_code == 200
    assert any(tag["name"] == "productivity" for tag in list_resp.json())

    add_resp = client.post(f"/prompts/{prompt['id']}/tags/{tag_id}", headers=headers)
    assert add_resp.status_code == 200
    assert any(tag["id"] == tag_id for tag in add_resp.json()["tags"])

    remove_resp = client.delete(f"/prompts/{prompt['id']}/tags/{tag_id}", headers=headers)
    assert remove_resp.status_code == 200
    assert remove_resp.json()["tags"] == []


def test_versions_execution_and_user_prompt_listing(client_with_db, monkeypatch):
    client = client_with_db
    owner = _create_user(client, "version-owner")
    headers = {"X-User-ID": str(owner["id"])}
    prompt = _create_prompt(client, owner["id"], title="Legacy Title", content="Original content")

    update_resp = client.put(
        f"/prompts/{prompt['id']}",
        json={"title": "New Title"},
        headers=headers,
    )
    assert update_resp.status_code == 200

    versions_resp = client.get(f"/prompts/{prompt['id']}/versions", headers=headers)
    assert versions_resp.status_code == 200
    assert len(versions_resp.json()) >= 2

    version_one = client.get(
        f"/prompts/{prompt['id']}/versions/1",
        headers=headers,
    )
    assert version_one.status_code == 200
    assert version_one.json()["title"] == "Legacy Title"

    rollback = client.post(
        f"/prompts/{prompt['id']}/rollback/1",
        headers=headers,
    )
    assert rollback.status_code == 200
    assert rollback.json()["title"] == "Legacy Title"

    fake_result = SimpleNamespace(
        success=True,
        content="Ok",
        usage={"total_tokens": 3},
        error=None,
    )

    def _fake_execute_prompt(prompt_content, variables):
        return fake_result

    monkeypatch.setattr(main, "execute_prompt", _fake_execute_prompt)

    exec_resp = client.post(
        f"/prompts/{prompt['id']}/execute",
        json={"variables": {}},
        headers=headers,
    )
    assert exec_resp.status_code == 200
    assert exec_resp.json()["response_text"] == "Ok"

    history = client.get(
        f"/prompts/{prompt['id']}/executions",
        headers=headers,
    )
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["token_usage"]["total_tokens"] == 3

    user_prompts = client.get(f"/users/{owner['id']}/prompts")
    assert user_prompts.status_code == 200
    assert len(user_prompts.json()) >= 1
