"""
Agent Base Class - Foundation for all ACOS agents.

All agents share:
- A reference to the model router for LLM calls
- A reference to the memory manager for memory operations
- A standard execute interface
- Thread-safe operation
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from acos.schemas.models import AgentOutput, AgentType, ThreadState
from acos.memory.manager import MemoryManager
from acos.models.router import ModelRouter


class Agent(ABC):
    """Base class for all ACOS agents."""

    agent_type: AgentType

    def __init__(self, model_router: ModelRouter, memory_manager: MemoryManager):
        self._router = model_router
        self._memory = memory_manager

    @abstractmethod
    async def execute(self, thread: ThreadState) -> AgentOutput:
        """Execute the agent's task within a thread context."""
        ...

    async def _llm_call(self, prompt: str, system: str | None = None) -> str:
        """Make an LLM call through the model router."""
        return await self._router.generate(prompt, system)

    async def _store_memory(self, thread_id: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Store a working memory for the current thread."""
        await self._memory.store_working(thread_id, content, metadata)

    async def _retrieve_context(self, thread_id: str, query: str) -> str:
        """Retrieve relevant context from memory."""
        records = await self._memory.search(thread_id, query)
        if not records:
            return ""
        return "\n".join(f"- {r.content}" for r in records[:5])

    async def _store_semantic(self, thread_id: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Store a semantic (long-term) memory."""
        await self._memory.store_semantic(thread_id, content, metadata)
