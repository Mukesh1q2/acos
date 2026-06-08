"""
Uncertainty Engine — track unknowns, conflicting beliefs, missing evidence, confidence changes.

Uncertainty must influence planning and reasoning. This module:
- Identifies knowledge gaps, conflicts, missing evidence
- Tracks confidence drift over time
- Propagates uncertainty through the knowledge graph
- Produces uncertainty reports for planning guidance

Persistence via shared StorageBackend SQLite connection.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v3_models import (
    UncertaintyEntry,
    UncertaintyReport,
    UncertaintyType,
    gen_id,
    utc_now,
)


class UncertaintyEngine:
    """Uncertainty Engine — identify, track, and propagate uncertainty.

    Usage::

        store = StorageBackend()
        await store.initialize()

        ue = UncertaintyEngine(store)
        await ue.initialize()

        entry = await ue.add_uncertainty(
            description="We lack evidence for claim X",
            uncertainty_type=UncertaintyType.MISSING_EVIDENCE,
            severity=0.8,
        )
        report = await ue.generate_report()
    """

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._entries: dict[str, UncertaintyEntry] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load existing entries."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS uncertainty_entries (
                id TEXT PRIMARY KEY,
                uncertainty_type TEXT NOT NULL,
                description TEXT NOT NULL,
                related_ids TEXT DEFAULT '[]',
                severity REAL DEFAULT 0.5,
                impact_on_planning REAL DEFAULT 0.5,
                resolution_suggestion TEXT DEFAULT '',
                is_resolved INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_uncertainty_type
                ON uncertainty_entries(uncertainty_type);
            CREATE INDEX IF NOT EXISTS idx_uncertainty_severity
                ON uncertainty_entries(severity);
            CREATE INDEX IF NOT EXISTS idx_uncertainty_resolved
                ON uncertainty_entries(is_resolved);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        assert conn is not None
        cursor = await conn.execute("SELECT * FROM uncertainty_entries")
        rows = await cursor.fetchall()
        for row in rows:
            entry = self._row_to_entry(row)
            self._entries[entry.id] = entry

    # ─── Row ↔ Model helpers ────────────────────────────────────────────────

    @staticmethod
    def _row_to_entry(row: Any) -> UncertaintyEntry:
        return UncertaintyEntry(
            id=row["id"],
            uncertainty_type=UncertaintyType(row["uncertainty_type"]),
            description=row["description"],
            related_ids=json.loads(row["related_ids"]) if row["related_ids"] else [],
            severity=row["severity"],
            impact_on_planning=row["impact_on_planning"],
            resolution_suggestion=row["resolution_suggestion"] or "",
            is_resolved=bool(row["is_resolved"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
        )

    async def _save_entry(self, entry: UncertaintyEntry) -> None:
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            """INSERT OR REPLACE INTO uncertainty_entries
               (id, uncertainty_type, description, related_ids, severity,
                impact_on_planning, resolution_suggestion, is_resolved,
                created_at, updated_at, resolved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.id,
                entry.uncertainty_type.value,
                entry.description,
                json.dumps(entry.related_ids),
                entry.severity,
                entry.impact_on_planning,
                entry.resolution_suggestion,
                int(entry.is_resolved),
                entry.created_at.isoformat(),
                entry.updated_at.isoformat(),
                entry.resolved_at.isoformat() if entry.resolved_at else None,
            ),
        )
        await conn.commit()

    # ─── Core API ───────────────────────────────────────────────────────────

    async def add_uncertainty(
        self,
        description: str,
        uncertainty_type: UncertaintyType,
        severity: float = 0.5,
        impact_on_planning: float = 0.5,
        related_ids: list[str] | None = None,
        resolution_suggestion: str = "",
    ) -> UncertaintyEntry:
        """Add a new uncertainty entry.

        Args:
            description: What is uncertain.
            uncertainty_type: Category of uncertainty.
            severity: How severe [0, 1].
            impact_on_planning: How much this affects planning [0, 1].
            related_ids: IDs of related concepts/beliefs/goals.
            resolution_suggestion: How to resolve this uncertainty.

        Returns:
            The created UncertaintyEntry.
        """
        entry = UncertaintyEntry(
            uncertainty_type=uncertainty_type,
            description=description,
            severity=max(0.0, min(1.0, severity)),
            impact_on_planning=max(0.0, min(1.0, impact_on_planning)),
            related_ids=related_ids or [],
            resolution_suggestion=resolution_suggestion,
        )
        self._entries[entry.id] = entry
        await self._save_entry(entry)
        return entry

    async def resolve_uncertainty(
        self, entry_id: str, resolution: str = ""
    ) -> UncertaintyEntry | None:
        """Mark an uncertainty as resolved.

        Args:
            entry_id: ID of the uncertainty entry.
            resolution: How it was resolved.

        Returns:
            The updated UncertaintyEntry, or None if not found.
        """
        entry = self._entries.get(entry_id)
        if entry is None:
            return None

        entry.is_resolved = True
        entry.resolved_at = utc_now()
        entry.updated_at = utc_now()
        if resolution:
            entry.resolution_suggestion = resolution
        await self._save_entry(entry)
        return entry

    async def update_severity(
        self, entry_id: str, new_severity: float
    ) -> UncertaintyEntry | None:
        """Update the severity of an uncertainty entry."""
        entry = self._entries.get(entry_id)
        if entry is None:
            return None

        entry.severity = max(0.0, min(1.0, new_severity))
        entry.updated_at = utc_now()
        await self._save_entry(entry)
        return entry

    async def get_active_uncertainties(self) -> list[UncertaintyEntry]:
        """Get all unresolved uncertainty entries, sorted by severity (desc)."""
        active = [e for e in self._entries.values() if not e.is_resolved]
        active.sort(key=lambda e: e.severity, reverse=True)
        return active

    async def get_uncertainties_by_type(
        self, uncertainty_type: UncertaintyType
    ) -> list[UncertaintyEntry]:
        """Get uncertainties of a specific type."""
        return [
            e for e in self._entries.values()
            if e.uncertainty_type == uncertainty_type and not e.is_resolved
        ]

    async def detect_from_beliefs(self, beliefs: list[Any]) -> list[UncertaintyEntry]:
        """Detect uncertainties from belief state.

        Scans beliefs for:
        - Low confidence (< 0.3) → CONFIDENCE_DRIFT
        - Conflicting beliefs → CONFLICT
        - Beliefs with no evidence → MISSING_EVIDENCE
        - Beliefs with contradicting evidence → CONFLICT

        Args:
            beliefs: List of Belief objects.

        Returns:
            List of newly created UncertaintyEntry objects.
        """
        new_entries: list[UncertaintyEntry] = []

        for belief in beliefs:
            # Skip already-processed beliefs
            if hasattr(belief, 'status') and str(belief.status) not in ('active', 'BeliefStatus.ACTIVE'):
                continue

            # Low confidence → confidence drift
            if hasattr(belief, 'confidence') and belief.confidence < 0.3:
                entry = await self.add_uncertainty(
                    description=f"Low confidence belief: '{getattr(belief, 'statement', 'unknown')}' "
                                f"(confidence={getattr(belief, 'confidence', 0):.2f})",
                    uncertainty_type=UncertaintyType.CONFIDENCE_DRIFT,
                    severity=1.0 - getattr(belief, 'confidence', 0.5),
                    impact_on_planning=0.7,
                    related_ids=[belief.id] if hasattr(belief, 'id') else [],
                    resolution_suggestion="Gather more supporting evidence or abandon the belief.",
                )
                new_entries.append(entry)

            # Missing evidence
            if hasattr(belief, 'supporting_evidence') and len(belief.supporting_evidence) == 0:
                entry = await self.add_uncertainty(
                    description=f"Belief without supporting evidence: '{getattr(belief, 'statement', 'unknown')}'",
                    uncertainty_type=UncertaintyType.MISSING_EVIDENCE,
                    severity=0.6,
                    impact_on_planning=0.5,
                    related_ids=[belief.id] if hasattr(belief, 'id') else [],
                    resolution_suggestion="Find supporting evidence for this belief.",
                )
                new_entries.append(entry)

            # Conflicting evidence
            if (hasattr(belief, 'contradicting_evidence') and
                    len(belief.contradicting_evidence) > 0):
                entry = await self.add_uncertainty(
                    description=f"Belief with contradicting evidence: '{getattr(belief, 'statement', 'unknown')}' "
                                f"({len(belief.contradicting_evidence)} contradicting items)",
                    uncertainty_type=UncertaintyType.CONFLICT,
                    severity=0.8,
                    impact_on_planning=0.8,
                    related_ids=[belief.id] if hasattr(belief, 'id') else [],
                    resolution_suggestion="Resolve the contradiction by evaluating evidence quality.",
                )
                new_entries.append(entry)

        return new_entries

    async def detect_from_goals(self, goals: list[Any]) -> list[UncertaintyEntry]:
        """Detect uncertainties from goal state.

        Scans goals for:
        - Goals with unmet dependencies → ASSUMPTION
        - Goals with low progress → KNOWLEDGE_GAP
        - Goals with no related beliefs → AMBIGUITY

        Args:
            goals: List of Goal objects.

        Returns:
            List of newly created UncertaintyEntry objects.
        """
        new_entries: list[UncertaintyEntry] = []

        for goal in goals:
            # Goals with no related beliefs → ambiguity
            if hasattr(goal, 'related_belief_ids') and len(goal.related_belief_ids) == 0:
                entry = await self.add_uncertainty(
                    description=f"Goal without supporting beliefs: '{getattr(goal, 'description', 'unknown')}'",
                    uncertainty_type=UncertaintyType.AMBIGUITY,
                    severity=0.4,
                    impact_on_planning=0.6,
                    related_ids=[goal.id] if hasattr(goal, 'id') else [],
                    resolution_suggestion="Identify beliefs that support this goal.",
                )
                new_entries.append(entry)

            # Goals with unmet dependencies
            if hasattr(goal, 'dependency_ids') and len(goal.dependency_ids) > 0:
                entry = await self.add_uncertainty(
                    description=f"Goal with {len(goal.dependency_ids)} unmet dependencies: "
                                f"'{getattr(goal, 'description', 'unknown')}'",
                    uncertainty_type=UncertaintyType.ASSUMPTION,
                    severity=0.5,
                    impact_on_planning=0.9,
                    related_ids=[goal.id] if hasattr(goal, 'id') else [],
                    resolution_suggestion="Complete prerequisite goals first.",
                )
                new_entries.append(entry)

        return new_entries

    async def propagate_uncertainty(
        self,
        source_id: str,
        target_ids: list[str],
        propagation_factor: float = 0.5,
    ) -> list[UncertaintyEntry]:
        """Propagate uncertainty from a source to related elements.

        When an element is uncertain, elements that depend on it also
        become uncertain (with reduced severity based on propagation factor).

        Args:
            source_id: The ID of the uncertain element.
            target_ids: IDs of elements that depend on the source.
            propagation_factor: How much uncertainty propagates [0, 1].

        Returns:
            List of newly created propagated UncertaintyEntry objects.
        """
        # Find the source uncertainty
        source_entry = None
        for entry in self._entries.values():
            if source_id in entry.related_ids and not entry.is_resolved:
                source_entry = entry
                break

        if source_entry is None:
            return []

        new_entries: list[UncertaintyEntry] = []
        propagated_severity = source_entry.severity * propagation_factor

        for target_id in target_ids:
            # Check if there's already a propagated uncertainty for this target
            # (skip the source entry itself — it contains the targets in its related_ids)
            existing = any(
                e for e in self._entries.values()
                if e.id != source_entry.id
                and target_id in e.related_ids
                and e.uncertainty_type == UncertaintyType.KNOWLEDGE_GAP
                and not e.is_resolved
            )
            if existing:
                continue

            entry = await self.add_uncertainty(
                description=f"Propagated uncertainty from '{source_entry.description[:80]}': "
                            f"affects related element",
                uncertainty_type=UncertaintyType.KNOWLEDGE_GAP,
                severity=max(0.1, propagated_severity),
                impact_on_planning=source_entry.impact_on_planning * propagation_factor,
                related_ids=[source_id, target_id],
                resolution_suggestion=f"Resolve the source uncertainty first: {source_entry.resolution_suggestion}",
            )
            new_entries.append(entry)

        return new_entries

    async def generate_report(self) -> UncertaintyReport:
        """Generate a comprehensive uncertainty report.

        Returns:
            An UncertaintyReport with all active uncertainties and aggregate metrics.
        """
        active = await self.get_active_uncertainties()
        high_severity = [e for e in active if e.severity >= 0.7]
        total_uncertainty = sum(e.severity for e in active) / max(len(active), 1)
        planning_impact = sum(e.impact_on_planning for e in active) / max(len(active), 1)

        return UncertaintyReport(
            entries=active,
            total_uncertainty=min(1.0, total_uncertainty),
            high_severity_count=len(high_severity),
            planning_impact_score=min(1.0, planning_impact),
        )

    async def get_planning_guidance(self) -> dict[str, Any]:
        """Get guidance for planning based on current uncertainty state.

        Returns:
            Dict with recommended actions based on uncertainty analysis.
        """
        report = await self.generate_report()
        active = report.entries

        high_priority = [e for e in active if e.severity >= 0.7 and e.impact_on_planning >= 0.7]
        moderate = [e for e in active if 0.4 <= e.severity < 0.7]

        return {
            "total_uncertainty": report.total_uncertainty,
            "planning_impact": report.planning_impact_score,
            "high_priority_count": len(high_priority),
            "moderate_count": len(moderate),
            "recommended_actions": [
                e.resolution_suggestion for e in high_priority[:5]
                if e.resolution_suggestion
            ],
            "uncertainty_types": {
                ut.value: len([e for e in active if e.uncertainty_type == ut])
                for ut in UncertaintyType
            },
        }

    async def get_stats(self) -> dict[str, Any]:
        """Get uncertainty statistics."""
        active = [e for e in self._entries.values() if not e.is_resolved]
        resolved = [e for e in self._entries.values() if e.is_resolved]

        by_type: dict[str, int] = {}
        for entry in active:
            key = entry.uncertainty_type.value
            by_type[key] = by_type.get(key, 0) + 1

        return {
            "total_entries": len(self._entries),
            "active_entries": len(active),
            "resolved_entries": len(resolved),
            "by_type": by_type,
            "avg_severity": (
                sum(e.severity for e in active) / len(active) if active else 0.0
            ),
            "high_severity_count": len([e for e in active if e.severity >= 0.7]),
        }
