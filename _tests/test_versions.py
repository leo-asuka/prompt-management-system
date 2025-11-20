# tests/test_versions.py

import httpx
import pytest

BASE_URL = "http://localhost:8002"
test_state = {}


# === 辅助函数 ===
def create_user(username, password):
    with httpx.Client() as client:
        res = client.post(
            f"{BASE_URL}/users", json={"username": username, "password": password}
        )
        # 如果用户已存在，忽略错误（为了方便重复运行测试调试）
        if res.status_code == 400:
            # 尝试登录或获取现有用户ID的逻辑在这里省略，直接假设测试环境是干净的
            pass
        return res.json()


# === 测试设置 ===
@pytest.fixture(scope="module", autouse=True)
def setup_for_version_tests():
    print("\n--- Setting up data for versioning tests ---")
    # 创建一个用户 Kevin
    user = create_user("kevin_v", "password123")
    test_state["user_id"] = user["id"]
    print("--- Versioning tests setup complete ---")


# === 测试用例 ===


def test_1_create_prompt_creates_v1():
    """测试：创建 Prompt 时，应该自动创建版本 1"""
    user_id = test_state["user_id"]
    headers = {"X-User-ID": str(user_id)}

    payload = {
        "title": "Original Idea",
        "content": "This is version 1 content.",
        "category": "Idea",
    }

    with httpx.Client() as client:
        # 1. 创建 Prompt
        res = client.post(f"{BASE_URL}/prompts", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        prompt_id = data["id"]
        test_state["prompt_id"] = prompt_id

        # 2. 检查版本历史
        ver_res = client.get(
            f"{BASE_URL}/prompts/{prompt_id}/versions", headers=headers
        )
        assert ver_res.status_code == 200
        versions = ver_res.json()

        # 断言：应该只有 1 个版本，且版本号为 1
        assert len(versions) == 1
        assert versions[0]["version_number"] == 1
        assert versions[0]["title"] == "Original Idea"
        assert versions[0]["content"] == "This is version 1 content."

    print("\n✅ Initial prompt creation correctly generated Version 1")


@pytest.mark.depends(on=["test_1_create_prompt_creates_v1"])
def test_2_update_prompt_creates_v2():
    """测试：更新 Prompt 时，应该自动创建版本 2"""
    user_id = test_state["user_id"]
    prompt_id = test_state["prompt_id"]
    headers = {"X-User-ID": str(user_id)}

    update_payload = {
        "title": "Improved Idea",
        "content": "This is version 2 content (better).",
    }

    with httpx.Client() as client:
        # 1. 更新 Prompt
        res = client.put(
            f"{BASE_URL}/prompts/{prompt_id}", json=update_payload, headers=headers
        )
        assert res.status_code == 200

        # 2. 检查 Prompt 当前状态
        current_prompt = res.json()
        assert current_prompt["title"] == "Improved Idea"

        # 3. 检查版本历史
        ver_res = client.get(
            f"{BASE_URL}/prompts/{prompt_id}/versions", headers=headers
        )
        versions = ver_res.json()

        # 断言：现在应该有 2 个版本
        assert len(versions) == 2
        # 列表默认按版本倒序排列（最新的在最前）
        assert versions[0]["version_number"] == 2
        assert versions[0]["title"] == "Improved Idea"

        assert versions[1]["version_number"] == 1
        assert versions[1]["title"] == "Original Idea"

    print("\n✅ Updating prompt correctly generated Version 2")


@pytest.mark.depends(on=["test_2_update_prompt_creates_v2"])
def test_3_get_specific_version():
    """测试：获取特定版本的详情"""
    user_id = test_state["user_id"]
    prompt_id = test_state["prompt_id"]
    headers = {"X-User-ID": str(user_id)}

    with httpx.Client() as client:
        # 获取版本 1
        res = client.get(f"{BASE_URL}/prompts/{prompt_id}/versions/1", headers=headers)
        assert res.status_code == 200
        v1 = res.json()
        assert v1["version_number"] == 1
        assert v1["content"] == "This is version 1 content."

    print("\n✅ Successfully retrieved specific version details")


@pytest.mark.depends(on=["test_2_update_prompt_creates_v2"])
def test_4_rollback_to_v1():
    """测试：回滚到版本 1"""
    user_id = test_state["user_id"]
    prompt_id = test_state["prompt_id"]
    headers = {"X-User-ID": str(user_id)}

    # 我们要回滚到版本 1 ("Original Idea")
    target_version = 1

    with httpx.Client() as client:
        # 1. 执行回滚
        # 注意：回滚逻辑本质上是一次更新，所以它会生成版本 3，内容与版本 1 相同
        res = client.post(
            f"{BASE_URL}/prompts/{prompt_id}/rollback/{target_version}", headers=headers
        )
        assert res.status_code == 200
        rolled_back_prompt = res.json()

        # 2. 验证当前 Prompt 内容是否变回了 v1 的内容
        assert rolled_back_prompt["title"] == "Original Idea"
        assert rolled_back_prompt["content"] == "This is version 1 content."

        # 3. 验证版本历史
        ver_res = client.get(
            f"{BASE_URL}/prompts/{prompt_id}/versions", headers=headers
        )
        versions = ver_res.json()

        # 断言：现在应该有 3 个版本
        # v3 (rollback to v1), v2 (improved), v1 (original)
        assert len(versions) == 3
        assert versions[0]["version_number"] == 3
        assert versions[0]["title"] == "Original Idea"  # v3 的内容等于 v1

    print("\n✅ Successfully rolled back to Version 1 (created Version 3)")
