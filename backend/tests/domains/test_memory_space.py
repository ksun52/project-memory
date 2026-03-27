import uuid
from unittest.mock import patch

from app.domains.ai.models import Embedding
from app.domains.auth.models import User
from app.domains.memory.models import MemoryRecord, RecordSourceLink
from app.domains.memory_space.models import MemorySpace
from app.domains.source.models import Source, SourceChunk, SourceContent
from app.domains.workspace.models import Workspace

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
    fake_ms_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/memory-spaces/{fake_ms_id}/query",
        json={"question": "test"},
    )
    assert resp.status_code == 404


# --- Tests with mocked AI service ---


def _seed_full(db_session):
    """Create user + workspace + memory space + source + records for AI tests."""
    _seed_dev_user(db_session)
    ws = Workspace(owner_id=DEV_USER_ID, name="Test WS", description="")
    db_session.add(ws)
    db_session.commit()
    db_session.refresh(ws)

    ms = MemorySpace(
        workspace_id=ws.id, name="Test MS", description="", status="active"
    )
    db_session.add(ms)
    db_session.commit()
    db_session.refresh(ms)

    source = Source(
        memory_space_id=ms.id,
        source_type="note",
        title="Meeting Notes",
        processing_status="completed",
    )
    db_session.add(source)
    db_session.flush()

    content = SourceContent(source_id=source.id, content_text="We decided to use Postgres.")
    db_session.add(content)
    db_session.flush()

    record = MemoryRecord(
        memory_space_id=ms.id,
        record_type="decision",
        content="Team decided to use Postgres with pgvector",
        confidence=0.95,
        importance="high",
        origin="extracted",
        status="active",
        record_metadata={},
    )
    db_session.add(record)
    db_session.flush()

    link = RecordSourceLink(
        record_id=record.id,
        source_id=source.id,
        evidence_text="We decided to use Postgres.",
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(ms)
    db_session.refresh(source)
    db_session.refresh(record)
    return ws, ms, source, record


def test_summarize_with_records(client, db_session):
    """Summarize with actual records calls LLM and returns valid SummaryResponse."""
    ws, ms, source, record = _seed_full(db_session)

    mock_llm_response = {
        "title": "Project Overview",
        "content": "## Key Decisions\n\nTeam uses Postgres with pgvector.",
    }
    with patch("app.domains.ai.service.llm_client") as mock_llm:
        mock_llm.summarize.return_value = mock_llm_response
        resp = client.post(
            f"/api/v1/memory-spaces/{ms.id}/summarize",
            json={"summary_type": "one_pager", "regenerate": True},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Project Overview"
    assert "Postgres" in data["content"]
    assert data["summary_type"] == "one_pager"
    assert str(record.id) in data["record_ids_used"]
    assert data["is_edited"] is False
    assert data["id"] is not None
    assert data["generated_at"] is not None


def test_summarize_regenerate_bypasses_cache(client, db_session):
    """regenerate=true creates a new summary even when cache exists."""
    ws, ms, source, record = _seed_full(db_session)

    mock_llm_response = {
        "title": "Summary v1",
        "content": "First version.",
    }
    with patch("app.domains.ai.service.llm_client") as mock_llm:
        mock_llm.summarize.return_value = mock_llm_response
        resp1 = client.post(
            f"/api/v1/memory-spaces/{ms.id}/summarize",
            json={"summary_type": "one_pager", "regenerate": True},
        )

    mock_llm_response_v2 = {
        "title": "Summary v2",
        "content": "Second version.",
    }
    with patch("app.domains.ai.service.llm_client") as mock_llm:
        mock_llm.summarize.return_value = mock_llm_response_v2
        resp2 = client.post(
            f"/api/v1/memory-spaces/{ms.id}/summarize",
            json={"summary_type": "one_pager", "regenerate": True},
        )

    assert resp1.json()["id"] != resp2.json()["id"]
    assert resp2.json()["title"] == "Summary v2"


def test_query_with_citations_and_source_id(client, db_session):
    """Query returns citations with source_id populated."""
    ws, ms, source, record = _seed_full(db_session)

    # Create an embedding for the record so vector search can find it
    embedding = Embedding(
        entity_type="memory_record",
        entity_id=record.id,
        embedding=[0.01] * 1536,
        model_id="text-embedding-3-small",
    )
    db_session.add(embedding)
    db_session.commit()

    mock_query_response = {
        "answer": "The team decided to use Postgres with pgvector.",
        "citations": [
            {
                "record_id": str(record.id),
                "chunk_id": None,
                "excerpt": "Team decided to use Postgres with pgvector",
            }
        ],
    }
    with patch("app.domains.ai.service.llm_client") as mock_llm:
        mock_llm.generate_embeddings.return_value = [[0.01] * 1536]
        mock_llm.query.return_value = mock_query_response
        resp = client.post(
            f"/api/v1/memory-spaces/{ms.id}/query",
            json={"question": "What database are we using?"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "Postgres" in data["answer"]
    assert len(data["citations"]) == 1
    cit = data["citations"][0]
    assert cit["record_id"] == str(record.id)
    assert cit["source_id"] == str(source.id)
    assert cit["excerpt"] == "Team decided to use Postgres with pgvector"


# --- Integration tests (extraction → summarize/query) ---


def _run_extraction(db_session, source):
    """Run the extraction pipeline with mocked LLM."""
    from app.processes.extraction import _run_extraction_pipeline

    mock_extraction = {
        "records": [
            {
                "record_type": "decision",
                "content": "Team decided to use Postgres with pgvector",
                "confidence": 0.95,
                "importance": "high",
                "evidence_text": "We decided to use Postgres.",
            },
        ]
    }
    with patch("app.domains.ai.service.llm_client") as mock_llm:
        mock_llm.extract.return_value = mock_extraction
        mock_llm.generate_embeddings.return_value = [[0.01] * 1536] * 10
        _run_extraction_pipeline(db_session, source.id)


def test_integration_extract_then_summarize(client, db_session):
    """Create source → extract → summarize references extracted records."""
    _seed_dev_user(db_session)
    ws = Workspace(owner_id=DEV_USER_ID, name="WS", description="")
    db_session.add(ws)
    db_session.commit()
    db_session.refresh(ws)

    ms = MemorySpace(
        workspace_id=ws.id, name="MS", description="", status="active"
    )
    db_session.add(ms)
    db_session.commit()
    db_session.refresh(ms)

    source = Source(
        memory_space_id=ms.id,
        source_type="note",
        title="Notes",
        processing_status="pending",
    )
    db_session.add(source)
    db_session.flush()
    content = SourceContent(
        source_id=source.id,
        content_text="We decided to use Postgres.",
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(source)

    _run_extraction(db_session, source)

    # Verify extraction completed
    db_session.refresh(source)
    assert source.processing_status == "completed"

    records = db_session.query(MemoryRecord).filter(
        MemoryRecord.memory_space_id == ms.id,
        MemoryRecord.deleted_at.is_(None),
    ).all()
    assert len(records) >= 1

    # Now call summarize
    mock_summary = {
        "title": "Project Summary",
        "content": "## Decisions\n\nPostgres with pgvector.",
    }
    with patch("app.domains.ai.service.llm_client") as mock_llm:
        mock_llm.summarize.return_value = mock_summary
        resp = client.post(
            f"/api/v1/memory-spaces/{ms.id}/summarize",
            json={"summary_type": "one_pager", "regenerate": True},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Project Summary"
    assert len(data["record_ids_used"]) >= 1
    # Verify extracted record IDs are in the summary
    extracted_ids = {str(r.id) for r in records}
    summary_ids = set(data["record_ids_used"])
    assert extracted_ids & summary_ids  # at least one overlap


def test_integration_extract_then_query(client, db_session):
    """Create source → extract → query returns answer with source_id in citations."""
    _seed_dev_user(db_session)
    ws = Workspace(owner_id=DEV_USER_ID, name="WS", description="")
    db_session.add(ws)
    db_session.commit()
    db_session.refresh(ws)

    ms = MemorySpace(
        workspace_id=ws.id, name="MS", description="", status="active"
    )
    db_session.add(ms)
    db_session.commit()
    db_session.refresh(ms)

    source = Source(
        memory_space_id=ms.id,
        source_type="note",
        title="Notes",
        processing_status="pending",
    )
    db_session.add(source)
    db_session.flush()
    content = SourceContent(
        source_id=source.id,
        content_text="We decided to use Postgres.",
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(source)

    _run_extraction(db_session, source)

    db_session.refresh(source)
    assert source.processing_status == "completed"

    # Get the extracted record for building mock response
    record = db_session.query(MemoryRecord).filter(
        MemoryRecord.memory_space_id == ms.id,
        MemoryRecord.deleted_at.is_(None),
    ).first()
    assert record is not None

    mock_query_result = {
        "answer": "The team uses Postgres with pgvector.",
        "citations": [
            {
                "record_id": str(record.id),
                "chunk_id": None,
                "excerpt": "Team decided to use Postgres with pgvector",
            }
        ],
    }
    with patch("app.domains.ai.service.llm_client") as mock_llm:
        mock_llm.generate_embeddings.return_value = [[0.01] * 1536]
        mock_llm.query.return_value = mock_query_result
        resp = client.post(
            f"/api/v1/memory-spaces/{ms.id}/query",
            json={"question": "What database?"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["citations"]) == 1
    assert data["citations"][0]["source_id"] == str(source.id)
    assert data["citations"][0]["record_id"] == str(record.id)
