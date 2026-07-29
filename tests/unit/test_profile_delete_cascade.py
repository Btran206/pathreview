"""Reproduces issue #80: DELETE /profiles/{profile_id} doesn't cascade to
delete associated reviews and embeddings.

Postgres-side cascades for Review and IngestedSource rows are configured
correctly (ondelete="CASCADE" + relationship cascade="all, delete-orphan"),
and core.services.profile_service.delete_profile() also deletes those rows
explicitly. But delete_profile() never calls
rag.retriever.vector_store.VectorStore.delete_by_source_id() for the
profile's ingested sources, so the ChromaDB embeddings for a deleted
profile are orphaned.

This test seeds a real (ephemeral, on-disk temp) ChromaDB collection with
an embedding tied to a profile's ingested source, runs delete_profile()
against a mocked DB session, and shows the embedding survives the delete.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from core.services.profile_service import delete_profile
from rag.retriever.vector_store import VectorStore


class FakeChunk:
    def __init__(
        self,
        id: str,
        source_id: str,
        text: str,
        chunk_index: int = 0,
        section: str | None = None,
    ) -> None:
        self.id = id
        self.source_id = source_id
        self.text = text
        self.chunk_index = chunk_index
        self.section = section


@pytest.mark.unit
class TestProfileDeleteCascadeEmbeddings:

    @pytest.fixture
    def vector_store(self, tmp_path: Path) -> VectorStore:
        return VectorStore(persist_dir=str(tmp_path / "chromadb"))

    @pytest.mark.asyncio
    async def test_delete_profile_leaves_embeddings_orphaned(
        self, vector_store: VectorStore
    ) -> None:
        profile_id = uuid4()
        user_id = uuid4()
        source_id = str(uuid4())
        collection_name = f"profile_{profile_id}"

        # Seed the vector store the way ingestion would: one embedded chunk
        # belonging to this profile's ingested source.
        chunk = FakeChunk(id=str(uuid4()), source_id=source_id, text="Experienced Python engineer")
        vector_store.add_chunks([(chunk, [0.1, 0.2, 0.3])], collection_name)

        # Sanity check the embedding actually exists before deletion.
        assert vector_store.get_collection(collection_name).count() == 1

        fake_profile = Mock(id=profile_id, user_id=user_id)
        fake_source = Mock(id=source_id, profile_id=profile_id)

        mock_db = AsyncMock()

        review_result = Mock()
        review_result.scalars.return_value.all.return_value = []

        source_result = Mock()
        source_result.scalars.return_value.all.return_value = [fake_source]

        mock_db.execute = AsyncMock(side_effect=[review_result, source_result])
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        async def fake_get_profile(db: Any, pid: UUID, uid: UUID) -> Mock:
            return fake_profile

        with patch("core.services.profile_service.get_profile", fake_get_profile):
            deleted = await delete_profile(mock_db, profile_id, user_id)

        assert deleted is True

        # BUG: the embedding for this profile's source is still in ChromaDB
        # even though the Profile/IngestedSource rows are gone from Postgres.
        remaining = vector_store.get_collection(collection_name).count()
        assert remaining == 0, (
            f"Expected delete_profile() to purge ChromaDB embeddings for the "
            f"profile's ingested sources, but {remaining} embedding(s) remain. "
            f"delete_profile() never calls VectorStore.delete_by_source_id()."
        )
