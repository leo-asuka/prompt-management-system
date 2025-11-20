# tests/test_users_and_auth.py

import httpx
import pytest

BASE_URL = "http://localhost:8002"

# 用于在测试用例之间共享状态
test_state = {}


def test_1_create_user_alice():
    """测试创建第一个用户 Alice"""
    with httpx.Client() as client:
        user_data = {"username": "alice", "password": "password123"}
        response = client.post(f"{BASE_URL}/users", json=user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "alice"
        assert "id" in data
        test_state["user_alice_id"] = data["id"]
        print(f"\n✅ Created user Alice with ID: {data['id']}")


def test_2_create_user_bob():
    """测试创建第二个用户 Bob"""
    with httpx.Client() as client:
        user_data = {"username": "bob", "password": "password456"}
        response = client.post(f"{BASE_URL}/users", json=user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "bob"
        test_state["user_bob_id"] = data["id"]
        print(f"\n✅ Created user Bob with ID: {data['id']}")


def test_3_create_duplicate_user():
    """测试创建同名用户，应该会失败"""
    with httpx.Client() as client:
        user_data = {"username": "alice", "password": "anotherpassword"}
        response = client.post(f"{BASE_URL}/users", json=user_data)
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]
        print("\n✅ Duplicate user creation failed as expected")


@pytest.mark.depends(on=["test_1_create_user_alice"])
def test_4_alice_creates_a_prompt():
    """测试 Alice 创建一个属于她自己的 Prompt"""
    with httpx.Client() as client:
        prompt_data = {
            "title": "Alice's Great Idea",
            "content": "A prompt created by Alice.",
            "category": "Personal",
        }
        # 关键：在请求头中表明身份
        headers = {"X-User-ID": str(test_state["user_alice_id"])}
        response = client.post(f"{BASE_URL}/prompts", json=prompt_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Alice's Great Idea"
        # 验证返回的数据中，所有者信息是 Alice
        assert data["owner"]["id"] == test_state["user_alice_id"]
        assert data["owner"]["username"] == "alice"

        test_state["alice_prompt_id"] = data["id"]
        print(f"\n✅ Alice created her prompt with ID: {data['id']}")


@pytest.mark.depends(on=["test_2_create_user_bob", "test_4_alice_creates_a_prompt"])
def test_5_bob_cannot_update_alices_prompt():
    """核心权限测试：Bob 尝试更新 Alice 的 Prompt，应该失败"""
    with httpx.Client() as client:
        update_data = {"title": "Bob's Attempted Takeover"}

        # 关键：Bob 在请求头中表明自己的身份
        headers = {"X-User-ID": str(test_state["user_bob_id"])}
        prompt_id = test_state["alice_prompt_id"]

        response = client.put(
            f"{BASE_URL}/prompts/{prompt_id}", json=update_data, headers=headers
        )

        # 应该返回 403 Forbidden
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]
        print("\n✅ Bob was correctly forbidden from updating Alice's prompt")


@pytest.mark.depends(on=["test_4_alice_creates_a_prompt"])
def test_6_alice_can_update_her_own_prompt():
    """核心权限测试：Alice 尝试更新自己的 Prompt，应该成功"""
    with httpx.Client() as client:
        update_data = {"title": "Alice's Updated Idea", "category": "Professional"}

        headers = {"X-User-ID": str(test_state["user_alice_id"])}
        prompt_id = test_state["alice_prompt_id"]

        response = client.put(
            f"{BASE_URL}/prompts/{prompt_id}", json=update_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Alice's Updated Idea"
        assert data["category"] == "Professional"
        print("\n✅ Alice successfully updated her own prompt")


@pytest.mark.depends(on=["test_2_create_user_bob", "test_4_alice_creates_a_prompt"])
def test_7_bob_cannot_delete_alices_prompt():
    """核心权限测试：Bob 尝试删除 Alice 的 Prompt，应该失败"""
    with httpx.Client() as client:
        headers = {"X-User-ID": str(test_state["user_bob_id"])}
        prompt_id = test_state["alice_prompt_id"]

        response = client.delete(f"{BASE_URL}/prompts/{prompt_id}", headers=headers)

        assert response.status_code == 403
        print("\n✅ Bob was correctly forbidden from deleting Alice's prompt")

        # 额外验证：Alice 的 prompt 应该还在
        verify_response = client.get(f"{BASE_URL}/prompts/{prompt_id}")
        assert verify_response.status_code == 200


@pytest.mark.depends(on=["test_6_alice_can_update_her_own_prompt"])
def test_8_alice_can_delete_her_own_prompt():
    """核心权限测试：Alice 删除自己的 Prompt，应该成功"""
    with httpx.Client() as client:
        headers = {"X-User-ID": str(test_state["user_alice_id"])}
        prompt_id = test_state["alice_prompt_id"]

        response = client.delete(f"{BASE_URL}/prompts/{prompt_id}", headers=headers)
        assert response.status_code == 204

        # 额外验证：Prompt 确实被删除了
        verify_response = client.get(f"{BASE_URL}/prompts/{prompt_id}")
        assert verify_response.status_code == 404
        print("\n✅ Alice successfully deleted her own prompt")
