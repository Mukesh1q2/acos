"""Unit tests for the ThreadScheduler."""

import asyncio
import pytest

from acos.scheduler import ThreadScheduler
from acos.schemas.models import (
    ThreadState, ThreadType, ThreadStatus, ThreadPriority,
    AgentType, Message,
)


@pytest.fixture
def scheduler():
    return ThreadScheduler()


class TestThreadScheduler:
    """Tests for ThreadScheduler."""

    @pytest.mark.asyncio
    async def test_create_thread(self, scheduler):
        """Test creating a thread."""
        thread = await scheduler.create_thread(
            query="Test query",
            thread_type=ThreadType.ANALYSIS,
        )
        assert thread.id is not None
        assert thread.status == ThreadStatus.PENDING
        assert thread.type == ThreadType.ANALYSIS
        assert thread.query == "Test query"

    @pytest.mark.asyncio
    async def test_start_thread_with_handler(self, scheduler):
        """Test starting a thread with a registered handler."""
        async def mock_handler(thread: ThreadState) -> str:
            return "Mock result"

        scheduler.register_handler(ThreadType.ANALYSIS, mock_handler)
        thread = await scheduler.create_thread(
            query="Test", thread_type=ThreadType.ANALYSIS,
        )
        started = await scheduler.start_thread(thread.id)
        assert started is True

        # Wait for completion
        await asyncio.sleep(0.1)
        updated = await scheduler.get_thread(thread.id)
        assert updated.status == ThreadStatus.COMPLETED
        assert updated.result == "Mock result"

    @pytest.mark.asyncio
    async def test_start_thread_without_handler(self, scheduler):
        """Test starting a thread without a handler fails gracefully."""
        thread = await scheduler.create_thread(
            query="Test", thread_type=ThreadType.CREATIVE,
        )
        started = await scheduler.start_thread(thread.id)
        assert started is True

        await asyncio.sleep(0.1)
        updated = await scheduler.get_thread(thread.id)
        assert updated.status == ThreadStatus.FAILED

    @pytest.mark.asyncio
    async def test_pause_and_resume(self, scheduler):
        """Test pausing and resuming a thread."""
        async def slow_handler(thread: ThreadState) -> str:
            await asyncio.sleep(10)
            return "Done"

        scheduler.register_handler(ThreadType.ANALYSIS, slow_handler)
        thread = await scheduler.create_thread(
            query="Slow task", thread_type=ThreadType.ANALYSIS,
        )
        await scheduler.start_thread(thread.id)
        await asyncio.sleep(0.05)

        paused = await scheduler.pause_thread(thread.id)
        assert paused is True
        updated = await scheduler.get_thread(thread.id)
        assert updated.status == ThreadStatus.PAUSED

        resumed = await scheduler.resume_thread(thread.id)
        assert resumed is True
        updated = await scheduler.get_thread(thread.id)
        assert updated.status == ThreadStatus.RUNNING

        # Clean up
        await scheduler.kill_thread(thread.id)

    @pytest.mark.asyncio
    async def test_kill_thread(self, scheduler):
        """Test killing a thread."""
        async def slow_handler(thread: ThreadState) -> str:
            await asyncio.sleep(100)
            return "Done"

        scheduler.register_handler(ThreadType.ANALYSIS, slow_handler)
        thread = await scheduler.create_thread(
            query="Kill test", thread_type=ThreadType.ANALYSIS,
        )
        await scheduler.start_thread(thread.id)
        await asyncio.sleep(0.05)

        killed = await scheduler.kill_thread(thread.id)
        assert killed is True

        await asyncio.sleep(0.1)
        updated = await scheduler.get_thread(thread.id)
        assert updated.status == ThreadStatus.KILLED

    @pytest.mark.asyncio
    async def test_set_priority(self, scheduler):
        """Test changing thread priority."""
        thread = await scheduler.create_thread(
            query="Priority test", priority=ThreadPriority.NORMAL,
        )
        assert thread.priority == ThreadPriority.NORMAL

        changed = await scheduler.set_priority(thread.id, ThreadPriority.HIGH)
        assert changed is True

        updated = await scheduler.get_thread(thread.id)
        assert updated.priority == ThreadPriority.HIGH

    @pytest.mark.asyncio
    async def test_list_threads(self, scheduler):
        """Test listing threads."""
        await scheduler.create_thread(query="Query 1", thread_type=ThreadType.ANALYSIS)
        await scheduler.create_thread(query="Query 2", thread_type=ThreadType.PLANNING)

        all_threads = await scheduler.list_threads()
        assert len(all_threads) == 2

        analysis_threads = await scheduler.list_threads(thread_type=ThreadType.ANALYSIS)
        assert len(analysis_threads) == 1

    @pytest.mark.asyncio
    async def test_add_message(self, scheduler):
        """Test adding messages to a thread."""
        thread = await scheduler.create_thread(query="Message test")
        msg = Message(role="user", content="Hello")
        added = await scheduler.add_message(thread.id, msg)
        assert added is True

        updated = await scheduler.get_thread(thread.id)
        assert len(updated.messages) == 1
        assert updated.messages[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_wait_for_completion(self, scheduler):
        """Test waiting for multiple threads to complete."""
        async def fast_handler(thread: ThreadState) -> str:
            await asyncio.sleep(0.05)
            return "Fast done"

        scheduler.register_handler(ThreadType.ANALYSIS, fast_handler)
        scheduler.register_handler(ThreadType.PLANNING, fast_handler)

        t1 = await scheduler.create_thread(query="Q1", thread_type=ThreadType.ANALYSIS)
        t2 = await scheduler.create_thread(query="Q2", thread_type=ThreadType.PLANNING)

        await scheduler.start_thread(t1.id)
        await scheduler.start_thread(t2.id)

        results = await scheduler.wait_for_completion([t1.id, t2.id], timeout=5.0)
        assert len(results) == 2
        for tid, state in results.items():
            assert state.status == ThreadStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_handler_failure(self, scheduler):
        """Test that handler exceptions are caught."""
        async def failing_handler(thread: ThreadState) -> str:
            raise ValueError("Handler error")

        scheduler.register_handler(ThreadType.ANALYSIS, failing_handler)
        thread = await scheduler.create_thread(
            query="Fail test", thread_type=ThreadType.ANALYSIS,
        )
        await scheduler.start_thread(thread.id)

        await asyncio.sleep(0.1)
        updated = await scheduler.get_thread(thread.id)
        assert updated.status == ThreadStatus.FAILED
        assert "Handler error" in updated.error
