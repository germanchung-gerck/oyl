def test_create_tenant(client):
    response = client.post("/api/v1/tenants", json={"name": "Acme Corp"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Corp"
    assert "id" in data
    assert "created_at" in data


def test_get_tenant(client):
    create_response = client.post("/api/v1/tenants", json={"name": "Beta Inc"})
    tenant_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/tenants/{tenant_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == tenant_id


def test_get_tenant_not_found(client):
    response = client.get("/api/v1/tenants/nonexistent-id")
    assert response.status_code == 404
