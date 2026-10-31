import pytest
import datetime
from fastapi.testclient import TestClient
from app.main import app
import uuid
from app.core.config import settings
from app.core.security import create_access_token

client = TestClient(app)

def test_register_user():
    test_email = f"test_{uuid.uuid4()}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": test_email, "password": "securepassword"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_email
    assert "id" in data
    # Ensure password hash is not returned
    assert "password_hash" not in data
    assert "password" not in data

def test_register_duplicate_email():
    # Attempt to register the same user again
    test_email = f"duplicate_{uuid.uuid4()}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": test_email, "password": "securepassword"}
    )
    response = client.post(
        "/api/v1/auth/register",
        json={"email": test_email, "password": "securepassword2"}
    )
    assert response.status_code == 400

def test_login_success():
    test_email = f"login_{uuid.uuid4()}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": test_email, "password": "securepassword"}
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": test_email, "password": "securepassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_failure():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "wrong@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_read_current_user():
    # Login first
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "securepassword"}
    )
    token = login_response.json()["access_token"]
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "password_hash" not in data

def test_unauthenticated_protected_endpoint():
    client.cookies.clear()
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

def test_invalid_jwt():
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code == 401

def test_expired_jwt():
    # Create an expired token manually
    # We need a user id first
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "securepassword"}
    )
    # The normal /me flow gives us ID
    token = login_response.json()["access_token"]
    user_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = user_response.json()["id"]

    # Create expired token
    expired_token = create_access_token(
        subject=user_id,
        expires_delta=datetime.timedelta(minutes=-1) # Expired 1 min ago
    )
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
