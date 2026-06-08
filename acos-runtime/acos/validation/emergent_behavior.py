"""
Emergent Behavior Analysis for ACOS Validation Lab v1.0.

Phase 6: Analyze emergent behaviors in ACOS vs baseline systems.

Emergence occurs when ACOS demonstrates capabilities that exceed
what would be expected from simply combining its components.
We measure this by comparing ACOS performance against the best
baseline in each dimension.

Emergence types:
- Planning: Emergent planning capabilities
- Memory: Emergent memory organization and retrieval
- Adaptation: Emergent learning and adaptation
- Reasoning: Emergent reasoning patterns
- Self-correction: Emergent self-monitoring and correction
"""

from __future__ import annotations

from typing import Any

from acos.validation.models import (
    BenchmarkResult,
    BenchmarkSuiteResult,
    EmergenceAnalysisResult,
    EmergenceIndicator,
    EmergenceReport,
    EmergenceType,
)


class EmergentBehaviorAnalyzer:
    """Analyze emergent behaviors in ACOS vs baselines.
    
    Usage::
    
        analyzer = EmergentBehaviorAnalyzer()
        result = analyzer.analyze_all(acos_results, baseline_results)
    """
    
    # Default threshold: ACOS must be 1.5x better than best baseline
    DEFAULT_EMERGENCE_THRESHOLD = 1.5

    def analyze_planning_emergence(
        self,
        acos_results: BenchmarkSuiteResult,
        baseline_results: list[BenchmarkSuiteResult],
    ) -> EmergenceReport:
        """Analyze emergent planning capabilities.
        
        Looks for planning performance that exceeds what baselines
        achieve, particularly in:
        - Goal decomposition quality
        - Dependency handling
        - Plan completion under constraints
        """
        acos_planning = self._get_category_scores(acos_results, "planning")
        best_baseline_planning = max(
            (self._get_category_scores(br, "planning") for br in baseline_results),
            key=lambda s: s.get("overall", 0.0),
            default={"overall": 0.0},
        )

        indicators = self._compute_indicators(
            acos_planning, best_baseline_planning,
            [
                ("goal_decomposition", "Goal Decomposition Quality"),
                ("multi_step_planning", "Multi-step Planning Accuracy"),
                ("dependency_handling", "Dependency Resolution"),
                ("plan_completion_rate", "Plan Completion Rate"),
            ],
        )

        emergence_score = self._compute_emergence_score(indicators)
        strongest = max(indicators, key=lambda i: i.improvement_factor) if indicators else None

        return EmergenceReport(
            emergence_type=EmergenceType.PLANNING,
            indicators=indicators,
            emergence_score=emergence_score,
            strongest_emergence=strongest.name if strongest else "",
            analysis_summary=(
                f"Planning emergence score: {emergence_score:.3f}. "
                f"ACOS planning {'shows' if emergence_score > 0.5 else 'does not show'} "
                f"significant emergent behavior over baselines."
            ),
        )

    def analyze_memory_emergence(
        self,
        acos_results: BenchmarkSuiteResult,
        baseline_results: list[BenchmarkSuiteResult],
    ) -> EmergenceReport:
        """Analyze emergent memory capabilities."""
        acos_memory = self._get_category_scores(acos_results, "memory")
        best_baseline_memory = max(
            (self._get_category_scores(br, "memory") for br in baseline_results),
            key=lambda s: s.get("overall", 0.0),
            default={"overall": 0.0},
        )

        indicators = self._compute_indicators(
            acos_memory, best_baseline_memory,
            [
                ("recall_accuracy", "Recall Accuracy"),
                ("long_term_retention", "Long-term Retention"),
                ("retrieval_quality", "Retrieval Quality"),
                ("knowledge_consolidation", "Knowledge Consolidation"),
            ],
        )

        emergence_score = self._compute_emergence_score(indicators)
        strongest = max(indicators, key=lambda i: i.improvement_factor) if indicators else None

        return EmergenceReport(
            emergence_type=EmergenceType.MEMORY,
            indicators=indicators,
            emergence_score=emergence_score,
            strongest_emergence=strongest.name if strongest else "",
            analysis_summary=(
                f"Memory emergence score: {emergence_score:.3f}. "
                f"ACOS memory {'shows' if emergence_score > 0.5 else 'does not show'} "
                f"significant emergent behavior over baselines."
            ),
        )

    def analyze_adaptation_emergence(
        self,
        acos_results: BenchmarkSuiteResult,
        baseline_results: list[BenchmarkSuiteResult],
    ) -> EmergenceReport:
        """Analyze emergent adaptation capabilities."""
        acos_learning = self._get_category_scores(acos_results, "learning")
        best_baseline_learning = max(
            (self._get_category_scores(br, "learning") for br in baseline_results),
            key=lambda s: s.get("overall", 0.0),
            default={"overall": 0.0},
        )

        indicators = self._compute_indicators(
            acos_learning, best_baseline_learning,
            [
                ("belief_updates", "Belief Update Accuracy"),
                ("error_correction", "Error Correction Speed"),
                ("adaptation_speed", "Adaptation Speed"),
                ("confidence_calibration", "Confidence Calibration"),
            ],
        )

        emergence_score = self._compute_emergence_score(indicators)
        strongest = max(indicators, key=lambda i: i.improvement_factor) if indicators else None

        return EmergenceReport(
            emergence_type=EmergenceType.ADAPTATION,
            indicators=indicators,
            emergence_score=emergence_score,
            strongest_emergence=strongest.name if strongest else "",
            analysis_summary=(
                f"Adaptation emergence score: {emergence_score:.3f}. "
                f"ACOS adaptation {'shows' if emergence_score > 0.5 else 'does not show'} "
                f"significant emergent behavior over baselines."
            ),
        )

    def analyze_reasoning_emergence(
        self,
        acos_results: BenchmarkSuiteResult,
        baseline_results: list[BenchmarkSuiteResult],
    ) -> EmergenceReport:
        """Analyze emergent reasoning capabilities."""
        acos_reasoning = self._get_category_scores(acos_results, "reasoning")
        best_baseline_reasoning = max(
            (self._get_category_scores(br, "reasoning") for br in baseline_results),
            key=lambda s: s.get("overall", 0.0),
            default={"overall": 0.0},
        )

        indicators = self._compute_indicators(
            acos_reasoning, best_baseline_reasoning,
            [
                ("deductive_reasoning", "Deductive Reasoning"),
                ("inductive_reasoning", "Inductive Reasoning"),
                ("causal_reasoning", "Causal Reasoning"),
                ("counterfactual_reasoning", "Counterfactual Reasoning"),
            ],
        )

        emergence_score = self._compute_emergence_score(indicators)
        strongest = max(indicators, key=lambda i: i.improvement_factor) if indicators else None

        return EmergenceReport(
            emergence_type=EmergenceType.REASONING,
            indicators=indicators,
            emergence_score=emergence_score,
            strongest_emergence=strongest.name if strongest else "",
            analysis_summary=(
                f"Reasoning emergence score: {emergence_score:.3f}. "
                f"ACOS reasoning {'shows' if emergence_score > 0.5 else 'does not show'} "
                f"significant emergent behavior over baselines."
            ),
        )

    def analyze_self_correction_emergence(
        self,
        acos_results: BenchmarkSuiteResult,
        baseline_results: list[BenchmarkSuiteResult],
    ) -> EmergenceReport:
        """Analyze emergent self-correction capabilities.
        
        Self-correction is a meta-capability that combines
        learning and prediction abilities.
        """
        # Self-correction combines learning and prediction
        acos_learning = self._get_category_scores(acos_results, "learning")
        acos_prediction = self._get_category_scores(acos_results, "prediction")
        
        # Combined self-correction score
        acos_combined = {
            "belief_updates": acos_learning.get("belief_updates", 0.0),
            "error_correction": acos_learning.get("error_correction", 0.0),
            "adaptation_speed": acos_learning.get("adaptation_speed", 0.0),
            "prediction_accuracy": acos_prediction.get("future_state_prediction", 0.0),
        }

        best_baseline_combined: dict[str, float] = {}
        for br in baseline_results:
            bl = self._get_category_scores(br, "learning")
            bp = self._get_category_scores(br, "prediction")
            combined = {
                "belief_updates": bl.get("belief_updates", 0.0),
                "error_correction": bl.get("error_correction", 0.0),
                "adaptation_speed": bl.get("adaptation_speed", 0.0),
                "prediction_accuracy": bp.get("future_state_prediction", 0.0),
            }
            if sum(combined.values()) > sum(best_baseline_combined.values()):
                best_baseline_combined = combined

        indicators = self._compute_indicators(
            acos_combined, best_baseline_combined,
            [
                ("belief_updates", "Self-Correcting Beliefs"),
                ("error_correction", "Error Detection & Correction"),
                ("adaptation_speed", "Rapid Adaptation"),
                ("prediction_accuracy", "Self-Monitoring via Prediction"),
            ],
        )

        emergence_score = self._compute_emergence_score(indicators)
        strongest = max(indicators, key=lambda i: i.improvement_factor) if indicators else None

        return EmergenceReport(
            emergence_type=EmergenceType.SELF_CORRECTION,
            indicators=indicators,
            emergence_score=emergence_score,
            strongest_emergence=strongest.name if strongest else "",
            analysis_summary=(
                f"Self-correction emergence score: {emergence_score:.3f}. "
                f"ACOS self-correction {'shows' if emergence_score > 0.5 else 'does not show'} "
                f"significant emergent behavior over baselines."
            ),
        )

    def analyze_all(
        self,
        acos_results: BenchmarkSuiteResult,
        baseline_results: list[BenchmarkSuiteResult],
    ) -> EmergenceAnalysisResult:
        """Run all emergence analyses and aggregate."""
        reports = [
            self.analyze_planning_emergence(acos_results, baseline_results),
            self.analyze_memory_emergence(acos_results, baseline_results),
            self.analyze_adaptation_emergence(acos_results, baseline_results),
            self.analyze_reasoning_emergence(acos_results, baseline_results),
            self.analyze_self_correction_emergence(acos_results, baseline_results),
        ]

        overall = sum(r.emergence_score for r in reports) / max(len(reports), 1)

        emergent = [
            r.emergence_type.value
            for r in reports
            if any(i.is_emergent for i in r.indicators)
        ]
        non_emergent = [
            r.emergence_type.value
            for r in reports
            if not any(i.is_emergent for i in r.indicators)
        ]

        return EmergenceAnalysisResult(
            reports=reports,
            overall_emergence_score=round(overall, 6),
            emergent_capabilities=emergent,
            non_emergent_capabilities=non_emergent,
        )

    # ─── Helpers ───────────────────────────────────────────────────────────────

    def _get_category_scores(
        self,
        result: BenchmarkSuiteResult,
        category: str,
    ) -> dict[str, float]:
        """Extract per-benchmark scores for a category."""
        scores: dict[str, float] = {"overall": result.category_scores.get(category, 0.0)}
        for r in result.results:
            if r.category.value == category:
                scores[r.benchmark_name] = r.overall_score
        return scores

    def _compute_indicators(
        self,
        acos_scores: dict[str, float],
        baseline_scores: dict[str, float],
        dimensions: list[tuple[str, str]],
    ) -> list[EmergenceIndicator]:
        """Compute emergence indicators for a set of dimensions."""
        indicators: list[EmergenceIndicator] = []
        
        for key, label in dimensions:
            acos_val = acos_scores.get(key, 0.0)
            baseline_val = baseline_scores.get(key, 0.0)
            
            if baseline_val > 0:
                improvement = acos_val / baseline_val
            elif acos_val > 0:
                improvement = float('inf')
            else:
                improvement = 1.0
            
            is_emergent = improvement >= self.DEFAULT_EMERGENCE_THRESHOLD

            indicators.append(EmergenceIndicator(
                name=label,
                acos_value=round(acos_val, 6),
                best_baseline_value=round(baseline_val, 6),
                improvement_factor=round(min(improvement, 10.0), 4),  # Cap for display
                is_emergent=is_emergent,
                threshold=self.DEFAULT_EMERGENCE_THRESHOLD,
            ))

        return indicators

    def _compute_emergence_score(self, indicators: list[EmergenceIndicator]) -> float:
        """Compute overall emergence score from indicators.
        
        Score is the fraction of indicators that show emergence,
        weighted by improvement factor.
        """
        if not indicators:
            return 0.0

        total_weight = 0.0
        emergence_sum = 0.0

        for ind in indicators:
            # Weight by improvement factor (capped at threshold)
            weight = min(ind.improvement_factor / ind.threshold, 2.0)
            total_weight += weight
            
            if ind.is_emergent:
                emergence_sum += weight

        return round(emergence_sum / max(total_weight, 1e-10), 6)
