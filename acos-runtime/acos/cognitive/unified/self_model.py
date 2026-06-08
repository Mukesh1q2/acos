"""
Self Model — the system maintains awareness of its own capabilities.

Tracks:
- current strengths (what it does well)
- weaknesses (what it does poorly)
- uncertainties (what it's unsure about)
- performance history (rolling records over time)
- model preferences (e.g., "Qwen performs better than Gemma for coding")

Assessment rules:
- Strength: average score > 0.7 for a dimension
- Weakness: average score < 0.4 for a dimension
- Uncertainty: high score variance OR score between 0.4–0.6

Persistence via shared StorageBackend SQLite connection.
"""

from __future__ import annotations

import statistics
import time
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v5_models import (
    ModelPreference,
    PerformanceRecord,
    SelfAssessmentDimension,
    SelfModelState,
    gen_id,
    utc_now,
)


# Rolling window size for computing averages / variance per dimension
ROLLING_WINDOW = 50


class SelfModel:
    """Self Model — maintain awareness of the system's own capabilities.

    Usage::

        store = StorageBackend()
        await store.initialize()

        sm = SelfModel(store)
        await sm.initialize()

        await sm.record_performance(
            SelfAssessmentDimension.REASONING_QUALITY, 0.85, context="syllogism"
        )
        strengths = await sm.assess_strengths()
        state = await sm.get_self_state()
    """

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage

        # In-memory caches
        self._performance_records: list[PerformanceRecord] = []
        self._model_preferences: dict[str, ModelPreference] = {}
        # key = f"{model_a}|{model_b}|{domain}" for quick lookup

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load existing self model state."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS self_performance_records (
                id TEXT PRIMARY KEY,
                dimension TEXT NOT NULL,
                score REAL NOT NULL DEFAULT 0.5,
                context TEXT NOT NULL DEFAULT '',
                session_id TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_perf_dimension
                ON self_performance_records(dimension);
            CREATE INDEX IF NOT EXISTS idx_perf_timestamp
                ON self_performance_records(timestamp);

            CREATE TABLE IF NOT EXISTS self_model_preferences (
                id TEXT PRIMARY KEY,
                model_a TEXT NOT NULL,
                model_b TEXT NOT NULL,
                preferred TEXT NOT NULL,
                domain TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0.5,
                evidence_count INTEGER NOT NULL DEFAULT 0,
                last_updated TEXT NOT NULL,
                created_at TEXT NOT NULL,
                lookup_key TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_pref_domain
                ON self_model_preferences(domain);
            CREATE INDEX IF NOT EXISTS idx_pref_lookup
                ON self_model_preferences(lookup_key);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        assert conn is not None

        # Load performance records (most recent ROLLING_WINDOW per dimension)
        cursor = await conn.execute(
            "SELECT * FROM self_performance_records ORDER BY timestamp DESC"
        )
        rows = await cursor.fetchall()
        seen_dims: dict[str, int] = {}
        for row in rows:
            dim = row["dimension"]
            seen_dims[dim] = seen_dims.get(dim, 0) + 1
            if seen_dims[dim] <= ROLLING_WINDOW:
                record = self._row_to_performance_record(row)
                self._performance_records.append(record)

        # Reverse to chronological order
        self._performance_records.reverse()

        # Load model preferences
        cursor = await conn.execute("SELECT * FROM self_model_preferences")
        rows = await cursor.fetchall()
        for row in rows:
            pref = self._row_to_model_preference(row)
            lookup_key = row["lookup_key"]
            self._model_preferences[lookup_key] = pref

    # ─── Row ↔ Model helpers ────────────────────────────────────────────────

    @staticmethod
    def _row_to_performance_record(row: Any) -> PerformanceRecord:
        return PerformanceRecord(
            id=row["id"],
            dimension=SelfAssessmentDimension(row["dimension"]),
            score=row["score"],
            context=row["context"],
            session_id=row["session_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )

    @staticmethod
    def _row_to_model_preference(row: Any) -> ModelPreference:
        return ModelPreference(
            id=row["id"],
            model_a=row["model_a"],
            model_b=row["model_b"],
            preferred=row["preferred"],
            domain=row["domain"],
            confidence=row["confidence"],
            evidence_count=row["evidence_count"],
            last_updated=datetime.fromisoformat(row["last_updated"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    async def _save_performance_record(self, record: PerformanceRecord) -> None:
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            """INSERT OR REPLACE INTO self_performance_records
               (id, dimension, score, context, session_id, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                record.id,
                record.dimension.value,
                record.score,
                record.context,
                record.session_id,
                record.timestamp.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_model_preference(self, pref: ModelPreference) -> None:
        conn = self._storage._conn
        assert conn is not None
        lookup_key = f"{pref.model_a}|{pref.model_b}|{pref.domain}"
        await conn.execute(
            """INSERT OR REPLACE INTO self_model_preferences
               (id, model_a, model_b, preferred, domain,
                confidence, evidence_count, last_updated, created_at, lookup_key)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pref.id,
                pref.model_a,
                pref.model_b,
                pref.preferred,
                pref.domain,
                pref.confidence,
                pref.evidence_count,
                pref.last_updated.isoformat(),
                pref.created_at.isoformat(),
                lookup_key,
            ),
        )
        await conn.commit()

    # ─── Helpers ────────────────────────────────────────────────────────────

    def _scores_for_dimension(self, dimension: SelfAssessmentDimension) -> list[float]:
        """Get the last ROLLING_WINDOW scores for a dimension."""
        scores = [
            r.score
            for r in self._performance_records
            if r.dimension == dimension
        ]
        return scores[-ROLLING_WINDOW:]

    def _average_score(self, dimension: SelfAssessmentDimension) -> float:
        scores = self._scores_for_dimension(dimension)
        if not scores:
            return 0.5  # Default middle score if no data
        return statistics.mean(scores)

    def _score_variance(self, dimension: SelfAssessmentDimension) -> float:
        scores = self._scores_for_dimension(dimension)
        if len(scores) < 2:
            return 0.0
        return statistics.variance(scores)

    @staticmethod
    def _make_lookup_key(model_a: str, model_b: str, domain: str) -> str:
        return f"{model_a}|{model_b}|{domain}"

    # ─── Core API ───────────────────────────────────────────────────────────

    async def record_performance(
        self,
        dimension: SelfAssessmentDimension,
        score: float,
        context: str = "",
    ) -> PerformanceRecord:
        """Record a performance observation.

        Args:
            dimension: The assessment dimension being measured.
            score: Performance score [0, 1].
            context: Optional context description.

        Returns:
            The created PerformanceRecord.
        """
        record = PerformanceRecord(
            dimension=dimension,
            score=max(0.0, min(1.0, score)),
            context=context,
        )
        self._performance_records.append(record)
        await self._save_performance_record(record)

        # Trim in-memory list if it grows beyond reasonable bounds
        # Keep last ROLLING_WINDOW * number_of_dimensions entries
        max_records = ROLLING_WINDOW * len(SelfAssessmentDimension)
        if len(self._performance_records) > max_records * 2:
            self._performance_records = self._performance_records[-max_records:]

        return record

    async def add_model_preference(
        self,
        model_a: str,
        model_b: str,
        preferred: str,
        domain: str,
        confidence: float = 0.5,
    ) -> ModelPreference:
        """Add a model preference entry.

        Args:
            model_a: First model identifier.
            model_b: Second model identifier.
            preferred: Which model is preferred (model_a or model_b value).
            domain: Domain of comparison (e.g., "coding", "analysis").
            confidence: Confidence in this preference [0, 1].

        Returns:
            The created ModelPreference.
        """
        lookup_key = self._make_lookup_key(model_a, model_b, domain)

        # If a preference for this pair+domain already exists, update it
        if lookup_key in self._model_preferences:
            existing = self._model_preferences[lookup_key]
            existing.preferred = preferred
            existing.confidence = max(0.0, min(1.0, confidence))
            existing.evidence_count += 1
            existing.last_updated = utc_now()
            await self._save_model_preference(existing)
            return existing

        pref = ModelPreference(
            model_a=model_a,
            model_b=model_b,
            preferred=preferred,
            domain=domain,
            confidence=max(0.0, min(1.0, confidence)),
            evidence_count=1,
        )
        self._model_preferences[lookup_key] = pref
        await self._save_model_preference(pref)
        return pref

    async def update_model_preference(
        self,
        preference_id: str,
        winner: str,
    ) -> ModelPreference | None:
        """Update a model preference with a new observation.

        Increments evidence count and adjusts confidence upward.

        Args:
            preference_id: ID of the ModelPreference to update.
            winner: Which model won this round (model_a or model_b value).

        Returns:
            The updated ModelPreference, or None if not found.
        """
        for pref in self._model_preferences.values():
            if pref.id == preference_id:
                pref.preferred = winner
                pref.evidence_count += 1
                # Increase confidence slightly with each consistent observation
                pref.confidence = min(1.0, pref.confidence + 0.05)
                pref.last_updated = utc_now()
                await self._save_model_preference(pref)
                return pref
        return None

    async def assess_strengths(self) -> list[str]:
        """Identify current strengths.

        A dimension is a strength if its average score > 0.7.

        Returns:
            List of human-readable strength descriptions.
        """
        strengths: list[str] = []
        for dim in SelfAssessmentDimension:
            avg = self._average_score(dim)
            if avg > 0.7:
                strengths.append(
                    f"Strong {dim.value} (avg score: {avg:.2f})"
                )
        return strengths

    async def assess_weaknesses(self) -> list[str]:
        """Identify current weaknesses.

        A dimension is a weakness if its average score < 0.4.

        Returns:
            List of human-readable weakness descriptions.
        """
        weaknesses: list[str] = []
        for dim in SelfAssessmentDimension:
            avg = self._average_score(dim)
            if avg < 0.4:
                weaknesses.append(
                    f"Weak {dim.value} (avg score: {avg:.2f})"
                )
        return weaknesses

    async def assess_uncertainties(self) -> list[str]:
        """Identify what the system is uncertain about.

        A dimension is uncertain if:
        - Score variance is high (> 0.05), OR
        - Average score is between 0.4 and 0.6

        Returns:
            List of human-readable uncertainty descriptions.
        """
        uncertainties: list[str] = []
        for dim in SelfAssessmentDimension:
            avg = self._average_score(dim)
            var = self._score_variance(dim)
            if var > 0.05:
                uncertainties.append(
                    f"Uncertain {dim.value} (high variance: {var:.4f}, avg: {avg:.2f})"
                )
            elif 0.4 <= avg <= 0.6:
                uncertainties.append(
                    f"Uncertain {dim.value} (ambiguous avg: {avg:.2f})"
                )
        return uncertainties

    async def get_self_state(self) -> SelfModelState:
        """Get the current self model state.

        Returns:
            SelfModelState with strengths, weaknesses, uncertainties, scores,
            preferences, and overall performance.
        """
        strengths = await self.assess_strengths()
        weaknesses = await self.assess_weaknesses()
        uncertainties = await self.assess_uncertainties()

        assessment_scores: dict[str, float] = {}
        for dim in SelfAssessmentDimension:
            assessment_scores[dim.value] = self._average_score(dim)

        all_scores = [r.score for r in self._performance_records]
        avg_performance = statistics.mean(all_scores) if all_scores else 0.5

        return SelfModelState(
            strengths=strengths,
            weaknesses=weaknesses,
            uncertainties=uncertainties,
            assessment_scores=assessment_scores,
            model_preferences=list(self._model_preferences.values()),
            total_performance_records=len(self._performance_records),
            average_performance=avg_performance,
        )

    async def get_performance_history(
        self,
        dimension: SelfAssessmentDimension | None = None,
        limit: int = 100,
    ) -> list[PerformanceRecord]:
        """Get performance history, optionally filtered by dimension.

        Args:
            dimension: If provided, filter to this dimension only.
            limit: Maximum number of records to return.

        Returns:
            List of PerformanceRecord entries, most recent first.
        """
        if dimension is not None:
            records = [
                r for r in self._performance_records if r.dimension == dimension
            ]
        else:
            records = list(self._performance_records)

        # Return most recent first
        records = sorted(records, key=lambda r: r.timestamp, reverse=True)
        return records[:limit]

    async def get_model_preference(
        self,
        domain: str = "",
    ) -> ModelPreference | None:
        """Get the model preference for a given domain.

        If multiple preferences exist for the domain, returns the one
        with the highest confidence.

        Args:
            domain: Domain to look up (e.g., "coding").

        Returns:
            The best ModelPreference for the domain, or None.
        """
        candidates = [
            pref for pref in self._model_preferences.values()
            if pref.domain == domain
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.confidence)

    async def get_stats(self) -> dict[str, Any]:
        """Get self model statistics."""
        # Per-dimension stats
        dim_stats: dict[str, dict[str, Any]] = {}
        for dim in SelfAssessmentDimension:
            scores = self._scores_for_dimension(dim)
            if scores:
                dim_stats[dim.value] = {
                    "count": len(scores),
                    "average": statistics.mean(scores),
                    "variance": statistics.variance(scores) if len(scores) >= 2 else 0.0,
                    "min": min(scores),
                    "max": max(scores),
                }
            else:
                dim_stats[dim.value] = {
                    "count": 0,
                    "average": 0.5,
                    "variance": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                }

        all_scores = [r.score for r in self._performance_records]
        return {
            "total_performance_records": len(self._performance_records),
            "total_model_preferences": len(self._model_preferences),
            "average_performance": statistics.mean(all_scores) if all_scores else 0.5,
            "dimension_stats": dim_stats,
            "strength_count": sum(
                1 for d in SelfAssessmentDimension if self._average_score(d) > 0.7
            ),
            "weakness_count": sum(
                1 for d in SelfAssessmentDimension if self._average_score(d) < 0.4
            ),
            "uncertainty_count": sum(
                1 for d in SelfAssessmentDimension
                if self._score_variance(d) > 0.05
                or 0.4 <= self._average_score(d) <= 0.6
            ),
        }
