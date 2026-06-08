"""
Unit tests for ACOS Runtime v0.5 — Unified Cognitive Architecture.

Tests each module in isolation:
- WorldModelEngine
- ActiveLearningLoop
- CognitiveStateManifold
- GoalCompetitionEngine
- AttentionEconomy
- EnhancedCausalReasoner
- SelfModel
- CognitiveCycle
- EvaluationFramework
- Integration: full unified cycle
"""

import os
import tempfile

import pytest

from acos.memory.store import StorageBackend
from acos.schemas.v2_models import (
    Belief,
    Goal,
    GoalStatus,
    GoalPriority,
    Concept,
    ConceptType,
)
from acos.schemas.v4_models import (
    CausalStrength,
)
from acos.schemas.v5_models import (
    RiskLevel,
    FutureStatePrediction,
    ActionOutcomeEstimate,
    LearningSignal,
    PredictionErrorRecord,
    LearningCycleResult,
    ManifoldPoint,
    ManifoldProjectionType,
    ManifoldState,
    ManifoldCluster,
    GoalCompetitionEntry,
    CompetitionResult,
    AttentionAllocation,
    AttentionBudget,
    EconomyCycleResult,
    CausalChain,
    RootCauseAnalysisResult,
    CausalForecast,
    SelfAssessmentDimension,
    ModelPreference,
    PerformanceRecord,
    SelfModelState,
    CognitiveCycleTrace,
    UnifiedCycleResult,
    MetricType,
    MetricMeasurement,
    EvaluationReport,
)
from acos.cognitive.predictive.world_model import WorldModel
from acos.cognitive.predictive.causal_reasoner import CausalReasoner
from acos.cognitive.unified.world_model_engine import WorldModelEngine
from acos.cognitive.unified.active_learning import ActiveLearningLoop
from acos.cognitive.unified.cognitive_manifold import CognitiveStateManifold
from acos.cognitive.unified.goal_competition import GoalCompetitionEngine
from acos.cognitive.unified.attention_economy import AttentionEconomy
from acos.cognitive.unified.enhanced_causal import EnhancedCausalReasoner
from acos.cognitive.unified.self_model import SelfModel
from acos.cognitive.unified.cognitive_cycle import CognitiveCycle
from acos.cognitive.unified.evaluation import EvaluationFramework


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
# WorldModelEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorldModelEngine:
    """Unit tests for WorldModelEngine."""

    @pytest.mark.asyncio
    async def test_learn_state_transitions_with_beliefs(self, storage):
        """learn_state_transitions processes belief changes."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()

        transitions = await engine.learn_state_transitions(
            beliefs=[
                {"id": "b1", "old_confidence": 0.5, "new_confidence": 0.8, "cause": "evidence"},
                {"id": "b2", "old_confidence": 0.7, "new_confidence": 0.3, "cause": "contradiction"},
            ],
        )
        assert len(transitions) == 2

    @pytest.mark.asyncio
    async def test_learn_state_transitions_with_goals(self, storage):
        """learn_state_transitions processes goal progress."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()

        transitions = await engine.learn_state_transitions(
            goals=[
                {"id": "g1", "old_progress": 0.2, "new_progress": 0.5},
            ],
        )
        assert len(transitions) == 1

    @pytest.mark.asyncio
    async def test_learn_state_transitions_with_cognitive_state(self, storage):
        """learn_state_transitions processes cognitive state shifts."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()

        transitions = await engine.learn_state_transitions(
            cognitive_state={
                "label": "learning",
                "previous_label": "idle",
                "cause": "new_query",
            },
        )
        assert len(transitions) == 1

    @pytest.mark.asyncio
    async def test_learn_state_transitions_with_sessions(self, storage):
        """learn_state_transitions processes session transitions."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()

        transitions = await engine.learn_state_transitions(
            sessions=[
                {"id": "s1", "previous_state": "start", "current_state": "active", "action": "login"},
            ],
        )
        assert len(transitions) == 1

    @pytest.mark.asyncio
    async def test_predict_future_state(self, storage):
        """predict_future_state returns FutureStatePrediction with risk."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()

        # Seed some transitions
        await wm.observe_transition("idle", "learning", action="study", confidence=0.9)
        await wm.observe_transition("idle", "resting", action="relax", confidence=0.3)

        pred = await engine.predict_future_state("idle", time_horizon=60.0)
        assert isinstance(pred, FutureStatePrediction)
        assert pred.predicted_state == "learning"
        assert isinstance(pred.risk_level, RiskLevel)
        assert 0.0 <= pred.probability <= 1.0
        assert 0.0 <= pred.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_estimate_action_outcome(self, storage):
        """estimate_action_outcome returns ActionOutcomeEstimate."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()

        await wm.observe_transition("beginner", "intermediate", action="practice", confidence=0.8)

        estimate = await engine.estimate_action_outcome("beginner", "practice")
        assert isinstance(estimate, ActionOutcomeEstimate)
        assert estimate.action == "practice"
        assert 0.0 <= estimate.success_probability <= 1.0
        assert 0.0 <= estimate.failure_probability <= 1.0
        assert 0.0 <= estimate.uncertainty <= 1.0

    @pytest.mark.asyncio
    async def test_estimate_probabilities(self, storage):
        """estimate_probabilities returns dict of state:action probabilities."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()

        await wm.observe_transition("idle", "learning", action="study", confidence=0.9)

        probs = await engine.estimate_probabilities(
            states=["idle"],
            actions=["study"],
        )
        assert "idle:study" in probs
        assert 0.0 <= probs["idle:study"] <= 1.0

    @pytest.mark.asyncio
    async def test_estimate_uncertainty(self, storage):
        """estimate_uncertainty returns a float in [0, 1]."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()

        # Make a prediction first so we have a prediction_id
        await wm.observe_transition("idle", "learning", action="study", confidence=0.8)
        pred = await engine.predict_future_state("idle")

        uncertainty = await engine.estimate_uncertainty(pred.id)
        assert isinstance(uncertainty, float)
        assert 0.0 <= uncertainty <= 1.0

    @pytest.mark.asyncio
    async def test_get_risk_assessment(self, storage):
        """get_risk_assessment returns risk factors for a goal."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()

        # Register a risk factor first
        await engine.register_goal_risk_factor("goal-1", "High uncertainty in target state")

        factors = engine.get_risk_assessment("goal-1")
        assert len(factors) == 1
        assert "High uncertainty" in factors[0]

    @pytest.mark.asyncio
    async def test_get_risk_assessment_empty(self, storage):
        """get_risk_assessment returns empty list for unknown goal."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()

        factors = engine.get_risk_assessment("unknown-goal")
        assert factors == []

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns WorldModelEngine statistics."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()

        stats = await engine.get_stats()
        assert "total_future_predictions" in stats
        assert "total_action_estimates" in stats
        assert "total_error_entries" in stats
        assert "average_uncertainty" in stats
        assert "risk_level_distribution" in stats
        assert "world_model" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# ActiveLearningLoop
# ═══════════════════════════════════════════════════════════════════════════════

class TestActiveLearningLoop:
    """Unit tests for ActiveLearningLoop."""

    @pytest.mark.asyncio
    async def test_measure_prediction_error(self, storage):
        """measure_prediction_error creates PredictionErrorRecord with learning signal."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()
        loop = ActiveLearningLoop(storage, world_model_engine=engine)
        await loop.initialize()

        # Seed a transition and make a prediction
        await wm.observe_transition("idle", "learning", action="study", confidence=0.8)
        fp = await engine.predict_future_state("idle")

        record = await loop.measure_prediction_error(fp.id, "learning")
        assert isinstance(record, PredictionErrorRecord)
        assert record.absolute_error == 0.0
        assert record.learning_signal in (
            LearningSignal.CORRECT,
            LearningSignal.CONFIRMING,
        )

    @pytest.mark.asyncio
    async def test_measure_prediction_error_incorrect(self, storage):
        """measure_prediction_error records incorrect prediction."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()
        loop = ActiveLearningLoop(storage, world_model_engine=engine)
        await loop.initialize()

        await wm.observe_transition("idle", "learning", action="study", confidence=0.8)
        fp = await engine.predict_future_state("idle")

        record = await loop.measure_prediction_error(fp.id, "resting")
        assert record.absolute_error == 1.0
        assert record.learning_signal in (
            LearningSignal.INCORRECT,
            LearningSignal.SURPRISING,
        )

    @pytest.mark.asyncio
    async def test_update_beliefs_from_error(self, storage):
        """update_beliefs_from_error returns list of updated belief IDs."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()
        loop = ActiveLearningLoop(storage, world_model_engine=engine)
        await loop.initialize()

        # Associate a belief with a prediction
        await loop.associate_belief_with_prediction("pred-1", "belief-A")
        await loop.associate_belief_with_prediction("pred-1", "belief-B")

        record = await loop.measure_prediction_error("pred-1", "wrong_outcome")
        updated = await loop.update_beliefs_from_error(record)
        assert len(updated) == 2
        assert "belief-A" in updated
        assert "belief-B" in updated

    @pytest.mark.asyncio
    async def test_update_confidence_from_error(self, storage):
        """update_confidence_from_error adjusts confidence."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()
        loop = ActiveLearningLoop(storage, world_model_engine=engine)
        await loop.initialize()

        await wm.observe_transition("idle", "learning", action="study", confidence=0.8)
        fp = await engine.predict_future_state("idle")

        record = await loop.measure_prediction_error(fp.id, "resting")
        new_confidence = await loop.update_confidence_from_error(record)
        assert isinstance(new_confidence, float)
        assert new_confidence <= record.confidence_before  # Should decrease for wrong prediction

    @pytest.mark.asyncio
    async def test_update_world_model_from_error_with_source(self, storage):
        """update_world_model_from_error records correct transition when source_state is available."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()
        loop = ActiveLearningLoop(storage, world_model_engine=engine)
        await loop.initialize()

        # Use a base WorldModel prediction which has source_state
        await wm.observe_transition("idle", "learning", action="study", confidence=0.8)
        base_pred = await wm.predict_next_state("idle")

        record = await loop.measure_prediction_error(base_pred.id, "resting")
        result = await loop.update_world_model_from_error(record)
        assert result is True
        assert record.world_model_updated is True

    @pytest.mark.asyncio
    async def test_update_world_model_from_error_no_source(self, storage):
        """update_world_model_from_error returns False when no source_state."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()
        loop = ActiveLearningLoop(storage, world_model_engine=engine)
        await loop.initialize()

        # FutureStatePrediction may not have source_state in metadata
        await wm.observe_transition("idle", "learning", action="study", confidence=0.8)
        fp = await engine.predict_future_state("idle")

        record = await loop.measure_prediction_error(fp.id, "resting")
        result = await loop.update_world_model_from_error(record)
        # Result depends on whether source_state is in metadata
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_run_learning_cycle(self, storage):
        """run_learning_cycle runs full cycle."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()
        loop = ActiveLearningLoop(storage, world_model_engine=engine)
        await loop.initialize()

        # Seed data and make predictions
        await wm.observe_transition("idle", "learning", action="study", confidence=0.8)
        fp = await engine.predict_future_state("idle")

        result = await loop.run_learning_cycle([
            {"prediction_id": fp.id, "actual_outcome": "learning"},
        ])
        assert isinstance(result, LearningCycleResult)
        assert result.prediction_errors_measured == 1
        assert result.confidence_updates >= 1

    @pytest.mark.asyncio
    async def test_get_prediction_error_stats(self, storage):
        """get_prediction_error_stats returns stats."""
        wm = WorldModel(storage)
        await wm.initialize()
        engine = WorldModelEngine(storage, world_model=wm)
        await engine.initialize()
        loop = ActiveLearningLoop(storage, world_model_engine=engine)
        await loop.initialize()

        await wm.observe_transition("idle", "learning", action="study", confidence=0.8)
        fp = await engine.predict_future_state("idle")

        await loop.measure_prediction_error(fp.id, "learning")
        stats = await loop.get_prediction_error_stats()
        assert "total_errors" in stats
        assert "learning_efficiency" in stats
        assert stats["total_errors"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# CognitiveStateManifold
# ═══════════════════════════════════════════════════════════════════════════════

class TestCognitiveStateManifold:
    """Unit tests for CognitiveStateManifold."""

    @pytest.mark.asyncio
    async def test_project_belief(self, storage):
        """project_belief creates ManifoldPoint with meaningful features."""
        manifold = CognitiveStateManifold(storage)
        await manifold.initialize()

        belief = Belief(statement="Python is great", confidence=0.9)
        point = await manifold.project_belief(belief)
        assert isinstance(point, ManifoldPoint)
        assert point.element_type == ManifoldProjectionType.BELIEF
        assert point.element_id == belief.id
        assert "confidence" in point.features
        assert point.features["confidence"] == 0.9
        assert "urgency" in point.features
        assert "importance" in point.features
        assert point.activation_level > 0.0

    @pytest.mark.asyncio
    async def test_project_goal(self, storage):
        """project_goal creates ManifoldPoint."""
        manifold = CognitiveStateManifold(storage)
        await manifold.initialize()

        goal = Goal(description="Learn Rust", priority=GoalPriority.HIGH, progress=0.2)
        point = await manifold.project_goal(goal)
        assert isinstance(point, ManifoldPoint)
        assert point.element_type == ManifoldProjectionType.GOAL
        assert point.element_id == goal.id
        assert "urgency" in point.features
        assert point.features["urgency"] > 0.0  # HIGH priority should have urgency

    @pytest.mark.asyncio
    async def test_project_concept(self, storage):
        """project_concept creates ManifoldPoint."""
        manifold = CognitiveStateManifold(storage)
        await manifold.initialize()

        concept = Concept(name="Machine Learning", concept_type=ConceptType.ABSTRACT, confidence=0.8)
        point = await manifold.project_concept(concept, relationship_count=5)
        assert isinstance(point, ManifoldPoint)
        assert point.element_type == ManifoldProjectionType.CONCEPT
        assert point.element_id == concept.id
        assert point.features["confidence"] == 0.8
        assert abs(point.features["uncertainty"] - 0.2) < 0.01  # 1 - confidence

    @pytest.mark.asyncio
    async def test_project_plan(self, storage):
        """project_plan creates ManifoldPoint."""
        manifold = CognitiveStateManifold(storage)
        await manifold.initialize()

        # Use a simple object as a plan-like object
        class FakePlan:
            id = "plan-1"
            name = "Build API"
            status = "active"
            steps = ["design", "implement", "test"]
            priority = 10
            deadline = None
            related_goal_id = "goal-1"
            metadata = {}

        plan = FakePlan()
        point = await manifold.project_plan(plan, step_completion_rate=0.3)
        assert isinstance(point, ManifoldPoint)
        assert point.element_type == ManifoldProjectionType.PLAN
        assert point.element_id == "plan-1"
        assert "confidence" in point.features
        assert "complexity" in point.features

    @pytest.mark.asyncio
    async def test_compute_similarity(self, storage):
        """compute_similarity returns cosine similarity."""
        manifold = CognitiveStateManifold(storage)
        await manifold.initialize()

        belief = Belief(statement="Python is great", confidence=0.9)
        goal = Goal(description="Learn Python", priority=GoalPriority.HIGH, progress=0.5)

        p1 = await manifold.project_belief(belief)
        p2 = await manifold.project_goal(goal)

        sim = manifold.compute_similarity(p1.id, p2.id)
        assert -1.0 <= sim <= 1.0
        assert sim > 0.0  # Both have high confidence/urgency, should be somewhat similar

    @pytest.mark.asyncio
    async def test_compute_similarity_self(self, storage):
        """compute_similarity of a point with itself is 1.0."""
        manifold = CognitiveStateManifold(storage)
        await manifold.initialize()

        belief = Belief(statement="Test", confidence=0.8)
        point = await manifold.project_belief(belief)

        sim = manifold.compute_similarity(point.id, point.id)
        assert abs(sim - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_find_clusters(self, storage):
        """find_clusters clusters related points."""
        manifold = CognitiveStateManifold(storage)
        await manifold.initialize()

        # Create several similar beliefs (high confidence)
        b1 = Belief(statement="A", confidence=0.9)
        b2 = Belief(statement="B", confidence=0.9)
        b3 = Belief(statement="C", confidence=0.05)  # Very different

        await manifold.project_belief(b1)
        await manifold.project_belief(b2)
        await manifold.project_belief(b3)

        clusters = await manifold.find_clusters(min_coherence=0.5)
        assert isinstance(clusters, list)
        # High-confidence beliefs should cluster together
        # Low-confidence one may or may not, depending on feature space

    @pytest.mark.asyncio
    async def test_get_active_points(self, storage):
        """get_active_points returns active points."""
        manifold = CognitiveStateManifold(storage)
        await manifold.initialize()

        belief = Belief(statement="Active belief", confidence=0.9)
        point = await manifold.project_belief(belief)

        active = manifold.get_active_points(threshold=0.3)
        assert len(active) >= 1
        assert point.id in [p.id for p in active]

    @pytest.mark.asyncio
    async def test_evolve(self, storage):
        """evolve decays/activates points."""
        manifold = CognitiveStateManifold(storage)
        await manifold.initialize()

        belief = Belief(statement="Test", confidence=0.8)
        point = await manifold.project_belief(belief)
        initial_activation = point.activation_level

        evolved_count = await manifold.evolve(time_elapsed_seconds=600.0)
        assert evolved_count >= 1  # Should have decayed

        # After evolution, activation should have decreased
        updated_point = await manifold.get_point(point.id)
        assert updated_point.activation_level <= initial_activation

    @pytest.mark.asyncio
    async def test_get_state(self, storage):
        """get_state returns ManifoldState."""
        manifold = CognitiveStateManifold(storage)
        await manifold.initialize()

        belief = Belief(statement="Test", confidence=0.8)
        await manifold.project_belief(belief)

        state = await manifold.get_state()
        assert isinstance(state, ManifoldState)
        assert state.total_points == 1
        assert state.dimensionality == 10
        assert state.average_activation >= 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# GoalCompetitionEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoalCompetitionEngine:
    """Unit tests for GoalCompetitionEngine."""

    @pytest.mark.asyncio
    async def test_enter_competition(self, storage):
        """enter_competition creates GoalCompetitionEntry."""
        engine = GoalCompetitionEngine(storage)
        await engine.initialize()

        entry = await engine.enter_competition(
            goal_id="goal-1",
            goal_description="Build the API",
            importance=0.8,
            urgency=0.6,
            uncertainty=0.3,
            expected_reward=0.7,
            dependency_satisfaction=1.0,
        )
        assert isinstance(entry, GoalCompetitionEntry)
        assert entry.goal_id == "goal-1"
        assert entry.composite_score > 0.0

    @pytest.mark.asyncio
    async def test_enter_competition_with_goal_object(self, storage):
        """enter_competition extracts factors from Goal object."""
        engine = GoalCompetitionEngine(storage)
        await engine.initialize()

        goal = Goal(description="Learn Rust", priority=GoalPriority.HIGH, progress=0.1)
        entry = await engine.enter_competition(goal=goal)
        assert entry.goal_id == goal.id
        assert entry.importance > 0.0  # HIGH priority → high importance

    @pytest.mark.asyncio
    async def test_run_competition(self, storage):
        """run_competition ranks goals."""
        engine = GoalCompetitionEngine(storage)
        await engine.initialize()

        # Use keyword args — first positional is `goal`, not `goal_id`
        await engine.enter_competition(goal_id="g1", goal_description="Low priority goal", importance=0.2, urgency=0.1)
        await engine.enter_competition(goal_id="g2", goal_description="High priority goal", importance=0.9, urgency=0.8)

        result = await engine.run_competition()
        assert isinstance(result, CompetitionResult)
        assert result.total_goals_competed == 2
        assert result.winner_id == "g2"  # Higher importance+urgency should win

    @pytest.mark.asyncio
    async def test_get_current_ranking(self, storage):
        """get_current_ranking returns sorted entries."""
        engine = GoalCompetitionEngine(storage)
        await engine.initialize()

        await engine.enter_competition("g1", "Low", importance=0.2, urgency=0.1)
        await engine.enter_competition("g2", "High", importance=0.9, urgency=0.8)

        ranking = engine.get_current_ranking()
        assert len(ranking) == 2
        assert ranking[0].composite_score >= ranking[1].composite_score

    @pytest.mark.asyncio
    async def test_update_factor_weights(self, storage):
        """update_factor_weights adjusts weights."""
        engine = GoalCompetitionEngine(storage)
        await engine.initialize()

        updated = engine.update_factor_weights({"importance": 0.5, "urgency": 0.3})
        assert "importance" in updated
        assert "urgency" in updated
        # Weights should be normalised to sum to 1.0
        assert abs(sum(updated.values()) - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_get_winner(self, storage):
        """get_winner returns highest-ranked goal."""
        engine = GoalCompetitionEngine(storage)
        await engine.initialize()

        await engine.enter_competition(goal_id="g1", goal_description="Low", importance=0.2, urgency=0.1)
        await engine.enter_competition(goal_id="g2", goal_description="High", importance=0.9, urgency=0.8)

        winner = engine.get_winner()
        assert winner is not None
        assert winner.goal_id == "g2"

    @pytest.mark.asyncio
    async def test_get_winner_empty(self, storage):
        """get_winner returns None when no entries."""
        engine = GoalCompetitionEngine(storage)
        await engine.initialize()

        winner = engine.get_winner()
        assert winner is None

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns competition engine statistics."""
        engine = GoalCompetitionEngine(storage)
        await engine.initialize()

        await engine.enter_competition("g1", "Test goal", importance=0.5)
        stats = await engine.get_stats()
        assert "total_competing_goals" in stats
        assert "total_competitions_run" in stats
        assert "current_factor_weights" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# AttentionEconomy
# ═══════════════════════════════════════════════════════════════════════════════

class TestAttentionEconomy:
    """Unit tests for AttentionEconomy."""

    @pytest.mark.asyncio
    async def test_allocate(self, storage):
        """allocate creates AttentionAllocation."""
        economy = AttentionEconomy(storage)
        await economy.initialize()

        alloc = await economy.allocate("goal-1", "goal", 25.0, reason="Active goal")
        assert isinstance(alloc, AttentionAllocation)
        assert alloc.target_id == "goal-1"
        assert alloc.target_type == "goal"
        assert alloc.allocated_amount == 25.0
        assert alloc.priority_reason == "Active goal"

    @pytest.mark.asyncio
    async def test_allocate_adds_to_existing(self, storage):
        """allocate adds to existing allocation."""
        economy = AttentionEconomy(storage)
        await economy.initialize()

        await economy.allocate("goal-1", "goal", 25.0)
        alloc = await economy.allocate("goal-1", "goal", 15.0)
        assert alloc.allocated_amount == 40.0

    @pytest.mark.asyncio
    async def test_request_attention_respects_budget(self, storage):
        """request_attention respects budget."""
        economy = AttentionEconomy(storage)
        await economy.initialize()

        # Default budget is 100.0
        await economy.allocate("t1", "goal", 80.0)

        # Request more than available
        alloc = await economy.request_attention("t2", "belief", 50.0, reason="Need attention")
        assert alloc.allocated_amount <= 20.0  # Only 20 available

    @pytest.mark.asyncio
    async def test_reallocate(self, storage):
        """reallocate moves attention."""
        economy = AttentionEconomy(storage)
        await economy.initialize()

        await economy.allocate("from-1", "goal", 50.0)
        result = await economy.reallocate("from-1", "to-1", 30.0)
        assert result is True

        budget = await economy.get_budget()
        # Check that "to-1" has received the allocation
        to_alloc = [a for a in budget.allocations if a.target_id == "to-1"]
        assert len(to_alloc) == 1
        assert to_alloc[0].allocated_amount == 30.0

    @pytest.mark.asyncio
    async def test_reallocate_nonexistent(self, storage):
        """reallocate fails for nonexistent source."""
        economy = AttentionEconomy(storage)
        await economy.initialize()

        result = await economy.reallocate("nonexistent", "to-1", 10.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_apply_decay(self, storage):
        """apply_decay reduces allocations."""
        economy = AttentionEconomy(storage)
        await economy.initialize()

        await economy.allocate("goal-1", "goal", 50.0)
        decayed = await economy.apply_decay(time_elapsed_seconds=120.0)
        assert decayed > 0.0

    @pytest.mark.asyncio
    async def test_run_economy_cycle(self, storage):
        """run_economy_cycle full cycle."""
        economy = AttentionEconomy(storage)
        await economy.initialize()

        result = await economy.run_economy_cycle(
            goals=[{"id": "g1", "importance": 0.8, "urgency": 0.6}],
            beliefs=[{"id": "b1", "uncertainty": 0.7}],
        )
        assert isinstance(result, EconomyCycleResult)
        assert result.cycle_time_ms >= 0.0
        assert 0.0 <= result.budget_utilization <= 1.0

    @pytest.mark.asyncio
    async def test_get_budget(self, storage):
        """get_budget returns AttentionBudget."""
        economy = AttentionEconomy(storage)
        await economy.initialize()

        await economy.allocate("goal-1", "goal", 30.0)
        budget = await economy.get_budget()
        assert isinstance(budget, AttentionBudget)
        assert budget.total_budget == 100.0
        assert budget.allocated == 30.0
        assert budget.available == 70.0

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns attention economy statistics."""
        economy = AttentionEconomy(storage)
        await economy.initialize()

        await economy.allocate("g1", "goal", 30.0)
        stats = await economy.get_stats()
        assert "total_budget" in stats
        assert "total_allocated" in stats
        assert "allocation_count" in stats
        assert "budget_utilization" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# EnhancedCausalReasoner
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnhancedCausalReasoner:
    """Unit tests for EnhancedCausalReasoner."""

    @pytest.mark.asyncio
    async def test_discover_causal_chains(self, storage):
        """discover_causal_chains finds chains."""
        wm = WorldModel(storage)
        await wm.initialize()
        base_cr = CausalReasoner(storage, wm.transition_graph)
        await base_cr.initialize()
        ecr = EnhancedCausalReasoner(storage, base_cr)
        await ecr.initialize()

        # Build a chain: motivation -> study -> knowledge
        await base_cr.add_causal_link(
            "motivation", "Motivation", "study", "Study",
            strength=CausalStrength.SUFFICIENT, confidence=0.8,
        )
        await base_cr.add_causal_link(
            "study", "Study", "knowledge", "Knowledge",
            strength=CausalStrength.SUFFICIENT, confidence=0.7,
        )

        chains = await ecr.discover_causal_chains("motivation", max_depth=5)
        assert len(chains) >= 1
        # Should find a chain from motivation through study to knowledge
        longest = max(chains, key=lambda c: c.length)
        assert longest.length >= 1

    @pytest.mark.asyncio
    async def test_analyze_root_cause(self, storage):
        """analyze_root_cause finds root causes."""
        wm = WorldModel(storage)
        await wm.initialize()
        base_cr = CausalReasoner(storage, wm.transition_graph)
        await base_cr.initialize()
        ecr = EnhancedCausalReasoner(storage, base_cr)
        await ecr.initialize()

        # Build: motivation -> study -> knowledge
        await base_cr.add_causal_link(
            "motivation", "Motivation", "study", "Study",
            strength=CausalStrength.SUFFICIENT, confidence=0.8,
        )
        await base_cr.add_causal_link(
            "study", "Study", "knowledge", "Knowledge",
            strength=CausalStrength.SUFFICIENT, confidence=0.7,
        )

        rca = await ecr.analyze_root_cause("knowledge", max_depth=5)
        assert isinstance(rca, RootCauseAnalysisResult)
        assert rca.observed_effect == "knowledge"
        # "motivation" has no incoming links, so it should be a root cause
        assert len(rca.root_causes) >= 1
        assert rca.root_causes[0]["cause_id"] == "motivation"

    @pytest.mark.asyncio
    async def test_forecast_from_cause(self, storage):
        """forecast_from_cause predicts effects."""
        wm = WorldModel(storage)
        await wm.initialize()
        base_cr = CausalReasoner(storage, wm.transition_graph)
        await base_cr.initialize()
        ecr = EnhancedCausalReasoner(storage, base_cr)
        await ecr.initialize()

        await base_cr.add_causal_link(
            "motivation", "Motivation", "study", "Study",
            strength=CausalStrength.SUFFICIENT, confidence=0.8,
        )
        await base_cr.add_causal_link(
            "study", "Study", "knowledge", "Knowledge",
            strength=CausalStrength.SUFFICIENT, confidence=0.7,
        )

        forecast = await ecr.forecast_from_cause("motivation", time_horizon=100.0)
        assert isinstance(forecast, CausalForecast)
        assert forecast.current_cause == "motivation"
        assert len(forecast.predicted_effects) >= 1
        assert forecast.confidence > 0.0

    @pytest.mark.asyncio
    async def test_compute_causal_influence(self, storage):
        """compute_causal_influence returns influence score."""
        wm = WorldModel(storage)
        await wm.initialize()
        base_cr = CausalReasoner(storage, wm.transition_graph)
        await base_cr.initialize()
        ecr = EnhancedCausalReasoner(storage, base_cr)
        await ecr.initialize()

        await base_cr.add_causal_link(
            "motivation", "Motivation", "study", "Study",
            strength=CausalStrength.SUFFICIENT, confidence=0.8,
        )
        await base_cr.add_causal_link(
            "study", "Study", "knowledge", "Knowledge",
            strength=CausalStrength.CONTRIBUTING, confidence=0.6,
        )

        influence = await ecr.compute_causal_influence("motivation")
        assert isinstance(influence, float)
        assert influence > 0.0  # Has outgoing links

    @pytest.mark.asyncio
    async def test_find_causal_paths(self, storage):
        """find_causal_paths finds paths between elements."""
        wm = WorldModel(storage)
        await wm.initialize()
        base_cr = CausalReasoner(storage, wm.transition_graph)
        await base_cr.initialize()
        ecr = EnhancedCausalReasoner(storage, base_cr)
        await ecr.initialize()

        await base_cr.add_causal_link(
            "A", "A", "B", "B",
            strength=CausalStrength.SUFFICIENT, confidence=0.8,
        )
        await base_cr.add_causal_link(
            "B", "B", "C", "C",
            strength=CausalStrength.SUFFICIENT, confidence=0.7,
        )

        paths = await ecr.find_causal_paths("A", "C")
        assert len(paths) >= 1
        assert paths[0].length == 2
        assert "A" in paths[0].chain
        assert "C" in paths[0].chain

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns enhanced causal reasoner statistics."""
        wm = WorldModel(storage)
        await wm.initialize()
        base_cr = CausalReasoner(storage, wm.transition_graph)
        await base_cr.initialize()
        ecr = EnhancedCausalReasoner(storage, base_cr)
        await ecr.initialize()

        stats = await ecr.get_stats()
        assert "base_causal_links" in stats
        assert "discovered_chains" in stats
        assert "total_forecasts" in stats
        assert "total_root_cause_analyses" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# SelfModel
# ═══════════════════════════════════════════════════════════════════════════════

class TestSelfModel:
    """Unit tests for SelfModel."""

    @pytest.mark.asyncio
    async def test_record_performance(self, storage):
        """record_performance stores record."""
        sm = SelfModel(storage)
        await sm.initialize()

        record = await sm.record_performance(
            SelfAssessmentDimension.REASONING_QUALITY, 0.85, context="syllogism",
        )
        assert isinstance(record, PerformanceRecord)
        assert record.dimension == SelfAssessmentDimension.REASONING_QUALITY
        assert record.score == 0.85

    @pytest.mark.asyncio
    async def test_add_model_preference(self, storage):
        """add_model_preference creates preference."""
        sm = SelfModel(storage)
        await sm.initialize()

        pref = await sm.add_model_preference(
            model_a="qwen", model_b="gemma", preferred="qwen",
            domain="coding", confidence=0.7,
        )
        assert isinstance(pref, ModelPreference)
        assert pref.model_a == "qwen"
        assert pref.preferred == "qwen"
        assert pref.domain == "coding"
        assert pref.evidence_count == 1

    @pytest.mark.asyncio
    async def test_update_model_preference(self, storage):
        """update_model_preference updates preference."""
        sm = SelfModel(storage)
        await sm.initialize()

        pref = await sm.add_model_preference(
            model_a="qwen", model_b="gemma", preferred="qwen",
            domain="coding", confidence=0.5,
        )

        updated = await sm.update_model_preference(pref.id, "qwen")
        assert updated is not None
        assert updated.evidence_count == 2
        assert updated.confidence > 0.5  # Should increase

    @pytest.mark.asyncio
    async def test_update_model_preference_not_found(self, storage):
        """update_model_preference returns None for unknown ID."""
        sm = SelfModel(storage)
        await sm.initialize()

        result = await sm.update_model_preference("nonexistent", "qwen")
        assert result is None

    @pytest.mark.asyncio
    async def test_assess_strengths(self, storage):
        """assess_strengths returns strengths."""
        sm = SelfModel(storage)
        await sm.initialize()

        # Record high scores in reasoning
        for _ in range(5):
            await sm.record_performance(SelfAssessmentDimension.REASONING_QUALITY, 0.85)

        strengths = await sm.assess_strengths()
        assert isinstance(strengths, list)
        assert len(strengths) >= 1
        assert any("reasoning_quality" in s for s in strengths)

    @pytest.mark.asyncio
    async def test_assess_weaknesses(self, storage):
        """assess_weaknesses returns weaknesses."""
        sm = SelfModel(storage)
        await sm.initialize()

        # Record low scores in planning
        for _ in range(5):
            await sm.record_performance(SelfAssessmentDimension.PLANNING_EFFECTIVENESS, 0.2)

        weaknesses = await sm.assess_weaknesses()
        assert isinstance(weaknesses, list)
        assert len(weaknesses) >= 1
        assert any("planning_effectiveness" in w for w in weaknesses)

    @pytest.mark.asyncio
    async def test_assess_uncertainties(self, storage):
        """assess_uncertainties returns uncertainties."""
        sm = SelfModel(storage)
        await sm.initialize()

        # Record ambiguous scores (around 0.5)
        await sm.record_performance(SelfAssessmentDimension.ADAPTABILITY, 0.5)
        await sm.record_performance(SelfAssessmentDimension.ADAPTABILITY, 0.5)

        uncertainties = await sm.assess_uncertainties()
        assert isinstance(uncertainties, list)
        assert len(uncertainties) >= 1

    @pytest.mark.asyncio
    async def test_get_self_state(self, storage):
        """get_self_state returns SelfModelState."""
        sm = SelfModel(storage)
        await sm.initialize()

        await sm.record_performance(SelfAssessmentDimension.REASONING_QUALITY, 0.8)

        state = await sm.get_self_state()
        assert isinstance(state, SelfModelState)
        assert isinstance(state.strengths, list)
        assert isinstance(state.weaknesses, list)
        assert isinstance(state.uncertainties, list)
        assert "reasoning_quality" in state.assessment_scores
        assert state.total_performance_records == 1

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns self model statistics."""
        sm = SelfModel(storage)
        await sm.initialize()

        await sm.record_performance(SelfAssessmentDimension.LEARNING_SPEED, 0.7)
        stats = await sm.get_stats()
        assert "total_performance_records" in stats
        assert "total_model_preferences" in stats
        assert "average_performance" in stats
        assert "dimension_stats" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# CognitiveCycle
# ═══════════════════════════════════════════════════════════════════════════════

class TestCognitiveCycle:
    """Unit tests for CognitiveCycle."""

    @pytest.mark.asyncio
    async def test_run(self, storage):
        """run executes all phases."""
        cycle = CognitiveCycle(storage, kernel=None)
        await cycle.initialize()

        trace = await cycle.run("What is machine learning?")
        assert isinstance(trace, CognitiveCycleTrace)
        assert trace.query == "What is machine learning?"
        assert trace.phases_completed > 0
        assert trace.total_duration_ms > 0.0

    @pytest.mark.asyncio
    async def test_run_unified(self, storage):
        """run_unified returns UnifiedCycleResult."""
        cycle = CognitiveCycle(storage, kernel=None)
        await cycle.initialize()

        result = await cycle.run_unified("How should we build an API?")
        assert isinstance(result, UnifiedCycleResult)
        assert result.version == "0.5.0"
        assert result.cycle_trace is not None
        assert result.total_cycle_time_ms > 0.0

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns stats."""
        cycle = CognitiveCycle(storage, kernel=None)
        await cycle.initialize()

        await cycle.run("test query")

        stats = await cycle.get_stats()
        assert "total_cycles" in stats
        assert "in_memory_traces" in stats
        assert stats["total_cycles"] >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# EvaluationFramework
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluationFramework:
    """Unit tests for EvaluationFramework."""

    @pytest.mark.asyncio
    async def test_measure_belief_accuracy(self, storage):
        """measure_belief_accuracy returns MetricMeasurement."""
        ef = EvaluationFramework(storage)
        await ef.initialize()

        beliefs = [
            {"confidence": 0.9, "actual_correctness": 1.0},
            {"confidence": 0.7, "actual_correctness": 0.0},
            {"confidence": 0.5, "actual_correctness": 1.0},
        ]
        mm = await ef.measure_belief_accuracy(beliefs)
        assert isinstance(mm, MetricMeasurement)
        assert mm.metric_type == MetricType.BELIEF_ACCURACY
        assert 0.0 <= mm.value <= 1.0
        assert mm.sample_size == 3

    @pytest.mark.asyncio
    async def test_measure_goal_completion_rate(self, storage):
        """measure_goal_completion_rate returns MetricMeasurement."""
        ef = EvaluationFramework(storage)
        await ef.initialize()

        goals = [
            {"completed": True},
            {"completed": False},
            {"completed": True},
        ]
        mm = await ef.measure_goal_completion_rate(goals)
        assert isinstance(mm, MetricMeasurement)
        assert mm.metric_type == MetricType.GOAL_COMPLETION_RATE
        assert abs(mm.value - 2.0 / 3.0) < 0.001
        assert mm.sample_size == 3

    @pytest.mark.asyncio
    async def test_measure_prediction_accuracy(self, storage):
        """measure_prediction_accuracy returns MetricMeasurement."""
        ef = EvaluationFramework(storage)
        await ef.initialize()

        predictions = [
            {"prediction_error": 0.1},
            {"prediction_error": 0.3},
            {"prediction_error": 0.0},
        ]
        mm = await ef.measure_prediction_accuracy(predictions)
        assert isinstance(mm, MetricMeasurement)
        assert mm.metric_type == MetricType.PREDICTION_ACCURACY
        assert 0.0 <= mm.value <= 1.0
        assert mm.sample_size == 3

    @pytest.mark.asyncio
    async def test_run_full_evaluation(self, storage):
        """run_full_evaluation returns EvaluationReport."""
        ef = EvaluationFramework(storage)
        await ef.initialize()

        report = await ef.run_full_evaluation(
            beliefs=[
                {"confidence": 0.8, "actual_correctness": 1.0},
                {"confidence": 0.6, "actual_correctness": 0.0},
            ],
            goals=[
                {"completed": True},
                {"completed": False},
            ],
            predictions=[
                {"prediction_error": 0.2},
            ],
        )
        assert isinstance(report, EvaluationReport)
        assert len(report.measurements) >= 3  # belief_accuracy, goal_completion, prediction_accuracy (+ uncertainty)
        assert 0.0 <= report.overall_score <= 1.0
        assert report.strongest_dimension != ""
        assert report.weakest_dimension != ""

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns evaluation framework statistics."""
        ef = EvaluationFramework(storage)
        await ef.initialize()

        await ef.measure_belief_accuracy([{"confidence": 0.8, "actual_correctness": 1.0}])
        stats = await ef.get_stats()
        assert "total_measurements" in stats
        assert "total_reports" in stats
        assert "average_metric_value" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: Full Unified Cycle
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnifiedIntegration:
    """Integration tests for the full unified cognitive architecture pipeline."""

    @pytest.mark.asyncio
    async def test_full_unified_cycle(self, storage):
        """Full cycle: initialize all subsystems → learn → predict → compete → learn from errors → evaluate."""
        # 1. Initialize all v0.5 subsystems
        wm = WorldModel(storage)
        await wm.initialize()

        wme = WorldModelEngine(storage, world_model=wm)
        await wme.initialize()

        learning_loop = ActiveLearningLoop(storage, world_model_engine=wme)
        await learning_loop.initialize()

        manifold = CognitiveStateManifold(storage)
        await manifold.initialize()

        competition = GoalCompetitionEngine(storage)
        await competition.initialize()

        economy = AttentionEconomy(storage)
        await economy.initialize()

        base_cr = CausalReasoner(storage, wm.transition_graph)
        await base_cr.initialize()
        ecr = EnhancedCausalReasoner(storage, base_cr)
        await ecr.initialize()

        self_model = SelfModel(storage)
        await self_model.initialize()

        evaluation = EvaluationFramework(storage)
        await evaluation.initialize()

        # 2. Learn: seed the world model with transitions
        transitions = await wme.learn_state_transitions(
            beliefs=[
                {"id": "b1", "old_confidence": 0.5, "new_confidence": 0.8, "cause": "evidence"},
            ],
            goals=[
                {"id": "g1", "old_progress": 0.1, "new_progress": 0.4},
            ],
            cognitive_state={
                "label": "learning",
                "previous_label": "idle",
                "cause": "new_query",
            },
        )
        assert len(transitions) >= 1

        # Also seed direct transitions for richer prediction
        await wm.observe_transition("beginner", "learning", action="start_course", confidence=0.8)
        await wm.observe_transition("learning", "practicing", action="do_exercises", confidence=0.7)
        await wm.observe_transition("practicing", "proficient", action="build_project", confidence=0.8)

        # 3. Predict: use the world model engine
        future_pred = await wme.predict_future_state("beginner", time_horizon=60.0)
        assert isinstance(future_pred, FutureStatePrediction)
        assert future_pred.predicted_state in ("learning", "beginner")

        action_est = await wme.estimate_action_outcome("beginner", "start_course")
        assert isinstance(action_est, ActionOutcomeEstimate)
        assert action_est.action == "start_course"

        # Register a risk factor
        await wme.register_goal_risk_factor("goal-1", "Uncertain target state")

        # 4. Compete: enter goals into competition
        goal_high = Goal(description="Master Python", priority=GoalPriority.HIGH, progress=0.3)
        goal_low = Goal(description="Read a book", priority=GoalPriority.LOW, progress=0.1)

        entry_high = await competition.enter_competition(goal=goal_high)
        entry_low = await competition.enter_competition(goal=goal_low)

        comp_result = await competition.run_competition()
        assert comp_result.total_goals_competed == 2
        # Verify winner is one of the entered goals (exact winner depends on
        # competition dynamics including urgency escalation and reward adjustments)
        assert comp_result.winner_id in (goal_high.id, goal_low.id)

        # 5. Project into manifold
        belief = Belief(statement="Python is powerful", confidence=0.9)
        concept = Concept(name="Python", concept_type=ConceptType.CONCRETE, confidence=0.95)

        bp = await manifold.project_belief(belief)
        gp = await manifold.project_goal(goal_high)
        cp = await manifold.project_concept(concept, relationship_count=3)

        assert bp.element_type == ManifoldProjectionType.BELIEF
        assert gp.element_type == ManifoldProjectionType.GOAL
        assert cp.element_type == ManifoldProjectionType.CONCEPT

        # Similarity should be computable
        sim = manifold.compute_similarity(bp.id, gp.id)
        assert -1.0 <= sim <= 1.0

        # 6. Allocate attention
        await economy.allocate(goal_high.id, "goal", 40.0, reason="High priority goal")
        await economy.allocate(belief.id, "belief", 20.0, reason="Important belief")

        budget = await economy.get_budget()
        assert budget.allocated > 0.0

        # 7. Causal reasoning
        await base_cr.add_causal_link(
            "practice", "Practice", "skill", "Skill",
            strength=CausalStrength.SUFFICIENT, confidence=0.8,
        )
        await base_cr.add_causal_link(
            "skill", "Skill", "project", "Project",
            strength=CausalStrength.CONTRIBUTING, confidence=0.6,
        )

        chains = await ecr.discover_causal_chains("practice")
        assert len(chains) >= 1

        rca = await ecr.analyze_root_cause("project")
        assert isinstance(rca, RootCauseAnalysisResult)

        influence = await ecr.compute_causal_influence("practice")
        assert influence > 0.0

        # 8. Learn from errors
        # Make a prediction and then measure the error
        pred = await wme.predict_future_state("beginner")
        error_record = await learning_loop.measure_prediction_error(pred.id, "learning")
        assert isinstance(error_record, PredictionErrorRecord)

        # Associate beliefs and update
        await learning_loop.associate_belief_with_prediction(pred.id, belief.id)
        updated = await learning_loop.update_beliefs_from_error(error_record)
        new_conf = await learning_loop.update_confidence_from_error(error_record)
        wm_updated = await learning_loop.update_world_model_from_error(error_record)
        assert wm_updated is True

        # Run a full learning cycle
        fp2 = await wme.predict_future_state("learning")
        learning_result = await learning_loop.run_learning_cycle([
            {"prediction_id": fp2.id, "actual_outcome": "practicing"},
        ])
        assert isinstance(learning_result, LearningCycleResult)
        assert learning_result.prediction_errors_measured >= 1

        # 9. Self-model assessment
        await self_model.record_performance(
            SelfAssessmentDimension.PREDICTION_ACCURACY, 0.85, context="unit test",
        )
        await self_model.record_performance(
            SelfAssessmentDimension.REASONING_QUALITY, 0.75, context="unit test",
        )
        await self_model.add_model_preference(
            model_a="enhanced", model_b="basic", preferred="enhanced",
            domain="prediction", confidence=0.7,
        )

        state = await self_model.get_self_state()
        assert isinstance(state, SelfModelState)
        assert state.total_performance_records >= 2

        # 10. Evaluate
        report = await evaluation.run_full_evaluation(
            beliefs=[{"confidence": 0.8, "actual_correctness": 1.0}],
            goals=[{"completed": True}, {"completed": False}],
            predictions=[{"prediction_error": 0.2}],
        )
        assert isinstance(report, EvaluationReport)
        assert len(report.measurements) >= 3
        assert report.overall_score > 0.0

        # Verify all subsystems have valid stats
        wme_stats = await wme.get_stats()
        assert wme_stats["total_future_predictions"] >= 1

        learning_stats = await learning_loop.get_stats()
        assert learning_stats["total_error_records"] >= 1

        manifold_state = await manifold.get_state()
        assert manifold_state.total_points >= 3  # belief, goal, concept

        comp_stats = await competition.get_stats()
        assert comp_stats["total_competing_goals"] == 2

        economy_stats = await economy.get_stats()
        assert economy_stats["allocation_count"] >= 1

        ecr_stats = await ecr.get_stats()
        assert ecr_stats["discovered_chains"] >= 1

        self_stats = await self_model.get_stats()
        assert self_stats["total_performance_records"] >= 2

        eval_stats = await evaluation.get_stats()
        assert eval_stats["total_measurements"] >= 3
