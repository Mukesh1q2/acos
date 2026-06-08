"""
Planning Agent - Strategic planning and task decomposition.

Responsibilities:
- Decompose complex queries into actionable steps
- Create execution plans
- Identify dependencies between steps
- Suggest optimal execution order
"""

from __future__ import annotations

from acos.agents.base import Agent
from acos.schemas.models import AgentOutput, AgentType, ThreadState


PLANNING_SYSTEM_PROMPT = """You are a Planning Agent in the ACOS (Avadhan Cognitive Operating System).
Your role is to create strategic plans and decompose complex tasks.

When given a query, you should:
1. Identify the core objective
2. Decompose into actionable steps
3. Identify dependencies between steps
4. Suggest optimal execution order
5. Estimate complexity and risk for each step
6. Define success criteria

Be structured and practical. Focus on executable plans."""


class PlanningAgent(Agent):
    """Agent specialized in planning and task decomposition."""

    agent_type = AgentType.PLANNING

    async def execute(self, thread: ThreadState) -> AgentOutput:
        """Create a strategic plan for the thread's query."""
        # Retrieve context from memory
        context = await self._retrieve_context(thread.id, thread.query)

        # Build planning prompt
        prompt = f"""Planning Query: {thread.query}

{f"Existing Context:\n{context}\n" if context else ""}

Please create a strategic plan including:
1. Core Objective
2. Step-by-Step Breakdown (with dependencies)
3. Execution Order and Parallelization Opportunities
4. Risk Assessment per Step
5. Success Criteria
6. Estimated Complexity (Low/Medium/High)"""

        # Call LLM
        result = await self._llm_call(prompt, system=PLANNING_SYSTEM_PROMPT)

        # Store the plan in memory
        await self._store_memory(
            thread.id,
            f"Strategic plan: {result[:500]}",
            {"agent": "planning", "query": thread.query},
        )

        return AgentOutput(
            agent_type=AgentType.PLANNING,
            thread_id=thread.id,
            content=result,
            confidence=0.75,
            metadata={"context_used": bool(context)},
        )
