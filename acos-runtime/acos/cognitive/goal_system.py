"""
Goal System — manages goals with priorities, dependencies, and progress.

Part of the ACOS Runtime v0.2 Cognitive Architecture.  This module provides the
``GoalManager`` class for creating, decomposing, tracking, and completing goals
that drive the cognitive system's purposive behaviour.

Key concepts
------------
* **Goal** – an objective the system is pursuing, with a priority, progress
  tracker, and optional dependency chain.
* **Dependencies** – a goal may depend on one or more other goals being
  completed before it becomes actionable.
* **Subgoals** – a goal can be decomposed into child subgoals, forming a
  tree structure.
* **Progress** – a float in [0, 1] tracking how close the goal is to
  completion.

Persistence
-----------
All goals are stored in a SQLite table (``goals``) managed through
:class:`~acos.memory.store.StorageBackend`.  List and dict fields are
serialised as JSON strings.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from acos.schemas.v2_models import (
    Goal,
    GoalPriority,
    GoalStatus,
    gen_id,
    utc_now,
)
from acos.memory.store import StorageBackend


class GoalManager:
    """Goal Manager — manages goals with priorities, dependencies, and progress.

    Usage::

        store = StorageBackend()
        await store.initialize()

        gm = GoalManager(store)
        await gm.initialize()

        goal = await gm.create_goal(
            description="Build the belief system",
            priority=GoalPriority.HIGH,
        )
        await gm.update_progress(goal.id, 0.5)
    """

    def __init__(self, store: StorageBackend) -> None:
        self._store = store

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create the ``goals`` table and indexes if they do not exist."""
        assert self._store._conn is not None, "StorageBackend must be initialized first"
        await self._store._conn.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                priority INTEGER DEFAULT 5,
                progress REAL DEFAULT 0.0,
                parent_goal_id TEXT,
                subgoal_ids TEXT DEFAULT '[]',
                dependency_ids TEXT DEFAULT '[]',
                related_concept_ids TEXT DEFAULT '[]',
                related_belief_ids TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
            CREATE INDEX IF NOT EXISTS idx_goals_parent ON goals(parent_goal_id);
        """)
        await self._store._conn.commit()

    # ─── Persistence helpers ────────────────────────────────────────────────

    async def _save_goal(self, goal: Goal) -> None:
        """Insert or replace a goal row in SQLite."""
        assert self._store._conn is not None
        await self._store._conn.execute(
            """INSERT OR REPLACE INTO goals
               (id, description, status, priority, progress, parent_goal_id,
                subgoal_ids, dependency_ids, related_concept_ids,
                related_belief_ids, metadata, created_at, updated_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                goal.id,
                goal.description,
                goal.status.value,
                int(goal.priority),
                goal.progress,
                goal.parent_goal_id,
                json.dumps(goal.subgoal_ids),
                json.dumps(goal.dependency_ids),
                json.dumps(goal.related_concept_ids),
                json.dumps(goal.related_belief_ids),
                json.dumps(goal.metadata),
                goal.created_at.isoformat(),
                goal.updated_at.isoformat(),
                goal.completed_at.isoformat() if goal.completed_at else None,
            ),
        )
        await self._store._conn.commit()

    def _row_to_goal(self, row: aiosqlite.Row) -> Goal:
        """Convert a SQLite row to a Goal Pydantic model."""
        return Goal(
            id=row["id"],
            description=row["description"],
            status=GoalStatus(row["status"]),
            priority=GoalPriority(row["priority"]),
            progress=row["progress"],
            parent_goal_id=row["parent_goal_id"],
            subgoal_ids=json.loads(row["subgoal_ids"]),
            dependency_ids=json.loads(row["dependency_ids"]),
            related_concept_ids=json.loads(row["related_concept_ids"]),
            related_belief_ids=json.loads(row["related_belief_ids"]),
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )

    async def _fetch_goal(self, goal_id: str) -> Goal | None:
        """Retrieve a single goal by ID from SQLite."""
        assert self._store._conn is not None
        cursor = await self._store._conn.execute(
            "SELECT * FROM goals WHERE id = ?", (goal_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_goal(row)

    # ─── Core API ───────────────────────────────────────────────────────────

    async def create_goal(
        self,
        description: str,
        priority: GoalPriority = GoalPriority.NORMAL,
        parent_goal_id: str | None = None,
        dependency_ids: list[str] | None = None,
        related_concept_ids: list[str] | None = None,
    ) -> Goal:
        """Create a new Goal.

        If *parent_goal_id* is provided, the new goal is registered as a
        subgoal of the parent (the parent's ``subgoal_ids`` is updated).

        If *dependency_ids* contains IDs that do not exist, those entries
        are silently ignored.

        Parameters
        ----------
        description:
            Human-readable goal description.
        priority:
            Goal priority (default: NORMAL / 5).
        parent_goal_id:
            Optional parent goal for decomposition.
        dependency_ids:
            IDs of goals that must be completed before this one.
        related_concept_ids:
            IDs of related knowledge-graph concepts.

        Returns
        -------
        Goal
            The newly created Goal object.

        Raises
        ------
        ValueError
            If *parent_goal_id* refers to a non-existent goal.
        """
        dependency_ids = dependency_ids or []
        related_concept_ids = related_concept_ids or []

        # Validate dependency IDs exist
        valid_deps: list[str] = []
        for dep_id in dependency_ids:
            dep = await self._fetch_goal(dep_id)
            if dep is not None:
                valid_deps.append(dep_id)

        # Validate parent exists
        if parent_goal_id is not None:
            parent = await self._fetch_goal(parent_goal_id)
            if parent is None:
                raise ValueError(f"Parent goal {parent_goal_id} not found")

        goal = Goal(
            description=description,
            priority=priority,
            parent_goal_id=parent_goal_id,
            dependency_ids=valid_deps,
            related_concept_ids=related_concept_ids,
        )
        await self._save_goal(goal)

        # Update parent's subgoal list
        if parent_goal_id is not None:
            parent = await self._fetch_goal(parent_goal_id)
            if parent is not None:
                if goal.id not in parent.subgoal_ids:
                    parent.subgoal_ids.append(goal.id)
                    parent.updated_at = utc_now()
                    await self._save_goal(parent)

        return goal

    async def update_progress(self, goal_id: str, progress: float) -> Goal:
        """Update goal progress.

        Progress is clamped to [0, 1].  If progress reaches 1.0 the goal
        is automatically marked as COMPLETED.

        Parameters
        ----------
        goal_id:
            ID of the goal to update.
        progress:
            New progress value in [0, 1].

        Returns
        -------
        Goal
            The updated goal.

        Raises
        ------
        ValueError
            If the goal does not exist.
        """
        goal = await self._fetch_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")

        goal.progress = max(0.0, min(1.0, progress))
        goal.updated_at = utc_now()

        if goal.progress >= 1.0:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = utc_now()

        await self._save_goal(goal)
        return goal

    async def complete_goal(self, goal_id: str) -> Goal:
        """Mark a goal as completed (progress = 1.0, status = COMPLETED).

        After completion, any goals that depend on this one are checked to
        see if they now have all dependencies met (no status change — use
        :meth:`get_next_actionable_goals` to discover them).

        Parameters
        ----------
        goal_id:
            ID of the goal to complete.

        Returns
        -------
        Goal
            The completed goal.

        Raises
        ------
        ValueError
            If the goal does not exist.
        """
        goal = await self._fetch_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")

        goal.progress = 1.0
        goal.status = GoalStatus.COMPLETED
        goal.completed_at = utc_now()
        goal.updated_at = utc_now()
        await self._save_goal(goal)
        return goal

    async def abandon_goal(self, goal_id: str, reason: str = "") -> Goal:
        """Mark a goal as ABANDONED.

        All subgoals that are still ACTIVE or PAUSED are also abandoned
        recursively.

        Parameters
        ----------
        goal_id:
            ID of the goal to abandon.
        reason:
            Optional reason for abandoning (stored in metadata).

        Returns
        -------
        Goal
            The abandoned goal.

        Raises
        ------
        ValueError
            If the goal does not exist.
        """
        goal = await self._fetch_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")

        goal.status = GoalStatus.ABANDONED
        if reason:
            goal.metadata["abandon_reason"] = reason
        goal.updated_at = utc_now()
        await self._save_goal(goal)

        # Recursively abandon subgoals
        for sub_id in goal.subgoal_ids:
            sub = await self._fetch_goal(sub_id)
            if sub is not None and sub.status in (GoalStatus.ACTIVE, GoalStatus.PAUSED):
                await self.abandon_goal(sub_id, reason=f"Parent goal {goal_id} abandoned")

        return goal

    async def pause_goal(self, goal_id: str) -> Goal:
        """Pause an active goal (status → PAUSED).

        Parameters
        ----------
        goal_id:
            ID of the goal to pause.

        Returns
        -------
        Goal
            The paused goal.

        Raises
        ------
        ValueError
            If the goal does not exist or is not ACTIVE.
        """
        goal = await self._fetch_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")
        if goal.status != GoalStatus.ACTIVE:
            raise ValueError(f"Goal {goal_id} is not ACTIVE (current: {goal.status.value})")

        goal.status = GoalStatus.PAUSED
        goal.updated_at = utc_now()
        await self._save_goal(goal)
        return goal

    async def resume_goal(self, goal_id: str) -> Goal:
        """Resume a paused goal (status → ACTIVE).

        Parameters
        ----------
        goal_id:
            ID of the goal to resume.

        Returns
        -------
        Goal
            The resumed goal.

        Raises
        ------
        ValueError
            If the goal does not exist or is not PAUSED.
        """
        goal = await self._fetch_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")
        if goal.status != GoalStatus.PAUSED:
            raise ValueError(f"Goal {goal_id} is not PAUSED (current: {goal.status.value})")

        goal.status = GoalStatus.ACTIVE
        goal.updated_at = utc_now()
        await self._save_goal(goal)
        return goal

    async def get_active_goals(self) -> list[Goal]:
        """Return all active goals sorted by priority (highest first).

        Returns
        -------
        list[Goal]
            Active goals in descending priority order.
        """
        assert self._store._conn is not None
        cursor = await self._store._conn.execute(
            "SELECT * FROM goals WHERE status = ? ORDER BY priority DESC, created_at ASC",
            (GoalStatus.ACTIVE.value,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_goal(r) for r in rows]

    async def get_goal(self, goal_id: str) -> Goal | None:
        """Retrieve a single goal by ID.

        Returns ``None`` if the goal does not exist.
        """
        return await self._fetch_goal(goal_id)

    async def get_subgoals(self, goal_id: str) -> list[Goal]:
        """Return all direct subgoals of a goal.

        Parameters
        ----------
        goal_id:
            ID of the parent goal.

        Returns
        -------
        list[Goal]
            Direct subgoals, ordered by priority (highest first).

        Raises
        ------
        ValueError
            If the parent goal does not exist.
        """
        goal = await self._fetch_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")

        subgoals: list[Goal] = []
        for sub_id in goal.subgoal_ids:
            sub = await self._fetch_goal(sub_id)
            if sub is not None:
                subgoals.append(sub)

        subgoals.sort(key=lambda g: g.priority, reverse=True)
        return subgoals

    async def get_dependency_chain(self, goal_id: str) -> list[Goal]:
        """Return the full transitive dependency chain for a goal.

        Traverses ``dependency_ids`` recursively, collecting all ancestor
        dependencies.  Circular references are detected and broken safely.

        Parameters
        ----------
        goal_id:
            ID of the goal whose dependencies to trace.

        Returns
        -------
        list[Goal]
            All transitive dependencies (order: immediate first).

        Raises
        ------
        ValueError
            If the goal does not exist.
        """
        goal = await self._fetch_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")

        visited: set[str] = set()
        result: list[Goal] = []

        async def _walk(gid: str) -> None:
            if gid in visited:
                return  # break circular references
            visited.add(gid)
            g = await self._fetch_goal(gid)
            if g is None:
                return
            for dep_id in g.dependency_ids:
                if dep_id not in visited:
                    dep = await self._fetch_goal(dep_id)
                    if dep is not None:
                        result.append(dep)
                    await _walk(dep_id)

        await _walk(goal_id)
        return result

    async def check_dependencies_met(self, goal_id: str) -> bool:
        """Check whether all dependencies of a goal are COMPLETED.

        Parameters
        ----------
        goal_id:
            ID of the goal to check.

        Returns
        -------
        bool
            ``True`` if all direct dependencies are COMPLETED (or if there
            are no dependencies), ``False`` otherwise.

        Raises
        ------
        ValueError
            If the goal does not exist.
        """
        goal = await self._fetch_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")

        if not goal.dependency_ids:
            return True

        for dep_id in goal.dependency_ids:
            dep = await self._fetch_goal(dep_id)
            if dep is None or dep.status != GoalStatus.COMPLETED:
                return False
        return True

    async def get_next_actionable_goals(self) -> list[Goal]:
        """Return goals that are ACTIVE and have all dependencies met.

        Sorted by priority (highest first), then by creation time (oldest
        first).

        Returns
        -------
        list[Goal]
            Actionable goals ready for work.
        """
        active = await self.get_active_goals()
        actionable: list[Goal] = []
        for goal in active:
            deps_met = await self.check_dependencies_met(goal.id)
            if deps_met:
                actionable.append(goal)
        return actionable

    async def decompose_goal(
        self, goal_id: str, subgoal_descriptions: list[str]
    ) -> list[Goal]:
        """Decompose a goal into subgoals.

        Creates a new Goal for each description in *subgoal_descriptions*,
        sets the parent goal, and registers each as a subgoal.  Each
        subgoal depends on the previous one being completed (sequential
        decomposition).

        Parameters
        ----------
        goal_id:
            ID of the parent goal to decompose.
        subgoal_descriptions:
            List of description strings for the new subgoals.

        Returns
        -------
        list[Goal]
            The newly created subgoals.

        Raises
        ------
        ValueError
            If the parent goal does not exist.
        """
        parent = await self._fetch_goal(goal_id)
        if parent is None:
            raise ValueError(f"Goal {goal_id} not found")

        subgoals: list[Goal] = []
        prev_subgoal_id: str | None = None

        for desc in subgoal_descriptions:
            # Each subgoal depends on the previous one (sequential)
            deps = [prev_subgoal_id] if prev_subgoal_id else []
            sub = await self.create_goal(
                description=desc,
                priority=parent.priority,
                parent_goal_id=goal_id,
                dependency_ids=deps,
            )
            subgoals.append(sub)
            prev_subgoal_id = sub.id

        return subgoals

    async def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics about goals.

        Returns
        -------
        dict
            * ``count_by_status`` – dict mapping status name → count
            * ``total`` – total number of goals
            * ``average_progress`` – mean progress of all goals
            * ``active_average_progress`` – mean progress of active goals
            * ``completion_rate`` – fraction of all goals that are COMPLETED
        """
        assert self._store._conn is not None
        cursor = await self._store._conn.execute(
            "SELECT status, COUNT(*) as cnt, AVG(progress) as avg_prog FROM goals GROUP BY status"
        )
        rows = await cursor.fetchall()

        count_by_status: dict[str, int] = {}
        total = 0
        weighted_progress = 0.0
        active_total = 0
        active_weighted_progress = 0.0
        completed_total = 0

        for row in rows:
            status = row["status"]
            cnt = row["cnt"]
            avg_prog = row["avg_prog"]
            count_by_status[status] = cnt
            total += cnt
            weighted_progress += avg_prog * cnt
            if status == GoalStatus.ACTIVE.value:
                active_total = cnt
                active_weighted_progress = avg_prog * cnt
            if status == GoalStatus.COMPLETED.value:
                completed_total = cnt

        avg_progress = weighted_progress / total if total > 0 else 0.0
        active_avg = active_weighted_progress / active_total if active_total > 0 else 0.0
        completion_rate = completed_total / total if total > 0 else 0.0

        return {
            "count_by_status": count_by_status,
            "total": total,
            "average_progress": round(avg_progress, 4),
            "active_average_progress": round(active_avg, 4),
            "completion_rate": round(completion_rate, 4),
        }
