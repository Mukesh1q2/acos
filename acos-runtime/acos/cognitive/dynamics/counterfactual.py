"""
Counterfactual Reasoner — support what-if reasoning.

Supports three types of counterfactual reasoning:
1. WHAT_IF: "If X happens, what likely follows?"
2. NEGATION: "What if X were false?"
3. ALTERNATIVE: "What alternative plans exist?"

Uses the cognitive graph and belief system to generate and evaluate
hypothetical scenarios without modifying actual state.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v3_models import (
    CounterfactualScenario,
    CounterfactualResult,
    CounterfactualType,
    CognitiveNodeType,
    gen_id,
    utc_now,
)


class CounterfactualReasoner:
    """Counterfactual Reasoner — what-if reasoning over cognitive state.

    Usage::

        store = StorageBackend()
        await store.initialize()

        cr = CounterfactualReasoner(store, belief_state, knowledge_fabric)
        await cr.initialize()

        result = await cr.what_if("Python becomes obsolete", beliefs, concepts)
        result = await cr.what_if_not("Python is the best language", beliefs)
        result = await cr.alternative_plans("Implement feature X", plans, goals)
    """

    def __init__(
        self,
        storage: StorageBackend,
        belief_state: Any = None,
        knowledge_fabric: Any = None,
        cognitive_graph: Any = None,
    ) -> None:
        self._storage = storage
        self._beliefs = belief_state
        self._fabric = knowledge_fabric
        self._cognitive_graph = cognitive_graph

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables for counterfactual audit trail."""
        await self._create_tables()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS counterfactual_scenarios (
                id TEXT PRIMARY KEY,
                scenario_type TEXT NOT NULL,
                premise TEXT NOT NULL,
                original_state TEXT DEFAULT '{}',
                modified_state TEXT DEFAULT '{}',
                predicted_outcomes TEXT DEFAULT '[]',
                affected_belief_ids TEXT DEFAULT '[]',
                affected_goal_ids TEXT DEFAULT '[]',
                affected_concept_ids TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.3,
                reasoning_chain TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS counterfactual_results (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                scenario_type TEXT NOT NULL,
                scenarios TEXT DEFAULT '[]',
                best_scenario_id TEXT,
                overall_confidence REAL DEFAULT 0.0,
                reasoning_time_ms REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_cf_type
                ON counterfactual_scenarios(scenario_type);
            CREATE INDEX IF NOT EXISTS idx_cf_premise
                ON counterfactual_scenarios(premise);
        """)
        await conn.commit()

    async def _persist_scenario(self, scenario: CounterfactualScenario) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO counterfactual_scenarios
               (id, scenario_type, premise, original_state, modified_state,
                predicted_outcomes, affected_belief_ids, affected_goal_ids,
                affected_concept_ids, confidence, reasoning_chain, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                scenario.id,
                scenario.scenario_type.value,
                scenario.premise,
                json.dumps(scenario.original_state),
                json.dumps(scenario.modified_state),
                json.dumps(scenario.predicted_outcomes),
                json.dumps(scenario.affected_belief_ids),
                json.dumps(scenario.affected_goal_ids),
                json.dumps(scenario.affected_concept_ids),
                scenario.confidence,
                json.dumps(scenario.reasoning_chain),
                json.dumps(scenario.metadata),
                scenario.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _persist_result(self, result: CounterfactualResult) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO counterfactual_results
               (id, query, scenario_type, scenarios, best_scenario_id,
                overall_confidence, reasoning_time_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.id,
                result.query,
                result.scenario_type.value,
                json.dumps([s.model_dump(mode="json") for s in result.scenarios]),
                result.best_scenario_id,
                result.overall_confidence,
                result.reasoning_time_ms,
                result.created_at.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Core Reasoning Methods ────────────────────────────────────────────

    async def what_if(
        self,
        premise: str,
        beliefs: list[Any] | None = None,
        concepts: list[Any] | None = None,
        goals: list[Any] | None = None,
    ) -> CounterfactualResult:
        """Answer: "If X happens, what likely follows?"

        Strategy:
        1. Identify beliefs and concepts related to the premise
        2. Simulate the premise being true
        3. Propagate effects through the knowledge graph
        4. Generate predicted outcomes

        Args:
            premise: The hypothetical premise.
            beliefs: Current beliefs.
            concepts: Current concepts.
            goals: Current goals.

        Returns:
            CounterfactualResult with scenarios.
        """
        start_time = time.monotonic()
        beliefs = beliefs or []
        concepts = concepts or []
        goals = goals or []

        premise_lower = premise.lower()
        premise_terms = set(premise_lower.split())

        # Find affected beliefs (terms overlap with premise)
        affected_beliefs: list[Any] = []
        affected_belief_ids: list[str] = []
        for belief in beliefs:
            if not hasattr(belief, 'statement'):
                continue
            belief_terms = set(belief.statement.lower().split())
            overlap = premise_terms & belief_terms
            if len(overlap) >= 1:
                affected_beliefs.append(belief)
                if hasattr(belief, 'id'):
                    affected_belief_ids.append(belief.id)

        # Find affected concepts
        affected_concept_ids: list[str] = []
        for concept in concepts:
            if not hasattr(concept, 'name'):
                continue
            concept_terms = set(concept.name.lower().split())
            overlap = premise_terms & concept_terms
            if len(overlap) >= 1 and hasattr(concept, 'id'):
                affected_concept_ids.append(concept.id)

        # Find affected goals
        affected_goal_ids: list[str] = []
        for goal in goals:
            if not hasattr(goal, 'description'):
                continue
            goal_terms = set(goal.description.lower().split())
            overlap = premise_terms & goal_terms
            if len(overlap) >= 1 and hasattr(goal, 'id'):
                affected_goal_ids.append(goal.id)

        # Build predicted outcomes based on affected elements
        predicted_outcomes: list[str] = []

        if affected_beliefs:
            for belief in affected_beliefs[:5]:
                stmt = getattr(belief, 'statement', 'unknown')
                predicted_outcomes.append(
                    f"Belief '{stmt}' may be reinforced or contradicted"
                )

        if affected_goal_ids:
            predicted_outcomes.append(
                f"{len(affected_goal_ids)} goal(s) may be impacted"
            )

        if affected_concept_ids:
            predicted_outcomes.append(
                f"{len(affected_concept_ids)} concept(s) may gain relevance"
            )

        if not predicted_outcomes:
            predicted_outcomes.append(
                "The premise has no direct impact on existing beliefs or goals"
            )

        # Build reasoning chain
        reasoning_chain = [
            f"Premise: {premise}",
            f"Found {len(affected_beliefs)} related beliefs",
            f"Found {len(affected_concept_ids)} related concepts",
            f"Found {len(affected_goal_ids)} related goals",
            f"Predicted {len(predicted_outcomes)} potential outcomes",
        ]

        # Calculate confidence based on evidence overlap
        confidence = 0.3
        if affected_beliefs:
            avg_belief_conf = sum(
                getattr(b, 'confidence', 0.5) for b in affected_beliefs
            ) / len(affected_beliefs)
            confidence = min(0.8, 0.3 + avg_belief_conf * 0.3)

        # Create scenario
        scenario = CounterfactualScenario(
            scenario_type=CounterfactualType.WHAT_IF,
            premise=premise,
            original_state={"belief_count": len(beliefs), "concept_count": len(concepts)},
            modified_state={
                "affected_beliefs": len(affected_beliefs),
                "affected_concepts": len(affected_concept_ids),
                "affected_goals": len(affected_goal_ids),
            },
            predicted_outcomes=predicted_outcomes,
            affected_belief_ids=affected_belief_ids,
            affected_goal_ids=affected_goal_ids,
            affected_concept_ids=affected_concept_ids,
            confidence=confidence,
            reasoning_chain=reasoning_chain,
        )
        await self._persist_scenario(scenario)

        result = CounterfactualResult(
            query=f"What if: {premise}",
            scenario_type=CounterfactualType.WHAT_IF,
            scenarios=[scenario],
            best_scenario_id=scenario.id,
            overall_confidence=confidence,
            reasoning_time_ms=(time.monotonic() - start_time) * 1000,
        )
        await self._persist_result(result)
        return result

    async def what_if_not(
        self,
        statement: str,
        beliefs: list[Any] | None = None,
    ) -> CounterfactualResult:
        """Answer: "What if X were false?"

        Strategy:
        1. Find beliefs matching or similar to the statement
        2. Simulate negation
        3. Identify cascading effects on dependent beliefs

        Args:
            statement: The statement to negate.
            beliefs: Current beliefs.

        Returns:
            CounterfactualResult with negation scenarios.
        """
        start_time = time.monotonic()
        beliefs = beliefs or []

        statement_lower = statement.lower()
        negated = f"NOT {statement}"

        # Find matching beliefs
        matching_beliefs: list[Any] = []
        matching_ids: list[str] = []
        for belief in beliefs:
            if not hasattr(belief, 'statement'):
                continue
            belief_lower = belief.statement.lower()
            # Check for direct match or significant overlap
            if (statement_lower in belief_lower or
                    belief_lower in statement_lower or
                    len(set(statement_lower.split()) & set(belief_lower.split())) >= 2):
                matching_beliefs.append(belief)
                if hasattr(belief, 'id'):
                    matching_ids.append(belief.id)

        # Predicted outcomes of negation
        predicted_outcomes: list[str] = []

        if matching_beliefs:
            for belief in matching_beliefs[:5]:
                stmt = getattr(belief, 'statement', 'unknown')
                conf = getattr(belief, 'confidence', 0.5)
                predicted_outcomes.append(
                    f"Belief '{stmt}' (conf={conf:.2f}) would be contradicted"
                )

            # Find beliefs that depend on the negated ones
            supporting_evidence_count = sum(
                len(getattr(b, 'supporting_evidence', []))
                for b in matching_beliefs
            )
            if supporting_evidence_count > 0:
                predicted_outcomes.append(
                    f"{supporting_evidence_count} supporting evidence items would be invalidated"
                )
        else:
            predicted_outcomes.append(
                "No directly matching beliefs found — negation has minimal impact"
            )

        reasoning_chain = [
            f"Negating: {statement}",
            f"Found {len(matching_beliefs)} matching beliefs",
            f"Predicted {len(predicted_outcomes)} cascading effects",
        ]

        confidence = 0.4
        if matching_beliefs:
            avg_conf = sum(getattr(b, 'confidence', 0.5) for b in matching_beliefs) / len(matching_beliefs)
            confidence = min(0.7, 0.4 + avg_conf * 0.2)

        scenario = CounterfactualScenario(
            scenario_type=CounterfactualType.NEGATION,
            premise=negated,
            original_state={"matching_beliefs": len(matching_beliefs)},
            modified_state={"negated_beliefs": len(matching_beliefs)},
            predicted_outcomes=predicted_outcomes,
            affected_belief_ids=matching_ids,
            confidence=confidence,
            reasoning_chain=reasoning_chain,
            metadata={"original_statement": statement, "negated_statement": negated},
        )
        await self._persist_scenario(scenario)

        result = CounterfactualResult(
            query=f"What if not: {statement}",
            scenario_type=CounterfactualType.NEGATION,
            scenarios=[scenario],
            best_scenario_id=scenario.id,
            overall_confidence=confidence,
            reasoning_time_ms=(time.monotonic() - start_time) * 1000,
        )
        await self._persist_result(result)
        return result

    async def alternative_plans(
        self,
        objective: str,
        plans: list[Any] | None = None,
        goals: list[Any] | None = None,
    ) -> CounterfactualResult:
        """Answer: "What alternative plans exist?"

        Strategy:
        1. Identify existing plans related to the objective
        2. Generate alternative approaches based on different strategies
        3. Evaluate alternatives against current beliefs and goals

        Args:
            objective: The objective to find alternatives for.
            plans: Existing plans.
            goals: Current goals.

        Returns:
            CounterfactualResult with alternative scenarios.
        """
        start_time = time.monotonic()
        plans = plans or []
        goals = goals or []

        objective_lower = objective.lower()
        objective_terms = set(objective_lower.split())

        # Find related existing plans
        related_plans: list[Any] = []
        for plan in plans:
            if not hasattr(plan, 'name'):
                continue
            plan_terms = set(plan.name.lower().split())
            if hasattr(plan, 'description') and plan.description:
                plan_terms.update(plan.description.lower().split())
            overlap = objective_terms & plan_terms
            if len(overlap) >= 1:
                related_plans.append(plan)

        # Generate alternative approaches
        strategies = [
            ("Incremental approach", "Break the objective into small, sequential steps"),
            ("Parallel approach", "Execute multiple independent sub-objectives simultaneously"),
            ("Reverse engineering", "Start from the desired outcome and work backwards"),
            ("MVP approach", "Build the minimum viable version first, then iterate"),
        ]

        scenarios: list[CounterfactualScenario] = []
        for strategy_name, strategy_desc in strategies:
            predicted = [
                f"Strategy: {strategy_name} — {strategy_desc}",
                f"Related to {len(related_plans)} existing plan(s)",
            ]

            # Determine affected goals
            affected_goal_ids: list[str] = []
            for goal in goals:
                if hasattr(goal, 'description') and hasattr(goal, 'id'):
                    goal_terms = set(goal.description.lower().split())
                    if objective_terms & goal_terms:
                        affected_goal_ids.append(goal.id)

            confidence = 0.3 + (0.1 * len(related_plans))  # Higher if existing plans support it
            confidence = min(0.7, confidence)

            scenario = CounterfactualScenario(
                scenario_type=CounterfactualType.ALTERNATIVE,
                premise=f"Alternative approach for: {objective}",
                original_state={"existing_plans": len(related_plans)},
                modified_state={"strategy": strategy_name},
                predicted_outcomes=predicted,
                affected_goal_ids=affected_goal_ids,
                confidence=confidence,
                reasoning_chain=[
                    f"Objective: {objective}",
                    f"Found {len(related_plans)} related plans",
                    f"Strategy: {strategy_name}",
                ],
                metadata={"strategy": strategy_name},
            )
            scenarios.append(scenario)
            await self._persist_scenario(scenario)

        # Pick best scenario (highest confidence)
        best = max(scenarios, key=lambda s: s.confidence) if scenarios else None

        result = CounterfactualResult(
            query=f"Alternatives for: {objective}",
            scenario_type=CounterfactualType.ALTERNATIVE,
            scenarios=scenarios,
            best_scenario_id=best.id if best else None,
            overall_confidence=best.confidence if best else 0.0,
            reasoning_time_ms=(time.monotonic() - start_time) * 1000,
        )
        await self._persist_result(result)
        return result

    async def get_stats(self) -> dict[str, Any]:
        """Get counterfactual reasoning statistics."""
        conn = self._storage._conn
        if conn is None:
            return {"total_scenarios": 0, "total_queries": 0}

        cursor = await conn.execute("SELECT COUNT(*) FROM counterfactual_scenarios")
        total_scenarios = (await cursor.fetchone())[0]

        cursor = await conn.execute("SELECT COUNT(*) FROM counterfactual_results")
        total_queries = (await cursor.fetchone())[0]

        cursor = await conn.execute(
            "SELECT scenario_type, COUNT(*) as cnt FROM counterfactual_scenarios GROUP BY scenario_type"
        )
        by_type = {}
        for row in await cursor.fetchall():
            by_type[row[0]] = row[1]

        return {
            "total_scenarios": total_scenarios,
            "total_queries": total_queries,
            "by_type": by_type,
        }
