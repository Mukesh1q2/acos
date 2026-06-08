"""
Plan State — represent and manage plans with subplans, dependencies, and outcomes.

Supports:
- Plan creation with steps, expected outcomes, and confidence
- Subplan decomposition and dependency tracking
- Outcome tracking (expected vs actual)
- Plan status lifecycle (draft → active → executing → completed/failed)
- Plan revision and alternative generation

Persistence via shared StorageBackend SQLite connection.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v3_models import (
    Plan,
    PlanStep,
    PlanStatus,
    gen_id,
    utc_now,
)


class PlanState:
    """Plan State — manage plans with subplans, dependencies, and outcomes.

    Usage::

        store = StorageBackend()
        await store.initialize()

        ps = PlanState(store)
        await ps.initialize()

        plan = await ps.create_plan(
            name="Implement Feature X",
            description="Step-by-step plan for feature X",
        )
        await ps.add_step(plan.id, "Design the API", order=0)
        await ps.add_step(plan.id, "Write tests", order=1)
    """

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._plans: dict[str, Plan] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load existing plans."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                steps TEXT DEFAULT '[]',
                subplan_ids TEXT DEFAULT '[]',
                parent_plan_id TEXT,
                dependency_ids TEXT DEFAULT '[]',
                expected_outcome TEXT DEFAULT '',
                actual_outcome TEXT DEFAULT '',
                overall_confidence REAL DEFAULT 0.5,
                related_goal_ids TEXT DEFAULT '[]',
                related_belief_ids TEXT DEFAULT '[]',
                related_concept_ids TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status);
            CREATE INDEX IF NOT EXISTS idx_plans_parent ON plans(parent_plan_id);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        assert conn is not None
        cursor = await conn.execute("SELECT * FROM plans")
        rows = await cursor.fetchall()
        for row in rows:
            plan = self._row_to_plan(row)
            self._plans[plan.id] = plan

    # ─── Row ↔ Model helpers ────────────────────────────────────────────────

    @staticmethod
    def _row_to_plan(row: Any) -> Plan:
        steps = []
        for s in json.loads(row["steps"]):
            try:
                steps.append(PlanStep(**s))
            except Exception:
                pass

        return Plan(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            status=PlanStatus(row["status"]),
            steps=steps,
            subplan_ids=json.loads(row["subplan_ids"]) if row["subplan_ids"] else [],
            parent_plan_id=row["parent_plan_id"],
            dependency_ids=json.loads(row["dependency_ids"]) if row["dependency_ids"] else [],
            expected_outcome=row["expected_outcome"] or "",
            actual_outcome=row["actual_outcome"] or "",
            overall_confidence=row["overall_confidence"],
            related_goal_ids=json.loads(row["related_goal_ids"]) if row["related_goal_ids"] else [],
            related_belief_ids=json.loads(row["related_belief_ids"]) if row["related_belief_ids"] else [],
            related_concept_ids=json.loads(row["related_concept_ids"]) if row["related_concept_ids"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )

    async def _save_plan(self, plan: Plan) -> None:
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            """INSERT OR REPLACE INTO plans
               (id, name, description, status, steps, subplan_ids, parent_plan_id,
                dependency_ids, expected_outcome, actual_outcome, overall_confidence,
                related_goal_ids, related_belief_ids, related_concept_ids,
                metadata, created_at, updated_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                plan.id,
                plan.name,
                plan.description,
                plan.status.value,
                json.dumps([s.model_dump(mode="json") for s in plan.steps]),
                json.dumps(plan.subplan_ids),
                plan.parent_plan_id,
                json.dumps(plan.dependency_ids),
                plan.expected_outcome,
                plan.actual_outcome,
                plan.overall_confidence,
                json.dumps(plan.related_goal_ids),
                json.dumps(plan.related_belief_ids),
                json.dumps(plan.related_concept_ids),
                json.dumps(plan.metadata),
                plan.created_at.isoformat(),
                plan.updated_at.isoformat(),
                plan.completed_at.isoformat() if plan.completed_at else None,
            ),
        )
        await conn.commit()

    # ─── Core API ───────────────────────────────────────────────────────────

    async def create_plan(
        self,
        name: str,
        description: str = "",
        expected_outcome: str = "",
        related_goal_ids: list[str] | None = None,
        related_belief_ids: list[str] | None = None,
        parent_plan_id: str | None = None,
        dependency_ids: list[str] | None = None,
    ) -> Plan:
        """Create a new plan.

        Args:
            name: Plan name.
            description: Detailed description.
            expected_outcome: What the plan should achieve.
            related_goal_ids: IDs of goals this plan addresses.
            related_belief_ids: IDs of beliefs relevant to this plan.
            parent_plan_id: Optional parent plan for subplan hierarchies.
            dependency_ids: IDs of plans that must complete before this one.

        Returns:
            The newly created Plan.
        """
        plan = Plan(
            name=name,
            description=description,
            expected_outcome=expected_outcome,
            related_goal_ids=related_goal_ids or [],
            related_belief_ids=related_belief_ids or [],
            parent_plan_id=parent_plan_id,
            dependency_ids=dependency_ids or [],
        )

        # Register as subplan of parent
        if parent_plan_id and parent_plan_id in self._plans:
            parent = self._plans[parent_plan_id]
            if plan.id not in parent.subplan_ids:
                parent.subplan_ids.append(plan.id)
                parent.updated_at = utc_now()
                await self._save_plan(parent)

        self._plans[plan.id] = plan
        await self._save_plan(plan)
        return plan

    async def add_step(
        self,
        plan_id: str,
        description: str,
        order: int | None = None,
        expected_outcome: str = "",
        confidence: float = 0.7,
    ) -> PlanStep | None:
        """Add a step to a plan.

        Args:
            plan_id: ID of the plan.
            description: Step description.
            order: Step order (appended if None).
            expected_outcome: What this step should produce.
            confidence: Confidence in this step's success.

        Returns:
            The created PlanStep, or None if plan not found.
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        if order is None:
            order = len(plan.steps)

        step = PlanStep(
            description=description,
            order=order,
            expected_outcome=expected_outcome,
            confidence=confidence,
        )
        plan.steps.append(step)
        plan.steps.sort(key=lambda s: s.order)
        plan.updated_at = utc_now()
        await self._save_plan(plan)
        return step

    async def update_step(
        self,
        plan_id: str,
        step_id: str,
        actual_outcome: str | None = None,
        status: PlanStatus | None = None,
    ) -> Plan | None:
        """Update a step within a plan.

        Args:
            plan_id: ID of the plan.
            step_id: ID of the step.
            actual_outcome: Actual outcome of the step.
            status: New status for the step.

        Returns:
            The updated Plan, or None if not found.
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        for step in plan.steps:
            if step.id == step_id:
                if actual_outcome is not None:
                    step.actual_outcome = actual_outcome
                if status is not None:
                    step.status = status
                step.updated_at = utc_now()
                break

        plan.updated_at = utc_now()
        await self._save_plan(plan)
        return plan

    async def activate_plan(self, plan_id: str) -> Plan | None:
        """Move a plan from DRAFT to ACTIVE."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return None
        plan.status = PlanStatus.ACTIVE
        plan.updated_at = utc_now()
        await self._save_plan(plan)
        return plan

    async def start_execution(self, plan_id: str) -> Plan | None:
        """Move a plan from ACTIVE to EXECUTING."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return None
        plan.status = PlanStatus.EXECUTING
        plan.updated_at = utc_now()
        await self._save_plan(plan)
        return plan

    async def complete_plan(
        self, plan_id: str, actual_outcome: str = ""
    ) -> Plan | None:
        """Mark a plan as completed with its actual outcome."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        plan.status = PlanStatus.COMPLETED
        plan.actual_outcome = actual_outcome
        plan.completed_at = utc_now()
        plan.updated_at = utc_now()
        await self._save_plan(plan)
        return plan

    async def fail_plan(
        self, plan_id: str, reason: str = ""
    ) -> Plan | None:
        """Mark a plan as failed."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        plan.status = PlanStatus.FAILED
        plan.actual_outcome = f"FAILED: {reason}"
        plan.updated_at = utc_now()
        await self._save_plan(plan)
        return plan

    async def revise_plan(
        self, plan_id: str, new_name: str | None = None,
        new_description: str | None = None,
        new_expected_outcome: str | None = None,
    ) -> Plan | None:
        """Revise a plan (creates a revision with REVISED status).

        Args:
            plan_id: ID of the plan to revise.
            new_name: Optional new name.
            new_description: Optional new description.
            new_expected_outcome: Optional new expected outcome.

        Returns:
            The revised Plan, or None if not found.
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        if new_name:
            plan.name = new_name
        if new_description:
            plan.description = new_description
        if new_expected_outcome:
            plan.expected_outcome = new_expected_outcome

        plan.status = PlanStatus.REVISED
        plan.updated_at = utc_now()
        await self._save_plan(plan)
        return plan

    async def get_plan(self, plan_id: str) -> Plan | None:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    async def get_active_plans(self) -> list[Plan]:
        """Get all active/executing plans."""
        return [
            p for p in self._plans.values()
            if p.status in (PlanStatus.ACTIVE, PlanStatus.EXECUTING)
        ]

    async def get_plans_for_goal(self, goal_id: str) -> list[Plan]:
        """Get all plans related to a goal."""
        return [
            p for p in self._plans.values()
            if goal_id in p.related_goal_ids
        ]

    async def get_subplans(self, plan_id: str) -> list[Plan]:
        """Get all subplans of a plan."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return []

        subplans: list[Plan] = []
        for sub_id in plan.subplan_ids:
            sub = self._plans.get(sub_id)
            if sub is not None:
                subplans.append(sub)
        return subplans

    async def evaluate_outcome(self, plan_id: str) -> dict[str, Any]:
        """Evaluate a plan's outcome: expected vs actual.

        Args:
            plan_id: ID of the plan.

        Returns:
            Dict with evaluation metrics.
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            return {"error": "Plan not found"}

        completed_steps = [s for s in plan.steps if s.status == PlanStatus.COMPLETED]
        failed_steps = [s for s in plan.steps if s.status == PlanStatus.FAILED]
        total_steps = len(plan.steps)

        step_completion_rate = len(completed_steps) / max(total_steps, 1)

        # Outcome alignment: simple text similarity heuristic
        outcome_alignment = 0.0
        if plan.expected_outcome and plan.actual_outcome:
            expected_terms = set(plan.expected_outcome.lower().split())
            actual_terms = set(plan.actual_outcome.lower().split())
            overlap = expected_terms & actual_terms
            outcome_alignment = len(overlap) / max(len(expected_terms), 1)

        return {
            "plan_id": plan_id,
            "status": plan.status.value,
            "total_steps": total_steps,
            "completed_steps": len(completed_steps),
            "failed_steps": len(failed_steps),
            "step_completion_rate": round(step_completion_rate, 4),
            "outcome_alignment": round(outcome_alignment, 4),
            "overall_confidence": plan.overall_confidence,
            "expected_outcome": plan.expected_outcome,
            "actual_outcome": plan.actual_outcome,
        }

    async def get_stats(self) -> dict[str, Any]:
        """Get plan statistics."""
        by_status: dict[str, int] = {}
        for plan in self._plans.values():
            key = plan.status.value
            by_status[key] = by_status.get(key, 0) + 1

        active = [p for p in self._plans.values() if p.status in (PlanStatus.ACTIVE, PlanStatus.EXECUTING)]
        avg_confidence = (
            sum(p.overall_confidence for p in active) / len(active) if active else 0.0
        )

        return {
            "total_plans": len(self._plans),
            "by_status": by_status,
            "active_count": len(active),
            "avg_confidence": round(avg_confidence, 4),
        }
