"""
Scientific Report Generator for ACOS Validation Lab v1.0.

Phase 7: Generate comprehensive scientific reports from benchmark data.

Report sections:
1. Experimental Design
2. Benchmark Results
3. Statistical Analysis
4. Cost Analysis
5. Failure Analysis
6. Strengths & Weaknesses
7. Recommended Architecture Changes
"""

from __future__ import annotations

from typing import Any

from acos.validation.models import (
    BenchmarkSuiteResult,
    ComparisonResult,
    CostAnalysis,
    EmergenceAnalysisResult,
    ExperimentDesign,
    FailureAnalysisReport,
    ScientificReport,
    TournamentResult,
    CognitiveMetricsResult,
)


class ScientificReportGenerator:
    """Generate scientific reports from benchmark data.
    
    Usage::
    
        generator = ScientificReportGenerator()
        report = generator.generate_report(
            benchmark_results=bench_results,
            comparison_results=comp_results,
            tournament_result=tourn_result,
            ...
        )
    """

    def generate_report(
        self,
        benchmark_results: list[BenchmarkSuiteResult] | None = None,
        comparison_results: list[ComparisonResult] | None = None,
        tournament_result: TournamentResult | None = None,
        cognitive_metrics: CognitiveMetricsResult | None = None,
        failure_analysis: FailureAnalysisReport | None = None,
        emergence_analysis: EmergenceAnalysisResult | None = None,
        execution_time_ms: float = 0.0,
    ) -> ScientificReport:
        """Generate a comprehensive scientific report.
        
        Combines all analysis phases into a structured report
        with experimental design, results, and recommendations.
        """
        # 1. Experimental Design
        experiment_design = self._build_experiment_design(
            benchmark_results, comparison_results, tournament_result,
        )

        # 2. Cost Analysis
        cost_analysis = self._build_cost_analysis(benchmark_results, tournament_result)

        # 3. Strengths & Weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(
            benchmark_results, cognitive_metrics, failure_analysis, emergence_analysis,
        )

        # 4. Recommended changes
        recommended_changes = self._generate_recommendations(
            weaknesses, failure_analysis, emergence_analysis,
        )

        # 5. Conclusion
        conclusion = self._generate_conclusion(
            benchmark_results, tournament_result, emergence_analysis,
        )

        # Collect individual benchmark results
        all_bench_results: list[Any] = []
        if benchmark_results:
            for br in benchmark_results:
                all_bench_results.extend(br.results)

        # Find ACOS result (first one, or the one named "ACOS Runtime")
        acos_result = None
        if benchmark_results:
            acos_result = next(
                (br for br in benchmark_results if "ACOS" in br.system_name.upper()),
                benchmark_results[0],
            )

        return ScientificReport(
            title="ACOS Validation Lab Report",
            version="1.0",
            experiment_design=experiment_design,
            benchmark_results=all_bench_results,
            comparison_results=comparison_results or [],
            tournament_result=tournament_result,
            cognitive_metrics=cognitive_metrics,
            failure_analysis=failure_analysis,
            emergence_analysis=emergence_analysis,
            cost_analysis=cost_analysis,
            strengths=strengths,
            weaknesses=weaknesses,
            recommended_changes=recommended_changes,
            conclusion=conclusion,
            total_execution_time_ms=execution_time_ms,
        )

    def format_text_report(self, report: ScientificReport) -> str:
        """Format the report as readable text."""
        lines: list[str] = []
        
        lines.append("=" * 80)
        lines.append(f"  {report.title} v{report.version}")
        lines.append("=" * 80)
        lines.append(f"Generated: {report.generated_at.isoformat()}")
        lines.append(f"Execution Time: {report.total_execution_time_ms:.1f}ms")
        lines.append("")
        
        # Experimental Design
        if report.experiment_design:
            ed = report.experiment_design
            lines.append("─" * 40)
            lines.append("1. EXPERIMENTAL DESIGN")
            lines.append("─" * 40)
            lines.append(f"  Systems Tested: {ed.n_systems}")
            lines.append(f"  Benchmarks Run: {ed.n_benchmarks}")
            lines.append(f"  Test Cases: {ed.n_test_cases}")
            lines.append(f"  Systems: {', '.join(ed.systems_tested)}")
            lines.append(f"  Methodology: {ed.methodology}")
            lines.append("")
        
        # Benchmark Results Summary
        if report.benchmark_results:
            lines.append("─" * 40)
            lines.append("2. BENCHMARK RESULTS")
            lines.append("─" * 40)
            by_system: dict[str, list[Any]] = {}
            for br in report.benchmark_results:
                by_system.setdefault(br.system_name, []).append(br)
            
            for system_name, results in by_system.items():
                avg_score = sum(r.overall_score for r in results) / max(len(results), 1)
                lines.append(f"  [{system_name}] Average Score: {avg_score:.4f}")
                for r in results:
                    lines.append(f"    - {r.benchmark_name}: {r.overall_score:.4f} (n={r.test_case_count})")
            lines.append("")
        
        # Tournament Results
        if report.tournament_result:
            tr = report.tournament_result
            lines.append("─" * 40)
            lines.append("3. TOURNAMENT RANKINGS")
            lines.append("─" * 40)
            for rank, (name, score) in enumerate(tr.rankings, 1):
                lines.append(f"  #{rank}: {name} (score: {score:.4f})")
            lines.append(f"  Best: {tr.best_system}")
            lines.append(f"  Worst: {tr.worst_system}")
            lines.append("")
        
        # Emergence Analysis
        if report.emergence_analysis:
            ea = report.emergence_analysis
            lines.append("─" * 40)
            lines.append("4. EMERGENCE ANALYSIS")
            lines.append("─" * 40)
            lines.append(f"  Overall Emergence Score: {ea.overall_emergence_score:.4f}")
            if ea.emergent_capabilities:
                lines.append(f"  Emergent Capabilities: {', '.join(ea.emergent_capabilities)}")
            if ea.non_emergent_capabilities:
                lines.append(f"  Non-Emergent: {', '.join(ea.non_emergent_capabilities)}")
            lines.append("")
        
        # Failure Analysis
        if report.failure_analysis:
            fa = report.failure_analysis
            lines.append("─" * 40)
            lines.append("5. FAILURE ANALYSIS")
            lines.append("─" * 40)
            lines.append(f"  Total Failures Detected: {fa.total_failures_detected}")
            lines.append(f"  Overall Health: {fa.overall_health:.4f}")
            for fr in fa.failure_reports:
                if fr.detected:
                    lines.append(f"  ⚠ {fr.failure_type.value}: severity={fr.severity:.3f}")
                    lines.append(f"    {fr.description}")
            lines.append("")
        
        # Strengths & Weaknesses
        if report.strengths:
            lines.append("─" * 40)
            lines.append("6. STRENGTHS")
            lines.append("─" * 40)
            for s in report.strengths[:10]:
                lines.append(f"  ✓ {s}")
            lines.append("")
        
        if report.weaknesses:
            lines.append("─" * 40)
            lines.append("7. WEAKNESSES")
            lines.append("─" * 40)
            for w in report.weaknesses[:10]:
                lines.append(f"  ✗ {w}")
            lines.append("")
        
        # Recommendations
        if report.recommended_changes:
            lines.append("─" * 40)
            lines.append("8. RECOMMENDED ARCHITECTURE CHANGES")
            lines.append("─" * 40)
            for i, rec in enumerate(report.recommended_changes, 1):
                lines.append(f"  {i}. {rec}")
            lines.append("")
        
        # Conclusion
        if report.conclusion:
            lines.append("─" * 40)
            lines.append("CONCLUSION")
            lines.append("─" * 40)
            lines.append(f"  {report.conclusion}")
            lines.append("")
        
        lines.append("=" * 80)
        return "\n".join(lines)

    # ─── Private Helpers ───────────────────────────────────────────────────────

    def _build_experiment_design(
        self,
        benchmark_results: list[BenchmarkSuiteResult] | None,
        comparison_results: list[ComparisonResult] | None,
        tournament_result: TournamentResult | None,
    ) -> ExperimentDesign:
        """Build experiment design section."""
        systems_tested: list[str] = []
        n_benchmarks = 0
        n_cases = 0

        if benchmark_results:
            for br in benchmark_results:
                if br.system_name not in systems_tested:
                    systems_tested.append(br.system_name)
                n_benchmarks = max(n_benchmarks, len(br.results))
                n_cases = max(n_cases, br.total_test_cases)

        methodology = (
            f"A/B comparison with {n_cases} test cases per benchmark. "
            f"Statistical significance assessed using Welch's t-test "
            f"with Cohen's d effect size. Emergence threshold: 1.5x "
            f"improvement over best baseline."
        )

        benchmark_names: list[str] = []
        if benchmark_results and benchmark_results[0].results:
            benchmark_names = [r.benchmark_name for r in benchmark_results[0].results]

        return ExperimentDesign(
            n_systems=len(systems_tested),
            n_benchmarks=n_benchmarks,
            n_test_cases=n_cases,
            systems_tested=systems_tested,
            benchmarks_run=benchmark_names,
            methodology=methodology,
        )

    def _build_cost_analysis(
        self,
        benchmark_results: list[BenchmarkSuiteResult] | None,
        tournament_result: TournamentResult | None,
    ) -> CostAnalysis:
        """Build cost analysis section."""
        system_costs: dict[str, float] = {}
        performance_per_cost: dict[str, float] = {}

        if benchmark_results:
            for br in benchmark_results:
                # Simulated cost based on execution time
                cost = br.total_execution_time_ms * 0.001  # $1 per second
                system_costs[br.system_name] = round(cost, 4)
                if cost > 0:
                    performance_per_cost[br.system_name] = round(br.overall_score / cost, 6)

        most_efficient = ""
        if performance_per_cost:
            most_efficient = max(performance_per_cost, key=performance_per_cost.get)

        return CostAnalysis(
            system_costs=system_costs,
            performance_per_cost=performance_per_cost,
            most_efficient=most_efficient,
        )

    def _identify_strengths_weaknesses(
        self,
        benchmark_results: list[BenchmarkSuiteResult] | None,
        cognitive_metrics: CognitiveMetricsResult | None,
        failure_analysis: FailureAnalysisReport | None,
        emergence_analysis: EmergenceAnalysisResult | None,
    ) -> tuple[list[str], list[str]]:
        """Identify strengths and weaknesses from all analysis."""
        strengths: list[str] = []
        weaknesses: list[str] = []

        # From benchmark results
        if benchmark_results:
            # Find ACOS results
            acos_result = next(
                (br for br in benchmark_results if "ACOS" in br.system_name.upper()),
                None,
            )
            if acos_result:
                for cat, score in acos_result.category_scores.items():
                    if score >= 0.7:
                        strengths.append(f"{cat} benchmark score: {score:.3f} (strong)")
                    elif score < 0.5:
                        weaknesses.append(f"{cat} benchmark score: {score:.3f} (weak)")

        # From cognitive metrics
        if cognitive_metrics:
            for m in cognitive_metrics.metrics:
                if m.is_above_baseline:
                    strengths.append(f"{m.metric_name}: {m.value:.3f} (above baseline)")
                else:
                    weaknesses.append(f"{m.metric_name}: {m.value:.3f} (below baseline)")

        # From failure analysis
        if failure_analysis:
            for fr in failure_analysis.failure_reports:
                if not fr.detected:
                    strengths.append(f"No {fr.failure_type.value} detected")
                elif fr.severity > 0.5:
                    weaknesses.append(f"{fr.failure_type.value}: severity {fr.severity:.3f}")

        # From emergence analysis
        if emergence_analysis:
            for cap in emergence_analysis.emergent_capabilities:
                strengths.append(f"Emergent {cap} capability detected")
            for cap in emergence_analysis.non_emergent_capabilities:
                weaknesses.append(f"{cap} capability not emergent over baselines")

        return strengths, weaknesses

    def _generate_recommendations(
        self,
        weaknesses: list[str],
        failure_analysis: FailureAnalysisReport | None,
        emergence_analysis: EmergenceAnalysisResult | None,
    ) -> list[str]:
        """Generate architecture change recommendations."""
        recommendations: list[str] = []

        # From failure analysis
        if failure_analysis:
            for fr in failure_analysis.failure_reports:
                if fr.detected:
                    for action in fr.recommended_actions[:2]:
                        if action not in recommendations:
                            recommendations.append(action)

        # From emergence gaps
        if emergence_analysis:
            for cap in emergence_analysis.non_emergent_capabilities:
                recommendations.append(
                    f"Investigate why {cap} capability is not emergent — "
                    f"consider enhancing the underlying cognitive module"
                )

        # General recommendations based on common patterns
        if any("memory" in w.lower() for w in weaknesses):
            recommendations.append(
                "Enhance memory consolidation pipeline with "
                "interference-resistant storage and retrieval"
            )

        if any("prediction" in w.lower() for w in weaknesses):
            recommendations.append(
                "Improve world model accuracy through active learning "
                "and more frequent model updates"
            )

        if any("reasoning" in w.lower() for w in weaknesses):
            recommendations.append(
                "Strengthen reasoning engine with explicit chain-of-thought "
                "verification and self-correction loops"
            )

        # Ensure we always have some recommendations
        if not recommendations:
            recommendations = [
                "Continue monitoring cognitive metrics over time",
                "Run extended benchmarks with more test cases",
                "Validate results against real-world scenarios",
            ]

        return recommendations[:10]  # Cap at 10

    def _generate_conclusion(
        self,
        benchmark_results: list[BenchmarkSuiteResult] | None,
        tournament_result: TournamentResult | None,
        emergence_analysis: EmergenceAnalysisResult | None,
    ) -> str:
        """Generate report conclusion."""
        parts: list[str] = []

        # Tournament result
        if tournament_result and tournament_result.best_system:
            parts.append(
                f"In the tournament comparison, {tournament_result.best_system} "
                f"ranked first across all benchmarks."
            )
            if "ACOS" in tournament_result.best_system.upper():
                parts.append(
                    "This provides evidence that the ACOS cognitive architecture "
                    "provides measurable advantages over baseline systems."
                )
            else:
                parts.append(
                    "ACOS did not rank first in the tournament, suggesting areas "
                    "for improvement in the cognitive architecture."
                )

        # Emergence result
        if emergence_analysis:
            n_emergent = len(emergence_analysis.emergent_capabilities)
            n_total = n_emergent + len(emergence_analysis.non_emergent_capabilities)
            parts.append(
                f"Of {n_total} capability dimensions analyzed, {n_emergent} "
                f"showed emergent behavior (improvement factor >= 1.5x over "
                f"best baseline). "
                f"Overall emergence score: {emergence_analysis.overall_emergence_score:.3f}."
            )
            if emergence_analysis.emergent_capabilities:
                parts.append(
                    f"Emergent capabilities: "
                    f"{', '.join(emergence_analysis.emergent_capabilities)}."
                )

        if not parts:
            parts.append(
                "Insufficient data to draw conclusions. "
                "Run the full validation suite for comprehensive analysis."
            )

        return " ".join(parts)
