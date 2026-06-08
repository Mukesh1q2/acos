"""
Cognitive Dynamics Engine — the core orchestrator for cognitive dynamics.

Responsibilities:
- belief updates
- goal competition
- uncertainty propagation
- memory reinforcement
- attention allocation
- state evolution

This engine ties together all v0.3 subsystems into a coherent dynamics cycle
that runs after every session (or on demand).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from acos.schemas.v3_models import DynamicsCycleResult
from acos.cognitive.dynamics.attention import AttentionManager
from acos.cognitive.dynamics.uncertainty import UncertaintyEngine
from acos.cognitive.dynamics.plan_state import PlanState
from acos.cognitive.dynamics.cognitive_graph import CognitiveGraph
from acos.cognitive.dynamics.state_evolution import StateEvolutionEngine
from acos.cognitive.dynamics.counterfactual import CounterfactualReasoner


class CognitiveDynamicsEngine:
    """Cognitive Dynamics Engine — orchestrates all cognitive dynamics.

    The engine runs a complete dynamics cycle that:

    1. Updates belief confidences based on evidence
    2. Runs goal competition (reprioritize based on relevance)
    3. Propagates uncertainty through related elements
    4. Reinforces frequently-accessed memories
    5. Allocates attention to active elements
    6. Evolves the cognitive state (dS/dt = F(S))

    Usage::

        from acos.cognitive.dynamics import CognitiveDynamicsEngine
        from acos.memory.store import StorageBackend

        store = StorageBackend()
        await store.initialize()

        engine = CognitiveDynamicsEngine(store)
        await engine.initialize()

        result = await engine.run_cycle(
            beliefs=active_beliefs,
            concepts=active_concepts,
            goals=active_goals,
        )
    """

    def __init__(
        self,
        storage: Any,
        belief_state: Any = None,
        goal_manager: Any = None,
        knowledge_fabric: Any = None,
    ) -> None:
        self._storage = storage
        self._belief_state = belief_state
        self._goal_manager = goal_manager
        self._knowledge_fabric = knowledge_fabric

        # v0.3 subsystems
        self._attention = AttentionManager(storage)
        self._uncertainty = UncertaintyEngine(storage)
        self._plan_state = PlanState(storage)
        self._cognitive_graph = CognitiveGraph(storage)
        self._state_evolution = StateEvolutionEngine(storage)
        self._counterfactual = CounterfactualReasoner(
            storage,
            belief_state=belief_state,
            knowledge_fabric=knowledge_fabric,
            cognitive_graph=self._cognitive_graph,
        )

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize all subsystems."""
        await self._attention.initialize()
        await self._uncertainty.initialize()
        await self._plan_state.initialize()
        await self._cognitive_graph.initialize()
        await self._state_evolution.initialize()
        await self._counterfactual.initialize()

    # ─── Subsystem Access ──────────────────────────────────────────────────

    @property
    def attention(self) -> AttentionManager:
        """Access the Attention Manager."""
        return self._attention

    @property
    def uncertainty(self) -> UncertaintyEngine:
        """Access the Uncertainty Engine."""
        return self._uncertainty

    @property
    def plan_state(self) -> PlanState:
        """Access the Plan State."""
        return self._plan_state

    @property
    def cognitive_graph(self) -> CognitiveGraph:
        """Access the Cognitive Graph."""
        return self._cognitive_graph

    @property
    def state_evolution(self) -> StateEvolutionEngine:
        """Access the State Evolution Engine."""
        return self._state_evolution

    @property
    def counterfactual(self) -> CounterfactualReasoner:
        """Access the Counterfactual Reasoner."""
        return self._counterfactual

    # ─── Core Dynamics Cycle ───────────────────────────────────────────────

    async def run_cycle(
        self,
        beliefs: list[Any] | None = None,
        concepts: list[Any] | None = None,
        goals: list[Any] | None = None,
        contradictions: list[tuple[Any, Any, str]] | None = None,
        current_query: str | None = None,
        time_elapsed_seconds: float = 60.0,
    ) -> DynamicsCycleResult:
        """Run a complete cognitive dynamics cycle.

        The cycle applies all dynamics operators in sequence:

        1. Attention allocation: Focus on query-relevant elements
        2. Uncertainty detection: Scan beliefs and goals for uncertainties
        3. State evolution: dS/dt = F(S) — reinforce, weaken, promote, suppress
        4. Attention decay: Apply temporal decay to all focus entries
        5. Goal competition: Reprioritize goals based on attention and relevance
        6. Uncertainty propagation: Spread uncertainty to related elements

        Args:
            beliefs: Current active beliefs.
            concepts: Current active concepts.
            goals: Current active goals.
            contradictions: Known contradictions.
            current_query: The current user query (if any).
            time_elapsed_seconds: Time since last cycle.

        Returns:
            DynamicsCycleResult with all cycle outcomes.
        """
        start_time = time.monotonic()
        beliefs = beliefs or []
        concepts = concepts or []
        goals = goals or []
        contradictions = contradictions or []

        # ── 1. Attention Allocation ─────────────────────────────────────────
        attention_shifts = 0

        # Focus on query-relevant elements
        if current_query:
            import re
            # Normalize: strip punctuation for better term matching
            query_terms = set(re.findall(r'[a-z]+', current_query.lower()))

            for belief in beliefs:
                if not hasattr(belief, 'statement') or not hasattr(belief, 'id'):
                    continue
                belief_terms = set(belief.statement.lower().split())
                overlap = query_terms & belief_terms
                if overlap:
                    score = min(1.0, 0.3 + 0.1 * len(overlap))
                    from acos.schemas.v3_models import AttentionTargetType
                    await self._attention.focus_on(
                        belief.id, AttentionTargetType.BELIEF, score=score
                    )
                    attention_shifts += 1

            for concept in concepts:
                if not hasattr(concept, 'name') or not hasattr(concept, 'id'):
                    continue
                concept_terms = set(concept.name.lower().split())
                overlap = query_terms & concept_terms
                if overlap:
                    score = min(1.0, 0.3 + 0.1 * len(overlap))
                    from acos.schemas.v3_models import AttentionTargetType
                    await self._attention.focus_on(
                        concept.id, AttentionTargetType.CONCEPT, score=score
                    )
                    attention_shifts += 1

            for goal in goals:
                if not hasattr(goal, 'description') or not hasattr(goal, 'id'):
                    continue
                goal_terms = set(goal.description.lower().split())
                overlap = query_terms & goal_terms
                if overlap:
                    score = min(1.0, 0.3 + 0.1 * len(overlap))
                    from acos.schemas.v3_models import AttentionTargetType
                    await self._attention.focus_on(
                        goal.id, AttentionTargetType.GOAL, score=score
                    )
                    attention_shifts += 1

        # ── 2. Uncertainty Detection ────────────────────────────────────────
        belief_uncertainties = await self._uncertainty.detect_from_beliefs(beliefs)
        goal_uncertainties = await self._uncertainty.detect_from_goals(goals)
        uncertainty_propagations = len(belief_uncertainties) + len(goal_uncertainties)

        # ── 3. State Evolution ──────────────────────────────────────────────
        evolution_result = await self._state_evolution.evolve(
            beliefs=beliefs,
            concepts=concepts,
            goals=goals,
            contradictions=contradictions,
        )

        # ── 4. Attention Decay ─────────────────────────────────────────────
        await self._attention.decay(time_elapsed_seconds)

        # ── 5. Goal Competition ────────────────────────────────────────────
        goal_competitions = 0
        if goals and self._goal_manager:
            # Get attention-weighted goal priorities
            for goal in goals:
                if not hasattr(goal, 'id') or not hasattr(goal, 'description'):
                    continue
                focus = await self._attention.get_focus(goal.id)
                if focus and hasattr(goal, 'priority'):
                    # Goals with higher attention get priority boost
                    attention_boost = int(focus.focus_score * 5)
                    new_priority = min(15, int(goal.priority) + attention_boost)
                    if new_priority != int(goal.priority):
                        goal_competitions += 1

        # ── 6. Memory Reinforcement ────────────────────────────────────────
        memory_reinforcements = 0
        for concept in concepts:
            if not hasattr(concept, 'id') or not hasattr(concept, 'access_count'):
                continue
            if concept.access_count > 0:
                from acos.schemas.v3_models import AttentionTargetType
                result = await self._attention.reinforce(
                    concept.id,
                    boost=0.02 * min(concept.access_count, 10),
                )
                if result:
                    memory_reinforcements += 1

        # ── 7. Uncertainty Propagation ─────────────────────────────────────
        # Propagate high-severity uncertainties to related elements
        active_uncertainties = await self._uncertainty.get_active_uncertainties()
        for entry in active_uncertainties[:5]:  # Limit propagation scope
            if entry.severity >= 0.7 and entry.related_ids:
                propagated = await self._uncertainty.propagate_uncertainty(
                    source_id=entry.related_ids[0] if entry.related_ids else "",
                    target_ids=entry.related_ids[1:4],  # Propagate to up to 3 related elements
                    propagation_factor=0.5,
                )
                uncertainty_propagations += len(propagated)

        # ── Build Result ───────────────────────────────────────────────────
        attention_snapshot = await self._attention.get_snapshot()
        uncertainty_report = await self._uncertainty.generate_report()

        cycle_time = (time.monotonic() - start_time) * 1000

        return DynamicsCycleResult(
            belief_updates=evolution_result.beliefs_reinforced + evolution_result.beliefs_weakened,
            goal_competitions=goal_competitions,
            uncertainty_propagations=uncertainty_propagations,
            memory_reinforcements=memory_reinforcements,
            attention_shifts=attention_shifts,
            state_deltas=evolution_result.deltas,
            evolution_result=evolution_result,
            uncertainty_report=uncertainty_report,
            attention_snapshot=attention_snapshot,
            cycle_time_ms=cycle_time,
        )

    # ─── Convenience Methods ───────────────────────────────────────────────

    async def sync_cognitive_graph(
        self,
        beliefs: list[Any] | None = None,
        concepts: list[Any] | None = None,
        goals: list[Any] | None = None,
    ) -> int:
        """Synchronize the cognitive graph with current beliefs, concepts, and goals.

        Adds all elements as nodes and creates edges for known relationships.

        Args:
            beliefs: Current beliefs.
            concepts: Current concepts.
            goals: Current goals.

        Returns:
            Number of nodes added/updated.
        """
        from acos.schemas.v3_models import CognitiveNodeType, CognitiveEdgeType

        count = 0

        for concept in concepts:
            if not hasattr(concept, 'id') or not hasattr(concept, 'name'):
                continue
            await self._cognitive_graph.add_node(
                element_id=concept.id,
                node_type=CognitiveNodeType.CONCEPT,
                label=concept.name,
                confidence=getattr(concept, 'confidence', 0.5),
            )
            count += 1

        for belief in beliefs:
            if not hasattr(belief, 'id') or not hasattr(belief, 'statement'):
                continue
            await self._cognitive_graph.add_node(
                element_id=belief.id,
                node_type=CognitiveNodeType.BELIEF,
                label=belief.statement[:80],
                confidence=getattr(belief, 'confidence', 0.5),
            )
            count += 1

            # Create edges from belief to related concepts
            for concept_id in getattr(belief, 'related_concept_ids', []):
                await self._cognitive_graph.add_edge(
                    source_id=belief.id,
                    target_id=concept_id,
                    edge_type=CognitiveEdgeType.SUPPORTS,
                    confidence=getattr(belief, 'confidence', 0.5),
                )

        for goal in goals:
            if not hasattr(goal, 'id') or not hasattr(goal, 'description'):
                continue
            await self._cognitive_graph.add_node(
                element_id=goal.id,
                node_type=CognitiveNodeType.GOAL,
                label=goal.description[:80],
                confidence=getattr(goal, 'progress', 0.0),
            )
            count += 1

        return count

    async def get_comprehensive_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics from all v0.3 subsystems."""
        attention_stats = await self._attention.get_stats()
        uncertainty_stats = await self._uncertainty.get_stats()
        plan_stats = await self._plan_state.get_stats()
        graph_stats = await self._cognitive_graph.get_stats()
        evolution_stats = await self._state_evolution.get_stats()
        counterfactual_stats = await self._counterfactual.get_stats()

        return {
            "version": "0.3.0",
            "attention": attention_stats,
            "uncertainty": uncertainty_stats,
            "plans": plan_stats,
            "cognitive_graph": graph_stats,
            "state_evolution": evolution_stats,
            "counterfactual": counterfactual_stats,
        }
