"""
Memory Manager - Three-tier memory hierarchy.

Implements the ACOS memory architecture:
- Working Memory: Short-term, current context (high access, low persistence)
- Episodic Memory: Event-based, timestamped experiences
- Semantic Memory: Long-term knowledge and facts (high persistence, high importance)

The manager coordinates between tiers, handling:
- Automatic tier promotion (working -> episodic -> semantic)
- Consolidation across threads
- Persistence across sessions
- Retrieval with relevance scoring
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from acos.schemas.models import MemoryRecord, MemoryType
from acos.memory.store import StorageBackend
from acos.memory.otm import OrthogonalThreadMemory


class MemoryManager:
    """
    Three-tier memory manager for ACOS.

    Manages the lifecycle of memories:
    1. Store: Place new information in the appropriate tier
    2. Retrieve: Fetch memories by type, thread, or content
    3. Consolidate: Promote working memories to semantic
    4. Summarize: Generate summaries of memory collections
    """

    def __init__(self, storage: StorageBackend):
        self._storage = storage
        self._otm = OrthogonalThreadMemory(storage)

    @property
    def otm(self) -> OrthogonalThreadMemory:
        """Access the Orthogonal Thread Memory subsystem."""
        return self._otm

    # ─── Store ────────────────────────────────────────────────────────────────

    async def store_working(
        self,
        thread_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        """Store in working memory (short-term, current context)."""
        return await self._otm.store(
            thread_id=thread_id,
            content=content,
            memory_type=MemoryType.WORKING,
            metadata=metadata or {},
            importance=0.3,
        )

    async def store_episodic(
        self,
        thread_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        importance: float = 0.6,
    ) -> MemoryRecord:
        """Store in episodic memory (event-based, timestamped)."""
        return await self._otm.store(
            thread_id=thread_id,
            content=content,
            memory_type=MemoryType.EPISODIC,
            metadata=metadata or {},
            importance=importance,
        )

    async def store_semantic(
        self,
        thread_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        importance: float = 0.8,
    ) -> MemoryRecord:
        """Store in semantic memory (long-term knowledge/facts)."""
        return await self._otm.store(
            thread_id=thread_id,
            content=content,
            memory_type=MemoryType.SEMANTIC,
            metadata=metadata or {},
            importance=importance,
        )

    # ─── Retrieve ─────────────────────────────────────────────────────────────

    async def retrieve(
        self,
        thread_id: str,
        memory_type: MemoryType | None = None,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        """Retrieve memories from a thread's space."""
        return await self._otm.retrieve(thread_id, memory_type, limit)

    async def retrieve_working(self, thread_id: str, limit: int = 20) -> list[MemoryRecord]:
        """Retrieve working memory for a thread."""
        return await self._otm.retrieve(thread_id, MemoryType.WORKING, limit)

    async def retrieve_episodic(self, thread_id: str, limit: int = 30) -> list[MemoryRecord]:
        """Retrieve episodic memory for a thread."""
        return await self._otm.retrieve(thread_id, MemoryType.EPISODIC, limit)

    async def retrieve_semantic(self, thread_id: str, limit: int = 50) -> list[MemoryRecord]:
        """Retrieve semantic memory for a thread."""
        return await self._otm.retrieve(thread_id, MemoryType.SEMANTIC, limit)

    async def search(
        self,
        thread_id: str,
        query: str,
        limit: int = 10,
    ) -> list[MemoryRecord]:
        """Search within a thread's memory space."""
        return await self._otm.search(thread_id, query, limit)

    async def search_global(self, query: str, limit: int = 20) -> list[MemoryRecord]:
        """Search across all threads (for global knowledge)."""
        return await self._storage.search_memories(query, limit)

    # ─── Consolidate ──────────────────────────────────────────────────────────

    async def consolidate_thread(self, thread_id: str, summary: str) -> MemoryRecord:
        """
        Consolidate a thread's working memory into semantic memory.

        Implements sleep-cycle consolidation:
        - Working memories are compressed
        - Important information is promoted to semantic tier
        - Unimportant details are retained in episodic tier
        """
        return await self._otm.consolidate(thread_id, summary, importance=0.8)

    async def consolidate_session(self, thread_ids: list[str], summary: str) -> list[MemoryRecord]:
        """
        Consolidate memories across multiple threads after a session.

        Creates a shared semantic memory that captures insights from all threads.
        """
        results = []
        for tid in thread_ids:
            record = await self._otm.consolidate(
                tid, f"[SESSION CONSOLIDATION] {summary}", importance=0.9
            )
            results.append(record)
        return results

    # ─── Summarize ────────────────────────────────────────────────────────────

    async def summarize_thread(self, thread_id: str) -> str:
        """Generate a text summary of a thread's memories."""
        working = await self._otm.retrieve(thread_id, MemoryType.WORKING)
        episodic = await self._otm.retrieve(thread_id, MemoryType.EPISODIC)
        semantic = await self._otm.retrieve(thread_id, MemoryType.SEMANTIC)

        parts = []
        if working:
            parts.append(f"Working Memory ({len(working)} records):")
            for r in working[:5]:
                parts.append(f"  - {r.content[:100]}")
        if episodic:
            parts.append(f"Episodic Memory ({len(episodic)} records):")
            for r in episodic[:5]:
                parts.append(f"  - {r.content[:100]}")
        if semantic:
            parts.append(f"Semantic Memory ({len(semantic)} records):")
            for r in semantic[:5]:
                parts.append(f"  - {r.content[:100]}")

        if not parts:
            return f"No memories found for thread {thread_id}"

        parts.insert(0, f"Memory Summary for Thread {thread_id}:")
        return "\n".join(parts)

    # ─── Stats ────────────────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        """Get memory system statistics."""
        total = await self._storage.count_memories()
        working = await self._storage.count_memories(memory_type=MemoryType.WORKING)
        episodic = await self._storage.count_memories(memory_type=MemoryType.EPISODIC)
        semantic = await self._storage.count_memories(memory_type=MemoryType.SEMANTIC)
        buffer_stats = self._otm.get_buffer_stats()

        return {
            "total_records": total,
            "working": working,
            "episodic": episodic,
            "semantic": semantic,
            "active_threads_in_buffer": len(buffer_stats),
            "buffer_stats": buffer_stats,
        }
