"""
Goal Forecast Engine — predict goal achievability and recommend actions.

Predicts:
- Which goals are achievable
- Which goals will fail
- Recommended next actions

Uses the World Model, Outcome Predictor, and Causal Reasoner
to assess goal feasibility and recommend the best course of action.
"""

from __future__ import annotations

import json
import time as time_mod
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v4_models import (
    GoalForecast,
    GoalFeasibility,
    GoalForecastReport,
    gen_id,
    utc_now,
)
from acos.cognitive.predictive.state_transition_graph import StateTransitionGraph
from acos.cognitive.predictive.world_model import WorldModel
from acos.cognitive.predictive.outcome_predictor import OutcomePredictor
from acos.cognitive.predictive.causal_reasoner import CausalReasoner


class GoalForecastEngine:
    """Goal Forecast Engine — predict goal achievability and recommend actions.

    Usage::

        store = StorageBackend()
        await store.initialize()

        gf = GoalForecastEngine(store, world_model, outcome_predictor, causal_reasoner)
        await gf.initialize()

        # Forecast a specific goal
        forecast = await gf.forecast_goal(
            goal_id="goal-123",
            goal_description="Master Python",
            current_state="beginner",
            target_state="expert",
        )

        # Forecast all goals
        report = await gf.forecast_all_goals(goals)
    """

    def __init__(
        self,
        storage: StorageBackend,
        world_model: WorldModel,
        outcome_predictor: OutcomePredictor,
        causal_reasoner: CausalReasoner,
    ) -> None:
        self._storage = storage
        self._world_model = world_model
        self._outcome_predictor = outcome_predictor
        self._causal_reasoner = causal_reasoner
        self._transition_graph = world_model.transition_graph
        self._forecasts: dict[str, GoalForecast] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load existing forecasts."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS goal_forecasts (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                goal_description TEXT DEFAULT '',
                feasibility TEXT NOT NULL,
                success_probability REAL DEFAULT 0.5,
                failure_probability REAL DEFAULT 0.5,
                estimated_steps_remaining INTEGER DEFAULT 0,
                estimated_duration REAL DEFAULT 0.0,
                estimated_completion_date TEXT,
                blocking_factors TEXT DEFAULT '[]',
                risk_factors TEXT DEFAULT '[]',
                dependency_risks TEXT DEFAULT '[]',
                recommended_next_actions TEXT DEFAULT '[]',
                prerequisite_goals TEXT DEFAULT '[]',
                alternative_approaches TEXT DEFAULT '[]',
                supporting_transition_ids TEXT DEFAULT '[]',
                supporting_causal_ids TEXT DEFAULT '[]',
                simulation_run_ids TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.5,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS goal_forecast_reports (
                id TEXT PRIMARY KEY,
                forecasts TEXT DEFAULT '[]',
                total_goals_assessed INTEGER DEFAULT 0,
                achievable_count INTEGER DEFAULT 0,
                unlikely_count INTEGER DEFAULT 0,
                infeasible_count INTEGER DEFAULT 0,
                top_priority_action TEXT DEFAULT '',
                overall_confidence REAL DEFAULT 0.5,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_gf_goal
                ON goal_forecasts(goal_id);
            CREATE INDEX IF NOT EXISTS idx_gf_feasibility
                ON goal_forecasts(feasibility);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        cursor = await conn.execute("SELECT * FROM goal_forecasts")
        rows = await cursor.fetchall()
        for row in rows:
            forecast = GoalForecast(
                id=row["id"],
                goal_id=row["goal_id"],
                goal_description=row["goal_description"],
                feasibility=GoalFeasibility(row["feasibility"]),
                success_probability=row["success_probability"],
                failure_probability=row["failure_probability"],
                estimated_steps_remaining=row["estimated_steps_remaining"],
                estimated_duration=row["estimated_duration"],
                estimated_completion_date=(
                    datetime.fromisoformat(row["estimated_completion_date"])
                    if row["estimated_completion_date"] else None
                ),
                blocking_factors=json.loads(row["blocking_factors"]) if row["blocking_factors"] else [],
                risk_factors=json.loads(row["risk_factors"]) if row["risk_factors"] else [],
                dependency_risks=json.loads(row["dependency_risks"]) if row["dependency_risks"] else [],
                recommended_next_actions=json.loads(row["recommended_next_actions"]) if row["recommended_next_actions"] else [],
                prerequisite_goals=json.loads(row["prerequisite_goals"]) if row["prerequisite_goals"] else [],
                alternative_approaches=json.loads(row["alternative_approaches"]) if row["alternative_approaches"] else [],
                supporting_transition_ids=json.loads(row["supporting_transition_ids"]) if row["supporting_transition_ids"] else [],
                supporting_causal_ids=json.loads(row["supporting_causal_ids"]) if row["supporting_causal_ids"] else [],
                simulation_run_ids=json.loads(row["simulation_run_ids"]) if row["simulation_run_ids"] else [],
                confidence=row["confidence"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            self._forecasts[forecast.id] = forecast

    async def _save_forecast(self, forecast: GoalForecast) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO goal_forecasts
               (id, goal_id, goal_description, feasibility, success_probability,
                failure_probability, estimated_steps_remaining, estimated_duration,
                estimated_completion_date, blocking_factors, risk_factors,
                dependency_risks, recommended_next_actions, prerequisite_goals,
                alternative_approaches, supporting_transition_ids, supporting_causal_ids,
                simulation_run_ids, confidence, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                forecast.id,
                forecast.goal_id,
                forecast.goal_description,
                forecast.feasibility.value,
                forecast.success_probability,
                forecast.failure_probability,
                forecast.estimated_steps_remaining,
                forecast.estimated_duration,
                forecast.estimated_completion_date.isoformat() if forecast.estimated_completion_date else None,
                json.dumps(forecast.blocking_factors),
                json.dumps(forecast.risk_factors),
                json.dumps(forecast.dependency_risks),
                json.dumps(forecast.recommended_next_actions),
                json.dumps(forecast.prerequisite_goals),
                json.dumps(forecast.alternative_approaches),
                json.dumps(forecast.supporting_transition_ids),
                json.dumps(forecast.supporting_causal_ids),
                json.dumps(forecast.simulation_run_ids),
                forecast.confidence,
                json.dumps(forecast.metadata),
                forecast.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_report(self, report: GoalForecastReport) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO goal_forecast_reports
               (id, forecasts, total_goals_assessed, achievable_count,
                unlikely_count, infeasible_count, top_priority_action,
                overall_confidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report.id,
                json.dumps([f.model_dump(mode="json") for f in report.forecasts]),
                report.total_goals_assessed,
                report.achievable_count,
                report.unlikely_count,
                report.infeasible_count,
                report.top_priority_action,
                report.overall_confidence,
                report.created_at.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Core Forecast Methods ──────────────────────────────────────────────

    async def forecast_goal(
        self,
        goal_id: str,
        goal_description: str = "",
        current_state: str = "",
        target_state: str = "",
        goal_progress: float = 0.0,
        dependency_goal_ids: list[str] | None = None,
    ) -> GoalForecast:
        """Forecast the achievability of a specific goal.

        Uses:
        - World Model: path from current to target state
        - Outcome Predictor: success probability of required actions
        - Causal Reasoner: causal factors affecting the goal

        Args:
            goal_id: The goal to forecast.
            goal_description: Human-readable description.
            current_state: Current state of the system.
            target_state: State representing goal completion.
            goal_progress: Current progress [0, 1].
            dependency_goal_ids: IDs of prerequisite goals.

        Returns:
            GoalForecast with achievability assessment and recommendations.
        """
        start_time = time_mod.monotonic()

        # 1. Use World Model to predict goal completion
        completion_prediction = await self._world_model.predict_goal_completion(
            goal_id=goal_id,
            goal_description=goal_description,
            current_state=current_state,
            goal_target_state=target_state,
        )
        base_probability = completion_prediction.probability

        # 2. Find a path from current to target state
        transition_path = None
        if current_state and target_state:
            transition_path = await self._transition_graph.find_transition_path(
                current_state, target_state
            )

        # 3. Assess actions along the path
        recommended_actions: list[str] = []
        risk_factors: list[str] = []
        blocking_factors: list[str] = []
        supporting_transition_ids: list[str] = []
        supporting_causal_ids: list[str] = []

        if transition_path:
            for t in transition_path:
                if t.action:
                    recommended_actions.append(f"Execute: {t.action}")
                supporting_transition_ids.append(t.id)

                # Predict outcome of this step
                outcome = await self._outcome_predictor.predict_outcome(
                    action=t.action,
                    current_state=t.source_state,
                )
                if outcome.failure_probability > 0.5:
                    risk_factors.append(
                        f"High failure risk for action '{t.action}' (p_fail={outcome.failure_probability:.1%})"
                    )
                if outcome.success_probability < 0.3:
                    blocking_factors.append(
                        f"Low success for action '{t.action}' (p_success={outcome.success_probability:.1%})"
                    )

            estimated_steps = len(transition_path)
            estimated_duration = sum(t.duration_estimate for t in transition_path)
        else:
            estimated_steps = 0
            estimated_duration = 0.0
            if current_state and target_state:
                blocking_factors.append(f"No known path from '{current_state}' to '{target_state}'")
                recommended_actions.append(f"Explore transitions from '{current_state}'")

        # 4. Check causal factors
        if target_state:
            causes = await self._causal_reasoner.get_causes_of(target_state)
            for cause in causes[:5]:
                supporting_causal_ids.append(cause.id)
                if cause.confidence >= 0.7:
                    recommended_actions.append(
                        f"Leverage causal factor: {cause.cause_label}"
                    )
                if cause.confidence < 0.3:
                    risk_factors.append(
                        f"Weak causal support: {cause.cause_label} -> {cause.effect_label}"
                    )

        # 5. Factor in current progress
        progress_boost = goal_progress * 0.3  # Existing progress helps
        adjusted_probability = min(1.0, base_probability + progress_boost)

        # 6. Factor in blocking factors
        blocking_penalty = len(blocking_factors) * 0.1
        adjusted_probability = max(0.0, adjusted_probability - blocking_penalty)

        # 7. Determine feasibility classification
        if adjusted_probability >= 0.8:
            feasibility = GoalFeasibility.HIGHLY_ACHIEVABLE
        elif adjusted_probability >= 0.6:
            feasibility = GoalFeasibility.LIKELY_ACHIEVABLE
        elif adjusted_probability >= 0.4:
            feasibility = GoalFeasibility.POSSIBLE
        elif adjusted_probability >= 0.2:
            feasibility = GoalFeasibility.UNLIKELY
        else:
            feasibility = GoalFeasibility.PROBABLY_INFEASIBLE

        # 8. Generate alternative approaches
        alternative_approaches: list[str] = []
        if adjusted_probability < 0.5 and current_state:
            # Look for alternative paths
            all_transitions = await self._transition_graph.get_transitions_from(current_state)
            for t in all_transitions[:3]:
                if t.action and t.action not in recommended_actions:
                    alternative_approaches.append(
                        f"Try alternative action: {t.action} (leads to {t.target_state})"
                    )

        # 9. Assess dependency risks
        dependency_risks: list[str] = []
        if dependency_goal_ids:
            for dep_id in dependency_goal_ids:
                dependency_risks.append(f"Depends on goal {dep_id}")

        # 10. Confidence in the forecast
        confidence = 0.3  # Base
        if transition_path:
            confidence += 0.2
        if supporting_causal_ids:
            confidence += 0.1
        if completion_prediction.confidence > 0.5:
            confidence += 0.1
        confidence = min(0.9, confidence)

        forecast = GoalForecast(
            goal_id=goal_id,
            goal_description=goal_description,
            feasibility=feasibility,
            success_probability=round(adjusted_probability, 4),
            failure_probability=round(1.0 - adjusted_probability, 4),
            estimated_steps_remaining=estimated_steps,
            estimated_duration=round(estimated_duration, 4),
            blocking_factors=blocking_factors[:10],
            risk_factors=risk_factors[:10],
            dependency_risks=dependency_risks,
            recommended_next_actions=recommended_actions[:10],
            prerequisite_goals=dependency_goal_ids or [],
            alternative_approaches=alternative_approaches[:5],
            supporting_transition_ids=supporting_transition_ids,
            supporting_causal_ids=supporting_causal_ids,
            confidence=round(confidence, 4),
            metadata={
                "base_probability": round(base_probability, 4),
                "progress_boost": round(progress_boost, 4),
                "blocking_penalty": round(blocking_penalty, 4),
            },
        )
        await self._save_forecast(forecast)
        self._forecasts[forecast.id] = forecast
        return forecast

    async def forecast_all_goals(
        self,
        goals: list[Any],
        current_state: str = "",
    ) -> GoalForecastReport:
        """Forecast all given goals and produce a comprehensive report.

        Args:
            goals: List of Goal objects (must have id, description attributes).
            current_state: Current state of the system.

        Returns:
            GoalForecastReport with all forecasts and recommendations.
        """
        start_time = time_mod.monotonic()
        forecasts: list[GoalForecast] = []

        for goal in goals:
            goal_id = getattr(goal, 'id', str(goal))
            goal_description = getattr(goal, 'description', str(goal))
            goal_progress = getattr(goal, 'progress', 0.0)
            dependency_ids = getattr(goal, 'dependency_ids', [])

            # Infer target state from goal description
            target_state = f"goal_{goal_id}_completed"

            forecast = await self.forecast_goal(
                goal_id=goal_id,
                goal_description=goal_description,
                current_state=current_state,
                target_state=target_state,
                goal_progress=goal_progress,
                dependency_goal_ids=dependency_ids,
            )
            forecasts.append(forecast)

        # Calculate summary
        achievable = sum(1 for f in forecasts if f.feasibility in (
            GoalFeasibility.HIGHLY_ACHIEVABLE,
            GoalFeasibility.LIKELY_ACHIEVABLE,
        ))
        unlikely = sum(1 for f in forecasts if f.feasibility == GoalFeasibility.UNLIKELY)
        infeasible = sum(1 for f in forecasts if f.feasibility == GoalFeasibility.PROBABLY_INFEASIBLE)

        # Find top priority action
        top_action = ""
        if forecasts:
            # Pick the most recommended action from the most achievable goal
            best_forecasts = sorted(
                [f for f in forecasts if f.recommended_next_actions],
                key=lambda f: f.success_probability,
                reverse=True,
            )
            if best_forecasts:
                top_action = best_forecasts[0].recommended_next_actions[0]

        # Overall confidence
        overall_confidence = 0.5
        if forecasts:
            overall_confidence = sum(f.confidence for f in forecasts) / len(forecasts)

        report = GoalForecastReport(
            forecasts=forecasts,
            total_goals_assessed=len(forecasts),
            achievable_count=achievable,
            unlikely_count=unlikely,
            infeasible_count=infeasible,
            top_priority_action=top_action,
            overall_confidence=round(overall_confidence, 4),
        )
        await self._save_report(report)
        return report

    async def recommend_next_actions(
        self,
        goal_id: str,
        current_state: str = "",
        target_state: str = "",
    ) -> list[str]:
        """Recommend the best next actions for a goal.

        Args:
            goal_id: The goal to recommend actions for.
            current_state: Current state.
            target_state: Target state.

        Returns:
            List of recommended action descriptions, ordered by priority.
        """
        forecast = await self.forecast_goal(
            goal_id=goal_id,
            current_state=current_state,
            target_state=target_state,
        )
        return forecast.recommended_next_actions

    # ─── Access Methods ─────────────────────────────────────────────────────

    async def get_forecast(self, forecast_id: str) -> GoalForecast | None:
        """Get a specific forecast."""
        return self._forecasts.get(forecast_id)

    async def get_forecasts_for_goal(self, goal_id: str) -> list[GoalForecast]:
        """Get all forecasts for a specific goal."""
        return [f for f in self._forecasts.values() if f.goal_id == goal_id]

    async def get_stats(self) -> dict[str, Any]:
        """Get goal forecast engine statistics."""
        total = len(self._forecasts)
        by_feasibility: dict[str, int] = {}
        for f in self._forecasts.values():
            key = f.feasibility.value
            by_feasibility[key] = by_feasibility.get(key, 0) + 1

        avg_success = 0.0
        if total > 0:
            avg_success = sum(f.success_probability for f in self._forecasts.values()) / total

        return {
            "total_forecasts": total,
            "by_feasibility": by_feasibility,
            "avg_success_probability": round(avg_success, 4),
        }
