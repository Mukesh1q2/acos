"""
Outcome Predictor — predict action outcomes.

Predicts:
- Success probability
- Failure probability
- Expected duration
- Expected resources

Uses the World Model's transition graph to estimate outcome probabilities
based on observed historical transitions.
"""

from __future__ import annotations

import json
import time as time_mod
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v4_models import (
    OutcomePrediction,
    gen_id,
    utc_now,
)
from acos.cognitive.predictive.state_transition_graph import StateTransitionGraph


class OutcomePredictor:
    """Outcome Predictor — predict the outcomes of actions.

    Usage::

        store = StorageBackend()
        await store.initialize()

        op = OutcomePredictor(store, transition_graph)
        await op.initialize()

        prediction = await op.predict_outcome(
            action="deploy_feature",
            context="production_environment",
            current_state="staging_passed",
        )
        print(f"Success probability: {prediction.success_probability}")
    """

    # How much to discount predictions without direct evidence
    EVIDENCE_DISCOUNT = 0.3

    def __init__(
        self,
        storage: StorageBackend,
        transition_graph: StateTransitionGraph,
    ) -> None:
        self._storage = storage
        self._transition_graph = transition_graph
        self._predictions: dict[str, OutcomePrediction] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load existing predictions."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS outcome_predictions (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                context TEXT DEFAULT '',
                success_probability REAL DEFAULT 0.5,
                failure_probability REAL DEFAULT 0.5,
                partial_success_probability REAL DEFAULT 0.0,
                expected_duration REAL DEFAULT 0.0,
                expected_resources REAL DEFAULT 0.0,
                duration_variance REAL DEFAULT 0.0,
                risk_factors TEXT DEFAULT '[]',
                mitigating_factors TEXT DEFAULT '[]',
                worst_case_outcome TEXT DEFAULT '',
                best_case_outcome TEXT DEFAULT '',
                confidence REAL DEFAULT 0.5,
                supporting_transition_ids TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_op_action
                ON outcome_predictions(action);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        cursor = await conn.execute("SELECT * FROM outcome_predictions")
        rows = await cursor.fetchall()
        for row in rows:
            pred = OutcomePrediction(
                id=row["id"],
                action=row["action"],
                context=row["context"],
                success_probability=row["success_probability"],
                failure_probability=row["failure_probability"],
                partial_success_probability=row["partial_success_probability"],
                expected_duration=row["expected_duration"],
                expected_resources=row["expected_resources"],
                duration_variance=row["duration_variance"],
                risk_factors=json.loads(row["risk_factors"]) if row["risk_factors"] else [],
                mitigating_factors=json.loads(row["mitigating_factors"]) if row["mitigating_factors"] else [],
                worst_case_outcome=row["worst_case_outcome"],
                best_case_outcome=row["best_case_outcome"],
                confidence=row["confidence"],
                supporting_transition_ids=json.loads(row["supporting_transition_ids"]) if row["supporting_transition_ids"] else [],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            self._predictions[pred.id] = pred

    async def _save_prediction(self, prediction: OutcomePrediction) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO outcome_predictions
               (id, action, context, success_probability, failure_probability,
                partial_success_probability, expected_duration, expected_resources,
                duration_variance, risk_factors, mitigating_factors,
                worst_case_outcome, best_case_outcome, confidence,
                supporting_transition_ids, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                prediction.id,
                prediction.action,
                prediction.context,
                prediction.success_probability,
                prediction.failure_probability,
                prediction.partial_success_probability,
                prediction.expected_duration,
                prediction.expected_resources,
                prediction.duration_variance,
                json.dumps(prediction.risk_factors),
                json.dumps(prediction.mitigating_factors),
                prediction.worst_case_outcome,
                prediction.best_case_outcome,
                prediction.confidence,
                json.dumps(prediction.supporting_transition_ids),
                json.dumps(prediction.metadata),
                prediction.created_at.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Core Prediction Methods ────────────────────────────────────────────

    async def predict_outcome(
        self,
        action: str,
        context: str = "",
        current_state: str = "",
    ) -> OutcomePrediction:
        """Predict the outcome of taking an action.

        Uses observed transitions to estimate:
        - Success/failure probabilities
        - Expected duration and resources
        - Risk and mitigating factors

        Args:
            action: The action to predict the outcome for.
            context: Additional context for the action.
            current_state: Current state of the system.

        Returns:
            An OutcomePrediction with all metrics.
        """
        start_time = time_mod.monotonic()

        # Gather evidence from transition graph
        transitions = await self._transition_graph.get_all_transitions()

        # Find transitions matching this action
        matching_transitions = [
            t for t in transitions if t.action == action
        ]

        # Further filter by context if provided
        if context:
            context_terms = set(context.lower().split())
            context_matches = [
                t for t in matching_transitions
                if context_terms & set(t.source_state.lower().split())
                or context_terms & set(t.target_state.lower().split())
                or context_terms & set(str(t.preconditions).lower().split())
            ]
            if context_matches:
                matching_transitions = context_matches

        # Further filter by current state if provided
        if current_state and matching_transitions:
            state_matches = [
                t for t in matching_transitions
                if t.source_state == current_state
            ]
            if state_matches:
                matching_transitions = state_matches

        # Calculate probabilities
        if matching_transitions:
            total_frequency = sum(t.frequency for t in matching_transitions)

            # Successful transitions = those with high confidence
            successful = [t for t in matching_transitions if t.confidence >= 0.6]
            failed = [t for t in matching_transitions if t.confidence < 0.3]
            partial = [t for t in matching_transitions if 0.3 <= t.confidence < 0.6]

            success_freq = sum(t.frequency for t in successful)
            failure_freq = sum(t.frequency for t in failed)
            partial_freq = sum(t.frequency for t in partial)

            success_prob = success_freq / total_frequency if total_frequency > 0 else 0.5
            failure_prob = failure_freq / total_frequency if total_frequency > 0 else 0.3
            partial_prob = partial_freq / total_frequency if total_frequency > 0 else 0.2

            # Normalize to sum to 1.0
            total_prob = success_prob + failure_prob + partial_prob
            if total_prob > 0:
                success_prob /= total_prob
                failure_prob /= total_prob
                partial_prob /= total_prob

            # Expected duration and resources
            expected_duration = (
                sum(t.duration_estimate * t.frequency for t in matching_transitions)
                / total_frequency
            ) if total_frequency > 0 else 0.0

            expected_resources = (
                sum(t.cost * t.frequency for t in matching_transitions)
                / total_frequency
            ) if total_frequency > 0 else 0.0

            # Duration variance
            if len(matching_transitions) > 1:
                mean_dur = expected_duration
                variance = sum(
                    (t.duration_estimate - mean_dur) ** 2 * t.frequency
                    for t in matching_transitions
                ) / total_frequency
            else:
                variance = 0.0

            # Risk and mitigating factors
            risk_factors = []
            mitigating_factors = []
            for t in matching_transitions:
                if t.confidence < 0.5:
                    risk_factors.append(f"Low confidence transition: {t.source_state} -> {t.target_state}")
                for se in t.side_effects:
                    risk_factors.append(f"Side effect: {se}")
                if t.confidence >= 0.8:
                    mitigating_factors.append(f"High confidence: {t.source_state} -> {t.target_state}")
                for pc in t.preconditions:
                    mitigating_factors.append(f"Precondition met: {pc}")

            # Remove duplicates
            risk_factors = list(dict.fromkeys(risk_factors))[:10]
            mitigating_factors = list(dict.fromkeys(mitigating_factors))[:10]

            # Best/worst case
            best_target = max(matching_transitions, key=lambda t: t.confidence).target_state
            worst_target = min(matching_transitions, key=lambda t: t.confidence).target_state

            confidence = min(1.0, len(matching_transitions) * 0.15 + 0.3)
            transition_ids = [t.id for t in matching_transitions[:20]]
        else:
            # No evidence — use priors
            success_prob = 0.4 * self.EVIDENCE_DISCOUNT
            failure_prob = 0.4 * self.EVIDENCE_DISCOUNT
            partial_prob = 1.0 - success_prob - failure_prob
            expected_duration = 0.0
            expected_resources = 0.0
            variance = 0.0
            risk_factors = ["No historical evidence for this action"]
            mitigating_factors = []
            best_target = "unknown"
            worst_target = "unknown"
            confidence = 0.1
            transition_ids = []

        prediction = OutcomePrediction(
            action=action,
            context=context,
            success_probability=round(success_prob, 4),
            failure_probability=round(failure_prob, 4),
            partial_success_probability=round(partial_prob, 4),
            expected_duration=round(expected_duration, 4),
            expected_resources=round(expected_resources, 4),
            duration_variance=round(variance, 4),
            risk_factors=risk_factors,
            mitigating_factors=mitigating_factors,
            worst_case_outcome=worst_target,
            best_case_outcome=best_target,
            confidence=round(confidence, 4),
            supporting_transition_ids=transition_ids,
            metadata={
                "matching_transitions": len(matching_transitions),
                "total_observations": sum(t.frequency for t in matching_transitions) if matching_transitions else 0,
            },
        )
        await self._save_prediction(prediction)
        self._predictions[prediction.id] = prediction
        return prediction

    async def predict_multi_action_outcome(
        self,
        actions: list[str],
        current_state: str = "",
    ) -> list[OutcomePrediction]:
        """Predict outcomes for a sequence of actions.

        Args:
            actions: Ordered list of actions to predict outcomes for.
            current_state: Starting state.

        Returns:
            List of OutcomePrediction, one per action.
        """
        predictions = []
        state = current_state

        for action in actions:
            pred = await self.predict_outcome(
                action=action,
                current_state=state,
            )
            predictions.append(pred)

            # Update the simulated state for the next action
            if state:
                result = await self._transition_graph.get_most_probable_next_state(
                    state, action=action
                )
                if result:
                    state = result[0]

        return predictions

    async def compare_actions(
        self,
        actions: list[str],
        current_state: str = "",
    ) -> list[tuple[str, OutcomePrediction]]:
        """Compare the predicted outcomes of different actions.

        Args:
            actions: List of candidate actions.
            current_state: Current state.

        Returns:
            List of (action, OutcomePrediction) tuples, sorted by success probability.
        """
        results = []
        for action in actions:
            pred = await self.predict_outcome(
                action=action,
                current_state=current_state,
            )
            results.append((action, pred))

        results.sort(key=lambda x: x[1].success_probability, reverse=True)
        return results

    # ─── Access Methods ─────────────────────────────────────────────────────

    async def get_prediction(self, prediction_id: str) -> OutcomePrediction | None:
        """Get a specific prediction."""
        return self._predictions.get(prediction_id)

    async def get_stats(self) -> dict[str, Any]:
        """Get outcome predictor statistics."""
        total = len(self._predictions)
        avg_success = 0.0
        avg_confidence = 0.0

        if total > 0:
            avg_success = sum(p.success_probability for p in self._predictions.values()) / total
            avg_confidence = sum(p.confidence for p in self._predictions.values()) / total

        return {
            "total_predictions": total,
            "avg_success_probability": round(avg_success, 4),
            "avg_confidence": round(avg_confidence, 4),
        }
