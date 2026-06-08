"""
Thread Scheduler - Manages the lifecycle of reasoning threads.

Capabilities:
- Create threads with type, priority, and agent assignment
- Pause/Resume threads
- Kill threads
- Prioritize threads (dynamic priority adjustment)
- Track execution state
- Schedule threads for execution based on priority

Thread Types:
- ANALYSIS: Deep analysis and reasoning
- MEMORY: Memory-intensive operations
- PLANNING: Strategic planning and decomposition
- VERIFICATION: Fact-checking and validation
- CREATIVE: Creative/exploratory reasoning
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from acos.schemas.models import (
    ThreadState, ThreadStatus, ThreadType, ThreadPriority,
    AgentType, Message,
)


class ThreadScheduler:
    """
    Thread lifecycle manager for ACOS.

    Manages creation, execution, and termination of reasoning threads.
    Supports priority-based scheduling and async execution.
    """

    def __init__(self):
        self._threads: dict[str, ThreadState] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._execution_queue: asyncio.PriorityQueue[tuple[int, str]] = asyncio.PriorityQueue()
        self._lock = asyncio.Lock()
        self._handlers: dict[ThreadType, Callable] = {}

    def register_handler(
        self,
        thread_type: ThreadType,
        handler: Callable[[ThreadState], Coroutine[Any, Any, str]],
    ) -> None:
        """Register a handler function for a thread type."""
        self._handlers[thread_type] = handler

    async def create_thread(
        self,
        query: str,
        thread_type: ThreadType = ThreadType.ANALYSIS,
        priority: ThreadPriority = ThreadPriority.NORMAL,
        agent_type: AgentType | None = None,
        parent_session_id: str | None = None,
    ) -> ThreadState:
        """Create a new reasoning thread."""
        thread = ThreadState(
            type=thread_type,
            status=ThreadStatus.PENDING,
            priority=priority,
            query=query,
            agent_type=agent_type,
            parent_session_id=parent_session_id,
        )
        async with self._lock:
            self._threads[thread.id] = thread
        return thread

    async def start_thread(self, thread_id: str) -> bool:
        """Start executing a pending thread."""
        async with self._lock:
            thread = self._threads.get(thread_id)
            if not thread or thread.status != ThreadStatus.PENDING:
                return False

            thread.status = ThreadStatus.RUNNING
            thread.updated_at = datetime.now(timezone.utc)

            # Create async task for execution
            handler = self._handlers.get(thread.type)
            if handler:
                task = asyncio.create_task(self._execute_thread(thread, handler))
                self._tasks[thread.id] = task
            else:
                thread.status = ThreadStatus.FAILED
                thread.error = f"No handler registered for thread type: {thread.type.value}"

            return True

    async def _execute_thread(
        self,
        thread: ThreadState,
        handler: Callable[[ThreadState], Coroutine[Any, Any, str]],
    ) -> None:
        """Execute a thread's handler and update state."""
        try:
            result = await handler(thread)
            async with self._lock:
                thread.status = ThreadStatus.COMPLETED
                thread.result = result
                thread.completed_at = datetime.now(timezone.utc)
                thread.updated_at = datetime.now(timezone.utc)
        except asyncio.CancelledError:
            async with self._lock:
                thread.status = ThreadStatus.KILLED
                thread.updated_at = datetime.now(timezone.utc)
        except Exception as e:
            async with self._lock:
                thread.status = ThreadStatus.FAILED
                thread.error = str(e)
                thread.updated_at = datetime.now(timezone.utc)

    async def pause_thread(self, thread_id: str) -> bool:
        """Pause a running thread."""
        async with self._lock:
            thread = self._threads.get(thread_id)
            if not thread or thread.status != ThreadStatus.RUNNING:
                return False
            # Cancel the current task
            task = self._tasks.get(thread_id)
            if task and not task.done():
                task.cancel()
            thread.status = ThreadStatus.PAUSED
            thread.updated_at = datetime.now(timezone.utc)
            return True

    async def resume_thread(self, thread_id: str) -> bool:
        """Resume a paused thread."""
        async with self._lock:
            thread = self._threads.get(thread_id)
            if not thread or thread.status != ThreadStatus.PAUSED:
                return False
            thread.status = ThreadStatus.RUNNING
            thread.updated_at = datetime.now(timezone.utc)
            # Restart the handler
            handler = self._handlers.get(thread.type)
            if handler:
                task = asyncio.create_task(self._execute_thread(thread, handler))
                self._tasks[thread.id] = task
            return True

    async def kill_thread(self, thread_id: str) -> bool:
        """Kill a thread (cannot be resumed)."""
        async with self._lock:
            thread = self._threads.get(thread_id)
            if not thread or thread.status in (ThreadStatus.COMPLETED, ThreadStatus.FAILED, ThreadStatus.KILLED):
                return False
            task = self._tasks.get(thread_id)
            if task and not task.done():
                task.cancel()
            thread.status = ThreadStatus.KILLED
            thread.updated_at = datetime.now(timezone.utc)
            return True

    async def set_priority(self, thread_id: str, priority: ThreadPriority) -> bool:
        """Change a thread's priority dynamically."""
        async with self._lock:
            thread = self._threads.get(thread_id)
            if not thread:
                return False
            thread.priority = priority
            thread.updated_at = datetime.now(timezone.utc)
            return True

    async def add_message(self, thread_id: str, message: Message) -> bool:
        """Add a message to a thread's history."""
        async with self._lock:
            thread = self._threads.get(thread_id)
            if not thread:
                return False
            thread.messages.append(message)
            thread.updated_at = datetime.now(timezone.utc)
            return True

    # ─── Query ────────────────────────────────────────────────────────────────

    async def get_thread(self, thread_id: str) -> ThreadState | None:
        """Get a thread's current state."""
        return self._threads.get(thread_id)

    async def list_threads(
        self,
        status: ThreadStatus | None = None,
        thread_type: ThreadType | None = None,
    ) -> list[ThreadState]:
        """List threads, optionally filtered by status or type."""
        threads = list(self._threads.values())
        if status:
            threads = [t for t in threads if t.status == status]
        if thread_type:
            threads = [t for t in threads if t.type == thread_type]
        return sorted(threads, key=lambda t: t.priority.value, reverse=True)

    async def get_active_count(self) -> int:
        """Get count of currently running threads."""
        return sum(1 for t in self._threads.values() if t.status == ThreadStatus.RUNNING)

    async def wait_for_completion(self, thread_ids: list[str], timeout: float = 120.0) -> dict[str, ThreadState]:
        """Wait for multiple threads to complete. Returns final states."""
        results: dict[str, ThreadState] = {}
        deadline = asyncio.get_event_loop().time() + timeout

        remaining = set(thread_ids)
        while remaining and asyncio.get_event_loop().time() < deadline:
            for tid in list(remaining):
                thread = self._threads.get(tid)
                if thread and thread.status in (
                    ThreadStatus.COMPLETED, ThreadStatus.FAILED, ThreadStatus.KILLED
                ):
                    results[tid] = thread
                    remaining.discard(tid)
            if remaining:
                await asyncio.sleep(0.1)

        # Add any remaining threads that didn't complete
        for tid in remaining:
            thread = self._threads.get(tid)
            if thread:
                results[tid] = thread

        return results

    async def shutdown(self) -> None:
        """Cancel all running tasks."""
        for task in self._tasks.values():
            if not task.done():
                task.cancel()
        # Wait for cancellations
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()
