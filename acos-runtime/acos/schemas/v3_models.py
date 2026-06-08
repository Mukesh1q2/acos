"""
Pydantic data models for ACOS Runtime v0.3 — Cognitive Dynamics Engine.

Extends v0.2 models with:
- Attention: focus tracking, decay, reinforcement
- Uncertainty: unknowns, conflicting beliefs, missing evidence
- Plan State: plans, subplans, dependencies, outcomes
- Cognitive Graph: unified graph node/edge types
- State Evolution: evolution operators, state deltas
- Counterfactual: what-if scenarios, alternative plans
- Dynamics Engine: orchestration records
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


# ─── Attention Models ──────────────────────────────────────────────────────────

class AttentionTargetType(str, Enum):
    CONCEPT = "concept"
    BELIEF = "belief"
    GOAL = "goal"
    MEMORY = "memory"
    PLAN = "plan"


class AttentionFocus(BaseModel):
    """A focus entry tracking attention on a cognitive element."""
    id: str = Field(default_factory=gen_id)
    target_id: str
    target_type: AttentionTargetType
    focus_score: float = Field(default=1.0, ge=0.0, le=1.0)
    reinforcement_count: int = 0
    last_reinforced: datetime = Field(default_factory=utc_now)
    decay_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AttentionSnapshot(BaseModel):
    """A snapshot of the current attention state."""
    id: str = Field(default_factory=gen_id)
    active_concepts: list[AttentionFocus] = Field(default_factory=list)
    active_goals: list[AttentionFocus] = Field(default_factory=list)
    active_beliefs: list[AttentionFocus] = Field(default_factory=list)
    total_focus: float = Field(default=0.0, ge=0.0)
    peak_focus_target_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Uncertainty Models ────────────────────────────────────────────────────────

class UncertaintyType(str, Enum):
    KNOWLEDGE_GAP = "knowledge_gap"         # Unknown information
    CONFLICT = "conflict"                   # Conflicting beliefs
    MISSING_EVIDENCE = "missing_evidence"   # Insufficient evidence
    CONFIDENCE_DRIFT = "confidence_drift"   # Confidence changing rapidly
    AMBIGUITY = "ambiguity"                 # Multiple valid interpretations
    ASSUMPTION = "assumption"               # Unverified assumption


class UncertaintyEntry(BaseModel):
    """An identified uncertainty in the cognitive system."""
    id: str = Field(default_factory=gen_id)
    uncertainty_type: UncertaintyType
    description: str
    related_ids: list[str] = Field(default_factory=list)
    severity: float = Field(default=0.5, ge=0.0, le=1.0)
    impact_on_planning: float = Field(default=0.5, ge=0.0, le=1.0)
    resolution_suggestion: str = ""
    is_resolved: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None


class UncertaintyReport(BaseModel):
    """A comprehensive uncertainty assessment."""
    id: str = Field(default_factory=gen_id)
    entries: list[UncertaintyEntry] = Field(default_factory=list)
    total_uncertainty: float = Field(default=0.0, ge=0.0, le=1.0)
    high_severity_count: int = 0
    planning_impact_score: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Plan State Models ────────────────────────────────────────────────────────

class PlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    REVISED = "revised"


class PlanStep(BaseModel):
    """A single step within a plan."""
    id: str = Field(default_factory=gen_id)
    description: str
    order: int = 0
    status: PlanStatus = PlanStatus.DRAFT
    expected_outcome: str = ""
    actual_outcome: str = ""
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    related_goal_ids: list[str] = Field(default_factory=list)
    related_concept_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Plan(BaseModel):
    """A plan with subplans, dependencies, and outcome tracking."""
    id: str = Field(default_factory=gen_id)
    name: str
    description: str = ""
    status: PlanStatus = PlanStatus.DRAFT
    steps: list[PlanStep] = Field(default_factory=list)
    subplan_ids: list[str] = Field(default_factory=list)
    parent_plan_id: str | None = None
    dependency_ids: list[str] = Field(default_factory=list)
    expected_outcome: str = ""
    actual_outcome: str = ""
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    related_goal_ids: list[str] = Field(default_factory=list)
    related_belief_ids: list[str] = Field(default_factory=list)
    related_concept_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


# ─── Cognitive Graph Models ────────────────────────────────────────────────────

class CognitiveNodeType(str, Enum):
    CONCEPT = "concept"
    BELIEF = "belief"
    GOAL = "goal"
    MEMORY = "memory"
    PLAN = "plan"
    UNCERTAINTY = "uncertainty"


class CognitiveEdgeType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DEPENDS_ON = "depends_on"
    RELATES_TO = "relates_to"
    EVOLVES_TO = "evolves_to"
    IMPLIES = "implies"
    CAUSES = "causes"
    IS_A = "is_a"
    PART_OF = "part_of"
    ADDRESSES = "addresses"
    BLOCKS = "blocks"
    REINFORCES = "reinforces"
    WEAKENS = "weakens"


class CognitiveNode(BaseModel):
    """A node in the unified cognitive graph."""
    id: str = Field(default_factory=gen_id)
    node_type: CognitiveNodeType
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    attention_score: float = Field(default=0.0, ge=0.0, le=1.0)
    activation_level: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CognitiveEdge(BaseModel):
    """An edge in the unified cognitive graph."""
    id: str = Field(default_factory=gen_id)
    source_id: str
    target_id: str
    edge_type: CognitiveEdgeType
    weight: float = Field(default=1.0, ge=0.0)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


# ─── State Evolution Models ────────────────────────────────────────────────────

class EvolutionOperator(str, Enum):
    REINFORCE = "reinforce"         # Strengthen a successful belief
    WEAKEN = "weaken"               # Weaken a contradictory belief
    PROMOTE = "promote"             # Elevate a useful concept
    SUPPRESS = "suppress"           # Demote an irrelevant concept
    CONSOLIDATE = "consolidate"     # Merge similar beliefs
    DIVERGE = "diverge"             # Split ambiguous beliefs
    DECAY = "decay"                 # Natural decay over time
    RESOLVE = "resolve"             # Resolve a contradiction


class StateDelta(BaseModel):
    """A single change to the cognitive state."""
    id: str = Field(default_factory=gen_id)
    operator: EvolutionOperator
    target_type: CognitiveNodeType
    target_id: str
    before_value: float = 0.0
    after_value: float = 0.0
    delta: float = 0.0
    reason: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class EvolutionResult(BaseModel):
    """Result of a state evolution cycle."""
    id: str = Field(default_factory=gen_id)
    deltas: list[StateDelta] = Field(default_factory=list)
    beliefs_reinforced: int = 0
    beliefs_weakened: int = 0
    concepts_promoted: int = 0
    concepts_suppressed: int = 0
    contradictions_resolved: int = 0
    total_changes: int = 0
    evolution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Counterfactual Models ─────────────────────────────────────────────────────

class CounterfactualType(str, Enum):
    WHAT_IF = "what_if"                     # "If X happens, what follows?"
    NEGATION = "negation"                   # "What if X were false?"
    ALTERNATIVE = "alternative"             # "What alternative plans exist?"
    INTERVENTION = "intervention"           # "What if we change X to Y?"


class CounterfactualScenario(BaseModel):
    """A counterfactual reasoning scenario."""
    id: str = Field(default_factory=gen_id)
    scenario_type: CounterfactualType
    premise: str                             # The hypothetical premise
    original_state: dict[str, Any] = Field(default_factory=dict)
    modified_state: dict[str, Any] = Field(default_factory=dict)
    predicted_outcomes: list[str] = Field(default_factory=list)
    affected_belief_ids: list[str] = Field(default_factory=list)
    affected_goal_ids: list[str] = Field(default_factory=list)
    affected_concept_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    reasoning_chain: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class CounterfactualResult(BaseModel):
    """Result of a counterfactual reasoning operation."""
    id: str = Field(default_factory=gen_id)
    query: str
    scenario_type: CounterfactualType
    scenarios: list[CounterfactualScenario] = Field(default_factory=list)
    best_scenario_id: str | None = None
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning_time_ms: float = 0.0
    created_at: datetime = Field(default_factory=utc_now)


# ─── Dynamics Engine Models ────────────────────────────────────────────────────

class DynamicsCycleResult(BaseModel):
    """Result of a complete cognitive dynamics cycle."""
    id: str = Field(default_factory=gen_id)
    belief_updates: int = 0
    goal_competitions: int = 0
    uncertainty_propagations: int = 0
    memory_reinforcements: int = 0
    attention_shifts: int = 0
    state_deltas: list[StateDelta] = Field(default_factory=list)
    evolution_result: EvolutionResult | None = None
    uncertainty_report: UncertaintyReport | None = None
    attention_snapshot: AttentionSnapshot | None = None
    cycle_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)
