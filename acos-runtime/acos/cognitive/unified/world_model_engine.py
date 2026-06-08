"""
World Model Engine — enhanced prediction with risk estimation and uncertainty quantification.

Extends v0.4's WorldModel with:
- Multi-source state transition learning (beliefs, goals, cognitive state, sessions)
- Future state prediction with risk levels and uncertainty
- Action outcome estimation with full risk/uncertainty profile
- Probability estimation across states and actions
- Uncertainty quantification from historical prediction errors
- Risk assessment for goals

The WorldModelEngine WRAPS (not replaces) v0.4's WorldModel — it delegates
core transition learning and prediction to the wrapped instance and adds a
risk/uncertainty estimation layer on top.

Persistence
-----------
All engine-specific state (future predictions, action estimates, risk factors,
uncertainty history) is stored in SQLite tables managed through
:class:`~acos.memory.store.StorageBackend`.
"""

from __future__ import annotations

import json
import math
import time as time_mod
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.cognitive.predictive.world_model import WorldModel
from acos.schemas.v5_models import (
    ActionOutcomeEstimate,
    FutureStatePrediction,
    RiskLevel,
    gen_id,
    utc_now,
)
from acos.schemas.v4_models import (
    Prediction,
    StateTransition,
    gen_id as v4_gen_id,
    utc_now as v4_utc_now,
)


class WorldModelEngine:
    """World Model Engine — enhanced prediction with risk and uncertainty.

    Wraps v0.4's :class:`WorldModel` and adds:
    - Risk estimation layer on top of predictions
    - Uncertainty tracking from historical prediction errors
    - Multi-source learning (beliefs, goals, cognitive state, sessions)
    - Probability and risk assessment queries

    Usage::

        store = StorageBackend()
        await store.initialize()

        wm = WorldModel(store)
        await wm.initialize()

        engine = WorldModelEngine(store, world_model=wm)
        await engine.initialize()

        # Learn from multiple sources
        await engine.learn_state_transitions(
            beliefs=[...], goals=[...],
            cognitive_state=..., sessions=[...],
        )

        # Predict with risk/uncertainty
        prediction = await engine.predict_future_state("learning", time_horizon=300.0)

        # Estimate action outcome
        estimate = await engine.estimate_action_outcome("learning", "take_test")
    """

    # Minimum number of verified predictions before we trust uncertainty estimates
    MIN_SAMPLES_FOR_UNCERTAINTY = 3
    # Default uncertainty when insufficient data
    DEFAULT_UNCERTAINTY = 0.5
    # Temporal decay factor (same as WorldModel for consistency)
    TEMPORAL_DECAY = 0.9
    # Risk thresholds: probability below these triggers risk level escalation
    RISK_THRESHOLD_MEDIUM = 0.7
    RISK_THRESHOLD_HIGH = 0.4
    RISK_THRESHOLD_CRITICAL = 0.2

    def __init__(
        self,
        storage: StorageBackend,
        world_model: WorldModel | None = None,
    ) -> None:
        self._storage = storage
        self._world_model = world_model or WorldModel(storage)
        self._future_predictions: dict[str, FutureStatePrediction] = {}
        self._action_estimates: dict[str, ActionOutcomeEstimate] = {}
        # Track historical prediction errors for uncertainty quantification
        # Key: source_state -> list of (predicted_state, actual_state, error)
        self._error_history: dict[str, list[tuple[str, str, float]]] = {}
        # In-memory risk factor registry per goal
        self._goal_risk_factors: dict[str, list[str]] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize the engine: ensure WorldModel is ready, create tables, load state."""
        await self._world_model.initialize()
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS wme_future_predictions (
                id TEXT PRIMARY KEY,
                predicted_state TEXT NOT NULL,
                probability REAL DEFAULT 0.5,
                confidence REAL DEFAULT 0.5,
                risk_level TEXT NOT NULL DEFAULT 'medium',
                risk_factors TEXT DEFAULT '[]',
                time_horizon_seconds REAL DEFAULT 0.0,
                assumptions TEXT DEFAULT '[]',
                reasoning_chain TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wme_action_estimates (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                expected_outcome TEXT DEFAULT '',
                success_probability REAL DEFAULT 0.5,
                failure_probability REAL DEFAULT 0.5,
                uncertainty REAL DEFAULT 0.5,
                expected_duration REAL DEFAULT 0.0,
                expected_cost REAL DEFAULT 0.0,
                risk_factors TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.5,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wme_error_history (
                id TEXT PRIMARY KEY,
                source_state TEXT NOT NULL,
                predicted_state TEXT NOT NULL,
                actual_state TEXT NOT NULL,
                error REAL NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wme_goal_risk_factors (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                risk_factor TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_wme_fp_state
                ON wme_future_predictions(predicted_state);
            CREATE INDEX IF NOT EXISTS idx_wme_ae_action
                ON wme_action_estimates(action);
            CREATE INDEX IF NOT EXISTS idx_wme_eh_source
                ON wme_error_history(source_state);
            CREATE INDEX IF NOT EXISTS idx_wme_grf_goal
                ON wme_goal_risk_factors(goal_id);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        assert conn is not None

        # Load future predictions
        cursor = await conn.execute("SELECT * FROM wme_future_predictions")
        rows = await cursor.fetchall()
        for row in rows:
            fp = FutureStatePrediction(
                id=row["id"],
                predicted_state=row["predicted_state"],
                probability=row["probability"],
                confidence=row["confidence"],
                risk_level=RiskLevel(row["risk_level"]),
                risk_factors=json.loads(row["risk_factors"]) if row["risk_factors"] else [],
                time_horizon_seconds=row["time_horizon_seconds"],
                assumptions=json.loads(row["assumptions"]) if row["assumptions"] else [],
                reasoning_chain=json.loads(row["reasoning_chain"]) if row["reasoning_chain"] else [],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            self._future_predictions[fp.id] = fp

        # Load action estimates
        cursor = await conn.execute("SELECT * FROM wme_action_estimates")
        rows = await cursor.fetchall()
        for row in rows:
            ae = ActionOutcomeEstimate(
                id=row["id"],
                action=row["action"],
                expected_outcome=row["expected_outcome"],
                success_probability=row["success_probability"],
                failure_probability=row["failure_probability"],
                uncertainty=row["uncertainty"],
                expected_duration=row["expected_duration"],
                expected_cost=row["expected_cost"],
                risk_factors=json.loads(row["risk_factors"]) if row["risk_factors"] else [],
                confidence=row["confidence"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            self._action_estimates[ae.id] = ae

        # Load error history
        cursor = await conn.execute("SELECT * FROM wme_error_history")
        rows = await cursor.fetchall()
        for row in rows:
            source = row["source_state"]
            if source not in self._error_history:
                self._error_history[source] = []
            self._error_history[source].append((
                row["predicted_state"],
                row["actual_state"],
                row["error"],
            ))

        # Load goal risk factors
        cursor = await conn.execute("SELECT * FROM wme_goal_risk_factors")
        rows = await cursor.fetchall()
        for row in rows:
            goal_id = row["goal_id"]
            if goal_id not in self._goal_risk_factors:
                self._goal_risk_factors[goal_id] = []
            self._goal_risk_factors[goal_id].append(row["risk_factor"])

    # ─── Persistence helpers ────────────────────────────────────────────────

    async def _save_future_prediction(self, fp: FutureStatePrediction) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO wme_future_predictions
               (id, predicted_state, probability, confidence, risk_level,
                risk_factors, time_horizon_seconds, assumptions,
                reasoning_chain, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fp.id,
                fp.predicted_state,
                fp.probability,
                fp.confidence,
                fp.risk_level.value,
                json.dumps(fp.risk_factors),
                fp.time_horizon_seconds,
                json.dumps(fp.assumptions),
                json.dumps(fp.reasoning_chain),
                json.dumps(fp.metadata),
                fp.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_action_estimate(self, ae: ActionOutcomeEstimate) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO wme_action_estimates
               (id, action, expected_outcome, success_probability,
                failure_probability, uncertainty, expected_duration,
                expected_cost, risk_factors, confidence, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ae.id,
                ae.action,
                ae.expected_outcome,
                ae.success_probability,
                ae.failure_probability,
                ae.uncertainty,
                ae.expected_duration,
                ae.expected_cost,
                json.dumps(ae.risk_factors),
                ae.confidence,
                json.dumps(ae.metadata),
                ae.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_error_entry(
        self, source_state: str, predicted_state: str, actual_state: str, error: float,
    ) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        entry_id = gen_id()
        await conn.execute(
            """INSERT INTO wme_error_history
               (id, source_state, predicted_state, actual_state, error, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                entry_id,
                source_state,
                predicted_state,
                actual_state,
                error,
                utc_now().isoformat(),
            ),
        )
        await conn.commit()

    async def _save_goal_risk_factor(self, goal_id: str, risk_factor: str) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        entry_id = gen_id()
        await conn.execute(
            """INSERT INTO wme_goal_risk_factors
               (id, goal_id, risk_factor, created_at)
               VALUES (?, ?, ?, ?)""",
            (entry_id, goal_id, risk_factor, utc_now().isoformat()),
        )
        await conn.commit()

    # ─── Multi-source Learning ──────────────────────────────────────────────

    async def learn_state_transitions(
        self,
        beliefs: list[dict[str, Any]] | None = None,
        goals: list[dict[str, Any]] | None = None,
        cognitive_state: dict[str, Any] | None = None,
        sessions: list[dict[str, Any]] | None = None,
    ) -> list[StateTransition]:
        """Learn state transitions from multiple cognitive sources.

        Each source is mapped to state transitions and fed to the wrapped
        WorldModel.  Belief changes become belief-state transitions, goal
        progress becomes goal-state transitions, cognitive state shifts are
        recorded as holistic transitions, and session-to-session changes
        capture macro-level dynamics.

        Args:
            beliefs: List of belief dicts with keys ``id``, ``old_confidence``,
                ``new_confidence``, ``cause``.
            goals: List of goal dicts with keys ``id``, ``old_progress``,
                ``new_progress``.
            cognitive_state: Dict describing current cognitive state with keys
                ``label``, ``previous_label``, ``cause``.
            sessions: List of session dicts with keys ``id``, ``previous_state``,
                ``current_state``, ``action``.

        Returns:
            All StateTransition objects recorded during this learning step.
        """
        transitions: list[StateTransition] = []

        # Learn from belief changes
        if beliefs:
            for b in beliefs:
                t = await self._world_model.learn_from_belief_change(
                    belief_id=b.get("id", ""),
                    old_confidence=b.get("old_confidence", 0.5),
                    new_confidence=b.get("new_confidence", 0.5),
                    cause=b.get("cause", ""),
                )
                if t is not None:
                    transitions.append(t)

        # Learn from goal progress
        if goals:
            for g in goals:
                t = await self._world_model.learn_from_goal_progress(
                    goal_id=g.get("id", ""),
                    old_progress=g.get("old_progress", 0.0),
                    new_progress=g.get("new_progress", 0.0),
                )
                if t is not None:
                    transitions.append(t)

        # Learn from cognitive state transition
        if cognitive_state:
            label = cognitive_state.get("label", "")
            previous_label = cognitive_state.get("previous_label", "")
            cause = cognitive_state.get("cause", "")
            if label and previous_label and label != previous_label:
                t = await self._world_model.observe_transition(
                    source_state=previous_label,
                    target_state=label,
                    action=cause or "cognitive_shift",
                    confidence=0.7,
                )
                transitions.append(t)

        # Learn from session-level transitions
        if sessions:
            for s in sessions:
                prev = s.get("previous_state", "")
                curr = s.get("current_state", "")
                action = s.get("action", "")
                if prev and curr and prev != curr:
                    t = await self._world_model.observe_transition(
                        source_state=prev,
                        target_state=curr,
                        action=action or "session_transition",
                        confidence=0.6,
                    )
                    transitions.append(t)

        return transitions

    # ─── Prediction with Risk/Uncertainty ───────────────────────────────────

    async def predict_future_state(
        self,
        current_state: str,
        time_horizon: float = 0.0,
    ) -> FutureStatePrediction:
        """Predict a future state with risk and uncertainty estimation.

        Delegates core prediction to the wrapped WorldModel and then
        enriches the result with:
        - Risk level based on prediction confidence and historical errors
        - Risk factors derived from error history and state uncertainty
        - Uncertainty-adjusted confidence

        Args:
            current_state: Current state label.
            time_horizon: How far into the future to predict (seconds).

        Returns:
            A :class:`FutureStatePrediction` with risk and uncertainty.
        """
        start_time = time_mod.monotonic()

        # Delegate core prediction to wrapped WorldModel
        base_prediction = await self._world_model.predict_next_state(
            current_state=current_state,
            time_horizon=time_horizon,
        )

        # Compute uncertainty from historical errors for this source state
        uncertainty = await self.estimate_uncertainty(base_prediction.id)

        # Determine risk level based on probability and uncertainty
        probability = base_prediction.probability
        risk_level = self._classify_risk(probability, uncertainty)

        # Derive risk factors
        risk_factors = self._derive_risk_factors(
            current_state=current_state,
            predicted_state=base_prediction.predicted_state,
            probability=probability,
            uncertainty=uncertainty,
            time_horizon=time_horizon,
        )

        # Adjusted confidence: penalised by uncertainty
        adjusted_confidence = max(0.0, base_prediction.confidence * (1.0 - uncertainty * 0.5))

        # Build reasoning chain
        reasoning_chain = list(base_prediction.reasoning_chain)
        reasoning_chain.append(f"Uncertainty estimate: {uncertainty:.3f}")
        reasoning_chain.append(f"Risk level: {risk_level.value}")
        if risk_factors:
            reasoning_chain.append(f"Risk factors: {risk_factors}")

        prediction = FutureStatePrediction(
            predicted_state=base_prediction.predicted_state,
            probability=probability,
            confidence=adjusted_confidence,
            risk_level=risk_level,
            risk_factors=risk_factors,
            time_horizon_seconds=time_horizon,
            assumptions=list(base_prediction.assumptions),
            reasoning_chain=reasoning_chain,
            metadata={
                "base_prediction_id": base_prediction.id,
                "base_confidence": base_prediction.confidence,
                "uncertainty": uncertainty,
            },
        )
        await self._save_future_prediction(prediction)
        self._future_predictions[prediction.id] = prediction
        return prediction

    async def estimate_action_outcome(
        self,
        current_state: str,
        action: str,
    ) -> ActionOutcomeEstimate:
        """Estimate the outcome of taking an action with full risk/uncertainty profile.

        Delegates core prediction to the wrapped WorldModel and enriches
        with success/failure probabilities, expected cost, duration,
        uncertainty, and risk factors.

        Args:
            current_state: Current state label.
            action: The action to evaluate.

        Returns:
            An :class:`ActionOutcomeEstimate` with risk and uncertainty.
        """
        # Delegate core prediction to wrapped WorldModel
        base_prediction = await self._world_model.predict_action_outcome(
            current_state=current_state,
            action=action,
        )

        probability = base_prediction.probability
        success_probability = probability
        failure_probability = 1.0 - probability

        # Estimate uncertainty from error history for this source state
        uncertainty = await self._compute_state_uncertainty(current_state)

        # Estimate expected duration and cost from transition data
        expected_duration = 0.0
        expected_cost = 0.0
        transitions = await self._world_model.transition_graph.get_transitions_from(current_state)
        action_transitions = [t for t in transitions if t.action == action]
        if action_transitions:
            expected_duration = sum(t.duration_estimate for t in action_transitions) / len(action_transitions)
            expected_cost = sum(t.cost for t in action_transitions) / len(action_transitions)

        # Risk factors for this action
        risk_factors = self._derive_action_risk_factors(
            current_state=current_state,
            action=action,
            probability=probability,
            uncertainty=uncertainty,
            expected_cost=expected_cost,
        )

        # Adjusted confidence incorporating uncertainty
        adjusted_confidence = max(0.0, base_prediction.confidence * (1.0 - uncertainty * 0.5))

        estimate = ActionOutcomeEstimate(
            action=action,
            expected_outcome=base_prediction.predicted_state,
            success_probability=success_probability,
            failure_probability=failure_probability,
            uncertainty=uncertainty,
            expected_duration=expected_duration,
            expected_cost=expected_cost,
            risk_factors=risk_factors,
            confidence=adjusted_confidence,
            metadata={
                "base_prediction_id": base_prediction.id,
                "base_confidence": base_prediction.confidence,
                "source_state": current_state,
            },
        )
        await self._save_action_estimate(estimate)
        self._action_estimates[estimate.id] = estimate
        return estimate

    async def estimate_probabilities(
        self,
        states: list[str],
        actions: list[str],
    ) -> dict[str, float]:
        """Estimate transition probabilities for state-action pairs.

        For each (state, action) combination, computes the probability
        of the most likely next state using the underlying WorldModel's
        transition graph.

        Args:
            states: List of source state labels.
            actions: List of action labels.

        Returns:
            Dict mapping ``"state:action"`` keys to probability floats.
        """
        result: dict[str, float] = {}
        for state in states:
            for action in actions:
                prob = await self._world_model.transition_graph.compute_transition_probability(
                    source_state=state,
                    target_state=state,  # default target = self (no change)
                    action=action,
                )
                # Find the most probable next state for this (state, action)
                next_result = await self._world_model.transition_graph.get_most_probable_next_state(
                    state, action=action,
                )
                if next_result is not None:
                    _, best_prob = next_result
                    key = f"{state}:{action}"
                    result[key] = best_prob
                else:
                    key = f"{state}:{action}"
                    result[key] = 0.0
        return result

    async def estimate_uncertainty(self, prediction_id: str) -> float:
        """Quantify uncertainty for a prediction based on historical errors.

        Uses the mean absolute error of past predictions from the same
        source state to estimate how uncertain the current prediction is.
        If insufficient data is available, returns the default uncertainty.

        Args:
            prediction_id: ID of the prediction to assess.

        Returns:
            Uncertainty value in [0.0, 1.0].
        """
        # Look up the base prediction in the wrapped WorldModel
        base_prediction = await self._world_model.get_prediction(prediction_id)
        if base_prediction is None:
            # Try our own future predictions
            fp = self._future_predictions.get(prediction_id)
            if fp is not None and "source_state" in fp.metadata:
                source_state = fp.metadata["source_state"]
            else:
                return self.DEFAULT_UNCERTAINTY
        else:
            source_state = base_prediction.source_state

        return await self._compute_state_uncertainty(source_state)

    async def _compute_state_uncertainty(self, source_state: str) -> float:
        """Compute uncertainty from historical errors for a given source state.

        Args:
            source_state: The source state to compute uncertainty for.

        Returns:
            Uncertainty value in [0.0, 1.0].
        """
        errors = self._error_history.get(source_state, [])

        # Also check verified predictions from the WorldModel
        all_preds = await self._world_model.get_predictions()
        verified_from_state = [
            p for p in all_preds
            if p.source_state == source_state and p.is_verified and p.prediction_error is not None
        ]

        all_errors: list[float] = [e[2] for e in errors]
        all_errors.extend(p.prediction_error for p in verified_from_state if p.prediction_error is not None)

        if len(all_errors) < self.MIN_SAMPLES_FOR_UNCERTAINTY:
            # Not enough data: use the default, slightly reduced by whatever we have
            if all_errors:
                # Weighted blend: 70% default, 30% observed
                mean_err = sum(all_errors) / len(all_errors)
                return 0.7 * self.DEFAULT_UNCERTAINTY + 0.3 * mean_err
            return self.DEFAULT_UNCERTAINTY

        mean_error = sum(all_errors) / len(all_errors)
        return min(1.0, mean_error)

    def get_risk_assessment(self, goal_id: str) -> list[str]:
        """Get risk factors for a goal.

        Risk factors come from two sources:
        1. Explicitly registered risk factors (from goal analysis)
        2. Inferred risk factors from the goal's target state uncertainty

        Args:
            goal_id: The goal to assess risks for.

        Returns:
            List of risk factor strings.
        """
        factors = list(self._goal_risk_factors.get(goal_id, []))
        return factors

    # ─── Risk Factor Registration ───────────────────────────────────────────

    async def register_goal_risk_factor(
        self, goal_id: str, risk_factor: str,
    ) -> None:
        """Register a risk factor for a goal.

        Args:
            goal_id: The goal ID.
            risk_factor: Description of the risk factor.
        """
        if goal_id not in self._goal_risk_factors:
            self._goal_risk_factors[goal_id] = []
        if risk_factor not in self._goal_risk_factors[goal_id]:
            self._goal_risk_factors[goal_id].append(risk_factor)
            await self._save_goal_risk_factor(goal_id, risk_factor)

    # ─── Error Recording ────────────────────────────────────────────────────

    async def record_prediction_error(
        self,
        source_state: str,
        predicted_state: str,
        actual_state: str,
    ) -> None:
        """Record a prediction error for future uncertainty estimation.

        Args:
            source_state: The state from which the prediction was made.
            predicted_state: The state that was predicted.
            actual_state: The state that actually occurred.
        """
        error = 0.0 if predicted_state == actual_state else 1.0
        if source_state not in self._error_history:
            self._error_history[source_state] = []
        self._error_history[source_state].append((predicted_state, actual_state, error))
        await self._save_error_entry(source_state, predicted_state, actual_state, error)

    # ─── Private Helpers ────────────────────────────────────────────────────

    def _classify_risk(self, probability: float, uncertainty: float) -> RiskLevel:
        """Classify risk level based on probability and uncertainty.

        A combined score factors in both the direct probability and the
        uncertainty amplification: low probability + high uncertainty →
        higher risk.

        Args:
            probability: Predicted probability.
            uncertainty: Estimated uncertainty.

        Returns:
            RiskLevel enum value.
        """
        # Combined risk score: lower probability and higher uncertainty → higher risk
        risk_score = (1.0 - probability) * 0.6 + uncertainty * 0.4

        if risk_score >= 0.8:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            return RiskLevel.HIGH
        elif risk_score >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _derive_risk_factors(
        self,
        current_state: str,
        predicted_state: str,
        probability: float,
        uncertainty: float,
        time_horizon: float,
    ) -> list[str]:
        """Derive risk factors for a future state prediction.

        Args:
            current_state: Starting state.
            predicted_state: Predicted state.
            probability: Prediction probability.
            uncertainty: Uncertainty estimate.
            time_horizon: How far into the future.

        Returns:
            List of risk factor strings.
        """
        factors: list[str] = []

        if probability < 0.3:
            factors.append("Low prediction probability")
        if uncertainty > 0.6:
            factors.append("High historical uncertainty for this state")
        if time_horizon > 300:
            factors.append("Long time horizon increases prediction decay")
        if current_state == predicted_state:
            factors.append("No state change predicted (stasis risk)")

        # Check error history for this source state
        errors = self._error_history.get(current_state, [])
        if errors:
            recent_errors = errors[-5:]  # Last 5
            wrong_count = sum(1 for _, _, e in recent_errors if e > 0.5)
            if wrong_count >= 3:
                factors.append("Frequent recent prediction errors for this state")

        return factors

    def _derive_action_risk_factors(
        self,
        current_state: str,
        action: str,
        probability: float,
        uncertainty: float,
        expected_cost: float,
    ) -> list[str]:
        """Derive risk factors for an action outcome estimate.

        Args:
            current_state: Starting state.
            action: The action being evaluated.
            probability: Success probability.
            uncertainty: Uncertainty estimate.
            expected_cost: Expected resource cost.

        Returns:
            List of risk factor strings.
        """
        factors: list[str] = []

        if probability < 0.3:
            factors.append(f"Low success probability for action '{action}'")
        if uncertainty > 0.6:
            factors.append("High uncertainty in outcome estimation")
        if expected_cost > 5.0:
            factors.append("High expected resource cost")
        if probability < 0.5 and expected_cost > 2.0:
            factors.append("Poor risk/reward ratio: low probability with significant cost")

        # Check error history
        errors = self._error_history.get(current_state, [])
        if errors:
            recent_errors = errors[-5:]
            wrong_count = sum(1 for _, _, e in recent_errors if e > 0.5)
            if wrong_count >= 3:
                factors.append("Unreliable prediction history for this state")

        return factors

    # ─── State Access ───────────────────────────────────────────────────────

    @property
    def world_model(self) -> WorldModel:
        """Access the wrapped v0.4 WorldModel."""
        return self._world_model

    async def get_future_prediction(self, prediction_id: str) -> FutureStatePrediction | None:
        """Get a specific future state prediction by ID."""
        return self._future_predictions.get(prediction_id)

    async def get_action_estimate(self, estimate_id: str) -> ActionOutcomeEstimate | None:
        """Get a specific action outcome estimate by ID."""
        return self._action_estimates.get(estimate_id)

    async def get_stats(self) -> dict[str, Any]:
        """Get WorldModelEngine statistics."""
        wm_stats = await self._world_model.get_stats()

        # Aggregate risk levels
        risk_counts: dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for fp in self._future_predictions.values():
            risk_counts[fp.risk_level.value] = risk_counts.get(fp.risk_level.value, 0) + 1

        # Average uncertainty across states with error history
        avg_uncertainty = 0.0
        if self._error_history:
            state_uncertainties = []
            for state in self._error_history:
                errors = self._error_history[state]
                if errors:
                    mean_err = sum(e[2] for e in errors) / len(errors)
                    state_uncertainties.append(mean_err)
            if state_uncertainties:
                avg_uncertainty = sum(state_uncertainties) / len(state_uncertainties)

        return {
            "total_future_predictions": len(self._future_predictions),
            "total_action_estimates": len(self._action_estimates),
            "total_error_entries": sum(len(v) for v in self._error_history.values()),
            "states_with_error_history": len(self._error_history),
            "average_uncertainty": round(avg_uncertainty, 4),
            "risk_level_distribution": risk_counts,
            "goals_with_risk_assessment": len(self._goal_risk_factors),
            "world_model": wm_stats,
        }
