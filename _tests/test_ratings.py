# tests/test_ratings.py

import httpx
import pytest

BASE_URL = "http://localhost:8002"
test_state = {}


# === 辅助函数 ===
def create_user_for_rating(username, password):
    with httpx.Client() as client:
        res = client.post(
            f"{BASE_URL}/users", json={"username": username, "password": password}
        )
        assert res.status_code == 201
        return res.json()


def create_prompt_for_rating(user_id, title):
    with httpx.Client() as client:
        headers = {"X-User-ID": str(user_id)}
        res = client.post(
            f"{BASE_URL}/prompts",
            json={"title": title, "content": "Test content"},
            headers=headers,
        )
        assert res.status_code == 201
        return res.json()


# === 测试设置 ===
@pytest.fixture(scope="module", autouse=True)
def setup_for_rating_tests():
    print("\n--- Setting up data for rating tests ---")
    # --- 【修复】修改密码，使其长度至少为 6 ---
    user_george = create_user_for_rating("george", "password_g")
    user_helen = create_user_for_rating("helen", "password_h")
    user_ian = create_user_for_rating("ian", "password_i")

    test_state["user_george_id"] = user_george["id"]
    test_state["user_helen_id"] = user_helen["id"]
    test_state["user_ian_id"] = user_ian["id"]

    prompt_by_george = create_prompt_for_rating(
        user_george["id"], "George's Famous Prompt"
    )
    test_state["prompt_id"] = prompt_by_george["id"]

    # 创建另一个 prompt 用于排序测试
    prompt2_by_george = create_prompt_for_rating(
        user_george["id"], "George's Less Famous Prompt"
    )
    test_state["prompt2_id"] = prompt2_by_george["id"]

    print("--- Rating test setup complete ---")


# === 测试用例 ===


def test_1_helen_rates_prompt():
    """Helen (非所有者) 为 George 的 Prompt 评 5 分"""
    helen_id = test_state["user_helen_id"]
    prompt_id = test_state["prompt_id"]
    headers = {"X-User-ID": str(helen_id)}

    with httpx.Client() as client:
        response = client.post(
            f"{BASE_URL}/prompts/{prompt_id}/ratings",
            json={"score": 5},
            headers=headers,
        )
        assert (
            response.status_code == 201
        )  # 应该是 200 OK 或 201 Created，取决于你的实现
        data = response.json()
        assert data["score"] == 5
        assert data["user_id"] == helen_id
    print("\n✅ Helen successfully rated a prompt.")


def test_2_george_cannot_rate_his_own_prompt():
    """George (所有者) 尝试为自己的 Prompt 评分，应该失败"""
    george_id = test_state["user_george_id"]
    prompt_id = test_state["prompt_id"]
    headers = {"X-User-ID": str(george_id)}

    with httpx.Client() as client:
        response = client.post(
            f"{BASE_URL}/prompts/{prompt_id}/ratings",
            json={"score": 5},
            headers=headers,
        )
        assert response.status_code == 403
        assert "cannot rate your own prompt" in response.json()["detail"]
    print("\n✅ Owner was correctly forbidden from rating their own prompt.")


def test_3_helen_cannot_rate_same_prompt_twice():
    """Helen 尝试重复评分，应该失败"""
    helen_id = test_state["user_helen_id"]
    prompt_id = test_state["prompt_id"]
    headers = {"X-User-ID": str(helen_id)}

    with httpx.Client() as client:
        response = client.post(
            f"{BASE_URL}/prompts/{prompt_id}/ratings",
            json={"score": 4},
            headers=headers,
        )
        assert response.status_code == 409  # 409 Conflict
        assert "already rated this prompt" in response.json()["detail"]
    print("\n✅ User was correctly forbidden from rating the same prompt twice.")


def test_4_ian_rates_prompt_and_check_average():
    """Ian 也来评分，然后我们检查平均分"""
    ian_id = test_state["user_ian_id"]
    prompt_id = test_state["prompt_id"]
    headers = {"X-User-ID": str(ian_id)}

    with httpx.Client() as client:
        client.post(
            f"{BASE_URL}/prompts/{prompt_id}/ratings",
            json={"score": 3},
            headers=headers,
        )

    # 现在获取 prompt 详情来检查平均分
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/prompts/{prompt_id}")
        assert response.status_code == 200
        data = response.json()
        # Helen 评了 5 分，Ian 评了 3 分，平均分应该是 (5+3)/2 = 4.0
        assert data["average_rating"] == 4.0
    print("\n✅ Average rating was calculated correctly (4.0).")


def test_5_sort_prompts_by_rating():
    """测试按评分排序功能"""
    # 首先，给第二个 prompt (prompt2) 一个较低的评分
    ian_id = test_state["user_ian_id"]
    prompt2_id = test_state["prompt2_id"]
    headers = {"X-User-ID": str(ian_id)}
    with httpx.Client() as client:
        client.post(
            f"{BASE_URL}/prompts/{prompt2_id}/ratings",
            json={"score": 2},
            headers=headers,
        )

    # 现在，按评分排序获取 prompt 列表
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/prompts?sort=rating")
        assert response.status_code == 200
        data = response.json()

        # 列表中的第一个 prompt 应该是平均分为 4.0 的那个
        assert len(data["prompts"]) >= 2
        assert data["prompts"][0]["id"] == test_state["prompt_id"]
        assert data["prompts"][0]["average_rating"] == 4.0

        # 第二个应该是平均分为 2.0 的那个
        assert data["prompts"][1]["id"] == test_state["prompt2_id"]
        assert data["prompts"][1]["average_rating"] == 2.0
    print("\n✅ Prompts were correctly sorted by rating in descending order.")
