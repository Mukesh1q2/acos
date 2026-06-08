"""
World Model — learn state transitions and predict future states.

Responsibilities:
- Learn state transitions from observations
- Predict future states
- Predict action outcomes
- Predict goal completion probability

Builds on StateTransitionGraph to maintain a model of how the world
(i.e., the cognitive system) evolves over time.
"""

from __future__ import annotations

import json
import time as time_mod
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v4_models import (
    Prediction,
    PredictionType,
    StateTransition,
    StateVector,
    WorldModelState,
    TransitionType,
    gen_id,
    utc_now,
)
from acos.cognitive.predictive.state_transition_graph import StateTransitionGraph


class WorldModel:
    """World Model — learn dynamics and predict future states.

    Usage::

        store = StorageBackend()
        await store.initialize()

        wm = WorldModel(store)
        await wm.initialize()

        # Learn from an observation
        await wm.observe_transition("idle", "learning", action="start_study")

        # Predict the future
        prediction = await wm.predict_next_state("learning", action="take_test")

        # Predict goal completion
        prob = await wm.predict_goal_completion("master_python", current_state="learning")
    """

    # How much to trust observed transitions vs priors
    LEARNING_RATE = 0.15
    # Minimum confidence to make a prediction
    MIN_PREDICTION_CONFIDENCE = 0.1
    # Decay factor for prediction accuracy over time horizon
    TEMPORAL_DECAY = 0.9

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._transition_graph = StateTransitionGraph(storage)
        self._predictions: dict[str, Prediction] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize the world model and its transition graph."""
        await self._transition_graph.initialize()
        await self._create_tables()
        await self._load_predictions()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                prediction_type TEXT NOT NULL,
                description TEXT NOT NULL,
                source_state TEXT DEFAULT '',
                predicted_state TEXT DEFAULT '',
                action TEXT DEFAULT '',
                goal_id TEXT,
                confidence REAL DEFAULT 0.5,
                time_horizon REAL DEFAULT 0.0,
                probability REAL DEFAULT 0.5,
                transition_ids TEXT DEFAULT '[]',
                assumptions TEXT DEFAULT '[]',
                reasoning_chain TEXT DEFAULT '[]',
                is_verified INTEGER DEFAULT 0,
                actual_outcome TEXT,
                prediction_error REAL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                verified_at TEXT
            );

            CREATE TABLE IF NOT EXISTS world_model_state (
                id TEXT PRIMARY KEY,
                total_transitions INTEGER DEFAULT 0,
                total_predictions INTEGER DEFAULT 0,
                verified_predictions INTEGER DEFAULT 0,
                average_prediction_accuracy REAL DEFAULT 0.0,
                model_confidence REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_pred_type
                ON predictions(prediction_type);
            CREATE INDEX IF NOT EXISTS idx_pred_source
                ON predictions(source_state);
            CREATE INDEX IF NOT EXISTS idx_pred_goal
                ON predictions(goal_id);
        """)
        await conn.commit()

    async def _load_predictions(self) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        cursor = await conn.execute("SELECT * FROM predictions")
        rows = await cursor.fetchall()
        for row in rows:
            pred = Prediction(
                id=row["id"],
                prediction_type=PredictionType(row["prediction_type"]),
                description=row["description"],
                source_state=row["source_state"],
                predicted_state=row["predicted_state"],
                action=row["action"],
                goal_id=row["goal_id"],
                confidence=row["confidence"],
                time_horizon=row["time_horizon"],
                probability=row["probability"],
                transition_ids=json.loads(row["transition_ids"]) if row["transition_ids"] else [],
                assumptions=json.loads(row["assumptions"]) if row["assumptions"] else [],
                reasoning_chain=json.loads(row["reasoning_chain"]) if row["reasoning_chain"] else [],
                is_verified=bool(row["is_verified"]),
                actual_outcome=row["actual_outcome"],
                prediction_error=row["prediction_error"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
                verified_at=datetime.fromisoformat(row["verified_at"]) if row["verified_at"] else None,
            )
            self._predictions[pred.id] = pred

    async def _save_prediction(self, prediction: Prediction) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO predictions
               (id, prediction_type, description, source_state, predicted_state,
                action, goal_id, confidence, time_horizon, probability,
                transition_ids, assumptions, reasoning_chain, is_verified,
                actual_outcome, prediction_error, metadata, created_at, verified_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                prediction.id,
                prediction.prediction_type.value,
                prediction.description,
                prediction.source_state,
                prediction.predicted_state,
                prediction.action,
                prediction.goal_id,
                prediction.confidence,
                prediction.time_horizon,
                prediction.probability,
                json.dumps(prediction.transition_ids),
                json.dumps(prediction.assumptions),
                json.dumps(prediction.reasoning_chain),
                int(prediction.is_verified),
                prediction.actual_outcome,
                prediction.prediction_error,
                json.dumps(prediction.metadata),
                prediction.created_at.isoformat(),
                prediction.verified_at.isoformat() if prediction.verified_at else None,
            ),
        )
        await conn.commit()

    # ─── Learning ───────────────────────────────────────────────────────────

    async def observe_transition(
        self,
        source_state: str,
        target_state: str,
        action: str = "",
        confidence: float = 0.8,
        cost: float = 0.0,
        duration: float = 0.0,
        preconditions: list[str] | None = None,
        side_effects: list[str] | None = None,
    ) -> StateTransition:
        """Observe a state transition and learn from it.

        This is the primary learning mechanism: the World Model records
        what it observes and updates its internal transition graph.

        Args:
            source_state: The state before the transition.
            target_state: The state after the transition.
            action: The action that triggered the transition.
            confidence: Confidence in this observation.
            cost: Resource cost of the transition.
            duration: How long the transition took.
            preconditions: Required preconditions.
            side_effects: Observed side effects.

        Returns:
            The recorded StateTransition.
        """
        transition = await self._transition_graph.record_transition(
            source_state=source_state,
            target_state=target_state,
            action=action,
            confidence=confidence,
            cost=cost,
            duration_estimate=duration,
            preconditions=preconditions,
            side_effects=side_effects,
        )
        return transition

    async def learn_from_belief_change(
        self,
        belief_id: str,
        old_confidence: float,
        new_confidence: float,
        cause: str = "",
    ) -> StateTransition | None:
        """Learn from a belief confidence change.

        Models belief state transitions as state changes.

        Args:
            belief_id: The belief that changed.
            old_confidence: Previous confidence.
            new_confidence: New confidence.
            cause: What caused the change.

        Returns:
            The recorded transition, or None.
        """
        source = f"belief_{belief_id}_conf_{old_confidence:.2f}"
        target = f"belief_{belief_id}_conf_{new_confidence:.2f}"

        if old_confidence > new_confidence:
            action = cause or "weakened"
        elif new_confidence > old_confidence:
            action = cause or "reinforced"
        else:
            return None  # No change

        return await self.observe_transition(
            source_state=source,
            target_state=target,
            action=action,
            confidence=0.7,
        )

    async def learn_from_goal_progress(
        self,
        goal_id: str,
        old_progress: float,
        new_progress: float,
    ) -> StateTransition | None:
        """Learn from a goal progress change.

        Args:
            goal_id: The goal that progressed.
            old_progress: Previous progress.
            new_progress: New progress.

        Returns:
            The recorded transition, or None.
        """
        if abs(old_progress - new_progress) < 0.001:
            return None

        source = f"goal_{goal_id}_prog_{old_progress:.2f}"
        target = f"goal_{goal_id}_prog_{new_progress:.2f}"
        action = "advanced" if new_progress > old_progress else "regressed"

        return await self.observe_transition(
            source_state=source,
            target_state=target,
            action=action,
            confidence=0.8,
        )

    # ─── Prediction ─────────────────────────────────────────────────────────

    async def predict_next_state(
        self,
        current_state: str,
        action: str = "",
        time_horizon: float = 0.0,
    ) -> Prediction:
        """Predict the next state from the current state.

        Uses the transition graph to find the most probable next state.

        Args:
            current_state: Current state label.
            action: Optional action to consider.
            time_horizon: How far into the future to predict.

        Returns:
            A Prediction about the next state.
        """
        start_time = time_mod.monotonic()

        result = await self._transition_graph.get_most_probable_next_state(
            current_state, action=action
        )

        reasoning_chain = [
            f"Current state: {current_state}",
            f"Action considered: {action or 'any'}",
        ]

        if result:
            predicted_state, probability = result
            reasoning_chain.append(
                f"Most probable next state: {predicted_state} (p={probability:.3f})"
            )
            confidence = probability
            transition_ids = []
            # Find the matching transition
            transitions = await self._transition_graph.get_transitions_from(current_state)
            for t in transitions:
                if t.target_state == predicted_state:
                    if not action or t.action == action:
                        transition_ids.append(t.id)
                        break
        else:
            predicted_state = current_state  # Default: stay in current state
            probability = 0.0
            confidence = self.MIN_PREDICTION_CONFIDENCE
            transition_ids = []
            reasoning_chain.append(
                "No observed transitions from this state — predicting no change"
            )

        # Apply temporal decay
        if time_horizon > 0:
            decayed_probability = probability * (self.TEMPORAL_DECAY ** (time_horizon / 60.0))
            confidence *= (self.TEMPORAL_DECAY ** (time_horizon / 60.0))
            reasoning_chain.append(
                f"Temporal decay applied for horizon {time_horizon}s"
            )
            probability = decayed_probability

        description = (
            f"From '{current_state}' with action '{action or 'any'}', "
            f"predict transition to '{predicted_state}' (p={probability:.3f})"
        )

        prediction = Prediction(
            prediction_type=PredictionType.STATE_PREDICTION,
            description=description,
            source_state=current_state,
            predicted_state=predicted_state,
            action=action,
            confidence=max(confidence, self.MIN_PREDICTION_CONFIDENCE),
            time_horizon=time_horizon,
            probability=probability,
            transition_ids=transition_ids,
            reasoning_chain=reasoning_chain,
            assumptions=["Transition graph is representative of future dynamics"],
        )
        await self._save_prediction(prediction)
        self._predictions[prediction.id] = prediction
        return prediction

    async def predict_action_outcome(
        self,
        current_state: str,
        action: str,
        time_horizon: float = 0.0,
    ) -> Prediction:
        """Predict the outcome of taking a specific action.

        Args:
            current_state: Current state label.
            action: The action to predict the outcome for.
            time_horizon: How far into the future.

        Returns:
            A Prediction about the action outcome.
        """
        start_time = time_mod.monotonic()

        transitions = await self._transition_graph.get_transitions_from(current_state)
        action_transitions = [t for t in transitions if t.action == action]

        reasoning_chain = [
            f"Current state: {current_state}",
            f"Action: {action}",
            f"Found {len(action_transitions)} observed transition(s) for this action",
        ]

        if action_transitions:
            # Aggregate possible outcomes
            total_frequency = sum(t.frequency for t in action_transitions)
            outcomes: dict[str, float] = {}
            transition_ids: list[str] = []

            for t in action_transitions:
                prob = t.frequency / total_frequency if total_frequency > 0 else 0.0
                outcomes[t.target_state] = outcomes.get(t.target_state, 0.0) + prob
                transition_ids.append(t.id)

            # Most probable outcome
            best_outcome = max(outcomes, key=outcomes.get)  # type: ignore
            best_probability = outcomes[best_outcome]

            # Average cost
            avg_cost = sum(t.cost for t in action_transitions) / len(action_transitions)

            reasoning_chain.append(
                f"Possible outcomes: {dict(sorted(outcomes.items(), key=lambda x: -x[1]))}"
            )
            reasoning_chain.append(
                f"Most probable: {best_outcome} (p={best_probability:.3f})"
            )
            reasoning_chain.append(f"Average cost: {avg_cost:.3f}")

            confidence = best_probability
            predicted_state = best_outcome
            probability = best_probability
        else:
            # No direct observations — try to infer from similar states
            predicted_state = current_state  # Conservative: no change
            probability = 0.0
            confidence = self.MIN_PREDICTION_CONFIDENCE
            transition_ids = []
            reasoning_chain.append(
                "No observed outcomes for this action — predicting no change"
            )
            reasoning_chain.append(
                "ASSUMPTION: Action has no effect without observed evidence"
            )

        description = (
            f"Action '{action}' from '{current_state}' "
            f"predicted to lead to '{predicted_state}' (p={probability:.3f})"
        )

        prediction = Prediction(
            prediction_type=PredictionType.ACTION_OUTCOME,
            description=description,
            source_state=current_state,
            predicted_state=predicted_state,
            action=action,
            confidence=max(confidence, self.MIN_PREDICTION_CONFIDENCE),
            time_horizon=time_horizon,
            probability=probability,
            transition_ids=transition_ids,
            reasoning_chain=reasoning_chain,
            assumptions=[
                "Past observations are representative of future outcomes",
                "No external disruptions are expected",
            ],
        )
        await self._save_prediction(prediction)
        self._predictions[prediction.id] = prediction
        return prediction

    async def predict_goal_completion(
        self,
        goal_id: str,
        goal_description: str = "",
        current_state: str = "",
        goal_target_state: str = "",
    ) -> Prediction:
        """Predict the probability of completing a goal.

        Args:
            goal_id: The goal to predict completion for.
            goal_description: Human-readable goal description.
            current_state: Current state of the system.
            goal_target_state: The state that represents goal completion.

        Returns:
            A Prediction about goal completion.
        """
        start_time = time_mod.monotonic()

        reasoning_chain = [
            f"Goal: {goal_description or goal_id}",
            f"Current state: {current_state or 'unknown'}",
            f"Target state: {goal_target_state or 'unknown'}",
        ]

        if current_state and goal_target_state:
            # Find a path from current to target
            path = await self._transition_graph.find_transition_path(
                current_state, goal_target_state
            )

            if path:
                # Calculate cumulative probability
                cumulative_prob = 1.0
                total_cost = 0.0
                total_duration = 0.0

                for t in path:
                    cumulative_prob *= t.confidence
                    total_cost += t.cost
                    total_duration += t.duration_estimate

                reasoning_chain.append(
                    f"Path found: {len(path)} step(s), "
                    f"cumulative probability: {cumulative_prob:.3f}, "
                    f"total cost: {total_cost:.3f}"
                )

                probability = cumulative_prob
                confidence = cumulative_prob
                transition_ids = [t.id for t in path]
            else:
                probability = 0.1  # Low but non-zero — might find a path later
                confidence = 0.2
                transition_ids = []
                reasoning_chain.append("No path found from current to target state")
        else:
            probability = 0.5  # No information
            confidence = 0.1
            transition_ids = []
            reasoning_chain.append("Insufficient state information for prediction")

        description = (
            f"Goal '{goal_description or goal_id}' completion probability: {probability:.1%}"
        )

        prediction = Prediction(
            prediction_type=PredictionType.GOAL_COMPLETION,
            description=description,
            source_state=current_state,
            predicted_state=goal_target_state,
            goal_id=goal_id,
            confidence=max(confidence, self.MIN_PREDICTION_CONFIDENCE),
            probability=probability,
            transition_ids=transition_ids,
            reasoning_chain=reasoning_chain,
            assumptions=["Goal can be reached via observed transition paths"],
        )
        await self._save_prediction(prediction)
        self._predictions[prediction.id] = prediction
        return prediction

    async def verify_prediction(
        self, prediction_id: str, actual_outcome: str
    ) -> Prediction | None:
        """Verify a past prediction against the actual outcome.

        This is how the world model improves: by checking its predictions.

        Args:
            prediction_id: The prediction to verify.
            actual_outcome: What actually happened.

        Returns:
            The updated Prediction with error metrics, or None.
        """
        prediction = self._predictions.get(prediction_id)
        if prediction is None:
            return None

        prediction.actual_outcome = actual_outcome
        prediction.is_verified = True
        prediction.verified_at = utc_now()

        # Calculate prediction error
        if prediction.predicted_state == actual_outcome:
            prediction.prediction_error = 0.0
        else:
            prediction.prediction_error = 1.0 - prediction.probability

        await self._save_prediction(prediction)
        return prediction

    # ─── State Access ───────────────────────────────────────────────────────

    @property
    def transition_graph(self) -> StateTransitionGraph:
        """Access the underlying transition graph."""
        return self._transition_graph

    async def get_state(self) -> WorldModelState:
        """Get current world model state."""
        stats = await self._transition_graph.get_stats()
        total_predictions = len(self._predictions)
        verified = [p for p in self._predictions.values() if p.is_verified]
        avg_accuracy = 0.0
        if verified:
            avg_accuracy = 1.0 - (sum(p.prediction_error or 0.0 for p in verified) / len(verified))

        return WorldModelState(
            total_transitions=stats["total_transitions"],
            total_predictions=total_predictions,
            verified_predictions=len(verified),
            average_prediction_accuracy=avg_accuracy,
            model_confidence=stats["avg_confidence"],
        )

    async def get_prediction(self, prediction_id: str) -> Prediction | None:
        """Get a specific prediction."""
        return self._predictions.get(prediction_id)

    async def get_predictions(
        self, prediction_type: PredictionType | None = None, limit: int = 50
    ) -> list[Prediction]:
        """Get predictions, optionally filtered by type."""
        preds = list(self._predictions.values())
        if prediction_type:
            preds = [p for p in preds if p.prediction_type == prediction_type]
        preds.sort(key=lambda p: p.created_at, reverse=True)
        return preds[:limit]

    async def get_stats(self) -> dict[str, Any]:
        """Get world model statistics."""
        wm_state = await self.get_state()
        graph_stats = await self._transition_graph.get_stats()

        by_type: dict[str, int] = {}
        for p in self._predictions.values():
            key = p.prediction_type.value
            by_type[key] = by_type.get(key, 0) + 1

        return {
            "total_predictions": wm_state.total_predictions,
            "verified_predictions": wm_state.verified_predictions,
            "average_accuracy": wm_state.average_prediction_accuracy,
            "model_confidence": wm_state.model_confidence,
            "predictions_by_type": by_type,
            "transition_graph": graph_stats,
        }
