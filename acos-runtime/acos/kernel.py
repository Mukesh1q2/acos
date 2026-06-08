"""
Cognitive Kernel v0.4 — The central orchestrator of ACOS.

Extended pipeline from v0.3:

v0.1 Pipeline:
  Query → Threads → Reflection → Verification → Synthesis

v0.2 Pipeline:
  Query → Cognitive State → Goals → Beliefs → Knowledge Fabric
       → Threads → Reflection → Verification → Consolidation
       → Updated Cognitive State → Synthesis

v0.3 Pipeline:
  Query → Cognitive State → Goals → Beliefs → Knowledge Fabric
       → Threads → Reflection → Verification → Consolidation
       → Cognitive Dynamics Cycle (attention, uncertainty, evolution)
       → Updated Cognitive State → Synthesis

v0.4 Pipeline:
  Query → Cognitive State → Goals → Beliefs → Knowledge Fabric
       → Threads → Reflection → Verification → Consolidation
       → Cognitive Dynamics Cycle (attention, uncertainty, evolution)
       → Predictive Cognition Cycle (world model, prediction, simulation)
       → Updated Cognitive State → Synthesis

New subsystems in v0.4:
- WorldModel: Learn state transitions, predict future states, predict action outcomes
- StateTransitionGraph: Track observed transitions with frequency, confidence, cost
- OutcomePredictor: Predict success/failure probabilities, duration, resources
- SimulationEngine: Future rollouts, scenario comparison, alternative futures
- CausalReasoner: Causal discovery, intervention analysis, counterfactual causality
- GoalForecastEngine: Goal achievability, failure prediction, recommended actions
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
from acos.schemas.v2_models import (
    ConsolidationResult, Belief, Goal, Concept,
    QueryResponseV2, QueryRequestV2, CognitiveStateResponse,
    KnowledgeGraphResponse,
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
from acos.cognitive.knowledge_fabric import KnowledgeFabric
from acos.cognitive.belief_system import BeliefState
from acos.cognitive.goal_system import GoalManager
from acos.cognitive.cognitive_state import CognitiveStateEngine
from acos.cognitive.semantic_memory import SemanticMemory
from acos.cognitive.knowledge_consolidator import KnowledgeConsolidator
from acos.cognitive.reasoning_engine import ReasoningEngine
from acos.cognitive.dynamics.engine import CognitiveDynamicsEngine
from acos.cognitive.dynamics.attention import AttentionManager
from acos.cognitive.dynamics.uncertainty import UncertaintyEngine
from acos.cognitive.dynamics.plan_state import PlanState
from acos.cognitive.dynamics.cognitive_graph import CognitiveGraph
from acos.cognitive.dynamics.state_evolution import StateEvolutionEngine
from acos.cognitive.dynamics.counterfactual import CounterfactualReasoner
from acos.cognitive.predictive.state_transition_graph import StateTransitionGraph
from acos.cognitive.predictive.world_model import WorldModel
from acos.cognitive.predictive.outcome_predictor import OutcomePredictor
from acos.cognitive.predictive.simulation_engine import SimulationEngine
from acos.cognitive.predictive.causal_reasoner import CausalReasoner
from acos.cognitive.predictive.goal_forecast import GoalForecastEngine


# Mapping of thread types to agent types
THREAD_AGENT_MAP: dict[ThreadType, AgentType] = {
    ThreadType.ANALYSIS: AgentType.RESEARCH,
    ThreadType.PLANNING: AgentType.PLANNING,
    ThreadType.MEMORY: AgentType.MEMORY,
    ThreadType.VERIFICATION: AgentType.VERIFICATION,
    ThreadType.CREATIVE: AgentType.RESEARCH,
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
    The central orchestrator of the ACOS Runtime v0.4.

    Coordinates all subsystems:
    - v0.1: ThreadScheduler, MemoryManager, ModelRouter, Agents,
            ReflectionEngine, VerificationEngine
    - v0.2: CognitiveStateEngine, KnowledgeFabric, BeliefState,
            GoalManager, SemanticMemory, KnowledgeConsolidator, ReasoningEngine
    - v0.3: CognitiveDynamicsEngine, AttentionManager, UncertaintyEngine,
            PlanState, CognitiveGraph, StateEvolutionEngine, CounterfactualReasoner
    - v0.4: WorldModel, StateTransitionGraph, OutcomePredictor,
            SimulationEngine, CausalReasoner, GoalForecastEngine
    """

    def __init__(self, db_path: str | None = None):
        # v0.1 subsystems
        self._storage = StorageBackend(db_path)
        self._memory = MemoryManager(self._storage)
        self._scheduler = ThreadScheduler()
        self._router = ModelRouter()
        self._reflection = ReflectionEngine(self._router)
        self._verification = VerificationEngine(self._router)

        # v0.2 cognitive subsystems
        self._knowledge_fabric = KnowledgeFabric(self._storage)
        self._belief_state = BeliefState(self._storage)
        self._goal_manager = GoalManager(self._storage)
        self._cognitive_state = CognitiveStateEngine(self._storage)
        self._semantic_memory = SemanticMemory(self._storage)
        self._consolidator = KnowledgeConsolidator(
            self._knowledge_fabric,
            self._belief_state,
            self._semantic_memory,
            self._memory,
        )
        self._reasoning_engine = ReasoningEngine(
            self._knowledge_fabric,
            self._belief_state,
        )

        # v0.3 dynamics subsystems
        self._dynamics_engine = CognitiveDynamicsEngine(
            self._storage,
            belief_state=self._belief_state,
            goal_manager=self._goal_manager,
            knowledge_fabric=self._knowledge_fabric,
        )

        # v0.4 predictive subsystems
        self._state_transition_graph = StateTransitionGraph(self._storage)
        self._world_model = WorldModel(self._storage)
        self._outcome_predictor = OutcomePredictor(
            self._storage,
            transition_graph=self._world_model.transition_graph,
        )
        self._simulation_engine = SimulationEngine(
            self._storage,
            transition_graph=self._world_model.transition_graph,
        )
        self._causal_reasoner = CausalReasoner(
            self._storage,
            transition_graph=self._world_model.transition_graph,
        )
        self._goal_forecast_engine = GoalForecastEngine(
            self._storage,
            world_model=self._world_model,
            outcome_predictor=self._outcome_predictor,
            causal_reasoner=self._causal_reasoner,
        )

        # Agents
        self._agents: dict[AgentType, ResearchAgent | PlanningAgent | MemoryAgent | VerificationAgent] = {}

        # Session tracking
        self._sessions: dict[str, SessionState] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all subsystems (v0.1 + v0.2)."""
        if self._initialized:
            return

        # v0.1 initialization
        await self._storage.initialize()
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
            self._scheduler.register_handler(
                thread_type,
                self._make_handler(agent),
            )

        # v0.2 initialization — cognitive subsystems
        await self._knowledge_fabric.initialize()
        await self._belief_state.initialize()
        await self._goal_manager.initialize()
        await self._cognitive_state.initialize()
        await self._semantic_memory.initialize()
        await self._reasoning_engine.initialize()

        # v0.3 initialization — dynamics subsystems
        await self._dynamics_engine.initialize()

        # v0.4 initialization — predictive subsystems
        await self._world_model.initialize()
        await self._outcome_predictor.initialize()
        await self._simulation_engine.initialize()
        await self._causal_reasoner.initialize()
        await self._goal_forecast_engine.initialize()

        self._initialized = True

    def _make_handler(self, agent: Any):
        """Create an async handler function for a given agent."""
        async def handler(thread: ThreadState) -> str:
            output = await agent.execute(thread)
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

    # ─── v0.2 Enhanced Pipeline ──────────────────────────────────────────────

    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """
        Process a user query through the full ACOS v0.1 pipeline.
        
        Maintained for backward compatibility.
        """
        v2_request = QueryRequestV2(
            query=request.query,
            thread_types=[t.value for t in request.thread_types] if request.thread_types else None,
            priority=request.priority.value,
            metadata=request.metadata,
        )
        v2_response = await self.process_query_v2(v2_request)

        # Convert v0.2 response to v0.1 format
        threads = []
        for t_dict in v2_response.threads:
            try:
                threads.append(ThreadState(**t_dict))
            except Exception:
                pass

        agent_outputs = []
        for a_dict in v2_response.agent_outputs:
            try:
                agent_outputs.append(AgentOutput(**a_dict))
            except Exception:
                pass

        reflections = []
        for r_dict in v2_response.reflections:
            try:
                reflections.append(ReflectionResult(**r_dict))
            except Exception:
                pass

        verifications = []
        for v_dict in v2_response.verifications:
            try:
                verifications.append(VerificationResult(**v_dict))
            except Exception:
                pass

        return QueryResponse(
            session_id=v2_response.session_id,
            query=v2_response.query,
            final_synthesis=v2_response.final_synthesis,
            threads=threads,
            agent_outputs=agent_outputs,
            reflections=reflections,
            verifications=verifications,
            total_time_ms=v2_response.total_time_ms,
        )

    async def process_query_v2(self, request: QueryRequestV2) -> QueryResponseV2:
        """
        Process a user query through the full ACOS v0.2 pipeline.

        Pipeline:
        1. Load Cognitive State
        2. Update session tracking
        3. Analyze query → determine thread types
        4. Update Goals (check if query relates to existing goals)
        5. Load relevant Beliefs and Knowledge
        6. Spawn threads with cognitive context
        7. Execute agents (parallel)
        8. Reflect on outputs
        9. Verify outputs
        10. Consolidate knowledge (episodic → semantic)
        11. Update Cognitive State
        12. Synthesize final answer with cognitive context
        """
        start_time = time.monotonic()

        if not self._initialized:
            await self.initialize()

        # 1. Load current cognitive state
        cognitive_state = await self._cognitive_state.get_state()

        # 2. Begin session tracking
        await self._cognitive_state.begin_session(request.query)

        # 3. Analyze query and determine thread types
        thread_types = self._analyze_query(request.query)
        if request.thread_types:
            thread_types = [ThreadType(t) for t in request.thread_types]

        # 4. Update Goals — check if query relates to existing goals
        beliefs_affected: list[str] = []
        goals_affected: list[str] = []
        knowledge_graph_changes: list[str] = []

        active_goals = await self._goal_manager.get_active_goals()
        for goal in active_goals:
            # Check if query is related to this goal
            goal_terms = set(goal.description.lower().split())
            query_terms = set(request.query.lower().split())
            overlap = goal_terms & query_terms
            if len(overlap) >= 2:
                # Update goal progress slightly
                await self._goal_manager.update_progress(goal.id, min(1.0, goal.progress + 0.05))
                goals_affected.append(goal.id)

        # 5. Load relevant beliefs and knowledge for context
        relevant_beliefs = await self._belief_state.get_active_beliefs()
        query_concepts = self._knowledge_fabric.extract_concepts(request.query)
        knowledge_context = ""
        for concept in query_concepts[:5]:
            existing = await self._knowledge_fabric.find_concept_by_name(concept.name)
            if existing:
                knowledge_context += f"- {existing[0].name}: {existing[0].description}\n"

        # 6. Create session and spawn threads
        session = SessionState(query=request.query)
        self._sessions[session.id] = session

        # Store the query with cognitive context
        await self._memory.store_working(
            "__session__",
            f"User query: {request.query}",
            {"session_id": session.id, "cognitive_state_id": cognitive_state.id},
        )

        # Set active threads in cognitive state
        threads: list[ThreadState] = []
        for thread_type in thread_types:
            agent_type = THREAD_AGENT_MAP.get(thread_type)
            thread = await self._scheduler.create_thread(
                query=request.query,
                thread_type=thread_type,
                priority=ThreadPriority(request.priority),
                agent_type=agent_type,
                parent_session_id=session.id,
            )
            threads.append(thread)

        await self._cognitive_state.set_active_threads([t.id for t in threads])
        session.threads = threads

        # 7. Execute agents (all threads in parallel)
        agent_outputs: list[AgentOutput] = []
        tasks = []
        for thread in threads:
            agent_type = THREAD_AGENT_MAP.get(thread.type)
            if agent_type and agent_type in self._agents:
                agent = self._agents[agent_type]
                tasks.append(self._execute_agent_in_thread(agent, thread))

        if tasks:
            outputs = await asyncio.gather(*tasks, return_exceptions=True)
            for output in outputs:
                if isinstance(output, AgentOutput):
                    agent_outputs.append(output)
                    session.agent_outputs.append(output)

        # 8. Reflection - review all outputs
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

        # 9. Verification - check outputs
        verifications = []
        for output in agent_outputs:
            verification = await self._verification.verify(output.thread_id, output.content)
            verifications.append(verification)
            session.verifications.append(verification)

        if len(agent_outputs) > 1:
            cross_verification = await self._verification.cross_verify(agent_outputs)
            verifications.append(cross_verification)
            session.verifications.append(cross_verification)

        # 10. Consolidate knowledge (episodic → semantic)
        consolidation: ConsolidationResult | None = None
        if request.update_cognitive_state:
            thread_ids = [t.id for t in threads]
            consolidation = await self._consolidator.consolidate_session(
                session_id=session.id,
                thread_ids=thread_ids,
                session_summary=f"Query: {request.query[:200]}",
            )
            knowledge_graph_changes.append(
                f"Consolidated: {consolidation.concepts_extracted} concepts, "
                f"{consolidation.relationships_extracted} relationships, "
                f"{consolidation.beliefs_created} new beliefs"
            )

        # 11. Update Cognitive State
        if request.update_cognitive_state:
            # Update beliefs in cognitive state
            all_beliefs = await self._belief_state.get_active_beliefs()
            await self._cognitive_state.update_beliefs(all_beliefs)

            # Update goals in cognitive state
            all_goals = await self._goal_manager.get_active_goals()
            await self._cognitive_state.update_goals(all_goals)

            # Update knowledge graph references
            fabric_stats = self._knowledge_fabric.get_stats()
            concept_ids = []
            try:
                # Get all concept IDs from fabric
                for node in self._knowledge_fabric._graph.nodes():
                    concept_ids.append(str(node))
            except Exception:
                pass
            await self._cognitive_state.set_knowledge_concepts(concept_ids[:500])

            # Update uncertainty based on verification results
            if verifications:
                avg_conf = sum(v.confidence_score for v in verifications) / max(len(verifications), 1)
                await self._cognitive_state.update_uncertainty(
                    request.query[:50], 1.0 - avg_conf
                )

        # 12. Synthesize final answer with cognitive context
        synthesis = await self._synthesize_v2(
            request.query, agent_outputs, reflections, verifications,
            cognitive_state, relevant_beliefs, knowledge_context,
        )

        session.final_synthesis = synthesis
        session.completed_at = datetime.now(timezone.utc)
        await self._storage.save_session(session)

        # End session in cognitive state
        avg_confidence = 0.5
        if verifications:
            avg_confidence = sum(v.confidence_score for v in verifications) / len(verifications)
        await self._cognitive_state.end_session(synthesis, avg_confidence)

        # v0.3: Run cognitive dynamics cycle after session
        if request.update_cognitive_state:
            try:
                all_beliefs = await self._belief_state.get_active_beliefs()
                all_concepts = []
                try:
                    for node in self._knowledge_fabric._graph.nodes():
                        concept = self._knowledge_fabric._concepts.get(node)
                        if concept:
                            all_concepts.append(concept)
                except Exception:
                    pass
                all_goals = await self._goal_manager.get_active_goals()
                contradictions_list = await self._belief_state.find_contradictions()

                dynamics_result = await self._dynamics_engine.run_cycle(
                    beliefs=all_beliefs,
                    concepts=all_concepts,
                    goals=all_goals,
                    contradictions=contradictions_list,
                    current_query=request.query,
                )
            except Exception:
                pass  # Non-blocking: dynamics failure shouldn't break the pipeline

        # v0.4: Run predictive cognition cycle
        if request.update_cognitive_state:
            try:
                # Learn state transitions from the session
                state_label = f"session_{session.id[:8]}"
                await self._world_model.observe_transition(
                    source_state="query_received",
                    target_state=state_label,
                    action="process_query",
                    confidence=0.7,
                )

                # Predict next state
                await self._world_model.predict_next_state(
                    current_state=state_label,
                    action="next_query",
                )

                # Forecast active goals
                active_goals = await self._goal_manager.get_active_goals()
                if active_goals:
                    await self._goal_forecast_engine.forecast_all_goals(
                        goals=active_goals,
                        current_state=state_label,
                    )
            except Exception:
                pass  # Non-blocking: predictive failure shouldn't break the pipeline

        # Also run v0.1 memory consolidation for backward compatibility
        thread_ids = [t.id for t in threads]
        await self._memory.consolidate_session(
            thread_ids,
            f"Session {session.id[:8]}: {request.query[:100]} -> {synthesis[:200]}",
        )

        total_time = (time.monotonic() - start_time) * 1000

        # Build v0.2 response
        cognitive_snapshot = await self._cognitive_state.get_snapshot()

        return QueryResponseV2(
            session_id=session.id,
            query=request.query,
            final_synthesis=synthesis,
            threads=[t.model_dump(mode="json") for t in threads],
            agent_outputs=[o.model_dump(mode="json") for o in agent_outputs],
            reflections=[r.model_dump(mode="json") for r in reflections],
            verifications=[v.model_dump(mode="json") for v in verifications],
            consolidation=consolidation,
            cognitive_state_snapshot=cognitive_snapshot,
            beliefs_affected=beliefs_affected,
            goals_affected=goals_affected,
            knowledge_graph_changes=knowledge_graph_changes,
            total_time_ms=total_time,
        )

    async def _execute_agent_in_thread(
        self, agent: Any, thread: ThreadState
    ) -> AgentOutput:
        """Execute an agent within a thread context."""
        await self._scheduler.start_thread(thread.id)

        try:
            output = await agent.execute(thread)
            thread.status = ThreadStatus.COMPLETED
            thread.result = output.content
            thread.completed_at = datetime.now(timezone.utc)

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

    async def _synthesize_v2(
        self,
        query: str,
        outputs: list[AgentOutput],
        reflections: list[ReflectionResult],
        verifications: list[VerificationResult],
        cognitive_state: Any,
        beliefs: list[Belief],
        knowledge_context: str,
    ) -> str:
        """Synthesize a final answer with v0.2 cognitive context."""
        if not outputs:
            return "No results were produced from the reasoning threads."

        # Build synthesis prompt with cognitive context
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

        # v0.2: Add cognitive context
        belief_context = ""
        if beliefs:
            belief_context = "\n\n### Current Beliefs\n" + "\n".join(
                f"- [{b.confidence:.0%}] {b.statement}"
                for b in beliefs[:10]
            )

        knowledge_section = ""
        if knowledge_context:
            knowledge_section = f"\n\n### Knowledge Graph Context\n{knowledge_context}"

        cognitive_context = (
            f"\n\n### Cognitive State\n"
            f"Sessions: {cognitive_state.session_count}, "
            f"Confidence: {cognitive_state.overall_confidence:.2f}, "
            f"Active beliefs: {len(cognitive_state.beliefs)}, "
            f"Active goals: {len(cognitive_state.goals)}"
        )

        prompt = f"""Synthesize a comprehensive final answer for the following query.

Original Query: {query}

## Thread Outputs:
{outputs_summary}
{reflection_summary}
{verification_summary}
{belief_context}
{knowledge_section}
{cognitive_context}

Please provide a well-structured final answer that:
1. Directly addresses the original query
2. Incorporates insights from all reasoning threads
3. Acknowledges any contradictions or uncertainties found
4. Reflects the confidence levels of the underlying analysis
5. Considers existing beliefs and knowledge when forming the answer
6. Provides actionable next steps if appropriate"""

        return await self._router.generate(
            prompt,
            system="You are the ACOS v0.2 Synthesis Engine. Combine multiple reasoning thread outputs into a coherent, comprehensive final answer. Consider existing beliefs, goals, and knowledge graph context when synthesizing.",
        )

    async def _synthesize(
        self,
        query: str,
        outputs: list[AgentOutput],
        reflections: list[ReflectionResult],
        verifications: list[VerificationResult],
    ) -> str:
        """Synthesize a final answer from all thread results (v0.1 compatibility)."""
        if not outputs:
            return "No results were produced from the reasoning threads."

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
        """Analyze a query to determine which thread types to spawn."""
        query_lower = query.lower()
        thread_types = []

        planning_keywords = ["plan", "strategy", "how to", "roadmap", "approach", "design", "build", "create", "implement", "develop", "architect"]
        if any(kw in query_lower for kw in planning_keywords):
            thread_types.append(ThreadType.PLANNING)

        research_keywords = ["analyze", "research", "investigate", "compare", "evaluate", "what is", "explain", "understand", "study", "analyze", "explore", "examine", "trading", "algorithm"]
        if any(kw in query_lower for kw in research_keywords):
            thread_types.append(ThreadType.ANALYSIS)

        verify_keywords = ["verify", "check", "validate", "confirm", "test", "prove", "correct", "ensure", "guarantee"]
        if any(kw in query_lower for kw in verify_keywords):
            thread_types.append(ThreadType.VERIFICATION)

        memory_keywords = ["remember", "recall", "history", "previous", "past", "context"]
        if any(kw in query_lower for kw in memory_keywords):
            thread_types.append(ThreadType.MEMORY)

        creative_keywords = ["imagine", "create", "invent", "brainstorm", "ideate", "novel", "innovative"]
        if any(kw in query_lower for kw in creative_keywords):
            thread_types.append(ThreadType.CREATIVE)

        if not thread_types:
            thread_types = list(DEFAULT_THREAD_TYPES)

        if ThreadType.MEMORY not in thread_types:
            thread_types.append(ThreadType.MEMORY)

        return thread_types

    # ─── v0.2 Cognitive Subsystem Access ─────────────────────────────────────

    @property
    def knowledge_fabric(self) -> KnowledgeFabric:
        """Access the Knowledge Fabric subsystem."""
        return self._knowledge_fabric

    @property
    def belief_state(self) -> BeliefState:
        """Access the Belief State subsystem."""
        return self._belief_state

    @property
    def goal_manager(self) -> GoalManager:
        """Access the Goal Manager subsystem."""
        return self._goal_manager

    @property
    def cognitive_state_engine(self) -> CognitiveStateEngine:
        """Access the Cognitive State Engine subsystem."""
        return self._cognitive_state

    @property
    def semantic_memory(self) -> SemanticMemory:
        """Access the Semantic Memory subsystem."""
        return self._semantic_memory

    @property
    def consolidator(self) -> KnowledgeConsolidator:
        """Access the Knowledge Consolidator subsystem."""
        return self._consolidator

    @property
    def reasoning_engine(self) -> ReasoningEngine:
        """Access the Reasoning Engine subsystem."""
        return self._reasoning_engine

    # ─── v0.3 Dynamics Subsystem Access ───────────────────────────────────────

    @property
    def dynamics_engine(self) -> CognitiveDynamicsEngine:
        """Access the Cognitive Dynamics Engine (v0.3)."""
        return self._dynamics_engine

    @property
    def attention_manager(self) -> AttentionManager:
        """Access the Attention Manager (v0.3)."""
        return self._dynamics_engine.attention

    @property
    def uncertainty_engine(self) -> UncertaintyEngine:
        """Access the Uncertainty Engine (v0.3)."""
        return self._dynamics_engine.uncertainty

    @property
    def plan_state(self) -> PlanState:
        """Access the Plan State (v0.3)."""
        return self._dynamics_engine.plan_state

    @property
    def cognitive_graph(self) -> CognitiveGraph:
        """Access the Cognitive Graph (v0.3)."""
        return self._dynamics_engine.cognitive_graph

    @property
    def state_evolution(self) -> StateEvolutionEngine:
        """Access the State Evolution Engine (v0.3)."""
        return self._dynamics_engine.state_evolution

    @property
    def counterfactual(self) -> CounterfactualReasoner:
        """Access the Counterfactual Reasoner (v0.3)."""
        return self._dynamics_engine.counterfactual

    # ─── v0.4 Predictive Subsystem Access ──────────────────────────────────────

    @property
    def world_model(self) -> WorldModel:
        """Access the World Model (v0.4)."""
        return self._world_model

    @property
    def state_transition_graph(self) -> StateTransitionGraph:
        """Access the State Transition Graph (v0.4)."""
        return self._state_transition_graph

    @property
    def outcome_predictor(self) -> OutcomePredictor:
        """Access the Outcome Predictor (v0.4)."""
        return self._outcome_predictor

    @property
    def simulation_engine(self) -> SimulationEngine:
        """Access the Simulation Engine (v0.4)."""
        return self._simulation_engine

    @property
    def causal_reasoner(self) -> CausalReasoner:
        """Access the Causal Reasoner (v0.4)."""
        return self._causal_reasoner

    @property
    def goal_forecast_engine(self) -> GoalForecastEngine:
        """Access the Goal Forecast Engine (v0.4)."""
        return self._goal_forecast_engine

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
        """Get runtime statistics including v0.2 cognitive subsystems."""
        memory_stats = await self._memory.get_stats()
        model_stats = self._router.get_performance_stats()
        active_threads = await self._scheduler.get_active_count()

        # v0.2 cognitive stats
        cognitive_stats = {}
        try:
            cognitive_stats = await self._cognitive_state.get_stats()
        except Exception:
            pass

        fabric_stats = {}
        try:
            fabric_stats = self._knowledge_fabric.get_stats()
        except Exception:
            pass

        belief_stats = {}
        try:
            belief_stats = await self._belief_state.get_stats()
        except Exception:
            pass

        goal_stats = {}
        try:
            goal_stats = await self._goal_manager.get_stats()
        except Exception:
            pass

        semantic_stats = {}
        try:
            semantic_stats = await self._semantic_memory.get_stats()
        except Exception:
            pass

        # v0.3 dynamics stats
        dynamics_stats = {}
        try:
            dynamics_stats = await self._dynamics_engine.get_comprehensive_stats()
        except Exception:
            pass

        # v0.4 predictive stats
        predictive_stats = {}
        try:
            predictive_stats = {
                "world_model": await self._world_model.get_stats(),
                "outcome_predictor": await self._outcome_predictor.get_stats(),
                "simulation": await self._simulation_engine.get_stats(),
                "causal": await self._causal_reasoner.get_stats(),
                "goal_forecast": await self._goal_forecast_engine.get_stats(),
            }
        except Exception:
            pass

        return {
            "initialized": self._initialized,
            "version": "0.4.0",
            "active_threads": active_threads,
            "total_sessions": len(self._sessions),
            "memory": memory_stats,
            "models": model_stats,
            "available_models": [m.name for m in await self._router.get_available_models()],
            "cognitive_state": cognitive_stats,
            "knowledge_fabric": fabric_stats,
            "beliefs": belief_stats,
            "goals": goal_stats,
            "semantic_memory": semantic_stats,
            "dynamics": dynamics_stats,
            "predictive": predictive_stats,
        }

    async def get_cognitive_state(self) -> CognitiveStateResponse:
        """Get cognitive state information for API responses."""
        snapshot = await self._cognitive_state.get_snapshot()
        return CognitiveStateResponse(**snapshot)

    async def get_knowledge_graph(self) -> KnowledgeGraphResponse:
        """Get the full knowledge graph for API responses."""
        try:
            concepts = await self._knowledge_fabric.get_all_concepts()
        except Exception:
            concepts = []

        try:
            relationships = await self._knowledge_fabric.get_all_relationships()
        except Exception:
            relationships = []

        try:
            entities = await self._knowledge_fabric.get_all_entities()
        except Exception:
            entities = []

        return KnowledgeGraphResponse(
            concepts=concepts,
            relationships=relationships,
            entities=entities,
            total_concepts=len(concepts),
            total_relationships=len(relationships),
        )

    async def shutdown(self) -> None:
        """Gracefully shut down the kernel."""
        # Save cognitive state
        try:
            await self._cognitive_state.save()
        except Exception:
            pass

        await self._scheduler.shutdown()
        await self._storage.close()
