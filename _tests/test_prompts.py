# tests/test_prompts.py

import httpx
import pytest

# 你的 FastAPI 应用正在 Docker 容器中运行，并通过 docker-compose.yml 映射到了主机的 8002 端口
BASE_URL = "http://localhost:8002"

# 我们将使用一个字典来在测试函数之间共享状态，例如新建的 prompt_id
test_state = {}


def test_health_check():
    """测试 API 健康检查端点"""
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/health")
        # 断言：检查 HTTP 状态码是否为 200 (OK)
        assert response.status_code == 200
        # 断言：检查返回的 JSON 内容是否符合预期
        assert response.json() == {"status": "ok"}
    print("\n✅ Health check passed!")


def test_db_health_check():
    """测试数据库连接健康检查端点"""
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/db_health")
        # 断言：检查 HTTP 状态码是否为 200 (OK)
        assert response.status_code == 200
        # 断言：检查返回的 JSON 内容是否符合预期
        assert response.json() == {"status": "ok", "database_connection": "successful"}
    print("\n✅ DB health check passed!")


def test_create_prompt():
    """
    测试用例 1: POST /prompts - 创建一个新的 Prompt
    """
    with httpx.Client() as client:
        # 准备要发送的数据
        new_prompt_data = {
            "title": "My Test Prompt",
            "content": "This is the content for the test prompt.",
            "category": "Testing",
        }
        response = client.post(f"{BASE_URL}/prompts", json=new_prompt_data)

        # 断言：检查状态码是否为 201 (Created)
        assert response.status_code == 201

        # 解析返回的 JSON 数据
        data = response.json()

        # 断言：检查返回的数据结构和内容
        assert "id" in data
        assert data["title"] == new_prompt_data["title"]
        assert data["content"] == new_prompt_data["content"]
        assert data["category"] == new_prompt_data["category"]

        # 将新创建的 prompt ID 保存到共享状态中，以便其他测试用例使用
        test_state["prompt_id"] = data["id"]
        print(f"\n✅ Prompt creation test passed! (Created ID: {data['id']})")


@pytest.mark.depends(on=["test_create_prompt"])
def test_get_specific_prompt():
    """
    测试用例 2: GET /prompts/{id} - 获取刚刚创建的 Prompt
    这个测试依赖于 test_create_prompt 成功执行
    """
    # 确保我们已经有了一个 prompt_id
    assert "prompt_id" in test_state, "Create prompt test must run first"
    prompt_id = test_state["prompt_id"]

    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/prompts/{prompt_id}")

        # 断言：检查状态码是否为 200 (OK)
        assert response.status_code == 200

        data = response.json()

        # 断言：返回的数据 ID 是否正确
        assert data["id"] == prompt_id
        assert data["title"] == "My Test Prompt"
        print(f"\n✅ Get specific prompt test passed! (ID: {prompt_id})")


@pytest.mark.depends(on=["test_create_prompt"])
def test_get_prompts_list():
    """
    测试用例 3: GET /prompts - 获取 Prompt 列表，并确认新创建的在其中
    """
    prompt_id = test_state["prompt_id"]

    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/prompts")

        # 断言：状态码为 200 (OK)
        assert response.status_code == 200

        data = response.json()

        # 断言：返回的数据结构正确
        assert "total" in data
        assert "prompts" in data
        assert isinstance(data["prompts"], list)

        # 确认列表不为空，并且我们创建的 prompt 在列表中
        assert data["total"] > 0
        ids_in_list = [p["id"] for p in data["prompts"]]
        assert prompt_id in ids_in_list
        print("\n✅ Get prompts list test passed!")


@pytest.mark.depends(on=["test_create_prompt"])
def test_update_prompt():
    """
    (推荐) 测试用例 4: PUT /prompts/{id} - 更新 Prompt
    """
    prompt_id = test_state["prompt_id"]
    update_data = {
        "title": "My Updated Test Prompt",
        "content": "This is the updated content.",
        "category": "Updated Testing",
    }

    with httpx.Client() as client:
        response = client.put(f"{BASE_URL}/prompts/{prompt_id}", json=update_data)

        # 断言：状态码为 200 (OK)
        assert response.status_code == 200

        data = response.json()

        # 断言：返回的数据已被更新
        assert data["id"] == prompt_id
        assert data["title"] == update_data["title"]
        assert data["content"] == update_data["content"]
        assert data["category"] == update_data["category"]
        print(f"\n✅ Update prompt test passed! (ID: {prompt_id})")


@pytest.mark.depends(on=["test_update_prompt"])
def test_delete_prompt():
    """
    (推荐) 测试用例 5: DELETE /prompts/{id} - 删除 Prompt 并验证
    """
    prompt_id = test_state["prompt_id"]

    with httpx.Client() as client:
        # 第一步：删除
        delete_response = client.delete(f"{BASE_URL}/prompts/{prompt_id}")

        # 断言：删除操作返回 204 (No Content)
        assert delete_response.status_code == 204

        # 第二步：验证删除
        # 再次请求该 ID，应该返回 404 (Not Found)
        verify_response = client.get(f"{BASE_URL}/prompts/{prompt_id}")
        assert verify_response.status_code == 404

        print(f"\n✅ Delete and verify prompt test passed! (ID: {prompt_id})")
