"""Unit tests for the CognitiveKernel."""

import asyncio
import os
import tempfile
import pytest

from acos.kernel import CognitiveKernel
from acos.schemas.models import QueryRequest, ThreadType


@pytest.fixture
def db_path():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
async def kernel(db_path):
    """Create and initialize a kernel for testing."""
    k = CognitiveKernel(db_path=db_path)
    await k.initialize()
    yield k
    await k.shutdown()


class TestCognitiveKernel:
    """Tests for the CognitiveKernel."""

    @pytest.mark.asyncio
    async def test_initialize(self, kernel):
        """Test that kernel initializes successfully."""
        assert kernel._initialized is True

    @pytest.mark.asyncio
    async def test_process_simple_query(self, kernel):
        """Test processing a simple query."""
        request = QueryRequest(query="What is ACOS?")
        response = await kernel.process_query(request)

        assert response.session_id is not None
        assert response.query == "What is ACOS?"
        assert response.final_synthesis is not None
        assert len(response.final_synthesis) > 0
        assert len(response.threads) > 0

    @pytest.mark.asyncio
    async def test_query_creates_multiple_threads(self, kernel):
        """Success Criterion 1: User query creates multiple reasoning threads."""
        request = QueryRequest(query="Design a trading strategy")
        response = await kernel.process_query(request)

        assert len(response.threads) >= 2, f"Expected at least 2 threads, got {len(response.threads)}"

    @pytest.mark.asyncio
    async def test_threads_execute_independently(self, kernel):
        """Success Criterion 2: Threads execute independently."""
        request = QueryRequest(query="Analyze the market")
        response = await kernel.process_query(request)

        # Each thread should have its own result
        completed_threads = [t for t in response.threads if t.status.value == "completed"]
        assert len(completed_threads) >= 2, "At least 2 threads should complete independently"

    @pytest.mark.asyncio
    async def test_threads_have_isolated_memory(self, kernel):
        """Success Criterion 3: Threads maintain isolated memory."""
        request = QueryRequest(query="Research quantum computing")
        response = await kernel.process_query(request)

        # Each thread should have its own memory space
        for thread in response.threads:
            if thread.id:
                memories = await kernel._memory.retrieve(thread.id)
                # All memories should belong to this thread
                for mem in memories:
                    assert mem.thread_id == thread.id, f"Memory leak: thread {thread.id} has memory from {mem.thread_id}"

    @pytest.mark.asyncio
    async def test_agent_orchestration(self, kernel):
        """Success Criterion 4: Agent orchestration works."""
        request = QueryRequest(query="Plan a research project")
        response = await kernel.process_query(request)

        # Check that agent outputs were produced
        assert len(response.agent_outputs) > 0, "No agent outputs produced"

        # Check that different agent types were used
        agent_types = set(o.agent_type.value for o in response.agent_outputs)
        assert len(agent_types) >= 2, f"Expected at least 2 agent types, got {agent_types}"

    @pytest.mark.asyncio
    async def test_reflection_loop(self, kernel):
        """Success Criterion 5: Reflection loop works."""
        request = QueryRequest(query="Verify the approach")
        response = await kernel.process_query(request)

        assert len(response.reflections) > 0, "No reflections produced"
        for r in response.reflections:
            assert r.quality_score >= 0.0
            assert r.quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_verifier_reviews_outputs(self, kernel):
        """Success Criterion 6: Verifier reviews outputs."""
        request = QueryRequest(query="Check the analysis")
        response = await kernel.process_query(request)

        assert len(response.verifications) > 0, "No verifications produced"
        for v in response.verifications:
            assert v.confidence_score >= 0.0
            assert v.consistency_score >= 0.0

    @pytest.mark.asyncio
    async def test_final_synthesis_combines_results(self, kernel):
        """Success Criterion 7: Final synthesis combines thread results."""
        request = QueryRequest(query="Design a trading strategy")
        response = await kernel.process_query(request)

        # Synthesis should incorporate insights from multiple threads
        assert response.final_synthesis is not None
        assert len(response.final_synthesis) > 50, "Synthesis too short - may not be combining results"

    @pytest.mark.asyncio
    async def test_memory_persistence(self, kernel, db_path):
        """Success Criterion 8: Memory persists across sessions."""
        # First session
        request1 = QueryRequest(query="Remember: ACOS uses orthogonal memory")
        response1 = await kernel.process_query(request1)

        # Shutdown and reinitialize
        await kernel.shutdown()

        kernel2 = CognitiveKernel(db_path=db_path)
        await kernel2.initialize()

        # Search for the memory from the first session
        results = await kernel2._memory.search_global("orthogonal memory")
        assert len(results) > 0, "Memory did not persist across sessions"

        await kernel2.shutdown()

    @pytest.mark.asyncio
    async def test_query_with_specific_threads(self, kernel):
        """Test processing a query with specific thread types."""
        request = QueryRequest(
            query="Quick analysis",
            thread_types=[ThreadType.ANALYSIS, ThreadType.MEMORY],
        )
        response = await kernel.process_query(request)

        thread_types = set(t.type for t in response.threads)
        assert ThreadType.ANALYSIS in thread_types
        assert ThreadType.MEMORY in thread_types

    @pytest.mark.asyncio
    async def test_session_persistence(self, kernel, db_path):
        """Test that sessions are persisted."""
        request = QueryRequest(query="Test session persistence")
        response = await kernel.process_query(request)

        # Load the session from storage
        session = await kernel._storage.load_session(response.session_id)
        assert session is not None
        assert session.query == "Test session persistence"

    @pytest.mark.asyncio
    async def test_stats(self, kernel):
        """Test that stats are returned correctly."""
        stats = await kernel.get_stats()
        assert stats["initialized"] is True
        assert "memory" in stats
        assert "models" in stats
