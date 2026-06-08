"""Unit tests for the Memory subsystem (OTM, MemoryManager, StorageBackend)."""

import os
import tempfile
import pytest

from acos.memory.store import StorageBackend
from acos.memory.otm import OrthogonalThreadMemory
from acos.memory.manager import MemoryManager
from acos.schemas.models import MemoryRecord, MemoryType


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
async def storage(db_path):
    s = StorageBackend(db_path=db_path)
    await s.initialize()
    yield s
    await s.close()


@pytest.fixture
async def otm(storage):
    return OrthogonalThreadMemory(storage)


@pytest.fixture
async def memory_manager(storage):
    return MemoryManager(storage)


class TestStorageBackend:
    """Tests for the SQLite storage backend."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, storage):
        """Test storing and retrieving a memory record."""
        record = MemoryRecord(
            thread_id="thread-1",
            memory_type=MemoryType.WORKING,
            content="Test memory content",
        )
        await storage.store_memory(record)

        retrieved = await storage.retrieve_memory(record.id)
        assert retrieved is not None
        assert retrieved.content == "Test memory content"
        assert retrieved.thread_id == "thread-1"
        assert retrieved.memory_type == MemoryType.WORKING

    @pytest.mark.asyncio
    async def test_query_by_thread(self, storage):
        """Test querying memories by thread ID."""
        for i in range(5):
            await storage.store_memory(MemoryRecord(
                thread_id="thread-1",
                content=f"Memory {i}",
            ))
        for i in range(3):
            await storage.store_memory(MemoryRecord(
                thread_id="thread-2",
                content=f"Other memory {i}",
            ))

        t1_memories = await storage.query_memories(thread_id="thread-1")
        t2_memories = await storage.query_memories(thread_id="thread-2")

        assert len(t1_memories) == 5
        assert len(t2_memories) == 3

    @pytest.mark.asyncio
    async def test_query_by_type(self, storage):
        """Test querying memories by type."""
        await storage.store_memory(MemoryRecord(
            thread_id="t1", memory_type=MemoryType.WORKING, content="Working",
        ))
        await storage.store_memory(MemoryRecord(
            thread_id="t1", memory_type=MemoryType.SEMANTIC, content="Semantic",
        ))

        working = await storage.query_memories(memory_type=MemoryType.WORKING)
        semantic = await storage.query_memories(memory_type=MemoryType.SEMANTIC)

        assert len(working) == 1
        assert len(semantic) == 1

    @pytest.mark.asyncio
    async def test_search(self, storage):
        """Test keyword search."""
        await storage.store_memory(MemoryRecord(
            thread_id="t1", content="Quantum computing uses qubits",
        ))
        await storage.store_memory(MemoryRecord(
            thread_id="t2", content="Classical computing uses bits",
        ))

        results = await storage.search_memories("quantum")
        assert len(results) == 1
        assert "qubits" in results[0].content

    @pytest.mark.asyncio
    async def test_delete(self, storage):
        """Test deleting a memory record."""
        record = MemoryRecord(thread_id="t1", content="To delete")
        await storage.store_memory(record)

        deleted = await storage.delete_memory(record.id)
        assert deleted is True

        retrieved = await storage.retrieve_memory(record.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_count(self, storage):
        """Test counting memories."""
        await storage.store_memory(MemoryRecord(
            thread_id="t1", memory_type=MemoryType.WORKING, content="W1",
        ))
        await storage.store_memory(MemoryRecord(
            thread_id="t1", memory_type=MemoryType.SEMANTIC, content="S1",
        ))

        total = await storage.count_memories()
        working = await storage.count_memories(memory_type=MemoryType.WORKING)
        assert total == 2
        assert working == 1


class TestOrthogonalThreadMemory:
    """Tests for OTM - memory isolation."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, otm):
        """Test storing and retrieving within a thread."""
        await otm.store("thread-1", "Memory for thread 1")
        await otm.store("thread-2", "Memory for thread 2")

        t1 = await otm.retrieve("thread-1")
        t2 = await otm.retrieve("thread-2")

        assert len(t1) == 1
        assert len(t2) == 1
        assert t1[0].content == "Memory for thread 1"
        assert t2[0].content == "Memory for thread 2"

    @pytest.mark.asyncio
    async def test_isolation_enforcement(self, otm):
        """Test that thread memories are isolated (no cross-contamination)."""
        await otm.store("thread-A", "Secret A")
        await otm.store("thread-B", "Secret B")

        a_memories = await otm.retrieve("thread-A")
        b_memories = await otm.retrieve("thread-B")

        # Thread A should not see Thread B's memories
        for m in a_memories:
            assert m.thread_id == "thread-A"
            assert "B" not in m.content

        # Thread B should not see Thread A's memories
        for m in b_memories:
            assert m.thread_id == "thread-B"
            assert "A" not in m.content

    @pytest.mark.asyncio
    async def test_search_isolation(self, otm):
        """Test that search respects thread boundaries."""
        await otm.store("thread-X", "Python is a programming language")
        await otm.store("thread-Y", "Python is a snake species")

        # Search in thread-X should only return thread-X results
        results = await otm.search("thread-X", "Python")
        assert all(m.thread_id == "thread-X" for m in results)

    @pytest.mark.asyncio
    async def test_cross_thread_read(self, otm):
        """Test explicit cross-thread memory read."""
        await otm.store("thread-A", "Important insight about quantum mechanics")
        await otm.store("thread-A", "Another quantum observation")

        # Thread B explicitly reads from Thread A
        cross_results = await otm.cross_thread_read("thread-A", "thread-B", "quantum")

        assert len(cross_results) > 0
        # The read should be logged in Thread B's memory
        b_memories = await otm.retrieve("thread-B")
        assert any("CROSS-THREAD READ" in m.content for m in b_memories)

    @pytest.mark.asyncio
    async def test_consolidation(self, otm):
        """Test memory consolidation (working -> semantic)."""
        # Store several working memories
        for i in range(5):
            await otm.store("thread-1", f"Working memory {i}", memory_type=MemoryType.WORKING)

        # Consolidate
        consolidated = await otm.consolidate("thread-1", "Summary of 5 working memories")
        assert consolidated.memory_type == MemoryType.SEMANTIC
        assert "CONSOLIDATED" in consolidated.content

    @pytest.mark.asyncio
    async def test_clear_thread(self, otm):
        """Test clearing a thread's memory."""
        await otm.store("thread-1", "Memory 1")
        await otm.store("thread-1", "Memory 2")

        count = await otm.clear_thread("thread-1")
        assert count == 2

        memories = await otm.retrieve("thread-1")
        assert len(memories) == 0

    @pytest.mark.asyncio
    async def test_snapshot(self, otm):
        """Test getting a thread memory snapshot."""
        await otm.store("thread-1", "Short")
        await otm.store("thread-1", "A longer memory content here")

        snapshot = await otm.get_snapshot("thread-1")
        assert snapshot.thread_id == "thread-1"
        assert len(snapshot.records) == 2
        assert snapshot.total_size > 0


class TestMemoryManager:
    """Tests for the three-tier MemoryManager."""

    @pytest.mark.asyncio
    async def test_store_in_all_tiers(self, memory_manager):
        """Test storing in working, episodic, and semantic tiers."""
        await memory_manager.store_working("t1", "Working content")
        await memory_manager.store_episodic("t1", "Episodic content")
        await memory_manager.store_semantic("t1", "Semantic content")

        working = await memory_manager.retrieve_working("t1")
        episodic = await memory_manager.retrieve_episodic("t1")
        semantic = await memory_manager.retrieve_semantic("t1")

        assert len(working) == 1
        assert len(episodic) == 1
        assert len(semantic) == 1

        assert working[0].memory_type == MemoryType.WORKING
        assert episodic[0].memory_type == MemoryType.EPISODIC
        assert semantic[0].memory_type == MemoryType.SEMANTIC

    @pytest.mark.asyncio
    async def test_consolidate_session(self, memory_manager):
        """Test session consolidation across threads."""
        await memory_manager.store_working("t1", "Working 1")
        await memory_manager.store_working("t2", "Working 2")

        results = await memory_manager.consolidate_session(
            ["t1", "t2"], "Session summary"
        )
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_global(self, memory_manager):
        """Test global search across all threads."""
        await memory_manager.store_semantic("t1", "ACOS uses orthogonal memory")
        await memory_manager.store_semantic("t2", "HBTA provides efficient attention")

        results = await memory_manager.search_global("orthogonal")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_summarize_thread(self, memory_manager):
        """Test thread memory summarization."""
        await memory_manager.store_working("t1", "First working memory")
        await memory_manager.store_semantic("t1", "Important semantic knowledge")

        summary = await memory_manager.summarize_thread("t1")
        assert "t1" in summary
        assert len(summary) > 0

    @pytest.mark.asyncio
    async def test_get_stats(self, memory_manager):
        """Test memory statistics."""
        await memory_manager.store_working("t1", "W1")
        await memory_manager.store_episodic("t1", "E1")
        await memory_manager.store_semantic("t1", "S1")

        stats = await memory_manager.get_stats()
        assert stats["total_records"] >= 3
        assert stats["working"] >= 1
        assert stats["episodic"] >= 1
        assert stats["semantic"] >= 1
