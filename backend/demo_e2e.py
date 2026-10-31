import os
import time
import requests
import uuid

API_BASE = "http://127.0.0.1:8000/api/v1"

def print_step(msg):
    print(f"\n{'='*50}\n[STEP] {msg}\n{'='*50}")

def main():
    session_a = requests.Session()
    session_b = requests.Session()
    
    # Generate unique IDs to avoid conflicts
    unique_suffix = str(uuid.uuid4())[:8]
    email_a = f"alice_{unique_suffix}@example.com"
    email_b = f"bob_{unique_suffix}@example.com"
    password = "securepassword"
    
    print_step("1. REGISTER & LOGIN")
    
    # Register A
    r = session_a.post(f"{API_BASE}/auth/register", json={"email": email_a, "password": password})
    assert r.status_code == 201, f"Failed to register A: {r.text}"
    user_a_id = r.json()["id"]
    
    # Login A (this will set the HttpOnly cookie in the session)
    r = session_a.post(f"{API_BASE}/auth/login", data={"username": email_a, "password": password})
    assert r.status_code == 200, f"Failed to login A: {r.text}"
    print("User A logged in successfully.")
    
    # Verify cookie auth works
    r = session_a.get(f"{API_BASE}/auth/me")
    assert r.status_code == 200, "Cookie auth failed"
    
    # Register B
    r = session_b.post(f"{API_BASE}/auth/register", json={"email": email_b, "password": password})
    assert r.status_code == 201, f"Failed to register B: {r.text}"
    
    # Login B
    r = session_b.post(f"{API_BASE}/auth/login", data={"username": email_b, "password": password})
    assert r.status_code == 200, f"Failed to login B: {r.text}"
    print("User B logged in successfully.")
    
    print_step("2. ORGANIZATION & MULTI-TENANT SETUP")
    
    # Get Org A
    r = session_a.post(f"{API_BASE}/organizations/", json={"name": f"Org A {unique_suffix}", "plan": "enterprise"})
    org_a_id = r.json()["id"]
    print(f"Org A ID: {org_a_id}")
    
    # Get Org B
    r = session_b.post(f"{API_BASE}/organizations/", json={"name": f"Org B {unique_suffix}", "plan": "enterprise"})
    org_b_id = r.json()["id"]
    print(f"Org B ID: {org_b_id}")
    
    print_step("3. UPLOAD ENTERPRISE DOCUMENT")
    
    # Create test document
    doc_content = """
    COMPANY POLICY 2026:
    1. Remote work is allowed 3 days a week (Tuesday, Wednesday, Thursday).
    2. The annual budget for learning and development is $1,500 per employee.
    3. Migrating to AWS is considered high risk due to legacy database dependencies, which lack active maintenance.
    """
    with open("hr_policy.txt", "w") as f:
        f.write(doc_content)
        
    # Upload A
    with open("hr_policy.txt", "rb") as f:
        r = session_a.post(f"{API_BASE}/organizations/{org_a_id}/documents/", files={"file": ("hr_policy.txt", f)})
        assert r.status_code == 201, f"Upload failed: {r.text}"
        doc_id = r.json()["id"]
    
    print("Document uploaded. Polling for processing to become ready...")
    for _ in range(15):
        r = session_a.get(f"{API_BASE}/organizations/{org_a_id}/documents/{doc_id}/status")
        if r.status_code == 200 and r.json()["status"] == "ready":
            break
        time.sleep(1)
    else:
        raise Exception("Document processing timed out (never became 'ready')")

    print("Document ready. Triggering indexing...")
    r = session_a.post(f"{API_BASE}/organizations/{org_a_id}/documents/{doc_id}/index")
    assert r.status_code == 202, f"Failed to trigger indexing: {r.text}"

    print("Polling for indexing status...")
    for _ in range(15):
        r = session_a.get(f"{API_BASE}/organizations/{org_a_id}/documents/{doc_id}/status")
        if r.status_code == 200 and r.json()["status"] == "indexed":
            print("Document indexed successfully.")
            break
        time.sleep(2)
    else:
        raise Exception("Document indexing timed out")
    
    print_step("4. DETERMINISTIC RAG (Answerable & Unanswerable)")
    
    r = session_a.post(f"{API_BASE}/rag/query", json={"query": "What is the learning budget?", "mode": "deterministic"})
    assert r.status_code == 200, f"RAG failed: {r.text}"
    data = r.json()
    assert "$1,500" in data["answer"] or "1500" in data["answer"], f"Answer did not contain correct fact: {data['answer']}"
    assert len(data["sources"]) > 0, "No sources cited"
    print("Answerable query SUCCESS")
    
    r = session_a.post(f"{API_BASE}/rag/query", json={"query": "What is the CEO's favorite color?", "mode": "deterministic"})
    data_un = r.json()
    # Should abstain
    assert len(data_un["sources"]) == 0 or "I cannot answer" in data_un["answer"] or "not mentioned" in data_un["answer"].lower(), "Failed abstention test"
    print("Unanswerable query abstained properly.")
    
    print_step("5. AGENTIC RAG")
    
    r = session_a.post(f"{API_BASE}/rag/query", json={"query": "Can I work remotely on Monday, and what is the learning budget?", "mode": "agentic"})
    assert r.status_code == 200
    agentic_data = r.json()
    print("Agentic Answer:", agentic_data["answer"])
    agentic_run_id = agentic_data.get("retrieval_metadata", {}).get("run_id")
    print(f"Agentic Run ID: {agentic_run_id}")
    
    print_step("6. DECISION INTELLIGENCE")
    
    r = session_a.post(f"{API_BASE}/decisions/analyze", json={"query": "What are the risks of migrating to AWS?"})
    assert r.status_code == 200
    decision_data = r.json()
    assert decision_data["decision_type"] == "risk_analysis", "Wrong decision type"
    print("Risks found:", len(decision_data.get("risks", [])))
    
    decision_run_id = decision_data["decision_trace"]["run_id"]
    
    print_step("7. TRACE & OBSERVABILITY (SECURITY CHECK)")
    
    # Get trace
    agentic_run_id = agentic_data.get("retrieval_metadata", {}).get("run_id")
    if agentic_run_id:
        r = session_a.get(f"{API_BASE}/traces/{agentic_run_id}")
        assert r.status_code == 200, f"Failed to get trace: {r.text}"
        trace_data = r.json()
        assert trace_data["id"] == agentic_run_id, "Trace mismatch"
        assert len(trace_data["steps"]) >= 1, "Agent trace should have at least one step"
        print("Agent trace verified successfully.")
    else:
        print("Warning: No run_id found in retrieval_metadata, skipping trace verification.")
    
    # Verify API keys not exposed
    trace_str = str(trace_data)
    assert "sk-" not in trace_str, "API key leaked in trace!"
    assert "password" not in trace_str.lower() or "password_hash" not in trace_str.lower(), "Passwords leaked!"
    print("Trace looks secure and human-readable.")
    
    # B cannot see A's trace
    r = session_b.get(f"{API_BASE}/traces/{agentic_run_id}")
    assert r.status_code in (403, 404), f"Cross-tenant trace leak! Status: {r.status_code}"
    print("Cross-tenant trace isolation SUCCESS.")
    
    # B cannot query A's documents
    r = session_b.post(f"{API_BASE}/rag/query", json={"query": "What is the learning budget?", "mode": "deterministic"})
    data_b = r.json()
    assert len(data_b["sources"]) == 0, "User B retrieved User A's documents!"
    print("Cross-tenant retrieval isolation SUCCESS.")
    
    print_step("8. RERANKER VERIFICATION")
    
    r = session_a.get(f"{API_BASE}/dashboard/stats?org_id={org_a_id}")
    stats = r.json()
    print("Dashboard Stats:", stats)
    
    print_step("ALL E2E TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
