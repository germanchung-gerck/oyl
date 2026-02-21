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


def test_list_tenants(client):
    client.post("/api/v1/tenants", json={"name": "Tenant A"})
    client.post("/api/v1/tenants", json={"name": "Tenant B"})

    response = client.get("/api/v1/tenants")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {item["name"] for item in data} == {"Tenant A", "Tenant B"}


def test_update_tenant(client):
    create_response = client.post("/api/v1/tenants", json={"name": "Old Name"})
    tenant_id = create_response.json()["id"]

    update_response = client.put(f"/api/v1/tenants/{tenant_id}", json={"name": "New Name"})
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "New Name"


def test_update_tenant_not_found(client):
    response = client.put("/api/v1/tenants/nonexistent-id", json={"name": "Any"})
    assert response.status_code == 404


def test_delete_tenant(client):
    create_response = client.post("/api/v1/tenants", json={"name": "Delete Me"})
    tenant_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/tenants/{tenant_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/tenants/{tenant_id}")
    assert get_response.status_code == 404


def test_delete_tenant_not_found(client):
    response = client.delete("/api/v1/tenants/nonexistent-id")
    assert response.status_code == 404


def test_create_tenant_duplicate_name(client):
    client.post("/api/v1/tenants", json={"name": "Acme Corp"})
    duplicate_response = client.post("/api/v1/tenants", json={"name": "Acme Corp"})

    assert duplicate_response.status_code == 400


def test_update_tenant_duplicate_name(client):
    first = client.post("/api/v1/tenants", json={"name": "Tenant One"}).json()
    client.post("/api/v1/tenants", json={"name": "Tenant Two"})

    response = client.put(f"/api/v1/tenants/{first['id']}", json={"name": "Tenant Two"})
    assert response.status_code == 400


def test_create_tenant_validation_empty_name(client):
    response = client.post("/api/v1/tenants", json={"name": ""})
    assert response.status_code == 422


def test_create_tenant_validation_whitespace_name(client):
    response = client.post("/api/v1/tenants", json={"name": "   "})
    assert response.status_code == 422
