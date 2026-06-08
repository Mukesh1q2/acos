"""
Attention Manager — track active concepts, goals, beliefs with focus scores.

Supports:
- Attention focus tracking with configurable decay
- Reinforcement of frequently-accessed elements
- Priority shifts based on goal relevance and query context
- Attention snapshots for reporting

Persistence via shared StorageBackend SQLite connection.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v3_models import (
    AttentionFocus,
    AttentionSnapshot,
    AttentionTargetType,
    gen_id,
    utc_now,
)


class AttentionManager:
    """Attention Manager — track and evolve what the cognitive system is focusing on.

    Usage::

        store = StorageBackend()
        await store.initialize()

        am = AttentionManager(store)
        await am.initialize()

        await am.focus_on("concept-123", AttentionTargetType.CONCEPT, score=0.8)
        await am.reinforce("concept-123")
        snapshot = await am.get_snapshot()
    """

    # Minimum focus score before an element is removed from attention
    MIN_FOCUS_THRESHOLD = 0.01

    # Maximum number of active focus entries
    MAX_FOCUS_ENTRIES = 200

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._focus_map: dict[str, AttentionFocus] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load existing attention state."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS attention_focus (
                id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                focus_score REAL DEFAULT 1.0,
                reinforcement_count INTEGER DEFAULT 0,
                last_reinforced TEXT NOT NULL,
                decay_rate REAL DEFAULT 0.05,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_attention_target
                ON attention_focus(target_id);
            CREATE INDEX IF NOT EXISTS idx_attention_type
                ON attention_focus(target_type);
            CREATE INDEX IF NOT EXISTS idx_attention_score
                ON attention_focus(focus_score);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        assert conn is not None
        cursor = await conn.execute("SELECT * FROM attention_focus")
        rows = await cursor.fetchall()
        for row in rows:
            focus = self._row_to_focus(row)
            self._focus_map[focus.target_id] = focus

    # ─── Row ↔ Model helpers ────────────────────────────────────────────────

    @staticmethod
    def _row_to_focus(row: Any) -> AttentionFocus:
        return AttentionFocus(
            id=row["id"],
            target_id=row["target_id"],
            target_type=AttentionTargetType(row["target_type"]),
            focus_score=row["focus_score"],
            reinforcement_count=row["reinforcement_count"],
            last_reinforced=datetime.fromisoformat(row["last_reinforced"]),
            decay_rate=row["decay_rate"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    async def _save_focus(self, focus: AttentionFocus) -> None:
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            """INSERT OR REPLACE INTO attention_focus
               (id, target_id, target_type, focus_score, reinforcement_count,
                last_reinforced, decay_rate, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                focus.id,
                focus.target_id,
                focus.target_type.value,
                focus.focus_score,
                focus.reinforcement_count,
                focus.last_reinforced.isoformat(),
                focus.decay_rate,
                focus.created_at.isoformat(),
                focus.updated_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _delete_focus(self, target_id: str) -> None:
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            "DELETE FROM attention_focus WHERE target_id = ?", (target_id,)
        )
        await conn.commit()

    # ─── Core API ───────────────────────────────────────────────────────────

    async def focus_on(
        self,
        target_id: str,
        target_type: AttentionTargetType,
        score: float = 1.0,
        decay_rate: float = 0.05,
    ) -> AttentionFocus:
        """Add or update a focus entry for a target.

        If the target is already being tracked, its focus score is updated
        (taking the maximum of current and new score).

        Args:
            target_id: ID of the concept/belief/goal/memory/plan.
            target_type: Type of the target element.
            score: Initial focus score [0, 1].
            decay_rate: How fast focus decays per cycle [0, 1].

        Returns:
            The AttentionFocus entry.
        """
        if target_id in self._focus_map:
            existing = self._focus_map[target_id]
            existing.focus_score = max(existing.focus_score, score)
            existing.reinforcement_count += 1
            existing.last_reinforced = utc_now()
            existing.updated_at = utc_now()
            await self._save_focus(existing)
            return existing

        focus = AttentionFocus(
            target_id=target_id,
            target_type=target_type,
            focus_score=max(0.0, min(1.0, score)),
            decay_rate=decay_rate,
        )
        self._focus_map[target_id] = focus
        await self._save_focus(focus)
        return focus

    async def reinforce(self, target_id: str, boost: float = 0.1) -> AttentionFocus | None:
        """Reinforce a target's focus score.

        Increases focus_score by *boost* (clamped to [0, 1]) and increments
        the reinforcement count.  Also updates last_reinforced timestamp.

        Args:
            target_id: ID of the target to reinforce.
            boost: Amount to add to focus score.

        Returns:
            The updated AttentionFocus, or None if not tracked.
        """
        focus = self._focus_map.get(target_id)
        if focus is None:
            return None

        focus.focus_score = min(1.0, focus.focus_score + boost)
        focus.reinforcement_count += 1
        focus.last_reinforced = utc_now()
        focus.updated_at = utc_now()
        await self._save_focus(focus)
        return focus

    async def decay(self, time_elapsed_seconds: float = 60.0) -> int:
        """Apply exponential decay to all focus entries.

        dF/dt = -decay_rate * F, discretised as:
            F_new = F_old * exp(-decay_rate * time_elapsed)

        Entries below MIN_FOCUS_THRESHOLD are removed.

        Args:
            time_elapsed_seconds: Time since last decay cycle.

        Returns:
            Number of entries removed due to decay.
        """
        removed = 0
        to_remove: list[str] = []

        for target_id, focus in self._focus_map.items():
            # Exponential decay
            decay_factor = math.exp(-focus.decay_rate * (time_elapsed_seconds / 60.0))
            focus.focus_score *= decay_factor
            focus.updated_at = utc_now()

            if focus.focus_score < self.MIN_FOCUS_THRESHOLD:
                to_remove.append(target_id)
            else:
                await self._save_focus(focus)

        for target_id in to_remove:
            del self._focus_map[target_id]
            await self._delete_focus(target_id)
            removed += 1

        return removed

    async def shift_priority(
        self,
        target_id: str,
        new_score: float,
    ) -> AttentionFocus | None:
        """Directly set a new focus score for a target (priority shift).

        Args:
            target_id: ID of the target.
            new_score: New focus score [0, 1].

        Returns:
            The updated AttentionFocus, or None if not tracked.
        """
        focus = self._focus_map.get(target_id)
        if focus is None:
            return None

        focus.focus_score = max(0.0, min(1.0, new_score))
        focus.updated_at = utc_now()
        await self._save_focus(focus)
        return focus

    async def get_focus(self, target_id: str) -> AttentionFocus | None:
        """Get the focus entry for a target."""
        return self._focus_map.get(target_id)

    async def get_top_focuses(self, limit: int = 10) -> list[AttentionFocus]:
        """Get the top focuses sorted by focus score (descending).

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of AttentionFocus entries sorted by score.
        """
        sorted_focuses = sorted(
            self._focus_map.values(),
            key=lambda f: f.focus_score,
            reverse=True,
        )
        return sorted_focuses[:limit]

    async def get_focuses_by_type(
        self, target_type: AttentionTargetType
    ) -> list[AttentionFocus]:
        """Get all focus entries of a given type."""
        return [
            f for f in self._focus_map.values()
            if f.target_type == target_type
        ]

    async def get_snapshot(self) -> AttentionSnapshot:
        """Get a snapshot of the current attention state."""
        concepts = [
            f for f in self._focus_map.values()
            if f.target_type == AttentionTargetType.CONCEPT
        ]
        goals = [
            f for f in self._focus_map.values()
            if f.target_type == AttentionTargetType.GOAL
        ]
        beliefs = [
            f for f in self._focus_map.values()
            if f.target_type == AttentionTargetType.BELIEF
        ]

        total_focus = sum(f.focus_score for f in self._focus_map.values())
        peak = max(self._focus_map.values(), key=lambda f: f.focus_score) if self._focus_map else None

        return AttentionSnapshot(
            active_concepts=concepts,
            active_goals=goals,
            active_beliefs=beliefs,
            total_focus=total_focus,
            peak_focus_target_id=peak.target_id if peak else None,
        )

    async def clear_all(self) -> None:
        """Remove all focus entries."""
        conn = self._storage._conn
        assert conn is not None
        await conn.execute("DELETE FROM attention_focus")
        await conn.commit()
        self._focus_map.clear()

    async def get_stats(self) -> dict[str, Any]:
        """Get attention statistics."""
        if not self._focus_map:
            return {
                "total_entries": 0,
                "total_focus": 0.0,
                "by_type": {},
                "avg_focus": 0.0,
            }

        by_type: dict[str, int] = {}
        for focus in self._focus_map.values():
            key = focus.target_type.value
            by_type[key] = by_type.get(key, 0) + 1

        return {
            "total_entries": len(self._focus_map),
            "total_focus": sum(f.focus_score for f in self._focus_map.values()),
            "by_type": by_type,
            "avg_focus": sum(f.focus_score for f in self._focus_map.values()) / len(self._focus_map),
        }
