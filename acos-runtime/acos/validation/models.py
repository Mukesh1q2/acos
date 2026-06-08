"""
Data models for ACOS Validation Lab v1.0.

Pydantic models for all validation results including:
- Benchmark results and test cases
- Comparison and tournament results
- Statistical significance and confidence intervals
- Failure reports and emergence reports
- Scientific reports
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


# ─── Enums ─────────────────────────────────────────────────────────────────────

class BenchmarkCategory(str, Enum):
    MEMORY = "memory"
    PLANNING = "planning"
    REASONING = "reasoning"
    LEARNING = "learning"
    PREDICTION = "prediction"


class BenchmarkMetric(str, Enum):
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    CALIBRATION_ERROR = "calibration_error"
    BRIER_SCORE = "brier_score"
    COMPLETION_RATE = "completion_rate"
    LATENCY_MS = "latency_ms"
    COST_TOKENS = "cost_tokens"


class FailureType(str, Enum):
    BELIEF_COLLAPSE = "belief_collapse"
    CONTRADICTION_ACCUMULATION = "contradiction_accumulation"
    MEMORY_CORRUPTION = "memory_corruption"
    GOAL_OSCILLATION = "goal_oscillation"
    PLANNING_LOOP = "planning_loop"
    PREDICTION_DRIFT = "prediction_drift"


class EmergenceType(str, Enum):
    PLANNING = "planning"
    MEMORY = "memory"
    ADAPTATION = "adaptation"
    REASONING = "reasoning"
    SELF_CORRECTION = "self_correction"


class SignificanceLevel(str, Enum):
    NOT_SIGNIFICANT = "not_significant"
    MARGINAL = "marginal"          # p < 0.10
    SIGNIFICANT = "significant"    # p < 0.05
    HIGHLY_SIGNIFICANT = "highly_significant"  # p < 0.01


class SystemType(str, Enum):
    ACOS = "acos"
    DIRECT_LLM = "direct_llm"
    MEMORY_RAG = "memory_rag"
    REACT = "react"
    LANGGRAPH = "langgraph"
    MULTI_AGENT = "multi_agent"


# ─── Test Case Models ──────────────────────────────────────────────────────────

class MemoryTestCase(BaseModel):
    """Test case for memory benchmarks."""
    id: str = Field(default_factory=gen_id)
    query: str
    expected_facts: list[str] = Field(default_factory=list)
    context: str = ""
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0)
    delay_steps: int = 0  # Steps between learning and recall
    interference_items: int = 0  # Distractor items
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlanningTestCase(BaseModel):
    """Test case for planning benchmarks."""
    id: str = Field(default_factory=gen_id)
    goal: str
    subgoals: list[str] = Field(default_factory=list)
    dependencies: list[tuple[str, str]] = Field(default_factory=list)  # (a, b) means a must precede b
    constraints: list[str] = Field(default_factory=list)
    optimal_steps: int = 0
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReasoningTestCase(BaseModel):
    """Test case for reasoning benchmarks."""
    id: str = Field(default_factory=gen_id)
    premises: list[str] = Field(default_factory=list)
    question: str
    correct_answer: str
    reasoning_type: str = "deductive"  # deductive, inductive, causal, counterfactual
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0)
    distractors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LearningTestCase(BaseModel):
    """Test case for learning benchmarks."""
    id: str = Field(default_factory=gen_id)
    initial_belief: str = ""
    evidence_sequence: list[dict[str, Any]] = Field(default_factory=list)
    expected_belief: str = ""
    expected_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PredictionTestCase(BaseModel):
    """Test case for prediction benchmarks."""
    id: str = Field(default_factory=gen_id)
    scenario: str
    initial_state: dict[str, Any] = Field(default_factory=dict)
    action: str = ""
    expected_outcome: str = ""
    expected_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    time_horizon: float = 1.0
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─── Benchmark Result Models ───────────────────────────────────────────────────

class BenchmarkScore(BaseModel):
    """Score for a single metric in a benchmark."""
    metric: BenchmarkMetric
    value: float
    stderr: float = 0.0
    min_value: float = 0.0
    max_value: float = 1.0
    sample_size: int = 0


class BenchmarkResult(BaseModel):
    """Result of running a single benchmark."""
    id: str = Field(default_factory=gen_id)
    benchmark_name: str
    category: BenchmarkCategory
    system_name: str
    scores: list[BenchmarkScore] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    execution_time_ms: float = 0.0
    test_case_count: int = 0
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkSuiteResult(BaseModel):
    """Result of running the full benchmark suite."""
    id: str = Field(default_factory=gen_id)
    system_name: str
    results: list[BenchmarkResult] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    category_scores: dict[str, float] = Field(default_factory=dict)
    total_execution_time_ms: float = 0.0
    total_test_cases: int = 0
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Comparison & Tournament Models ────────────────────────────────────────────

class SignificanceResult(BaseModel):
    """Statistical significance test result."""
    test_name: str = "welch_t"  # welch_t, mann_whitney_u, bootstrap
    statistic: float = 0.0
    p_value: float = 1.0
    significance_level: SignificanceLevel = SignificanceLevel.NOT_SIGNIFICANT
    confidence_interval_diff: tuple[float, float] = (0.0, 0.0)
    effect_size_cohens_d: float = 0.0
    sample_size_a: int = 0
    sample_size_b: int = 0


class SystemBenchmarkTrace(BaseModel):
    """Trace of a single system's performance on a benchmark."""
    system_name: str
    system_type: SystemType
    scores: list[float] = Field(default_factory=list)
    mean_score: float = 0.0
    std_score: float = 0.0
    median_score: float = 0.0
    min_score: float = 0.0
    max_score: float = 0.0
    total_latency_ms: float = 0.0
    total_cost: float = 0.0


class ComparisonResult(BaseModel):
    """Result of an A/B comparison between two systems."""
    id: str = Field(default_factory=gen_id)
    system_a_name: str
    system_b_name: str
    benchmark_name: str
    system_a_trace: SystemBenchmarkTrace | None = None
    system_b_trace: SystemBenchmarkTrace | None = None
    significance: SignificanceResult | None = None
    winner: str = ""
    margin: float = 0.0
    n_cases: int = 0
    timestamp: datetime = Field(default_factory=utc_now)


class TournamentResult(BaseModel):
    """Result of a tournament across multiple systems."""
    id: str = Field(default_factory=gen_id)
    systems: list[str] = Field(default_factory=list)
    comparisons: list[ComparisonResult] = Field(default_factory=list)
    rankings: list[tuple[str, float]] = Field(default_factory=list)  # (system, score) sorted
    best_system: str = ""
    worst_system: str = ""
    n_cases: int = 0
    total_execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Failure Analysis Models ───────────────────────────────────────────────────

class FailureReport(BaseModel):
    """Report of a detected failure mode."""
    id: str = Field(default_factory=gen_id)
    failure_type: FailureType
    detected: bool = False
    severity: float = Field(default=0.0, ge=0.0, le=1.0)
    description: str = ""
    affected_components: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class FailureAnalysisReport(BaseModel):
    """Comprehensive failure analysis report."""
    id: str = Field(default_factory=gen_id)
    system_name: str
    failure_reports: list[FailureReport] = Field(default_factory=list)
    total_failures_detected: int = 0
    most_severe_failure: FailureType | None = None
    overall_health: float = Field(default=1.0, ge=0.0, le=1.0)
    recommendations: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Emergence Analysis Models ─────────────────────────────────────────────────

class EmergenceIndicator(BaseModel):
    """A single indicator of emergent behavior."""
    name: str
    acos_value: float = 0.0
    best_baseline_value: float = 0.0
    improvement_factor: float = 0.0
    is_emergent: bool = False  # True if improvement exceeds threshold
    threshold: float = 1.5  # Minimum improvement factor to count as emergent


class EmergenceReport(BaseModel):
    """Report on emergent behavior analysis."""
    id: str = Field(default_factory=gen_id)
    emergence_type: EmergenceType
    indicators: list[EmergenceIndicator] = Field(default_factory=list)
    emergence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    strongest_emergence: str = ""
    analysis_summary: str = ""
    timestamp: datetime = Field(default_factory=utc_now)


class EmergenceAnalysisResult(BaseModel):
    """Complete emergence analysis across all types."""
    id: str = Field(default_factory=gen_id)
    reports: list[EmergenceReport] = Field(default_factory=list)
    overall_emergence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    emergent_capabilities: list[str] = Field(default_factory=list)
    non_emergent_capabilities: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Cognitive Metrics Models ──────────────────────────────────────────────────

class CognitiveMetricResult(BaseModel):
    """Result of a cognitive metric computation."""
    metric_name: str
    value: float = 0.0
    interpretation: str = ""
    percentile_vs_baseline: float = 0.0
    is_above_baseline: bool = False


class CognitiveMetricsResult(BaseModel):
    """Complete cognitive metrics computation result."""
    id: str = Field(default_factory=gen_id)
    system_name: str
    metrics: list[CognitiveMetricResult] = Field(default_factory=list)
    overall_cognitive_score: float = Field(default=0.0, ge=0.0, le=1.0)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Scientific Report Models ──────────────────────────────────────────────────

class ExperimentDesign(BaseModel):
    """Description of the experimental design."""
    n_systems: int = 0
    n_benchmarks: int = 0
    n_test_cases: int = 0
    systems_tested: list[str] = Field(default_factory=list)
    benchmarks_run: list[str] = Field(default_factory=list)
    methodology: str = ""


class CostAnalysis(BaseModel):
    """Cost analysis of running the systems."""
    system_costs: dict[str, float] = Field(default_factory=dict)  # system -> cost
    performance_per_cost: dict[str, float] = Field(default_factory=dict)
    most_efficient: str = ""


class ScientificReport(BaseModel):
    """Complete scientific report from validation."""
    id: str = Field(default_factory=gen_id)
    title: str = "ACOS Validation Lab Report"
    version: str = "1.0"

    # Sections
    experiment_design: ExperimentDesign | None = None
    benchmark_results: list[BenchmarkResult] = Field(default_factory=list)
    comparison_results: list[ComparisonResult] = Field(default_factory=list)
    tournament_result: TournamentResult | None = None
    cognitive_metrics: CognitiveMetricsResult | None = None
    failure_analysis: FailureAnalysisReport | None = None
    emergence_analysis: EmergenceAnalysisResult | None = None
    cost_analysis: CostAnalysis | None = None

    # Summary
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommended_changes: list[str] = Field(default_factory=list)
    conclusion: str = ""

    # Metadata
    total_execution_time_ms: float = 0.0
    generated_at: datetime = Field(default_factory=utc_now)


# ─── Validation Run Config ─────────────────────────────────────────────────────

class ValidationConfig(BaseModel):
    """Configuration for a validation run."""
    n_test_cases: int = 100
    n_cases_ab_test: int = 1000
    confidence_level: float = 0.95
    emergence_threshold: float = 1.5
    include_baselines: list[SystemType] = Field(
        default_factory=lambda: [
            SystemType.DIRECT_LLM,
            SystemType.MEMORY_RAG,
            SystemType.REACT,
            SystemType.LANGGRAPH,
            SystemType.MULTI_AGENT,
        ]
    )
    categories: list[BenchmarkCategory] = Field(
        default_factory=lambda: list(BenchmarkCategory)
    )
    seed: int = 42
