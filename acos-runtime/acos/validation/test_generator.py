"""
Test Case Generator for ACOS Validation Lab v1.0.

Generates deterministic, reproducible test cases for all benchmark categories:
- Memory: recall, retention, retrieval, consolidation
- Planning: decomposition, multi-step, dependencies, completion
- Reasoning: deductive, inductive, causal, counterfactual
- Learning: belief updates, error correction, adaptation, calibration
- Prediction: future state, outcome estimation, risk forecasting
"""

from __future__ import annotations

import random
from typing import Any

from acos.validation.models import (
    LearningTestCase,
    MemoryTestCase,
    PlanningTestCase,
    PredictionTestCase,
    ReasoningTestCase,
)


# ─── Memory Domain Data ────────────────────────────────────────────────────────

MEMORY_FACTS: list[dict[str, str]] = [
    {"subject": "Einstein", "attribute": "developed", "object": "theory of relativity"},
    {"subject": "Darwin", "attribute": "proposed", "object": "theory of evolution"},
    {"subject": "Curie", "attribute": "discovered", "object": "radium and polonium"},
    {"subject": "Newton", "attribute": "formulated", "object": "laws of motion"},
    {"subject": "Tesla", "attribute": "invented", "object": "alternating current system"},
    {"subject": "Planck", "attribute": "originated", "object": "quantum theory"},
    {"subject": "Bohr", "attribute": "developed", "object": "atomic model"},
    {"subject": "Feynman", "attribute": "contributed to", "object": "quantum electrodynamics"},
    {"subject": "Hawking", "attribute": "theorized", "object": "black hole radiation"},
    {"subject": "Turing", "attribute": "created", "object": "Turing machine concept"},
    {"subject": "Shannon", "attribute": "founded", "object": "information theory"},
    {"subject": "Von Neumann", "attribute": "designed", "object": "stored-program architecture"},
    {"subject": "Lovelace", "attribute": "wrote", "object": "first computer algorithm"},
    {"subject": "Hopper", "attribute": "developed", "object": "first compiler"},
    {"subject": "Knuth", "attribute": "wrote", "object": "The Art of Computer Programming"},
    {"subject": "Dijkstra", "attribute": "created", "object": "shortest path algorithm"},
    {"subject": "Minsky", "attribute": "co-founded", "object": "MIT AI Lab"},
    {"subject": "McCarthy", "attribute": "invented", "object": "Lisp programming language"},
    {"subject": "Backus", "attribute": "developed", "object": "FORTRAN compiler"},
    {"subject": "Berners-Lee", "attribute": "invented", "object": "World Wide Web"},
    {"subject": "Ritchie", "attribute": "created", "object": "C programming language"},
    {"subject": "Thompson", "attribute": "created", "object": "Unix operating system"},
    {"subject": "Stallman", "attribute": "launched", "object": "GNU Project"},
    {"subject": "Torvalds", "attribute": "created", "object": "Linux kernel"},
    {"subject": "Engelbart", "attribute": "invented", "object": "computer mouse"},
]

MEMORY_CONTEXTS: list[str] = [
    "scientific discoveries", "computer science pioneers", "physics breakthroughs",
    "mathematics fundamentals", "software engineering", "artificial intelligence",
    "quantum mechanics", "evolutionary biology", "electrical engineering",
    "information technology", "programming languages", "operating systems",
]


# ─── Planning Domain Data ──────────────────────────────────────────────────────

PLANNING_SCENARIOS: list[dict[str, Any]] = [
    {
        "goal": "Deploy a web application to production",
        "subgoals": ["Write code", "Write tests", "Set up CI/CD", "Configure server", "Deploy"],
        "dependencies": [("Write code", "Write tests"), ("Write tests", "Set up CI/CD"), ("Set up CI/CD", "Deploy")],
        "optimal_steps": 5,
    },
    {
        "goal": "Conduct a research study",
        "subgoals": ["Define hypothesis", "Design methodology", "Collect data", "Analyze results", "Write paper", "Submit for review"],
        "dependencies": [("Define hypothesis", "Design methodology"), ("Design methodology", "Collect data"), ("Collect data", "Analyze results"), ("Analyze results", "Write paper"), ("Write paper", "Submit for review")],
        "optimal_steps": 6,
    },
    {
        "goal": "Build a machine learning model",
        "subgoals": ["Gather data", "Clean data", "Feature engineering", "Train model", "Evaluate model", "Deploy model"],
        "dependencies": [("Gather data", "Clean data"), ("Clean data", "Feature engineering"), ("Feature engineering", "Train model"), ("Train model", "Evaluate model"), ("Evaluate model", "Deploy model")],
        "optimal_steps": 6,
    },
    {
        "goal": "Organize a conference",
        "subgoals": ["Set date and venue", "Create budget", "Invite speakers", "Open registration", "Arrange catering", "Set up AV equipment"],
        "dependencies": [("Set date and venue", "Create budget"), ("Set date and venue", "Invite speakers"), ("Create budget", "Arrange catering"), ("Invite speakers", "Open registration")],
        "optimal_steps": 6,
    },
    {
        "goal": "Refactor a legacy codebase",
        "subgoals": ["Analyze current architecture", "Write characterization tests", "Identify refactor targets", "Refactor modules", "Run integration tests", "Update documentation"],
        "dependencies": [("Analyze current architecture", "Identify refactor targets"), ("Analyze current architecture", "Write characterization tests"), ("Write characterization tests", "Refactor modules"), ("Refactor modules", "Run integration tests"), ("Run integration tests", "Update documentation")],
        "optimal_steps": 6,
    },
    {
        "goal": "Launch a startup product",
        "subgoals": ["Validate market", "Build MVP", "Get beta users", "Iterate on feedback", "Scale infrastructure", "Launch publicly"],
        "dependencies": [("Validate market", "Build MVP"), ("Build MVP", "Get beta users"), ("Get beta users", "Iterate on feedback"), ("Iterate on feedback", "Scale infrastructure"), ("Scale infrastructure", "Launch publicly")],
        "optimal_steps": 6,
    },
    {
        "goal": "Write a technical book",
        "subgoals": ["Outline chapters", "Write first draft", "Technical review", "Revise draft", "Copy editing", "Publish"],
        "dependencies": [("Outline chapters", "Write first draft"), ("Write first draft", "Technical review"), ("Technical review", "Revise draft"), ("Revise draft", "Copy editing"), ("Copy editing", "Publish")],
        "optimal_steps": 6,
    },
    {
        "goal": "Set up a data pipeline",
        "subgoals": ["Define data sources", "Design schema", "Build ETL process", "Set up scheduling", "Add monitoring", "Document pipeline"],
        "dependencies": [("Define data sources", "Design schema"), ("Design schema", "Build ETL process"), ("Build ETL process", "Set up scheduling"), ("Set up scheduling", "Add monitoring")],
        "optimal_steps": 6,
    },
]


# ─── Reasoning Domain Data ─────────────────────────────────────────────────────

DEDUCTIVE_PREMISES: list[dict[str, Any]] = [
    {
        "premises": ["All mammals are warm-blooded", "Whales are mammals"],
        "question": "Are whales warm-blooded?",
        "answer": "yes",
        "distractors": ["no", "unknown", "partially"],
    },
    {
        "premises": ["If it rains, the ground gets wet", "It is raining"],
        "question": "Is the ground wet?",
        "answer": "yes",
        "distractors": ["no", "maybe", "only if there is no roof"],
    },
    {
        "premises": ["All prime numbers greater than 2 are odd", "7 is a prime number greater than 2"],
        "question": "Is 7 odd?",
        "answer": "yes",
        "distractors": ["no", "unknown", "it depends"],
    },
    {
        "premises": ["No reptiles are mammals", "Snakes are reptiles"],
        "question": "Are snakes mammals?",
        "answer": "no",
        "distractors": ["yes", "sometimes", "unknown"],
    },
    {
        "premises": ["If a system has redundant components, it is fault-tolerant", "System X has redundant components"],
        "question": "Is System X fault-tolerant?",
        "answer": "yes",
        "distractors": ["no", "not necessarily", "depends on the type of fault"],
    },
]

INDUCTIVE_PREMISES: list[dict[str, Any]] = [
    {
        "premises": ["Swan 1 is white", "Swan 2 is white", "Swan 3 is white", "Swan 4 is white"],
        "question": "What color is the next swan likely to be?",
        "answer": "white",
        "distractors": ["black", "blue", "unknown"],
    },
    {
        "premises": ["Server A crashed after memory exceeded 90%", "Server B crashed after memory exceeded 90%", "Server C crashed after memory exceeded 90%"],
        "question": "What will happen when Server D's memory exceeds 90%?",
        "answer": "it will likely crash",
        "distractors": ["nothing will happen", "performance will improve", "memory will free itself"],
    },
    {
        "premises": ["Test suite passed after fix #1", "Test suite passed after fix #2", "Test suite passed after fix #3"],
        "question": "Will the test suite pass after fix #4?",
        "answer": "likely yes",
        "distractors": ["likely no", "impossible to know", "definitely no"],
    },
]

CAUSAL_PREMISES: list[dict[str, Any]] = [
    {
        "premises": ["Increasing temperature causes metal to expand", "The temperature of the bridge increased by 30 degrees"],
        "question": "What happened to the bridge?",
        "answer": "it expanded",
        "distractors": ["it contracted", "nothing happened", "it melted"],
    },
    {
        "premises": ["Removing the database index causes queries to slow down", "The DBA removed the primary index"],
        "question": "What happened to query performance?",
        "answer": "queries slowed down",
        "distractors": ["queries sped up", "no change", "database crashed"],
    },
    {
        "premises": ["Adding more training data reduces overfitting", "The team added 10x more training data"],
        "question": "What happened to overfitting?",
        "answer": "overfitting decreased",
        "distractors": ["overfitting increased", "no change", "model became underfit"],
    },
]

COUNTERFACTUAL_PREMISES: list[dict[str, Any]] = [
    {
        "premises": ["The deployment failed because the config file was missing", "The config file was not added to the Docker image"],
        "question": "What would have happened if the config file had been added?",
        "answer": "the deployment would have succeeded",
        "distractors": ["the deployment would still fail for another reason", "nothing would change", "the system would crash"],
    },
    {
        "premises": ["The project was delayed because the key developer left", "The developer left due to burnout"],
        "question": "What would have happened if the developer had not burned out?",
        "answer": "the project would likely have been on time",
        "distractors": ["the project would still be delayed", "the developer would have left anyway", "the project would be faster"],
    },
]


# ─── Learning Domain Data ──────────────────────────────────────────────────────

LEARNING_SCENARIOS: list[dict[str, Any]] = [
    {
        "initial_belief": "Service X is reliable",
        "evidence_sequence": [
            {"observation": "Service X responded in 50ms", "supports": True, "confidence_impact": 0.1},
            {"observation": "Service X had a timeout", "supports": False, "confidence_impact": -0.3},
            {"observation": "Service X recovered quickly", "supports": True, "confidence_impact": 0.15},
            {"observation": "Service X had another timeout", "supports": False, "confidence_impact": -0.25},
        ],
        "expected_belief": "Service X is somewhat unreliable",
        "expected_confidence": 0.35,
    },
    {
        "initial_belief": "Algorithm A is faster than Algorithm B",
        "evidence_sequence": [
            {"observation": "A completed in 100ms, B in 150ms", "supports": True, "confidence_impact": 0.2},
            {"observation": "A completed in 120ms, B in 110ms", "supports": False, "confidence_impact": -0.2},
            {"observation": "A completed in 90ms, B in 200ms", "supports": True, "confidence_impact": 0.15},
            {"observation": "A completed in 110ms, B in 105ms", "supports": False, "confidence_impact": -0.15},
            {"observation": "A completed in 80ms, B in 180ms", "supports": True, "confidence_impact": 0.2},
        ],
        "expected_belief": "Algorithm A is generally faster but not always",
        "expected_confidence": 0.65,
    },
    {
        "initial_belief": "The new feature will increase user engagement",
        "evidence_sequence": [
            {"observation": "User testing showed 20% more clicks", "supports": True, "confidence_impact": 0.25},
            {"observation": "A/B test showed no significant difference", "supports": False, "confidence_impact": -0.3},
            {"observation": "Power users reported improved workflow", "supports": True, "confidence_impact": 0.1},
        ],
        "expected_belief": "The feature may increase engagement for some users",
        "expected_confidence": 0.45,
    },
]


# ─── Prediction Domain Data ────────────────────────────────────────────────────

PREDICTION_SCENARIOS: list[dict[str, Any]] = [
    {
        "scenario": "Web server under increasing load",
        "initial_state": {"current_rps": 100, "max_capacity": 500, "latency_ms": 50},
        "action": "increase load to 400 rps",
        "expected_outcome": "latency increases moderately",
        "expected_probability": 0.8,
    },
    {
        "scenario": "Database with growing dataset",
        "initial_state": {"rows": 1000000, "query_time_ms": 10, "index_coverage": 0.9},
        "action": "add 5000000 more rows without new indexes",
        "expected_outcome": "query time increases significantly",
        "expected_probability": 0.9,
    },
    {
        "scenario": "ML model in production",
        "initial_state": {"accuracy": 0.95, "data_drift_score": 0.05, "training_data_age_days": 30},
        "action": "continue without retraining for 90 more days",
        "expected_outcome": "accuracy decreases due to data drift",
        "expected_probability": 0.7,
    },
    {
        "scenario": "Microservice with cascading dependencies",
        "initial_state": {"service_health": 0.99, "dependency_count": 5, "circuit_breakers_active": 0},
        "action": "one dependency starts failing 50% of requests",
        "expected_outcome": "service degrades, circuit breakers activate",
        "expected_probability": 0.85,
    },
    {
        "scenario": "Memory-constrained application",
        "initial_state": {"memory_usage_pct": 70, "gc_frequency_per_min": 2, "heap_size_mb": 512},
        "action": "increase concurrent users by 3x",
        "expected_outcome": "GC frequency increases, potential OOM",
        "expected_probability": 0.75,
    },
]


class TestCaseGenerator:
    """Generate test cases for cognitive benchmarks.
    
    All generators use a seeded random number generator for reproducibility.
    
    Usage::
    
        gen = TestCaseGenerator(seed=42)
        memory_cases = gen.generate_memory_cases(n=100)
        planning_cases = gen.generate_planning_cases(n=100)
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    def generate_memory_cases(self, n: int = 1000) -> list[MemoryTestCase]:
        """Generate memory benchmark test cases.
        
        Test cases span:
        - Simple recall (given context, recall a fact)
        - Long-term retention (facts with delay steps)
        - Interfered recall (facts with distractors)
        - Complex retrieval (multi-fact queries)
        """
        cases: list[MemoryTestCase] = []
        for i in range(n):
            difficulty = self._rng.uniform(0.1, 1.0)
            
            # Select a random fact
            fact = self._rng.choice(MEMORY_FACTS)
            context = self._rng.choice(MEMORY_CONTEXTS)
            
            # Scale complexity with difficulty
            n_related_facts = min(int(difficulty * 5) + 1, len(MEMORY_FACTS))
            related_facts = self._rng.sample(MEMORY_FACTS, min(n_related_facts, len(MEMORY_FACTS)))
            expected_facts = [f"{f['subject']} {f['attribute']} {f['object']}" for f in related_facts]
            
            delay_steps = int(difficulty * 20) if difficulty > 0.5 else 0
            interference_items = int(difficulty * 10) if difficulty > 0.3 else 0
            
            query_types = [
                f"What did {fact['subject']} {fact['attribute']}?",
                f"Who {fact['attribute']} {fact['object']}?",
                f"Tell me about {context}",
            ]
            query = self._rng.choice(query_types)
            
            cases.append(MemoryTestCase(
                query=query,
                expected_facts=expected_facts[:max(1, int(difficulty * 3))],
                context=context,
                difficulty=round(difficulty, 3),
                delay_steps=delay_steps,
                interference_items=interference_items,
                metadata={
                    "source_fact": fact,
                    "related_count": n_related_facts,
                },
            ))
        return cases

    def generate_planning_cases(self, n: int = 1000) -> list[PlanningTestCase]:
        """Generate planning benchmark test cases.
        
        Test cases include:
        - Goal decomposition (break goals into subgoals)
        - Multi-step planning (ordered sequences)
        - Dependency handling (precedence constraints)
        - Plan completion (full plans from start to end)
        """
        cases: list[PlanningTestCase] = []
        for i in range(n):
            difficulty = self._rng.uniform(0.1, 1.0)
            
            # Select a base scenario and modify based on difficulty
            scenario = self._rng.choice(PLANNING_SCENARIOS)
            
            # For harder cases, add more subgoals and dependencies
            subgoals = list(scenario["subgoals"])
            dependencies = list(scenario["dependencies"])
            
            if difficulty > 0.6:
                extra_subgoals = [
                    "Risk assessment", "Quality review", "Stakeholder approval",
                    "Documentation", "Performance testing", "Security audit",
                    "Rollback planning", "Monitoring setup",
                ]
                n_extra = int((difficulty - 0.6) * 10)
                for _ in range(n_extra):
                    extra = self._rng.choice(extra_subgoals)
                    subgoals.append(f"{extra} ({scenario['goal'][:20]})")
                    # Add a dependency from a random earlier subgoal
                    if len(subgoals) > 1:
                        dep_from = self._rng.choice(subgoals[:-1])
                        dependencies.append((dep_from, subgoals[-1]))
            
            # Shuffle subgoals but keep dependencies valid
            # (the system needs to figure out ordering)
            
            # Add constraints for harder cases
            constraints: list[str] = []
            if difficulty > 0.4:
                constraints.append(f"Budget limited to ${int(1000 * (1 - difficulty) + 100)}")
            if difficulty > 0.7:
                constraints.append("Must complete within 2 weeks")
            if difficulty > 0.9:
                constraints.append("Team of 2 people only")
            
            cases.append(PlanningTestCase(
                goal=scenario["goal"] + (f" (variant {i})" if i > 0 else ""),
                subgoals=subgoals,
                dependencies=dependencies,
                constraints=constraints,
                optimal_steps=scenario["optimal_steps"] + len(subgoals) - len(scenario["subgoals"]),
                difficulty=round(difficulty, 3),
                metadata={"base_scenario": scenario["goal"]},
            ))
        return cases

    def generate_reasoning_cases(self, n: int = 1000) -> list[ReasoningTestCase]:
        """Generate reasoning benchmark test cases.
        
        Distributes across reasoning types:
        - Deductive (logic from general to specific)
        - Inductive (generalization from examples)
        - Causal (cause and effect)
        - Counterfactual (what-if reasoning)
        """
        cases: list[ReasoningTestCase] = []
        
        # Allocate proportionally
        n_deductive = n // 4
        n_inductive = n // 4
        n_causal = n // 4
        n_counterfactual = n - n_deductive - n_inductive - n_causal
        
        # Deductive
        for i in range(n_deductive):
            template = self._rng.choice(DEDUCTIVE_PREMISES)
            difficulty = self._rng.uniform(0.1, 1.0)
            cases.append(ReasoningTestCase(
                premises=template["premises"],
                question=template["question"],
                correct_answer=template["answer"],
                reasoning_type="deductive",
                difficulty=round(difficulty, 3),
                distractors=template["distractors"],
                metadata={"template_idx": DEDUCTIVE_PREMISES.index(template)},
            ))
        
        # Inductive
        for i in range(n_inductive):
            template = self._rng.choice(INDUCTIVE_PREMISES)
            difficulty = self._rng.uniform(0.3, 1.0)
            cases.append(ReasoningTestCase(
                premises=template["premises"],
                question=template["question"],
                correct_answer=template["answer"],
                reasoning_type="inductive",
                difficulty=round(difficulty, 3),
                distractors=template["distractors"],
                metadata={"template_idx": INDUCTIVE_PREMISES.index(template)},
            ))
        
        # Causal
        for i in range(n_causal):
            template = self._rng.choice(CAUSAL_PREMISES)
            difficulty = self._rng.uniform(0.2, 1.0)
            cases.append(ReasoningTestCase(
                premises=template["premises"],
                question=template["question"],
                correct_answer=template["answer"],
                reasoning_type="causal",
                difficulty=round(difficulty, 3),
                distractors=template["distractors"],
                metadata={"template_idx": CAUSAL_PREMISES.index(template)},
            ))
        
        # Counterfactual
        for i in range(n_counterfactual):
            template = self._rng.choice(COUNTERFACTUAL_PREMISES)
            difficulty = self._rng.uniform(0.4, 1.0)
            cases.append(ReasoningTestCase(
                premises=template["premises"],
                question=template["question"],
                correct_answer=template["answer"],
                reasoning_type="counterfactual",
                difficulty=round(difficulty, 3),
                distractors=template["distractors"],
                metadata={"template_idx": COUNTERFACTUAL_PREMISES.index(template)},
            ))
        
        # Shuffle to mix reasoning types
        self._rng.shuffle(cases)
        return cases

    def generate_learning_cases(self, n: int = 1000) -> list[LearningTestCase]:
        """Generate learning benchmark test cases.
        
        Tests:
        - Belief updates (updating confidence based on evidence)
        - Error correction (fixing wrong beliefs)
        - Adaptation speed (how quickly beliefs converge)
        - Confidence calibration (matching confidence to accuracy)
        """
        cases: list[LearningTestCase] = []
        for i in range(n):
            difficulty = self._rng.uniform(0.1, 1.0)
            scenario = self._rng.choice(LEARNING_SCENARIOS)
            
            # Vary evidence sequences by difficulty
            evidence = list(scenario["evidence_sequence"])
            if difficulty > 0.5:
                # Add contradictory evidence for harder cases
                extra_evidence = [
                    {"observation": "New contradictory data point observed", "supports": False, "confidence_impact": -0.2},
                    {"observation": "Partial confirmation from alternative source", "supports": True, "confidence_impact": 0.1},
                    {"observation": "Outlier event occurred", "supports": False, "confidence_impact": -0.15},
                ]
                n_extra = int((difficulty - 0.5) * 6)
                for _ in range(n_extra):
                    evidence.append(self._rng.choice(extra_evidence))
            
            cases.append(LearningTestCase(
                initial_belief=scenario["initial_belief"],
                evidence_sequence=evidence,
                expected_belief=scenario["expected_belief"],
                expected_confidence=round(
                    scenario["expected_confidence"] + self._rng.uniform(-0.1, 0.1),
                    3,
                ),
                difficulty=round(difficulty, 3),
                metadata={"scenario_type": "belief_update"},
            ))
        return cases

    def generate_prediction_cases(self, n: int = 1000) -> list[PredictionTestCase]:
        """Generate prediction benchmark test cases.
        
        Tests:
        - Future state prediction (what will happen next)
        - Outcome estimation (probability of outcomes)
        - Risk forecasting (identifying potential failures)
        """
        cases: list[PredictionTestCase] = []
        for i in range(n):
            difficulty = self._rng.uniform(0.1, 1.0)
            scenario = self._rng.choice(PREDICTION_SCENARIOS)
            
            # Vary probability expectations by difficulty
            expected_prob = scenario["expected_probability"]
            if difficulty > 0.7:
                expected_prob = round(expected_prob - self._rng.uniform(0, 0.2), 3)
            expected_prob = max(0.1, min(0.95, expected_prob))
            
            # Vary time horizon by difficulty
            time_horizon = scenario.get("time_horizon", 1.0) * (1 + difficulty)
            
            cases.append(PredictionTestCase(
                scenario=scenario["scenario"],
                initial_state=scenario["initial_state"],
                action=scenario["action"],
                expected_outcome=scenario["expected_outcome"],
                expected_probability=round(expected_prob, 3),
                time_horizon=round(time_horizon, 2),
                difficulty=round(difficulty, 3),
                metadata={"base_scenario": scenario["scenario"]},
            ))
        return cases
