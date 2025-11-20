# tests/test_tags.py

import httpx
import pytest

BASE_URL = "http://localhost:8002"

# 共享状态，用于在测试用例之间传递数据
test_state = {}


# === 辅助函数：用于创建用户和 Prompt，减少重复代码 ===
def create_user(username, password):
    with httpx.Client() as client:
        response = client.post(
            f"{BASE_URL}/users", json={"username": username, "password": password}
        )
        assert response.status_code == 201
        return response.json()


def create_prompt(user_id, title, content):
    with httpx.Client() as client:
        headers = {"X-User-ID": str(user_id)}
        response = client.post(
            f"{BASE_URL}/prompts",
            json={"title": title, "content": content, "category": "Testing"},
            headers=headers,
        )
        assert response.status_code == 201
        return response.json()


# === 测试设置：创建两个用户和一些 Prompts ===
@pytest.fixture(scope="module", autouse=True)
def setup_users_and_prompts():
    """在所有测试开始前运行一次，准备基础数据"""
    print("\n--- Setting up initial data for tag tests ---")
    user_charlie = create_user("charlie", "pass123")
    user_diana = create_user("diana", "pass456")

    test_state["user_charlie_id"] = user_charlie["id"]
    test_state["user_diana_id"] = user_diana["id"]

    prompt1 = create_prompt(
        user_charlie["id"], "Charlie's Marketing Prompt", "Content for marketing."
    )
    prompt2 = create_prompt(
        user_charlie["id"], "Charlie's Sales Prompt", "Content for sales."
    )
    prompt3 = create_prompt(
        user_diana["id"], "Diana's Engineering Prompt", "Content for engineering."
    )

    test_state["charlie_prompt1_id"] = prompt1["id"]
    test_state["charlie_prompt2_id"] = prompt2["id"]
    test_state["diana_prompt3_id"] = prompt3["id"]
    print("--- Initial data setup complete ---")


# === 正式测试用例 ===


def test_1_create_tags():
    """测试创建新标签"""
    user_id = test_state["user_charlie_id"]
    headers = {"X-User-ID": str(user_id)}

    with httpx.Client() as client:
        # 创建 marketing 标签
        response = client.post(
            f"{BASE_URL}/tags", json={"name": "marketing"}, headers=headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "marketing"
        test_state["tag_marketing_id"] = data["id"]

        # 创建 sales 标签
        response = client.post(
            f"{BASE_URL}/tags", json={"name": "sales"}, headers=headers
        )
        assert response.status_code == 201
        test_state["tag_sales_id"] = response.json()["id"]

        # 创建 engineering 标签
        response = client.post(
            f"{BASE_URL}/tags", json={"name": "engineering"}, headers=headers
        )
        assert response.status_code == 201
        test_state["tag_engineering_id"] = response.json()["id"]

    print("\n✅ Created tags: marketing, sales, engineering")


def test_2_create_duplicate_tag():
    """测试创建同名标签，应该失败"""
    user_id = test_state["user_charlie_id"]
    headers = {"X-User-ID": str(user_id)}
    with httpx.Client() as client:
        response = client.post(
            f"{BASE_URL}/tags", json={"name": "marketing"}, headers=headers
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    print("\n✅ Duplicate tag creation failed as expected")


@pytest.mark.depends(on=["test_1_create_tags"])
def test_3_add_tags_to_prompt():
    """测试为 Prompt 添加标签"""
    user_id = test_state["user_charlie_id"]
    headers = {"X-User-ID": str(user_id)}
    prompt_id = test_state["charlie_prompt1_id"]
    tag_id = test_state["tag_marketing_id"]

    with httpx.Client() as client:
        # 为 Charlie 的 prompt 1 添加 marketing 标签
        response = client.post(
            f"{BASE_URL}/prompts/{prompt_id}/tags/{tag_id}", headers=headers
        )
        assert response.status_code == 200
        data = response.json()

        # 验证返回的 prompt 数据中包含了 marketing 标签
        tag_names = [tag["name"] for tag in data["tags"]]
        assert "marketing" in tag_names
        assert len(data["tags"]) == 1

    print(f"\n✅ Added 'marketing' tag to prompt {prompt_id}")


@pytest.mark.depends(on=["test_3_add_tags_to_prompt"])
def test_4_diana_cannot_add_tag_to_charlies_prompt():
    """权限测试：Diana 尝试为 Charlie 的 Prompt 添加标签，应该失败"""
    diana_id = test_state["user_diana_id"]
    headers = {"X-User-ID": str(diana_id)}
    prompt_id = test_state["charlie_prompt1_id"]  # Charlie's prompt
    tag_id = test_state["tag_sales_id"]

    with httpx.Client() as client:
        response = client.post(
            f"{BASE_URL}/prompts/{prompt_id}/tags/{tag_id}", headers=headers
        )
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]

    print("\n✅ Diana was correctly forbidden from modifying Charlie's prompt tags")


@pytest.mark.depends(on=["test_3_add_tags_to_prompt"])
def test_5_list_prompts_by_tag():
    """测试按标签筛选 Prompt 列表"""
    with httpx.Client() as client:
        # 筛选包含 marketing 标签的 prompts
        response = client.get(f"{BASE_URL}/prompts?tags=marketing")
        assert response.status_code == 200
        data = response.json()

        # 应该只返回一个结果 (charlie_prompt1)
        assert data["total"] == 1
        assert data["prompts"][0]["id"] == test_state["charlie_prompt1_id"]
        assert data["prompts"][0]["title"] == "Charlie's Marketing Prompt"

    print("\n✅ Successfully filtered prompts by tag 'marketing'")


@pytest.mark.depends(on=["test_5_list_prompts_by_tag"])
def test_6_list_prompts_by_multiple_tags():
    """测试按多个标签筛选（目前我们的逻辑是 AND，所以应该返回 0）"""
    with httpx.Client() as client:
        # 筛选同时包含 marketing 和 sales 的 prompts
        response = client.get(f"{BASE_URL}/prompts?tags=marketing,sales")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0  # 因为还没有 prompt 同时拥有这两个标签

    # 现在，我们给 Charlie's Prompt 1 再加上 sales 标签
    user_id = test_state["user_charlie_id"]
    headers = {"X-User-ID": str(user_id)}
    prompt_id = test_state["charlie_prompt1_id"]
    tag_id = test_state["tag_sales_id"]
    with httpx.Client() as client:
        client.post(f"{BASE_URL}/prompts/{prompt_id}/tags/{tag_id}", headers=headers)

    # 再次筛选
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/prompts?tags=marketing,sales")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # 现在应该有了
        assert data["prompts"][0]["id"] == test_state["charlie_prompt1_id"]

    print("\n✅ Successfully filtered prompts by multiple tags 'marketing,sales'")


@pytest.mark.depends(on=["test_6_list_prompts_by_multiple_tags"])
def test_7_remove_tag_from_prompt():
    """测试从 Prompt 移除标签"""
    user_id = test_state["user_charlie_id"]
    headers = {"X-User-ID": str(user_id)}
    prompt_id = test_state["charlie_prompt1_id"]
    tag_id = test_state["tag_marketing_id"]

    with httpx.Client() as client:
        response = client.delete(
            f"{BASE_URL}/prompts/{prompt_id}/tags/{tag_id}", headers=headers
        )
        assert response.status_code == 200
        data = response.json()

        # 验证返回的数据中已经没有 marketing 标签了，但应该还有 sales 标签
        tag_names = [tag["name"] for tag in data["tags"]]
        assert "marketing" not in tag_names
        assert "sales" in tag_names
        assert len(data["tags"]) == 1

    print(f"\n✅ Successfully removed 'marketing' tag from prompt {prompt_id}")
