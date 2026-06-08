"""
A/B Testing Engine for ACOS Validation Lab v1.0.

Phase 3: Statistical comparison engine for evaluating cognitive systems.

Provides:
- Pairwise A/B comparison with statistical significance testing
- Tournament mode for comparing multiple systems
- Statistical analysis: Welch's t-test, Cohen's d, confidence intervals
- Per-case scoring, tracing, and cost tracking
"""

from __future__ import annotations

import math
import time
from typing import Any, Protocol

from scipy import stats as scipy_stats

from acos.validation.models import (
    BenchmarkCategory,
    BenchmarkSuiteResult,
    ComparisonResult,
    SignificanceLevel,
    SignificanceResult,
    SystemBenchmarkTrace,
    SystemType,
    TournamentResult,
)
from acos.validation.baselines import ACOSSimulated, SimulatedBaseline, get_baseline
from acos.validation.benchmarks import BenchmarkSuite, SystemUnderTest


class ABTestEngine:
    """A/B testing engine for comparing cognitive systems.
    
    Usage::
    
        engine = ABTestEngine()
        result = engine.run_comparison(system_a, system_b, suite, n_cases=1000)
        tournament = engine.run_tournament([system_a, system_b, system_c], suite)
    """

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed

    def run_comparison(
        self,
        system_a: SystemUnderTest,
        system_b: SystemUnderTest,
        benchmarks: BenchmarkSuite,
        n_cases: int = 1000,
    ) -> ComparisonResult:
        """Run a pairwise A/B comparison between two systems.
        
        Both systems are tested on the same benchmark suite with the
        same test cases. Results are compared using statistical tests.
        """
        # Run benchmarks for both systems
        result_a = benchmarks.run_full_suite(system_a, n_cases=n_cases)
        result_b = benchmarks.run_full_suite(system_b, n_cases=n_cases)

        # Build traces
        trace_a = self._build_trace(system_a.name, result_a)
        trace_b = self._build_trace(system_b.name, result_b)

        # Statistical significance
        significance = self.compute_statistical_significance(
            [r.overall_score for r in result_a.results],
            [r.overall_score for r in result_b.results],
        )

        # Determine winner
        if significance.significance_level in (
            SignificanceLevel.SIGNIFICANT,
            SignificanceLevel.HIGHLY_SIGNIFICANT,
        ):
            winner = system_a.name if trace_a.mean_score > trace_b.mean_score else system_b.name
        else:
            winner = "tie"

        margin = abs(trace_a.mean_score - trace_b.mean_score)

        return ComparisonResult(
            system_a_name=system_a.name,
            system_b_name=system_b.name,
            benchmark_name="full_suite",
            system_a_trace=trace_a,
            system_b_trace=trace_b,
            significance=significance,
            winner=winner,
            margin=round(margin, 6),
            n_cases=n_cases,
        )

    def run_tournament(
        self,
        systems: list[SystemUnderTest],
        benchmarks: BenchmarkSuite,
        n_cases: int = 1000,
    ) -> TournamentResult:
        """Run a round-robin tournament across all systems.
        
        Every pair of systems is compared. Rankings are computed
        based on mean scores across all comparisons.
        """
        start = time.monotonic()
        comparisons: list[ComparisonResult] = []
        score_totals: dict[str, list[float]] = {s.name: [] for s in systems}

        # Run benchmarks for each system
        results: dict[str, BenchmarkSuiteResult] = {}
        for system in systems:
            result = benchmarks.run_full_suite(system, n_cases=n_cases)
            results[system.name] = result
            score_totals[system.name].append(result.overall_score)

        # Pairwise comparisons
        for i in range(len(systems)):
            for j in range(i + 1, len(systems)):
                comp = self.run_comparison(
                    systems[i], systems[j], benchmarks, n_cases=n_cases
                )
                comparisons.append(comp)

                # Track scores
                if comp.system_a_trace:
                    score_totals[systems[i].name].append(comp.system_a_trace.mean_score)
                if comp.system_b_trace:
                    score_totals[systems[j].name].append(comp.system_b_trace.mean_score)

        # Compute rankings
        rankings = [
            (name, round(sum(scores) / max(len(scores), 1), 6))
            for name, scores in score_totals.items()
        ]
        rankings.sort(key=lambda x: x[1], reverse=True)

        best_system = rankings[0][0] if rankings else ""
        worst_system = rankings[-1][0] if rankings else ""

        elapsed = (time.monotonic() - start) * 1000

        return TournamentResult(
            systems=[s.name for s in systems],
            comparisons=comparisons,
            rankings=rankings,
            best_system=best_system,
            worst_system=worst_system,
            n_cases=n_cases,
            total_execution_time_ms=elapsed,
        )

    def compute_statistical_significance(
        self,
        results_a: list[float],
        results_b: list[float],
    ) -> SignificanceResult:
        """Compute statistical significance between two sets of results.
        
        Uses Welch's t-test (does not assume equal variances).
        """
        if not results_a or not results_b:
            return SignificanceResult(
                test_name="welch_t",
                statistic=0.0,
                p_value=1.0,
                significance_level=SignificanceLevel.NOT_SIGNIFICANT,
                confidence_interval_diff=(0.0, 0.0),
                effect_size_cohens_d=0.0,
                sample_size_a=len(results_a),
                sample_size_b=len(results_b),
            )

        n_a = len(results_a)
        n_b = len(results_b)
        mean_a = sum(results_a) / n_a
        mean_b = sum(results_b) / n_b

        # Welch's t-test
        if n_a >= 2 and n_b >= 2:
            var_a = sum((x - mean_a) ** 2 for x in results_a) / (n_a - 1)
            var_b = sum((x - mean_b) ** 2 for x in results_b) / (n_b - 1)

            se_a = var_a / n_a
            se_b = var_b / n_b
            se_diff = math.sqrt(se_a + se_b)

            if se_diff > 0:
                t_stat = (mean_a - mean_b) / se_diff

                # Degrees of freedom (Welch-Satterthwaite)
                df_num = (se_a + se_b) ** 2
                df_den = (se_a ** 2 / (n_a - 1)) + (se_b ** 2 / (n_b - 1))
                df = df_num / max(df_den, 1e-10)

                # Two-tailed p-value using scipy
                try:
                    p_value = 2 * scipy_stats.t.sf(abs(t_stat), df)
                except Exception:
                    p_value = 1.0
            else:
                t_stat = 0.0
                p_value = 1.0
                df = n_a + n_b - 2
        else:
            t_stat = 0.0
            p_value = 1.0
            df = 0

        # Effect size: Cohen's d
        cohens_d = self.compute_effect_size(results_a, results_b)

        # Confidence interval for the difference
        ci = self.compute_confidence_interval(
            [a - b for a, b in zip(results_a, results_b)],
            confidence=0.95,
        ) if len(results_a) == len(results_b) else (
            mean_a - mean_b - 1.96 * math.sqrt(se_a + se_b) if n_a >= 2 and n_b >= 2 else (0.0, 0.0),
        )

        # Determine significance level
        if p_value < 0.01:
            sig_level = SignificanceLevel.HIGHLY_SIGNIFICANT
        elif p_value < 0.05:
            sig_level = SignificanceLevel.SIGNIFICANT
        elif p_value < 0.10:
            sig_level = SignificanceLevel.MARGINAL
        else:
            sig_level = SignificanceLevel.NOT_SIGNIFICANT

        return SignificanceResult(
            test_name="welch_t",
            statistic=round(t_stat, 6),
            p_value=round(p_value, 6),
            significance_level=sig_level,
            confidence_interval_diff=(round(ci[0], 6), round(ci[1], 6)),
            effect_size_cohens_d=round(cohens_d, 6),
            sample_size_a=n_a,
            sample_size_b=n_b,
        )

    def compute_effect_size(self, results_a: list[float], results_b: list[float]) -> float:
        """Compute Cohen's d effect size.
        
        d = (mean_a - mean_b) / pooled_std
        """
        if not results_a or not results_b:
            return 0.0

        n_a = len(results_a)
        n_b = len(results_b)
        mean_a = sum(results_a) / n_a
        mean_b = sum(results_b) / n_b

        var_a = sum((x - mean_a) ** 2 for x in results_a) / max(n_a - 1, 1)
        var_b = sum((x - mean_b) ** 2 for x in results_b) / max(n_b - 1, 1)

        # Pooled standard deviation
        pooled_var = ((n_a - 1) * var_a + (n_b - 1) * var_b) / max(n_a + n_b - 2, 1)
        pooled_std = math.sqrt(pooled_var)

        if pooled_std == 0:
            return 0.0

        return (mean_a - mean_b) / pooled_std

    def compute_confidence_interval(
        self,
        results: list[float],
        confidence: float = 0.95,
    ) -> tuple[float, float]:
        """Compute confidence interval for a set of results.
        
        Uses the t-distribution for small samples.
        """
        if not results:
            return (0.0, 0.0)

        n = len(results)
        mean = sum(results) / n

        if n < 2:
            return (mean, mean)

        var = sum((x - mean) ** 2 for x in results) / (n - 1)
        se = math.sqrt(var / n)

        # t-critical value
        alpha = 1 - confidence
        try:
            t_crit = scipy_stats.t.ppf(1 - alpha / 2, df=n - 1)
        except Exception:
            t_crit = 1.96  # Fallback to normal approximation

        margin = t_crit * se
        return (round(mean - margin, 6), round(mean + margin, 6))

    def _build_trace(
        self,
        system_name: str,
        suite_result: BenchmarkSuiteResult,
    ) -> SystemBenchmarkTrace:
        """Build a SystemBenchmarkTrace from a BenchmarkSuiteResult."""
        scores = [r.overall_score for r in suite_result.results]
        n = len(scores)
        
        if n == 0:
            return SystemBenchmarkTrace(
                system_name=system_name,
                system_type=SystemType.ACOS,
                scores=[],
            )

        mean = sum(scores) / n
        variance = sum((s - mean) ** 2 for s in scores) / max(n - 1, 1)
        std = math.sqrt(variance)
        
        sorted_scores = sorted(scores)
        median = sorted_scores[n // 2] if n % 2 == 1 else (
            (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
        )

        return SystemBenchmarkTrace(
            system_name=system_name,
            system_type=SystemType.ACOS,
            scores=scores,
            mean_score=round(mean, 6),
            std_score=round(std, 6),
            median_score=round(median, 6),
            min_score=round(min(scores), 6),
            max_score=round(max(scores), 6),
            total_latency_ms=suite_result.total_execution_time_ms,
        )
