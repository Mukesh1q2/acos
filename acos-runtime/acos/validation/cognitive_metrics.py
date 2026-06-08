"""
Cognitive Metrics Calculator for ACOS Validation Lab v1.0.

Phase 4: Unified cognitive metrics that evaluate system state
across multiple cognitive dimensions.

Metrics:
- Belief accuracy: How well do beliefs match reality
- Goal completion rate: Fraction of goals achieved
- Memory utilization: How effectively memory is used
- Prediction accuracy: How accurate predictions are
- Uncertainty calibration: Brier score for confidence calibration
- Reflection quality: Quality of self-reflection
- Causal accuracy: Accuracy of causal reasoning
- Counterfactual accuracy: Accuracy of counterfactual reasoning
"""

from __future__ import annotations

import math
from typing import Any

from acos.validation.models import (
    CognitiveMetricResult,
    CognitiveMetricsResult,
)


class CognitiveMetrics:
    """Unified cognitive metrics calculator.
    
    Computes metrics based on system state, which can be derived
    from the ACOS Runtime's internal state or from simulated baselines.
    
    Usage::
    
        metrics = CognitiveMetrics()
        result = metrics.compute_all(system_state)
    """

    # Baseline thresholds (based on typical LLM performance)
    BASELINES: dict[str, float] = {
        "belief_accuracy": 0.45,
        "goal_completion_rate": 0.50,
        "memory_utilization": 0.40,
        "prediction_accuracy": 0.50,
        "uncertainty_calibration": 0.55,  # 1 - brier
        "reflection_quality": 0.40,
        "causal_accuracy": 0.50,
        "counterfactual_accuracy": 0.45,
    }

    def belief_accuracy(self, system_state: dict[str, Any]) -> float:
        """Compute belief accuracy: how well beliefs match reality.
        
        Uses the average |confidence - actual_correctness| across beliefs.
        Result is 1.0 - average_error.
        """
        beliefs = system_state.get("beliefs", [])
        if not beliefs:
            return 0.0

        total_error = 0.0
        n = 0
        for belief in beliefs:
            if isinstance(belief, dict):
                confidence = float(belief.get("confidence", 0.5))
                actual = float(belief.get("actual_correctness", 0.5))
                total_error += abs(confidence - actual)
                n += 1

        if n == 0:
            return 0.0

        return max(0.0, 1.0 - total_error / n)

    def goal_completion_rate(self, system_state: dict[str, Any]) -> float:
        """Compute goal completion rate.
        
        Fraction of goals that have been completed.
        """
        goals = system_state.get("goals", [])
        if not goals:
            return 0.0

        completed = 0
        total = 0
        for goal in goals:
            if isinstance(goal, dict):
                total += 1
                if goal.get("completed", False) or goal.get("progress", 0) >= 1.0:
                    completed += 1

        return completed / max(total, 1)

    def memory_utilization(self, system_state: dict[str, Any]) -> float:
        """Compute memory utilization efficiency.
        
        Measures how effectively stored memories are being retrieved
        and used. Combines retrieval rate and relevance.
        """
        memories = system_state.get("memories", [])
        memory_stats = system_state.get("memory_stats", {})

        if not memories and not memory_stats:
            return 0.0

        # If we have stats, use them
        if memory_stats:
            retrieval_rate = float(memory_stats.get("retrieval_rate", 0.5))
            avg_relevance = float(memory_stats.get("average_relevance", 0.5))
            return 0.5 * retrieval_rate + 0.5 * avg_relevance

        # Otherwise estimate from memory count
        n_memories = len(memories)
        if n_memories == 0:
            return 0.0

        # Logarithmic scaling: more memories = better utilization, with diminishing returns
        utilization = math.log1p(n_memories) / math.log1p(100)  # Normalize to ~1.0 at 100 memories
        return min(1.0, utilization)

    def prediction_accuracy(self, system_state: dict[str, Any]) -> float:
        """Compute prediction accuracy.
        
        1.0 - average prediction error for verified predictions.
        """
        predictions = system_state.get("predictions", [])
        if not predictions:
            return 0.0

        total_error = 0.0
        n_verified = 0
        for pred in predictions:
            if isinstance(pred, dict):
                error = pred.get("prediction_error")
                if error is not None:
                    total_error += float(error)
                    n_verified += 1

        if n_verified == 0:
            # Use a default based on available data
            return 0.5

        return max(0.0, min(1.0, 1.0 - total_error / n_verified))

    def uncertainty_calibration(self, system_state: dict[str, Any]) -> float:
        """Compute uncertainty calibration using Brier score.
        
        Brier score = mean((predicted_prob - actual_outcome)^2)
        Returns 1.0 - brier_score (higher is better calibrated).
        """
        predictions = system_state.get("predictions", [])
        calibration_data = system_state.get("calibration_data", [])

        # Use calibration_data if available
        if calibration_data:
            brier_sum = 0.0
            n = 0
            for item in calibration_data:
                if isinstance(item, dict):
                    predicted = float(item.get("predicted_prob", 0.5))
                    actual = float(item.get("actual_outcome", 0.5))
                    brier_sum += (predicted - actual) ** 2
                    n += 1

            if n > 0:
                brier = brier_sum / n
                return max(0.0, 1.0 - brier)

        # Fall back to predictions
        if predictions:
            brier_sum = 0.0
            n = 0
            for pred in predictions:
                if isinstance(pred, dict):
                    prob = float(pred.get("predicted_prob", 0.5))
                    outcome = float(pred.get("actual_outcome", 0.5))
                    brier_sum += (prob - outcome) ** 2
                    n += 1

            if n > 0:
                brier = brier_sum / n
                return max(0.0, 1.0 - brier)

        return 0.5  # Default

    def reflection_quality(self, system_state: dict[str, Any]) -> float:
        """Compute reflection quality.
        
        Measures how well the system reflects on its own performance
        and identifies issues. Based on issue detection rate and
        improvement suggestions.
        """
        reflections = system_state.get("reflections", [])
        self_model = system_state.get("self_model", {})

        if self_model:
            # Use self-model data if available
            strengths_count = len(self_model.get("strengths", []))
            weaknesses_count = len(self_model.get("weaknesses", []))
            avg_performance = float(self_model.get("average_performance", 0.5))

            # Good reflection = identifies both strengths and weaknesses
            balance = min(strengths_count, weaknesses_count) / max(
                max(strengths_count, weaknesses_count), 1
            )
            return 0.5 * avg_performance + 0.5 * balance

        if reflections:
            total_quality = 0.0
            n = 0
            for reflection in reflections:
                if isinstance(reflection, dict):
                    quality = float(reflection.get("quality_score", 0.5))
                    issues_found = len(reflection.get("issues_found", []))
                    # Quality increases with issues found (up to a point)
                    detection_bonus = min(0.2, issues_found * 0.05)
                    total_quality += min(1.0, quality + detection_bonus)
                    n += 1

            return total_quality / max(n, 1)

        return 0.5  # Default

    def causal_accuracy(self, system_state: dict[str, Any]) -> float:
        """Compute causal reasoning accuracy.
        
        Measures how accurately the system identifies and reasons
        about cause-effect relationships.
        """
        causal_data = system_state.get("causal_reasoning", [])

        if causal_data:
            correct = 0
            total = 0
            for item in causal_data:
                if isinstance(item, dict):
                    total += 1
                    if item.get("correct", False):
                        correct += 1

            return correct / max(total, 1)

        # Estimate from reasoning results
        reasoning_results = system_state.get("reasoning_results", [])
        causal_results = [
            r for r in reasoning_results
            if isinstance(r, dict) and r.get("reasoning_type") == "causal"
        ]

        if causal_results:
            correct = sum(1 for r in causal_results if r.get("correct", False))
            return correct / max(len(causal_results), 1)

        return 0.5  # Default

    def counterfactual_accuracy(self, system_state: dict[str, Any]) -> float:
        """Compute counterfactual reasoning accuracy.
        
        Measures how accurately the system reasons about
        "what would have happened if" scenarios.
        """
        counterfactual_data = system_state.get("counterfactual_reasoning", [])

        if counterfactual_data:
            correct = 0
            total = 0
            for item in counterfactual_data:
                if isinstance(item, dict):
                    total += 1
                    if item.get("correct", False):
                        correct += 1

            return correct / max(total, 1)

        # Estimate from reasoning results
        reasoning_results = system_state.get("reasoning_results", [])
        cf_results = [
            r for r in reasoning_results
            if isinstance(r, dict) and r.get("reasoning_type") == "counterfactual"
        ]

        if cf_results:
            correct = sum(1 for r in cf_results if r.get("correct", False))
            return correct / max(len(cf_results), 1)

        return 0.5  # Default

    def compute_all(self, system_state: dict[str, Any], system_name: str = "unknown") -> CognitiveMetricsResult:
        """Compute all cognitive metrics.
        
        Returns a CognitiveMetricsResult with all metric values,
        interpretations, and comparisons to baseline.
        """
        metrics_map = {
            "belief_accuracy": self.belief_accuracy,
            "goal_completion_rate": self.goal_completion_rate,
            "memory_utilization": self.memory_utilization,
            "prediction_accuracy": self.prediction_accuracy,
            "uncertainty_calibration": self.uncertainty_calibration,
            "reflection_quality": self.reflection_quality,
            "causal_accuracy": self.causal_accuracy,
            "counterfactual_accuracy": self.counterfactual_accuracy,
        }

        results: list[CognitiveMetricResult] = []
        strengths: list[str] = []
        weaknesses: list[str] = []

        for metric_name, compute_fn in metrics_map.items():
            value = round(compute_fn(system_state), 6)
            baseline = self.BASELINES.get(metric_name, 0.5)

            # Percentile vs baseline (simple ratio)
            percentile = min(1.0, value / max(baseline, 0.01))
            is_above = value > baseline

            # Interpretation
            if value >= 0.8:
                interpretation = "Excellent"
            elif value >= 0.6:
                interpretation = "Good"
            elif value >= 0.4:
                interpretation = "Fair"
            else:
                interpretation = "Needs improvement"

            result = CognitiveMetricResult(
                metric_name=metric_name,
                value=value,
                interpretation=interpretation,
                percentile_vs_baseline=round(percentile, 4),
                is_above_baseline=is_above,
            )
            results.append(result)

            if is_above:
                strengths.append(f"{metric_name}: {value:.3f} (above baseline {baseline:.3f})")
            else:
                weaknesses.append(f"{metric_name}: {value:.3f} (below baseline {baseline:.3f})")

        # Overall cognitive score: average of all metrics
        overall = sum(r.value for r in results) / max(len(results), 1)

        return CognitiveMetricsResult(
            system_name=system_name,
            metrics=results,
            overall_cognitive_score=round(overall, 6),
            strengths=strengths,
            weaknesses=weaknesses,
        )
