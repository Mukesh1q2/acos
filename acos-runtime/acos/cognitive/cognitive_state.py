"""
Cognitive State Engine — Central internal representation of ACOS cognitive state.

This is the 'conscious state' of the system — everything the system
'knows', 'believes', 'wants', and 'remembers' at a given point in time.

Every session updates CognitiveState, and it persists across sessions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from acos.schemas.v2_models import CognitiveState, Belief, Goal, BeliefStatus, GoalStatus


class CognitiveStateEngine:
    """
    Cognitive State Engine for ACOS v0.2.
    
    Manages the central internal representation that persists across sessions.
    The CognitiveState contains:
    - Beliefs (what the system believes)
    - Goals (what the system is working toward)
    - Active threads (what's currently being processed)
    - Recent memories (what was recently experienced)
    - Uncertainty estimates (what the system is unsure about)
    - Knowledge graph references (what concepts are known)
    """

    def __init__(self, storage: Any):
        """
        Initialize the Cognitive State Engine.
        
        Args:
            storage: StorageBackend instance for SQLite persistence
        """
        self._storage = storage
        self._current_state: CognitiveState | None = None

    async def initialize(self) -> None:
        """Initialize the engine and create DB tables. Load last state if available."""
        await self._create_tables()
        self._current_state = await self._load_last_state()
        if not self._current_state:
            self._current_state = CognitiveState()
            await self._save_state(self._current_state)

    async def _create_tables(self) -> None:
        """Create SQLite tables for cognitive state persistence."""
        conn = self._storage._conn
        if not conn:
            return

        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS cognitive_states (
                id TEXT PRIMARY KEY,
                beliefs TEXT DEFAULT '[]',
                goals TEXT DEFAULT '[]',
                active_thread_ids TEXT DEFAULT '[]',
                recent_memory_ids TEXT DEFAULT '[]',
                uncertainty_estimates TEXT DEFAULT '{}',
                knowledge_graph_concept_ids TEXT DEFAULT '[]',
                session_count INTEGER DEFAULT 0,
                last_query TEXT,
                last_synthesis TEXT,
                overall_confidence REAL DEFAULT 0.5,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_cognitive_states_updated ON cognitive_states(updated_at);
        """)
        await conn.commit()

    async def _load_last_state(self) -> CognitiveState | None:
        """Load the most recent cognitive state from the database."""
        conn = self._storage._conn
        if not conn:
            return None

        cursor = await conn.execute(
            "SELECT * FROM cognitive_states ORDER BY updated_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if not row:
            return None

        return self._row_to_state(row)

    async def _save_state(self, state: CognitiveState) -> None:
        """Save a cognitive state to the database."""
        conn = self._storage._conn
        if not conn:
            return

        await conn.execute(
            """INSERT OR REPLACE INTO cognitive_states
               (id, beliefs, goals, active_thread_ids, recent_memory_ids,
                uncertainty_estimates, knowledge_graph_concept_ids, session_count,
                last_query, last_synthesis, overall_confidence, metadata,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                state.id,
                json.dumps([b.model_dump(mode="json") for b in state.beliefs]),
                json.dumps([g.model_dump(mode="json") for g in state.goals]),
                json.dumps(state.active_thread_ids),
                json.dumps(state.recent_memory_ids),
                json.dumps(state.uncertainty_estimates),
                json.dumps(state.knowledge_graph_concept_ids),
                state.session_count,
                state.last_query,
                state.last_synthesis,
                state.overall_confidence,
                json.dumps(state.metadata),
                state.created_at.isoformat(),
                state.updated_at.isoformat(),
            ),
        )
        await conn.commit()

    @staticmethod
    def _row_to_state(row: Any) -> CognitiveState:
        """Convert a database row to a CognitiveState object."""
        beliefs = []
        for b in json.loads(row["beliefs"]):
            try:
                beliefs.append(Belief(**b))
            except Exception:
                pass

        goals = []
        for g in json.loads(row["goals"]):
            try:
                goals.append(Goal(**g))
            except Exception:
                pass

        return CognitiveState(
            id=row["id"],
            beliefs=beliefs,
            goals=goals,
            active_thread_ids=json.loads(row["active_thread_ids"]),
            recent_memory_ids=json.loads(row["recent_memory_ids"]),
            uncertainty_estimates=json.loads(row["uncertainty_estimates"]),
            knowledge_graph_concept_ids=json.loads(row["knowledge_graph_concept_ids"]),
            session_count=row["session_count"],
            last_query=row["last_query"],
            last_synthesis=row["last_synthesis"],
            overall_confidence=row["overall_confidence"],
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # ─── State Access ────────────────────────────────────────────────────────

    async def get_state(self) -> CognitiveState:
        """Get the current cognitive state."""
        if not self._current_state:
            self._current_state = CognitiveState()
        return self._current_state

    async def save(self) -> None:
        """Persist the current cognitive state to the database."""
        if self._current_state:
            self._current_state.updated_at = datetime.now(timezone.utc)
            await self._save_state(self._current_state)

    # ─── Belief Operations ───────────────────────────────────────────────────

    async def update_beliefs(self, beliefs: list[Belief]) -> None:
        """Update the beliefs in cognitive state."""
        state = await self.get_state()
        # Replace all active beliefs (full sync)
        state.beliefs = [b for b in beliefs if b.status == BeliefStatus.ACTIVE]
        state.updated_at = datetime.now(timezone.utc)
        await self.save()

    async def add_belief_to_state(self, belief: Belief) -> None:
        """Add a single belief to the cognitive state."""
        state = await self.get_state()
        # Remove existing version if any
        state.beliefs = [b for b in state.beliefs if b.id != belief.id]
        state.beliefs.append(belief)
        state.updated_at = datetime.now(timezone.utc)
        await self.save()

    async def get_active_beliefs(self) -> list[Belief]:
        """Get all active beliefs from cognitive state."""
        state = await self.get_state()
        return [b for b in state.beliefs if b.status == BeliefStatus.ACTIVE]

    async def get_belief_by_statement(self, statement: str) -> Belief | None:
        """Find a belief matching a statement (fuzzy)."""
        state = await self.get_state()
        statement_lower = statement.lower()
        for belief in state.beliefs:
            if belief.statement.lower() in statement_lower or statement_lower in belief.statement.lower():
                return belief
        return None

    # ─── Goal Operations ─────────────────────────────────────────────────────

    async def update_goals(self, goals: list[Goal]) -> None:
        """Update the goals in cognitive state."""
        state = await self.get_state()
        state.goals = [g for g in goals if g.status in (GoalStatus.ACTIVE, GoalStatus.PAUSED)]
        state.updated_at = datetime.now(timezone.utc)
        await self.save()

    async def add_goal_to_state(self, goal: Goal) -> None:
        """Add a single goal to the cognitive state."""
        state = await self.get_state()
        state.goals = [g for g in state.goals if g.id != goal.id]
        state.goals.append(goal)
        state.updated_at = datetime.now(timezone.utc)
        await self.save()

    async def get_active_goals(self) -> list[Goal]:
        """Get all active goals from cognitive state."""
        state = await self.get_state()
        return [g for g in state.goals if g.status == GoalStatus.ACTIVE]

    # ─── Thread Tracking ─────────────────────────────────────────────────────

    async def set_active_threads(self, thread_ids: list[str]) -> None:
        """Update the list of active reasoning threads."""
        state = await self.get_state()
        state.active_thread_ids = thread_ids
        state.updated_at = datetime.now(timezone.utc)
        await self.save()

    async def clear_active_threads(self) -> None:
        """Clear the active thread list (session ended)."""
        state = await self.get_state()
        state.active_thread_ids = []
        state.updated_at = datetime.now(timezone.utc)
        await self.save()

    # ─── Memory Tracking ─────────────────────────────────────────────────────

    async def add_recent_memory(self, memory_id: str) -> None:
        """Add a memory to the recent memory list."""
        state = await self.get_state()
        if memory_id not in state.recent_memory_ids:
            state.recent_memory_ids.append(memory_id)
        # Keep only last 100
        state.recent_memory_ids = state.recent_memory_ids[-100:]
        state.updated_at = datetime.now(timezone.utc)
        await self.save()

    # ─── Uncertainty Tracking ────────────────────────────────────────────────

    async def update_uncertainty(self, topic: str, uncertainty: float) -> None:
        """Update the uncertainty estimate for a topic."""
        state = await self.get_state()
        state.uncertainty_estimates[topic] = max(0.0, min(1.0, uncertainty))
        state.updated_at = datetime.now(timezone.utc)
        await self.save()

    async def get_uncertainty(self, topic: str) -> float:
        """Get the uncertainty estimate for a topic."""
        state = await self.get_state()
        return state.uncertainty_estimates.get(topic, 0.5)

    # ─── Knowledge Graph References ──────────────────────────────────────────

    async def add_knowledge_concept(self, concept_id: str) -> None:
        """Add a concept reference to the cognitive state."""
        state = await self.get_state()
        if concept_id not in state.knowledge_graph_concept_ids:
            state.knowledge_graph_concept_ids.append(concept_id)
        state.updated_at = datetime.now(timezone.utc)
        await self.save()

    async def set_knowledge_concepts(self, concept_ids: list[str]) -> None:
        """Set all knowledge graph concept references."""
        state = await self.get_state()
        state.knowledge_graph_concept_ids = concept_ids
        state.updated_at = datetime.now(timezone.utc)
        await self.save()

    # ─── Session Operations ──────────────────────────────────────────────────

    async def begin_session(self, query: str) -> None:
        """
        Mark the beginning of a new session.
        
        Updates session count and records the query.
        """
        state = await self.get_state()
        state.session_count += 1
        state.last_query = query
        state.updated_at = datetime.now(timezone.utc)
        await self.save()

    async def end_session(self, synthesis: str, overall_confidence: float) -> None:
        """
        Mark the end of a session.
        
        Updates the synthesis and confidence, clears active threads.
        """
        state = await self.get_state()
        state.last_synthesis = synthesis[:500]  # Truncate long syntheses
        state.overall_confidence = max(0.0, min(1.0, overall_confidence))
        state.active_thread_ids = []
        state.updated_at = datetime.now(timezone.utc)
        await self.save()

    # ─── Full State Snapshot ─────────────────────────────────────────────────

    async def get_snapshot(self) -> dict[str, Any]:
        """Get a complete snapshot of the cognitive state for API responses."""
        state = await self.get_state()
        return {
            "state_id": state.id,
            "active_beliefs": len([b for b in state.beliefs if b.status == BeliefStatus.ACTIVE]),
            "weakened_beliefs": len([b for b in state.beliefs if b.status == BeliefStatus.WEAKENED]),
            "active_goals": len([g for g in state.goals if g.status == GoalStatus.ACTIVE]),
            "knowledge_concepts": len(state.knowledge_graph_concept_ids),
            "overall_confidence": state.overall_confidence,
            "session_count": state.session_count,
            "last_query": state.last_query,
            "last_updated": state.updated_at.isoformat(),
            "uncertainty_topics": list(state.uncertainty_estimates.keys()),
        }

    async def get_full_state(self) -> dict[str, Any]:
        """Get the complete cognitive state as a dictionary."""
        state = await self.get_state()
        return state.model_dump(mode="json")

    # ─── Statistics ──────────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        """Get cognitive state statistics."""
        state = await self.get_state()
        active_beliefs = [b for b in state.beliefs if b.status == BeliefStatus.ACTIVE]
        active_goals = [g for g in state.goals if g.status == GoalStatus.ACTIVE]

        return {
            "session_count": state.session_count,
            "active_beliefs": len(active_beliefs),
            "weakened_beliefs": len([b for b in state.beliefs if b.status == BeliefStatus.WEAKENED]),
            "superseded_beliefs": len([b for b in state.beliefs if b.status == BeliefStatus.SUPERSEDED]),
            "active_goals": len(active_goals),
            "completed_goals": len([g for g in state.goals if g.status == GoalStatus.COMPLETED]),
            "knowledge_concepts": len(state.knowledge_graph_concept_ids),
            "overall_confidence": state.overall_confidence,
            "avg_belief_confidence": (
                sum(b.confidence for b in active_beliefs) / len(active_beliefs)
                if active_beliefs else 0.0
            ),
            "avg_goal_progress": (
                sum(g.progress for g in active_goals) / len(active_goals)
                if active_goals else 0.0
            ),
            "uncertainty_topics": len(state.uncertainty_estimates),
            "recent_memories": len(state.recent_memory_ids),
        }
