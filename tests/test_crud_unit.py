# tests/test_crud_unit.py
from src.app import crud, schemas, llm_client


# ==========================================
# User Tests
# ==========================================
def test_create_user(db_session):
    """单元测试：创建用户 (修复数据长度问题)"""
    # 修复：使用符合长度要求的用户名和密码
    user_in = schemas.UserCreate(username="unit_test_user", password="password123")
    user = crud.create_user(db_session, user_in)

    assert user.username == "unit_test_user"
    assert hasattr(user, "hashed_password")
    assert user.hashed_password != "password123"


def test_authenticate_user_logic(db_session):
    """单元测试：验证用户查重逻辑"""
    user_in = schemas.UserCreate(username="duplicate_user", password="password123")
    crud.create_user(db_session, user_in)

    # 尝试查找
    found = crud.get_user_by_username(db_session, "duplicate_user")
    assert found is not None
    assert found.id is not None


# ==========================================
# Prompt & Version Tests
# ==========================================
def test_create_prompt_and_version(db_session):
    """单元测试：验证创建 Prompt 时自动创建版本 1"""
    # 修复：用户名密码长度
    user = crud.create_user(
        db_session,
        schemas.UserCreate(username="user_for_prompt", password="password123"),
    )

    prompt_in = schemas.PromptCreate(
        title="Unit Test Prompt", content="Content", category="Test"
    )
    prompt = crud.create_prompt(db_session, prompt_in, user.id)

    assert prompt.id is not None
    assert prompt.title == "Unit Test Prompt"

    # 验证版本
    versions = crud.get_prompt_versions(db_session, prompt.id)
    assert len(versions) == 1
    assert versions[0].version_number == 1


def test_update_prompt_creates_version(db_session):
    """单元测试：验证更新 Prompt 自动创建新版本"""
    user = crud.create_user(
        db_session, schemas.UserCreate(username="user_update", password="password123")
    )
    prompt = crud.create_prompt(
        db_session, schemas.PromptCreate(title="Original", content="C1"), user.id
    )

    # 更新
    update_in = schemas.PromptUpdate(title="Updated", content="C2")
    updated_prompt = crud.update_prompt(db_session, prompt, update_in)

    assert updated_prompt.title == "Updated"

    # 验证版本历史
    versions = crud.get_prompt_versions(db_session, prompt.id)
    assert len(versions) == 2
    assert versions[0].version_number == 2
    assert versions[1].version_number == 1


def test_rollback_prompt(db_session):
    """单元测试：验证回滚逻辑"""
    user = crud.create_user(
        db_session, schemas.UserCreate(username="user_rollback", password="password123")
    )
    prompt = crud.create_prompt(
        db_session, schemas.PromptCreate(title="V1", content="C1"), user.id
    )

    # 更新到 V2
    crud.update_prompt(db_session, prompt, schemas.PromptUpdate(title="V2"))

    # 回滚到 V1 (这会创建 V3，内容等于 V1)
    rolled_back = crud.rollback_prompt(db_session, prompt, 1)

    assert rolled_back.title == "V1"
    versions = crud.get_prompt_versions(db_session, prompt.id)
    assert len(versions) == 3
    assert versions[0].version_number == 3
    assert versions[0].title == "V1"


def test_delete_prompt(db_session):
    """单元测试：删除 Prompt"""
    user = crud.create_user(
        db_session, schemas.UserCreate(username="user_del", password="password123")
    )
    prompt = crud.create_prompt(
        db_session, schemas.PromptCreate(title="To Delete", content="C"), user.id
    )

    crud.delete_prompt(db_session, prompt)

    found = crud.get_prompt(db_session, prompt.id)
    assert found is None


def test_get_prompts_list_logic(db_session):
    """单元测试：查询列表与筛选"""
    user = crud.create_user(
        db_session, schemas.UserCreate(username="user_list", password="password123")
    )
    crud.create_prompt(
        db_session, schemas.PromptCreate(title="P1", content="C"), user.id
    )
    crud.create_prompt(
        db_session, schemas.PromptCreate(title="P2", content="C"), user.id
    )

    prompts, total = crud.get_prompts(db_session, skip=0, limit=10)
    assert total == 2
    assert len(prompts) == 2


# ==========================================
# Rating Tests
# ==========================================
def test_rating_logic(db_session):
    """单元测试：验证评分逻辑"""
    user = crud.create_user(
        db_session, schemas.UserCreate(username="user_rate", password="password123")
    )
    prompt = crud.create_prompt(
        db_session, schemas.PromptCreate(title="P", content="C"), user.id
    )

    # 评分
    rating = crud.create_rating_for_prompt(db_session, prompt.id, user.id, 5)
    assert rating is not None
    assert rating.score == 5

    # 验证唯一性约束
    duplicate = crud.create_rating_for_prompt(db_session, prompt.id, user.id, 4)
    assert duplicate is None

    # 验证平均分计算
    # 需要另一个用户来评分以验证平均值
    user2 = crud.create_user(
        db_session, schemas.UserCreate(username="user_rate2", password="password123")
    )
    crud.create_rating_for_prompt(db_session, prompt.id, user2.id, 3)  # 5 和 3 平均 4

    p_with_rating = crud.get_prompt_with_average_rating(db_session, prompt.id)
    assert p_with_rating.average_rating == 4.0


# ==========================================
# Tag Tests
# ==========================================
def test_tags_logic(db_session):
    """单元测试：标签逻辑"""
    user = crud.create_user(
        db_session, schemas.UserCreate(username="user_tag", password="password123")
    )
    prompt = crud.create_prompt(
        db_session, schemas.PromptCreate(title="P", content="C"), user.id
    )

    # 创建标签
    tag = crud.create_tag(db_session, schemas.TagCreate(name="AI"))
    assert tag.id is not None

    # 关联
    crud.add_tag_to_prompt(db_session, prompt, tag)
    assert len(prompt.tags) == 1
    assert prompt.tags[0].name == "AI"

    # 筛选
    prompts, total = crud.get_prompts(db_session, tags=["AI"])
    assert total == 1

    # 移除
    crud.remove_tag_from_prompt(db_session, prompt, tag)
    assert len(prompt.tags) == 0


# ==========================================
# LLM Execution Tests
# ==========================================
def test_create_execution_log(db_session):
    """单元测试：创建执行日志"""
    user = crud.create_user(
        db_session, schemas.UserCreate(username="user_llm", password="password123")
    )
    prompt = crud.create_prompt(
        db_session, schemas.PromptCreate(title="P", content="C"), user.id
    )

    # 模拟一个结果对象
    mock_result = llm_client.LLMExecutionResult(
        success=True, content="Result", usage={"total": 10}
    )

    execution = crud.create_prompt_execution(
        db_session, prompt.id, user.id, {"var": "val"}, mock_result
    )
    assert execution.id is not None
    assert execution.response_text == "Result"

    history = crud.get_prompt_executions(db_session, prompt.id)
    assert len(history) == 1
