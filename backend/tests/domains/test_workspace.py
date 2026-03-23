import uuid

from app.domains.auth.models import User
from app.domains.memory_space.models import MemorySpace

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


def _create_workspace(client, name="Test Workspace", description=None):
    body = {"name": name}
    if description is not None:
        body["description"] = description
    return client.post("/api/v1/workspaces", json=body)


# --- Create ---


def test_create_workspace(client, db_session):
    _seed_dev_user(db_session)
    resp = _create_workspace(client, name="My Workspace", description="A workspace")
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Workspace"
    assert data["description"] == "A workspace"
    assert data["owner_id"] == str(DEV_USER_ID)
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_workspace_with_description(client, db_session):
    _seed_dev_user(db_session)
    resp = _create_workspace(client, description="Has a description")
    assert resp.status_code == 201
    assert resp.json()["description"] == "Has a description"


def test_create_workspace_no_description(client, db_session):
    _seed_dev_user(db_session)
    resp = _create_workspace(client)
    assert resp.status_code == 201
    assert resp.json()["description"] == ""


def test_create_workspace_missing_name(client, db_session):
    _seed_dev_user(db_session)
    resp = client.post("/api/v1/workspaces", json={})
    assert resp.status_code == 422


# --- List ---


def test_list_workspaces_empty(client, db_session):
    _seed_dev_user(db_session)
    resp = client.get("/api/v1/workspaces")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_list_workspaces(client, db_session):
    _seed_dev_user(db_session)
    for i in range(3):
        _create_workspace(client, name=f"Workspace {i}")
    resp = client.get("/api/v1/workspaces")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["total"] == 3


def test_list_workspaces_pagination(client, db_session):
    _seed_dev_user(db_session)
    for i in range(5):
        _create_workspace(client, name=f"Workspace {i}")
    resp = client.get("/api/v1/workspaces", params={"page_size": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page_size"] == 2


# --- Get ---


def test_get_workspace(client, db_session):
    _seed_dev_user(db_session)
    create_resp = _create_workspace(client, name="Get Me", description="Details")
    workspace_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == workspace_id
    assert data["name"] == "Get Me"
    assert data["description"] == "Details"


def test_get_workspace_not_found(client, db_session):
    _seed_dev_user(db_session)
    random_id = uuid.uuid4()
    resp = client.get(f"/api/v1/workspaces/{random_id}")
    assert resp.status_code == 404


# --- Update ---


def test_update_workspace_name(client, db_session):
    _seed_dev_user(db_session)
    create_resp = _create_workspace(client, name="Old Name", description="Keep me")
    workspace_id = create_resp.json()["id"]

    resp = client.patch(f"/api/v1/workspaces/{workspace_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["description"] == "Keep me"


def test_update_workspace_description(client, db_session):
    _seed_dev_user(db_session)
    create_resp = _create_workspace(client, name="Stay", description="Old desc")
    workspace_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/workspaces/{workspace_id}", json={"description": "New desc"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Stay"
    assert data["description"] == "New desc"


def test_update_workspace_not_found(client, db_session):
    _seed_dev_user(db_session)
    random_id = uuid.uuid4()
    resp = client.patch(f"/api/v1/workspaces/{random_id}", json={"name": "Nope"})
    assert resp.status_code == 404


# --- Delete ---


def test_delete_workspace(client, db_session):
    _seed_dev_user(db_session)
    create_resp = _create_workspace(client, name="Delete Me")
    workspace_id = create_resp.json()["id"]

    resp = client.delete(f"/api/v1/workspaces/{workspace_id}")
    assert resp.status_code == 204

    # Subsequent GET should 404
    resp = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert resp.status_code == 404


def test_delete_workspace_cascades_memory_spaces(client, db_session):
    _seed_dev_user(db_session)
    create_resp = _create_workspace(client, name="Parent Workspace")
    workspace_id = create_resp.json()["id"]

    # Create memory spaces directly via ORM (memory space router doesn't exist yet)
    for i in range(2):
        ms = MemorySpace(
            workspace_id=uuid.UUID(workspace_id),
            name=f"Space {i}",
            description="",
            status="active",
        )
        db_session.add(ms)
    db_session.commit()

    # Verify they exist
    spaces = (
        db_session.query(MemorySpace)
        .filter(
            MemorySpace.workspace_id == uuid.UUID(workspace_id),
            MemorySpace.deleted_at.is_(None),
        )
        .all()
    )
    assert len(spaces) == 2

    # Delete the workspace
    resp = client.delete(f"/api/v1/workspaces/{workspace_id}")
    assert resp.status_code == 204

    # Memory spaces should be soft-deleted
    db_session.expire_all()
    spaces = (
        db_session.query(MemorySpace)
        .filter(
            MemorySpace.workspace_id == uuid.UUID(workspace_id),
            MemorySpace.deleted_at.is_(None),
        )
        .all()
    )
    assert len(spaces) == 0
