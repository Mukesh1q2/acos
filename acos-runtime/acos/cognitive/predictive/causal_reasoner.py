"""
Causal Reasoner — represent and reason about causal relationships.

Represents: Cause -> Effect

Supports:
- Causal discovery: discover causal links from observations
- Intervention analysis: "What if we change X?" (do-calculus style)
- Counterfactual causality: "Would Y have happened if X were different?"

Uses the cognitive graph and transition data to identify and validate
causal relationships, distinguishing causation from correlation.
"""

from __future__ import annotations

import json
import time as time_mod
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v4_models import (
    CausalLink,
    CausalDirection,
    CausalStrength,
    InterventionResult,
    CausalDiscoveryResult,
    StateTransition,
    gen_id,
    utc_now,
)
from acos.cognitive.predictive.state_transition_graph import StateTransitionGraph


class CausalReasoner:
    """Causal Reasoner — discover and reason about causal relationships.

    Usage::

        store = StorageBackend()
        await store.initialize()

        cr = CausalReasoner(store, transition_graph)
        await cr.initialize()

        # Discover causal links from transitions
        result = await cr.discover_causes()

        # Analyze an intervention
        intervention = await cr.analyze_intervention(
            target="study_hours",
            new_value="8_hours",
            current_value="2_hours",
        )

        # Counterfactual causality
        counter = await cr.counterfactual_cause(
            observed_effect="exam_failed",
            hypothesized_cause="insufficient_study",
        )
    """

    # Minimum observations to establish a causal link
    MIN_OBSERVATIONS_FOR_CAUSALITY = 2
    # Minimum correlation to suggest causality
    MIN_CORRELATION_FOR_CAUSALITY = 0.5
    # Confidence boost from intervention evidence
    INTERVENTION_CONFIDENCE_BOOST = 0.2

    def __init__(
        self,
        storage: StorageBackend,
        transition_graph: StateTransitionGraph,
    ) -> None:
        self._storage = storage
        self._transition_graph = transition_graph
        self._causal_links: dict[str, CausalLink] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load existing causal links."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS causal_links (
                id TEXT PRIMARY KEY,
                cause_id TEXT NOT NULL,
                cause_label TEXT NOT NULL,
                effect_id TEXT NOT NULL,
                effect_label TEXT NOT NULL,
                direction TEXT NOT NULL,
                strength TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                supporting_observations INTEGER DEFAULT 0,
                contradicting_observations INTEGER DEFAULT 0,
                intervention_evidence INTEGER DEFAULT 0,
                mechanism TEXT DEFAULT '',
                mediator_ids TEXT DEFAULT '[]',
                confounder_ids TEXT DEFAULT '[]',
                preconditions TEXT DEFAULT '[]',
                context_description TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS intervention_results (
                id TEXT PRIMARY KEY,
                intervention_target TEXT NOT NULL,
                intervention_value TEXT NOT NULL,
                original_value TEXT DEFAULT '',
                predicted_effects TEXT DEFAULT '[]',
                affected_goal_ids TEXT DEFAULT '[]',
                affected_belief_ids TEXT DEFAULT '[]',
                causal_paths TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.3,
                reasoning_chain TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS causal_discoveries (
                id TEXT PRIMARY KEY,
                discovered_links TEXT DEFAULT '[]',
                rejected_links TEXT DEFAULT '[]',
                ambiguous_links TEXT DEFAULT '[]',
                confidence_threshold REAL DEFAULT 0.5,
                total_observations_used INTEGER DEFAULT 0,
                discovery_time_ms REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_cl_cause
                ON causal_links(cause_id);
            CREATE INDEX IF NOT EXISTS idx_cl_effect
                ON causal_links(effect_id);
            CREATE INDEX IF NOT EXISTS idx_cl_strength
                ON causal_links(strength);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        cursor = await conn.execute("SELECT * FROM causal_links")
        rows = await cursor.fetchall()
        for row in rows:
            link = CausalLink(
                id=row["id"],
                cause_id=row["cause_id"],
                cause_label=row["cause_label"],
                effect_id=row["effect_id"],
                effect_label=row["effect_label"],
                direction=CausalDirection(row["direction"]),
                strength=CausalStrength(row["strength"]),
                confidence=row["confidence"],
                supporting_observations=row["supporting_observations"],
                contradicting_observations=row["contradicting_observations"],
                intervention_evidence=row["intervention_evidence"],
                mechanism=row["mechanism"],
                mediator_ids=json.loads(row["mediator_ids"]) if row["mediator_ids"] else [],
                confounder_ids=json.loads(row["confounder_ids"]) if row["confounder_ids"] else [],
                preconditions=json.loads(row["preconditions"]) if row["preconditions"] else [],
                context_description=row["context_description"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            self._causal_links[link.id] = link

    async def _save_causal_link(self, link: CausalLink) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO causal_links
               (id, cause_id, cause_label, effect_id, effect_label, direction,
                strength, confidence, supporting_observations, contradicting_observations,
                intervention_evidence, mechanism, mediator_ids, confounder_ids,
                preconditions, context_description, metadata, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                link.id,
                link.cause_id,
                link.cause_label,
                link.effect_id,
                link.effect_label,
                link.direction.value,
                link.strength.value,
                link.confidence,
                link.supporting_observations,
                link.contradicting_observations,
                link.intervention_evidence,
                link.mechanism,
                json.dumps(link.mediator_ids),
                json.dumps(link.confounder_ids),
                json.dumps(link.preconditions),
                link.context_description,
                json.dumps(link.metadata),
                link.created_at.isoformat(),
                link.updated_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_intervention(self, result: InterventionResult) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO intervention_results
               (id, intervention_target, intervention_value, original_value,
                predicted_effects, affected_goal_ids, affected_belief_ids,
                causal_paths, confidence, reasoning_chain, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.id,
                result.intervention_target,
                result.intervention_value,
                result.original_value,
                json.dumps(result.predicted_effects),
                json.dumps(result.affected_goal_ids),
                json.dumps(result.affected_belief_ids),
                json.dumps(result.causal_paths),
                result.confidence,
                json.dumps(result.reasoning_chain),
                json.dumps(result.metadata),
                result.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_discovery(self, result: CausalDiscoveryResult) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO causal_discoveries
               (id, discovered_links, rejected_links, ambiguous_links,
                confidence_threshold, total_observations_used,
                discovery_time_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.id,
                json.dumps([l.model_dump(mode="json") for l in result.discovered_links]),
                json.dumps([l.model_dump(mode="json") for l in result.rejected_links]),
                json.dumps([l.model_dump(mode="json") for l in result.ambiguous_links]),
                result.confidence_threshold,
                result.total_observations_used,
                result.discovery_time_ms,
                result.created_at.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Causal Link Management ─────────────────────────────────────────────

    async def add_causal_link(
        self,
        cause_id: str,
        cause_label: str,
        effect_id: str,
        effect_label: str,
        direction: CausalDirection = CausalDirection.FORWARD,
        strength: CausalStrength = CausalStrength.CONTRIBUTING,
        confidence: float = 0.5,
        mechanism: str = "",
        context_description: str = "",
    ) -> CausalLink:
        """Add a causal link between two elements.

        Args:
            cause_id: ID of the causing element.
            cause_label: Human-readable cause description.
            effect_id: ID of the affected element.
            effect_label: Human-readable effect description.
            direction: Causal direction.
            strength: Causal strength classification.
            confidence: Initial confidence in this causal link.
            mechanism: How the cause produces the effect.
            context_description: Context for this causal relationship.

        Returns:
            The CausalLink.
        """
        # Check for existing link
        for link in self._causal_links.values():
            if link.cause_id == cause_id and link.effect_id == effect_id:
                # Update existing
                link.supporting_observations += 1
                link.confidence = min(1.0, link.confidence + 0.1)
                link.updated_at = utc_now()
                if mechanism:
                    link.mechanism = mechanism
                await self._save_causal_link(link)
                return link

        link = CausalLink(
            cause_id=cause_id,
            cause_label=cause_label,
            effect_id=effect_id,
            effect_label=effect_label,
            direction=direction,
            strength=strength,
            confidence=confidence,
            supporting_observations=1,
            mechanism=mechanism,
            context_description=context_description,
        )
        self._causal_links[link.id] = link
        await self._save_causal_link(link)
        return link

    async def add_contradicting_observation(self, causal_link_id: str) -> CausalLink | None:
        """Record an observation that contradicts a causal link.

        Args:
            causal_link_id: The link to contradict.

        Returns:
            The updated CausalLink, or None.
        """
        link = self._causal_links.get(causal_link_id)
        if link is None:
            return None

        link.contradicting_observations += 1
        # Reduce confidence
        link.confidence = max(0.0, link.confidence - 0.05)
        link.updated_at = utc_now()
        await self._save_causal_link(link)
        return link

    async def add_intervention_evidence(self, causal_link_id: str) -> CausalLink | None:
        """Record intervention evidence supporting a causal link.

        Intervention evidence is the strongest form of causal evidence.

        Args:
            causal_link_id: The link to support.

        Returns:
            The updated CausalLink, or None.
        """
        link = self._causal_links.get(causal_link_id)
        if link is None:
            return None

        link.intervention_evidence += 1
        link.confidence = min(1.0, link.confidence + self.INTERVENTION_CONFIDENCE_BOOST)
        link.updated_at = utc_now()
        await self._save_causal_link(link)
        return link

    # ─── Causal Discovery ───────────────────────────────────────────────────

    async def discover_causes(
        self,
        confidence_threshold: float = 0.5,
    ) -> CausalDiscoveryResult:
        """Discover causal links from observed transitions.

        Analyzes the transition graph to identify patterns that suggest
        causal relationships:
        1. Temporal precedence: Cause precedes effect in transitions
        2. Consistency: The cause-effect pattern repeats consistently
        3. Specificity: The cause specifically produces this effect

        Args:
            confidence_threshold: Minimum confidence to accept a causal link.

        Returns:
            CausalDiscoveryResult with discovered, rejected, and ambiguous links.
        """
        start_time = time_mod.monotonic()

        discovered: list[CausalLink] = []
        rejected: list[CausalLink] = []
        ambiguous: list[CausalLink] = []

        transitions = await self._transition_graph.get_all_transitions()
        total_observations = sum(t.frequency for t in transitions)

        # Group transitions by action (potential cause)
        action_groups: dict[str, list[StateTransition]] = {}
        for t in transitions:
            if t.action:
                action_groups.setdefault(t.action, []).append(t)

        # Analyze each action group for causal patterns
        for action, group_transitions in action_groups.items():
            total_action_frequency = sum(t.frequency for t in group_transitions)

            if total_action_frequency < self.MIN_OBSERVATIONS_FOR_CAUSALITY:
                continue

            # Check for consistent cause-effect patterns
            # Group by (source, target) pairs
            effect_counts: dict[str, int] = {}
            for t in group_transitions:
                key = f"{t.source_state} -> {t.target_state}"
                effect_counts[key] = effect_counts.get(key, 0) + t.frequency

            for effect_key, count in effect_counts.items():
                source, target = effect_key.split(" -> ")
                # Consistency: how often does this action produce this specific effect?
                consistency = count / total_action_frequency

                if consistency < self.MIN_CORRELATION_FOR_CAUSALITY:
                    # Not consistent enough — reject
                    link = CausalLink(
                        cause_id=f"action:{action}",
                        cause_label=f"Action: {action}",
                        effect_id=f"transition:{source}->{target}",
                        effect_label=f"{source} → {target}",
                        direction=CausalDirection.FORWARD,
                        strength=CausalStrength.CONTRIBUTING,
                        confidence=consistency * 0.5,  # Low confidence
                        supporting_observations=count,
                        contradicting_observations=total_action_frequency - count,
                    )
                    rejected.append(link)
                    continue

                # Determine strength
                if consistency >= 0.9:
                    strength = CausalStrength.SUFFICIENT
                elif consistency >= 0.7:
                    strength = CausalStrength.NECESSARY
                else:
                    strength = CausalStrength.CONTRIBUTING

                confidence = consistency * 0.8  # Scale down for caution

                # Check for existing link
                existing = None
                for link in self._causal_links.values():
                    if link.cause_label == f"Action: {action}" and link.effect_label == f"{source} → {target}":
                        existing = link
                        break

                if existing:
                    # Update existing link
                    existing.supporting_observations += count
                    existing.confidence = min(1.0, existing.confidence + 0.05)
                    existing.updated_at = utc_now()
                    await self._save_causal_link(existing)
                    discovered.append(existing)
                else:
                    link = CausalLink(
                        cause_id=f"action:{action}",
                        cause_label=f"Action: {action}",
                        effect_id=f"transition:{source}->{target}",
                        effect_label=f"{source} → {target}",
                        direction=CausalDirection.FORWARD,
                        strength=strength,
                        confidence=confidence,
                        supporting_observations=count,
                        contradicting_observations=total_action_frequency - count,
                        mechanism=f"Action '{action}' triggers state change from {source} to {target}",
                        context_description=f"Observed in {count}/{total_action_frequency} instances",
                    )
                    self._causal_links[link.id] = link
                    await self._save_causal_link(link)

                    if confidence >= confidence_threshold:
                        discovered.append(link)
                    elif confidence >= confidence_threshold * 0.5:
                        ambiguous.append(link)
                    else:
                        rejected.append(link)

        result = CausalDiscoveryResult(
            discovered_links=discovered,
            rejected_links=rejected,
            ambiguous_links=ambiguous,
            confidence_threshold=confidence_threshold,
            total_observations_used=total_observations,
            discovery_time_ms=(time_mod.monotonic() - start_time) * 1000,
        )
        await self._save_discovery(result)
        return result

    # ─── Intervention Analysis ──────────────────────────────────────────────

    async def analyze_intervention(
        self,
        target: str,
        new_value: str,
        original_value: str = "",
        affected_goal_ids: list[str] | None = None,
        affected_belief_ids: list[str] | None = None,
    ) -> InterventionResult:
        """Analyze the effects of an intervention (do-calculus style).

        Answers: "What would happen if we set X to Y?"

        Args:
            target: The element to intervene on.
            new_value: The value to set.
            original_value: Current value.
            affected_goal_ids: Goals potentially affected.
            affected_belief_ids: Beliefs potentially affected.

        Returns:
            InterventionResult with predicted effects.
        """
        start_time = time_mod.monotonic()

        predicted_effects: list[dict[str, Any]] = []
        causal_paths: list[list[str]] = []
        reasoning_chain = [
            f"Intervention: set '{target}' from '{original_value}' to '{new_value}'",
        ]

        # Find causal links where the target is a cause
        forward_links = [
            link for link in self._causal_links.values()
            if link.cause_id == target or link.cause_label == target
        ]

        if forward_links:
            reasoning_chain.append(
                f"Found {len(forward_links)} causal link(s) originating from '{target}'"
            )

            for link in forward_links[:10]:  # Limit cascading
                effect = {
                    "effect_id": link.effect_id,
                    "effect_label": link.effect_label,
                    "mechanism": link.mechanism,
                    "confidence": link.confidence,
                    "strength": link.strength.value,
                }
                predicted_effects.append(effect)
                causal_paths.append([link.cause_label, link.effect_label])
        else:
            reasoning_chain.append(
                f"No known causal links from '{target}' — effects are uncertain"
            )

        # Check if target is an effect of other causes (for context)
        backward_links = [
            link for link in self._causal_links.values()
            if link.effect_id == target or link.effect_label == target
        ]
        if backward_links:
            reasoning_chain.append(
                f"'{target}' is also an effect of {len(backward_links)} other cause(s)"
            )

        # Calculate confidence
        confidence = 0.3  # Base confidence for intervention analysis
        if forward_links:
            avg_link_conf = sum(l.confidence for l in forward_links) / len(forward_links)
            confidence = min(0.8, 0.3 + avg_link_conf * 0.4)

        result = InterventionResult(
            intervention_target=target,
            intervention_value=new_value,
            original_value=original_value,
            predicted_effects=predicted_effects,
            affected_goal_ids=affected_goal_ids or [],
            affected_belief_ids=affected_belief_ids or [],
            causal_paths=causal_paths,
            confidence=confidence,
            reasoning_chain=reasoning_chain,
        )
        await self._save_intervention(result)
        return result

    # ─── Counterfactual Causality ───────────────────────────────────────────

    async def counterfactual_cause(
        self,
        observed_effect: str,
        hypothesized_cause: str,
    ) -> InterventionResult:
        """Counterfactual causal analysis.

        Answers: "Would the effect have occurred if the cause were different?"

        This is the counterfactual approach to causality:
        If the hypothesized cause were removed/changed, would the effect
        still have occurred?

        Args:
            observed_effect: The observed effect.
            hypothesized_cause: The hypothesized cause to test.

        Returns:
            InterventionResult analyzing the counterfactual.
        """
        reasoning_chain = [
            f"Observed effect: {observed_effect}",
            f"Hypothesized cause: {hypothesized_cause}",
            f"Counterfactual: Would '{observed_effect}' occur without '{hypothesized_cause}'?",
        ]

        # Find causal links supporting this cause-effect relationship
        supporting_links = []
        for link in self._causal_links.values():
            cause_match = (link.cause_id == hypothesized_cause or
                          hypothesized_cause.lower() in link.cause_label.lower())
            effect_match = (link.effect_id == observed_effect or
                           observed_effect.lower() in link.effect_label.lower())
            if cause_match and effect_match:
                supporting_links.append(link)

        predicted_effects = []
        causal_paths = []

        if supporting_links:
            # There is evidence for this causal relationship
            for link in supporting_links[:5]:
                # In the counterfactual world, removing the cause would prevent the effect
                counterfactual_effect = {
                    "effect_id": link.effect_id,
                    "effect_label": link.effect_label,
                    "mechanism": f"Without '{hypothesized_cause}', '{link.effect_label}' may not occur",
                    "confidence": link.confidence * 0.7,  # Reduced confidence for counterfactual
                    "strength": link.strength.value,
                    "counterfactual": True,
                }
                predicted_effects.append(counterfactual_effect)
                causal_paths.append([f"NOT {link.cause_label}", link.effect_label + " (prevented?)"])

            avg_conf = sum(l.confidence for l in supporting_links) / len(supporting_links)
            confidence = min(0.7, avg_conf * 0.6)

            reasoning_chain.append(
                f"Found {len(supporting_links)} supporting causal link(s) — "
                f"removing '{hypothesized_cause}' would likely affect '{observed_effect}'"
            )
        else:
            confidence = 0.2
            reasoning_chain.append(
                f"No supporting causal links found — "
                f"removing '{hypothesized_cause}' likely has no effect on '{observed_effect}'"
            )

        result = InterventionResult(
            intervention_target=hypothesized_cause,
            intervention_value="REMOVED",  # Counterfactual: the cause doesn't exist
            original_value="PRESENT",
            predicted_effects=predicted_effects,
            causal_paths=causal_paths,
            confidence=confidence,
            reasoning_chain=reasoning_chain,
            metadata={"analysis_type": "counterfactual_causality"},
        )
        await self._save_intervention(result)
        return result

    # ─── Query Methods ──────────────────────────────────────────────────────

    async def get_causes_of(self, effect_id: str) -> list[CausalLink]:
        """Get all known causes of an effect.

        Args:
            effect_id: The effect to find causes for.

        Returns:
            List of CausalLink where this element is the effect.
        """
        results = []
        for link in self._causal_links.values():
            if link.effect_id == effect_id:
                results.append(link)
        results.sort(key=lambda l: l.confidence, reverse=True)
        return results

    async def get_effects_of(self, cause_id: str) -> list[CausalLink]:
        """Get all known effects of a cause.

        Args:
            cause_id: The cause to find effects for.

        Returns:
            List of CausalLink where this element is the cause.
        """
        results = []
        for link in self._causal_links.values():
            if link.cause_id == cause_id:
                results.append(link)
        results.sort(key=lambda l: l.confidence, reverse=True)
        return results

    async def get_causal_chain(self, start_id: str, max_depth: int = 5) -> list[CausalLink]:
        """Trace a causal chain from a starting element.

        Follows forward causal links from the start element.

        Args:
            start_id: The starting element.
            max_depth: Maximum chain depth.

        Returns:
            List of CausalLink forming the chain.
        """
        chain: list[CausalLink] = []
        visited: set[str] = set()
        current_id = start_id

        for _ in range(max_depth):
            if current_id in visited:
                break
            visited.add(current_id)

            effects = await self.get_effects_of(current_id)
            if not effects:
                break

            # Follow the highest-confidence link
            best = effects[0]
            chain.append(best)
            current_id = best.effect_id

        return chain

    async def get_stats(self) -> dict[str, Any]:
        """Get causal reasoner statistics."""
        total = len(self._causal_links)
        by_strength: dict[str, int] = {}
        for link in self._causal_links.values():
            key = link.strength.value
            by_strength[key] = by_strength.get(key, 0) + 1

        avg_confidence = 0.0
        with_intervention = 0
        if total > 0:
            avg_confidence = sum(l.confidence for l in self._causal_links.values()) / total
            with_intervention = sum(1 for l in self._causal_links.values() if l.intervention_evidence > 0)

        return {
            "total_causal_links": total,
            "by_strength": by_strength,
            "avg_confidence": round(avg_confidence, 4),
            "links_with_intervention_evidence": with_intervention,
        }
