"""
Benchmark Suite for ACOS Validation Lab v1.0.

Phase 1: Benchmarks that measure cognitive capabilities across:
- Memory: recall accuracy, long-term retention, retrieval quality, consolidation
- Planning: goal decomposition, multi-step planning, dependency handling, completion
- Reasoning: deductive, inductive, causal, counterfactual
- Learning: belief updates, error correction, adaptation speed, confidence calibration
- Prediction: future state, outcome estimation, risk forecasting

Each benchmark generates test cases, runs them against a system, and returns
BenchmarkResult with detailed scores.
"""

from __future__ import annotations

import time
from typing import Any, Protocol

from acos.validation.models import (
    BenchmarkCategory,
    BenchmarkMetric,
    BenchmarkResult,
    BenchmarkScore,
    BenchmarkSuiteResult,
    LearningTestCase,
    MemoryTestCase,
    PlanningTestCase,
    PredictionTestCase,
    ReasoningTestCase,
)
from acos.validation.test_generator import TestCaseGenerator


class SystemUnderTest(Protocol):
    """Protocol for any system being benchmarked."""
    name: str
    
    def process(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Process a query and return results."""
        ...
    
    def get_state(self) -> dict[str, Any]:
        """Get the current state of the system."""
        ...


class BenchmarkSuite:
    """Complete benchmark suite for evaluating cognitive systems.
    
    Usage::
    
        suite = BenchmarkSuite()
        result = suite.benchmark_recall_accuracy(system, test_cases)
        suite_result = suite.run_full_suite(system, n_cases=100)
    """

    def __init__(self, seed: int = 42) -> None:
        self._generator = TestCaseGenerator(seed=seed)

    # ─── Memory Benchmarks ─────────────────────────────────────────────────────

    def benchmark_recall_accuracy(
        self,
        system: SystemUnderTest,
        test_cases: list[MemoryTestCase],
    ) -> BenchmarkResult:
        """Measure how accurately the system recalls stored information.
        
        For each test case:
        1. Present the fact(s) to the system
        2. Query for recall
        3. Check if expected facts are in the response
        """
        start = time.monotonic()
        correct = 0
        total_retrieved = 0
        total_relevant = 0
        total_expected = 0
        
        for tc in test_cases:
            # Store information first
            store_context = {
                "action": "store",
                "facts": tc.expected_facts,
                "context": tc.context,
                "delay_steps": tc.delay_steps,
                "interference_items": tc.interference_items,
            }
            system.process(f"Remember: {'; '.join(tc.expected_facts)}", store_context)
            
            # Simulate delay/interference steps
            if tc.interference_items > 0:
                for j in range(tc.interference_items):
                    system.process(
                        f"Distractor item {j}: unrelated information",
                        {"action": "store", "interference": True},
                    )
            
            # Query for recall
            response = system.process(tc.query, {"action": "recall", "context": tc.context})
            
            # Evaluate: check if expected facts appear in the response
            retrieved_facts: list[str] = response.get("retrieved_facts", [])
            if isinstance(retrieved_facts, str):
                retrieved_facts = [retrieved_facts]
            
            response_text = response.get("response", "").lower()
            
            n_relevant = 0
            for fact in tc.expected_facts:
                total_expected += 1
                fact_lower = fact.lower()
                # Check if the fact or its key components appear
                if fact_lower in response_text or any(
                    comp in response_text for comp in fact_lower.split() if len(comp) > 3
                ):
                    n_relevant += 1
                    correct += 1
                if fact in retrieved_facts:
                    correct += 1
                    n_relevant += 1
            
            total_retrieved += len(retrieved_facts) + (1 if response_text else 0)
            total_relevant += n_relevant
        
        # Compute metrics
        n = len(test_cases)
        accuracy = correct / max(total_expected * 2, 1)  # *2 because we check both ways
        precision = total_relevant / max(total_retrieved, 1)
        recall = total_relevant / max(total_expected, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-10)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="recall_accuracy",
            category=BenchmarkCategory.MEMORY,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(accuracy, 6), sample_size=n),
                BenchmarkScore(metric=BenchmarkMetric.PRECISION, value=round(precision, 6), sample_size=n),
                BenchmarkScore(metric=BenchmarkMetric.RECALL, value=round(recall, 6), sample_size=n),
                BenchmarkScore(metric=BenchmarkMetric.F1_SCORE, value=round(f1, 6), sample_size=n),
            ],
            overall_score=round(f1, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    def benchmark_long_term_retention(
        self,
        system: SystemUnderTest,
        test_cases: list[MemoryTestCase],
    ) -> BenchmarkResult:
        """Measure how well the system retains information over time.
        
        Uses test cases with delay_steps > 0 to simulate passage of time.
        """
        start = time.monotonic()
        retention_scores: list[float] = []
        
        for tc in test_cases:
            if tc.delay_steps == 0:
                continue  # Skip non-retention cases
            
            # Store
            system.process(
                f"Remember: {'; '.join(tc.expected_facts)}",
                {"action": "store", "facts": tc.expected_facts},
            )
            
            # Simulate intervening operations
            for step in range(tc.delay_steps):
                system.process(
                    f"Process step {step}",
                    {"action": "intermediate", "step": step},
                )
            
            # Recall
            response = system.process(tc.query, {"action": "recall"})
            response_text = response.get("response", "").lower()
            
            # Compute retention score
            retained = 0
            for fact in tc.expected_facts:
                if fact.lower() in response_text:
                    retained += 1
            
            retention = retained / max(len(tc.expected_facts), 1)
            retention_scores.append(retention)
        
        n = len(retention_scores)
        avg_retention = sum(retention_scores) / max(n, 1)
        
        # Compute decay rate: retention decreases with delay
        high_delay_scores = [
            s for tc, s in zip(test_cases, retention_scores)
            if tc.delay_steps > 10
        ]
        low_delay_scores = [
            s for tc, s in zip(test_cases, retention_scores)
            if tc.delay_steps <= 10 and tc.delay_steps > 0
        ]
        
        avg_high = sum(high_delay_scores) / max(len(high_delay_scores), 1) if high_delay_scores else 0
        avg_low = sum(low_delay_scores) / max(len(low_delay_scores), 1) if low_delay_scores else 0
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="long_term_retention",
            category=BenchmarkCategory.MEMORY,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(avg_retention, 6), sample_size=n),
                BenchmarkScore(
                    metric=BenchmarkMetric.COMPLETION_RATE,
                    value=round(avg_high / max(avg_low, 1e-10), 6),
                    sample_size=n,
                ),
            ],
            overall_score=round(avg_retention, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    def benchmark_retrieval_quality(
        self,
        system: SystemUnderTest,
        test_cases: list[MemoryTestCase],
    ) -> BenchmarkResult:
        """Measure the quality of memory retrieval (relevance ranking)."""
        start = time.monotonic()
        quality_scores: list[float] = []
        
        for tc in test_cases:
            # Store and retrieve
            system.process(
                f"Remember: {'; '.join(tc.expected_facts)}",
                {"action": "store", "facts": tc.expected_facts, "context": tc.context},
            )
            
            response = system.process(tc.query, {"action": "retrieve", "context": tc.context})
            relevance = response.get("relevance_score", 0.5)
            quality_scores.append(float(relevance))
        
        n = len(quality_scores)
        avg_quality = sum(quality_scores) / max(n, 1)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="retrieval_quality",
            category=BenchmarkCategory.MEMORY,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(avg_quality, 6), sample_size=n),
            ],
            overall_score=round(avg_quality, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    def benchmark_knowledge_consolidation(
        self,
        system: SystemUnderTest,
        test_cases: list[MemoryTestCase],
    ) -> BenchmarkResult:
        """Measure how well the system consolidates episodic memories into knowledge."""
        start = time.monotonic()
        consolidation_scores: list[float] = []
        
        for tc in test_cases:
            # Store multiple related episodes
            for fact in tc.expected_facts:
                system.process(
                    f"Experience: {fact}",
                    {"action": "store_episodic", "context": tc.context},
                )
            
            # Trigger consolidation
            response = system.process(
                "Summarize what you know",
                {"action": "consolidate", "context": tc.context},
            )
            
            # Check if consolidated knowledge includes the expected facts
            response_text = response.get("response", "").lower()
            consolidated_count = sum(
                1 for fact in tc.expected_facts
                if fact.lower() in response_text
            )
            score = consolidated_count / max(len(tc.expected_facts), 1)
            consolidation_scores.append(score)
        
        n = len(consolidation_scores)
        avg_consolidation = sum(consolidation_scores) / max(n, 1)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="knowledge_consolidation",
            category=BenchmarkCategory.MEMORY,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(avg_consolidation, 6), sample_size=n),
                BenchmarkScore(metric=BenchmarkMetric.COMPLETION_RATE, value=round(avg_consolidation, 6), sample_size=n),
            ],
            overall_score=round(avg_consolidation, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    # ─── Planning Benchmarks ───────────────────────────────────────────────────

    def benchmark_goal_decomposition(
        self,
        system: SystemUnderTest,
        test_cases: list[PlanningTestCase],
    ) -> BenchmarkResult:
        """Measure how well the system decomposes goals into subgoals."""
        start = time.monotonic()
        decomposition_scores: list[float] = []
        
        for tc in test_cases:
            response = system.process(
                f"Decompose this goal: {tc.goal}",
                {"action": "plan", "expected_subgoals": tc.subgoals},
            )
            
            proposed = response.get("subgoals", [])
            if isinstance(proposed, str):
                proposed = [proposed]
            
            # Compute overlap with expected subgoals
            if not tc.subgoals:
                decomposition_scores.append(1.0)
                continue
            
            expected_lower = {s.lower() for s in tc.subgoals}
            proposed_lower = {s.lower() for s in proposed}
            
            # Semantic overlap (keyword matching)
            matches = 0
            for exp in expected_lower:
                exp_words = set(exp.split())
                for prop in proposed_lower:
                    prop_words = set(prop.split())
                    if exp_words & prop_words:  # Word overlap
                        matches += 1
                        break
            
            precision = matches / max(len(proposed), 1)
            recall = matches / max(len(expected_lower), 1)
            score = 2 * precision * recall / max(precision + recall, 1e-10)
            decomposition_scores.append(score)
        
        n = len(decomposition_scores)
        avg_score = sum(decomposition_scores) / max(n, 1)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="goal_decomposition",
            category=BenchmarkCategory.PLANNING,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(avg_score, 6), sample_size=n),
                BenchmarkScore(metric=BenchmarkMetric.F1_SCORE, value=round(avg_score, 6), sample_size=n),
            ],
            overall_score=round(avg_score, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    def benchmark_multi_step_planning(
        self,
        system: SystemUnderTest,
        test_cases: list[PlanningTestCase],
    ) -> BenchmarkResult:
        """Measure quality of multi-step plan generation."""
        start = time.monotonic()
        plan_scores: list[float] = []
        
        for tc in test_cases:
            response = system.process(
                f"Create a plan for: {tc.goal}",
                {"action": "plan", "constraints": tc.constraints},
            )
            
            steps = response.get("plan_steps", [])
            if isinstance(steps, str):
                steps = [steps]
            
            if not steps:
                plan_scores.append(0.0)
                continue
            
            # Score based on:
            # 1. Number of steps relative to optimal
            step_ratio = len(steps) / max(tc.optimal_steps, 1)
            step_score = 1.0 / max(step_ratio, 1.0 / step_ratio)  # Harmonic-ish
            step_score = min(1.0, step_score)
            
            # 2. Coverage of subgoals
            if tc.subgoals:
                covered = 0
                for subgoal in tc.subgoals:
                    subgoal_lower = subgoal.lower()
                    for step_text in steps:
                        if isinstance(step_text, str):
                            step_lower = step_text.lower()
                            overlap = set(subgoal_lower.split()) & set(step_lower.split())
                            if len(overlap) >= 2 or subgoal_lower in step_lower:
                                covered += 1
                                break
                coverage = covered / max(len(tc.subgoals), 1)
            else:
                coverage = 0.5
            
            score = 0.5 * step_score + 0.5 * coverage
            plan_scores.append(score)
        
        n = len(plan_scores)
        avg_score = sum(plan_scores) / max(n, 1)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="multi_step_planning",
            category=BenchmarkCategory.PLANNING,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(avg_score, 6), sample_size=n),
                BenchmarkScore(metric=BenchmarkMetric.COMPLETION_RATE, value=round(avg_score, 6), sample_size=n),
            ],
            overall_score=round(avg_score, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    def benchmark_dependency_handling(
        self,
        system: SystemUnderTest,
        test_cases: list[PlanningTestCase],
    ) -> BenchmarkResult:
        """Measure how well the system handles dependencies in plans."""
        start = time.monotonic()
        dep_scores: list[float] = []
        
        for tc in test_cases:
            if not tc.dependencies:
                continue
            
            response = system.process(
                f"Create a plan respecting dependencies for: {tc.goal}",
                {
                    "action": "plan",
                    "dependencies": tc.dependencies,
                    "subgoals": tc.subgoals,
                },
            )
            
            steps = response.get("plan_steps", [])
            if isinstance(steps, str):
                steps = [steps]
            
            # Check if dependencies are respected
            violations = 0
            step_positions: dict[str, int] = {}
            for idx, step in enumerate(steps):
                if isinstance(step, str):
                    step_lower = step.lower()
                    for sg in tc.subgoals:
                        if sg.lower() in step_lower or len(set(sg.lower().split()) & set(step_lower.split())) >= 2:
                            step_positions[sg.lower()] = idx
            
            for before, after in tc.dependencies:
                pos_before = step_positions.get(before.lower(), -1)
                pos_after = step_positions.get(after.lower(), -1)
                if pos_before >= 0 and pos_after >= 0 and pos_before > pos_after:
                    violations += 1
            
            total_deps = len(tc.dependencies)
            score = 1.0 - (violations / max(total_deps, 1))
            dep_scores.append(score)
        
        n = len(dep_scores)
        avg_score = sum(dep_scores) / max(n, 1) if dep_scores else 0.0
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="dependency_handling",
            category=BenchmarkCategory.PLANNING,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(avg_score, 6), sample_size=n),
            ],
            overall_score=round(avg_score, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    def benchmark_plan_completion_rate(
        self,
        system: SystemUnderTest,
        test_cases: list[PlanningTestCase],
    ) -> BenchmarkResult:
        """Measure the rate at which generated plans can be completed."""
        start = time.monotonic()
        completion_scores: list[float] = []
        
        for tc in test_cases:
            response = system.process(
                f"Complete this plan: {tc.goal}",
                {"action": "plan_complete", "subgoals": tc.subgoals},
            )
            
            completeness = response.get("completeness_score", 0.5)
            completion_scores.append(float(completeness))
        
        n = len(completion_scores)
        avg_completion = sum(completion_scores) / max(n, 1)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="plan_completion_rate",
            category=BenchmarkCategory.PLANNING,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.COMPLETION_RATE, value=round(avg_completion, 6), sample_size=n),
            ],
            overall_score=round(avg_completion, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    # ─── Reasoning Benchmarks ──────────────────────────────────────────────────

    def benchmark_deductive_reasoning(
        self,
        system: SystemUnderTest,
        test_cases: list[ReasoningTestCase],
    ) -> BenchmarkResult:
        """Measure deductive reasoning accuracy."""
        return self._benchmark_reasoning_type(system, test_cases, "deductive", "deductive_reasoning")

    def benchmark_inductive_reasoning(
        self,
        system: SystemUnderTest,
        test_cases: list[ReasoningTestCase],
    ) -> BenchmarkResult:
        """Measure inductive reasoning accuracy."""
        return self._benchmark_reasoning_type(system, test_cases, "inductive", "inductive_reasoning")

    def benchmark_causal_reasoning(
        self,
        system: SystemUnderTest,
        test_cases: list[ReasoningTestCase],
    ) -> BenchmarkResult:
        """Measure causal reasoning accuracy."""
        return self._benchmark_reasoning_type(system, test_cases, "causal", "causal_reasoning")

    def benchmark_counterfactual_reasoning(
        self,
        system: SystemUnderTest,
        test_cases: list[ReasoningTestCase],
    ) -> BenchmarkResult:
        """Measure counterfactual reasoning accuracy."""
        return self._benchmark_reasoning_type(system, test_cases, "counterfactual", "counterfactual_reasoning")

    def _benchmark_reasoning_type(
        self,
        system: SystemUnderTest,
        test_cases: list[ReasoningTestCase],
        reasoning_type: str,
        benchmark_name: str,
    ) -> BenchmarkResult:
        """Generic reasoning benchmark implementation."""
        start = time.monotonic()
        
        filtered = [tc for tc in test_cases if tc.reasoning_type == reasoning_type]
        if not filtered:
            filtered = test_cases  # Fall back to all if type doesn't match
        
        correct = 0
        total = 0
        confidence_scores: list[float] = []
        
        for tc in filtered:
            premises_str = "; ".join(tc.premises)
            prompt = f"Given: {premises_str}. {tc.question}"
            
            response = system.process(prompt, {
                "action": "reason",
                "reasoning_type": reasoning_type,
                "expected_answer": tc.correct_answer,
            })
            
            answer = response.get("answer", "").lower()
            confidence = float(response.get("confidence", 0.5))
            confidence_scores.append(confidence)
            
            correct_lower = tc.correct_answer.lower()
            
            # Check if the correct answer is contained in the response
            if correct_lower in answer:
                correct += 1
            else:
                # Check for keyword overlap
                correct_words = set(correct_lower.split())
                answer_words = set(answer.split())
                if correct_words & answer_words:
                    correct += 1
            
            total += 1
        
        accuracy = correct / max(total, 1)
        avg_confidence = sum(confidence_scores) / max(len(confidence_scores), 1)
        
        # Calibration: how well does confidence match accuracy
        calibration_error = abs(avg_confidence - accuracy)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name=benchmark_name,
            category=BenchmarkCategory.REASONING,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(accuracy, 6), sample_size=total),
                BenchmarkScore(metric=BenchmarkMetric.CALIBRATION_ERROR, value=round(calibration_error, 6), sample_size=total),
            ],
            overall_score=round(accuracy, 6),
            execution_time_ms=elapsed,
            test_case_count=total,
        )

    # ─── Learning Benchmarks ───────────────────────────────────────────────────

    def benchmark_belief_updates(
        self,
        system: SystemUnderTest,
        test_cases: list[LearningTestCase],
    ) -> BenchmarkResult:
        """Measure how accurately the system updates beliefs based on evidence."""
        start = time.monotonic()
        update_scores: list[float] = []
        
        for tc in test_cases:
            # Present initial belief
            system.process(
                f"Initial belief: {tc.initial_belief}",
                {"action": "set_belief", "belief": tc.initial_belief},
            )
            
            # Present evidence sequentially
            for evidence in tc.evidence_sequence:
                system.process(
                    f"Evidence: {evidence['observation']}",
                    {"action": "update_belief", "supports": evidence["supports"]},
                )
            
            # Check updated belief
            response = system.process(
                f"What is your current belief about: {tc.initial_belief}?",
                {"action": "query_belief"},
            )
            
            belief_confidence = float(response.get("confidence", 0.5))
            
            # Score based on how close the updated confidence is to expected
            error = abs(belief_confidence - tc.expected_confidence)
            score = 1.0 - error
            update_scores.append(max(0.0, score))
        
        n = len(update_scores)
        avg_score = sum(update_scores) / max(n, 1)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="belief_updates",
            category=BenchmarkCategory.LEARNING,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(avg_score, 6), sample_size=n),
            ],
            overall_score=round(avg_score, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    def benchmark_error_correction(
        self,
        system: SystemUnderTest,
        test_cases: list[LearningTestCase],
    ) -> BenchmarkResult:
        """Measure how well the system corrects errors in its beliefs."""
        start = time.monotonic()
        correction_scores: list[float] = []
        
        for tc in test_cases:
            # Set a potentially incorrect initial belief
            system.process(
                f"Initial belief: {tc.initial_belief}",
                {"action": "set_belief", "belief": tc.initial_belief},
            )
            
            # Present corrective evidence
            corrective_evidence = [
                e for e in tc.evidence_sequence if not e.get("supports", True)
            ]
            
            for evidence in corrective_evidence:
                system.process(
                    f"Correction: {evidence['observation']}",
                    {"action": "correct_belief", "supports": evidence["supports"]},
                )
            
            # Check if belief was corrected
            response = system.process(
                f"What is your belief about: {tc.initial_belief}?",
                {"action": "query_belief"},
            )
            
            correction_quality = float(response.get("correction_score", 0.5))
            correction_scores.append(correction_quality)
        
        n = len(correction_scores)
        avg_score = sum(correction_scores) / max(n, 1)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="error_correction",
            category=BenchmarkCategory.LEARNING,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(avg_score, 6), sample_size=n),
            ],
            overall_score=round(avg_score, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    def benchmark_adaptation_speed(
        self,
        system: SystemUnderTest,
        test_cases: list[LearningTestCase],
    ) -> BenchmarkResult:
        """Measure how quickly the system adapts to new information."""
        start = time.monotonic()
        adaptation_scores: list[float] = []
        
        for tc in test_cases:
            system.process(
                f"Initial belief: {tc.initial_belief}",
                {"action": "set_belief", "belief": tc.initial_belief},
            )
            
            # Track belief change over evidence sequence
            prev_confidence = 0.5
            total_shift = 0.0
            steps_to_converge = len(tc.evidence_sequence)
            
            for idx, evidence in enumerate(tc.evidence_sequence):
                response = system.process(
                    f"Evidence: {evidence['observation']}",
                    {"action": "update_belief", "supports": evidence["supports"]},
                )
                new_confidence = float(response.get("confidence", 0.5))
                shift = abs(new_confidence - prev_confidence)
                total_shift += shift
                prev_confidence = new_confidence
                
                # Check convergence
                if abs(new_confidence - tc.expected_confidence) < 0.1:
                    steps_to_converge = idx + 1
                    break
            
            # Adaptation speed: ratio of steps needed vs total available
            speed = steps_to_converge / max(len(tc.evidence_sequence), 1)
            # Invert: faster convergence = higher score
            speed_score = 1.0 - speed + 0.5  # Normalize to [0.5, 1.5] range
            speed_score = min(1.0, speed_score)
            
            adaptation_scores.append(speed_score)
        
        n = len(adaptation_scores)
        avg_score = sum(adaptation_scores) / max(n, 1)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="adaptation_speed",
            category=BenchmarkCategory.LEARNING,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(avg_score, 6), sample_size=n),
            ],
            overall_score=round(avg_score, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    def benchmark_confidence_calibration(
        self,
        system: SystemUnderTest,
        test_cases: list[LearningTestCase],
    ) -> BenchmarkResult:
        """Measure how well the system's confidence matches its accuracy (Brier score)."""
        start = time.monotonic()
        brier_scores: list[float] = []
        
        for tc in test_cases:
            system.process(
                f"Initial belief: {tc.initial_belief}",
                {"action": "set_belief", "belief": tc.initial_belief},
            )
            
            for evidence in tc.evidence_sequence:
                system.process(
                    f"Evidence: {evidence['observation']}",
                    {"action": "update_belief", "supports": evidence["supports"]},
                )
            
            response = system.process(
                f"How confident are you about: {tc.initial_belief}?",
                {"action": "query_confidence"},
            )
            
            predicted_prob = float(response.get("confidence", 0.5))
            actual_outcome = 1.0 if tc.expected_confidence > 0.5 else 0.0
            
            # Brier score: (predicted - actual)^2
            brier = (predicted_prob - actual_outcome) ** 2
            brier_scores.append(brier)
        
        n = len(brier_scores)
        avg_brier = sum(brier_scores) / max(n, 1)
        # Convert to calibration quality (1 - brier, normalized)
        calibration_quality = max(0.0, 1.0 - avg_brier)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="confidence_calibration",
            category=BenchmarkCategory.LEARNING,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.BRIER_SCORE, value=round(avg_brier, 6), sample_size=n),
                BenchmarkScore(metric=BenchmarkMetric.CALIBRATION_ERROR, value=round(avg_brier, 6), sample_size=n),
            ],
            overall_score=round(calibration_quality, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    # ─── Prediction Benchmarks ─────────────────────────────────────────────────

    def benchmark_future_state_prediction(
        self,
        system: SystemUnderTest,
        test_cases: list[PredictionTestCase],
    ) -> BenchmarkResult:
        """Measure accuracy of future state predictions."""
        start = time.monotonic()
        prediction_scores: list[float] = []
        
        for tc in test_cases:
            state_str = ", ".join(f"{k}={v}" for k, v in tc.initial_state.items())
            prompt = f"Scenario: {tc.scenario}. Current state: {state_str}. Action: {tc.action}. What happens next?"
            
            response = system.process(prompt, {
                "action": "predict",
                "initial_state": tc.initial_state,
                "action_taken": tc.action,
            })
            
            predicted_outcome = response.get("predicted_outcome", "").lower()
            predicted_prob = float(response.get("predicted_probability", 0.5))
            
            # Check if predicted outcome matches expected
            expected_lower = tc.expected_outcome.lower()
            outcome_match = 1.0 if expected_lower in predicted_outcome else 0.0
            
            # Check probability calibration
            prob_error = abs(predicted_prob - tc.expected_probability)
            
            score = 0.6 * outcome_match + 0.4 * (1.0 - prob_error)
            prediction_scores.append(score)
        
        n = len(prediction_scores)
        avg_score = sum(prediction_scores) / max(n, 1)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="future_state_prediction",
            category=BenchmarkCategory.PREDICTION,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(avg_score, 6), sample_size=n),
                BenchmarkScore(metric=BenchmarkMetric.CALIBRATION_ERROR, value=round(1.0 - avg_score, 6), sample_size=n),
            ],
            overall_score=round(avg_score, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    def benchmark_outcome_estimation(
        self,
        system: SystemUnderTest,
        test_cases: list[PredictionTestCase],
    ) -> BenchmarkResult:
        """Measure accuracy of outcome probability estimation."""
        start = time.monotonic()
        estimation_errors: list[float] = []
        
        for tc in test_cases:
            state_str = ", ".join(f"{k}={v}" for k, v in tc.initial_state.items())
            prompt = f"Estimate the probability: {tc.scenario}. State: {state_str}. Action: {tc.action}. Outcome: {tc.expected_outcome}"
            
            response = system.process(prompt, {
                "action": "estimate_probability",
                "initial_state": tc.initial_state,
            })
            
            estimated_prob = float(response.get("estimated_probability", 0.5))
            error = abs(estimated_prob - tc.expected_probability)
            estimation_errors.append(error)
        
        n = len(estimation_errors)
        avg_error = sum(estimation_errors) / max(n, 1)
        quality = max(0.0, 1.0 - avg_error)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="outcome_estimation",
            category=BenchmarkCategory.PREDICTION,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(quality, 6), sample_size=n),
                BenchmarkScore(metric=BenchmarkMetric.CALIBRATION_ERROR, value=round(avg_error, 6), sample_size=n),
            ],
            overall_score=round(quality, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    def benchmark_risk_forecasting(
        self,
        system: SystemUnderTest,
        test_cases: list[PredictionTestCase],
    ) -> BenchmarkResult:
        """Measure accuracy of risk forecasting."""
        start = time.monotonic()
        risk_scores: list[float] = []
        
        for tc in test_cases:
            state_str = ", ".join(f"{k}={v}" for k, v in tc.initial_state.items())
            prompt = f"Assess the risk: {tc.scenario}. State: {state_str}. Action: {tc.action}"
            
            response = system.process(prompt, {
                "action": "forecast_risk",
                "initial_state": tc.initial_state,
            })
            
            risk_level = float(response.get("risk_level", 0.5))
            # Higher expected probability of bad outcomes = higher risk
            expected_risk = 1.0 - tc.expected_probability
            
            error = abs(risk_level - expected_risk)
            score = 1.0 - error
            risk_scores.append(max(0.0, score))
        
        n = len(risk_scores)
        avg_score = sum(risk_scores) / max(n, 1)
        
        elapsed = (time.monotonic() - start) * 1000
        
        return BenchmarkResult(
            benchmark_name="risk_forecasting",
            category=BenchmarkCategory.PREDICTION,
            system_name=system.name,
            scores=[
                BenchmarkScore(metric=BenchmarkMetric.ACCURACY, value=round(avg_score, 6), sample_size=n),
            ],
            overall_score=round(avg_score, 6),
            execution_time_ms=elapsed,
            test_case_count=n,
        )

    # ─── Full Suite ────────────────────────────────────────────────────────────

    def run_full_suite(
        self,
        system: SystemUnderTest,
        n_cases: int = 100,
    ) -> BenchmarkSuiteResult:
        """Run the complete benchmark suite against a system.
        
        Runs all 19 benchmarks and aggregates results.
        """
        start = time.monotonic()
        results: list[BenchmarkResult] = []
        
        # Memory benchmarks
        memory_cases = self._generator.generate_memory_cases(n=n_cases)
        results.append(self.benchmark_recall_accuracy(system, memory_cases))
        results.append(self.benchmark_long_term_retention(system, memory_cases))
        results.append(self.benchmark_retrieval_quality(system, memory_cases))
        results.append(self.benchmark_knowledge_consolidation(system, memory_cases))
        
        # Planning benchmarks
        planning_cases = self._generator.generate_planning_cases(n=n_cases)
        results.append(self.benchmark_goal_decomposition(system, planning_cases))
        results.append(self.benchmark_multi_step_planning(system, planning_cases))
        results.append(self.benchmark_dependency_handling(system, planning_cases))
        results.append(self.benchmark_plan_completion_rate(system, planning_cases))
        
        # Reasoning benchmarks
        reasoning_cases = self._generator.generate_reasoning_cases(n=n_cases)
        results.append(self.benchmark_deductive_reasoning(system, reasoning_cases))
        results.append(self.benchmark_inductive_reasoning(system, reasoning_cases))
        results.append(self.benchmark_causal_reasoning(system, reasoning_cases))
        results.append(self.benchmark_counterfactual_reasoning(system, reasoning_cases))
        
        # Learning benchmarks
        learning_cases = self._generator.generate_learning_cases(n=n_cases)
        results.append(self.benchmark_belief_updates(system, learning_cases))
        results.append(self.benchmark_error_correction(system, learning_cases))
        results.append(self.benchmark_adaptation_speed(system, learning_cases))
        results.append(self.benchmark_confidence_calibration(system, learning_cases))
        
        # Prediction benchmarks
        prediction_cases = self._generator.generate_prediction_cases(n=n_cases)
        results.append(self.benchmark_future_state_prediction(system, prediction_cases))
        results.append(self.benchmark_outcome_estimation(system, prediction_cases))
        results.append(self.benchmark_risk_forecasting(system, prediction_cases))
        
        # Compute category scores
        category_scores: dict[str, list[float]] = {}
        for r in results:
            category_scores.setdefault(r.category.value, []).append(r.overall_score)
        
        category_avgs = {
            cat: round(sum(scores) / len(scores), 6)
            for cat, scores in category_scores.items()
        }
        
        overall_score = sum(r.overall_score for r in results) / max(len(results), 1)
        total_time = (time.monotonic() - start) * 1000
        total_cases = sum(r.test_case_count for r in results)
        
        return BenchmarkSuiteResult(
            system_name=system.name,
            results=results,
            overall_score=round(overall_score, 6),
            category_scores=category_avgs,
            total_execution_time_ms=total_time,
            total_test_cases=total_cases,
        )
