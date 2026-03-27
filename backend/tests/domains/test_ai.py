"""Tests for AI service, extraction process, and extraction pipeline integration.

All LLM calls are mocked at the llm_client boundary — tests verify pipeline
orchestration and data persistence without making real API calls.
"""

import time
import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.domains.ai.models import (
    Citation,
    EmbeddingResult,
    ExtractionOutput,
    ExtractedRecord,
    QueryResult,
    SummaryResult,
)
from app.domains.ai.prompts.extraction import (
    EXTRACTION_PROMPT_VERSION,
    build_extraction_prompt,
)
from app.domains.ai.prompts.query import (
    QUERY_PROMPT_VERSION,
    build_query_prompt,
)
from app.domains.ai.prompts.summarization import (
    SUMMARIZATION_PROMPT_VERSION,
    build_summarization_prompt,
)
from app.domains.auth.models import User
from app.domains.memory.models import MemoryRecord, RecordSourceLink
from app.domains.memory_space.models import MemorySpace
from app.domains.source.models import Source, SourceChunk, SourceContent
from app.domains.workspace.models import Workspace

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# --- Fixtures ---


def _seed(db_session):
    """Create user + workspace + memory space for tests."""
    user = User(
        id=DEV_USER_ID,
        auth_provider="dev",
        auth_provider_id="dev-user-001",
        email="dev@projectmemory.local",
        display_name="Dev User",
    )
    db_session.add(user)
    db_session.commit()

    workspace = Workspace(
        owner_id=DEV_USER_ID,
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


def _create_source_with_content(db_session, ms, text_content="Some test content."):
    """Create a source + content directly in the DB (no extraction trigger)."""
    source = Source(
        memory_space_id=ms.id,
        source_type="note",
        title="Test Source",
        processing_status="pending",
    )
    db_session.add(source)
    db_session.flush()

    content = SourceContent(
        source_id=source.id,
        content_text=text_content,
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(source)
    return source


def _mock_extraction_response():
    """Return a valid-shaped extraction response dict."""
    return {
        "records": [
            {
                "record_type": "decision",
                "content": "Team decided to use Postgres with pgvector",
                "confidence": 0.95,
                "importance": "high",
                "evidence_text": "Some test content.",
            },
            {
                "record_type": "fact",
                "content": "The project uses Python 3.12",
                "confidence": 0.88,
                "importance": "medium",
                "evidence_text": None,
            },
        ]
    }


def _mock_embedding_vector():
    """Return a fake 1536-dim embedding vector."""
    return [0.01] * 1536


# ===== Domain Entity Tests =====


class TestAIEntities:
    def test_extracted_record_creation(self):
        rec = ExtractedRecord(
            record_type="decision",
            content="Use Postgres",
            confidence=0.95,
            importance="high",
            evidence_text="We agreed on Postgres",
        )
        assert rec.record_type == "decision"
        assert rec.confidence == 0.95

    def test_extraction_output_default(self):
        output = ExtractionOutput()
        assert output.records == []

    def test_summary_result(self):
        now = datetime.now()
        record_id = uuid.uuid4()
        result = SummaryResult(
            id=uuid.uuid4(),
            memory_space_id=uuid.uuid4(),
            summary_type="one_pager",
            title="Test",
            content="# Summary",
            is_edited=False,
            edited_content=None,
            record_ids_used=[record_id],
            generated_at=now,
            created_at=now,
            updated_at=now,
        )
        assert result.summary_type == "one_pager"
        assert result.is_edited is False
        assert result.record_ids_used == [record_id]

    def test_citation_with_chunk_id(self):
        cit = Citation(
            record_id=None,
            chunk_id=uuid.uuid4(),
            excerpt="some text",
        )
        assert cit.record_id is None
        assert cit.source_id is None
        assert cit.chunk_id is not None

    def test_citation_with_source_id(self):
        source_id = uuid.uuid4()
        cit = Citation(
            record_id=uuid.uuid4(),
            source_id=source_id,
            excerpt="evidence",
        )
        assert cit.source_id == source_id

    def test_query_result(self):
        result = QueryResult(answer="Test answer", citations=[])
        assert result.answer == "Test answer"

    def test_embedding_result(self):
        result = EmbeddingResult(
            entity_type="memory_record",
            entity_id=uuid.uuid4(),
            embedding=[0.1] * 1536,
        )
        assert len(result.embedding) == 1536


# ===== Prompt Build Tests =====


class TestPromptBuilders:
    def test_build_extraction_prompt_note(self):
        messages = build_extraction_prompt("Some content", "note")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Some content" in messages[1]["content"]
        assert "Note" in messages[0]["content"]

    def test_build_extraction_prompt_document(self):
        messages = build_extraction_prompt("Doc content", "document")
        assert "Document" in messages[0]["content"]

    def test_build_extraction_prompt_transcript(self):
        messages = build_extraction_prompt("Transcript", "transcript")
        assert "Transcript" in messages[0]["content"]

    def test_build_extraction_prompt_with_chunk_position(self):
        messages = build_extraction_prompt(
            "Chunk text", "note", chunk_position="section 2 of 4"
        )
        assert "section 2 of 4" in messages[0]["content"]

    def test_build_summarization_prompt_one_pager(self):
        records = [
            {"id": "abc", "record_type": "fact", "content": "Test", "importance": "high"}
        ]
        messages = build_summarization_prompt(records, "one_pager")
        assert len(messages) == 2
        assert "One-Pager" in messages[0]["content"]
        assert "Test" in messages[1]["content"]

    def test_build_summarization_prompt_recent_updates(self):
        records = [
            {"id": "abc", "record_type": "decision", "content": "Test", "importance": "medium"}
        ]
        messages = build_summarization_prompt(records, "recent_updates")
        assert "Recent Updates" in messages[0]["content"]

    def test_build_query_prompt(self):
        records = [
            {"id": "r1", "record_type": "fact", "content": "X is true", "importance": "high"}
        ]
        chunks = [
            {"id": "c1", "content": "Some raw text", "source_id": "s1"}
        ]
        messages = build_query_prompt("What is X?", records, chunks)
        assert len(messages) == 2
        assert "What is X?" in messages[1]["content"]
        assert "r1" in messages[1]["content"]
        assert "c1" in messages[1]["content"]

    def test_build_query_prompt_empty_context(self):
        messages = build_query_prompt("Question?", [], [])
        assert "No context available" in messages[1]["content"]


# ===== Extraction Validation Tests =====


class TestExtractionValidation:
    def test_valid_records_pass(self):
        from app.domains.ai.service import _validate_extraction_output

        raw = _mock_extraction_response()
        output = _validate_extraction_output(raw)
        assert len(output.records) == 2
        assert output.records[0].record_type == "decision"
        assert output.records[1].record_type == "fact"

    def test_invalid_record_type_skipped(self):
        from app.domains.ai.service import _validate_extraction_output

        raw = {"records": [
            {"record_type": "invalid_type", "content": "test", "confidence": 0.9, "importance": "medium"},
        ]}
        output = _validate_extraction_output(raw)
        assert len(output.records) == 0

    def test_empty_content_skipped(self):
        from app.domains.ai.service import _validate_extraction_output

        raw = {"records": [
            {"record_type": "fact", "content": "", "confidence": 0.9, "importance": "medium"},
        ]}
        output = _validate_extraction_output(raw)
        assert len(output.records) == 0

    def test_confidence_clamped(self):
        from app.domains.ai.service import _validate_extraction_output

        raw = {"records": [
            {"record_type": "fact", "content": "test", "confidence": 1.5, "importance": "medium"},
        ]}
        output = _validate_extraction_output(raw)
        assert output.records[0].confidence == 1.0

    def test_invalid_importance_defaults_to_medium(self):
        from app.domains.ai.service import _validate_extraction_output

        raw = {"records": [
            {"record_type": "fact", "content": "test", "confidence": 0.8, "importance": "critical"},
        ]}
        output = _validate_extraction_output(raw)
        assert output.records[0].importance == "medium"

    def test_missing_records_key(self):
        from app.domains.ai.service import _validate_extraction_output

        output = _validate_extraction_output({"no_records": []})
        assert len(output.records) == 0

    def test_records_not_a_list(self):
        from app.domains.ai.service import _validate_extraction_output

        output = _validate_extraction_output({"records": "not a list"})
        assert len(output.records) == 0

    def test_mixed_valid_and_invalid(self):
        from app.domains.ai.service import _validate_extraction_output

        raw = {"records": [
            {"record_type": "fact", "content": "valid", "confidence": 0.9, "importance": "medium"},
            {"record_type": "bogus", "content": "invalid type", "confidence": 0.9, "importance": "high"},
            {"record_type": "fact", "content": "", "confidence": 0.9, "importance": "low"},
            {"record_type": "decision", "content": "also valid", "confidence": 0.8, "importance": "high"},
        ]}
        output = _validate_extraction_output(raw)
        assert len(output.records) == 2
        assert output.records[0].content == "valid"
        assert output.records[1].content == "also valid"


# ===== Store Embeddings Tests =====


class TestStoreEmbeddings:
    def test_store_new_embeddings(self, db_session):
        from app.domains.ai.models import Embedding
        from app.domains.ai.service import store_embeddings

        entity_id = uuid.uuid4()
        results = [
            EmbeddingResult(
                entity_type="memory_record",
                entity_id=entity_id,
                embedding=_mock_embedding_vector(),
            )
        ]
        store_embeddings(db_session, results)

        stored = db_session.query(Embedding).filter(
            Embedding.entity_id == entity_id,
        ).first()
        assert stored is not None
        assert stored.entity_type == "memory_record"

    def test_upsert_replaces_existing(self, db_session):
        from app.domains.ai.models import Embedding
        from app.domains.ai.service import store_embeddings

        entity_id = uuid.uuid4()

        # Store initial
        results1 = [
            EmbeddingResult(
                entity_type="memory_record",
                entity_id=entity_id,
                embedding=[0.1] * 1536,
            )
        ]
        store_embeddings(db_session, results1)

        # Upsert with different vector
        results2 = [
            EmbeddingResult(
                entity_type="memory_record",
                entity_id=entity_id,
                embedding=[0.2] * 1536,
            )
        ]
        store_embeddings(db_session, results2)

        # Should still be one row
        count = db_session.query(Embedding).filter(
            Embedding.entity_id == entity_id,
        ).count()
        assert count == 1


# ===== Extraction Pipeline Integration Tests =====


class TestExtractionPipeline:
    """Integration tests for the full extraction pipeline.

    LLM client is mocked at the boundary — tests verify orchestration
    and data persistence.
    """

    @patch("app.domains.ai.service.llm_client")
    def test_full_pipeline_note_source(self, mock_llm, db_session):
        """Create note source → run extraction → verify records + chunks + embeddings."""
        _seed(db_session)
        _, ms = _seed(db_session) if False else (None, None)
        # Re-seed since _seed was already called above
        # Actually, let's just seed properly
        workspace = db_session.query(Workspace).first()
        ms = db_session.query(MemorySpace).first()

        if not workspace:
            _, ms = _seed(db_session)

        source = _create_source_with_content(
            db_session, ms,
            "We decided to use Postgres with pgvector for the MVP. The project uses Python 3.12."
        )

        # Mock LLM responses
        mock_llm.extract.return_value = _mock_extraction_response()
        mock_llm.generate_embeddings.return_value = [_mock_embedding_vector()] * 10

        # Run the extraction pipeline directly (not in a thread)
        from app.processes.extraction import _run_extraction_pipeline
        _run_extraction_pipeline(db_session, source.id)

        # Verify source status updated
        db_session.refresh(source)
        assert source.processing_status == "completed"

        # Verify memory records created
        records = db_session.query(MemoryRecord).filter(
            MemoryRecord.memory_space_id == ms.id,
            MemoryRecord.deleted_at.is_(None),
        ).all()
        assert len(records) == 2
        assert records[0].origin == "extracted"
        assert records[0].status == "active"

        # Verify record_source_links created
        links = db_session.query(RecordSourceLink).filter(
            RecordSourceLink.source_id == source.id,
            RecordSourceLink.deleted_at.is_(None),
        ).all()
        assert len(links) == 2

        # Verify source chunks created
        chunks = db_session.query(SourceChunk).filter(
            SourceChunk.source_id == source.id,
            SourceChunk.deleted_at.is_(None),
        ).all()
        assert len(chunks) >= 1

        # Verify embeddings generated for both chunks and records
        from app.domains.ai.models import Embedding
        chunk_embeddings = db_session.query(Embedding).filter(
            Embedding.entity_type == "source_chunk",
            Embedding.deleted_at.is_(None),
        ).all()
        assert len(chunk_embeddings) >= 1

        record_embeddings = db_session.query(Embedding).filter(
            Embedding.entity_type == "memory_record",
            Embedding.deleted_at.is_(None),
        ).all()
        assert len(record_embeddings) == 2

    @patch("app.domains.ai.service.llm_client")
    def test_pipeline_malformed_json_retry_then_fail(self, mock_llm, db_session):
        """LLM returns malformed JSON → extraction marks source as failed."""
        _seed(db_session)
        ms = db_session.query(MemorySpace).first()
        source = _create_source_with_content(db_session, ms)

        # Mock LLM to raise ValueError (simulating malformed JSON after retry)
        mock_llm.extract.side_effect = ValueError("LLM returned invalid JSON")

        from app.processes.extraction import _run_extraction_pipeline
        with pytest.raises(ValueError):
            _run_extraction_pipeline(db_session, source.id)

        # The outer run_extraction() would catch this and mark as failed.
        # Since we called _run_extraction_pipeline directly, we verify
        # the status was set to "processing" before the error
        db_session.refresh(source)
        assert source.processing_status == "processing"

    @patch("app.domains.ai.service.llm_client")
    def test_pipeline_zero_records_marks_failed(self, mock_llm, db_session):
        """Extraction producing zero records from non-empty content → source marked failed."""
        _seed(db_session)
        ms = db_session.query(MemorySpace).first()
        source = _create_source_with_content(db_session, ms, "Non-empty content here.")

        mock_llm.extract.return_value = {"records": []}

        from app.processes.extraction import _run_extraction_pipeline
        _run_extraction_pipeline(db_session, source.id)

        db_session.refresh(source)
        assert source.processing_status == "failed"
        assert "zero records" in source.processing_error.lower()

    @patch("app.domains.ai.service.llm_client")
    def test_pipeline_empty_content_zero_records_ok(self, mock_llm, db_session):
        """Empty source content with zero records → not a failure (completed with 0 records)."""
        _seed(db_session)
        ms = db_session.query(MemorySpace).first()
        source = _create_source_with_content(db_session, ms, "   ")

        mock_llm.extract.return_value = {"records": []}
        mock_llm.generate_embeddings.return_value = [_mock_embedding_vector()]

        from app.processes.extraction import _run_extraction_pipeline
        _run_extraction_pipeline(db_session, source.id)

        db_session.refresh(source)
        assert source.processing_status == "completed"

    @patch("app.domains.ai.service.llm_client")
    def test_pipeline_evidence_offsets_computed(self, mock_llm, db_session):
        """Evidence text offsets are computed via string matching."""
        _seed(db_session)
        ms = db_session.query(MemorySpace).first()

        content = "The team decided to use Postgres. Budget is 500K."
        source = _create_source_with_content(db_session, ms, content)

        mock_llm.extract.return_value = {
            "records": [
                {
                    "record_type": "decision",
                    "content": "Team decided to use Postgres",
                    "confidence": 0.95,
                    "importance": "high",
                    "evidence_text": "decided to use Postgres",
                },
            ]
        }
        mock_llm.generate_embeddings.return_value = [_mock_embedding_vector()] * 5

        from app.processes.extraction import _run_extraction_pipeline
        _run_extraction_pipeline(db_session, source.id)

        link = db_session.query(RecordSourceLink).filter(
            RecordSourceLink.source_id == source.id,
            RecordSourceLink.deleted_at.is_(None),
        ).first()
        assert link is not None
        assert link.evidence_text == "decided to use Postgres"
        assert link.evidence_start_offset == content.find("decided to use Postgres")
        assert link.evidence_end_offset == link.evidence_start_offset + len("decided to use Postgres")

    @patch("app.domains.ai.service.llm_client")
    def test_pipeline_embedding_failure_propagates(self, mock_llm, db_session):
        """If embedding generation fails, the error propagates."""
        _seed(db_session)
        ms = db_session.query(MemorySpace).first()
        source = _create_source_with_content(db_session, ms)

        mock_llm.extract.return_value = _mock_extraction_response()
        mock_llm.generate_embeddings.side_effect = RuntimeError("OpenAI API error")

        from app.processes.extraction import _run_extraction_pipeline
        with pytest.raises(RuntimeError):
            _run_extraction_pipeline(db_session, source.id)


# ===== run_extraction Error Handling Tests =====


class TestRunExtractionErrorHandling:
    """Test the outer run_extraction() that catches errors and marks source as failed."""

    @patch("app.processes.extraction.SessionLocal")
    @patch("app.processes.extraction.source_service")
    @patch("app.processes.extraction.ai_service")
    def test_run_extraction_marks_failed_on_error(
        self, mock_ai, mock_source_svc, mock_session_factory
    ):
        """run_extraction catches exceptions and marks source as failed."""
        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db

        # Simulate get_source_internal raising an error
        mock_source_svc.get_source_internal.side_effect = RuntimeError("DB error")

        from app.processes.extraction import run_extraction
        source_id = uuid.uuid4()
        run_extraction(source_id)

        # Should have called update_source_status with "failed"
        mock_source_svc.update_source_status.assert_called_once()
        call_args = mock_source_svc.update_source_status.call_args
        assert call_args[0][2] == "failed"
        assert "DB error" in call_args[0][3]

        mock_db.close.assert_called_once()


# ===== Background Thread Trigger Tests =====


class TestExtractionTrigger:
    """Test that source creation triggers extraction in a background thread."""

    @patch("app.domains.source.service._trigger_extraction")
    def test_note_creation_triggers_extraction(self, mock_trigger, db_session):
        _seed(db_session)
        ms = db_session.query(MemorySpace).first()

        from app.domains.source.models import SourceCreateNote
        from app.domains.source.service import create_note_source

        data = SourceCreateNote(source_type="note", title="Test", content="Hello")
        entity = create_note_source(db_session, ms.id, DEV_USER_ID, data)

        mock_trigger.assert_called_once_with(entity.id)

    @patch("app.domains.source.service._trigger_extraction")
    def test_document_creation_triggers_extraction(self, mock_trigger, db_session):
        import io

        _seed(db_session)
        ms = db_session.query(MemorySpace).first()

        from app.domains.source.service import create_document_source

        # Create a mock file object
        mock_file = MagicMock()
        mock_file.file = io.BytesIO(b"Hello world document content")
        mock_file.content_type = "text/plain"
        mock_file.filename = "test.txt"

        entity = create_document_source(
            db_session, ms.id, DEV_USER_ID, "Test Doc", mock_file
        )

        mock_trigger.assert_called_once_with(entity.id)
