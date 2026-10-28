def login(client, email, password):
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def register(client, email, password="Password@123"):
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_full_approval_flow(client):
    admin = login(client, "admin@example.com", "Admin@12345")
    register(client, "emp@example.com")
    manager_id = register(client, "mgr@example.com")
    r = client.put(f"/users/{manager_id}/role", json={"role": "manager"}, headers=admin)
    assert r.status_code == 200

    emp = login(client, "emp@example.com", "Password@123")
    mgr = login(client, "mgr@example.com", "Password@123")

    # employee creates a request
    r = client.post("/requests", json={"title": "Annual leave", "kind": "leave"}, headers=emp)
    assert r.status_code == 201
    req_id = r.json()["id"]
    assert r.json()["stage"] == "manager"

    # employee cannot approve their own request
    assert client.post(f"/requests/{req_id}/approve", headers=emp).status_code == 403

    # admin cannot skip the manager stage
    assert client.post(f"/requests/{req_id}/approve", headers=admin).status_code == 403

    # manager approves -> moves to admin stage
    r = client.post(f"/requests/{req_id}/approve", json={"comment": "ok"}, headers=mgr)
    assert r.status_code == 200
    assert r.json()["stage"] == "admin" and r.json()["status"] == "pending"

    # admin approves -> final approval
    r = client.post(f"/requests/{req_id}/approve", headers=admin)
    assert r.json()["status"] == "approved"
    assert [log["action"] for log in r.json()["logs"]] == ["created", "approved", "approved"]

    # a finished request cannot be decided again
    assert client.post(f"/requests/{req_id}/reject", headers=admin).status_code == 409


def test_reject_and_access_control(client):
    admin = login(client, "admin@example.com", "Admin@12345")
    register(client, "other@example.com")
    other = login(client, "other@example.com", "Password@123")
    emp = login(client, "emp@example.com", "Password@123")

    r = client.post("/requests", json={"title": "Buy laptop", "kind": "purchase"}, headers=emp)
    req_id = r.json()["id"]

    # another employee cannot view it, and sees an empty list
    assert client.get(f"/requests/{req_id}", headers=other).status_code == 403
    assert client.get("/requests", headers=other).json() == []
    # unauthenticated access is rejected
    assert client.get("/requests").status_code == 401

    # manager rejects at stage 1
    mgr = login(client, "mgr@example.com", "Password@123")
    r = client.post(f"/requests/{req_id}/reject", json={"comment": "over budget"}, headers=mgr)
    assert r.json()["status"] == "rejected"
    assert client.get(f"/requests/{req_id}", headers=admin).json()["logs"][-1]["comment"] == "over budget"
