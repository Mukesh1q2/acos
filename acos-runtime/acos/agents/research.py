"""
Research Agent - Deep analysis and information gathering.

Responsibilities:
- Analyze the query from multiple angles
- Gather relevant information from memory
- Generate research findings
- Store insights for other agents
"""

from __future__ import annotations

from acos.agents.base import Agent
from acos.schemas.models import AgentOutput, AgentType, ThreadState


RESEARCH_SYSTEM_PROMPT = """You are a Research Agent in the ACOS (Avadhan Cognitive Operating System).
Your role is to perform deep analysis and information gathering.

When given a query, you should:
1. Break it down into key research questions
2. Analyze from multiple perspectives
3. Identify relevant facts, patterns, and relationships
4. Generate structured findings
5. Note any assumptions or limitations

Be thorough but concise. Focus on actionable insights."""


class ResearchAgent(Agent):
    """Agent specialized in research and analysis."""

    agent_type = AgentType.RESEARCH

    async def execute(self, thread: ThreadState) -> AgentOutput:
        """Execute research on the thread's query."""
        # Retrieve any existing context
        context = await self._retrieve_context(thread.id, thread.query)

        # Build research prompt
        prompt = f"""Research Query: {thread.query}

{f"Existing Context:\n{context}\n" if context else ""}

Please provide a comprehensive analysis including:
1. Key Research Questions
2. Analysis from Multiple Perspectives
3. Findings and Patterns
4. Assumptions and Limitations
5. Recommendations for Further Investigation"""

        # Call LLM
        result = await self._llm_call(prompt, system=RESEARCH_SYSTEM_PROMPT)

        # Store the research findings in memory
        await self._store_memory(
            thread.id,
            f"Research findings: {result[:500]}",
            {"agent": "research", "query": thread.query},
        )

        # Store key findings as semantic memory
        await self._store_semantic(
            thread.id,
            f"Research completed for: {thread.query}. Key findings: {result[:200]}",
            {"agent": "research", "type": "research_summary"},
        )

        return AgentOutput(
            agent_type=AgentType.RESEARCH,
            thread_id=thread.id,
            content=result,
            confidence=0.8,
            metadata={"context_used": bool(context)},
        )
