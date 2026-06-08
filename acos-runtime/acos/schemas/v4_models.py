"""
Pydantic data models for ACOS Runtime v0.4 — World Model & Predictive Cognition.

Extends v0.3 models with:
- State Transitions: observed state changes, action outcomes
- World Model: learned dynamics, future predictions
- Outcome Prediction: success/failure probabilities, resource estimates
- Simulation: future rollouts, scenario comparison
- Causal Reasoning: causal links, interventions, counterfactual causality
- Goal Forecasting: achievability, failure prediction, recommended actions
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


# ─── State Transition Models ──────────────────────────────────────────────────

class TransitionType(str, Enum):
    DETERMINISTIC = "deterministic"   # Always A -> B
    PROBABILISTIC = "probabilistic"   # A -> B with probability p
    CONDITIONAL = "conditional"       # A -> B given condition C
    STOCHASTIC = "stochastic"         # A -> {B, C, D} with distribution


class StateTransition(BaseModel):
    """An observed or inferred state transition.

    Represents: State A --action--> State B
    with frequency, confidence, and cost metrics.
    """
    id: str = Field(default_factory=gen_id)
    source_state: str                          # Description/hash of source state
    target_state: str                          # Description/hash of target state
    action: str = ""                           # The action that triggers the transition
    transition_type: TransitionType = TransitionType.PROBABILISTIC

    # Tracking metrics
    frequency: int = 1                         # How often this transition has been observed
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)  # Confidence in this transition
    cost: float = Field(default=0.0, ge=0.0)  # Resource cost of the transition
    duration_estimate: float = Field(default=0.0, ge=0.0)   # Expected time in seconds

    # Context
    preconditions: list[str] = Field(default_factory=list)  # Required conditions
    side_effects: list[str] = Field(default_factory=list)   # Unintended consequences
    metadata: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class StateVector(BaseModel):
    """A snapshot of the cognitive state at a point in time.

    Represents a 'state' in the state transition graph.
    """
    id: str = Field(default_factory=gen_id)
    label: str
    features: dict[str, float] = Field(default_factory=dict)  # State feature vector
    belief_ids: list[str] = Field(default_factory=list)
    goal_ids: list[str] = Field(default_factory=list)
    concept_ids: list[str] = Field(default_factory=list)
    uncertainty_level: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=utc_now)


# ─── World Model Models ───────────────────────────────────────────────────────

class PredictionType(str, Enum):
    STATE_PREDICTION = "state_prediction"       # Predict a future state
    ACTION_OUTCOME = "action_outcome"           # Predict outcome of an action
    GOAL_COMPLETION = "goal_completion"         # Predict goal completion probability
    TRAJECTORY = "trajectory"                   # Predict a sequence of states


class Prediction(BaseModel):
    """A prediction about a future state or outcome."""
    id: str = Field(default_factory=gen_id)
    prediction_type: PredictionType
    description: str

    # What is being predicted
    source_state: str = ""                      # Starting state
    predicted_state: str = ""                   # Predicted future state
    action: str = ""                            # Action being predicted (if applicable)
    goal_id: str | None = None                  # Goal being forecast (if applicable)

    # Prediction metrics
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    time_horizon: float = Field(default=0.0, ge=0.0)  # How far into the future (seconds)
    probability: float = Field(default=0.5, ge=0.0, le=1.0)  # Probability of this outcome

    # Supporting evidence
    transition_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    reasoning_chain: list[str] = Field(default_factory=list)

    # Validation
    is_verified: bool = False
    actual_outcome: str | None = None
    prediction_error: float | None = None       # |predicted - actual| once verified

    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    verified_at: datetime | None = None


class WorldModelState(BaseModel):
    """Current state of the world model."""
    id: str = Field(default_factory=gen_id)
    total_transitions: int = 0
    total_predictions: int = 0
    verified_predictions: int = 0
    average_prediction_accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    model_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Outcome Predictor Models ─────────────────────────────────────────────────

class OutcomePrediction(BaseModel):
    """Prediction of a specific outcome."""
    id: str = Field(default_factory=gen_id)
    action: str
    context: str = ""                           # Context in which the action is taken

    # Probabilities
    success_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    failure_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    partial_success_probability: float = Field(default=0.0, ge=0.0, le=1.0)

    # Resource estimates
    expected_duration: float = Field(default=0.0, ge=0.0)      # In seconds
    expected_resources: float = Field(default=0.0, ge=0.0)     # Abstract resource units
    duration_variance: float = Field(default=0.0, ge=0.0)      # Uncertainty in duration

    # Risk assessment
    risk_factors: list[str] = Field(default_factory=list)
    mitigating_factors: list[str] = Field(default_factory=list)
    worst_case_outcome: str = ""
    best_case_outcome: str = ""

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_transition_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


# ─── Simulation Models ────────────────────────────────────────────────────────

class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimulationStep(BaseModel):
    """A single step in a simulation rollout."""
    id: str = Field(default_factory=gen_id)
    step_number: int
    state: str                                  # State at this step
    action: str = ""                            # Action taken at this step
    predicted_next_state: str = ""              # Where we predict to go
    transition_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    cumulative_cost: float = Field(default=0.0, ge=0.0)
    cumulative_probability: float = Field(default=1.0, ge=0.0, le=1.0)
    observations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SimulationRun(BaseModel):
    """A complete simulation rollout."""
    id: str = Field(default_factory=gen_id)
    name: str = ""
    description: str = ""
    status: SimulationStatus = SimulationStatus.PENDING

    # Configuration
    initial_state: str = ""
    planned_actions: list[str] = Field(default_factory=list)
    max_steps: int = 10
    confidence_threshold: float = Field(default=0.1, ge=0.0, le=1.0)

    # Results
    steps: list[SimulationStep] = Field(default_factory=list)
    final_state: str = ""
    total_cost: float = 0.0
    final_probability: float = Field(default=1.0, ge=0.0, le=1.0)
    goal_achieved: bool = False
    goal_id: str | None = None

    # Comparison
    alternative_run_ids: list[str] = Field(default_factory=list)
    is_best_alternative: bool = False

    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class ScenarioComparison(BaseModel):
    """Comparison of multiple simulation scenarios."""
    id: str = Field(default_factory=gen_id)
    scenario_ids: list[str] = Field(default_factory=list)
    best_scenario_id: str | None = None
    comparison_criteria: list[str] = Field(default_factory=list)
    rankings: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    created_at: datetime = Field(default_factory=utc_now)


# ─── Causal Reasoning Models ──────────────────────────────────────────────────

class CausalDirection(str, Enum):
    FORWARD = "forward"           # Cause -> Effect
    BACKWARD = "backward"         # Effect -> Cause (diagnostic)
    BIDIRECTIONAL = "bidirectional"  # Both directions possible


class CausalStrength(str, Enum):
    NECESSARY = "necessary"       # Cause is necessary for effect
    SUFFICIENT = "sufficient"     # Cause alone produces effect
    CONTRIBUTING = "contributing" # Cause contributes but isn't sufficient
    INHIBITING = "inhibiting"     # Cause prevents/inhibits effect


class CausalLink(BaseModel):
    """A causal relationship between two elements.

    Represents: Cause -> Effect
    """
    id: str = Field(default_factory=gen_id)
    cause_id: str                                # ID of the causing element
    cause_label: str                             # Human-readable cause
    effect_id: str                               # ID of the affected element
    effect_label: str                            # Human-readable effect

    # Causal properties
    direction: CausalDirection = CausalDirection.FORWARD
    strength: CausalStrength = CausalStrength.CONTRIBUTING
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    # Evidence
    supporting_observations: int = 0             # Times this causal link was observed
    contradicting_observations: int = 0          # Times the cause didn't produce the effect
    intervention_evidence: int = 0               # Times we intervened and confirmed

    # Mechanism
    mechanism: str = ""                          # How the cause produces the effect
    mediator_ids: list[str] = Field(default_factory=list)  # Intermediate causes
    confounder_ids: list[str] = Field(default_factory=list)  # Potential confounders

    # Context
    preconditions: list[str] = Field(default_factory=list)
    context_description: str = ""

    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class InterventionResult(BaseModel):
    """Result of an intervention analysis (do-calculus style)."""
    id: str = Field(default_factory=gen_id)
    intervention_target: str                     # What we're intervening on
    intervention_value: str                      # What we're setting it to
    original_value: str                          # What it was before

    # Predicted effects
    predicted_effects: list[dict[str, Any]] = Field(default_factory=list)
    affected_goal_ids: list[str] = Field(default_factory=list)
    affected_belief_ids: list[str] = Field(default_factory=list)

    # Causal paths
    causal_paths: list[list[str]] = Field(default_factory=list)  # Paths from intervention to effects
    confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    reasoning_chain: list[str] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class CausalDiscoveryResult(BaseModel):
    """Result of a causal discovery operation."""
    id: str = Field(default_factory=gen_id)
    discovered_links: list[CausalLink] = Field(default_factory=list)
    rejected_links: list[CausalLink] = Field(default_factory=list)
    ambiguous_links: list[CausalLink] = Field(default_factory=list)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    total_observations_used: int = 0
    discovery_time_ms: float = 0.0
    created_at: datetime = Field(default_factory=utc_now)


# ─── Goal Forecast Models ─────────────────────────────────────────────────────

class GoalFeasibility(str, Enum):
    HIGHLY_ACHIEVABLE = "highly_achievable"     # >80% probability
    LIKELY_ACHIEVABLE = "likely_achievable"     # 60-80% probability
    POSSIBLE = "possible"                       # 40-60% probability
    UNLIKELY = "unlikely"                       # 20-40% probability
    PROBABLY_INFEASIBLE = "probably_infeasible"  # <20% probability


class GoalForecast(BaseModel):
    """A forecast for a specific goal."""
    id: str = Field(default_factory=gen_id)
    goal_id: str
    goal_description: str = ""

    # Feasibility assessment
    feasibility: GoalFeasibility = GoalFeasibility.POSSIBLE
    success_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    failure_probability: float = Field(default=0.5, ge=0.0, le=1.0)

    # Timeline
    estimated_steps_remaining: int = 0
    estimated_duration: float = Field(default=0.0, ge=0.0)  # In seconds
    estimated_completion_date: datetime | None = None

    # Risk factors
    blocking_factors: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    dependency_risks: list[str] = Field(default_factory=list)

    # Recommendations
    recommended_next_actions: list[str] = Field(default_factory=list)
    prerequisite_goals: list[str] = Field(default_factory=list)
    alternative_approaches: list[str] = Field(default_factory=list)

    # Supporting data
    supporting_transition_ids: list[str] = Field(default_factory=list)
    supporting_causal_ids: list[str] = Field(default_factory=list)
    simulation_run_ids: list[str] = Field(default_factory=list)

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class GoalForecastReport(BaseModel):
    """A comprehensive goal forecast report."""
    id: str = Field(default_factory=gen_id)
    forecasts: list[GoalForecast] = Field(default_factory=list)
    total_goals_assessed: int = 0
    achievable_count: int = 0
    unlikely_count: int = 0
    infeasible_count: int = 0
    top_priority_action: str = ""
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utc_now)


# ─── Predictive Cycle Result ──────────────────────────────────────────────────

class PredictiveCycleResult(BaseModel):
    """Result of a complete predictive cognition cycle."""
    id: str = Field(default_factory=gen_id)
    predictions_made: int = 0
    transitions_learned: int = 0
    causal_links_discovered: int = 0
    simulations_run: int = 0
    goals_forecasted: int = 0
    goal_forecast_report: GoalForecastReport | None = None
    world_model_state: WorldModelState | None = None
    cycle_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)
