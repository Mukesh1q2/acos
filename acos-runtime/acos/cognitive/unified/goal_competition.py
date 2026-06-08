"""
Goal Competition Engine — goals compete for attention and resources.

Responsibilities:
- Manage a dynamic pool of competing goals
- Compute composite scores from weighted competition factors
- Rank goals and determine winners
- Handle urgency escalation for blocked goals (deadlines approaching)
- Track progress momentum for goals making recent progress
- Persist competition entries and results to SQLite

Competition factors with default weights:
    importance:               0.25
    urgency:                  0.20
    uncertainty:              0.15  (uncertain goals need attention)
    expected_reward:          0.15
    dependency_satisfaction:  0.10
    attention_score:          0.10
    progress_momentum:        0.05

Composite score = weighted sum of all factors.
"""

from __future__ import annotations

import json
import math
import time as time_mod
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v5_models import (
    CompetitionFactor,
    CompetitionResult,
    GoalCompetitionEntry,
    gen_id,
    utc_now,
)

# ─── Default factor weights ──────────────────────────────────────────────────
DEFAULT_WEIGHTS: dict[str, float] = {
    CompetitionFactor.IMPORTANCE.value: 0.25,
    CompetitionFactor.URGENCY.value: 0.20,
    CompetitionFactor.UNCERTAINTY.value: 0.15,
    CompetitionFactor.EXPECTED_REWARD.value: 0.15,
    CompetitionFactor.DEPENDENCY_SATISFACTION.value: 0.10,
    CompetitionFactor.ATTENTION_SCORE.value: 0.10,
    CompetitionFactor.PROGRESS_MOMENTUM.value: 0.05,
}

# Urgency escalation rate: blocked goals gain urgency over time
# Each 60 seconds of being blocked adds this much urgency
URGENCY_ESCALATION_PER_MINUTE = 0.02

# Progress momentum decay: recent progress has exponential decay
MOMENTUM_DECAY_RATE = 0.005  # per second


class GoalCompetitionEngine:
    """Goal Competition Engine — dynamic prioritization through competition.

    Usage::

        store = StorageBackend()
        await store.initialize()

        engine = GoalCompetitionEngine(store)
        await engine.initialize()

        # Enter goals into competition
        entry1 = await engine.enter_competition(
            goal_id="goal_1",
            goal_description="Build the API",
            importance=0.8,
            urgency=0.6,
            uncertainty=0.3,
            expected_reward=0.7,
            dependency_satisfaction=1.0,
            attention_score=0.5,
            progress_momentum=0.2,
        )

        # Run the competition
        result = await engine.run_competition()
        winner = engine.get_winner()
    """

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._entries: dict[str, GoalCompetitionEntry] = {}
        self._competition_history: list[CompetitionResult] = []
        self._factor_weights: dict[str, float] = dict(DEFAULT_WEIGHTS)

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize the engine: create tables and load existing data."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS goal_competition_entries (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                goal_description TEXT DEFAULT '',
                importance REAL DEFAULT 0.5,
                urgency REAL DEFAULT 0.5,
                uncertainty REAL DEFAULT 0.5,
                expected_reward REAL DEFAULT 0.5,
                dependency_satisfaction REAL DEFAULT 0.5,
                attention_score REAL DEFAULT 0.0,
                progress_momentum REAL DEFAULT 0.0,
                composite_score REAL DEFAULT 0.0,
                rank INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS goal_competition_results (
                id TEXT PRIMARY KEY,
                entries TEXT DEFAULT '[]',
                winner_id TEXT,
                total_goals_competed INTEGER DEFAULT 0,
                competition_time_ms REAL DEFAULT 0.0,
                factor_weights TEXT DEFAULT '{}',
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_gce_goal
                ON goal_competition_entries(goal_id);
            CREATE INDEX IF NOT EXISTS idx_gce_rank
                ON goal_competition_entries(rank);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        """Load existing competition entries from SQLite."""
        conn = self._storage._conn
        if conn is None:
            return

        # Load entries
        cursor = await conn.execute("SELECT * FROM goal_competition_entries")
        rows = await cursor.fetchall()
        for row in rows:
            entry = GoalCompetitionEntry(
                id=row["id"],
                goal_id=row["goal_id"],
                goal_description=row["goal_description"],
                importance=row["importance"],
                urgency=row["urgency"],
                uncertainty=row["uncertainty"],
                expected_reward=row["expected_reward"],
                dependency_satisfaction=row["dependency_satisfaction"],
                attention_score=row["attention_score"],
                progress_momentum=row["progress_momentum"],
                composite_score=row["composite_score"],
                rank=row["rank"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            self._entries[entry.id] = entry

        # Load recent competition results (keep last 100 in memory)
        cursor = await conn.execute(
            "SELECT * FROM goal_competition_results ORDER BY timestamp DESC LIMIT 100"
        )
        rows = await cursor.fetchall()
        for row in rows:
            result = CompetitionResult(
                id=row["id"],
                entries=[GoalCompetitionEntry(**e) for e in json.loads(row["entries"])],
                winner_id=row["winner_id"],
                total_goals_competed=row["total_goals_competed"],
                competition_time_ms=row["competition_time_ms"],
                factor_weights=json.loads(row["factor_weights"]) if row["factor_weights"] else {},
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )
            self._competition_history.append(result)

    # ─── Persistence helpers ───────────────────────────────────────────────

    async def _save_entry(self, entry: GoalCompetitionEntry) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO goal_competition_entries
               (id, goal_id, goal_description, importance, urgency, uncertainty,
                expected_reward, dependency_satisfaction, attention_score,
                progress_momentum, composite_score, rank, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.id,
                entry.goal_id,
                entry.goal_description,
                entry.importance,
                entry.urgency,
                entry.uncertainty,
                entry.expected_reward,
                entry.dependency_satisfaction,
                entry.attention_score,
                entry.progress_momentum,
                entry.composite_score,
                entry.rank,
                json.dumps(entry.metadata),
                entry.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_competition_result(self, result: CompetitionResult) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO goal_competition_results
               (id, entries, winner_id, total_goals_competed,
                competition_time_ms, factor_weights, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                result.id,
                json.dumps([e.model_dump(mode="json") for e in result.entries]),
                result.winner_id,
                result.total_goals_competed,
                result.competition_time_ms,
                json.dumps(result.factor_weights),
                result.timestamp.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Core API ──────────────────────────────────────────────────────────

    async def enter_competition(
        self,
        goal: Any = None,
        goal_id: str = "",
        goal_description: str = "",
        importance: float = 0.5,
        urgency: float = 0.5,
        uncertainty: float = 0.5,
        expected_reward: float = 0.5,
        dependency_satisfaction: float = 0.5,
        attention_score: float = 0.0,
        progress_momentum: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> GoalCompetitionEntry:
        """Enter a goal into the competition pool.

        If a Goal object is provided (from v2_models), its attributes are
        automatically extracted and used as defaults. Explicit parameters
        override the extracted values.

        Args:
            goal: A Goal model (v2_models.Goal or compatible). Optional.
            goal_id: ID of the goal (required if goal not provided).
            goal_description: Human-readable description.
            importance: How important this goal is [0, 1].
            urgency: How urgent this goal is [0, 1].
            uncertainty: How uncertain we are about this goal [0, 1].
            expected_reward: Expected reward upon completion [0, 1].
            dependency_satisfaction: How satisfied the goal's dependencies are [0, 1].
            attention_score: Current attention allocation [0, 1].
            progress_momentum: How much recent progress the goal has made [0, 1].
            metadata: Optional extra metadata.

        Returns:
            A GoalCompetitionEntry with computed composite_score.
        """
        # Extract from Goal object if provided
        if goal is not None:
            if not goal_id:
                goal_id = getattr(goal, "id", "")
            if not goal_description:
                goal_description = getattr(goal, "description", "")

            # Derive importance from priority if not explicitly set
            priority = getattr(goal, "priority", 5)
            if isinstance(priority, int):
                importance = max(importance, min(1.0, priority / 15.0))

            # Derive urgency from status and progress
            progress = getattr(goal, "progress", 0.0)
            status = getattr(goal, "status", None)
            status_str = status.value if status else "active"
            if status_str == "active" and progress < 0.3:
                urgency = max(urgency, 0.5 + (1.0 - progress) * 0.3)

            # Derive uncertainty from progress
            uncertainty = max(uncertainty, (1.0 - progress) * 0.4)

            # Derive dependency_satisfaction from dependency status
            dependency_ids = getattr(goal, "dependency_ids", [])
            if not dependency_ids:
                dependency_satisfaction = 1.0

            # Progress momentum from current progress
            if progress > 0.0:
                progress_momentum = max(progress_momentum, progress * 0.3)

        # Check for existing entry for this goal
        existing = self._find_entry_by_goal_id(goal_id)
        if existing is not None:
            # Update the existing entry
            existing.importance = importance
            existing.urgency = urgency
            existing.uncertainty = uncertainty
            existing.expected_reward = expected_reward
            existing.dependency_satisfaction = dependency_satisfaction
            existing.attention_score = attention_score
            existing.progress_momentum = progress_momentum
            existing.goal_description = goal_description
            if metadata:
                existing.metadata.update(metadata)
            existing.composite_score = self._compute_composite_score(existing)
            await self._save_entry(existing)
            return existing

        entry = GoalCompetitionEntry(
            goal_id=goal_id,
            goal_description=goal_description,
            importance=importance,
            urgency=urgency,
            uncertainty=uncertainty,
            expected_reward=expected_reward,
            dependency_satisfaction=dependency_satisfaction,
            attention_score=attention_score,
            progress_momentum=progress_momentum,
            metadata=metadata or {},
        )
        entry.composite_score = self._compute_composite_score(entry)
        self._entries[entry.id] = entry
        await self._save_entry(entry)
        return entry

    async def run_competition(
        self, goal_ids: list[str] | None = None
    ) -> CompetitionResult:
        """Run a competition round and rank all competing goals.

        The competition:
        1. Selects the goals to compete (all or specified subset).
        2. Applies urgency escalation for blocked goals.
        3. Adjusts expected_reward based on uncertainty.
        4. Recomputes composite scores with current factor weights.
        5. Ranks goals by composite score (descending).
        6. Determines the winner.

        Key behaviors:
        - Urgency increases over time for blocked goals (deadlines approaching)
        - Uncertainty boosts attention needs but reduces expected reward
        - Dependency satisfaction: goals whose dependencies are met score higher
        - Progress momentum: goals making recent progress get a boost

        Args:
            goal_ids: Optional list of goal IDs to include. If None, all
                      competing goals are included.

        Returns:
            A CompetitionResult with ranked entries and a winner.
        """
        start_time = time_mod.monotonic()

        # Select competing entries
        if goal_ids is not None:
            competing = [
                e for e in self._entries.values() if e.goal_id in goal_ids
            ]
        else:
            competing = list(self._entries.values())

        if not competing:
            result = CompetitionResult(
                entries=[],
                winner_id=None,
                total_goals_competed=0,
                competition_time_ms=0.0,
                factor_weights=dict(self._factor_weights),
            )
            self._competition_history.append(result)
            await self._save_competition_result(result)
            return result

        # ── Apply dynamic adjustments ────────────────────────────────────
        now = utc_now()
        for entry in competing:
            # Urgency escalation: goals blocked (low dependency_satisfaction)
            # gain urgency over time
            if entry.dependency_satisfaction < 0.5:
                created_at = entry.created_at
                elapsed_minutes = max(0.0, (now - created_at).total_seconds() / 60.0)
                urgency_boost = URGENCY_ESCALATION_PER_MINUTE * elapsed_minutes
                entry.urgency = min(1.0, entry.urgency + urgency_boost)

            # Uncertainty reduces expected reward
            uncertainty_penalty = entry.uncertainty * 0.3
            effective_reward = max(0.0, entry.expected_reward - uncertainty_penalty)
            entry.expected_reward = effective_reward

            # Progress momentum: apply exponential decay to momentum
            # (momentum fades if not refreshed)
            created_at = entry.created_at
            elapsed_seconds = max(0.0, (now - created_at).total_seconds())
            entry.progress_momentum *= math.exp(-MOMENTUM_DECAY_RATE * elapsed_seconds)

            # Recompute composite score
            entry.composite_score = self._compute_composite_score(entry)

        # ── Rank entries ─────────────────────────────────────────────────
        competing.sort(key=lambda e: e.composite_score, reverse=True)
        for i, entry in enumerate(competing):
            entry.rank = i + 1
            await self._save_entry(entry)

        # ── Determine winner ─────────────────────────────────────────────
        winner_id = competing[0].goal_id if competing else None

        elapsed_ms = (time_mod.monotonic() - start_time) * 1000.0

        result = CompetitionResult(
            entries=competing,
            winner_id=winner_id,
            total_goals_competed=len(competing),
            competition_time_ms=elapsed_ms,
            factor_weights=dict(self._factor_weights),
        )
        self._competition_history.append(result)
        await self._save_competition_result(result)
        return result

    def get_current_ranking(self) -> list[GoalCompetitionEntry]:
        """Get the current ranking of competing goals.

        Returns entries sorted by composite_score (descending).
        If no competition has been run yet, computes scores on the fly.
        """
        entries = list(self._entries.values())
        # Recompute scores in case weights changed
        for entry in entries:
            entry.composite_score = self._compute_composite_score(entry)
        entries.sort(key=lambda e: e.composite_score, reverse=True)
        return entries

    def update_factor_weights(self, new_weights: dict[str, float]) -> dict[str, float]:
        """Adjust competition dynamics by updating factor weights.

        Only the provided weights are updated; others remain unchanged.
        Weights are normalised to sum to 1.0 after the update.

        Args:
            new_weights: Dict mapping factor name → new weight.

        Returns:
            The updated full weight dict (normalised).
        """
        for key, value in new_weights.items():
            if key in self._factor_weights:
                self._factor_weights[key] = max(0.0, float(value))

        # Normalise so weights sum to 1.0
        total = sum(self._factor_weights.values())
        if total > 0:
            self._factor_weights = {
                k: v / total for k, v in self._factor_weights.items()
            }

        return dict(self._factor_weights)

    def get_winner(self) -> GoalCompetitionEntry | None:
        """Get the current winning goal (highest composite score).

        Returns:
            The GoalCompetitionEntry with the highest score, or None if empty.
        """
        if not self._entries:
            return None
        ranking = self.get_current_ranking()
        return ranking[0] if ranking else None

    async def get_stats(self) -> dict[str, Any]:
        """Get competition engine statistics."""
        total_entries = len(self._entries)
        total_competitions = len(self._competition_history)

        avg_composite = 0.0
        if total_entries > 0:
            avg_composite = sum(e.composite_score for e in self._entries.values()) / total_entries

        # Most recent competition result
        last_result = self._competition_history[-1] if self._competition_history else None

        # Factor distribution
        factor_averages: dict[str, float] = {}
        if total_entries > 0:
            for factor_key in DEFAULT_WEIGHTS:
                vals = [getattr(e, factor_key, 0.0) for e in self._entries.values()]
                factor_averages[factor_key] = round(sum(vals) / total_entries, 4)

        return {
            "total_competing_goals": total_entries,
            "total_competitions_run": total_competitions,
            "average_composite_score": round(avg_composite, 4),
            "current_factor_weights": {k: round(v, 4) for k, v in self._factor_weights.items()},
            "factor_averages": factor_averages,
            "last_winner_id": last_result.winner_id if last_result else None,
            "last_competition_time_ms": last_result.competition_time_ms if last_result else 0.0,
        }

    # ─── Private helpers ──────────────────────────────────────────────────

    def _compute_composite_score(self, entry: GoalCompetitionEntry) -> float:
        """Compute the weighted composite score for a competition entry.

        composite = Σ (factor_value × factor_weight)

        The score is clamped to [0, 1].
        """
        score = 0.0
        score += entry.importance * self._factor_weights.get(CompetitionFactor.IMPORTANCE.value, 0.0)
        score += entry.urgency * self._factor_weights.get(CompetitionFactor.URGENCY.value, 0.0)
        score += entry.uncertainty * self._factor_weights.get(CompetitionFactor.UNCERTAINTY.value, 0.0)
        score += entry.expected_reward * self._factor_weights.get(CompetitionFactor.EXPECTED_REWARD.value, 0.0)
        score += entry.dependency_satisfaction * self._factor_weights.get(CompetitionFactor.DEPENDENCY_SATISFACTION.value, 0.0)
        score += entry.attention_score * self._factor_weights.get(CompetitionFactor.ATTENTION_SCORE.value, 0.0)
        score += entry.progress_momentum * self._factor_weights.get(CompetitionFactor.PROGRESS_MOMENTUM.value, 0.0)
        return max(0.0, min(1.0, score))

    def _find_entry_by_goal_id(self, goal_id: str) -> GoalCompetitionEntry | None:
        """Find an existing competition entry by goal ID."""
        for entry in self._entries.values():
            if entry.goal_id == goal_id:
                return entry
        return None
