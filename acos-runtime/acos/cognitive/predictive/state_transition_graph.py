"""
State Transition Graph — represent observed state transitions.

Represents: State A --action--> State B

Tracks:
- Transition frequency (how often observed)
- Transition confidence (how reliable)
- Transition cost (resource expenditure)

Uses NetworkX for in-memory graph operations with SQLite persistence.
This is the foundation for the WorldModel.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import networkx as nx

from acos.memory.store import StorageBackend
from acos.schemas.v4_models import (
    StateTransition,
    StateVector,
    TransitionType,
    gen_id,
    utc_now,
)


class StateTransitionGraph:
    """State Transition Graph — track observed and inferred state transitions.

    Usage::

        store = StorageBackend()
        await store.initialize()

        stg = StateTransitionGraph(store)
        await stg.initialize()

        # Record an observed transition
        transition = await stg.record_transition(
            source_state="idle",
            target_state="learning",
            action="start_study",
        )

        # Query transitions
        outgoing = await stg.get_transitions_from("idle")
        path = await stg.find_transition_path("idle", "expert")
    """

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        # Directed multigraph: same source+target can have multiple actions
        self._graph: nx.DiGraph = nx.DiGraph()
        self._transitions: dict[str, StateTransition] = {}
        self._states: dict[str, StateVector] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load existing transitions."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS state_transitions (
                id TEXT PRIMARY KEY,
                source_state TEXT NOT NULL,
                target_state TEXT NOT NULL,
                action TEXT DEFAULT '',
                transition_type TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.5,
                cost REAL DEFAULT 0.0,
                duration_estimate REAL DEFAULT 0.0,
                preconditions TEXT DEFAULT '[]',
                side_effects TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS state_vectors (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                features TEXT DEFAULT '{}',
                belief_ids TEXT DEFAULT '[]',
                goal_ids TEXT DEFAULT '[]',
                concept_ids TEXT DEFAULT '[]',
                uncertainty_level REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_st_source
                ON state_transitions(source_state);
            CREATE INDEX IF NOT EXISTS idx_st_target
                ON state_transitions(target_state);
            CREATE INDEX IF NOT EXISTS idx_st_action
                ON state_transitions(action);
            CREATE INDEX IF NOT EXISTS idx_sv_label
                ON state_vectors(label);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        assert conn is not None

        # Load state vectors
        cursor = await conn.execute("SELECT * FROM state_vectors")
        rows = await cursor.fetchall()
        for row in rows:
            sv = StateVector(
                id=row["id"],
                label=row["label"],
                features=json.loads(row["features"]) if row["features"] else {},
                belief_ids=json.loads(row["belief_ids"]) if row["belief_ids"] else [],
                goal_ids=json.loads(row["goal_ids"]) if row["goal_ids"] else [],
                concept_ids=json.loads(row["concept_ids"]) if row["concept_ids"] else [],
                uncertainty_level=row["uncertainty_level"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )
            self._states[sv.label] = sv
            self._graph.add_node(sv.label, data=sv)

        # Load transitions
        cursor = await conn.execute("SELECT * FROM state_transitions")
        rows = await cursor.fetchall()
        for row in rows:
            st = StateTransition(
                id=row["id"],
                source_state=row["source_state"],
                target_state=row["target_state"],
                action=row["action"],
                transition_type=TransitionType(row["transition_type"]),
                frequency=row["frequency"],
                confidence=row["confidence"],
                cost=row["cost"],
                duration_estimate=row["duration_estimate"],
                preconditions=json.loads(row["preconditions"]) if row["preconditions"] else [],
                side_effects=json.loads(row["side_effects"]) if row["side_effects"] else [],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            self._transitions[st.id] = st
            # Add edge if both nodes exist
            if st.source_state in self._states and st.target_state in self._states:
                self._graph.add_edge(
                    st.source_state, st.target_state,
                    action=st.action, data=st,
                )

    async def _save_transition(self, transition: StateTransition) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO state_transitions
               (id, source_state, target_state, action, transition_type,
                frequency, confidence, cost, duration_estimate, preconditions,
                side_effects, metadata, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                transition.id,
                transition.source_state,
                transition.target_state,
                transition.action,
                transition.transition_type.value,
                transition.frequency,
                transition.confidence,
                transition.cost,
                transition.duration_estimate,
                json.dumps(transition.preconditions),
                json.dumps(transition.side_effects),
                json.dumps(transition.metadata),
                transition.created_at.isoformat(),
                transition.updated_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_state_vector(self, sv: StateVector) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO state_vectors
               (id, label, features, belief_ids, goal_ids, concept_ids,
                uncertainty_level, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sv.id,
                sv.label,
                json.dumps(sv.features),
                json.dumps(sv.belief_ids),
                json.dumps(sv.goal_ids),
                json.dumps(sv.concept_ids),
                sv.uncertainty_level,
                sv.timestamp.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Core API ───────────────────────────────────────────────────────────

    async def register_state(
        self,
        label: str,
        features: dict[str, float] | None = None,
        belief_ids: list[str] | None = None,
        goal_ids: list[str] | None = None,
        concept_ids: list[str] | None = None,
        uncertainty_level: float = 0.0,
    ) -> StateVector:
        """Register a new state (or update an existing one).

        Args:
            label: Human-readable state identifier.
            features: State feature vector.
            belief_ids: Beliefs active in this state.
            goal_ids: Goals active in this state.
            concept_ids: Concepts active in this state.
            uncertainty_level: Overall uncertainty in this state.

        Returns:
            The StateVector.
        """
        if label in self._states:
            existing = self._states[label]
            if features:
                existing.features.update(features)
            if belief_ids:
                existing.belief_ids = belief_ids
            if goal_ids:
                existing.goal_ids = goal_ids
            if concept_ids:
                existing.concept_ids = concept_ids
            existing.uncertainty_level = uncertainty_level
            existing.timestamp = utc_now()
            await self._save_state_vector(existing)
            return existing

        sv = StateVector(
            label=label,
            features=features or {},
            belief_ids=belief_ids or [],
            goal_ids=goal_ids or [],
            concept_ids=concept_ids or [],
            uncertainty_level=uncertainty_level,
        )
        self._states[label] = sv
        self._graph.add_node(label, data=sv)
        await self._save_state_vector(sv)
        return sv

    async def record_transition(
        self,
        source_state: str,
        target_state: str,
        action: str = "",
        transition_type: TransitionType = TransitionType.PROBABILISTIC,
        confidence: float = 0.5,
        cost: float = 0.0,
        duration_estimate: float = 0.0,
        preconditions: list[str] | None = None,
        side_effects: list[str] | None = None,
    ) -> StateTransition:
        """Record an observed state transition.

        If a matching transition (same source, target, action) exists,
        increments its frequency and updates confidence.

        Args:
            source_state: Source state label.
            target_state: Target state label.
            action: The action that triggers this transition.
            transition_type: Type of transition.
            confidence: Confidence in this observation.
            cost: Resource cost.
            duration_estimate: Expected duration.
            preconditions: Required preconditions.
            side_effects: Observed side effects.

        Returns:
            The StateTransition (new or updated).
        """
        # Ensure both states exist
        if source_state not in self._states:
            await self.register_state(source_state)
        if target_state not in self._states:
            await self.register_state(target_state)

        # Check for existing transition with same source, target, action
        for existing in self._transitions.values():
            if (existing.source_state == source_state and
                    existing.target_state == target_state and
                    existing.action == action):
                # Update existing: increment frequency, adjust confidence
                existing.frequency += 1
                # Bayesian update: confidence increases with observations
                existing.confidence = min(1.0, existing.confidence + (1.0 - existing.confidence) * 0.1)
                if cost > 0:
                    # Running average of cost
                    existing.cost = (existing.cost * (existing.frequency - 1) + cost) / existing.frequency
                if duration_estimate > 0:
                    existing.duration_estimate = (
                        existing.duration_estimate * (existing.frequency - 1) + duration_estimate
                    ) / existing.frequency
                if preconditions:
                    for p in preconditions:
                        if p not in existing.preconditions:
                            existing.preconditions.append(p)
                if side_effects:
                    for s in side_effects:
                        if s not in existing.side_effects:
                            existing.side_effects.append(s)
                existing.updated_at = utc_now()
                await self._save_transition(existing)
                return existing

        # Create new transition
        transition = StateTransition(
            source_state=source_state,
            target_state=target_state,
            action=action,
            transition_type=transition_type,
            frequency=1,
            confidence=confidence,
            cost=cost,
            duration_estimate=duration_estimate,
            preconditions=preconditions or [],
            side_effects=side_effects or [],
        )
        self._transitions[transition.id] = transition
        self._graph.add_edge(
            source_state, target_state,
            action=action, data=transition,
        )
        await self._save_transition(transition)
        return transition

    async def get_transitions_from(self, state: str) -> list[StateTransition]:
        """Get all transitions originating from a state.

        Args:
            state: Source state label.

        Returns:
            List of StateTransition objects.
        """
        results = []
        for t in self._transitions.values():
            if t.source_state == state:
                results.append(t)
        # Sort by confidence descending
        results.sort(key=lambda t: t.confidence, reverse=True)
        return results

    async def get_transitions_to(self, state: str) -> list[StateTransition]:
        """Get all transitions leading to a state.

        Args:
            state: Target state label.

        Returns:
            List of StateTransition objects.
        """
        results = []
        for t in self._transitions.values():
            if t.target_state == state:
                results.append(t)
        results.sort(key=lambda t: t.confidence, reverse=True)
        return results

    async def get_transition(
        self, source_state: str, target_state: str, action: str = ""
    ) -> StateTransition | None:
        """Get a specific transition.

        Args:
            source_state: Source state.
            target_state: Target state.
            action: Action (empty string matches any).

        Returns:
            The most confident matching transition, or None.
        """
        best: StateTransition | None = None
        for t in self._transitions.values():
            if t.source_state == source_state and t.target_state == target_state:
                if action and t.action != action:
                    continue
                if best is None or t.confidence > best.confidence:
                    best = t
        return best

    async def find_transition_path(
        self, source_state: str, target_state: str
    ) -> list[StateTransition] | None:
        """Find the highest-confidence path between two states.

        Uses shortest path in the transition graph.

        Args:
            source_state: Starting state.
            target_state: Destination state.

        Returns:
            List of transitions along the path, or None if unreachable.
        """
        if source_state not in self._states or target_state not in self._states:
            return None

        try:
            path_labels = nx.shortest_path(self._graph, source_state, target_state)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

        # Convert labels to transitions
        transitions: list[StateTransition] = []
        for i in range(len(path_labels) - 1):
            t = await self.get_transition(path_labels[i], path_labels[i + 1])
            if t:
                transitions.append(t)
            else:
                return None  # Gap in path

        return transitions

    async def get_most_probable_next_state(
        self, current_state: str, action: str = ""
    ) -> tuple[str, float] | None:
        """Get the most probable next state from current state.

        Args:
            current_state: Current state label.
            action: Optional action filter.

        Returns:
            Tuple of (next_state_label, probability) or None.
        """
        transitions = await self.get_transitions_from(current_state)
        if action:
            transitions = [t for t in transitions if t.action == action]

        if not transitions:
            return None

        best = max(transitions, key=lambda t: t.confidence)
        return (best.target_state, best.confidence)

    async def get_state(self, label: str) -> StateVector | None:
        """Get a state vector by label."""
        return self._states.get(label)

    async def get_all_states(self) -> list[StateVector]:
        """Get all registered states."""
        return list(self._states.values())

    async def get_all_transitions(self) -> list[StateTransition]:
        """Get all recorded transitions."""
        return list(self._transitions.values())

    async def compute_transition_probability(
        self, source_state: str, target_state: str, action: str = ""
    ) -> float:
        """Compute the probability of transitioning from source to target.

        Based on observed frequency of the specific transition vs all
        transitions from the source state.

        Args:
            source_state: Source state.
            target_state: Target state.
            action: Optional action filter.

        Returns:
            Probability [0, 1].
        """
        outgoing = await self.get_transitions_from(source_state)
        if action:
            outgoing = [t for t in outgoing if t.action == action]

        if not outgoing:
            return 0.0

        total_frequency = sum(t.frequency for t in outgoing)
        matching = [t for t in outgoing if t.target_state == target_state]
        if not matching:
            return 0.0

        matching_frequency = sum(t.frequency for t in matching)
        return matching_frequency / total_frequency if total_frequency > 0 else 0.0

    async def get_stats(self) -> dict[str, Any]:
        """Get transition graph statistics."""
        return {
            "total_states": len(self._states),
            "total_transitions": len(self._transitions),
            "total_observations": sum(t.frequency for t in self._transitions.values()),
            "avg_confidence": (
                sum(t.confidence for t in self._transitions.values()) / len(self._transitions)
                if self._transitions else 0.0
            ),
            "avg_cost": (
                sum(t.cost for t in self._transitions.values()) / len(self._transitions)
                if self._transitions else 0.0
            ),
            "graph_density": nx.density(self._graph) if self._states else 0.0,
            "unique_actions": len(set(t.action for t in self._transitions.values() if t.action)),
        }
