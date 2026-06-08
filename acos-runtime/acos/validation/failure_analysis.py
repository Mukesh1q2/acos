"""
Failure Analysis for ACOS Validation Lab v1.0.

Phase 5: Automated failure mode detection and analysis.

Detects failure modes in cognitive systems:
- Belief collapse: Confidence drops to near zero
- Contradiction accumulation: Unresolved contradictions growing
- Memory corruption: Stored information becoming unreliable
- Goal oscillation: Goals switching back and forth
- Planning loops: Plans repeating without progress
- Prediction drift: Predictions becoming increasingly inaccurate
"""

from __future__ import annotations

from typing import Any

from acos.validation.models import (
    FailureAnalysisReport,
    FailureReport,
    FailureType,
)


class FailureAnalyzer:
    """Automated failure mode detection and analysis.
    
    Usage::
    
        analyzer = FailureAnalyzer()
        report = analyzer.generate_report(system_state)
    """

    # Thresholds for failure detection
    COLLAPSE_THRESHOLD = 0.15  # Belief confidence below this = collapse
    CONTRADICTION_THRESHOLD = 5  # More than this = accumulation
    CORRUPTION_THRESHOLD = 0.3  # Memory accuracy below this = corruption
    OSCILLATION_THRESHOLD = 3  # More than N goal switches = oscillation
    LOOP_THRESHOLD = 2  # More than N plan repeats = loop
    DRIFT_THRESHOLD = 0.15  # Prediction error above this = drift

    def detect_belief_collapse(self, system_state: dict[str, Any]) -> FailureReport:
        """Detect belief collapse: when confidence drops to near-zero.
        
        A belief collapse occurs when the system loses confidence in
        most of its beliefs, typically due to conflicting evidence
        or internal inconsistency.
        """
        beliefs = system_state.get("beliefs", [])
        if not beliefs:
            return FailureReport(
                failure_type=FailureType.BELIEF_COLLAPSE,
                detected=False,
                description="No beliefs to analyze",
            )

        collapsed_count = 0
        total_confidence = 0.0
        collapsed_beliefs: list[str] = []

        for belief in beliefs:
            if isinstance(belief, dict):
                confidence = float(belief.get("confidence", 0.5))
                total_confidence += confidence
                if confidence < self.COLLAPSE_THRESHOLD:
                    collapsed_count += 1
                    statement = belief.get("statement", belief.get("content", "unknown"))
                    collapsed_beliefs.append(str(statement))

        n = len(beliefs)
        avg_confidence = total_confidence / max(n, 1)
        collapse_ratio = collapsed_count / max(n, 1)
        
        detected = collapse_ratio > 0.3 or avg_confidence < 0.2
        severity = min(1.0, collapse_ratio * 2 + (1 - avg_confidence) * 0.5)

        return FailureReport(
            failure_type=FailureType.BELIEF_COLLAPSE,
            detected=detected,
            severity=round(severity, 4),
            description=(
                f"Belief collapse detected: {collapsed_count}/{n} beliefs have "
                f"confidence below {self.COLLAPSE_THRESHOLD}. "
                f"Average confidence: {avg_confidence:.3f}"
            ),
            affected_components=["belief_system"],
            evidence=[
                {"collapsed_count": collapsed_count, "total_beliefs": n,
                 "avg_confidence": round(avg_confidence, 4), "collapse_ratio": round(collapse_ratio, 4)},
            ],
            recommended_actions=[
                "Review evidence sources for contradictory inputs",
                "Implement belief stabilization mechanisms",
                "Add confidence floor to prevent total collapse",
            ],
        )

    def detect_contradiction_accumulation(self, system_state: dict[str, Any]) -> FailureReport:
        """Detect contradiction accumulation: unresolved contradictions growing.
        
        When the system fails to resolve contradictions, they can
        accumulate and degrade overall reasoning quality.
        """
        contradictions = system_state.get("contradictions", [])
        resolved = system_state.get("resolved_contradictions", 0)
        
        n_contradictions = len(contradictions) if isinstance(contradictions, list) else int(contradictions)
        total = n_contradictions + int(resolved)
        
        if total == 0:
            return FailureReport(
                failure_type=FailureType.CONTRADICTION_ACCUMULATION,
                detected=False,
                description="No contradictions to analyze",
            )

        unresolved_ratio = n_contradictions / max(total, 1)
        detected = n_contradictions > self.CONTRADICTION_THRESHOLD
        severity = min(1.0, unresolved_ratio * 1.5)

        return FailureReport(
            failure_type=FailureType.CONTRADICTION_ACCUMULATION,
            detected=detected,
            severity=round(severity, 4),
            description=(
                f"Contradiction accumulation: {n_contradictions} unresolved "
                f"contradictions out of {total} total. "
                f"Resolution rate: {1 - unresolved_ratio:.1%}"
            ),
            affected_components=["belief_system", "knowledge_fabric"],
            evidence=[
                {"unresolved": n_contradictions, "resolved": int(resolved),
                 "resolution_rate": round(1 - unresolved_ratio, 4)},
            ],
            recommended_actions=[
                "Implement automatic contradiction resolution",
                "Add priority-based contradiction triage",
                "Strengthen belief revision mechanisms",
            ],
        )

    def detect_memory_corruption(self, system_state: dict[str, Any]) -> FailureReport:
        """Detect memory corruption: stored information becoming unreliable.
        
        Memory corruption occurs when stored memories no longer
        accurately reflect what was originally stored, often due to
        interference or consolidation errors.
        """
        memory_stats = system_state.get("memory_stats", {})
        memories = system_state.get("memories", [])

        # Check for accuracy metrics
        accuracy = float(memory_stats.get("retrieval_accuracy", -1))
        
        if accuracy < 0:
            # Estimate from memory state
            if not memories:
                return FailureReport(
                    failure_type=FailureType.MEMORY_CORRUPTION,
                    detected=False,
                    description="No memories to analyze",
                )
            
            # Heuristic: check if memories have inconsistent metadata
            corrupted = 0
            for mem in memories:
                if isinstance(mem, dict):
                    # Check for signs of corruption
                    if mem.get("corrupted", False):
                        corrupted += 1
                    elif not mem.get("content") and not mem.get("query"):
                        corrupted += 1
            
            accuracy = 1.0 - (corrupted / max(len(memories), 1))

        detected = accuracy < self.CORRUPTION_THRESHOLD
        severity = min(1.0, (1 - accuracy) * 2)

        return FailureReport(
            failure_type=FailureType.MEMORY_CORRUPTION,
            detected=detected,
            severity=round(severity, 4),
            description=(
                f"Memory corruption analysis: retrieval accuracy = {accuracy:.3f}. "
                f"{'Corruption detected' if detected else 'No significant corruption'}."
            ),
            affected_components=["memory_manager", "semantic_memory", "otm"],
            evidence=[
                {"retrieval_accuracy": round(accuracy, 4),
                 "threshold": self.CORRUPTION_THRESHOLD},
            ],
            recommended_actions=[
                "Implement memory integrity checks",
                "Add versioning to stored memories",
                "Use checksums for memory verification",
            ],
        )

    def detect_goal_oscillation(self, system_state: dict[str, Any]) -> FailureReport:
        """Detect goal oscillation: goals switching back and forth.
        
        Goal oscillation occurs when the system repeatedly switches
        between goals without making progress on any of them.
        """
        goals = system_state.get("goals", [])
        goal_history = system_state.get("goal_history", [])

        if not goal_history:
            # Estimate from current goals
            if not goals:
                return FailureReport(
                    failure_type=FailureType.GOAL_OSCILLATION,
                    detected=False,
                    description="No goals to analyze",
                )
            
            # Check for goals with low progress and high priority changes
            oscillating = 0
            for goal in goals:
                if isinstance(goal, dict):
                    progress = float(goal.get("progress", 0))
                    priority_changes = int(goal.get("priority_changes", 0))
                    if progress < 0.3 and priority_changes > self.OSCILLATION_THRESHOLD:
                        oscillating += 1
            
            detected = oscillating > 0
            severity = min(1.0, oscillating / max(len(goals), 1))
            
            return FailureReport(
                failure_type=FailureType.GOAL_OSCILLATION,
                detected=detected,
                severity=round(severity, 4),
                description=(
                    f"Goal oscillation: {oscillating} goals show signs of "
                    f"oscillation (low progress + high priority changes)."
                ),
                affected_components=["goal_manager", "attention_economy"],
                evidence=[
                    {"oscillating_goals": oscillating, "total_goals": len(goals)},
                ],
                recommended_actions=[
                    "Implement goal commitment mechanisms",
                    "Add cooldown period for goal priority changes",
                    "Use goal competition with momentum",
                ],
            )

        # Analyze goal history for oscillation patterns
        switches = 0
        for i in range(1, len(goal_history)):
            if isinstance(goal_history[i], dict) and isinstance(goal_history[i-1], dict):
                if goal_history[i].get("active_goal") != goal_history[i-1].get("active_goal"):
                    switches += 1

        detected = switches > self.OSCILLATION_THRESHOLD
        severity = min(1.0, switches / max(len(goal_history), 1) * 5)

        return FailureReport(
            failure_type=FailureType.GOAL_OSCILLATION,
            detected=detected,
            severity=round(severity, 4),
            description=(
                f"Goal oscillation: {switches} goal switches in "
                f"{len(goal_history)} history entries."
            ),
            affected_components=["goal_manager", "attention_economy"],
            evidence=[
                {"switches": switches, "history_length": len(goal_history)},
            ],
            recommended_actions=[
                "Implement goal commitment mechanisms",
                "Add cooldown period for goal switching",
                "Use goal competition with hysteresis",
            ],
        )

    def detect_planning_loops(self, system_state: dict[str, Any]) -> FailureReport:
        """Detect planning loops: plans repeating without progress.
        
        Planning loops occur when the system generates the same
        plan steps repeatedly without making progress toward the goal.
        """
        plans = system_state.get("plans", [])
        plan_history = system_state.get("plan_history", [])

        if not plans and not plan_history:
            return FailureReport(
                failure_type=FailureType.PLANNING_LOOP,
                detected=False,
                description="No plans to analyze",
            )

        # Check for repeated plan steps
        step_counts: dict[str, int] = {}
        for plan in plans:
            if isinstance(plan, dict):
                steps = plan.get("steps", [])
                for step in steps:
                    if isinstance(step, str):
                        step_counts[step] = step_counts.get(step, 0) + 1

        # Steps that appear more than the threshold indicate loops
        looped_steps = [
            (step, count) for step, count in step_counts.items()
            if count > self.LOOP_THRESHOLD
        ]

        detected = len(looped_steps) > 0
        severity = min(1.0, len(looped_steps) / max(len(step_counts), 1) * 3)

        return FailureReport(
            failure_type=FailureType.PLANNING_LOOP,
            detected=detected,
            severity=round(severity, 4),
            description=(
                f"Planning loop analysis: {len(looped_steps)} plan steps "
                f"appear more than {self.LOOP_THRESHOLD} times."
            ),
            affected_components=["planning_engine", "goal_manager"],
            evidence=[
                {"looped_steps": len(looped_steps), "unique_steps": len(step_counts),
                 "examples": looped_steps[:5]},
            ],
            recommended_actions=[
                "Add plan deduplication mechanisms",
                "Implement plan progress tracking",
                "Add maximum retry limits for plan steps",
            ],
        )

    def detect_prediction_drift(self, system_state: dict[str, Any]) -> FailureReport:
        """Detect prediction drift: predictions becoming increasingly inaccurate.
        
        Prediction drift occurs when the system's predictive accuracy
        degrades over time, often due to stale models or changing
        environment conditions.
        """
        predictions = system_state.get("predictions", [])
        prediction_history = system_state.get("prediction_errors", [])

        if not prediction_history and not predictions:
            return FailureReport(
                failure_type=FailureType.PREDICTION_DRIFT,
                detected=False,
                description="No predictions to analyze",
            )

        # Analyze prediction error trend
        if prediction_history:
            errors = [float(e) for e in prediction_history if isinstance(e, (int, float))]
        else:
            errors = [
                float(p.get("prediction_error", 0.5))
                for p in predictions
                if isinstance(p, dict) and p.get("prediction_error") is not None
            ]

        if len(errors) < 2:
            return FailureReport(
                failure_type=FailureType.PREDICTION_DRIFT,
                detected=False,
                description="Insufficient prediction data for drift analysis",
            )

        # Compute trend: compare first half vs second half
        mid = len(errors) // 2
        first_half_avg = sum(errors[:mid]) / max(mid, 1)
        second_half_avg = sum(errors[mid:]) / max(len(errors) - mid, 1)

        drift = second_half_avg - first_half_avg
        detected = drift > self.DRIFT_THRESHOLD
        severity = min(1.0, abs(drift) * 3)

        return FailureReport(
            failure_type=FailureType.PREDICTION_DRIFT,
            detected=detected,
            severity=round(severity, 4),
            description=(
                f"Prediction drift analysis: error trend = {drift:+.3f}. "
                f"First half avg: {first_half_avg:.3f}, "
                f"Second half avg: {second_half_avg:.3f}. "
                f"{'Drift detected' if detected else 'No significant drift'}."
            ),
            affected_components=["world_model", "outcome_predictor", "simulation_engine"],
            evidence=[
                {"drift": round(drift, 4),
                 "first_half_avg": round(first_half_avg, 4),
                 "second_half_avg": round(second_half_avg, 4),
                 "threshold": self.DRIFT_THRESHOLD},
            ],
            recommended_actions=[
                "Implement model retraining triggers",
                "Add data drift detection to world model",
                "Use active learning to update stale predictions",
            ],
        )

    def generate_report(self, system_state: dict[str, Any]) -> FailureAnalysisReport:
        """Generate comprehensive failure analysis report.
        
        Runs all failure detectors and aggregates results.
        """
        reports = [
            self.detect_belief_collapse(system_state),
            self.detect_contradiction_accumulation(system_state),
            self.detect_memory_corruption(system_state),
            self.detect_goal_oscillation(system_state),
            self.detect_planning_loops(system_state),
            self.detect_prediction_drift(system_state),
        ]

        total_failures = sum(1 for r in reports if r.detected)
        
        # Find most severe failure
        most_severe: FailureType | None = None
        max_severity = 0.0
        for r in reports:
            if r.detected and r.severity > max_severity:
                max_severity = r.severity
                most_severe = r.failure_type

        # Overall health: 1.0 = no failures, decreasing with failures
        health = max(0.0, 1.0 - sum(r.severity for r in reports if r.detected) / max(len(reports), 1))

        # Generate recommendations
        recommendations: list[str] = []
        for r in reports:
            if r.detected:
                recommendations.extend(r.recommended_actions[:2])  # Top 2 per failure

        system_name = system_state.get("name", system_state.get("system_name", "unknown"))

        return FailureAnalysisReport(
            system_name=system_name,
            failure_reports=reports,
            total_failures_detected=total_failures,
            most_severe_failure=most_severe,
            overall_health=round(health, 4),
            recommendations=recommendations,
        )
