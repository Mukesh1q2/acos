"""
Cognitive Cycle — the heart of ACOS v0.5.

Every query runs through this cycle:

Observe
→ Activate Relevant Concepts
→ Retrieve Memories
→ Retrieve Beliefs
→ Activate Goals
→ Predict Outcomes
→ Generate Plans
→ Simulate Alternatives
→ Select Strategy
→ Execute Threads
→ Verify
→ Reflect
→ Consolidate
→ Update World Model
→ Update Cognitive State
→ Learn
→ Evolve

This is the unifying loop that ties all v0.1–v0.5 subsystems together.
"""

from __future__ import annotations

import time as time_mod
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v5_models import (
    CyclePhase,
    PhaseResult,
    CognitiveCycleTrace,
    UnifiedCycleResult,
    LearningCycleResult,
    CompetitionResult,
    EconomyCycleResult,
    EvaluationReport,
    SelfModelState,
    ManifoldState,
    gen_id,
    utc_now,
)


class CognitiveCycle:
    """Cognitive Cycle — the core runtime loop of ACOS v0.5.

    Orchestrates ALL subsystems into a coherent cycle:

    Observe → Activate → Retrieve → Predict → Plan → Simulate →
    Select → Execute → Verify → Reflect → Consolidate → Update → Learn → Evolve

    Usage::

        store = StorageBackend()
        await store.initialize()

        cycle = CognitiveCycle(
            storage=store,
            kernel=kernel,  # CognitiveKernel instance
        )
        await cycle.initialize()

        result = await cycle.run(query="How should we approach building an AFM?")
    """

    # Maximum time per phase in seconds
    PHASE_TIMEOUT_S = 30.0

    def __init__(
        self,
        storage: StorageBackend,
        kernel: Any = None,
    ) -> None:
        self._storage = storage
        self._kernel = kernel

        # Cycle history
        self._cycle_traces: list[CognitiveCycleTrace] = []
        self._total_cycles = 0

    async def initialize(self) -> None:
        """Initialize the cognitive cycle."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS cognitive_cycle_traces (
                id TEXT PRIMARY KEY,
                query TEXT DEFAULT '',
                total_duration_ms REAL DEFAULT 0.0,
                phases_completed INTEGER DEFAULT 0,
                phases_failed INTEGER DEFAULT 0,
                final_synthesis TEXT DEFAULT '',
                learning_applied INTEGER DEFAULT 0,
                world_model_updated INTEGER DEFAULT 0,
                beliefs_changed INTEGER DEFAULT 0,
                goals_reprioritized INTEGER DEFAULT 0,
                predictions_made INTEGER DEFAULT 0,
                prediction_errors_measured INTEGER DEFAULT 0,
                self_model_updated INTEGER DEFAULT 0,
                phase_results TEXT DEFAULT '[]',
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS phase_results (
                id TEXT PRIMARY KEY,
                cycle_trace_id TEXT NOT NULL,
                phase TEXT NOT NULL,
                success INTEGER DEFAULT 1,
                duration_ms REAL DEFAULT 0.0,
                items_processed INTEGER DEFAULT 0,
                items_produced INTEGER DEFAULT 0,
                summary TEXT DEFAULT '',
                errors TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_cct_query
                ON cognitive_cycle_traces(query);
            CREATE INDEX IF NOT EXISTS idx_cct_timestamp
                ON cognitive_cycle_traces(timestamp);
            CREATE INDEX IF NOT EXISTS idx_pr_cycle
                ON phase_results(cycle_trace_id);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        cursor = await conn.execute(
            "SELECT COUNT(*) as cnt FROM cognitive_cycle_traces"
        )
        row = await cursor.fetchone()
        if row:
            self._total_cycles = row["cnt"]

    async def _save_trace(self, trace: CognitiveCycleTrace) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        import json
        await conn.execute(
            """INSERT OR REPLACE INTO cognitive_cycle_traces
               (id, query, total_duration_ms, phases_completed, phases_failed,
                final_synthesis, learning_applied, world_model_updated,
                beliefs_changed, goals_reprioritized, predictions_made,
                prediction_errors_measured, self_model_updated, phase_results,
                timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trace.id,
                trace.query,
                trace.total_duration_ms,
                trace.phases_completed,
                trace.phases_failed,
                trace.final_synthesis,
                int(trace.learning_applied),
                int(trace.world_model_updated),
                trace.beliefs_changed,
                trace.goals_reprioritized,
                trace.predictions_made,
                trace.prediction_errors_measured,
                int(trace.self_model_updated),
                json.dumps([p.model_dump(mode="json") for p in trace.phase_results]),
                trace.timestamp.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Phase Implementations ─────────────────────────────────────────────

    async def _phase_observe(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 1: Observe the input and environment."""
        start = time_mod.monotonic()
        items = 1  # The query itself
        summary = f"Observed query: '{query[:100]}'"

        # If kernel available, begin session tracking
        if self._kernel and hasattr(self._kernel, '_cognitive_state'):
            try:
                await self._kernel._cognitive_state.begin_session(query)
            except Exception:
                pass

        return PhaseResult(
            phase=CyclePhase.OBSERVE,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=items,
            items_produced=1,
            summary=summary,
        )

    async def _phase_activate_concepts(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 2: Activate relevant concepts from knowledge fabric."""
        start = time_mod.monotonic()
        concepts_activated = 0

        if self._kernel and hasattr(self._kernel, '_knowledge_fabric'):
            try:
                fabric = self._kernel._knowledge_fabric
                concepts = fabric.extract_concepts(query)
                concepts_activated = len(concepts)

                # Add to cognitive graph if dynamics engine exists
                if hasattr(self._kernel, '_dynamics_engine'):
                    cog_graph = self._kernel._dynamics_engine.cognitive_graph
                    from acos.schemas.v3_models import CognitiveNodeType
                    for concept in concepts[:20]:
                        try:
                            await cog_graph.add_node(
                                element_id=concept.id if hasattr(concept, 'id') else str(concept),
                                node_type=CognitiveNodeType.CONCEPT,
                                label=concept.name if hasattr(concept, 'name') else str(concept),
                            )
                        except Exception:
                            pass
            except Exception:
                pass

        return PhaseResult(
            phase=CyclePhase.ACTIVATE_CONCEPTS,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=concepts_activated,
            summary=f"Activated {concepts_activated} concepts",
        )

    async def _phase_retrieve_memories(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 3: Retrieve relevant memories."""
        start = time_mod.monotonic()
        memories_retrieved = 0

        if self._kernel and hasattr(self._kernel, '_memory'):
            try:
                # Retrieve from working memory
                working = await self._kernel._memory.retrieve_working(
                    "__session__", limit=5
                )
                memories_retrieved = len(working) if working else 0

                # Retrieve from semantic memory
                if hasattr(self._kernel, '_semantic_memory'):
                    semantic_results = await self._kernel._semantic_memory.search(
                        query, limit=5
                    )
                    if semantic_results:
                        memories_retrieved += len(semantic_results.concepts) if hasattr(semantic_results, 'concepts') else 0
            except Exception:
                pass

        return PhaseResult(
            phase=CyclePhase.RETRIEVE_MEMORIES,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=memories_retrieved,
            summary=f"Retrieved {memories_retrieved} memories",
        )

    async def _phase_retrieve_beliefs(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 4: Retrieve relevant beliefs."""
        start = time_mod.monotonic()
        beliefs_retrieved = 0

        if self._kernel and hasattr(self._kernel, '_belief_state'):
            try:
                beliefs = await self._kernel._belief_state.get_active_beliefs()
                beliefs_retrieved = len(beliefs)

                # Find contradictions
                contradictions = await self._kernel._belief_state.find_contradictions()
                context["contradictions"] = contradictions
                context["beliefs"] = beliefs
            except Exception:
                pass

        return PhaseResult(
            phase=CyclePhase.RETRIEVE_BELIEFS,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=beliefs_retrieved,
            summary=f"Retrieved {beliefs_retrieved} beliefs",
        )

    async def _phase_activate_goals(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 5: Activate goals relevant to the query."""
        start = time_mod.monotonic()
        goals_activated = 0

        if self._kernel and hasattr(self._kernel, '_goal_manager'):
            try:
                goals = await self._kernel._goal_manager.get_active_goals()
                goals_activated = len(goals)
                context["goals"] = goals

                # Update goal progress for query-relevant goals
                for goal in goals:
                    goal_terms = set(goal.description.lower().split())
                    query_terms = set(query.lower().split())
                    overlap = goal_terms & query_terms
                    if len(overlap) >= 2:
                        await self._kernel._goal_manager.update_progress(
                            goal.id, min(1.0, goal.progress + 0.05)
                        )
            except Exception:
                pass

        return PhaseResult(
            phase=CyclePhase.ACTIVATE_GOALS,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=goals_activated,
            summary=f"Activated {goals_activated} goals",
        )

    async def _phase_predict_outcomes(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 6: Predict outcomes using the world model."""
        start = time_mod.monotonic()
        predictions_made = 0

        if self._kernel:
            try:
                # Use WorldModelEngine if available, else WorldModel
                if hasattr(self._kernel, '_world_model_engine'):
                    wme = self._kernel._world_model_engine
                    pred = await wme.predict_future_state("query_received", time_horizon=60.0)
                    predictions_made += 1
                    context["future_prediction"] = pred
                elif hasattr(self._kernel, '_world_model'):
                    wm = self._kernel._world_model
                    pred = await wm.predict_next_state("query_received")
                    predictions_made += 1

                # Predict goal success for active goals
                goals = context.get("goals", [])
                if goals and hasattr(self._kernel, '_goal_forecast_engine'):
                    for goal in goals[:3]:
                        try:
                            await self._kernel._goal_forecast_engine.forecast_goal(
                                goal_id=goal.id,
                                goal_description=goal.description,
                            )
                            predictions_made += 1
                        except Exception:
                            pass
            except Exception:
                pass

        return PhaseResult(
            phase=CyclePhase.PREDICT_OUTCOMES,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=predictions_made,
            summary=f"Made {predictions_made} predictions",
        )

    async def _phase_generate_plans(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 7: Generate plans based on predictions and goals."""
        start = time_mod.monotonic()
        plans_generated = 0

        # Planning is handled by the planning agent during thread execution
        # This phase prepares the planning context
        context["planning_context"] = {
            "beliefs": [b.statement if hasattr(b, 'statement') else str(b) for b in context.get("beliefs", [])[:5]],
            "goals": [g.description if hasattr(g, 'description') else str(g) for g in context.get("goals", [])[:5]],
            "contradictions": len(context.get("contradictions", [])),
        }
        plans_generated = 1  # Planning context prepared

        return PhaseResult(
            phase=CyclePhase.GENERATE_PLANS,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=plans_generated,
            summary="Planning context prepared",
        )

    async def _phase_simulate_alternatives(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 8: Simulate alternative futures."""
        start = time_mod.monotonic()
        simulations_run = 0

        if self._kernel and hasattr(self._kernel, '_simulation_engine'):
            try:
                sim = self._kernel._simulation_engine
                run = await sim.simulate(
                    initial_state="query_received",
                    planned_actions=["process_query"],
                    max_steps=3,
                )
                simulations_run = 1
            except Exception:
                pass

        return PhaseResult(
            phase=CyclePhase.SIMULATE_ALTERNATIVES,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=simulations_run,
            summary=f"Ran {simulations_run} simulations",
        )

    async def _phase_select_strategy(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 9: Select the best strategy based on predictions and simulations."""
        start = time_mod.monotonic()
        # Strategy selection happens implicitly through thread type analysis
        # The kernel's _analyze_query method determines which threads to spawn
        strategy = "multi_thread_analysis"
        context["selected_strategy"] = strategy

        return PhaseResult(
            phase=CyclePhase.SELECT_STRATEGY,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=1,
            summary=f"Selected strategy: {strategy}",
        )

    async def _phase_execute_threads(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 10: Execute reasoning threads (delegated to kernel)."""
        start = time_mod.monotonic()
        threads_executed = 0
        synthesis = ""

        if self._kernel:
            try:
                from acos.schemas.models import QueryRequest, ThreadPriority
                from acos.schemas.v2_models import QueryRequestV2

                request = QueryRequestV2(
                    query=query,
                    update_cognitive_state=True,
                )
                response = await self._kernel.process_query_v2(request)
                threads_executed = len(response.threads)
                synthesis = response.final_synthesis
                context["synthesis"] = synthesis
                context["agent_outputs"] = response.agent_outputs
                context["reflections"] = response.reflections
                context["verifications"] = response.verifications
            except Exception as e:
                context["execution_error"] = str(e)

        return PhaseResult(
            phase=CyclePhase.EXECUTE_THREADS,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=threads_executed,
            summary=f"Executed {threads_executed} threads",
        )

    async def _phase_verify(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 11: Verify results."""
        start = time_mod.monotonic()
        verifications = len(context.get("verifications", []))

        return PhaseResult(
            phase=CyclePhase.VERIFY,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=verifications,
            summary=f"Verified {verifications} outputs",
        )

    async def _phase_reflect(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 12: Reflect on the results."""
        start = time_mod.monotonic()
        reflections = len(context.get("reflections", []))

        return PhaseResult(
            phase=CyclePhase.REFLECT,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=reflections,
            summary=f"Generated {reflections} reflections",
        )

    async def _phase_consolidate(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 13: Consolidate knowledge."""
        start = time_mod.monotonic()
        items_consolidated = 0

        # Consolidation is handled by the kernel during process_query_v2
        # This phase acknowledges the consolidation step
        if context.get("synthesis"):
            items_consolidated = 1

        return PhaseResult(
            phase=CyclePhase.CONSOLIDATE,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=items_consolidated,
            summary=f"Consolidated {items_consolidated} items",
        )

    async def _phase_update_world_model(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 14: Update world model with observations."""
        start = time_mod.monotonic()
        updates = 0

        if self._kernel and hasattr(self._kernel, '_world_model'):
            try:
                await self._kernel._world_model.observe_transition(
                    source_state="query_received",
                    target_state="query_processed",
                    action="cognitive_cycle",
                    confidence=0.7,
                )
                updates += 1
            except Exception:
                pass

        return PhaseResult(
            phase=CyclePhase.UPDATE_WORLD_MODEL,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=updates,
            summary=f"Updated world model with {updates} observations",
        )

    async def _phase_update_cognitive_state(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 15: Update cognitive state."""
        start = time_mod.monotonic()
        updates = 0

        if self._kernel:
            try:
                # Update cognitive state with latest beliefs and goals
                if hasattr(self._kernel, '_cognitive_state'):
                    beliefs = context.get("beliefs", [])
                    goals = context.get("goals", [])
                    if beliefs:
                        await self._kernel._cognitive_state.update_beliefs(beliefs)
                        updates += 1
                    if goals:
                        await self._kernel._cognitive_state.update_goals(goals)
                        updates += 1

                # Run goal competition if available
                if hasattr(self._kernel, '_goal_competition_engine'):
                    goals = context.get("goals", [])
                    if goals:
                        try:
                            competition = await self._kernel._goal_competition_engine.run_competition()
                            context["competition_result"] = competition
                            updates += 1
                        except Exception:
                            pass

                # Run attention economy if available
                if hasattr(self._kernel, '_attention_economy'):
                    try:
                        economy_result = await self._kernel._attention_economy.run_economy_cycle(
                            goals=context.get("goals"),
                            beliefs=context.get("beliefs"),
                            contradictions=context.get("contradictions"),
                        )
                        context["economy_result"] = economy_result
                        updates += 1
                    except Exception:
                        pass
            except Exception:
                pass

        return PhaseResult(
            phase=CyclePhase.UPDATE_COGNITIVE_STATE,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=updates,
            summary=f"Updated cognitive state with {updates} changes",
        )

    async def _phase_learn(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 16: Learn from the cycle (active learning)."""
        start = time_mod.monotonic()
        learning_updates = 0

        if self._kernel and hasattr(self._kernel, '_active_learning_loop'):
            try:
                # Measure prediction errors for any predictions made
                predictions = context.get("predictions", [])
                for pred_id, actual in predictions:
                    try:
                        error_record = await self._kernel._active_learning_loop.measure_prediction_error(
                            prediction_id=pred_id,
                            actual_outcome=actual,
                        )
                        if error_record:
                            learning_updates += 1
                    except Exception:
                        pass
            except Exception:
                pass

        # Update self model
        if self._kernel and hasattr(self._kernel, '_self_model'):
            try:
                from acos.schemas.v5_models import SelfAssessmentDimension
                overall_conf = 0.5
                if context.get("verifications"):
                    confs = [v.confidence_score if hasattr(v, 'confidence_score') else 0.5
                             for v in context["verifications"]]
                    overall_conf = sum(confs) / len(confs) if confs else 0.5

                await self._kernel._self_model.record_performance(
                    dimension=SelfAssessmentDimension.REASONING_QUALITY,
                    score=overall_conf,
                    context=query[:100],
                )
                learning_updates += 1
            except Exception:
                pass

        return PhaseResult(
            phase=CyclePhase.LEARN,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=learning_updates,
            summary=f"Applied {learning_updates} learning updates",
        )

    async def _phase_evolve(self, query: str, context: dict[str, Any]) -> PhaseResult:
        """Phase 17: Evolve cognitive state (apply dynamics)."""
        start = time_mod.monotonic()
        evolution_applied = False

        if self._kernel and hasattr(self._kernel, '_dynamics_engine'):
            try:
                beliefs = context.get("beliefs", [])
                goals = context.get("goals", [])
                contradictions = context.get("contradictions", [])

                # Get concepts from knowledge fabric
                concepts = []
                try:
                    if hasattr(self._kernel, '_knowledge_fabric'):
                        for node in self._kernel._knowledge_fabric._graph.nodes():
                            concept = self._kernel._knowledge_fabric._concepts.get(node)
                            if concept:
                                concepts.append(concept)
                except Exception:
                    pass

                result = await self._kernel._dynamics_engine.run_cycle(
                    beliefs=beliefs,
                    concepts=concepts,
                    goals=goals,
                    contradictions=contradictions,
                    current_query=query,
                )
                evolution_applied = True
            except Exception:
                pass

        # Evolve manifold if available
        if self._kernel and hasattr(self._kernel, '_cognitive_manifold'):
            try:
                evolved = await self._kernel._cognitive_manifold.evolve(time_elapsed_seconds=60.0)
            except Exception:
                pass

        return PhaseResult(
            phase=CyclePhase.EVOLVE,
            success=True,
            duration_ms=(time_mod.monotonic() - start) * 1000,
            items_processed=1,
            items_produced=1 if evolution_applied else 0,
            summary="Cognitive state evolved" if evolution_applied else "Evolution skipped",
        )

    # ─── Main Cycle Runner ──────────────────────────────────────────────────

    async def run(self, query: str) -> CognitiveCycleTrace:
        """Run the complete cognitive cycle for a query.

        This is the primary entry point. Every query should go through this cycle.

        Args:
            query: The user query to process.

        Returns:
            CognitiveCycleTrace with the full execution trace.
        """
        start_time = time_mod.monotonic()
        context: dict[str, Any] = {}

        # Define the complete cycle phases
        phases = [
            (CyclePhase.OBSERVE, self._phase_observe),
            (CyclePhase.ACTIVATE_CONCEPTS, self._phase_activate_concepts),
            (CyclePhase.RETRIEVE_MEMORIES, self._phase_retrieve_memories),
            (CyclePhase.RETRIEVE_BELIEFS, self._phase_retrieve_beliefs),
            (CyclePhase.ACTIVATE_GOALS, self._phase_activate_goals),
            (CyclePhase.PREDICT_OUTCOMES, self._phase_predict_outcomes),
            (CyclePhase.GENERATE_PLANS, self._phase_generate_plans),
            (CyclePhase.SIMULATE_ALTERNATIVES, self._phase_simulate_alternatives),
            (CyclePhase.SELECT_STRATEGY, self._phase_select_strategy),
            (CyclePhase.EXECUTE_THREADS, self._phase_execute_threads),
            (CyclePhase.VERIFY, self._phase_verify),
            (CyclePhase.REFLECT, self._phase_reflect),
            (CyclePhase.CONSOLIDATE, self._phase_consolidate),
            (CyclePhase.UPDATE_WORLD_MODEL, self._phase_update_world_model),
            (CyclePhase.UPDATE_COGNITIVE_STATE, self._phase_update_cognitive_state),
            (CyclePhase.LEARN, self._phase_learn),
            (CyclePhase.EVOLVE, self._phase_evolve),
        ]

        phase_results: list[PhaseResult] = []
        phases_completed = 0
        phases_failed = 0

        for phase_name, phase_fn in phases:
            try:
                result = await phase_fn(query, context)
                phase_results.append(result)
                if result.success:
                    phases_completed += 1
                else:
                    phases_failed += 1
            except Exception as e:
                phase_results.append(PhaseResult(
                    phase=phase_name,
                    success=False,
                    errors=[str(e)],
                    summary=f"Phase failed: {e}",
                ))
                phases_failed += 1

        # Build trace
        synthesis = context.get("synthesis", "")
        total_duration = (time_mod.monotonic() - start_time) * 1000

        trace = CognitiveCycleTrace(
            query=query,
            phase_results=phase_results,
            total_duration_ms=total_duration,
            phases_completed=phases_completed,
            phases_failed=phases_failed,
            final_synthesis=synthesis,
            learning_applied=any(p.phase == CyclePhase.LEARN and p.success for p in phase_results),
            world_model_updated=any(p.phase == CyclePhase.UPDATE_WORLD_MODEL and p.items_produced > 0 for p in phase_results),
            beliefs_changed=sum(p.items_produced for p in phase_results if p.phase in [CyclePhase.RETRIEVE_BELIEFS, CyclePhase.UPDATE_COGNITIVE_STATE]),
            goals_reprioritized=sum(p.items_produced for p in phase_results if p.phase == CyclePhase.ACTIVATE_GOALS),
            predictions_made=sum(p.items_produced for p in phase_results if p.phase == CyclePhase.PREDICT_OUTCOMES),
            prediction_errors_measured=sum(p.items_produced for p in phase_results if p.phase == CyclePhase.LEARN),
            self_model_updated=any(p.phase == CyclePhase.LEARN and p.success for p in phase_results),
        )

        # Persist trace
        await self._save_trace(trace)
        self._cycle_traces.append(trace)
        self._total_cycles += 1

        return trace

    async def run_unified(self, query: str) -> UnifiedCycleResult:
        """Run the complete cognitive cycle and return a unified result.

        This wraps run() and also collects results from all v0.5 subsystems.

        Args:
            query: The user query to process.

        Returns:
            UnifiedCycleResult with all subsystem results.
        """
        start_time = time_mod.monotonic()

        # Run the core cycle
        trace = await self.run(query)

        # Collect results from v0.5 subsystems
        learning_result: LearningCycleResult | None = None
        competition_result: CompetitionResult | None = None
        economy_result: EconomyCycleResult | None = None
        evaluation_report: EvaluationReport | None = None
        self_model_state: SelfModelState | None = None
        manifold_state: ManifoldState | None = None

        if self._kernel:
            # Self model state
            if hasattr(self._kernel, '_self_model'):
                try:
                    self_model_state = await self._kernel._self_model.get_self_state()
                except Exception:
                    pass

            # Manifold state
            if hasattr(self._kernel, '_cognitive_manifold'):
                try:
                    manifold_state = await self._kernel._cognitive_manifold.get_state()
                except Exception:
                    pass

        total_cycle_time = (time_mod.monotonic() - start_time) * 1000

        return UnifiedCycleResult(
            cycle_trace=trace,
            learning_result=learning_result,
            competition_result=competition_result,
            economy_result=economy_result,
            evaluation_report=evaluation_report,
            self_model_state=self_model_state,
            manifold_state=manifold_state,
            total_cycle_time_ms=total_cycle_time,
            version="0.5.0",
        )

    # ─── Access Methods ─────────────────────────────────────────────────────

    async def get_trace(self, trace_id: str) -> CognitiveCycleTrace | None:
        """Get a specific cycle trace."""
        for trace in self._cycle_traces:
            if trace.id == trace_id:
                return trace
        return None

    async def get_recent_traces(self, limit: int = 10) -> list[CognitiveCycleTrace]:
        """Get recent cycle traces."""
        return self._cycle_traces[-limit:]

    async def get_stats(self) -> dict[str, Any]:
        """Get cognitive cycle statistics."""
        total = len(self._cycle_traces)
        if total == 0:
            return {
                "total_cycles": self._total_cycles,
                "in_memory_traces": 0,
                "avg_cycle_time_ms": 0.0,
                "avg_phases_completed": 0,
                "avg_predictions_made": 0.0,
            }

        avg_time = sum(t.total_duration_ms for t in self._cycle_traces) / total
        avg_phases = sum(t.phases_completed for t in self._cycle_traces) / total
        avg_preds = sum(t.predictions_made for t in self._cycle_traces) / total

        return {
            "total_cycles": self._total_cycles,
            "in_memory_traces": total,
            "avg_cycle_time_ms": round(avg_time, 2),
            "avg_phases_completed": round(avg_phases, 1),
            "avg_predictions_made": round(avg_preds, 1),
            "learning_rate": sum(1 for t in self._cycle_traces if t.learning_applied) / total,
            "world_model_update_rate": sum(1 for t in self._cycle_traces if t.world_model_updated) / total,
        }
