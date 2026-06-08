"""
Integration Test - Full ACOS Pipeline End-to-End.

Verifies all 8 success criteria:
1. User query creates multiple reasoning threads
2. Threads execute independently
3. Threads maintain isolated memory
4. Agent orchestration works
5. Reflection loop works
6. Verifier reviews outputs
7. Final synthesis combines thread results
8. Memory persists across sessions
"""

import os
import tempfile
import pytest

from acos.kernel import CognitiveKernel
from acos.schemas.models import QueryRequest, ThreadType, ThreadPriority


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


class TestFullPipeline:
    """End-to-end integration test for the full ACOS pipeline."""

    @pytest.mark.asyncio
    async def test_complete_pipeline(self, db_path):
        """
        Test the complete ACOS pipeline with a complex query.

        This test validates all 8 success criteria in a single
        comprehensive workflow.
        """
        # Initialize kernel
        kernel = CognitiveKernel(db_path=db_path)
        await kernel.initialize()

        try:
            # ─── Criterion 1: User query creates multiple reasoning threads ───
            request = QueryRequest(
                query="Design a trading strategy for tech stocks",
                priority=ThreadPriority.HIGH,
            )
            response = await kernel.process_query(request)

            assert len(response.threads) >= 2, (
                f"FAIL Criterion 1: Expected >= 2 threads, got {len(response.threads)}"
            )

            thread_types = set(t.type for t in response.threads)
            assert len(thread_types) >= 2, (
                f"FAIL Criterion 1: Expected >= 2 thread types, got {thread_types}"
            )

            # ─── Criterion 2: Threads execute independently ───────────────────
            completed_threads = [
                t for t in response.threads
                if t.status.value in ("completed", "failed")
            ]
            assert len(completed_threads) >= 2, (
                f"FAIL Criterion 2: Only {len(completed_threads)} threads completed"
            )

            # Each thread should have independent content
            results = [t.result for t in completed_threads if t.result]
            assert len(results) >= 2, (
                "FAIL Criterion 2: Not enough threads produced independent results"
            )

            # ─── Criterion 3: Threads maintain isolated memory ───────────────
            for thread in response.threads:
                if thread.id:
                    memories = await kernel._memory.retrieve(thread.id)
                    for mem in memories:
                        assert mem.thread_id == thread.id, (
                            f"FAIL Criterion 3: Memory leak detected - "
                            f"thread {thread.id} has memory from {mem.thread_id}"
                        )

            # ─── Criterion 4: Agent orchestration works ──────────────────────
            assert len(response.agent_outputs) > 0, (
                "FAIL Criterion 4: No agent outputs produced"
            )

            agent_types = set(o.agent_type for o in response.agent_outputs)
            assert len(agent_types) >= 2, (
                f"FAIL Criterion 4: Only {len(agent_types)} agent types used"
            )

            # ─── Criterion 5: Reflection loop works ──────────────────────────
            assert len(response.reflections) > 0, (
                "FAIL Criterion 5: No reflections produced"
            )

            for r in response.reflections:
                assert 0.0 <= r.quality_score <= 1.0, (
                    f"FAIL Criterion 5: Invalid quality score {r.quality_score}"
                )

            # ─── Criterion 6: Verifier reviews outputs ───────────────────────
            assert len(response.verifications) > 0, (
                "FAIL Criterion 6: No verifications produced"
            )

            for v in response.verifications:
                assert 0.0 <= v.confidence_score <= 1.0, (
                    f"FAIL Criterion 6: Invalid confidence score {v.confidence_score}"
                )
                assert 0.0 <= v.consistency_score <= 1.0, (
                    f"FAIL Criterion 6: Invalid consistency score {v.consistency_score}"
                )

            # ─── Criterion 7: Final synthesis combines thread results ────────
            assert response.final_synthesis is not None, (
                "FAIL Criterion 7: No final synthesis produced"
            )
            assert len(response.final_synthesis) > 50, (
                f"FAIL Criterion 7: Synthesis too short ({len(response.final_synthesis)} chars)"
            )

            # ─── Criterion 8: Memory persists across sessions ───────────────
            session_id = response.session_id
            session = await kernel._storage.load_session(session_id)
            assert session is not None, (
                "FAIL Criterion 8: Session did not persist"
            )
            assert session.query == request.query, (
                "FAIL Criterion 8: Session data corrupted"
            )

            # Search for memories from this session
            results = await kernel._memory.search_global("trading strategy")
            assert len(results) > 0, (
                "FAIL Criterion 8: No memories persisted from the session"
            )

        finally:
            await kernel.shutdown()

    @pytest.mark.asyncio
    async def test_persistence_across_restarts(self, db_path):
        """Test that memory persists even after kernel restart."""
        # First run
        kernel1 = CognitiveKernel(db_path=db_path)
        await kernel1.initialize()
        await kernel1.process_query(QueryRequest(query="Remember: ACOS uses orthogonal memory"))
        await kernel1.shutdown()

        # Second run with same database
        kernel2 = CognitiveKernel(db_path=db_path)
        await kernel2.initialize()

        try:
            results = await kernel2._memory.search_global("orthogonal memory")
            assert len(results) > 0, (
                "FAIL Criterion 8: Memory did not persist across kernel restarts"
            )
        finally:
            await kernel2.shutdown()

    @pytest.mark.asyncio
    async def test_multiple_queries(self, db_path):
        """Test processing multiple queries in sequence."""
        kernel = CognitiveKernel(db_path=db_path)
        await kernel.initialize()

        try:
            queries = [
                "Analyze quantum computing trends",
                "Plan a machine learning project",
                "What is the capital of France?",
            ]

            for query in queries:
                response = await kernel.process_query(QueryRequest(query=query))
                assert response.final_synthesis is not None
                assert len(response.threads) > 0

            # All sessions should be accessible
            sessions = await kernel.list_sessions()
            assert len(sessions) == 3

        finally:
            await kernel.shutdown()

    @pytest.mark.asyncio
    async def test_custom_thread_types(self, db_path):
        """Test processing with specific thread types."""
        kernel = CognitiveKernel(db_path=db_path)
        await kernel.initialize()

        try:
            response = await kernel.process_query(QueryRequest(
                query="Research and verify",
                thread_types=[ThreadType.ANALYSIS, ThreadType.VERIFICATION],
            ))

            types = set(t.type for t in response.threads)
            assert ThreadType.ANALYSIS in types
            assert ThreadType.VERIFICATION in types

        finally:
            await kernel.shutdown()

    @pytest.mark.asyncio
    async def test_execution_trace(self, db_path):
        """Test and display a complete execution trace."""
        kernel = CognitiveKernel(db_path=db_path)
        await kernel.initialize()

        try:
            response = await kernel.process_query(QueryRequest(
                query="Design a trading strategy",
            ))

            # Print execution trace
            print("\n" + "=" * 80)
            print("ACOS Runtime v0.1 - Execution Trace")
            print("=" * 80)
            print(f"\nQuery: {response.query}")
            print(f"Session ID: {response.session_id}")
            print(f"Total time: {response.total_time_ms:.1f}ms")
            print(f"\n--- Threads ({len(response.threads)}) ---")
            for t in response.threads:
                print(f"  [{t.type.value}] {t.status.value} (agent: {t.agent_type.value if t.agent_type else 'N/A'})")
                if t.result:
                    print(f"    Result: {t.result[:100]}...")

            print(f"\n--- Agent Outputs ({len(response.agent_outputs)}) ---")
            for o in response.agent_outputs:
                print(f"  [{o.agent_type.value}] confidence={o.confidence:.2f}")

            print(f"\n--- Reflections ({len(response.reflections)}) ---")
            for r in response.reflections:
                print(f"  Quality: {r.quality_score:.2f}, Issues: {len(r.issues_found)}, Improvements: {len(r.improvements)}")

            print(f"\n--- Verifications ({len(response.verifications)}) ---")
            for v in response.verifications:
                print(f"  Passed: {v.passed}, Confidence: {v.confidence_score:.2f}, Consistency: {v.consistency_score:.2f}")

            print(f"\n--- Final Synthesis ---")
            print(f"  {response.final_synthesis[:200]}...")
            print("=" * 80)

        finally:
            await kernel.shutdown()
