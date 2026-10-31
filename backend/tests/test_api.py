import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check_root():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "development"}

def test_health_check_v1():
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "API is running"}

def test_db_health_check_v1():
    response = client.get("/api/v1/db-health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}
