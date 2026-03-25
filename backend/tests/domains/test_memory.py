import uuid
from decimal import Decimal

import pytest

from app.domains.auth.models import User
from app.domains.memory.models import (
    MemoryRecord,
    MemoryRecordEntity,
    RecordCreate,
    RecordListResponse,
    RecordResponse,
    RecordSourceLink,
    RecordSourceLinkEntity,
    RecordSourceLinkResponse,
    RecordUpdate,
)
from app.domains.memory_space.models import MemorySpace
from app.domains.source.models import Source, SourceContent
from app.domains.workspace.models import Workspace

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


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


def _seed_other_user(db_session) -> None:
    user = User(
        id=OTHER_USER_ID,
        auth_provider="dev",
        auth_provider_id="dev-user-002",
        email="other@projectmemory.local",
        display_name="Other User",
    )
    db_session.add(user)
    db_session.commit()


def _create_workspace_and_space(db_session, owner_id=DEV_USER_ID):
    workspace = Workspace(
        owner_id=owner_id,
        name="Test Workspace",
        description="",
    )
    db_session.add(workspace)
    db_session.commit()
    db_session.refresh(workspace)

    ms = MemorySpace(
        workspace_id=workspace.id,
        name="Test Space",
        description="",
        status="active",
    )
    db_session.add(ms)
    db_session.commit()
    db_session.refresh(ms)
    return workspace, ms


def _create_source_with_content(db_session, memory_space_id, content_text="Source content here"):
    """Create a source + content for testing record-source links."""
    source = Source(
        memory_space_id=memory_space_id,
        source_type="note",
        title="Test Source",
        processing_status="completed",
    )
    db_session.add(source)
    db_session.flush()

    content = SourceContent(
        source_id=source.id,
        content_text=content_text,
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(source)
    return source


# ===== Entity Tests =====


class TestMemoryRecordEntity:
    def test_from_orm(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        record = MemoryRecord(
            memory_space_id=ms.id,
            record_type="fact",
            content="Python is a programming language",
            origin="manual",
            status="active",
            confidence=Decimal("1.00"),
            importance="medium",
            record_metadata={},
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        entity = MemoryRecordEntity.from_orm(record)
        assert entity.id == record.id
        assert entity.memory_space_id == ms.id
        assert entity.record_type == "fact"
        assert entity.content == "Python is a programming language"
        assert entity.origin == "manual"
        assert entity.status == "active"
        assert entity.confidence == Decimal("1.00")
        assert entity.importance == "medium"
        assert entity.metadata == {}
        assert entity.created_at is not None
        assert entity.updated_at is not None


class TestRecordSourceLinkEntity:
    def test_from_orm(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        record = MemoryRecord(
            memory_space_id=ms.id,
            record_type="fact",
            content="Test fact",
            origin="extracted",
            status="active",
            confidence=Decimal("0.85"),
            importance="high",
            record_metadata={},
        )
        db_session.add(record)
        db_session.flush()

        source = _create_source_with_content(db_session, ms.id)

        link = RecordSourceLink(
            record_id=record.id,
            source_id=source.id,
            evidence_text="some evidence",
            evidence_start_offset=10,
            evidence_end_offset=23,
        )
        db_session.add(link)
        db_session.commit()
        db_session.refresh(link)

        entity = RecordSourceLinkEntity.from_orm(link)
        assert entity.id == link.id
        assert entity.record_id == record.id
        assert entity.source_id == source.id
        assert entity.evidence_text == "some evidence"
        assert entity.evidence_start_offset == 10
        assert entity.evidence_end_offset == 23
        assert entity.created_at is not None


# ===== Schema Validation Tests =====


class TestRecordCreate:
    def test_valid_defaults(self):
        schema = RecordCreate(record_type="fact", content="A fact")
        assert schema.record_type == "fact"
        assert schema.content == "A fact"
        assert schema.importance == "medium"
        assert schema.metadata == {}

    def test_valid_all_fields(self):
        schema = RecordCreate(
            record_type="decision",
            content="We chose React",
            importance="high",
            metadata={"context": "frontend"},
        )
        assert schema.record_type == "decision"
        assert schema.importance == "high"
        assert schema.metadata == {"context": "frontend"}

    def test_invalid_record_type_rejected(self):
        with pytest.raises(Exception):
            RecordCreate(record_type="invalid", content="stuff")

    def test_invalid_importance_rejected(self):
        with pytest.raises(Exception):
            RecordCreate(record_type="fact", content="stuff", importance="critical")

    def test_all_valid_record_types(self):
        valid_types = ["fact", "event", "decision", "issue", "question", "preference", "task", "insight"]
        for rt in valid_types:
            schema = RecordCreate(record_type=rt, content="test")
            assert schema.record_type == rt


class TestRecordUpdate:
    def test_all_optional(self):
        schema = RecordUpdate()
        assert schema.content is None
        assert schema.status is None
        assert schema.importance is None
        assert schema.metadata is None

    def test_partial_update(self):
        schema = RecordUpdate(status="archived", importance="high")
        assert schema.status == "archived"
        assert schema.importance == "high"
        assert schema.content is None

    def test_invalid_status_rejected(self):
        with pytest.raises(Exception):
            RecordUpdate(status="deleted")

    def test_invalid_importance_rejected(self):
        with pytest.raises(Exception):
            RecordUpdate(importance="critical")


# ===== Service Tests =====


class TestCreateRecord:
    def test_creates_manual_record(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        data = RecordCreate(record_type="fact", content="Python is great")
        entity = service.create_record(db_session, ms.id, DEV_USER_ID, data)

        assert isinstance(entity, MemoryRecordEntity)
        assert entity.record_type == "fact"
        assert entity.content == "Python is great"
        assert entity.origin == "manual"
        assert entity.status == "active"
        assert entity.confidence == Decimal("1.00")
        assert entity.importance == "medium"
        assert entity.metadata == {}

    def test_rejects_nonexistent_memory_space(self, db_session):
        _seed_dev_user(db_session)
        from app.domains.memory import service
        from app.core.exceptions import NotFoundError

        data = RecordCreate(record_type="fact", content="test")
        with pytest.raises(NotFoundError):
            service.create_record(db_session, uuid.uuid4(), DEV_USER_ID, data)

    def test_rejects_other_user(self, db_session):
        _seed_dev_user(db_session)
        _seed_other_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service
        from app.core.exceptions import ForbiddenError

        data = RecordCreate(record_type="fact", content="test")
        with pytest.raises(ForbiddenError):
            service.create_record(db_session, ms.id, OTHER_USER_ID, data)


class TestBulkCreateRecords:
    def test_creates_multiple_records_and_links(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)
        source = _create_source_with_content(
            db_session, ms.id, "Python is a programming language. It was created by Guido."
        )

        from app.domains.memory import service

        extracted_records = [
            {
                "record_type": "fact",
                "content": "Python is a programming language",
                "confidence": 0.95,
                "importance": "high",
                "evidence_text": "Python is a programming language",
            },
            {
                "record_type": "fact",
                "content": "Created by Guido",
                "confidence": 0.90,
                "importance": "medium",
                "evidence_text": "It was created by Guido",
            },
        ]

        entities = service.bulk_create_records(
            db_session, ms.id, source.id, extracted_records
        )

        assert len(entities) == 2
        assert entities[0].record_type == "fact"
        assert entities[0].origin == "extracted"
        assert entities[0].status == "active"

        # Verify links were created
        links = db_session.query(RecordSourceLink).filter(
            RecordSourceLink.source_id == source.id,
            RecordSourceLink.deleted_at.is_(None),
        ).all()
        assert len(links) == 2

    def test_computes_evidence_offsets(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)
        content_text = "The sky is blue. Water is wet."
        source = _create_source_with_content(db_session, ms.id, content_text)

        from app.domains.memory import service

        extracted_records = [
            {
                "record_type": "fact",
                "content": "The sky is blue",
                "confidence": 0.95,
                "importance": "medium",
                "evidence_text": "The sky is blue",
            },
        ]

        service.bulk_create_records(db_session, ms.id, source.id, extracted_records)

        link = db_session.query(RecordSourceLink).filter(
            RecordSourceLink.source_id == source.id,
            RecordSourceLink.deleted_at.is_(None),
        ).first()

        assert link.evidence_start_offset == 0
        assert link.evidence_end_offset == 15  # len("The sky is blue")


class TestComputeEvidenceOffsets:
    def test_exact_match(self):
        from app.domains.memory.service import _compute_evidence_offsets

        start, end = _compute_evidence_offsets("Hello world", "Hello world")
        assert start == 0
        assert end == 11

    def test_substring_match(self):
        from app.domains.memory.service import _compute_evidence_offsets

        start, end = _compute_evidence_offsets("The sky is blue today", "sky is blue")
        assert start == 4
        assert end == 15

    def test_not_found_returns_none(self):
        from app.domains.memory.service import _compute_evidence_offsets

        start, end = _compute_evidence_offsets("Hello world", "missing text")
        assert start is None
        assert end is None

    def test_empty_evidence(self):
        from app.domains.memory.service import _compute_evidence_offsets

        start, end = _compute_evidence_offsets("Hello world", "")
        assert start is None
        assert end is None


class TestListRecords:
    def test_list_empty(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        entities, total = service.list_records(db_session, ms.id, DEV_USER_ID)
        assert entities == []
        assert total == 0

    def test_list_with_records(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        for i in range(3):
            data = RecordCreate(record_type="fact", content=f"Fact {i}")
            service.create_record(db_session, ms.id, DEV_USER_ID, data)

        entities, total = service.list_records(db_session, ms.id, DEV_USER_ID)
        assert total == 3
        assert len(entities) == 3

    def test_pagination(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        for i in range(5):
            data = RecordCreate(record_type="fact", content=f"Fact {i}")
            service.create_record(db_session, ms.id, DEV_USER_ID, data)

        entities, total = service.list_records(
            db_session, ms.id, DEV_USER_ID, page=1, page_size=2
        )
        assert total == 5
        assert len(entities) == 2

    def test_filter_by_record_type(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        service.create_record(db_session, ms.id, DEV_USER_ID, RecordCreate(record_type="fact", content="A fact"))
        service.create_record(db_session, ms.id, DEV_USER_ID, RecordCreate(record_type="event", content="An event"))
        service.create_record(db_session, ms.id, DEV_USER_ID, RecordCreate(record_type="fact", content="Another fact"))

        entities, total = service.list_records(
            db_session, ms.id, DEV_USER_ID, record_type="fact"
        )
        assert total == 2

    def test_filter_by_status(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        entity = service.create_record(
            db_session, ms.id, DEV_USER_ID,
            RecordCreate(record_type="fact", content="A fact"),
        )
        # Archive one
        service.update_record(
            db_session, entity.id, DEV_USER_ID,
            RecordUpdate(status="archived"),
        )
        service.create_record(
            db_session, ms.id, DEV_USER_ID,
            RecordCreate(record_type="fact", content="Active fact"),
        )

        entities, total = service.list_records(
            db_session, ms.id, DEV_USER_ID, status="active"
        )
        assert total == 1

    def test_filter_by_importance(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        service.create_record(
            db_session, ms.id, DEV_USER_ID,
            RecordCreate(record_type="fact", content="Low fact", importance="low"),
        )
        service.create_record(
            db_session, ms.id, DEV_USER_ID,
            RecordCreate(record_type="fact", content="High fact", importance="high"),
        )

        entities, total = service.list_records(
            db_session, ms.id, DEV_USER_ID, importance="high"
        )
        assert total == 1
        assert entities[0].importance == "high"

    def test_combined_filters(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        service.create_record(
            db_session, ms.id, DEV_USER_ID,
            RecordCreate(record_type="fact", content="High fact", importance="high"),
        )
        service.create_record(
            db_session, ms.id, DEV_USER_ID,
            RecordCreate(record_type="event", content="High event", importance="high"),
        )
        service.create_record(
            db_session, ms.id, DEV_USER_ID,
            RecordCreate(record_type="fact", content="Low fact", importance="low"),
        )

        entities, total = service.list_records(
            db_session, ms.id, DEV_USER_ID, record_type="fact", importance="high"
        )
        assert total == 1
        assert entities[0].content == "High fact"


class TestGetRecord:
    def test_get_record(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        data = RecordCreate(record_type="fact", content="Test fact")
        created = service.create_record(db_session, ms.id, DEV_USER_ID, data)

        entity = service.get_record(db_session, created.id, DEV_USER_ID)
        assert entity.id == created.id
        assert entity.content == "Test fact"

    def test_not_found(self, db_session):
        _seed_dev_user(db_session)
        from app.domains.memory import service
        from app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            service.get_record(db_session, uuid.uuid4(), DEV_USER_ID)

    def test_deleted_record_not_found(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service
        from app.core.exceptions import NotFoundError

        data = RecordCreate(record_type="fact", content="Delete me")
        created = service.create_record(db_session, ms.id, DEV_USER_ID, data)
        service.delete_record(db_session, created.id, DEV_USER_ID)

        with pytest.raises(NotFoundError):
            service.get_record(db_session, created.id, DEV_USER_ID)

    def test_wrong_owner(self, db_session):
        _seed_dev_user(db_session)
        _seed_other_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service
        from app.core.exceptions import ForbiddenError

        data = RecordCreate(record_type="fact", content="My fact")
        created = service.create_record(db_session, ms.id, DEV_USER_ID, data)

        with pytest.raises(ForbiddenError):
            service.get_record(db_session, created.id, OTHER_USER_ID)


class TestUpdateRecord:
    def test_partial_update_content(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        data = RecordCreate(record_type="fact", content="Original")
        created = service.create_record(db_session, ms.id, DEV_USER_ID, data)

        updated = service.update_record(
            db_session, created.id, DEV_USER_ID,
            RecordUpdate(content="Updated content"),
        )
        assert updated.content == "Updated content"
        assert updated.id == created.id

    def test_status_transition(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        data = RecordCreate(record_type="fact", content="A fact")
        created = service.create_record(db_session, ms.id, DEV_USER_ID, data)
        assert created.status == "active"

        updated = service.update_record(
            db_session, created.id, DEV_USER_ID,
            RecordUpdate(status="archived"),
        )
        assert updated.status == "archived"

    def test_importance_change(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        data = RecordCreate(record_type="fact", content="A fact", importance="low")
        created = service.create_record(db_session, ms.id, DEV_USER_ID, data)

        updated = service.update_record(
            db_session, created.id, DEV_USER_ID,
            RecordUpdate(importance="high"),
        )
        assert updated.importance == "high"

    def test_metadata_update(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service

        data = RecordCreate(record_type="fact", content="A fact")
        created = service.create_record(db_session, ms.id, DEV_USER_ID, data)

        updated = service.update_record(
            db_session, created.id, DEV_USER_ID,
            RecordUpdate(metadata={"tag": "important"}),
        )
        assert updated.metadata == {"tag": "important"}


class TestDeleteRecord:
    def test_soft_deletes_record(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service
        from app.core.exceptions import NotFoundError

        data = RecordCreate(record_type="fact", content="Delete me")
        created = service.create_record(db_session, ms.id, DEV_USER_ID, data)

        service.delete_record(db_session, created.id, DEV_USER_ID)

        with pytest.raises(NotFoundError):
            service.get_record(db_session, created.id, DEV_USER_ID)

    def test_cascade_soft_deletes_links(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)
        source = _create_source_with_content(db_session, ms.id, "Some text here")

        from app.domains.memory import service

        extracted_records = [
            {
                "record_type": "fact",
                "content": "Some fact",
                "confidence": 0.90,
                "importance": "medium",
                "evidence_text": "Some text here",
            },
        ]
        entities = service.bulk_create_records(db_session, ms.id, source.id, extracted_records)

        service.delete_record(db_session, entities[0].id, DEV_USER_ID)

        db_session.expire_all()
        links = db_session.query(RecordSourceLink).filter(
            RecordSourceLink.record_id == entities[0].id,
            RecordSourceLink.deleted_at.is_(None),
        ).all()
        assert len(links) == 0

    def test_cascade_soft_deletes_embeddings(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)

        from app.domains.memory import service
        from app.domains.ai.models import Embedding
        import numpy as np

        data = RecordCreate(record_type="fact", content="A fact")
        created = service.create_record(db_session, ms.id, DEV_USER_ID, data)

        # Create an embedding for this record
        embedding = Embedding(
            entity_type="memory_record",
            entity_id=created.id,
            embedding=np.zeros(1536).tolist(),
            model_id="test-model",
        )
        db_session.add(embedding)
        db_session.commit()

        service.delete_record(db_session, created.id, DEV_USER_ID)

        db_session.expire_all()
        emb = db_session.query(Embedding).filter(
            Embedding.entity_id == created.id,
            Embedding.deleted_at.is_(None),
        ).first()
        assert emb is None

    def test_not_found(self, db_session):
        _seed_dev_user(db_session)
        from app.domains.memory import service
        from app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            service.delete_record(db_session, uuid.uuid4(), DEV_USER_ID)


class TestGetRecordSources:
    def test_returns_denormalized_source_info(self, db_session):
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)
        source = _create_source_with_content(
            db_session, ms.id, "Evidence text in the source"
        )

        from app.domains.memory import service

        extracted_records = [
            {
                "record_type": "fact",
                "content": "A fact from source",
                "confidence": 0.90,
                "importance": "medium",
                "evidence_text": "Evidence text",
            },
        ]
        entities = service.bulk_create_records(db_session, ms.id, source.id, extracted_records)

        links = service.get_record_sources(db_session, entities[0].id, DEV_USER_ID)
        assert len(links) == 1
        assert links[0].source_title == "Test Source"
        assert links[0].source_type == "note"
        assert links[0].evidence_text == "Evidence text"
        assert links[0].source_id == source.id
        assert links[0].record_id == entities[0].id


# ===== Router Tests =====


class TestMemoryRouter:
    def _setup(self, client, db_session):
        """Seed user, workspace, and memory space for router tests."""
        _seed_dev_user(db_session)
        workspace, ms = _create_workspace_and_space(db_session)
        return ms

    def test_create_record_via_api(self, client, db_session):
        ms = self._setup(client, db_session)
        resp = client.post(
            f"/api/v1/memory-spaces/{ms.id}/records",
            json={
                "record_type": "fact",
                "content": "API created fact",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["record_type"] == "fact"
        assert data["content"] == "API created fact"
        assert data["origin"] == "manual"
        assert data["status"] == "active"
        assert data["confidence"] == "1.00"
        assert data["importance"] == "medium"
        assert "id" in data

    def test_create_record_with_importance(self, client, db_session):
        ms = self._setup(client, db_session)
        resp = client.post(
            f"/api/v1/memory-spaces/{ms.id}/records",
            json={
                "record_type": "decision",
                "content": "We chose FastAPI",
                "importance": "high",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["importance"] == "high"

    def test_create_record_invalid_type(self, client, db_session):
        ms = self._setup(client, db_session)
        resp = client.post(
            f"/api/v1/memory-spaces/{ms.id}/records",
            json={
                "record_type": "invalid_type",
                "content": "stuff",
            },
        )
        assert resp.status_code == 422

    def test_list_records_via_api(self, client, db_session):
        ms = self._setup(client, db_session)
        for i in range(3):
            client.post(
                f"/api/v1/memory-spaces/{ms.id}/records",
                json={"record_type": "fact", "content": f"Fact {i}"},
            )

        resp = client.get(f"/api/v1/memory-spaces/{ms.id}/records")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_list_records_pagination(self, client, db_session):
        ms = self._setup(client, db_session)
        for i in range(5):
            client.post(
                f"/api/v1/memory-spaces/{ms.id}/records",
                json={"record_type": "fact", "content": f"Fact {i}"},
            )

        resp = client.get(
            f"/api/v1/memory-spaces/{ms.id}/records",
            params={"page_size": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2

    def test_list_records_filter_type(self, client, db_session):
        ms = self._setup(client, db_session)
        client.post(
            f"/api/v1/memory-spaces/{ms.id}/records",
            json={"record_type": "fact", "content": "A fact"},
        )
        client.post(
            f"/api/v1/memory-spaces/{ms.id}/records",
            json={"record_type": "event", "content": "An event"},
        )

        resp = client.get(
            f"/api/v1/memory-spaces/{ms.id}/records",
            params={"record_type": "fact"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_record_via_api(self, client, db_session):
        ms = self._setup(client, db_session)
        create_resp = client.post(
            f"/api/v1/memory-spaces/{ms.id}/records",
            json={"record_type": "fact", "content": "A fact"},
        )
        record_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/records/{record_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == record_id
        assert data["content"] == "A fact"

    def test_get_record_not_found(self, client, db_session):
        _seed_dev_user(db_session)
        resp = client.get(f"/api/v1/records/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_update_record_via_api(self, client, db_session):
        ms = self._setup(client, db_session)
        create_resp = client.post(
            f"/api/v1/memory-spaces/{ms.id}/records",
            json={"record_type": "fact", "content": "Original"},
        )
        record_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/records/{record_id}",
            json={"content": "Updated", "status": "archived"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "Updated"
        assert data["status"] == "archived"

    def test_delete_record_via_api(self, client, db_session):
        ms = self._setup(client, db_session)
        create_resp = client.post(
            f"/api/v1/memory-spaces/{ms.id}/records",
            json={"record_type": "fact", "content": "Delete me"},
        )
        record_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/records/{record_id}")
        assert resp.status_code == 204

        # Verify it's gone
        resp = client.get(f"/api/v1/records/{record_id}")
        assert resp.status_code == 404

    def test_get_record_sources_via_api(self, client, db_session):
        ms = self._setup(client, db_session)
        source = _create_source_with_content(
            db_session, ms.id, "Evidence text in the source"
        )

        from app.domains.memory import service

        extracted_records = [
            {
                "record_type": "fact",
                "content": "A fact",
                "confidence": 0.90,
                "importance": "medium",
                "evidence_text": "Evidence text",
            },
        ]
        entities = service.bulk_create_records(db_session, ms.id, source.id, extracted_records)

        resp = client.get(f"/api/v1/records/{entities[0].id}/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["source_title"] == "Test Source"
        assert data[0]["source_type"] == "note"
        assert data[0]["evidence_text"] == "Evidence text"
