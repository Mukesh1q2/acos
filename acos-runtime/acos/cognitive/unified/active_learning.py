"""
Active Learning Loop — prediction error tracking, belief/confidence updates, and model improvement.

Implements the learning cycle:
    Prediction → Outcome → Error Measurement → Belief Update → Confidence Update → World Model Update

Key concepts
------------
* **Prediction error as a first-class metric** — every error is recorded, stored
  in the database, and queryable.  This makes the learning signal traceable.
* **Learning signal classification** — each error is classified as one of:
  ``correct``, ``incorrect``, ``partial``, ``surprising``, or ``confirming``.
* **Surprise detection** — when prediction error exceeds a configurable
  threshold (default 0.5), the outcome is marked as "surprising" to trigger
  deeper model revision.
* **Belief update** — incorrect predictions reduce confidence in the beliefs
  that supported them.
* **World model update** — the correct transition is recorded so future
  predictions improve.
* **Learning efficiency** — ratio of correct predictions to total predictions.

Persistence
-----------
All prediction errors are stored in SQLite tables managed through
:class:`~acos.memory.store.StorageBackend`.  The ActiveLearningLoop depends
on :class:`WorldModelEngine` for world model updates and on
:class:`~acos.cognitive.belief_system.BeliefState` for belief confidence
adjustments (optional — if not provided, belief updates are tracked
internally only).
"""

from __future__ import annotations

import json
import time as time_mod
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v5_models import (
    LearningCycleResult,
    LearningSignal,
    PredictionErrorRecord,
    gen_id,
    utc_now,
)


class ActiveLearningLoop:
    """Active Learning Loop — close the loop between prediction and learning.

    The cycle is:
        1. **Measure** — compare a prediction against the actual outcome
        2. **Classify** — determine the learning signal (correct, incorrect, etc.)
        3. **Update beliefs** — reduce confidence in beliefs that supported wrong predictions
        4. **Update confidence** — adjust overall prediction confidence
        5. **Update world model** — record the correct transition for future predictions

    Usage::

        store = StorageBackend()
        await store.initialize()

        from acos.cognitive.unified.world_model_engine import WorldModelEngine
        engine = WorldModelEngine(store)
        await engine.initialize()

        loop = ActiveLearningLoop(store, world_model_engine=engine)
        await loop.initialize()

        # Measure a single error
        error_record = await loop.measure_prediction_error(
            prediction_id="pred-123",
            actual_outcome="learning",
        )

        # Run a full learning cycle
        result = await loop.run_learning_cycle([
            {"prediction_id": "pred-123", "actual_outcome": "learning"},
            {"prediction_id": "pred-456", "actual_outcome": "idle"},
        ])
    """

    # Threshold above which a prediction error is considered "surprising"
    DEFAULT_SURPRISE_THRESHOLD = 0.5
    # How much to reduce belief confidence on incorrect predictions
    BELIEF_PENALTY = 0.15
    # How much to increase belief confidence on correct predictions (smaller)
    BELIEF_REWARD = 0.05
    # Confidence adjustment rate per error
    CONFIDENCE_ADJUSTMENT_RATE = 0.1
    # Maximum belief IDs to track per prediction
    MAX_BELIEF_IDS_PER_PREDICTION = 20

    def __init__(
        self,
        storage: StorageBackend,
        world_model_engine: Any | None = None,
        belief_system: Any | None = None,
        surprise_threshold: float | None = None,
    ) -> None:
        self._storage = storage
        self._world_model_engine = world_model_engine
        self._belief_system = belief_system
        self._surprise_threshold = surprise_threshold or self.DEFAULT_SURPRISE_THRESHOLD

        # In-memory index of all error records
        self._error_records: dict[str, PredictionErrorRecord] = {}
        # Track current confidence values (prediction_id -> confidence)
        self._confidence_map: dict[str, float] = {}
        # Track which belief IDs support which predictions
        self._prediction_belief_map: dict[str, list[str]] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load existing error records."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS all_prediction_errors (
                id TEXT PRIMARY KEY,
                prediction_id TEXT NOT NULL,
                predicted_value TEXT DEFAULT '',
                actual_value TEXT DEFAULT '',
                absolute_error REAL DEFAULT 0.0,
                squared_error REAL DEFAULT 0.0,
                learning_signal TEXT NOT NULL DEFAULT 'partial',
                belief_ids_updated TEXT DEFAULT '[]',
                confidence_before REAL DEFAULT 0.5,
                confidence_after REAL DEFAULT 0.5,
                world_model_updated INTEGER DEFAULT 0,
                reflection TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS all_prediction_belief_map (
                id TEXT PRIMARY KEY,
                prediction_id TEXT NOT NULL,
                belief_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS all_confidence_map (
                prediction_id TEXT PRIMARY KEY,
                confidence REAL DEFAULT 0.5,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_all_pe_prediction
                ON all_prediction_errors(prediction_id);
            CREATE INDEX IF NOT EXISTS idx_all_pe_signal
                ON all_prediction_errors(learning_signal);
            CREATE INDEX IF NOT EXISTS idx_all_pe_created
                ON all_prediction_errors(created_at);
            CREATE INDEX IF NOT EXISTS idx_all_pbm_prediction
                ON all_prediction_belief_map(prediction_id);
            CREATE INDEX IF NOT EXISTS idx_all_pbm_belief
                ON all_prediction_belief_map(belief_id);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        assert conn is not None

        # Load error records
        cursor = await conn.execute("SELECT * FROM all_prediction_errors")
        rows = await cursor.fetchall()
        for row in rows:
            record = PredictionErrorRecord(
                id=row["id"],
                prediction_id=row["prediction_id"],
                predicted_value=row["predicted_value"],
                actual_value=row["actual_value"],
                absolute_error=row["absolute_error"],
                squared_error=row["squared_error"],
                learning_signal=LearningSignal(row["learning_signal"]),
                belief_ids_updated=json.loads(row["belief_ids_updated"]) if row["belief_ids_updated"] else [],
                confidence_before=row["confidence_before"],
                confidence_after=row["confidence_after"],
                world_model_updated=bool(row["world_model_updated"]),
                reflection=row["reflection"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            self._error_records[record.id] = record

        # Load prediction-belief map
        cursor = await conn.execute("SELECT * FROM all_prediction_belief_map")
        rows = await cursor.fetchall()
        for row in rows:
            pred_id = row["prediction_id"]
            belief_id = row["belief_id"]
            if pred_id not in self._prediction_belief_map:
                self._prediction_belief_map[pred_id] = []
            if belief_id not in self._prediction_belief_map[pred_id]:
                self._prediction_belief_map[pred_id].append(belief_id)

        # Load confidence map
        cursor = await conn.execute("SELECT * FROM all_confidence_map")
        rows = await cursor.fetchall()
        for row in rows:
            self._confidence_map[row["prediction_id"]] = row["confidence"]

    # ─── Persistence helpers ────────────────────────────────────────────────

    async def _save_error_record(self, record: PredictionErrorRecord) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO all_prediction_errors
               (id, prediction_id, predicted_value, actual_value,
                absolute_error, squared_error, learning_signal,
                belief_ids_updated, confidence_before, confidence_after,
                world_model_updated, reflection, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.id,
                record.prediction_id,
                record.predicted_value,
                record.actual_value,
                record.absolute_error,
                record.squared_error,
                record.learning_signal.value,
                json.dumps(record.belief_ids_updated),
                record.confidence_before,
                record.confidence_after,
                int(record.world_model_updated),
                record.reflection,
                json.dumps(record.metadata),
                record.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_prediction_belief_map(
        self, prediction_id: str, belief_id: str,
    ) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        entry_id = gen_id()
        await conn.execute(
            """INSERT OR IGNORE INTO all_prediction_belief_map
               (id, prediction_id, belief_id, created_at)
               VALUES (?, ?, ?, ?)""",
            (entry_id, prediction_id, belief_id, utc_now().isoformat()),
        )
        await conn.commit()

    async def _save_confidence(self, prediction_id: str, confidence: float) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO all_confidence_map
               (prediction_id, confidence, updated_at)
               VALUES (?, ?, ?)""",
            (prediction_id, confidence, utc_now().isoformat()),
        )
        await conn.commit()

    # ─── Core: Measure Prediction Error ─────────────────────────────────────

    async def measure_prediction_error(
        self,
        prediction_id: str,
        actual_outcome: str,
    ) -> PredictionErrorRecord:
        """Measure prediction error — the first-class error metric.

        Compares a prediction's expected value against the actual outcome,
        computes error metrics, and classifies the learning signal.

        The error record is persisted to the database and can be queried
        later for analysis.

        Args:
            prediction_id: ID of the prediction to evaluate.
            actual_outcome: The actual outcome that occurred.

        Returns:
            A :class:`PredictionErrorRecord` with all error metrics.
        """
        # Retrieve the prediction from the world model engine
        predicted_value = ""
        confidence_before = 0.5
        source_state = ""

        if self._world_model_engine is not None:
            # Try future predictions first
            fp = await self._world_model_engine.get_future_prediction(prediction_id)
            if fp is not None:
                predicted_value = fp.predicted_state
                confidence_before = fp.confidence
                source_state = fp.metadata.get("source_state", "")
            else:
                # Try action estimates
                ae = await self._world_model_engine.get_action_estimate(prediction_id)
                if ae is not None:
                    predicted_value = ae.expected_outcome
                    confidence_before = ae.confidence
                    source_state = ae.metadata.get("source_state", "")
                else:
                    # Try base WorldModel predictions
                    bp = await self._world_model_engine.world_model.get_prediction(prediction_id)
                    if bp is not None:
                        predicted_value = bp.predicted_state
                        confidence_before = bp.confidence
                        source_state = bp.source_state
        else:
            # Fallback: check confidence map
            confidence_before = self._confidence_map.get(prediction_id, 0.5)

        # Compute error metrics
        if predicted_value == actual_outcome:
            absolute_error = 0.0
        else:
            absolute_error = 1.0  # Categorical: match or no match

        squared_error = absolute_error ** 2

        # Classify the learning signal
        learning_signal = self._classify_learning_signal(
            absolute_error, confidence_before,
        )

        # Build reflection
        reflection = self._build_reflection(
            predicted_value, actual_outcome, absolute_error, learning_signal,
        )

        record = PredictionErrorRecord(
            prediction_id=prediction_id,
            predicted_value=predicted_value,
            actual_value=actual_outcome,
            absolute_error=absolute_error,
            squared_error=squared_error,
            learning_signal=learning_signal,
            belief_ids_updated=[],  # Will be populated by update_beliefs_from_error
            confidence_before=confidence_before,
            confidence_after=confidence_before,  # Will be updated by update_confidence_from_error
            world_model_updated=False,  # Will be updated by update_world_model_from_error
            reflection=reflection,
            metadata={"source_state": source_state},
        )

        await self._save_error_record(record)
        self._error_records[record.id] = record
        return record

    # ─── Core: Update Beliefs ───────────────────────────────────────────────

    async def update_beliefs_from_error(
        self,
        error_record: PredictionErrorRecord,
    ) -> list[str]:
        """Update beliefs based on a prediction error.

        If the prediction was wrong, reduce confidence in the beliefs
        that supported it.  If the prediction was correct, slightly
        increase confidence in supporting beliefs.

        Args:
            error_record: The error record to process.

        Returns:
            List of belief IDs that were updated.
        """
        updated_ids: list[str] = []

        # Find beliefs associated with this prediction
        belief_ids = self._prediction_belief_map.get(error_record.prediction_id, [])

        if not belief_ids:
            # No beliefs tracked for this prediction — nothing to update
            return updated_ids

        if error_record.absolute_error > 0.0:
            # Prediction was wrong: reduce belief confidence
            delta = -self.BELIEF_PENALTY * error_record.absolute_error
        else:
            # Prediction was correct: small reward
            delta = self.BELIEF_REWARD

        if self._belief_system is not None:
            # Use the actual BeliefState to update beliefs
            for belief_id in belief_ids[:self.MAX_BELIEF_IDS_PER_PREDICTION]:
                try:
                    self._belief_system.update_confidence(belief_id, delta)
                    updated_ids.append(belief_id)
                except ValueError:
                    # Belief not found — skip
                    continue
        else:
            # No belief system connected — just track the IDs
            updated_ids = list(belief_ids[:self.MAX_BELIEF_IDS_PER_PREDICTION])

        # Update the error record
        error_record.belief_ids_updated = updated_ids
        await self._save_error_record(error_record)

        return updated_ids

    # ─── Core: Update Confidence ────────────────────────────────────────────

    async def update_confidence_from_error(
        self,
        error_record: PredictionErrorRecord,
    ) -> float:
        """Update prediction confidence based on a prediction error.

        Confidence is adjusted proportionally to the error:
        - Correct prediction: increase confidence slightly
        - Incorrect prediction: decrease confidence proportionally

        Args:
            error_record: The error record to process.

        Returns:
            The new confidence value.
        """
        confidence_before = error_record.confidence_before

        if error_record.absolute_error < 0.01:
            # Correct: small confidence boost
            confidence_after = min(1.0, confidence_before + self.CONFIDENCE_ADJUSTMENT_RATE * 0.5)
        else:
            # Incorrect: reduce confidence proportionally to error
            confidence_after = max(0.0, confidence_before - self.CONFIDENCE_ADJUSTMENT_RATE * error_record.absolute_error)

        # Update the error record
        error_record.confidence_after = confidence_after
        await self._save_error_record(error_record)

        # Persist confidence
        self._confidence_map[error_record.prediction_id] = confidence_after
        await self._save_confidence(error_record.prediction_id, confidence_after)

        return confidence_after

    # ─── Core: Update World Model ───────────────────────────────────────────

    async def update_world_model_from_error(
        self,
        error_record: PredictionErrorRecord,
    ) -> bool:
        """Update the world model based on a prediction error.

        Records the correct state transition so future predictions improve.
        Only updates the world model when the prediction was incorrect
        (there's nothing to learn from a correct prediction in terms of
        new transitions).

        Also records the error in the WorldModelEngine's error history
        for uncertainty quantification.

        Args:
            error_record: The error record to process.

        Returns:
            True if the world model was updated, False otherwise.
        """
        source_state = error_record.metadata.get("source_state", "")

        # Record the error in the world model engine's error history
        if self._world_model_engine is not None:
            await self._world_model_engine.record_prediction_error(
                source_state=source_state,
                predicted_state=error_record.predicted_value,
                actual_state=error_record.actual_value,
            )

        # If prediction was correct, no new transition to learn
        if error_record.absolute_error < 0.01:
            error_record.world_model_updated = True
            await self._save_error_record(error_record)
            return True

        # Prediction was wrong: record the correct transition
        if self._world_model_engine is not None and source_state:
            await self._world_model_engine.world_model.observe_transition(
                source_state=source_state,
                target_state=error_record.actual_value,
                action="corrected_from_error",
                confidence=0.7,
            )
            error_record.world_model_updated = True
            await self._save_error_record(error_record)
            return True

        # No world model engine or no source state — can't update
        error_record.world_model_updated = False
        await self._save_error_record(error_record)
        return False

    # ─── Core: Full Learning Cycle ──────────────────────────────────────────

    async def run_learning_cycle(
        self,
        predictions_and_outcomes: list[dict[str, str]],
    ) -> LearningCycleResult:
        """Execute a complete learning cycle over multiple predictions.

        For each (prediction, outcome) pair:
        1. Measure prediction error
        2. Update beliefs from error
        3. Update confidence from error
        4. Update world model from error

        Then aggregate all results into a :class:`LearningCycleResult`.

        Args:
            predictions_and_outcomes: List of dicts with keys
                ``prediction_id`` and ``actual_outcome``.

        Returns:
            A :class:`LearningCycleResult` summarising the cycle.
        """
        cycle_start = time_mod.monotonic()

        total_errors_measured = 0
        total_beliefs_updated = 0
        total_confidence_updates = 0
        total_wm_transitions = 0
        surprise_count = 0
        confirmation_count = 0
        correct_count = 0
        total_error_sum = 0.0

        for entry in predictions_and_outcomes:
            prediction_id = entry.get("prediction_id", "")
            actual_outcome = entry.get("actual_outcome", "")
            if not prediction_id or not actual_outcome:
                continue

            # Step 1: Measure prediction error
            error_record = await self.measure_prediction_error(prediction_id, actual_outcome)
            total_errors_measured += 1
            total_error_sum += error_record.absolute_error

            # Track signals
            if error_record.learning_signal == LearningSignal.SURPRISING:
                surprise_count += 1
            elif error_record.learning_signal == LearningSignal.CONFIRMING:
                confirmation_count += 1
            if error_record.absolute_error < 0.01:
                correct_count += 1

            # Step 2: Update beliefs from error
            updated_belief_ids = await self.update_beliefs_from_error(error_record)
            if updated_belief_ids:
                total_beliefs_updated += len(updated_belief_ids)

            # Step 3: Update confidence from error
            new_confidence = await self.update_confidence_from_error(error_record)
            total_confidence_updates += 1

            # Step 4: Update world model from error
            wm_updated = await self.update_world_model_from_error(error_record)
            if wm_updated and error_record.absolute_error >= 0.01:
                total_wm_transitions += 1

        cycle_end = time_mod.monotonic()
        cycle_time_ms = (cycle_end - cycle_start) * 1000.0

        # Compute aggregate metrics
        avg_error = total_error_sum / total_errors_measured if total_errors_measured > 0 else 0.0
        learning_efficiency = correct_count / total_errors_measured if total_errors_measured > 0 else 0.0

        result = LearningCycleResult(
            prediction_errors_measured=total_errors_measured,
            beliefs_updated=total_beliefs_updated,
            confidence_updates=total_confidence_updates,
            world_model_transitions_learned=total_wm_transitions,
            surprise_count=surprise_count,
            confirmation_count=confirmation_count,
            average_prediction_error=avg_error,
            learning_efficiency=learning_efficiency,
            cycle_time_ms=cycle_time_ms,
        )
        return result

    # ─── Prediction-Belief Association ──────────────────────────────────────

    async def associate_belief_with_prediction(
        self, prediction_id: str, belief_id: str,
    ) -> None:
        """Associate a belief with a prediction for future error attribution.

        When a prediction is later evaluated, the associated beliefs
        will have their confidence adjusted based on the prediction error.

        Args:
            prediction_id: The prediction ID.
            belief_id: The belief ID that supports this prediction.
        """
        if prediction_id not in self._prediction_belief_map:
            self._prediction_belief_map[prediction_id] = []
        if belief_id not in self._prediction_belief_map[prediction_id]:
            self._prediction_belief_map[prediction_id].append(belief_id)
            await self._save_prediction_belief_map(prediction_id, belief_id)

    # ─── Query: Error Statistics ────────────────────────────────────────────

    async def get_prediction_error_stats(self) -> dict[str, Any]:
        """Get aggregate prediction error statistics.

        Returns:
            Dict with error stats including counts by learning signal,
            average errors, learning efficiency, and surprise rate.
        """
        if not self._error_records:
            return {
                "total_errors": 0,
                "correct_count": 0,
                "incorrect_count": 0,
                "partial_count": 0,
                "surprising_count": 0,
                "confirming_count": 0,
                "average_absolute_error": 0.0,
                "average_squared_error": 0.0,
                "learning_efficiency": 0.0,
                "surprise_rate": 0.0,
            }

        signal_counts: dict[str, int] = {}
        total_abs_error = 0.0
        total_sq_error = 0.0
        correct_count = 0

        for record in self._error_records.values():
            key = record.learning_signal.value
            signal_counts[key] = signal_counts.get(key, 0) + 1
            total_abs_error += record.absolute_error
            total_sq_error += record.squared_error
            if record.absolute_error < 0.01:
                correct_count += 1

        total = len(self._error_records)
        avg_abs = total_abs_error / total
        avg_sq = total_sq_error / total
        efficiency = correct_count / total
        surprise_rate = signal_counts.get("surprising", 0) / total

        return {
            "total_errors": total,
            "correct_count": signal_counts.get("correct", 0),
            "incorrect_count": signal_counts.get("incorrect", 0),
            "partial_count": signal_counts.get("partial", 0),
            "surprising_count": signal_counts.get("surprising", 0),
            "confirming_count": signal_counts.get("confirming", 0),
            "average_absolute_error": round(avg_abs, 4),
            "average_squared_error": round(avg_sq, 4),
            "learning_efficiency": round(efficiency, 4),
            "surprise_rate": round(surprise_rate, 4),
        }

    # ─── Private Helpers ────────────────────────────────────────────────────

    def _classify_learning_signal(
        self,
        absolute_error: float,
        confidence_before: float,
    ) -> LearningSignal:
        """Classify the learning signal from a prediction error.

        Classification rules:
        - ``correct``: prediction exactly matched outcome (error ≈ 0)
        - ``confirming``: correct AND confidence was already high
        - ``incorrect``: prediction was wrong (error > 0)
        - ``surprising``: error exceeds surprise threshold
        - ``partial``: ambiguous case

        Args:
            absolute_error: The absolute prediction error.
            confidence_before: Confidence before the outcome was known.

        Returns:
            The classified :class:`LearningSignal`.
        """
        if absolute_error < 0.01:
            # Correct prediction
            if confidence_before >= 0.7:
                return LearningSignal.CONFIRMING
            return LearningSignal.CORRECT
        elif absolute_error >= self._surprise_threshold:
            # Large error — surprising
            return LearningSignal.SURPRISING
        elif absolute_error > 0.0:
            # Wrong but not surprising
            if confidence_before >= 0.7:
                # We were confident but wrong — that's surprising
                return LearningSignal.SURPRISING
            return LearningSignal.INCORRECT
        else:
            return LearningSignal.PARTIAL

    def _build_reflection(
        self,
        predicted_value: str,
        actual_value: str,
        absolute_error: float,
        learning_signal: LearningSignal,
    ) -> str:
        """Build a human-readable reflection for an error record.

        Args:
            predicted_value: What was predicted.
            actual_value: What actually happened.
            absolute_error: The error magnitude.
            learning_signal: The classified signal.

        Returns:
            A reflection string.
        """
        if learning_signal == LearningSignal.CORRECT:
            return f"Prediction '{predicted_value}' matched actual outcome. Confidence reinforced."
        elif learning_signal == LearningSignal.CONFIRMING:
            return f"Prediction '{predicted_value}' confirmed with high confidence. Model validated."
        elif learning_signal == LearningSignal.SURPRISING:
            return (
                f"Surprising outcome: predicted '{predicted_value}' but got '{actual_value}' "
                f"(error={absolute_error:.2f}). Model needs revision."
            )
        elif learning_signal == LearningSignal.INCORRECT:
            return (
                f"Incorrect prediction: expected '{predicted_value}', "
                f"got '{actual_value}' (error={absolute_error:.2f}). Belief adjustment needed."
            )
        else:
            return (
                f"Partial match: predicted '{predicted_value}', "
                f"got '{actual_value}' (error={absolute_error:.2f})."
            )

    # ─── State Access ───────────────────────────────────────────────────────

    async def get_error_record(self, record_id: str) -> PredictionErrorRecord | None:
        """Get a specific error record by ID."""
        return self._error_records.get(record_id)

    async def get_error_records_for_prediction(
        self, prediction_id: str,
    ) -> list[PredictionErrorRecord]:
        """Get all error records for a specific prediction.

        Args:
            prediction_id: The prediction ID.

        Returns:
            List of error records for this prediction.
        """
        return [
            r for r in self._error_records.values()
            if r.prediction_id == prediction_id
        ]

    async def get_stats(self) -> dict[str, Any]:
        """Get active learning loop statistics."""
        error_stats = await self.get_prediction_error_stats()

        # Prediction-belief associations
        total_associations = sum(len(v) for v in self._prediction_belief_map.values())

        # Confidence distribution
        confidence_values = list(self._confidence_map.values())
        avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0

        return {
            "total_error_records": len(self._error_records),
            "total_prediction_belief_associations": total_associations,
            "predictions_with_confidence": len(self._confidence_map),
            "average_confidence": round(avg_confidence, 4),
            "surprise_threshold": self._surprise_threshold,
            "has_world_model_engine": self._world_model_engine is not None,
            "has_belief_system": self._belief_system is not None,
            **error_stats,
        }
