"""
Tests for ACOS Validation Lab v1.0.

Covers all 7 phases:
- Phase 1: Benchmark Suite
- Phase 2: Baseline Systems
- Phase 3: A/B Testing Engine
- Phase 4: Cognitive Metrics
- Phase 5: Failure Analysis
- Phase 6: Emergent Behavior Analysis
- Phase 7: Scientific Report Generation
- Integration: Full ValidationLab pipeline
"""

import math
import random
import pytest

from acos.validation.models import (
    BenchmarkCategory,
    BenchmarkMetric,
    BenchmarkResult,
    BenchmarkSuiteResult,
    ComparisonResult,
    EmergenceAnalysisResult,
    EmergenceReport,
    EmergenceType,
    FailureAnalysisReport,
    FailureReport,
    FailureType,
    LearningTestCase,
    MemoryTestCase,
    PlanningTestCase,
    PredictionTestCase,
    ReasoningTestCase,
    ScientificReport,
    SignificanceLevel,
    SignificanceResult,
    SystemType,
    TournamentResult,
    ValidationConfig,
    CognitiveMetricsResult,
)
from acos.validation.test_generator import TestCaseGenerator
from acos.validation.benchmarks import BenchmarkSuite
from acos.validation.baselines import (
    ACOSSimulated,
    DirectLLMBaseline,
    MemoryRAGBaseline,
    MultiAgentBaseline,
    LangGraphBaseline,
    ReActBaseline,
    SimulatedBaseline,
    get_baseline,
    ACOS_PROFILE,
    PROFILES,
)
from acos.validation.ab_testing import ABTestEngine
from acos.validation.cognitive_metrics import CognitiveMetrics
from acos.validation.failure_analysis import FailureAnalyzer
from acos.validation.emergent_behavior import EmergentBehaviorAnalyzer
from acos.validation.report_generator import ScientificReportGenerator
from acos.validation import ValidationLab


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Test Case Generator Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestTestCaseGenerator:
    """Tests for TestCaseGenerator."""

    def test_generate_memory_cases_default(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_memory_cases(n=50)
        assert len(cases) == 50
        assert all(isinstance(c, MemoryTestCase) for c in cases)

    def test_generate_memory_cases_reproducible(self):
        gen1 = TestCaseGenerator(seed=42)
        gen2 = TestCaseGenerator(seed=42)
        cases1 = gen1.generate_memory_cases(n=10)
        cases2 = gen2.generate_memory_cases(n=10)
        assert [c.query for c in cases1] == [c.query for c in cases2]

    def test_generate_memory_cases_has_expected_facts(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_memory_cases(n=10)
        assert all(len(c.expected_facts) >= 1 for c in cases)

    def test_generate_planning_cases(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_planning_cases(n=30)
        assert len(cases) == 30
        assert all(isinstance(c, PlanningTestCase) for c in cases)

    def test_generate_planning_cases_has_subgoals(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_planning_cases(n=20)
        assert all(len(c.subgoals) >= 1 for c in cases)

    def test_generate_reasoning_cases_all_types(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_reasoning_cases(n=40)
        types = {c.reasoning_type for c in cases}
        assert "deductive" in types
        assert "inductive" in types
        assert "causal" in types
        assert "counterfactual" in types

    def test_generate_learning_cases(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_learning_cases(n=20)
        assert len(cases) == 20
        assert all(isinstance(c, LearningTestCase) for c in cases)

    def test_generate_prediction_cases(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_prediction_cases(n=15)
        assert len(cases) == 15
        assert all(isinstance(c, PredictionTestCase) for c in cases)

    def test_difficulty_range(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_memory_cases(n=100)
        difficulties = [c.difficulty for c in cases]
        assert min(difficulties) >= 0.0
        assert max(difficulties) <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Benchmark Suite Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestBenchmarkSuite:
    """Tests for BenchmarkSuite."""

    def _make_system(self):
        """Create a simple test system."""
        return ACOSSimulated(seed=42)

    def test_benchmark_recall_accuracy(self):
        suite = BenchmarkSuite(seed=42)
        gen = TestCaseGenerator(seed=42)
        system = self._make_system()
        cases = gen.generate_memory_cases(n=20)
        result = suite.benchmark_recall_accuracy(system, cases)
        assert isinstance(result, BenchmarkResult)
        assert result.benchmark_name == "recall_accuracy"
        assert result.category == BenchmarkCategory.MEMORY
        assert result.test_case_count == 20
        assert 0.0 <= result.overall_score <= 1.0

    def test_benchmark_long_term_retention(self):
        suite = BenchmarkSuite(seed=42)
        gen = TestCaseGenerator(seed=42)
        system = self._make_system()
        cases = gen.generate_memory_cases(n=20)
        result = suite.benchmark_long_term_retention(system, cases)
        assert result.benchmark_name == "long_term_retention"
        assert result.category == BenchmarkCategory.MEMORY

    def test_benchmark_goal_decomposition(self):
        suite = BenchmarkSuite(seed=42)
        gen = TestCaseGenerator(seed=42)
        system = self._make_system()
        cases = gen.generate_planning_cases(n=20)
        result = suite.benchmark_goal_decomposition(system, cases)
        assert result.benchmark_name == "goal_decomposition"
        assert result.category == BenchmarkCategory.PLANNING

    def test_benchmark_deductive_reasoning(self):
        suite = BenchmarkSuite(seed=42)
        gen = TestCaseGenerator(seed=42)
        system = self._make_system()
        cases = gen.generate_reasoning_cases(n=20)
        result = suite.benchmark_deductive_reasoning(system, cases)
        assert result.benchmark_name == "deductive_reasoning"
        assert result.category == BenchmarkCategory.REASONING

    def test_benchmark_belief_updates(self):
        suite = BenchmarkSuite(seed=42)
        gen = TestCaseGenerator(seed=42)
        system = self._make_system()
        cases = gen.generate_learning_cases(n=20)
        result = suite.benchmark_belief_updates(system, cases)
        assert result.benchmark_name == "belief_updates"
        assert result.category == BenchmarkCategory.LEARNING

    def test_benchmark_future_state_prediction(self):
        suite = BenchmarkSuite(seed=42)
        gen = TestCaseGenerator(seed=42)
        system = self._make_system()
        cases = gen.generate_prediction_cases(n=20)
        result = suite.benchmark_future_state_prediction(system, cases)
        assert result.benchmark_name == "future_state_prediction"
        assert result.category == BenchmarkCategory.PREDICTION

    def test_run_full_suite(self):
        suite = BenchmarkSuite(seed=42)
        system = self._make_system()
        result = suite.run_full_suite(system, n_cases=10)
        assert isinstance(result, BenchmarkSuiteResult)
        assert len(result.results) == 19  # 19 benchmarks total
        assert result.system_name == "ACOS Runtime"
        assert 0.0 <= result.overall_score <= 1.0
        assert "memory" in result.category_scores
        assert "planning" in result.category_scores
        assert "reasoning" in result.category_scores
        assert "learning" in result.category_scores
        assert "prediction" in result.category_scores


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Baseline Systems Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestBaselineSystems:
    """Tests for baseline systems."""

    def test_direct_llm_baseline_name(self):
        baseline = DirectLLMBaseline(seed=42)
        assert baseline.name == "Direct LLM"

    def test_memory_rag_baseline_name(self):
        baseline = MemoryRAGBaseline(seed=42)
        assert baseline.name == "Memory RAG"

    def test_react_baseline_name(self):
        baseline = ReActBaseline(seed=42)
        assert baseline.name == "ReAct Agent"

    def test_langgraph_baseline_name(self):
        baseline = LangGraphBaseline(seed=42)
        assert baseline.name == "LangGraph Agent"

    def test_multi_agent_baseline_name(self):
        baseline = MultiAgentBaseline(seed=42)
        assert baseline.name == "Multi-Agent System"

    def test_baseline_process_returns_dict(self):
        baseline = DirectLLMBaseline(seed=42)
        result = baseline.process("test query", {"action": "query"})
        assert isinstance(result, dict)

    def test_baseline_get_state_returns_dict(self):
        baseline = DirectLLMBaseline(seed=42)
        state = baseline.get_state()
        assert isinstance(state, dict)
        assert "beliefs" in state
        assert "memories" in state

    def test_acos_simulated_name(self):
        acos = ACOSSimulated(seed=42)
        assert acos.name == "ACOS Runtime"

    def test_acos_profile_has_higher_accuracy(self):
        """ACOS profile should have higher base accuracy than baselines."""
        acos_memory_base = ACOS_PROFILE["memory"]["base_accuracy"]
        for st, profile in PROFILES.items():
            assert acos_memory_base >= profile["memory"]["base_accuracy"], (
                f"ACOS memory base ({acos_memory_base}) should be >= {st} ({profile['memory']['base_accuracy']})"
            )

    def test_get_baseline_factory(self):
        for st in SystemType:
            if st == SystemType.ACOS:
                continue
            baseline = get_baseline(st, seed=42)
            assert isinstance(baseline, SimulatedBaseline)

    def test_get_baseline_unknown_raises(self):
        with pytest.raises(ValueError):
            get_baseline(SystemType.ACOS, seed=42)

    def test_baseline_reproducibility(self):
        """Same seed should produce same results."""
        b1 = DirectLLMBaseline(seed=42)
        b2 = DirectLLMBaseline(seed=42)
        r1 = b1.process("test", {"action": "store", "facts": ["a", "b"]})
        r2 = b2.process("test", {"action": "store", "facts": ["a", "b"]})
        assert r1 == r2


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: A/B Testing Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestABTestEngine:
    """Tests for ABTestEngine."""

    def test_compute_effect_size(self):
        engine = ABTestEngine(seed=42)
        # Identical distributions should have ~0 effect size
        d = engine.compute_effect_size([0.5] * 20, [0.5] * 20)
        assert abs(d) < 0.01

    def test_compute_effect_size_large(self):
        engine = ABTestEngine(seed=42)
        # Different distributions should have large effect size
        # Add small noise to avoid zero variance
        rng = random.Random(42)
        a = [0.9 + rng.gauss(0, 0.05) for _ in range(20)]
        b = [0.3 + rng.gauss(0, 0.05) for _ in range(20)]
        d = engine.compute_effect_size(a, b)
        assert d > 1.0  # Large effect

    def test_compute_confidence_interval(self):
        engine = ABTestEngine(seed=42)
        ci = engine.compute_confidence_interval([0.5, 0.6, 0.55, 0.58, 0.52])
        assert len(ci) == 2
        assert ci[0] <= ci[1]

    def test_compute_confidence_interval_empty(self):
        engine = ABTestEngine(seed=42)
        ci = engine.compute_confidence_interval([])
        assert ci == (0.0, 0.0)

    def test_compute_statistical_significance(self):
        engine = ABTestEngine(seed=42)
        # Add noise to avoid zero variance which causes t-test issues
        rng = random.Random(42)
        a = [0.8 + rng.gauss(0, 0.05) for _ in range(30)]
        b = [0.4 + rng.gauss(0, 0.05) for _ in range(30)]
        result = engine.compute_statistical_significance(a, b)
        assert isinstance(result, SignificanceResult)
        assert result.p_value < 0.05
        assert result.significance_level in (
            SignificanceLevel.SIGNIFICANT,
            SignificanceLevel.HIGHLY_SIGNIFICANT,
        )

    def test_compute_statistical_significance_no_diff(self):
        engine = ABTestEngine(seed=42)
        result = engine.compute_statistical_significance(
            [0.5] * 30, [0.5] * 30,
        )
        assert result.p_value > 0.05
        assert result.significance_level == SignificanceLevel.NOT_SIGNIFICANT

    def test_run_comparison(self):
        engine = ABTestEngine(seed=42)
        suite = BenchmarkSuite(seed=42)
        system_a = ACOSSimulated(seed=42)
        system_b = DirectLLMBaseline(seed=42)
        result = engine.run_comparison(system_a, system_b, suite, n_cases=10)
        assert isinstance(result, ComparisonResult)
        assert result.system_a_name == "ACOS Runtime"
        assert result.system_b_name == "Direct LLM"
        assert result.winner in ("ACOS Runtime", "Direct LLM", "tie")

    def test_run_tournament(self):
        engine = ABTestEngine(seed=42)
        suite = BenchmarkSuite(seed=42)
        systems = [
            ACOSSimulated(seed=42),
            DirectLLMBaseline(seed=42),
            MemoryRAGBaseline(seed=42),
        ]
        result = engine.run_tournament(systems, suite, n_cases=10)
        assert isinstance(result, TournamentResult)
        assert len(result.rankings) == 3
        assert result.best_system != ""


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: Cognitive Metrics Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCognitiveMetrics:
    """Tests for CognitiveMetrics."""

    def test_belief_accuracy_empty(self):
        metrics = CognitiveMetrics()
        assert metrics.belief_accuracy({}) == 0.0

    def test_belief_accuracy_perfect(self):
        metrics = CognitiveMetrics()
        state = {
            "beliefs": [
                {"confidence": 1.0, "actual_correctness": 1.0},
                {"confidence": 0.0, "actual_correctness": 0.0},
            ]
        }
        assert metrics.belief_accuracy(state) == 1.0

    def test_belief_accuracy_poor(self):
        metrics = CognitiveMetrics()
        state = {
            "beliefs": [
                {"confidence": 1.0, "actual_correctness": 0.0},
                {"confidence": 0.0, "actual_correctness": 1.0},
            ]
        }
        assert metrics.belief_accuracy(state) == 0.0

    def test_goal_completion_rate(self):
        metrics = CognitiveMetrics()
        state = {
            "goals": [
                {"completed": True},
                {"completed": False},
                {"completed": True},
            ]
        }
        rate = metrics.goal_completion_rate(state)
        assert abs(rate - 2/3) < 0.01

    def test_memory_utilization_with_stats(self):
        metrics = CognitiveMetrics()
        state = {
            "memory_stats": {
                "retrieval_rate": 0.8,
                "average_relevance": 0.7,
            }
        }
        util = metrics.memory_utilization(state)
        assert abs(util - 0.75) < 0.01

    def test_prediction_accuracy(self):
        metrics = CognitiveMetrics()
        state = {
            "predictions": [
                {"prediction_error": 0.1},
                {"prediction_error": 0.2},
            ]
        }
        acc = metrics.prediction_accuracy(state)
        assert abs(acc - 0.85) < 0.01

    def test_uncertainty_calibration(self):
        metrics = CognitiveMetrics()
        state = {
            "predictions": [
                {"predicted_prob": 0.8, "actual_outcome": 1.0},
                {"predicted_prob": 0.3, "actual_outcome": 0.0},
            ]
        }
        cal = metrics.uncertainty_calibration(state)
        # Brier = (0.2)^2 + (0.3)^2 = 0.04 + 0.09 = 0.065
        assert abs(cal - (1.0 - 0.065)) < 0.01

    def test_compute_all(self):
        metrics = CognitiveMetrics()
        state = {
            "beliefs": [{"confidence": 0.8, "actual_correctness": 0.9}],
            "goals": [{"completed": True}],
            "memories": [{"content": "test"}] * 50,
            "predictions": [{"prediction_error": 0.1, "predicted_prob": 0.8, "actual_outcome": 1.0}],
        }
        result = metrics.compute_all(state, system_name="test")
        assert isinstance(result, CognitiveMetricsResult)
        assert len(result.metrics) == 8
        assert 0.0 <= result.overall_cognitive_score <= 1.0
        assert len(result.strengths) + len(result.weaknesses) == 8


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5: Failure Analysis Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailureAnalysis:
    """Tests for FailureAnalyzer."""

    def test_detect_belief_collapse_not_detected(self):
        analyzer = FailureAnalyzer()
        state = {
            "beliefs": [
                {"confidence": 0.8, "statement": "A"},
                {"confidence": 0.7, "statement": "B"},
            ]
        }
        report = analyzer.detect_belief_collapse(state)
        assert isinstance(report, FailureReport)
        assert not report.detected
        assert report.failure_type == FailureType.BELIEF_COLLAPSE

    def test_detect_belief_collapse_detected(self):
        analyzer = FailureAnalyzer()
        state = {
            "beliefs": [
                {"confidence": 0.05, "statement": "A"},
                {"confidence": 0.03, "statement": "B"},
                {"confidence": 0.08, "statement": "C"},
                {"confidence": 0.10, "statement": "D"},
            ]
        }
        report = analyzer.detect_belief_collapse(state)
        assert report.detected
        assert report.severity > 0.5

    def test_detect_contradiction_accumulation(self):
        analyzer = FailureAnalyzer()
        state = {
            "contradictions": [{"a": 1}, {"b": 2}, {"c": 3}, {"d": 4}, {"e": 5}, {"f": 6}],
            "resolved_contradictions": 1,
        }
        report = analyzer.detect_contradiction_accumulation(state)
        assert report.detected  # 6 > 5 threshold

    def test_detect_goal_oscillation(self):
        analyzer = FailureAnalyzer()
        state = {
            "goals": [
                {"progress": 0.1, "priority_changes": 5},
                {"progress": 0.2, "priority_changes": 4},
            ]
        }
        report = analyzer.detect_goal_oscillation(state)
        assert isinstance(report, FailureReport)
        assert report.failure_type == FailureType.GOAL_OSCILLATION

    def test_detect_prediction_drift(self):
        analyzer = FailureAnalyzer()
        # Errors increasing over time
        state = {
            "prediction_errors": [0.05, 0.08, 0.12, 0.18, 0.25, 0.35],
        }
        report = analyzer.detect_prediction_drift(state)
        assert report.detected
        assert report.severity > 0

    def test_generate_report(self):
        analyzer = FailureAnalyzer()
        state = {
            "beliefs": [{"confidence": 0.8, "statement": "A"}],
            "goals": [{"completed": True}],
            "predictions": [],
        }
        report = analyzer.generate_report(state)
        assert isinstance(report, FailureAnalysisReport)
        assert len(report.failure_reports) == 6
        assert 0.0 <= report.overall_health <= 1.0

    def test_generate_report_with_failures(self):
        analyzer = FailureAnalyzer()
        state = {
            "beliefs": [{"confidence": 0.01, "statement": "A"}] * 5,
            "contradictions": list(range(10)),
            "prediction_errors": [0.5, 0.6, 0.7, 0.8, 0.9],
        }
        report = analyzer.generate_report(state)
        assert report.total_failures_detected >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 6: Emergent Behavior Analysis Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmergentBehavior:
    """Tests for EmergentBehaviorAnalyzer."""

    def _make_suite_result(self, system_name: str, scores: dict[str, float]) -> BenchmarkSuiteResult:
        """Helper to create a BenchmarkSuiteResult."""
        results = []
        for cat in BenchmarkCategory:
            results.append(BenchmarkResult(
                benchmark_name=f"{cat.value}_benchmark",
                category=cat,
                system_name=system_name,
                overall_score=scores.get(cat.value, 0.5),
                test_case_count=10,
            ))
        return BenchmarkSuiteResult(
            system_name=system_name,
            results=results,
            overall_score=sum(scores.values()) / max(len(scores), 1),
            category_scores=scores,
            total_test_cases=len(results) * 10,
        )

    def test_analyze_planning_emergence(self):
        analyzer = EmergentBehaviorAnalyzer()
        acos = self._make_suite_result("ACOS", {"planning": 0.8})
        baseline = self._make_suite_result("Baseline", {"planning": 0.4})
        report = analyzer.analyze_planning_emergence(acos, [baseline])
        assert isinstance(report, EmergenceReport)
        assert report.emergence_type == EmergenceType.PLANNING

    def test_analyze_all(self):
        analyzer = EmergentBehaviorAnalyzer()
        acos = self._make_suite_result("ACOS", {
            "planning": 0.8, "memory": 0.75, "learning": 0.7,
            "reasoning": 0.72, "prediction": 0.68,
        })
        baseline = self._make_suite_result("Baseline", {
            "planning": 0.5, "memory": 0.5, "learning": 0.45,
            "reasoning": 0.5, "prediction": 0.5,
        })
        result = analyzer.analyze_all(acos, [baseline])
        assert isinstance(result, EmergenceAnalysisResult)
        assert len(result.reports) == 5
        assert 0.0 <= result.overall_emergence_score <= 1.0

    def test_emergence_threshold(self):
        """ACOS at 1.5x baseline should be detected as emergent."""
        analyzer = EmergentBehaviorAnalyzer()
        # Create results with specific benchmark names matching what the analyzer expects
        acos_results = []
        baseline_results_list = []
        for cat in BenchmarkCategory:
            acos_results.append(BenchmarkResult(
                benchmark_name="goal_decomposition" if cat == BenchmarkCategory.PLANNING else f"{cat.value}_bench",
                category=cat, system_name="ACOS", overall_score=0.75 if cat == BenchmarkCategory.PLANNING else 0.5,
                test_case_count=10,
            ))
            baseline_results_list.append(BenchmarkResult(
                benchmark_name="goal_decomposition" if cat == BenchmarkCategory.PLANNING else f"{cat.value}_bench",
                category=cat, system_name="Baseline", overall_score=0.50 if cat == BenchmarkCategory.PLANNING else 0.4,
                test_case_count=10,
            ))
        acos_suite = BenchmarkSuiteResult(
            system_name="ACOS", results=acos_results, overall_score=0.6,
            category_scores={"planning": 0.75}, total_test_cases=50,
        )
        baseline_suite = BenchmarkSuiteResult(
            system_name="Baseline", results=baseline_results_list, overall_score=0.45,
            category_scores={"planning": 0.50}, total_test_cases=50,
        )
        report = analyzer.analyze_planning_emergence(acos_suite, [baseline_suite])
        # 0.75 / 0.50 = 1.5, exactly at threshold
        assert any(i.improvement_factor >= 1.5 for i in report.indicators)


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 7: Scientific Report Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestScientificReport:
    """Tests for ScientificReportGenerator."""

    def test_generate_report(self):
        gen = ScientificReportGenerator()
        report = gen.generate_report()
        assert isinstance(report, ScientificReport)
        assert report.title == "ACOS Validation Lab Report"
        assert report.version == "1.0"

    def test_generate_report_with_data(self):
        gen = ScientificReportGenerator()
        suite = BenchmarkSuite(seed=42)
        acos = ACOSSimulated(seed=42)
        result = suite.run_full_suite(acos, n_cases=5)
        
        report = gen.generate_report(
            benchmark_results=[result],
            execution_time_ms=1000,
        )
        assert report.experiment_design is not None
        assert report.experiment_design.n_systems == 1

    def test_format_text_report(self):
        gen = ScientificReportGenerator()
        report = gen.generate_report()
        text = gen.format_text_report(report)
        assert "ACOS Validation Lab Report" in text
        assert "EXPERIMENTAL DESIGN" in text


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: Full ValidationLab Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationLabIntegration:
    """Integration tests for the full ValidationLab pipeline."""

    def test_validation_lab_run_small(self):
        config = ValidationConfig(
            n_test_cases=5,
            n_cases_ab_test=5,
            include_baselines=[SystemType.DIRECT_LLM, SystemType.MEMORY_RAG],
            seed=42,
        )
        lab = ValidationLab(config)
        report = lab.run()
        assert isinstance(report, ScientificReport)
        assert report.experiment_design is not None
        assert report.experiment_design.n_systems >= 2

    def test_validation_lab_has_all_sections(self):
        config = ValidationConfig(
            n_test_cases=5,
            n_cases_ab_test=5,
            include_baselines=[SystemType.DIRECT_LLM],
            seed=42,
        )
        lab = ValidationLab(config)
        report = lab.run()
        assert report.experiment_design is not None
        assert len(report.benchmark_results) > 0
        assert len(report.comparison_results) > 0
        assert report.tournament_result is not None
        assert report.cognitive_metrics is not None
        assert report.failure_analysis is not None
        assert report.emergence_analysis is not None
        assert report.cost_analysis is not None

    def test_validation_lab_acos_wins_tournament(self):
        """ACOS should generally win the tournament due to higher performance profile."""
        config = ValidationConfig(
            n_test_cases=10,
            n_cases_ab_test=10,
            include_baselines=[SystemType.DIRECT_LLM],
            seed=42,
        )
        lab = ValidationLab(config)
        report = lab.run()
        if report.tournament_result:
            # ACOS should be ranked first (its profile is better)
            assert report.tournament_result.best_system == "ACOS Runtime"

    def test_validation_config_defaults(self):
        config = ValidationConfig()
        assert config.n_test_cases == 100
        assert config.n_cases_ab_test == 1000
        assert config.confidence_level == 0.95
        assert config.emergence_threshold == 1.5
        assert len(config.include_baselines) == 5


# ═══════════════════════════════════════════════════════════════════════════════
# Edge Case & Robustness Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge case and robustness tests."""

    def test_empty_test_cases(self):
        suite = BenchmarkSuite(seed=42)
        system = ACOSSimulated(seed=42)
        # Empty memory cases
        result = suite.benchmark_recall_accuracy(system, [])
        assert result.test_case_count == 0

    def test_ab_engine_empty_results(self):
        engine = ABTestEngine(seed=42)
        result = engine.compute_statistical_significance([], [])
        assert result.significance_level == SignificanceLevel.NOT_SIGNIFICANT

    def test_failure_analyzer_empty_state(self):
        analyzer = FailureAnalyzer()
        report = analyzer.generate_report({})
        assert isinstance(report, FailureAnalysisReport)

    def test_cognitive_metrics_empty_state(self):
        metrics = CognitiveMetrics()
        result = metrics.compute_all({}, system_name="empty")
        # Some metrics return 0.5 as default when no data available
        assert 0.0 <= result.overall_cognitive_score <= 0.5

    def test_benchmark_suite_result_serialization(self):
        """BenchmarkSuiteResult should be serializable to dict."""
        suite = BenchmarkSuite(seed=42)
        system = ACOSSimulated(seed=42)
        result = suite.run_full_suite(system, n_cases=5)
        data = result.model_dump()
        assert "system_name" in data
        assert "results" in data

    def test_scientific_report_serialization(self):
        gen = ScientificReportGenerator()
        report = gen.generate_report()
        data = report.model_dump()
        assert "title" in data
        assert "version" in data
