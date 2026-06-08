"""
Cognitive Kernel - The central orchestrator of ACOS.

Responsibilities:
- Accept user requests
- Spawn reasoning threads based on query analysis
- Track execution state across all threads
- Coordinate agents (Research, Planning, Memory, Verification)
- Merge results from all threads
- Coordinate reflection and verification
- Synthesize final answer

Workflow:
1. User submits a query
2. Kernel analyzes the query to determine required thread types
3. ThreadScheduler creates and manages threads
4. Agents execute within their assigned threads
5. ReflectionEngine reviews all outputs
6. VerificationEngine checks for accuracy and consistency
7. Kernel synthesizes the final answer from all verified results
8. Memory persists across sessions via MemoryManager
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from acos.schemas.models import (
    SessionState, ThreadState, ThreadType, ThreadStatus,
    ThreadPriority, AgentType, AgentOutput, Message,
    ReflectionResult, VerificationResult, QueryRequest, QueryResponse,
)
from acos.memory.store import StorageBackend
from acos.memory.manager import MemoryManager
from acos.scheduler import ThreadScheduler
from acos.models.router import ModelRouter
from acos.agents.research import ResearchAgent
from acos.agents.planning import PlanningAgent
from acos.agents.memory import MemoryAgent
from acos.agents.verification import VerificationAgent
from acos.engines.reflection import ReflectionEngine
from acos.engines.verification import VerificationEngine


# Mapping of thread types to agent types
THREAD_AGENT_MAP: dict[ThreadType, AgentType] = {
    ThreadType.ANALYSIS: AgentType.RESEARCH,
    ThreadType.PLANNING: AgentType.PLANNING,
    ThreadType.MEMORY: AgentType.MEMORY,
    ThreadType.VERIFICATION: AgentType.VERIFICATION,
    ThreadType.CREATIVE: AgentType.RESEARCH,  # Creative uses research agent
}

# Default thread types spawned for a complex query
DEFAULT_THREAD_TYPES = [
    ThreadType.PLANNING,
    ThreadType.ANALYSIS,
    ThreadType.MEMORY,
    ThreadType.VERIFICATION,
]


class CognitiveKernel:
    """
    The central orchestrator of the ACOS Runtime.

    Coordinates all subsystems:
    - ThreadScheduler for thread management
    - MemoryManager for memory operations
    - ModelRouter for LLM routing
    - Agents for reasoning
    - ReflectionEngine for quality review
    - VerificationEngine for accuracy checking
    """

    def __init__(self, db_path: str | None = None):
        # Initialize subsystems
        self._storage = StorageBackend(db_path)
        self._memory = MemoryManager(self._storage)
        self._scheduler = ThreadScheduler()
        self._router = ModelRouter()
        self._reflection = ReflectionEngine(self._router)
        self._verification = VerificationEngine(self._router)

        # Initialize agents
        self._agents: dict[AgentType, ResearchAgent | PlanningAgent | MemoryAgent | VerificationAgent] = {}

        # Session tracking
        self._sessions: dict[str, SessionState] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all subsystems."""
        if self._initialized:
            return

        # Initialize storage
        await self._storage.initialize()

        # Auto-discover LLM backends
        await self._router.auto_discover()

        # Initialize agents
        self._agents = {
            AgentType.RESEARCH: ResearchAgent(self._router, self._memory),
            AgentType.PLANNING: PlanningAgent(self._router, self._memory),
            AgentType.MEMORY: MemoryAgent(self._router, self._memory),
            AgentType.VERIFICATION: VerificationAgent(self._router, self._memory),
        }

        # Register thread handlers
        for thread_type, agent_type in THREAD_AGENT_MAP.items():
            agent = self._agents[agent_type]
            # Create a proper async handler closure for each agent
            self._scheduler.register_handler(
                thread_type,
                self._make_handler(agent),
            )

        self._initialized = True

    def _make_handler(self, agent: Any):
        """Create an async handler function for a given agent."""
        async def handler(thread: ThreadState) -> str:
            output = await agent.execute(thread)
            # Store the output as a message in the thread
            msg = Message(
                role="assistant",
                content=output.content,
                thread_id=thread.id,
                agent_type=output.agent_type,
                metadata={"confidence": output.confidence},
            )
            thread.messages.append(msg)
            thread.result = output.content
            return output.content
        return handler

    async def _run_agent(self, agent: Any, thread: ThreadState) -> str:
        """Run an agent and return its output content."""
        output = await agent.execute(thread)
        # Store the output as a message in the thread
        msg = Message(
            role="assistant",
            content=output.content,
            thread_id=thread.id,
            agent_type=output.agent_type,
            metadata={"confidence": output.confidence},
        )
        thread.messages.append(msg)
        thread.result = output.content
        return output.content

    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """
        Process a user query through the full ACOS pipeline.

        Pipeline:
        1. Analyze query → determine thread types
        2. Create session
        3. Spawn threads
        4. Execute agents
        5. Reflect on outputs
        6. Verify outputs
        7. Synthesize final answer
        8. Persist session
        """
        start_time = time.monotonic()

        if not self._initialized:
            await self.initialize()

        # 1. Analyze query and determine thread types
        thread_types = request.thread_types or self._analyze_query(request.query)

        # 2. Create session
        session = SessionState(query=request.query)
        self._sessions[session.id] = session

        # Store the query in session memory
        await self._memory.store_working(
            "__session__",
            f"User query: {request.query}",
            {"session_id": session.id},
        )

        # 3. Spawn threads
        threads: list[ThreadState] = []
        for thread_type in thread_types:
            agent_type = THREAD_AGENT_MAP.get(thread_type)
            thread = await self._scheduler.create_thread(
                query=request.query,
                thread_type=thread_type,
                priority=request.priority,
                agent_type=agent_type,
                parent_session_id=session.id,
            )
            threads.append(thread)

        session.threads = threads

        # 4. Execute agents (all threads in parallel)
        agent_outputs: list[AgentOutput] = []
        tasks = []
        for thread in threads:
            agent_type = THREAD_AGENT_MAP.get(thread.type)
            if agent_type and agent_type in self._agents:
                agent = self._agents[agent_type]
                tasks.append(self._execute_agent_in_thread(agent, thread))

        # Run all agents concurrently
        if tasks:
            outputs = await asyncio.gather(*tasks, return_exceptions=True)
            for output in outputs:
                if isinstance(output, AgentOutput):
                    agent_outputs.append(output)
                    session.agent_outputs.append(output)
                elif isinstance(output, Exception):
                    # Log error but continue
                    pass

        # 5. Reflection - review all outputs
        reflections = []
        for thread in threads:
            thread_outputs = [o for o in agent_outputs if o.thread_id == thread.id]
            if thread_outputs:
                reflection = await self._reflection.reflect(thread.id, thread_outputs)
                reflections.append(reflection)
                session.reflections.append(reflection)

        # Cross-thread contradiction detection
        cross_contradictions = await self._reflection.detect_cross_thread_contradictions(agent_outputs)
        if cross_contradictions:
            await self._memory.store_episodic(
                "__session__",
                f"Cross-thread contradictions detected: {cross_contradictions}",
                {"session_id": session.id},
            )

        # 6. Verification - check outputs
        verifications = []
        for output in agent_outputs:
            verification = await self._verification.verify(output.thread_id, output.content)
            verifications.append(verification)
            session.verifications.append(verification)

        # Cross-verification
        if len(agent_outputs) > 1:
            cross_verification = await self._verification.cross_verify(agent_outputs)
            verifications.append(cross_verification)
            session.verifications.append(cross_verification)

        # 7. Synthesize final answer
        synthesis = await self._synthesize(
            request.query, agent_outputs, reflections, verifications
        )
        session.final_synthesis = synthesis

        # 8. Persist session
        session.completed_at = datetime.now(timezone.utc)
        await self._storage.save_session(session)

        # Consolidate session memories
        thread_ids = [t.id for t in threads]
        await self._memory.consolidate_session(
            thread_ids,
            f"Session {session.id[:8]}: {request.query[:100]} -> {synthesis[:200]}",
        )

        total_time = (time.monotonic() - start_time) * 1000

        return QueryResponse(
            session_id=session.id,
            query=request.query,
            final_synthesis=synthesis,
            threads=threads,
            agent_outputs=agent_outputs,
            reflections=reflections,
            verifications=verifications,
            total_time_ms=total_time,
        )

    async def _execute_agent_in_thread(
        self, agent: Any, thread: ThreadState
    ) -> AgentOutput:
        """Execute an agent within a thread context."""
        # Start the thread
        await self._scheduler.start_thread(thread.id)

        # Execute the agent
        try:
            output = await agent.execute(thread)
            # Update thread state
            thread.status = ThreadStatus.COMPLETED
            thread.result = output.content
            thread.completed_at = datetime.now(timezone.utc)

            # Add message to thread
            msg = Message(
                role="assistant",
                content=output.content,
                thread_id=thread.id,
                agent_type=output.agent_type,
            )
            thread.messages.append(msg)

            return output
        except Exception as e:
            thread.status = ThreadStatus.FAILED
            thread.error = str(e)
            raise

    async def _synthesize(
        self,
        query: str,
        outputs: list[AgentOutput],
        reflections: list[ReflectionResult],
        verifications: list[VerificationResult],
    ) -> str:
        """Synthesize a final answer from all thread results."""
        if not outputs:
            return "No results were produced from the reasoning threads."

        # Build synthesis prompt
        outputs_summary = "\n\n".join(
            f"## {o.agent_type.value.title()} Thread (confidence: {o.confidence:.2f})\n{o.content}"
            for o in outputs
        )

        reflection_summary = ""
        if reflections:
            reflection_summary = "\n\n### Reflection Summary\n" + "\n".join(
                f"- Quality score: {r.quality_score:.2f}, "
                f"Issues: {len(r.issues_found)}, "
                f"Contradictions: {len(r.contradictions)}, "
                f"Improvements: {len(r.improvements)}"
                for r in reflections
            )

        verification_summary = ""
        if verifications:
            passed = sum(1 for v in verifications if v.passed)
            verification_summary = (
                f"\n\n### Verification Summary\n"
                f"Passed: {passed}/{len(verifications)}, "
                f"Avg confidence: {sum(v.confidence_score for v in verifications) / len(verifications):.2f}"
            )

        prompt = f"""Synthesize a comprehensive final answer for the following query.

Original Query: {query}

## Thread Outputs:
{outputs_summary}
{reflection_summary}
{verification_summary}

Please provide a well-structured final answer that:
1. Directly addresses the original query
2. Incorporates insights from all reasoning threads
3. Acknowledges any contradictions or uncertainties found
4. Reflects the confidence levels of the underlying analysis
5. Provides actionable next steps if appropriate"""

        return await self._router.generate(prompt, system="You are the ACOS Synthesis Engine. Combine multiple reasoning thread outputs into a coherent, comprehensive final answer.")

    def _analyze_query(self, query: str) -> list[ThreadType]:
        """
        Analyze a query to determine which thread types to spawn.

        Uses simple heuristic rules. In production, this would use
        an LLM for intelligent query routing.
        """
        query_lower = query.lower()
        thread_types = []

        # Planning indicators
        planning_keywords = ["plan", "strategy", "how to", "roadmap", "approach", "design", "build", "create", "implement", "develop", "architect"]
        if any(kw in query_lower for kw in planning_keywords):
            thread_types.append(ThreadType.PLANNING)

        # Research/Analysis indicators
        research_keywords = ["analyze", "research", "investigate", "compare", "evaluate", "what is", "explain", "understand", "study", "analyze", "explore", "examine", "trading", "algorithm"]
        if any(kw in query_lower for kw in research_keywords):
            thread_types.append(ThreadType.ANALYSIS)

        # Verification indicators
        verify_keywords = ["verify", "check", "validate", "confirm", "test", "prove", "correct", "ensure", "guarantee"]
        if any(kw in query_lower for kw in verify_keywords):
            thread_types.append(ThreadType.VERIFICATION)

        # Memory indicators
        memory_keywords = ["remember", "recall", "history", "previous", "past", "context"]
        if any(kw in query_lower for kw in memory_keywords):
            thread_types.append(ThreadType.MEMORY)

        # Creative indicators
        creative_keywords = ["imagine", "create", "invent", "brainstorm", "ideate", "novel", "innovative"]
        if any(kw in query_lower for kw in creative_keywords):
            thread_types.append(ThreadType.CREATIVE)

        # If no specific types matched, use default (all types)
        if not thread_types:
            thread_types = list(DEFAULT_THREAD_TYPES)

        # Always include memory thread for context building
        if ThreadType.MEMORY not in thread_types:
            thread_types.append(ThreadType.MEMORY)

        return thread_types

    # ─── Query Interface ──────────────────────────────────────────────────────

    async def get_session(self, session_id: str) -> SessionState | None:
        """Retrieve a session by ID."""
        if session_id in self._sessions:
            return self._sessions[session_id]
        return await self._storage.load_session(session_id)

    async def list_sessions(self, limit: int = 20) -> list[SessionState]:
        """List recent sessions."""
        return list(self._sessions.values())[-limit:]

    async def get_thread(self, thread_id: str) -> ThreadState | None:
        """Get a thread's current state."""
        return await self._scheduler.get_thread(thread_id)

    async def get_stats(self) -> dict[str, Any]:
        """Get runtime statistics."""
        memory_stats = await self._memory.get_stats()
        model_stats = self._router.get_performance_stats()
        active_threads = await self._scheduler.get_active_count()

        return {
            "initialized": self._initialized,
            "active_threads": active_threads,
            "total_sessions": len(self._sessions),
            "memory": memory_stats,
            "models": model_stats,
            "available_models": [m.name for m in await self._router.get_available_models()],
        }

    async def shutdown(self) -> None:
        """Gracefully shut down the kernel."""
        await self._scheduler.shutdown()
        await self._storage.close()
