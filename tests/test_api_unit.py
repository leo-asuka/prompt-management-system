# tests/test_api_unit.py


def test_read_root(client_with_db):
    response = client_with_db.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]


def test_health_check(client_with_db):
    response = client_with_db.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_user_api(client_with_db):
    response = client_with_db.post("/users", json={"username": "api_unit_user", "password": "password123"})
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "api_unit_user"
    assert "id" in data


def test_create_user_duplicate_api(client_with_db):
    client_with_db.post("/users", json={"username": "dup_user", "password": "pwd"})
    response = client_with_db.post("/users", json={"username": "dup_user", "password": "pwd"})
    assert response.status_code == 400


def test_get_prompts_empty(client_with_db):
    response = client_with_db.get("/prompts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["prompts"] == []


def test_create_prompt_unauthorized(client_with_db):
    response = client_with_db.post("/prompts", json={"title": "T", "content": "C"})
    assert response.status_code == 422
