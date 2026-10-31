import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_user_and_login(email: str, password: str = "securepassword") -> tuple[str, str]:
    """Helper to create a user and return (user_id, token)."""
    # Create
    res = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    # If already exists, just login
    if res.status_code == 400:
        pass
    else:
        assert res.status_code == 201
        
    login_res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return me_res.json()["id"], token

def test_organization_creation_and_isolation():
    user1_id, token1 = create_user_and_login("user1@example.com")
    user2_id, token2 = create_user_and_login("user2@example.com")
    
    # User 1 creates Org A
    orgA_res = client.post(
        "/api/v1/organizations/",
        json={"name": "Org A"},
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert orgA_res.status_code == 201
    orgA_id = orgA_res.json()["id"]

    # User 2 creates Org B
    orgB_res = client.post(
        "/api/v1/organizations/",
        json={"name": "Org B"},
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert orgB_res.status_code == 201
    orgB_id = orgB_res.json()["id"]

    # --- ISOLATION TESTS ---
    
    # User A cannot access Org B
    res = client.get(f"/api/v1/organizations/{orgB_id}", headers={"Authorization": f"Bearer {token1}"})
    assert res.status_code == 403

    # Org A admin cannot access Org B
    # (Same as above, user1 is admin of Org A)
    res = client.get(f"/api/v1/organizations/{orgB_id}/members", headers={"Authorization": f"Bearer {token1}"})
    assert res.status_code == 403
    
    # Manipulating org_id cannot bypass tenant isolation
    res = client.post(
        f"/api/v1/organizations/{orgB_id}/members",
        json={"email": "user1@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert res.status_code == 403

def test_member_cannot_perform_admin_operations():
    admin_id, admin_token = create_user_and_login("admin@example.com")
    member_id, member_token = create_user_and_login("member@example.com")
    outsider_id, outsider_token = create_user_and_login("outsider@example.com")
    
    # Admin creates Org
    org_res = client.post(
        "/api/v1/organizations/",
        json={"name": "Test Org"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    org_id = org_res.json()["id"]

    # Admin invites Member
    add_res = client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "member@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert add_res.status_code == 201

    # Member tries to invite outsider (should fail with 403)
    invite_res = client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "outsider@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {member_token}"}
    )
    assert invite_res.status_code == 403

    # Member tries to modify role (should fail)
    patch_res = client.patch(
        f"/api/v1/organizations/{org_id}/members/{admin_id}",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {member_token}"}
    )
    assert patch_res.status_code == 403

    # Admin can change outsider? No, outsider is not in org. 
    # But admin CAN remove member
    remove_res = client.delete(
        f"/api/v1/organizations/{org_id}/members/{member_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert remove_res.status_code == 204

    # Removed organization member immediately loses access
    get_res = client.get(
        f"/api/v1/organizations/{org_id}",
        headers={"Authorization": f"Bearer {member_token}"}
    )
    assert get_res.status_code == 403
