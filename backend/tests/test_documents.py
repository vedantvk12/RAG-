import pytest
import time
import os
from uuid import UUID
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_user_and_login(email: str, password: str = "securepassword") -> tuple[str, str]:
    res = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return me_res.json()["id"], token

def create_org(token: str, name: str) -> str:
    res = client.post("/api/v1/organizations/", json={"name": name}, headers={"Authorization": f"Bearer {token}"})
    return res.json()["id"]

def test_document_upload_and_processing(tmp_path):
    user_id, token = create_user_and_login("docuser1@example.com")
    org_id = create_org(token, "Doc Org 1")

    # Create dummy txt file
    test_file_path = tmp_path / "test.txt"
    test_file_path.write_text("This is a test paragraph.\n\nThis is another paragraph.")

    with open(test_file_path, "rb") as f:
        response = client.post(
            f"/api/v1/organizations/{org_id}/documents/",
            files={"file": ("test.txt", f, "text/plain")},
            headers={"Authorization": f"Bearer {token}"}
        )
    
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    doc_id = response.json()["id"]
    
    # Wait a bit for background task (TestClient runs background tasks synchronously after returning response)
    # So by the time we get here, it should be done.
    
    status_res = client.get(
        f"/api/v1/organizations/{org_id}/documents/{doc_id}/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] in ["ready", "indexed"]

    # Fetch document and chunks
    doc_res = client.get(
        f"/api/v1/organizations/{org_id}/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert doc_res.status_code == 200
    doc_data = doc_res.json()
    assert len(doc_data["chunks"]) == 1
    assert "This is a test paragraph" in doc_data["chunks"][0]["text"]
    assert "This is another paragraph" in doc_data["chunks"][0]["text"]

def test_duplicate_document_upload(tmp_path):
    user_id, token = create_user_and_login("docuser2@example.com")
    org_id = create_org(token, "Doc Org 2")

    test_file_path = tmp_path / "dup.txt"
    test_file_path.write_text("Duplicate content")

    # Upload first time
    with open(test_file_path, "rb") as f:
        res1 = client.post(
            f"/api/v1/organizations/{org_id}/documents/",
            files={"file": ("dup.txt", f, "text/plain")},
            headers={"Authorization": f"Bearer {token}"}
        )
    assert res1.status_code == 201
    
    # Upload second time (duplicate)
    with open(test_file_path, "rb") as f:
        res2 = client.post(
            f"/api/v1/organizations/{org_id}/documents/",
            files={"file": ("dup.txt", f, "text/plain")},
            headers={"Authorization": f"Bearer {token}"}
        )
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]

def test_invalid_extension(tmp_path):
    user_id, token = create_user_and_login("docuser3@example.com")
    org_id = create_org(token, "Doc Org 3")

    test_file_path = tmp_path / "bad.exe"
    test_file_path.write_text("malicious")

    with open(test_file_path, "rb") as f:
        res = client.post(
            f"/api/v1/organizations/{org_id}/documents/",
            files={"file": ("bad.exe", f, "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"}
        )
    assert res.status_code == 400

def test_tenant_isolation_documents(tmp_path):
    userA_id, tokenA = create_user_and_login("tenantA@example.com")
    orgA_id = create_org(tokenA, "Org A")
    
    userB_id, tokenB = create_user_and_login("tenantB@example.com")
    orgB_id = create_org(tokenB, "Org B")

    # A uploads to A
    test_file_path = tmp_path / "A.txt"
    test_file_path.write_text("Content A")
    with open(test_file_path, "rb") as f:
        res = client.post(
            f"/api/v1/organizations/{orgA_id}/documents/",
            files={"file": ("A.txt", f, "text/plain")},
            headers={"Authorization": f"Bearer {tokenA}"}
        )
    docA_id = res.json()["id"]

    # B tries to get A's doc by altering URL to use orgA_id 
    # (should fail because B is not a member of orgA)
    res_b_get_a = client.get(
        f"/api/v1/organizations/{orgA_id}/documents/{docA_id}",
        headers={"Authorization": f"Bearer {tokenB}"}
    )
    assert res_b_get_a.status_code == 403

    # B tries to get A's doc by using orgB_id in URL but docA_id
    # (should fail because docA doesn't belong to orgB)
    res_b_get_a2 = client.get(
        f"/api/v1/organizations/{orgB_id}/documents/{docA_id}",
        headers={"Authorization": f"Bearer {tokenB}"}
    )
    assert res_b_get_a2.status_code == 404
