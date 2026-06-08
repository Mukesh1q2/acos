"""
Attention Economy — allocate limited cognitive resources across targets.

Attention flows toward:
- active goals (importance * urgency)
- uncertain beliefs (uncertainty)
- important concepts (importance * activation)
- unresolved contradictions (severity)

Attention decays exponentially over time.  Total budget is finite (default
100.0 units) so allocations compete for limited resources.

Persistence via shared StorageBackend SQLite connection.
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v5_models import (
    AttentionAllocation,
    AttentionBudget,
    EconomyCycleResult,
    gen_id,
    utc_now,
)


class AttentionEconomy:
    """Attention Economy — allocate limited cognitive resources.

    Usage::

        store = StorageBackend()
        await store.initialize()

        economy = AttentionEconomy(store)
        await economy.initialize()

        await economy.allocate("goal-1", "goal", 25.0, reason="Active goal")
        result = await economy.run_economy_cycle(goals=[...], beliefs=[...])
        budget = await economy.get_budget()
    """

    # Minimum allocated amount before an allocation is expired
    DECAY_THRESHOLD = 0.01

    # Default decay rate per allocation
    DEFAULT_DECAY_RATE = 0.05

    # Default total attention budget
    DEFAULT_TOTAL_BUDGET = 100.0

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._allocations: dict[str, AttentionAllocation] = {}
        self._total_budget: float = self.DEFAULT_TOTAL_BUDGET

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load existing economy state."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS attention_allocations (
                id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                allocated_amount REAL NOT NULL DEFAULT 0.0,
                priority_reason TEXT NOT NULL DEFAULT '',
                decay_rate REAL NOT NULL DEFAULT 0.05,
                granted_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_alloc_target
                ON attention_allocations(target_id);
            CREATE INDEX IF NOT EXISTS idx_alloc_type
                ON attention_allocations(target_type);
            CREATE INDEX IF NOT EXISTS idx_alloc_amount
                ON attention_allocations(allocated_amount);

            CREATE TABLE IF NOT EXISTS attention_budget_config (
                id TEXT PRIMARY KEY,
                total_budget REAL NOT NULL DEFAULT 100.0,
                updated_at TEXT NOT NULL
            );
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        assert conn is not None

        # Load allocations
        cursor = await conn.execute("SELECT * FROM attention_allocations")
        rows = await cursor.fetchall()
        for row in rows:
            alloc = self._row_to_allocation(row)
            self._allocations[alloc.target_id] = alloc

        # Load budget config
        cursor = await conn.execute(
            "SELECT total_budget FROM attention_budget_config LIMIT 1"
        )
        budget_row = await cursor.fetchone()
        if budget_row:
            self._total_budget = budget_row["total_budget"]

    # ─── Row ↔ Model helpers ────────────────────────────────────────────────

    @staticmethod
    def _row_to_allocation(row: Any) -> AttentionAllocation:
        return AttentionAllocation(
            id=row["id"],
            target_id=row["target_id"],
            target_type=row["target_type"],
            allocated_amount=row["allocated_amount"],
            priority_reason=row["priority_reason"],
            decay_rate=row["decay_rate"],
            granted_at=datetime.fromisoformat(row["granted_at"]),
        )

    async def _save_allocation(self, alloc: AttentionAllocation) -> None:
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            """INSERT OR REPLACE INTO attention_allocations
               (id, target_id, target_type, allocated_amount,
                priority_reason, decay_rate, granted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                alloc.id,
                alloc.target_id,
                alloc.target_type,
                alloc.allocated_amount,
                alloc.priority_reason,
                alloc.decay_rate,
                alloc.granted_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _delete_allocation(self, target_id: str) -> None:
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            "DELETE FROM attention_allocations WHERE target_id = ?",
            (target_id,),
        )
        await conn.commit()

    async def _save_budget_config(self) -> None:
        conn = self._storage._conn
        assert conn is not None
        # Upsert: always one row
        await conn.execute(
            """INSERT OR REPLACE INTO attention_budget_config
               (id, total_budget, updated_at)
               VALUES (?, ?, ?)""",
            ("budget_config", self._total_budget, utc_now().isoformat()),
        )
        await conn.commit()

    # ─── Helpers ────────────────────────────────────────────────────────────

    def _total_allocated(self) -> float:
        """Sum of all current allocated amounts."""
        return sum(a.allocated_amount for a in self._allocations.values())

    # ─── Core API ───────────────────────────────────────────────────────────

    async def set_total_budget(self, amount: float) -> None:
        """Set the total attention budget.

        Args:
            amount: New total budget (must be >= 0).
        """
        self._total_budget = max(0.0, amount)
        await self._save_budget_config()

    async def allocate(
        self,
        target_id: str,
        target_type: str,
        amount: float,
        reason: str = "",
    ) -> AttentionAllocation:
        """Allocate attention to a target (no budget check).

        If the target already has an allocation, the amount is added to the
        existing allocation.

        Args:
            target_id: ID of the target element.
            target_type: Type of target (goal, belief, concept, contradiction).
            amount: Amount of attention to allocate.
            reason: Why attention is being allocated.

        Returns:
            The AttentionAllocation entry.
        """
        if target_id in self._allocations:
            existing = self._allocations[target_id]
            existing.allocated_amount += amount
            if reason:
                existing.priority_reason = reason
            existing.granted_at = utc_now()
            await self._save_allocation(existing)
            return existing

        alloc = AttentionAllocation(
            target_id=target_id,
            target_type=target_type,
            allocated_amount=max(0.0, amount),
            priority_reason=reason,
            decay_rate=self.DEFAULT_DECAY_RATE,
        )
        self._allocations[target_id] = alloc
        await self._save_allocation(alloc)
        return alloc

    async def request_attention(
        self,
        target_id: str,
        target_type: str,
        requested_amount: float,
        reason: str = "",
    ) -> AttentionAllocation:
        """Request attention with budget check.

        Only grants the request if there is sufficient available budget.
        If budget is insufficient, a proportional amount is granted.

        Args:
            target_id: ID of the target element.
            target_type: Type of target.
            requested_amount: Desired amount of attention.
            reason: Why attention is being requested.

        Returns:
            The AttentionAllocation entry (may be partially granted).
        """
        available = self._total_budget - self._total_allocated()
        # If already allocated to this target, reclaim its current amount
        current_for_target = 0.0
        if target_id in self._allocations:
            current_for_target = self._allocations[target_id].allocated_amount

        effective_available = available + current_for_target
        granted = min(requested_amount, max(0.0, effective_available))

        if target_id in self._allocations:
            existing = self._allocations[target_id]
            existing.allocated_amount = granted
            if reason:
                existing.priority_reason = reason
            existing.granted_at = utc_now()
            await self._save_allocation(existing)
            return existing

        alloc = AttentionAllocation(
            target_id=target_id,
            target_type=target_type,
            allocated_amount=max(0.0, granted),
            priority_reason=reason,
            decay_rate=self.DEFAULT_DECAY_RATE,
        )
        self._allocations[target_id] = alloc
        await self._save_allocation(alloc)
        return alloc

    async def reallocate(
        self,
        from_target_id: str,
        to_target_id: str,
        amount: float,
    ) -> bool:
        """Move attention from one target to another.

        Args:
            from_target_id: Source target to take attention from.
            to_target_id: Destination target to give attention to.
            amount: How much to move.

        Returns:
            True if reallocation succeeded, False otherwise.
        """
        from_alloc = self._allocations.get(from_target_id)
        if from_alloc is None:
            return False

        actual_amount = min(amount, from_alloc.allocated_amount)
        if actual_amount <= 0:
            return False

        # Deduct from source
        from_alloc.allocated_amount -= actual_amount
        from_alloc.granted_at = utc_now()
        if from_alloc.allocated_amount < self.DECAY_THRESHOLD:
            del self._allocations[from_target_id]
            await self._delete_allocation(from_target_id)
        else:
            await self._save_allocation(from_alloc)

        # Add to destination
        to_alloc = self._allocations.get(to_target_id)
        if to_alloc is not None:
            to_alloc.allocated_amount += actual_amount
            to_alloc.granted_at = utc_now()
            await self._save_allocation(to_alloc)
        else:
            # Need target_type for new allocation — inherit from source
            new_alloc = AttentionAllocation(
                target_id=to_target_id,
                target_type=from_alloc.target_type,
                allocated_amount=actual_amount,
                priority_reason=f"Reallocated from {from_target_id}",
                decay_rate=self.DEFAULT_DECAY_RATE,
            )
            self._allocations[to_target_id] = new_alloc
            await self._save_allocation(new_alloc)

        return True

    async def apply_decay(self, time_elapsed_seconds: float = 60.0) -> float:
        """Apply exponential decay to all allocations.

        Formula: amount *= exp(-decay_rate * time_elapsed / 60.0)

        Entries below DECAY_THRESHOLD are removed.

        Args:
            time_elapsed_seconds: Time since last decay cycle.

        Returns:
            Total amount decayed across all allocations.
        """
        total_decayed = 0.0
        to_remove: list[str] = []

        for target_id, alloc in self._allocations.items():
            before = alloc.allocated_amount
            decay_factor = math.exp(-alloc.decay_rate * (time_elapsed_seconds / 60.0))
            alloc.allocated_amount *= decay_factor
            decayed = before - alloc.allocated_amount
            total_decayed += decayed

            if alloc.allocated_amount < self.DECAY_THRESHOLD:
                to_remove.append(target_id)
            else:
                await self._save_allocation(alloc)

        for target_id in to_remove:
            del self._allocations[target_id]
            await self._delete_allocation(target_id)

        return total_decayed

    async def run_economy_cycle(
        self,
        goals: list[dict[str, Any]] | None = None,
        beliefs: list[dict[str, Any]] | None = None,
        concepts: list[dict[str, Any]] | None = None,
        contradictions: list[dict[str, Any]] | None = None,
    ) -> EconomyCycleResult:
        """Run a complete attention economy cycle.

        Steps:
        1. Apply decay to all existing allocations.
        2. Calculate demand for each target:
           - Active goals: demand = importance * urgency * 2.0
           - Uncertain beliefs: demand = uncertainty * 0.8
           - Important concepts: demand = importance * activation * 0.5
           - Contradictions: demand = severity * 1.5
        3. Allocate within budget constraints (proportional if over budget).
        4. Remove allocations below threshold.

        Each input item should be a dict with at minimum an ``id`` key plus
        the relevant scoring keys (importance, urgency, uncertainty, etc.).

        Args:
            goals: List of goal dicts with keys: id, importance, urgency.
            beliefs: List of belief dicts with keys: id, uncertainty.
            concepts: List of concept dicts with keys: id, importance, activation.
            contradictions: List of contradiction dicts with keys: id, severity.

        Returns:
            EconomyCycleResult summarising the cycle.
        """
        cycle_start = time.monotonic()

        # Step 1: Apply decay
        total_decayed = await self.apply_decay(time_elapsed_seconds=60.0)

        # Step 2: Calculate demands
        demands: dict[str, tuple[str, float, str]] = {}
        # (target_id -> (target_type, demand_amount, reason))

        for g in (goals or []):
            gid = g.get("id", "")
            importance = float(g.get("importance", 0.5))
            urgency = float(g.get("urgency", 0.5))
            demand = importance * urgency * 2.0
            demands[gid] = (
                "goal",
                demand,
                f"Active goal (importance={importance:.2f}, urgency={urgency:.2f})",
            )

        for b in (beliefs or []):
            bid = b.get("id", "")
            uncertainty = float(b.get("uncertainty", 0.5))
            demand = uncertainty * 0.8
            demands[bid] = (
                "belief",
                demand,
                f"Uncertain belief (uncertainty={uncertainty:.2f})",
            )

        for c in (concepts or []):
            cid = c.get("id", "")
            importance = float(c.get("importance", 0.5))
            activation = float(c.get("activation", 0.5))
            demand = importance * activation * 0.5
            demands[cid] = (
                "concept",
                demand,
                f"Important concept (importance={importance:.2f}, activation={activation:.2f})",
            )

        for cx in (contradictions or []):
            cxid = cx.get("id", "")
            severity = float(cx.get("severity", 0.5))
            demand = severity * 1.5
            demands[cxid] = (
                "contradiction",
                demand,
                f"Unresolved contradiction (severity={severity:.2f})",
            )

        # Step 3: Allocate within budget constraints
        total_demand = sum(d[1] for d in demands.values())
        new_allocations = 0

        if total_demand > 0:
            # Available budget after existing allocations
            current_allocated = self._total_allocated()
            available_budget = max(0.0, self._total_budget - current_allocated)

            if total_demand <= available_budget:
                # Sufficient budget — grant full demands
                for target_id, (target_type, demand, reason) in demands.items():
                    alloc = self._allocations.get(target_id)
                    if alloc is not None:
                        alloc.allocated_amount += demand
                        alloc.priority_reason = reason
                        alloc.granted_at = utc_now()
                        await self._save_allocation(alloc)
                    else:
                        new_alloc = AttentionAllocation(
                            target_id=target_id,
                            target_type=target_type,
                            allocated_amount=demand,
                            priority_reason=reason,
                            decay_rate=self.DEFAULT_DECAY_RATE,
                        )
                        self._allocations[target_id] = new_alloc
                        await self._save_allocation(new_alloc)
                        new_allocations += 1
            else:
                # Over budget — proportional allocation
                scale = available_budget / total_demand
                for target_id, (target_type, demand, reason) in demands.items():
                    granted = demand * scale
                    if granted < self.DECAY_THRESHOLD:
                        continue
                    alloc = self._allocations.get(target_id)
                    if alloc is not None:
                        alloc.allocated_amount += granted
                        alloc.priority_reason = reason + " [proportional]"
                        alloc.granted_at = utc_now()
                        await self._save_allocation(alloc)
                    else:
                        new_alloc = AttentionAllocation(
                            target_id=target_id,
                            target_type=target_type,
                            allocated_amount=granted,
                            priority_reason=reason + " [proportional]",
                            decay_rate=self.DEFAULT_DECAY_RATE,
                        )
                        self._allocations[target_id] = new_alloc
                        await self._save_allocation(new_alloc)
                        new_allocations += 1

        # Step 4: Remove allocations below threshold (already done in apply_decay,
        # but do a final sweep for safety)
        expired = 0
        to_remove: list[str] = []
        for target_id, alloc in self._allocations.items():
            if alloc.allocated_amount < self.DECAY_THRESHOLD:
                to_remove.append(target_id)
        for target_id in to_remove:
            del self._allocations[target_id]
            await self._delete_allocation(target_id)
            expired += 1

        # Build result
        cycle_time_ms = (time.monotonic() - cycle_start) * 1000.0
        final_allocated = self._total_allocated()
        top_targets = [
            a.target_id
            for a in sorted(
                self._allocations.values(),
                key=lambda a: a.allocated_amount,
                reverse=True,
            )[:5]
        ]

        return EconomyCycleResult(
            total_allocated=final_allocated,
            total_decayed=total_decayed,
            new_allocations=new_allocations,
            expired_allocations=expired,
            top_targets=top_targets,
            budget_utilization=(
                final_allocated / self._total_budget if self._total_budget > 0 else 0.0
            ),
            cycle_time_ms=cycle_time_ms,
        )

    async def get_budget(self) -> AttentionBudget:
        """Get the current attention budget state.

        Returns:
            AttentionBudget with current totals and allocations.
        """
        allocated = self._total_allocated()
        return AttentionBudget(
            total_budget=self._total_budget,
            allocated=allocated,
            available=max(0.0, self._total_budget - allocated),
            allocations=list(self._allocations.values()),
        )

    async def get_top_allocated(self, limit: int = 10) -> list[AttentionAllocation]:
        """Get the top allocations sorted by amount (descending).

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of AttentionAllocation entries sorted by amount.
        """
        sorted_allocs = sorted(
            self._allocations.values(),
            key=lambda a: a.allocated_amount,
            reverse=True,
        )
        return sorted_allocs[:limit]

    async def get_stats(self) -> dict[str, Any]:
        """Get attention economy statistics."""
        if not self._allocations:
            return {
                "total_budget": self._total_budget,
                "total_allocated": 0.0,
                "available": self._total_budget,
                "allocation_count": 0,
                "by_type": {},
                "avg_allocation": 0.0,
                "budget_utilization": 0.0,
            }

        by_type: dict[str, int] = {}
        by_type_amount: dict[str, float] = {}
        for alloc in self._allocations.values():
            by_type[alloc.target_type] = by_type.get(alloc.target_type, 0) + 1
            by_type_amount[alloc.target_type] = (
                by_type_amount.get(alloc.target_type, 0.0) + alloc.allocated_amount
            )

        total_alloc = self._total_allocated()
        return {
            "total_budget": self._total_budget,
            "total_allocated": total_alloc,
            "available": max(0.0, self._total_budget - total_alloc),
            "allocation_count": len(self._allocations),
            "by_type": by_type,
            "by_type_amount": by_type_amount,
            "avg_allocation": total_alloc / len(self._allocations),
            "budget_utilization": (
                total_alloc / self._total_budget if self._total_budget > 0 else 0.0
            ),
        }
