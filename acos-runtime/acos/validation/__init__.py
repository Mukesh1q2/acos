"""
ACOS Validation Lab v1.0 — Comprehensive evaluation framework for cognitive systems.

This package provides a rigorous evaluation framework that measures whether
the ACOS cognitive architecture provides measurable advantages over baseline systems.

Phases:
1. Benchmark Suite — measures cognitive capabilities across 5 categories
2. Baseline Systems — simulated comparison systems with realistic profiles
3. A/B Testing Engine — statistical comparison with significance testing
4. Cognitive Metrics — unified metric calculator
5. Failure Analysis — automated failure mode detection
6. Emergent Behavior — emergence detection vs baselines
7. Scientific Report — comprehensive report generation

Usage::

    from acos.validation import ValidationLab, ValidationConfig

    # Quick validation
    lab = ValidationLab()
    report = lab.run()

    # Custom configuration
    config = ValidationConfig(n_test_cases=500, seed=123)
    lab = ValidationLab(config)
    report = lab.run()

    # Access results
    print(report.conclusion)
    print(f"Overall emergence score: {report.emergence_analysis.overall_emergence_score}")
"""

from acos.validation.models import (
    # Enums
    BenchmarkCategory,
    BenchmarkMetric,
    EmergenceType,
    FailureType,
    SignificanceLevel,
    SystemType,
    # Test case models
    MemoryTestCase,
    PlanningTestCase,
    ReasoningTestCase,
    LearningTestCase,
    PredictionTestCase,
    # Result models
    BenchmarkScore,
    BenchmarkResult,
    BenchmarkSuiteResult,
    SignificanceResult,
    SystemBenchmarkTrace,
    ComparisonResult,
    TournamentResult,
    FailureReport,
    FailureAnalysisReport,
    EmergenceIndicator,
    EmergenceReport,
    EmergenceAnalysisResult,
    CognitiveMetricResult,
    CognitiveMetricsResult,
    ExperimentDesign,
    CostAnalysis,
    ScientificReport,
    ValidationConfig,
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
)
from acos.validation.ab_testing import ABTestEngine
from acos.validation.cognitive_metrics import CognitiveMetrics
from acos.validation.failure_analysis import FailureAnalyzer
from acos.validation.emergent_behavior import EmergentBehaviorAnalyzer
from acos.validation.report_generator import ScientificReportGenerator

import time as _time
from typing import Any


class ValidationLab:
    """Top-level validation lab that orchestrates all phases.
    
    Usage::
    
        lab = ValidationLab()
        report = lab.run()
    """

    def __init__(self, config: ValidationConfig | None = None) -> None:
        self._config = config or ValidationConfig()
        self._generator = TestCaseGenerator(seed=self._config.seed)
        self._suite = BenchmarkSuite(seed=self._config.seed)
        self._ab_engine = ABTestEngine(seed=self._config.seed)
        self._metrics = CognitiveMetrics()
        self._failure_analyzer = FailureAnalyzer()
        self._emergence_analyzer = EmergentBehaviorAnalyzer()
        self._report_generator = ScientificReportGenerator()

    def run(self) -> ScientificReport:
        """Run the complete validation pipeline.
        
        Steps:
        1. Create ACOS system and baseline systems
        2. Run benchmarks for all systems
        3. Run A/B comparisons and tournament
        4. Compute cognitive metrics
        5. Analyze failure modes
        6. Analyze emergent behaviors
        7. Generate scientific report
        """
        start = _time.monotonic()

        # 1. Create systems
        acos_system = ACOSSimulated(seed=self._config.seed)
        baseline_systems = [
            get_baseline(st, seed=self._config.seed)
            for st in self._config.include_baselines
        ]

        # 2. Run benchmarks
        acos_result = self._suite.run_full_suite(acos_system, n_cases=self._config.n_test_cases)
        
        baseline_results: list[BenchmarkSuiteResult] = []
        for baseline in baseline_systems:
            result = self._suite.run_full_suite(baseline, n_cases=self._config.n_test_cases)
            baseline_results.append(result)

        all_results = [acos_result] + baseline_results

        # 3. Run tournament
        all_systems = [acos_system] + list(baseline_systems)  # type: ignore
        tournament = self._ab_engine.run_tournament(
            all_systems, self._suite, n_cases=self._config.n_cases_ab_test,
        )

        # 4. Run pairwise comparisons
        comparisons: list[ComparisonResult] = []
        for baseline in baseline_systems:
            comp = self._ab_engine.run_comparison(
                acos_system, baseline, self._suite,
                n_cases=self._config.n_cases_ab_test,
            )
            comparisons.append(comp)

        # 5. Compute cognitive metrics
        acos_state = acos_system.get_state()
        cognitive_metrics = self._metrics.compute_all(acos_state, system_name=acos_system.name)

        # 6. Analyze failure modes
        failure_analysis = self._failure_analyzer.generate_report(acos_state)

        # 7. Analyze emergent behaviors
        emergence_analysis = self._emergence_analyzer.analyze_all(
            acos_result, baseline_results,
        )

        # 8. Generate report
        elapsed = (_time.monotonic() - start) * 1000

        report = self._report_generator.generate_report(
            benchmark_results=all_results,
            comparison_results=comparisons,
            tournament_result=tournament,
            cognitive_metrics=cognitive_metrics,
            failure_analysis=failure_analysis,
            emergence_analysis=emergence_analysis,
            execution_time_ms=elapsed,
        )

        return report


__all__ = [
    # Top-level
    "ValidationLab",
    "ValidationConfig",
    # Models
    "BenchmarkCategory",
    "BenchmarkMetric",
    "EmergenceType",
    "FailureType",
    "SignificanceLevel",
    "SystemType",
    "MemoryTestCase",
    "PlanningTestCase",
    "ReasoningTestCase",
    "LearningTestCase",
    "PredictionTestCase",
    "BenchmarkScore",
    "BenchmarkResult",
    "BenchmarkSuiteResult",
    "SignificanceResult",
    "SystemBenchmarkTrace",
    "ComparisonResult",
    "TournamentResult",
    "FailureReport",
    "FailureAnalysisReport",
    "EmergenceIndicator",
    "EmergenceReport",
    "EmergenceAnalysisResult",
    "CognitiveMetricResult",
    "CognitiveMetricsResult",
    "ExperimentDesign",
    "CostAnalysis",
    "ScientificReport",
    # Components
    "TestCaseGenerator",
    "BenchmarkSuite",
    "ACOSSimulated",
    "DirectLLMBaseline",
    "MemoryRAGBaseline",
    "MultiAgentBaseline",
    "LangGraphBaseline",
    "ReActBaseline",
    "SimulatedBaseline",
    "get_baseline",
    "ABTestEngine",
    "CognitiveMetrics",
    "FailureAnalyzer",
    "EmergentBehaviorAnalyzer",
    "ScientificReportGenerator",
]
