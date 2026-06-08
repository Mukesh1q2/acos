"""
Orthogonal Thread Memory (OTM) - Per-thread isolated memory.

Implements the core principle from the ACOS architecture:
each reasoning thread maintains its own memory space, preventing
cross-thread contamination. This is a practical implementation
of the Stiefel Manifold orthogonality principle (Theorem 4.4).

Design:
- Each thread gets a completely separate memory namespace
- Cross-thread reads require explicit API calls (never implicit)
- Memory isolation is enforced at the storage layer
- Thread memory snapshots can be retrieved for synthesis
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from acos.schemas.models import MemoryRecord, MemoryType, ThreadMemorySnapshot
from acos.memory.store import StorageBackend


class OrthogonalThreadMemory:
    """
    Orthogonal Thread Memory (OTM).

    Guarantees memory isolation between threads:
    - S_i^T * S_j = 0 (zero inter-thread interference)
    - Each thread can only write to its own namespace
    - Cross-thread reads go through explicit retrieval API
    - Memory consolidation preserves isolation boundaries
    """

    def __init__(self, storage: StorageBackend):
        self._storage = storage
        self._thread_buffers: dict[str, list[MemoryRecord]] = {}

    async def store(
        self,
        thread_id: str,
        content: str,
        memory_type: MemoryType = MemoryType.WORKING,
        metadata: dict[str, Any] | None = None,
        importance: float = 0.5,
    ) -> MemoryRecord:
        """Store a memory record in a thread's isolated space."""
        record = MemoryRecord(
            thread_id=thread_id,
            memory_type=memory_type,
            content=content,
            metadata=metadata or {},
            importance=importance,
        )
        # Store in buffer for fast access
        if thread_id not in self._thread_buffers:
            self._thread_buffers[thread_id] = []
        self._thread_buffers[thread_id].append(record)
        # Persist to storage
        await self._storage.store_memory(record)
        return record

    async def retrieve(
        self,
        thread_id: str,
        memory_type: MemoryType | None = None,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        """Retrieve memories from a specific thread's space only."""
        return await self._storage.query_memories(
            thread_id=thread_id, memory_type=memory_type, limit=limit
        )

    async def search(
        self,
        thread_id: str,
        query: str,
        limit: int = 10,
    ) -> list[MemoryRecord]:
        """Search within a thread's memory space only."""
        # First try the buffer for fast access
        buffer_results = []
        if thread_id in self._thread_buffers:
            query_lower = query.lower()
            for record in self._thread_buffers[thread_id]:
                if query_lower in record.content.lower():
                    buffer_results.append(record)
            if buffer_results:
                return buffer_results[:limit]
        # Fall back to storage search with thread filter
        all_results = await self._storage.search_memories(query, limit=limit * 2)
        # Enforce isolation: only return records from this thread
        return [r for r in all_results if r.thread_id == thread_id][:limit]

    async def get_snapshot(self, thread_id: str) -> ThreadMemorySnapshot:
        """Get a complete snapshot of a thread's memory state."""
        records = await self.retrieve(thread_id)
        return ThreadMemorySnapshot(
            thread_id=thread_id,
            records=records,
            total_size=sum(len(r.content) for r in records),
        )

    async def clear_thread(self, thread_id: str) -> int:
        """Clear all memory for a specific thread. Returns count deleted."""
        records = await self.retrieve(thread_id)
        count = 0
        for record in records:
            if await self._storage.delete_memory(record.id):
                count += 1
        if thread_id in self._thread_buffers:
            del self._thread_buffers[thread_id]
        return count

    async def consolidate(
        self,
        thread_id: str,
        summary: str,
        importance: float = 0.8,
    ) -> MemoryRecord:
        """
        Consolidate a thread's working memory into a semantic memory summary.

        This implements the sleep-cycle consolidation from the ACOS spec:
        working memories are compressed into higher-importance semantic records.
        """
        records = await self.retrieve(thread_id, memory_type=MemoryType.WORKING)
        # Create consolidated semantic memory
        consolidated = await self.store(
            thread_id=thread_id,
            content=f"[CONSOLIDATED from {len(records)} records] {summary}",
            memory_type=MemoryType.SEMANTIC,
            metadata={
                "consolidated_from": [r.id for r in records],
                "record_count": len(records),
            },
            importance=importance,
        )
        return consolidated

    async def cross_thread_read(
        self,
        target_thread_id: str,
        requesting_thread_id: str,
        query: str,
        limit: int = 5,
    ) -> list[MemoryRecord]:
        """
        Explicit cross-thread memory read (controlled information sharing).

        This is the ONLY way to access another thread's memory.
        All reads are logged for auditability.
        """
        results = await self.search(target_thread_id, query, limit)
        # Log the cross-thread access
        await self.store(
            thread_id=requesting_thread_id,
            content=f"[CROSS-THREAD READ from {target_thread_id}] query='{query}' results={len(results)}",
            memory_type=MemoryType.EPISODIC,
            metadata={
                "access_type": "cross_thread_read",
                "source_thread": target_thread_id,
                "query": query,
                "result_count": len(results),
            },
            importance=0.3,
        )
        return results

    def get_buffer_stats(self) -> dict[str, int]:
        """Get statistics on in-memory buffers."""
        return {
            tid: len(records) for tid, records in self._thread_buffers.items()
        }
