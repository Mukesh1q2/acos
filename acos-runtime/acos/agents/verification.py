"""
Verification Agent - Fact checking and validation.

Responsibilities:
- Verify factual claims in other agents' outputs
- Check logical consistency
- Identify potential errors or contradictions
- Score confidence of claims
"""

from __future__ import annotations

from acos.agents.base import Agent
from acos.schemas.models import AgentOutput, AgentType, ThreadState


VERIFICATION_SYSTEM_PROMPT = """You are a Verification Agent in the ACOS (Avadhan Cognitive Operating System).
Your role is to verify and validate outputs from other agents.

When given content to verify, you should:
1. Identify key claims and assertions
2. Check factual accuracy against known information
3. Verify logical consistency (no contradictions, circular reasoning)
4. Assess confidence level of each claim
5. Flag unverifiable claims
6. Provide a confidence score (0.0 to 1.0)

Be rigorous but fair. Distinguish between definitely wrong, uncertain, and verified."""


class VerificationAgent(Agent):
    """Agent specialized in verification and fact checking."""

    agent_type = AgentType.VERIFICATION

    async def execute(self, thread: ThreadState) -> AgentOutput:
        """Verify the thread's accumulated outputs."""
        # Get all messages/content from the thread
        thread_content = thread.query
        if thread.messages:
            thread_content += "\n\nThread History:\n"
            for msg in thread.messages[-5:]:
                thread_content += f"[{msg.role}]: {msg.content[:200]}\n"

        if thread.result:
            thread_content += f"\nThread Result: {thread.result[:500]}"

        # Retrieve context for verification
        context = await self._retrieve_context(thread.id, thread.query)

        prompt = f"""Verify the following content:

{thread_content}

{f"Context for verification:\n{context}\n" if context else ""}

Please provide a verification report:
1. Key Claims Identified
2. Factual Accuracy Check (for each claim)
3. Logical Consistency Check
4. Confidence Score (0.0-1.0)
5. Issues or Concerns
6. Overall Assessment"""

        result = await self._llm_call(prompt, system=VERIFICATION_SYSTEM_PROMPT)

        # Store verification results
        await self._store_memory(
            thread.id,
            f"Verification: {result[:500]}",
            {"agent": "verification", "query": thread.query},
        )

        return AgentOutput(
            agent_type=AgentType.VERIFICATION,
            thread_id=thread.id,
            content=result,
            confidence=0.85,
            metadata={"content_verified": bool(thread.result or thread.messages)},
        )
