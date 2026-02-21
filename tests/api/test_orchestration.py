def _bootstrap_teammate_with_assistants(client, strategy_config, assistant_names):
    tenant = client.post("/api/v1/tenants", json={"name": "Orch Tenant"}).json()
    workspace = client.post(
        f"/api/v1/tenants/{tenant['id']}/workspaces",
        json={"name": "Orch Workspace"},
    ).json()
    teammate = client.post(
        f"/api/v1/workspaces/{workspace['id']}/teammates",
        json={"name": "Orch Teammate", "orchestration_config": strategy_config},
    ).json()

    assistants = []
    for name in assistant_names:
        assistants.append(
            client.post(
                f"/api/v1/teammates/{teammate['id']}/assistants",
                json={"name": name},
            ).json()
        )

    return teammate, assistants


def test_teammate_query_weighted_routes_highest_weight(client):
    teammate, assistants = _bootstrap_teammate_with_assistants(
        client,
        strategy_config={
            "strategy": "weighted",
            "max_assistants": 1,
            "weights_by_name": {"Planner": 0.1, "Researcher": 2.5},
        },
        assistant_names=["Planner", "Researcher"],
    )

    response = client.post(
        f"/api/v1/teammates/{teammate['id']}/query",
        json={"query": "How should we proceed?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "weighted"
    assert len(data["responses"]) == 1
    assert data["selected_assistant_ids"] == [assistants[1]["id"]]
    assert data["responses"][0]["assistant_name"] == "Researcher"


def test_teammate_query_sequential_returns_all_responses(client):
    teammate, assistants = _bootstrap_teammate_with_assistants(
        client,
        strategy_config={"strategy": "sequential"},
        assistant_names=["Assistant One", "Assistant Two"],
    )

    response = client.post(
        f"/api/v1/teammates/{teammate['id']}/query",
        json={"query": "Summarize the meeting"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "sequential"
    assert len(data["responses"]) == 2
    assert data["selected_assistant_ids"] == [assistants[0]["id"], assistants[1]["id"]]


def test_teammate_query_parallel_returns_all_responses(client):
    teammate, _assistants = _bootstrap_teammate_with_assistants(
        client,
        strategy_config={"strategy": "parallel"},
        assistant_names=["A", "B", "C"],
    )

    response = client.post(
        f"/api/v1/teammates/{teammate['id']}/query",
        json={"query": "Find risks"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "parallel"
    assert len(data["responses"]) == 3


def test_teammate_query_not_found(client):
    response = client.post("/api/v1/teammates/nonexistent/query", json={"query": "hello"})
    assert response.status_code == 404


def test_teammate_query_no_assistants(client):
    tenant = client.post("/api/v1/tenants", json={"name": "No Assistant Tenant"}).json()
    workspace = client.post(
        f"/api/v1/tenants/{tenant['id']}/workspaces",
        json={"name": "No Assistant Workspace"},
    ).json()
    teammate = client.post(
        f"/api/v1/workspaces/{workspace['id']}/teammates",
        json={"name": "No Assistant Teammate", "orchestration_config": {"strategy": "weighted"}},
    ).json()

    response = client.post(
        f"/api/v1/teammates/{teammate['id']}/query",
        json={"query": "hello"},
    )
    assert response.status_code == 404
