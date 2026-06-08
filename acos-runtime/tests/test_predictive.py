"""
Unit tests for ACOS Runtime v0.4 — World Model & Predictive Cognition.

Tests each module in isolation:
- StateTransitionGraph
- WorldModel
- OutcomePredictor
- SimulationEngine
- CausalReasoner
- GoalForecastEngine
- Integration: full predictive cycle
"""

import os
import tempfile

import pytest

from acos.memory.store import StorageBackend
from acos.schemas.v2_models import (
    Goal,
    GoalStatus,
    GoalPriority,
)
from acos.schemas.v4_models import (
    TransitionType,
    PredictionType,
    SimulationStatus,
    CausalDirection,
    CausalStrength,
    GoalFeasibility,
)
from acos.cognitive.predictive.state_transition_graph import StateTransitionGraph
from acos.cognitive.predictive.world_model import WorldModel
from acos.cognitive.predictive.outcome_predictor import OutcomePredictor
from acos.cognitive.predictive.simulation_engine import SimulationEngine
from acos.cognitive.predictive.causal_reasoner import CausalReasoner
from acos.cognitive.predictive.goal_forecast import GoalForecastEngine


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def db_path():
    """Create a temporary database path for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
async def storage(db_path):
    """Create and initialise a StorageBackend for testing."""
    s = StorageBackend(db_path=db_path)
    await s.initialize()
    yield s
    await s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# StateTransitionGraph
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateTransitionGraph:
    """Unit tests for StateTransitionGraph."""

    @pytest.mark.asyncio
    async def test_register_state(self, storage):
        """register_state creates a new state vector."""
        stg = StateTransitionGraph(storage)
        await stg.initialize()

        sv = await stg.register_state("idle", features={"energy": 0.8})
        assert sv.label == "idle"
        assert sv.features["energy"] == 0.8

    @pytest.mark.asyncio
    async def test_register_state_updates_existing(self, storage):
        """register_state on existing state updates features."""
        stg = StateTransitionGraph(storage)
        await stg.initialize()

        await stg.register_state("idle", features={"energy": 0.8})
        updated = await stg.register_state("idle", features={"mood": 0.5})
        assert updated.features["energy"] == 0.8
        assert updated.features["mood"] == 0.5

    @pytest.mark.asyncio
    async def test_record_transition(self, storage):
        """record_transition creates a new transition."""
        stg = StateTransitionGraph(storage)
        await stg.initialize()

        t = await stg.record_transition("idle", "learning", action="start_study")
        assert t.source_state == "idle"
        assert t.target_state == "learning"
        assert t.action == "start_study"
        assert t.frequency == 1

    @pytest.mark.asyncio
    async def test_record_transition_increments_frequency(self, storage):
        """record_transition on existing (source, target, action) increments frequency."""
        stg = StateTransitionGraph(storage)
        await stg.initialize()

        await stg.record_transition("idle", "learning", action="study")
        t2 = await stg.record_transition("idle", "learning", action="study")
        assert t2.frequency == 2
        assert t2.confidence > 0.5  # Should increase with observations

    @pytest.mark.asyncio
    async def test_get_transitions_from(self, storage):
        """get_transitions_from returns outgoing transitions."""
        stg = StateTransitionGraph(storage)
        await stg.initialize()

        await stg.record_transition("idle", "learning", action="study", confidence=0.8)
        await stg.record_transition("idle", "resting", action="relax", confidence=0.6)

        transitions = await stg.get_transitions_from("idle")
        assert len(transitions) == 2
        # Sorted by confidence descending
        assert transitions[0].confidence >= transitions[1].confidence

    @pytest.mark.asyncio
    async def test_get_transitions_to(self, storage):
        """get_transitions_to returns incoming transitions."""
        stg = StateTransitionGraph(storage)
        await stg.initialize()

        await stg.record_transition("idle", "learning", action="study")
        await stg.record_transition("confused", "learning", action="review")

        transitions = await stg.get_transitions_to("learning")
        assert len(transitions) == 2

    @pytest.mark.asyncio
    async def test_find_transition_path(self, storage):
        """find_transition_path finds a path between states."""
        stg = StateTransitionGraph(storage)
        await stg.initialize()

        await stg.record_transition("beginner", "intermediate", action="practice")
        await stg.record_transition("intermediate", "advanced", action="practice_more")
        await stg.record_transition("advanced", "expert", action="master")

        path = await stg.find_transition_path("beginner", "expert")
        assert path is not None
        assert len(path) == 3

    @pytest.mark.asyncio
    async def test_find_transition_path_unreachable(self, storage):
        """find_transition_path returns None for unreachable states."""
        stg = StateTransitionGraph(storage)
        await stg.initialize()

        await stg.record_transition("beginner", "intermediate", action="practice")

        path = await stg.find_transition_path("beginner", "expert")
        assert path is None

    @pytest.mark.asyncio
    async def test_get_most_probable_next_state(self, storage):
        """get_most_probable_next_state returns the best next state."""
        stg = StateTransitionGraph(storage)
        await stg.initialize()

        await stg.record_transition("idle", "learning", action="study", confidence=0.9)
        await stg.record_transition("idle", "resting", action="relax", confidence=0.3)

        result = await stg.get_most_probable_next_state("idle")
        assert result is not None
        assert result[0] == "learning"
        assert result[1] == 0.9

    @pytest.mark.asyncio
    async def test_compute_transition_probability(self, storage):
        """compute_transition_probability calculates observed probability."""
        stg = StateTransitionGraph(storage)
        await stg.initialize()

        await stg.record_transition("idle", "learning", action="study")
        await stg.record_transition("idle", "learning", action="study")
        await stg.record_transition("idle", "resting", action="relax")

        prob = await stg.compute_transition_probability("idle", "learning")
        assert prob > 0.5  # 2/3 of observations

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns graph statistics."""
        stg = StateTransitionGraph(storage)
        await stg.initialize()

        await stg.record_transition("a", "b", action="go")
        stats = await stg.get_stats()
        assert stats["total_states"] == 2
        assert stats["total_transitions"] == 1
        assert stats["total_observations"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# WorldModel
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorldModel:
    """Unit tests for WorldModel."""

    @pytest.mark.asyncio
    async def test_observe_transition(self, storage):
        """observe_transition learns from observations."""
        wm = WorldModel(storage)
        await wm.initialize()

        t = await wm.observe_transition("idle", "learning", action="study")
        assert t.source_state == "idle"
        assert t.target_state == "learning"

    @pytest.mark.asyncio
    async def test_predict_next_state(self, storage):
        """predict_next_state predicts the most probable next state."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("idle", "learning", action="study", confidence=0.9)
        await wm.observe_transition("idle", "resting", action="relax", confidence=0.3)

        pred = await wm.predict_next_state("idle")
        assert pred.prediction_type == PredictionType.STATE_PREDICTION
        assert pred.predicted_state == "learning"
        assert pred.probability > 0.5

    @pytest.mark.asyncio
    async def test_predict_next_state_unknown(self, storage):
        """predict_next_state handles unknown states gracefully."""
        wm = WorldModel(storage)
        await wm.initialize()

        pred = await wm.predict_next_state("unknown_state")
        assert pred.predicted_state == "unknown_state"  # Stays in place
        assert pred.confidence <= 0.2  # Low confidence

    @pytest.mark.asyncio
    async def test_predict_action_outcome(self, storage):
        """predict_action_outcome predicts the result of an action."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("beginner", "intermediate", action="practice", confidence=0.8)
        await wm.observe_transition("beginner", "beginner", action="practice", confidence=0.2)

        pred = await wm.predict_action_outcome("beginner", "practice")
        assert pred.prediction_type == PredictionType.ACTION_OUTCOME
        assert pred.action == "practice"

    @pytest.mark.asyncio
    async def test_predict_goal_completion(self, storage):
        """predict_goal_completion estimates goal achievability."""
        wm = WorldModel(storage)
        await wm.initialize()

        # Create a path to the goal
        await wm.observe_transition("beginner", "intermediate", action="practice", confidence=0.8)
        await wm.observe_transition("intermediate", "advanced", action="practice_more", confidence=0.7)
        await wm.observe_transition("advanced", "expert", action="master", confidence=0.6)

        pred = await wm.predict_goal_completion(
            goal_id="goal-1",
            current_state="beginner",
            goal_target_state="expert",
        )
        assert pred.prediction_type == PredictionType.GOAL_COMPLETION
        assert pred.probability > 0.0

    @pytest.mark.asyncio
    async def test_verify_prediction(self, storage):
        """verify_prediction checks predictions against actual outcomes."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("idle", "learning", action="study", confidence=0.9)
        pred = await wm.predict_next_state("idle")

        verified = await wm.verify_prediction(pred.id, "learning")
        assert verified is not None
        assert verified.is_verified
        assert verified.actual_outcome == "learning"

    @pytest.mark.asyncio
    async def test_learn_from_belief_change(self, storage):
        """learn_from_belief_change records belief transitions."""
        wm = WorldModel(storage)
        await wm.initialize()

        t = await wm.learn_from_belief_change("belief-1", 0.5, 0.8)
        assert t is not None
        assert t.action == "reinforced"  # Confidence increased = reinforced

        t2 = await wm.learn_from_belief_change("belief-2", 0.8, 0.3)
        assert t2 is not None
        assert t2.action == "weakened"  # Confidence decreased = weakened

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns world model statistics."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("a", "b", action="go")
        stats = await wm.get_stats()
        assert stats["total_predictions"] >= 0
        assert "transition_graph" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# OutcomePredictor
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutcomePredictor:
    """Unit tests for OutcomePredictor."""

    @pytest.mark.asyncio
    async def test_predict_outcome(self, storage):
        """predict_outcome predicts success/failure probabilities."""
        wm = WorldModel(storage)
        await wm.initialize()

        # Seed some observations
        await wm.observe_transition("beginner", "intermediate", action="practice", confidence=0.8)
        await wm.observe_transition("beginner", "beginner", action="practice", confidence=0.2)

        op = OutcomePredictor(storage, wm.transition_graph)
        await op.initialize()

        pred = await op.predict_outcome("practice", current_state="beginner")
        assert pred.action == "practice"
        assert 0.0 <= pred.success_probability <= 1.0
        assert 0.0 <= pred.failure_probability <= 1.0

    @pytest.mark.asyncio
    async def test_predict_outcome_no_evidence(self, storage):
        """predict_outcome handles unknown actions."""
        wm = WorldModel(storage)
        await wm.initialize()

        op = OutcomePredictor(storage, wm.transition_graph)
        await op.initialize()

        pred = await op.predict_outcome("unknown_action")
        assert pred.action == "unknown_action"
        assert pred.confidence <= 0.2
        assert len(pred.risk_factors) >= 1

    @pytest.mark.asyncio
    async def test_compare_actions(self, storage):
        """compare_actions ranks actions by success probability."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("idle", "productive", action="work", confidence=0.9)
        await wm.observe_transition("idle", "relaxed", action="relax", confidence=0.6)

        op = OutcomePredictor(storage, wm.transition_graph)
        await op.initialize()

        results = await op.compare_actions(["work", "relax"], current_state="idle")
        assert len(results) == 2
        # Results should be sorted by success probability
        assert results[0][1].success_probability >= results[1][1].success_probability

    @pytest.mark.asyncio
    async def test_predict_multi_action_outcome(self, storage):
        """predict_multi_action_outcome predicts a sequence of actions."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("start", "step1", action="do_a", confidence=0.8)
        await wm.observe_transition("step1", "step2", action="do_b", confidence=0.7)

        op = OutcomePredictor(storage, wm.transition_graph)
        await op.initialize()

        predictions = await op.predict_multi_action_outcome(["do_a", "do_b"], current_state="start")
        assert len(predictions) == 2

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns outcome predictor statistics."""
        wm = WorldModel(storage)
        await wm.initialize()

        op = OutcomePredictor(storage, wm.transition_graph)
        await op.initialize()

        stats = await op.get_stats()
        assert "total_predictions" in stats
        assert "avg_success_probability" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# SimulationEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimulationEngine:
    """Unit tests for SimulationEngine."""

    @pytest.mark.asyncio
    async def test_simulate(self, storage):
        """simulate runs a forward simulation."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("beginner", "intermediate", action="practice", confidence=0.8)
        await wm.observe_transition("intermediate", "advanced", action="practice_more", confidence=0.7)

        se = SimulationEngine(storage, wm.transition_graph)
        await se.initialize()

        run = await se.simulate(
            initial_state="beginner",
            planned_actions=["practice", "practice_more"],
            max_steps=5,
        )
        assert run.status == SimulationStatus.COMPLETED
        assert len(run.steps) >= 1
        assert run.final_probability > 0.0

    @pytest.mark.asyncio
    async def test_simulate_with_goal(self, storage):
        """simulate checks goal achievement."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("start", "mid", action="go", confidence=0.8)
        await wm.observe_transition("mid", "goal", action="finish", confidence=0.7)

        se = SimulationEngine(storage, wm.transition_graph)
        await se.initialize()

        run = await se.simulate(
            initial_state="start",
            planned_actions=["go", "finish"],
            goal_target_state="goal",
        )
        assert run.goal_achieved

    @pytest.mark.asyncio
    async def test_simulate_alternatives(self, storage):
        """simulate_alternatives compares multiple action sequences."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("start", "path_a", action="route_a", confidence=0.9)
        await wm.observe_transition("start", "path_b", action="route_b", confidence=0.5)

        se = SimulationEngine(storage, wm.transition_graph)
        await se.initialize()

        runs = await se.simulate_alternatives(
            initial_state="start",
            action_sets=[["route_a"], ["route_b"]],
        )
        assert len(runs) == 2
        # One should be marked best
        best_runs = [r for r in runs if r.is_best_alternative]
        assert len(best_runs) >= 1

    @pytest.mark.asyncio
    async def test_compare_scenarios(self, storage):
        """compare_scenarios ranks multiple scenarios."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("start", "fast", action="fast_route", confidence=0.9)
        await wm.observe_transition("start", "slow", action="slow_route", confidence=0.6)

        se = SimulationEngine(storage, wm.transition_graph)
        await se.initialize()

        comparison = await se.compare_scenarios([
            ("Fast", "start", ["fast_route"]),
            ("Slow", "start", ["slow_route"]),
        ])
        assert comparison.best_scenario_id is not None
        assert len(comparison.rankings) == 2

    @pytest.mark.asyncio
    async def test_rollout(self, storage):
        """rollout runs multiple stochastic rollouts."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("start", "end", action="go", confidence=0.8)

        se = SimulationEngine(storage, wm.transition_graph)
        await se.initialize()

        runs = await se.rollout("start", num_rollouts=3, max_steps=5)
        assert len(runs) == 3

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns simulation statistics."""
        wm = WorldModel(storage)
        await wm.initialize()

        se = SimulationEngine(storage, wm.transition_graph)
        await se.initialize()

        stats = await se.get_stats()
        assert "total_runs" in stats
        assert "completed_runs" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# CausalReasoner
# ═══════════════════════════════════════════════════════════════════════════════

class TestCausalReasoner:
    """Unit tests for CausalReasoner."""

    @pytest.mark.asyncio
    async def test_add_causal_link(self, storage):
        """add_causal_link creates a causal relationship."""
        wm = WorldModel(storage)
        await wm.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        link = await cr.add_causal_link(
            cause_id="study_hours",
            cause_label="Study Hours",
            effect_id="knowledge_level",
            effect_label="Knowledge Level",
            strength=CausalStrength.SUFFICIENT,
            confidence=0.8,
        )
        assert link.cause_id == "study_hours"
        assert link.effect_id == "knowledge_level"
        assert link.strength == CausalStrength.SUFFICIENT
        assert link.confidence == 0.8

    @pytest.mark.asyncio
    async def test_add_causal_link_updates_existing(self, storage):
        """add_causal_link on existing link increments observations."""
        wm = WorldModel(storage)
        await wm.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        await cr.add_causal_link("cause", "Cause", "effect", "Effect")
        updated = await cr.add_causal_link("cause", "Cause", "effect", "Effect")
        assert updated.supporting_observations == 2
        assert updated.confidence > 0.5  # Should increase

    @pytest.mark.asyncio
    async def test_add_contradicting_observation(self, storage):
        """add_contradicting_observation reduces confidence."""
        wm = WorldModel(storage)
        await wm.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        link = await cr.add_causal_link("cause", "Cause", "effect", "Effect", confidence=0.8)
        contradicted = await cr.add_contradicting_observation(link.id)
        assert contradicted is not None
        assert contradicted.contradicting_observations == 1
        assert contradicted.confidence < 0.8

    @pytest.mark.asyncio
    async def test_add_intervention_evidence(self, storage):
        """add_intervention_evidence boosts confidence."""
        wm = WorldModel(storage)
        await wm.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        link = await cr.add_causal_link("cause", "Cause", "effect", "Effect", confidence=0.5)
        intervened = await cr.add_intervention_evidence(link.id)
        assert intervened.intervention_evidence == 1
        assert intervened.confidence > 0.5

    @pytest.mark.asyncio
    async def test_discover_causes(self, storage):
        """discover_causes discovers causal links from transitions."""
        wm = WorldModel(storage)
        await wm.initialize()

        # Create consistent action patterns
        for _ in range(5):
            await wm.observe_transition("idle", "learning", action="study", confidence=0.8)

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        result = await cr.discover_causes(confidence_threshold=0.3)
        assert len(result.discovered_links) >= 1
        assert result.discovery_time_ms > 0

    @pytest.mark.asyncio
    async def test_analyze_intervention(self, storage):
        """analyze_intervention predicts intervention effects."""
        wm = WorldModel(storage)
        await wm.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        await cr.add_causal_link("study", "Study", "knowledge", "Knowledge", confidence=0.8)

        result = await cr.analyze_intervention(
            target="study",
            new_value="8_hours",
            original_value="2_hours",
        )
        assert result.intervention_target == "study"
        assert len(result.predicted_effects) >= 1
        assert len(result.causal_paths) >= 1

    @pytest.mark.asyncio
    async def test_counterfactual_cause(self, storage):
        """counterfactual_cause analyzes what-if-no-cause scenarios."""
        wm = WorldModel(storage)
        await wm.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        await cr.add_causal_link(
            "practice", "Practice", "skill", "Skill",
            strength=CausalStrength.SUFFICIENT, confidence=0.8,
        )

        result = await cr.counterfactual_cause("skill", "practice")
        assert result.intervention_target == "practice"
        assert result.intervention_value == "REMOVED"
        assert len(result.predicted_effects) >= 1

    @pytest.mark.asyncio
    async def test_get_causes_of(self, storage):
        """get_causes_of returns causes for an effect."""
        wm = WorldModel(storage)
        await wm.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        await cr.add_causal_link("study", "Study", "knowledge", "Knowledge", confidence=0.8)
        await cr.add_causal_link("practice", "Practice", "knowledge", "Knowledge", confidence=0.6)

        causes = await cr.get_causes_of("knowledge")
        assert len(causes) == 2
        assert causes[0].confidence >= causes[1].confidence  # Sorted

    @pytest.mark.asyncio
    async def test_get_effects_of(self, storage):
        """get_effects_of returns effects of a cause."""
        wm = WorldModel(storage)
        await wm.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        await cr.add_causal_link("study", "Study", "knowledge", "Knowledge", confidence=0.8)
        await cr.add_causal_link("study", "Study", "fatigue", "Fatigue", confidence=0.4)

        effects = await cr.get_effects_of("study")
        assert len(effects) == 2

    @pytest.mark.asyncio
    async def test_get_causal_chain(self, storage):
        """get_causal_chain traces a chain of causes."""
        wm = WorldModel(storage)
        await wm.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        await cr.add_causal_link("motivation", "Motivation", "study", "Study", confidence=0.8)
        await cr.add_causal_link("study", "Study", "knowledge", "Knowledge", confidence=0.7)

        chain = await cr.get_causal_chain("motivation")
        assert len(chain) >= 1

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns causal reasoner statistics."""
        wm = WorldModel(storage)
        await wm.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        stats = await cr.get_stats()
        assert "total_causal_links" in stats
        assert "by_strength" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# GoalForecastEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoalForecastEngine:
    """Unit tests for GoalForecastEngine."""

    @pytest.mark.asyncio
    async def test_forecast_goal(self, storage):
        """forecast_goal predicts goal achievability."""
        wm = WorldModel(storage)
        await wm.initialize()

        op = OutcomePredictor(storage, wm.transition_graph)
        await op.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        gf = GoalForecastEngine(storage, wm, op, cr)
        await gf.initialize()

        # Seed some transitions
        await wm.observe_transition("beginner", "intermediate", action="practice", confidence=0.8)

        forecast = await gf.forecast_goal(
            goal_id="goal-1",
            goal_description="Learn Python",
            current_state="beginner",
            target_state="expert",
        )
        assert forecast.goal_id == "goal-1"
        assert 0.0 <= forecast.success_probability <= 1.0
        assert 0.0 <= forecast.failure_probability <= 1.0
        assert isinstance(forecast.feasibility, GoalFeasibility)

    @pytest.mark.asyncio
    async def test_forecast_goal_with_path(self, storage):
        """forecast_goal with a clear path yields higher probability."""
        wm = WorldModel(storage)
        await wm.initialize()

        op = OutcomePredictor(storage, wm.transition_graph)
        await op.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        gf = GoalForecastEngine(storage, wm, op, cr)
        await gf.initialize()

        # Create a clear path
        await wm.observe_transition("start", "step1", action="go1", confidence=0.9)
        await wm.observe_transition("step1", "goal_state", action="go2", confidence=0.9)

        forecast = await gf.forecast_goal(
            goal_id="goal-1",
            current_state="start",
            target_state="goal_state",
        )
        assert forecast.success_probability > 0.0
        assert len(forecast.recommended_next_actions) >= 1

    @pytest.mark.asyncio
    async def test_forecast_goal_with_causal_factors(self, storage):
        """forecast_goal considers causal factors."""
        wm = WorldModel(storage)
        await wm.initialize()

        op = OutcomePredictor(storage, wm.transition_graph)
        await op.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        # Add a causal factor
        await cr.add_causal_link("practice", "Practice", "goal_state", "Goal Achieved", confidence=0.8)

        gf = GoalForecastEngine(storage, wm, op, cr)
        await gf.initialize()

        forecast = await gf.forecast_goal(
            goal_id="goal-1",
            target_state="goal_state",
        )
        assert len(forecast.supporting_causal_ids) >= 1

    @pytest.mark.asyncio
    async def test_forecast_all_goals(self, storage):
        """forecast_all_goals produces a comprehensive report."""
        wm = WorldModel(storage)
        await wm.initialize()

        op = OutcomePredictor(storage, wm.transition_graph)
        await op.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        gf = GoalForecastEngine(storage, wm, op, cr)
        await gf.initialize()

        goals = [
            Goal(description="Learn Python", status=GoalStatus.ACTIVE, progress=0.3),
            Goal(description="Build App", status=GoalStatus.ACTIVE, progress=0.1),
        ]

        report = await gf.forecast_all_goals(goals)
        assert report.total_goals_assessed == 2
        assert len(report.forecasts) == 2

    @pytest.mark.asyncio
    async def test_recommend_next_actions(self, storage):
        """recommend_next_actions returns actionable recommendations."""
        wm = WorldModel(storage)
        await wm.initialize()

        op = OutcomePredictor(storage, wm.transition_graph)
        await op.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        gf = GoalForecastEngine(storage, wm, op, cr)
        await gf.initialize()

        await wm.observe_transition("idle", "learning", action="start_study", confidence=0.8)

        actions = await gf.recommend_next_actions("goal-1", current_state="idle", target_state="expert")
        assert isinstance(actions, list)

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns goal forecast statistics."""
        wm = WorldModel(storage)
        await wm.initialize()

        op = OutcomePredictor(storage, wm.transition_graph)
        await op.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        gf = GoalForecastEngine(storage, wm, op, cr)
        await gf.initialize()

        stats = await gf.get_stats()
        assert "total_forecasts" in stats
        assert "by_feasibility" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: Full Predictive Cycle
# ═══════════════════════════════════════════════════════════════════════════════

class TestPredictiveIntegration:
    """Integration tests for the full predictive cognition pipeline."""

    @pytest.mark.asyncio
    async def test_full_predictive_cycle(self, storage):
        """Full cycle: learn → predict → simulate → forecast."""
        # 1. Initialize all v0.4 subsystems
        wm = WorldModel(storage)
        await wm.initialize()

        op = OutcomePredictor(storage, wm.transition_graph)
        await op.initialize()

        se = SimulationEngine(storage, wm.transition_graph)
        await se.initialize()

        cr = CausalReasoner(storage, wm.transition_graph)
        await cr.initialize()

        gf = GoalForecastEngine(storage, wm, op, cr)
        await gf.initialize()

        # 2. Learn: observe several transitions
        await wm.observe_transition("beginner", "learning", action="start_course", confidence=0.8)
        await wm.observe_transition("learning", "practicing", action="do_exercises", confidence=0.7)
        await wm.observe_transition("practicing", "proficient", action="build_project", confidence=0.8)
        await wm.observe_transition("proficient", "expert", action="teach_others", confidence=0.6)

        # 3. Predict: future states
        next_pred = await wm.predict_next_state("beginner")
        assert next_pred.predicted_state == "learning"

        action_pred = await wm.predict_action_outcome("beginner", "start_course")
        assert action_pred.probability > 0.0

        goal_pred = await wm.predict_goal_completion(
            goal_id="master-skill",
            current_state="beginner",
            goal_target_state="expert",
        )
        assert goal_pred.probability > 0.0

        # 4. Simulate: future rollout
        sim_run = await se.simulate(
            initial_state="beginner",
            planned_actions=["start_course", "do_exercises", "build_project", "teach_others"],
            goal_target_state="expert",
        )
        assert sim_run.status == SimulationStatus.COMPLETED

        # 5. Causal: discover and analyze
        discovery = await cr.discover_causes(confidence_threshold=0.3)
        assert discovery.total_observations_used > 0

        await cr.add_causal_link(
            "practice", "Practice", "proficiency", "Proficiency",
            strength=CausalStrength.SUFFICIENT, confidence=0.8,
        )
        intervention = await cr.analyze_intervention("practice", "daily", "weekly")
        assert len(intervention.predicted_effects) >= 1

        # 6. Forecast: goal achievability
        goals = [
            Goal(description="Become proficient", status=GoalStatus.ACTIVE, progress=0.1),
            Goal(description="Become expert", status=GoalStatus.ACTIVE, progress=0.0),
        ]
        report = await gf.forecast_all_goals(goals, current_state="beginner")
        assert report.total_goals_assessed == 2

    @pytest.mark.asyncio
    async def test_scenario_comparison(self, storage):
        """Compare different strategic scenarios."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("start", "path_a", action="strategy_a", confidence=0.9)
        await wm.observe_transition("path_a", "success", action="execute_a", confidence=0.8)

        await wm.observe_transition("start", "path_b", action="strategy_b", confidence=0.6)
        await wm.observe_transition("path_b", "success", action="execute_b", confidence=0.5)

        se = SimulationEngine(storage, wm.transition_graph)
        await se.initialize()

        comparison = await se.compare_scenarios([
            ("Strategy A", "start", ["strategy_a", "execute_a"]),
            ("Strategy B", "start", ["strategy_b", "execute_b"]),
        ], goal_target_state="success")

        assert comparison.best_scenario_id is not None
        # Strategy A should rank higher (higher confidence transitions)
        best_run = None
        for ranking in comparison.rankings:
            if ranking["rank"] == 1:
                best_run = ranking
        assert best_run is not None
        assert "A" in best_run["name"]

    @pytest.mark.asyncio
    async def test_prediction_verification_improves_model(self, storage):
        """Verify predictions and check that accuracy improves."""
        wm = WorldModel(storage)
        await wm.initialize()

        await wm.observe_transition("a", "b", action="go", confidence=0.7)

        # Make a prediction
        pred = await wm.predict_next_state("a")

        # Verify it correctly
        verified = await wm.verify_prediction(pred.id, "b")
        assert verified.is_verified
        assert verified.prediction_error == 0.0

        # Check model state
        state = await wm.get_state()
        assert state.verified_predictions >= 1
        assert state.average_prediction_accuracy == 1.0  # Perfect accuracy
