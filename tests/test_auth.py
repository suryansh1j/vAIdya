"""Tests for registration, login, and token-protected endpoints."""


def test_register_success(client):
    response = client.post("/api/v1/auth/register", json={
        "username": "newdoc",
        "email": "newdoc@example.com",
        "password": "averygoodpassword",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "newdoc"
    assert body["email"] == "newdoc@example.com"


def test_register_duplicate_username(client, registered_user):
    response = client.post("/api/v1/auth/register", json={
        "username": registered_user["username"],
        "email": "other@example.com",
        "password": "averygoodpassword",
    })
    assert response.status_code == 400


def test_register_invalid_email(client):
    response = client.post("/api/v1/auth/register", json={
        "username": "bademail",
        "email": "not-an-email",
        "password": "averygoodpassword",
    })
    assert response.status_code == 422


def test_register_short_password(client):
    response = client.post("/api/v1/auth/register", json={
        "username": "shortpw",
        "email": "shortpw@example.com",
        "password": "short",
    })
    assert response.status_code == 422


def test_register_invalid_username_characters(client):
    response = client.post("/api/v1/auth/register", json={
        "username": "bad user!",
        "email": "baduser@example.com",
        "password": "averygoodpassword",
    })
    assert response.status_code == 422


def test_login_success(client, registered_user):
    response = client.post("/api/v1/auth/login", data={
        "username": registered_user["username"],
        "password": registered_user["password"],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client, registered_user):
    response = client.post("/api/v1/auth/login", data={
        "username": registered_user["username"],
        "password": "wrongpassword123",
    })
    assert response.status_code == 401


def test_login_unknown_user(client):
    response = client.post("/api/v1/auth/login", data={
        "username": "ghost",
        "password": "whatever12345",
    })
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_user(client, auth_headers, registered_user):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == registered_user["username"]
    assert body["email"] == registered_user["email"]


def test_me_rejects_garbage_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.token"},
    )
    assert response.status_code == 401


def test_login_rate_limited(client, registered_user):
    for _ in range(10):
        client.post("/api/v1/auth/login", data={
            "username": registered_user["username"],
            "password": "wrongpassword123",
        })
    response = client.post("/api/v1/auth/login", data={
        "username": registered_user["username"],
        "password": registered_user["password"],
    })
    assert response.status_code == 429
