# tests/test_llm_integration.py

import httpx
import pytest
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量，特别是 OPENAI_API_KEY
load_dotenv()

BASE_URL = "http://localhost:8002"

# 共享状态
test_state = {}


# === 辅助函数 ===
def create_user_for_llm(username, password):
    with httpx.Client() as client:
        response = client.post(
            f"{BASE_URL}/users", json={"username": username, "password": password}
        )
        assert response.status_code == 201
        return response.json()


def create_prompt_for_llm(user_id, title, content):
    with httpx.Client() as client:
        headers = {"X-User-ID": str(user_id)}
        response = client.post(
            f"{BASE_URL}/prompts",
            json={"title": title, "content": content},
            headers=headers,
        )
        assert response.status_code == 201
        return response.json()


# === 测试设置 ===
@pytest.fixture(scope="module", autouse=True)
def setup_for_llm_tests():
    print("\n--- Setting up data for REAL LLM integration tests ---")
    user_frank = create_user_for_llm("frank_real", "pass_real_123")
    test_state["user_frank_id"] = user_frank["id"]

    prompt_template = "In one short sentence, what is the core concept of the theory" \
    " of relativity? Answer in the persona of a pirate."
    prompt = create_prompt_for_llm(
        user_frank["id"], "Pirate Scientist", prompt_template
    )
    test_state["prompt_id"] = prompt["id"]
    print("--- REAL LLM test setup complete ---")


# === 测试用例 (真实 API 调用) ===


# 使用 pytest.mark.skipif 来有条件地跳过测试
# 如果环境变量 OPENAI_API_KEY 不存在或为空，则跳过此测试
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY is not set, skipping real API call test.",
)
def test_1_real_successful_prompt_execution():
    """
    测试成功的 Prompt 执行流程，通过真实的 OpenAI API 调用。
    """
    user_id = test_state["user_frank_id"]
    prompt_id = test_state["prompt_id"]
    headers = {"X-User-ID": str(user_id)}
    # 这个 prompt 没有变量，所以 payload 是空的
    payload = {"variables": {}}

    # 使用 httpx.Client 并增加超时时间，因为真实 API 调用可能需要更长时间
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{BASE_URL}/prompts/{prompt_id}/execute", json=payload, headers=headers
        )

    # --- 断言 ---
    # 1. 检查 HTTP 状态码
    assert (
        response.status_code == 200
    ), f"API call failed with status {response.status_code}: {response.text}"

    data = response.json()

    # 2. 对返回的数据结构进行断言
    assert "id" in data
    assert data["prompt_id"] == prompt_id
    assert data["user_id"] == user_id
    assert data["error_message"] is None

    # 3. 对 LLM 的返回内容进行灵活的断言
    # 我们不能断言确切的文本，但可以检查它是否包含某些关键词
    assert data["response_text"] is not None
    assert len(data["response_text"]) > 5  # 响应不应为空
    assert (
        "arrr" in data["response_text"].lower()
        or "matey" in data["response_text"].lower()
        or "shiver" in data["response_text"].lower()
    )  # 检查是否符合 persona
    print(f"\n✅ Real LLM call successful. Response: '{data['response_text']}'")

    # 4. 验证 token usage
    assert "token_usage" in data
    assert data["token_usage"]["total_tokens"] > 0
    assert data["token_usage"]["prompt_tokens"] > 0
    assert data["token_usage"]["completion_tokens"] > 0
    print(f"✅ Token usage recorded: {data['token_usage']}")

    test_state["execution_id"] = data["id"]


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY is not set, skipping real API call test.",
)
@pytest.mark.depends(on=["test_1_real_successful_prompt_execution"])
def test_2_list_real_execution_history():
    """
    测试获取包含真实调用的执行历史记录。
    """
    user_id = test_state["user_frank_id"]
    prompt_id = test_state["prompt_id"]
    headers = {"X-User-ID": str(user_id)}

    with httpx.Client() as client:
        response = client.get(
            f"{BASE_URL}/prompts/{prompt_id}/executions", headers=headers
        )

    assert response.status_code == 200
    data = response.json()

    assert len(data) >= 1

    # 查找我们刚刚创建的那条成功记录
    execution_ids = [r["id"] for r in data]
    assert test_state["execution_id"] in execution_ids

    # 找到记录并验证其内容
    record = next((r for r in data if r["id"] == test_state["execution_id"]), None)
    assert record is not None
    assert record["error_message"] is None
    assert record["token_usage"]["total_tokens"] > 0

    print("\n✅ List real execution history test passed")
