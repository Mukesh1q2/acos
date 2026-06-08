"""
State Evolution Engine — implement dS/dt = F(S) where S is the Cognitive State.

The engine must:
- Reinforce successful beliefs (increase confidence of well-evidenced beliefs)
- Weaken contradictory beliefs (reduce confidence of contradicted beliefs)
- Promote useful concepts (increase attention of frequently accessed concepts)
- Suppress irrelevant concepts (decrease attention of rarely accessed concepts)
- Consolidate similar beliefs
- Resolve contradictions where possible
- Apply natural decay to all elements over time

This is the continuous dynamics that makes the cognitive state *evolve*
rather than just persist.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v3_models import (
    EvolutionOperator,
    EvolutionResult,
    StateDelta,
    CognitiveNodeType,
    gen_id,
    utc_now,
)


class StateEvolutionEngine:
    """State Evolution Engine — dS/dt = F(S).

    Applies evolution operators to the cognitive state:

    - REINFORCE: Strengthen beliefs with supporting evidence
    - WEAKEN: Reduce confidence of contradicted beliefs
    - PROMOTE: Increase attention on useful concepts
    - SUPPRESS: Decrease attention on irrelevant concepts
    - CONSOLIDATE: Merge similar beliefs
    - DIVERGE: Split ambiguous beliefs
    - DECAY: Apply natural time decay
    - RESOLVE: Resolve contradictions

    Usage::

        store = StorageBackend()
        await store.initialize()

        engine = StateEvolutionEngine(store)
        await engine.initialize()

        result = await engine.evolve(
            beliefs=active_beliefs,
            concepts=active_concepts,
            goals=active_goals,
        )
    """

    # Reinforcement boost per supporting evidence item
    EVIDENCE_REINFORCEMENT_RATE = 0.03

    # Weakening per contradicting evidence item
    CONTRADICTION_WEAKENING_RATE = 0.05

    # Promotion boost per access
    ACCESS_PROMOTION_RATE = 0.02

    # Suppression threshold (access_count below this → suppress)
    SUPPRESSION_ACCESS_THRESHOLD = 2

    # Suppression rate
    SUPPRESSION_RATE = 0.05

    # Natural decay rate per cycle
    NATURAL_DECAY_RATE = 0.01

    # Minimum confidence before abandoning
    ABANDON_THRESHOLD = 0.1

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._delta_log: list[StateDelta] = []

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables for evolution audit trail."""
        await self._create_tables()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS state_deltas (
                id TEXT PRIMARY KEY,
                operator TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                before_value REAL DEFAULT 0.0,
                after_value REAL DEFAULT 0.0,
                delta REAL DEFAULT 0.0,
                reason TEXT DEFAULT '',
                evidence_ids TEXT DEFAULT '[]',
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evolution_results (
                id TEXT PRIMARY KEY,
                deltas TEXT DEFAULT '[]',
                beliefs_reinforced INTEGER DEFAULT 0,
                beliefs_weakened INTEGER DEFAULT 0,
                concepts_promoted INTEGER DEFAULT 0,
                concepts_suppressed INTEGER DEFAULT 0,
                contradictions_resolved INTEGER DEFAULT 0,
                total_changes INTEGER DEFAULT 0,
                evolution_time_ms REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_deltas_operator
                ON state_deltas(operator);
            CREATE INDEX IF NOT EXISTS idx_deltas_target
                ON state_deltas(target_id);
        """)
        await conn.commit()

    async def _persist_delta(self, delta: StateDelta) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO state_deltas
               (id, operator, target_type, target_id, before_value,
                after_value, delta, reason, evidence_ids, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                delta.id,
                delta.operator.value,
                delta.target_type.value,
                delta.target_id,
                delta.before_value,
                delta.after_value,
                delta.delta,
                delta.reason,
                json.dumps(delta.evidence_ids),
                delta.timestamp.isoformat(),
            ),
        )
        await conn.commit()

    async def _persist_result(self, result: EvolutionResult) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO evolution_results
               (id, deltas, beliefs_reinforced, beliefs_weakened,
                concepts_promoted, concepts_suppressed, contradictions_resolved,
                total_changes, evolution_time_ms, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.id,
                json.dumps([d.model_dump(mode="json") for d in result.deltas]),
                result.beliefs_reinforced,
                result.beliefs_weakened,
                result.concepts_promoted,
                result.concepts_suppressed,
                result.contradictions_resolved,
                result.total_changes,
                result.evolution_time_ms,
                result.timestamp.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Evolution Operators ────────────────────────────────────────────────

    def _make_delta(
        self,
        operator: EvolutionOperator,
        target_type: CognitiveNodeType,
        target_id: str,
        before: float,
        after: float,
        reason: str,
        evidence_ids: list[str] | None = None,
    ) -> StateDelta:
        """Create a StateDelta record."""
        return StateDelta(
            operator=operator,
            target_type=target_type,
            target_id=target_id,
            before_value=before,
            after_value=round(after, 6),
            delta=round(after - before, 6),
            reason=reason,
            evidence_ids=evidence_ids or [],
        )

    async def reinforce_beliefs(self, beliefs: list[Any]) -> list[StateDelta]:
        """Reinforce beliefs with supporting evidence.

        For each active belief with supporting evidence, increase confidence
        proportionally to evidence count and quality.

        Args:
            beliefs: List of Belief objects.

        Returns:
            List of StateDelta records for reinforced beliefs.
        """
        deltas: list[StateDelta] = []

        for belief in beliefs:
            if not hasattr(belief, 'supporting_evidence'):
                continue
            if not hasattr(belief, 'status') or str(belief.status) not in ('active', 'BeliefStatus.ACTIVE'):
                continue

            evidence_count = len(belief.supporting_evidence)
            if evidence_count == 0:
                continue

            before = belief.confidence
            boost = self.EVIDENCE_REINFORCEMENT_RATE * evidence_count
            after = min(1.0, before + boost)

            if after > before:
                delta = self._make_delta(
                    operator=EvolutionOperator.REINFORCE,
                    target_type=CognitiveNodeType.BELIEF,
                    target_id=belief.id,
                    before=before,
                    after=after,
                    reason=f"Reinforced by {evidence_count} supporting evidence items",
                    evidence_ids=[e.id for e in belief.supporting_evidence if hasattr(e, 'id')],
                )
                deltas.append(delta)
                # Apply the delta to the belief object
                belief.confidence = after
                if hasattr(belief, 'updated_at'):
                    belief.updated_at = utc_now()

        return deltas

    async def weaken_contradicted_beliefs(self, beliefs: list[Any]) -> list[StateDelta]:
        """Weaken beliefs with contradicting evidence.

        For each active belief with contradicting evidence, decrease confidence.

        Args:
            beliefs: List of Belief objects.

        Returns:
            List of StateDelta records for weakened beliefs.
        """
        deltas: list[StateDelta] = []

        for belief in beliefs:
            if not hasattr(belief, 'contradicting_evidence'):
                continue
            if not hasattr(belief, 'status') or str(belief.status) not in ('active', 'BeliefStatus.ACTIVE'):
                continue

            contra_count = len(belief.contradicting_evidence)
            if contra_count == 0:
                continue

            before = belief.confidence
            reduction = self.CONTRADICTION_WEAKENING_RATE * contra_count
            after = max(0.0, before - reduction)

            if after < before:
                delta = self._make_delta(
                    operator=EvolutionOperator.WEAKEN,
                    target_type=CognitiveNodeType.BELIEF,
                    target_id=belief.id,
                    before=before,
                    after=after,
                    reason=f"Weakened by {contra_count} contradicting evidence items",
                    evidence_ids=[e.id for e in belief.contradicting_evidence if hasattr(e, 'id')],
                )
                deltas.append(delta)
                belief.confidence = after
                if hasattr(belief, 'updated_at'):
                    belief.updated_at = utc_now()

        return deltas

    async def promote_useful_concepts(self, concepts: list[Any]) -> list[StateDelta]:
        """Promote concepts that are frequently accessed or have high connectivity.

        Increases attention/access metrics for concepts that are being used.

        Args:
            concepts: List of Concept objects.

        Returns:
            List of StateDelta records for promoted concepts.
        """
        deltas: list[StateDelta] = []

        for concept in concepts:
            if not hasattr(concept, 'access_count'):
                continue

            access_count = concept.access_count
            if access_count < 2:
                continue

            before = getattr(concept, 'confidence', 0.5)
            boost = self.ACCESS_PROMOTION_RATE * min(access_count, 20)  # Cap at 20 accesses
            after = min(1.0, before + boost)

            if after > before + 0.001:
                delta = self._make_delta(
                    operator=EvolutionOperator.PROMOTE,
                    target_type=CognitiveNodeType.CONCEPT,
                    target_id=concept.id,
                    before=before,
                    after=after,
                    reason=f"Promoted: accessed {access_count} times",
                )
                deltas.append(delta)
                concept.confidence = after
                if hasattr(concept, 'updated_at'):
                    concept.updated_at = utc_now()

        return deltas

    async def suppress_irrelevant_concepts(self, concepts: list[Any]) -> list[StateDelta]:
        """Suppress concepts with low access and low connectivity.

        Decreases confidence of concepts that are rarely accessed.

        Args:
            concepts: List of Concept objects.

        Returns:
            List of StateDelta records for suppressed concepts.
        """
        deltas: list[StateDelta] = []

        for concept in concepts:
            if not hasattr(concept, 'access_count'):
                continue

            if concept.access_count >= self.SUPPRESSION_ACCESS_THRESHOLD:
                continue

            before = getattr(concept, 'confidence', 0.5)
            after = max(0.0, before - self.SUPPRESSION_RATE)

            if after < before - 0.001:
                delta = self._make_delta(
                    operator=EvolutionOperator.SUPPRESS,
                    target_type=CognitiveNodeType.CONCEPT,
                    target_id=concept.id,
                    before=before,
                    after=after,
                    reason=f"Suppressed: only {concept.access_count} access(es)",
                )
                deltas.append(delta)
                concept.confidence = after
                if hasattr(concept, 'updated_at'):
                    concept.updated_at = utc_now()

        return deltas

    async def apply_natural_decay(self, beliefs: list[Any], concepts: list[Any]) -> list[StateDelta]:
        """Apply natural time decay to all cognitive elements.

        All confidences naturally decay slightly over time, ensuring
        that unsupported beliefs and unused concepts gradually fade.

        Args:
            beliefs: List of Belief objects.
            concepts: List of Concept objects.

        Returns:
            List of StateDelta records for decayed elements.
        """
        deltas: list[StateDelta] = []

        for belief in beliefs:
            if not hasattr(belief, 'confidence') or not hasattr(belief, 'id'):
                continue
            before = belief.confidence
            after = max(0.0, before - self.NATURAL_DECAY_RATE)
            if after < before - 0.0001:
                delta = self._make_delta(
                    operator=EvolutionOperator.DECAY,
                    target_type=CognitiveNodeType.BELIEF,
                    target_id=belief.id,
                    before=before,
                    after=after,
                    reason="Natural decay over time",
                )
                deltas.append(delta)
                belief.confidence = after

        for concept in concepts:
            if not hasattr(concept, 'confidence') or not hasattr(concept, 'id'):
                continue
            before = concept.confidence
            after = max(0.0, before - self.NATURAL_DECAY_RATE * 0.5)  # Concepts decay slower
            if after < before - 0.0001:
                delta = self._make_delta(
                    operator=EvolutionOperator.DECAY,
                    target_type=CognitiveNodeType.CONCEPT,
                    target_id=concept.id,
                    before=before,
                    after=after,
                    reason="Natural decay over time",
                )
                deltas.append(delta)
                concept.confidence = after

        return deltas

    async def resolve_contradictions(self, contradictions: list[tuple[Any, Any, str]]) -> list[StateDelta]:
        """Resolve contradictions by weakening the less-confident belief.

        Args:
            contradictions: List of (belief_1, belief_2, reason) tuples.

        Returns:
            List of StateDelta records for resolved contradictions.
        """
        deltas: list[StateDelta] = []

        for b1, b2, reason in contradictions:
            if not hasattr(b1, 'confidence') or not hasattr(b2, 'confidence'):
                continue

            # Weaken the less confident belief more
            if b1.confidence <= b2.confidence:
                weaker = b1
                stronger = b2
            else:
                weaker = b2
                stronger = b1

            before = weaker.confidence
            after = max(0.0, before * 0.8)  # 20% reduction

            delta = self._make_delta(
                operator=EvolutionOperator.RESOLVE,
                target_type=CognitiveNodeType.BELIEF,
                target_id=weaker.id,
                before=before,
                after=after,
                reason=f"Contradiction resolution: {reason}. Weaker belief penalized.",
            )
            deltas.append(delta)
            weaker.confidence = after

        return deltas

    # ─── Main Evolution Cycle ──────────────────────────────────────────────

    async def evolve(
        self,
        beliefs: list[Any] | None = None,
        concepts: list[Any] | None = None,
        goals: list[Any] | None = None,
        contradictions: list[tuple[Any, Any, str]] | None = None,
    ) -> EvolutionResult:
        """Run a complete evolution cycle: dS/dt = F(S).

        Applies all operators in order:
        1. Reinforce beliefs with supporting evidence
        2. Weaken beliefs with contradicting evidence
        3. Promote useful concepts
        4. Suppress irrelevant concepts
        5. Resolve contradictions
        6. Apply natural decay

        Args:
            beliefs: Current active beliefs.
            concepts: Current active concepts.
            goals: Current active goals.
            contradictions: Known contradictions.

        Returns:
            EvolutionResult with all deltas and summary statistics.
        """
        start_time = time.monotonic()

        beliefs = beliefs or []
        concepts = concepts or []
        contradictions = contradictions or []

        all_deltas: list[StateDelta] = []

        # 1. Reinforce
        reinforce_deltas = await self.reinforce_beliefs(beliefs)
        all_deltas.extend(reinforce_deltas)

        # 2. Weaken
        weaken_deltas = await self.weaken_contradicted_beliefs(beliefs)
        all_deltas.extend(weaken_deltas)

        # 3. Promote
        promote_deltas = await self.promote_useful_concepts(concepts)
        all_deltas.extend(promote_deltas)

        # 4. Suppress
        suppress_deltas = await self.suppress_irrelevant_concepts(concepts)
        all_deltas.extend(suppress_deltas)

        # 5. Resolve contradictions
        resolve_deltas = await self.resolve_contradictions(contradictions)
        all_deltas.extend(resolve_deltas)

        # 6. Natural decay
        decay_deltas = await self.apply_natural_decay(beliefs, concepts)
        all_deltas.extend(decay_deltas)

        # Persist all deltas
        for delta in all_deltas:
            await self._persist_delta(delta)

        result = EvolutionResult(
            deltas=all_deltas,
            beliefs_reinforced=len(reinforce_deltas),
            beliefs_weakened=len(weaken_deltas),
            concepts_promoted=len(promote_deltas),
            concepts_suppressed=len(suppress_deltas),
            contradictions_resolved=len(resolve_deltas),
            total_changes=len(all_deltas),
            evolution_time_ms=(time.monotonic() - start_time) * 1000,
        )

        await self._persist_result(result)
        return result

    async def get_stats(self) -> dict[str, Any]:
        """Get evolution statistics."""
        conn = self._storage._conn
        if conn is None:
            return {"total_deltas": 0, "total_cycles": 0}

        cursor = await conn.execute("SELECT COUNT(*) FROM state_deltas")
        total_deltas = (await cursor.fetchone())[0]

        cursor = await conn.execute("SELECT COUNT(*) FROM evolution_results")
        total_cycles = (await cursor.fetchone())[0]

        cursor = await conn.execute(
            "SELECT operator, COUNT(*) as cnt FROM state_deltas GROUP BY operator"
        )
        by_operator = {}
        for row in await cursor.fetchall():
            by_operator[row[0]] = row[1]

        return {
            "total_deltas": total_deltas,
            "total_cycles": total_cycles,
            "by_operator": by_operator,
        }
