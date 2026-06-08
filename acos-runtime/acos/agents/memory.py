"""
Memory Agent - Memory retrieval and context building.

Responsibilities:
- Retrieve relevant memories for the current query
- Build context from historical sessions
- Identify patterns across memories
- Suggest memory consolidation
"""

from __future__ import annotations

from acos.agents.base import Agent
from acos.schemas.models import AgentOutput, AgentType, ThreadState


MEMORY_SYSTEM_PROMPT = """You are a Memory Agent in the ACOS (Avadhan Cognitive Operating System).
Your role is to retrieve relevant memories and build context.

When given a query, you should:
1. Search for relevant memories across all memory tiers
2. Identify patterns and connections between memories
3. Build a coherent context from retrieved information
4. Flag important but potentially forgotten information
5. Suggest which memories should be consolidated

Focus on building a comprehensive context that other agents can use."""


class MemoryAgent(Agent):
    """Agent specialized in memory retrieval and context building."""

    agent_type = AgentType.MEMORY

    async def execute(self, thread: ThreadState) -> AgentOutput:
        """Retrieve relevant memories and build context."""
        # Search across memory tiers
        working_memories = await self._memory.retrieve_working(thread.id)
        episodic_memories = await self._memory.retrieve_episodic(thread.id)
        semantic_memories = await self._memory.retrieve_semantic(thread.id)

        # Search globally for cross-session context
        global_results = await self._memory.search_global(thread.query, limit=5)

        # Build memory context
        memory_parts = []

        if working_memories:
            memory_parts.append("Working Memory (current context):")
            for m in working_memories[:5]:
                memory_parts.append(f"  - {m.content[:150]}")

        if episodic_memories:
            memory_parts.append("\nEpisodic Memory (past events):")
            for m in episodic_memories[:5]:
                memory_parts.append(f"  - {m.content[:150]}")

        if semantic_memories:
            memory_parts.append("\nSemantic Memory (knowledge):")
            for m in semantic_memories[:5]:
                memory_parts.append(f"  - {m.content[:150]}")

        if global_results:
            memory_parts.append("\nGlobal Context (cross-session):")
            for m in global_results[:5]:
                memory_parts.append(f"  - [Thread {m.thread_id[:8]}] {m.content[:150]}")

        memory_context = "\n".join(memory_parts) if memory_parts else "No relevant memories found."

        # Use LLM to synthesize memory context
        prompt = f"""Query: {thread.query}

Retrieved Memories:
{memory_context}

Please analyze the retrieved memories and:
1. Summarize the most relevant context for this query
2. Identify patterns or connections across memories
3. Flag any important but potentially overlooked information
4. Suggest which memories should be consolidated for long-term retention"""

        result = await self._llm_call(prompt, system=MEMORY_SYSTEM_PROMPT)

        # Store the memory analysis
        await self._store_memory(
            thread.id,
            f"Memory context analysis: {result[:500]}",
            {"agent": "memory", "query": thread.query},
        )

        return AgentOutput(
            agent_type=AgentType.MEMORY,
            thread_id=thread.id,
            content=result,
            confidence=0.7,
            metadata={
                "working_count": len(working_memories),
                "episodic_count": len(episodic_memories),
                "semantic_count": len(semantic_memories),
                "global_count": len(global_results),
            },
        )
