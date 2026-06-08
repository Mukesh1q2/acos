"""
Pydantic data models for ACOS Runtime v0.5 — Unified Cognitive Architecture.

Extends v0.4 models with:
- World Model Engine: enhanced prediction, risk estimation, uncertainty quantification
- Active Learning Loop: prediction error tracking, belief/confidence/model updates
- Cognitive State Manifold: unified latent representation, similarity, clustering
- Goal Competition: dynamic prioritization, competition results
- Attention Economy: resource allocation, budget tracking
- Enhanced Causal Reasoner: causal chains, root cause, forecasting
- Self Model: strengths, weaknesses, performance history, model preferences
- Cognitive Cycle: complete loop execution trace
- Evaluation Framework: benchmarks, metrics, historical performance
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def gen_id() -> str:
    return str(uuid.uuid4())


# ─── World Model Engine Models ────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FutureStatePrediction(BaseModel):
    """A prediction about a future state with confidence and risk."""
    id: str = Field(default_factory=gen_id)
    predicted_state: str
    probability: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_factors: list[str] = Field(default_factory=list)
    time_horizon_seconds: float = Field(default=0.0, ge=0.0)
    assumptions: list[str] = Field(default_factory=list)
    reasoning_chain: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ActionOutcomeEstimate(BaseModel):
    """Estimate of an action's outcome with full risk/uncertainty profile."""
    id: str = Field(default_factory=gen_id)
    action: str
    expected_outcome: str = ""
    success_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    failure_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.5, ge=0.0, le=1.0)
    expected_duration: float = Field(default=0.0, ge=0.0)
    expected_cost: float = Field(default=0.0, ge=0.0)
    risk_factors: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


# ─── Active Learning Loop Models ──────────────────────────────────────────────

class LearningSignal(str, Enum):
    CORRECT = "correct"          # Prediction matched outcome
    INCORRECT = "incorrect"      # Prediction was wrong
    PARTIAL = "partial"          # Partially correct
    SURPRISING = "surprising"    # Unexpected outcome (high prediction error)
    CONFIRMING = "confirming"    # Outcome confirmed existing belief


class PredictionErrorRecord(BaseModel):
    """A first-class record of prediction error."""
    id: str = Field(default_factory=gen_id)
    prediction_id: str
    predicted_value: str = ""
    actual_value: str = ""
    absolute_error: float = Field(default=0.0, ge=0.0)
    squared_error: float = Field(default=0.0, ge=0.0)
    learning_signal: LearningSignal = LearningSignal.PARTIAL
    belief_ids_updated: list[str] = Field(default_factory=list)
    confidence_before: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence_after: float = Field(default=0.5, ge=0.0, le=1.0)
    world_model_updated: bool = False
    reflection: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class LearningCycleResult(BaseModel):
    """Result of one active learning cycle."""
    id: str = Field(default_factory=gen_id)
    prediction_errors_measured: int = 0
    beliefs_updated: int = 0
    confidence_updates: int = 0
    world_model_transitions_learned: int = 0
    surprise_count: int = 0
    confirmation_count: int = 0
    average_prediction_error: float = Field(default=0.0, ge=0.0, le=1.0)
    learning_efficiency: float = Field(default=0.0, ge=0.0, le=1.0)
    cycle_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Cognitive State Manifold Models ──────────────────────────────────────────

class ManifoldProjectionType(str, Enum):
    BELIEF = "belief"
    GOAL = "goal"
    MEMORY = "memory"
    CONCEPT = "concept"
    UNCERTAINTY = "uncertainty"
    PLAN = "plan"


class ManifoldPoint(BaseModel):
    """A point in the cognitive state manifold.

    Each point represents a projection of a cognitive element into a
    common latent space defined by meaningful features.
    """
    id: str = Field(default_factory=gen_id)
    element_id: str                              # ID of the source element
    element_type: ManifoldProjectionType
    label: str = ""

    # Meaningful feature vector (NOT placeholder)
    features: dict[str, float] = Field(default_factory=dict)
    # Default feature keys:
    #   confidence, urgency, importance, activation, uncertainty,
    #   connectivity, recency, relevance, complexity, familiarity

    cluster_id: str | None = None
    activation_level: float = Field(default=0.0, ge=0.0, le=1.0)
    last_activated: datetime = Field(default_factory=utc_now)

    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ManifoldCluster(BaseModel):
    """A cluster of related cognitive elements in the manifold."""
    id: str = Field(default_factory=gen_id)
    label: str = ""
    point_ids: list[str] = Field(default_factory=list)
    centroid_features: dict[str, float] = Field(default_factory=dict)
    coherence: float = Field(default=0.0, ge=0.0, le=1.0)  # How coherent the cluster is
    dominant_type: ManifoldProjectionType | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ManifoldState(BaseModel):
    """Current state of the cognitive manifold."""
    id: str = Field(default_factory=gen_id)
    total_points: int = 0
    total_clusters: int = 0
    average_activation: float = Field(default=0.0, ge=0.0, le=1.0)
    dimensionality: int = 0
    dominant_cluster_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Goal Competition Models ──────────────────────────────────────────────────

class CompetitionFactor(str, Enum):
    IMPORTANCE = "importance"
    URGENCY = "urgency"
    UNCERTAINTY = "uncertainty"
    EXPECTED_REWARD = "expected_reward"
    DEPENDENCY_SATISFACTION = "dependency_satisfaction"
    ATTENTION_SCORE = "attention_score"
    PROGRESS_MOMENTUM = "progress_momentum"


class GoalCompetitionEntry(BaseModel):
    """A goal's entry in a competition round."""
    id: str = Field(default_factory=gen_id)
    goal_id: str
    goal_description: str = ""

    # Factor scores
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    urgency: float = Field(default=0.5, ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.5, ge=0.0, le=1.0)
    expected_reward: float = Field(default=0.5, ge=0.0, le=1.0)
    dependency_satisfaction: float = Field(default=0.5, ge=0.0, le=1.0)
    attention_score: float = Field(default=0.0, ge=0.0, le=1.0)
    progress_momentum: float = Field(default=0.0, ge=0.0, le=1.0)

    # Computed
    composite_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rank: int = 0

    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class CompetitionResult(BaseModel):
    """Result of a goal competition round."""
    id: str = Field(default_factory=gen_id)
    entries: list[GoalCompetitionEntry] = Field(default_factory=list)
    winner_id: str | None = None
    total_goals_competed: int = 0
    competition_time_ms: float = 0.0
    factor_weights: dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Attention Economy Models ─────────────────────────────────────────────────

class ResourceType(str, Enum):
    COMPUTATION = "computation"
    MEMORY = "memory"
    ATTENTION = "attention"
    REASONING = "reasoning"


class AttentionAllocation(BaseModel):
    """An allocation of attention to a specific target."""
    id: str = Field(default_factory=gen_id)
    target_id: str
    target_type: str  # belief, goal, concept, contradiction
    allocated_amount: float = Field(default=0.0, ge=0.0)
    priority_reason: str = ""
    decay_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    granted_at: datetime = Field(default_factory=utc_now)


class AttentionBudget(BaseModel):
    """Current attention budget state."""
    id: str = Field(default_factory=gen_id)
    total_budget: float = Field(default=100.0, ge=0.0)
    allocated: float = Field(default=0.0, ge=0.0)
    available: float = Field(default=100.0, ge=0.0)
    allocations: list[AttentionAllocation] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class EconomyCycleResult(BaseModel):
    """Result of an attention economy cycle."""
    id: str = Field(default_factory=gen_id)
    total_allocated: float = 0.0
    total_decayed: float = 0.0
    new_allocations: int = 0
    expired_allocations: int = 0
    top_targets: list[str] = Field(default_factory=list)
    budget_utilization: float = Field(default=0.0, ge=0.0, le=1.0)
    cycle_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Enhanced Causal Reasoner Models ──────────────────────────────────────────

class CausalChain(BaseModel):
    """A chain of causal links: A -> B -> C -> ..."""
    id: str = Field(default_factory=gen_id)
    chain: list[str] = Field(default_factory=list)  # Ordered list of element IDs
    labels: list[str] = Field(default_factory=list)  # Human-readable labels
    cumulative_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    total_strength: float = Field(default=0.0, ge=0.0)
    length: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class RootCauseAnalysisResult(BaseModel):
    """Result of a root cause analysis."""
    id: str = Field(default_factory=gen_id)
    observed_effect: str
    root_causes: list[dict[str, Any]] = Field(default_factory=list)
    # Each: {"cause_id": str, "cause_label": str, "confidence": float,
    #        "chain": list[str], "evidence_count": int}
    contributing_factors: list[dict[str, Any]] = Field(default_factory=list)
    analysis_depth: int = 0
    confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    reasoning_chain: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class CausalForecast(BaseModel):
    """A forecast based on causal reasoning."""
    id: str = Field(default_factory=gen_id)
    current_cause: str
    predicted_effects: list[dict[str, Any]] = Field(default_factory=list)
    # Each: {"effect_id": str, "effect_label": str, "probability": float,
    #        "time_delay": float, "mechanism": str}
    confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    time_horizon: float = Field(default=0.0, ge=0.0)
    reasoning_chain: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


# ─── Self Model Models ────────────────────────────────────────────────────────

class SelfAssessmentDimension(str, Enum):
    REASONING_QUALITY = "reasoning_quality"
    PREDICTION_ACCURACY = "prediction_accuracy"
    PLANNING_EFFECTIVENESS = "planning_effectiveness"
    MEMORY_RETRIEVAL = "memory_retrieval"
    GOAL_COMPLETION = "goal_completion"
    LEARNING_SPEED = "learning_speed"
    ADAPTABILITY = "adaptability"


class ModelPreference(BaseModel):
    """A learned preference about which model/approach works better."""
    id: str = Field(default_factory=gen_id)
    model_a: str
    model_b: str
    preferred: str  # Which model is preferred
    domain: str = ""  # e.g., "coding", "analysis", "creative"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_count: int = 0
    last_updated: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)


class PerformanceRecord(BaseModel):
    """A historical performance record."""
    id: str = Field(default_factory=gen_id)
    dimension: SelfAssessmentDimension
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    context: str = ""
    session_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class SelfModelState(BaseModel):
    """Current state of the self model."""
    id: str = Field(default_factory=gen_id)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    assessment_scores: dict[str, float] = Field(default_factory=dict)
    model_preferences: list[ModelPreference] = Field(default_factory=list)
    total_performance_records: int = 0
    average_performance: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Cognitive Cycle Models ───────────────────────────────────────────────────

class CyclePhase(str, Enum):
    OBSERVE = "observe"
    ACTIVATE_CONCEPTS = "activate_concepts"
    RETRIEVE_MEMORIES = "retrieve_memories"
    RETRIEVE_BELIEFS = "retrieve_beliefs"
    ACTIVATE_GOALS = "activate_goals"
    PREDICT_OUTCOMES = "predict_outcomes"
    GENERATE_PLANS = "generate_plans"
    SIMULATE_ALTERNATIVES = "simulate_alternatives"
    SELECT_STRATEGY = "select_strategy"
    EXECUTE_THREADS = "execute_threads"
    VERIFY = "verify"
    REFLECT = "reflect"
    CONSOLIDATE = "consolidate"
    UPDATE_WORLD_MODEL = "update_world_model"
    UPDATE_COGNITIVE_STATE = "update_cognitive_state"
    LEARN = "learn"
    EVOLVE = "evolve"


class PhaseResult(BaseModel):
    """Result of a single phase in the cognitive cycle."""
    id: str = Field(default_factory=gen_id)
    phase: CyclePhase
    success: bool = True
    duration_ms: float = 0.0
    items_processed: int = 0
    items_produced: int = 0
    summary: str = ""
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class CognitiveCycleTrace(BaseModel):
    """Complete trace of a cognitive cycle execution."""
    id: str = Field(default_factory=gen_id)
    query: str = ""
    phase_results: list[PhaseResult] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    phases_completed: int = 0
    phases_failed: int = 0
    final_synthesis: str = ""
    learning_applied: bool = False
    world_model_updated: bool = False
    beliefs_changed: int = 0
    goals_reprioritized: int = 0
    predictions_made: int = 0
    prediction_errors_measured: int = 0
    self_model_updated: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Evaluation Framework Models ──────────────────────────────────────────────

class MetricType(str, Enum):
    BELIEF_ACCURACY = "belief_accuracy"
    GOAL_COMPLETION_RATE = "goal_completion_rate"
    PREDICTION_ACCURACY = "prediction_accuracy"
    CONTRADICTION_RESOLUTION_RATE = "contradiction_resolution_rate"
    UNCERTAINTY_CALIBRATION = "uncertainty_calibration"
    PLANNING_QUALITY = "planning_quality"
    MEMORY_RETRIEVAL_QUALITY = "memory_retrieval_quality"
    LEARNING_EFFICIENCY = "learning_efficiency"
    CAUSAL_REASONING_ACCURACY = "causal_reasoning_accuracy"
    ATTENTION_ALLOCATION_EFFICIENCY = "attention_allocation_efficiency"


class MetricMeasurement(BaseModel):
    """A single metric measurement."""
    id: str = Field(default_factory=gen_id)
    metric_type: MetricType
    value: float = Field(default=0.0, ge=0.0, le=1.0)
    baseline: float = Field(default=0.0, ge=0.0, le=1.0)
    improvement: float = Field(default=0.0)  # value - baseline
    sample_size: int = 0
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    context: str = ""
    timestamp: datetime = Field(default_factory=utc_now)


class EvaluationReport(BaseModel):
    """A comprehensive evaluation report."""
    id: str = Field(default_factory=gen_id)
    measurements: list[MetricMeasurement] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    strongest_dimension: str = ""
    weakest_dimension: str = ""
    improvement_areas: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class HistoricalPerformance(BaseModel):
    """Historical performance tracking."""
    id: str = Field(default_factory=gen_id)
    metric_type: MetricType
    measurements: list[MetricMeasurement] = Field(default_factory=list)
    trend: str = "stable"  # improving, declining, stable
    current_value: float = Field(default=0.0, ge=0.0, le=1.0)
    best_value: float = Field(default=0.0, ge=0.0, le=1.0)
    worst_value: float = Field(default=0.0, ge=0.0, le=1.0)
    updated_at: datetime = Field(default_factory=utc_now)


# ─── Unified v0.5 Cycle Result ───────────────────────────────────────────────

class UnifiedCycleResult(BaseModel):
    """Result of a complete unified cognitive cycle (v0.5)."""
    id: str = Field(default_factory=gen_id)
    cycle_trace: CognitiveCycleTrace | None = None
    learning_result: LearningCycleResult | None = None
    competition_result: CompetitionResult | None = None
    economy_result: EconomyCycleResult | None = None
    evaluation_report: EvaluationReport | None = None
    self_model_state: SelfModelState | None = None
    manifold_state: ManifoldState | None = None
    total_cycle_time_ms: float = 0.0
    version: str = "0.5.0"
    timestamp: datetime = Field(default_factory=utc_now)
