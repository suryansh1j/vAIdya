"""
Shared test fixtures. Uses an in-memory SQLite database and overrides the
get_db dependency so tests never touch a real database.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import get_db
from backend.main import app, login_rate_limiter, register_rate_limiter
from backend.models import Base


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Each test gets a fresh rate-limit window
    login_rate_limiter._hits.clear()
    register_rate_limiter._hits.clear()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client):
    payload = {
        "username": "drsmith",
        "email": "drsmith@example.com",
        "password": "strongpassword1",
        "full_name": "Dr. Smith",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200
    return payload


@pytest.fixture()
def auth_headers(client, registered_user):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
