import uuid

from app.domains.auth.models import User

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _seed_dev_user(db_session) -> None:
    user = User(
        id=DEV_USER_ID,
        auth_provider="dev",
        auth_provider_id="dev-user-001",
        email="dev@projectmemory.local",
        display_name="Dev User",
    )
    db_session.add(user)
    db_session.commit()


def _create_workspace(client, name="Test Workspace"):
    return client.post("/api/v1/workspaces", json={"name": name})


def _create_memory_space(client, workspace_id, name="Test Space", description=None):
    body = {"name": name}
    if description is not None:
        body["description"] = description
    return client.post(f"/api/v1/workspaces/{workspace_id}/memory-spaces", json=body)


# --- Create ---


def test_create_memory_space(client, db_session):
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]

    resp = _create_memory_space(client, ws_id, name="My Space", description="A space")
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Space"
    assert data["description"] == "A space"
    assert data["status"] == "active"
    assert data["workspace_id"] == ws_id
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_memory_space_no_description(client, db_session):
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]

    resp = _create_memory_space(client, ws_id)
    assert resp.status_code == 201
    assert resp.json()["description"] == ""


def test_create_memory_space_invalid_workspace(client, db_session):
    _seed_dev_user(db_session)
    random_id = uuid.uuid4()

    resp = _create_memory_space(client, random_id)
    assert resp.status_code == 404


# --- List ---


def test_list_memory_spaces_empty(client, db_session):
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]

    resp = client.get(f"/api/v1/workspaces/{ws_id}/memory-spaces")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_list_memory_spaces(client, db_session):
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]
    for i in range(3):
        _create_memory_space(client, ws_id, name=f"Space {i}")

    resp = client.get(f"/api/v1/workspaces/{ws_id}/memory-spaces")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["total"] == 3


def test_list_memory_spaces_filter_by_status(client, db_session):
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]

    # Create 3 spaces (all start as active)
    ids = []
    for i in range(3):
        resp = _create_memory_space(client, ws_id, name=f"Space {i}")
        ids.append(resp.json()["id"])

    # Archive one
    client.patch(f"/api/v1/memory-spaces/{ids[2]}", json={"status": "archived"})

    # Filter by active
    resp = client.get(f"/api/v1/workspaces/{ws_id}/memory-spaces", params={"status": "active"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 2

    # Filter by archived
    resp = client.get(f"/api/v1/workspaces/{ws_id}/memory-spaces", params={"status": "archived"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1


def test_list_memory_spaces_pagination(client, db_session):
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]
    for i in range(5):
        _create_memory_space(client, ws_id, name=f"Space {i}")

    resp = client.get(f"/api/v1/workspaces/{ws_id}/memory-spaces", params={"page_size": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page_size"] == 2


# --- Get ---


def test_get_memory_space(client, db_session):
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]
    create_resp = _create_memory_space(client, ws_id, name="Get Me", description="Details")
    ms_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/memory-spaces/{ms_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == ms_id
    assert data["name"] == "Get Me"
    assert data["description"] == "Details"
    assert data["status"] == "active"


def test_get_memory_space_not_found(client, db_session):
    _seed_dev_user(db_session)
    random_id = uuid.uuid4()

    resp = client.get(f"/api/v1/memory-spaces/{random_id}")
    assert resp.status_code == 404


# --- Update ---


def test_update_memory_space_name(client, db_session):
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]
    ms_id = _create_memory_space(client, ws_id, name="Old Name").json()["id"]

    resp = client.patch(f"/api/v1/memory-spaces/{ms_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["status"] == "active"


def test_update_memory_space_status(client, db_session):
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]
    ms_id = _create_memory_space(client, ws_id).json()["id"]

    resp = client.patch(f"/api/v1/memory-spaces/{ms_id}", json={"status": "archived"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


def test_update_memory_space_invalid_status(client, db_session):
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]
    ms_id = _create_memory_space(client, ws_id).json()["id"]

    resp = client.patch(f"/api/v1/memory-spaces/{ms_id}", json={"status": "invalid"})
    assert resp.status_code == 422


# --- Delete ---


def test_delete_memory_space(client, db_session):
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]
    ms_id = _create_memory_space(client, ws_id).json()["id"]

    resp = client.delete(f"/api/v1/memory-spaces/{ms_id}")
    assert resp.status_code == 204

    # Subsequent GET should 404
    resp = client.get(f"/api/v1/memory-spaces/{ms_id}")
    assert resp.status_code == 404


def test_delete_memory_space_not_found(client, db_session):
    _seed_dev_user(db_session)
    random_id = uuid.uuid4()

    resp = client.delete(f"/api/v1/memory-spaces/{random_id}")
    assert resp.status_code == 404


# --- Summarize + Query endpoints ---


def test_summarize_empty_memory_space(client, db_session):
    """Summarize with no records returns a valid summary with 'no records' message."""
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]
    ms_id = _create_memory_space(client, ws_id).json()["id"]

    resp = client.post(
        f"/api/v1/memory-spaces/{ms_id}/summarize",
        json={"summary_type": "one_pager"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary_type"] == "one_pager"
    assert data["title"] == "No Records Available"
    assert data["memory_space_id"] == ms_id
    assert data["is_edited"] is False
    assert "id" in data
    assert "generated_at" in data


def test_summarize_returns_cached(client, db_session):
    """Second call without regenerate returns the same cached summary."""
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]
    ms_id = _create_memory_space(client, ws_id).json()["id"]

    resp1 = client.post(
        f"/api/v1/memory-spaces/{ms_id}/summarize",
        json={"summary_type": "one_pager"},
    )
    resp2 = client.post(
        f"/api/v1/memory-spaces/{ms_id}/summarize",
        json={"summary_type": "one_pager"},
    )
    assert resp1.json()["id"] == resp2.json()["id"]


def test_summarize_ownership(client, db_session):
    """Summarize rejects requests for memory spaces the user doesn't own."""
    _seed_dev_user(db_session)
    import uuid
    fake_ms_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/memory-spaces/{fake_ms_id}/summarize",
        json={"summary_type": "one_pager"},
    )
    assert resp.status_code == 404


def test_query_empty_memory_space(client, db_session):
    """Query with no records/embeddings returns a valid response."""
    _seed_dev_user(db_session)
    ws_id = _create_workspace(client).json()["id"]
    ms_id = _create_memory_space(client, ws_id).json()["id"]

    from unittest.mock import patch
    mock_result = {"answer": "No context available.", "citations": []}
    with patch("app.integrations.llm_client.llm_client.query", return_value=mock_result), \
         patch("app.integrations.llm_client.llm_client.generate_embeddings", return_value=[[0.0] * 1536]):
        resp = client.post(
            f"/api/v1/memory-spaces/{ms_id}/query",
            json={"question": "What is this project about?"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "citations" in data
    assert isinstance(data["citations"], list)


def test_query_ownership(client, db_session):
    """Query rejects requests for memory spaces the user doesn't own."""
    _seed_dev_user(db_session)
    import uuid
    fake_ms_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/memory-spaces/{fake_ms_id}/query",
        json={"question": "test"},
    )
    assert resp.status_code == 404
