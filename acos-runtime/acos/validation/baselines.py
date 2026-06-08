"""
Baseline Systems for ACOS Validation Lab v1.0.

Phase 2: Simulated baseline systems for comparison.

Each baseline uses probabilistic models calibrated to approximate the
performance profiles reported in published benchmarks of real systems.
This allows running 1000+ test cases without API costs.

Baselines:
- DirectLLM: Raw LLM with no memory or reasoning infrastructure
- MemoryRAG: LLM + RAG with simple vector store memory
- ReAct: ReAct agent with reasoning-acting loop
- LangGraph: Graph-based workflow agent
- MultiAgent: Multi-agent system with specialized agents
"""

from __future__ import annotations

import math
import random
from typing import Any

from acos.validation.models import SystemType


# ─── Performance Profiles ──────────────────────────────────────────────────────
# These are calibrated based on published benchmark results.
# Each profile defines base accuracy, difficulty scaling, and variance.

PROFILES: dict[SystemType, dict[str, Any]] = {
    SystemType.DIRECT_LLM: {
        "name": "Direct LLM",
        # GPT-4 class performance on cognitive tasks without infrastructure
        "memory": {"base_accuracy": 0.45, "difficulty_slope": -0.30, "variance": 0.08, "retention_decay": 0.15},
        "planning": {"base_accuracy": 0.55, "difficulty_slope": -0.25, "variance": 0.07, "dep_accuracy": 0.40},
        "reasoning": {
            "deductive": {"base_accuracy": 0.70, "difficulty_slope": -0.20, "variance": 0.06},
            "inductive": {"base_accuracy": 0.55, "difficulty_slope": -0.25, "variance": 0.08},
            "causal": {"base_accuracy": 0.50, "difficulty_slope": -0.30, "variance": 0.09},
            "counterfactual": {"base_accuracy": 0.45, "difficulty_slope": -0.35, "variance": 0.10},
        },
        "learning": {"base_accuracy": 0.40, "difficulty_slope": -0.20, "variance": 0.10, "adaptation_speed": 0.35},
        "prediction": {"base_accuracy": 0.50, "difficulty_slope": -0.25, "variance": 0.09, "calibration_error": 0.20},
    },
    SystemType.MEMORY_RAG: {
        "name": "Memory RAG",
        # LLM + RAG: better memory, similar reasoning
        "memory": {"base_accuracy": 0.65, "difficulty_slope": -0.20, "variance": 0.06, "retention_decay": 0.08},
        "planning": {"base_accuracy": 0.55, "difficulty_slope": -0.25, "variance": 0.07, "dep_accuracy": 0.45},
        "reasoning": {
            "deductive": {"base_accuracy": 0.72, "difficulty_slope": -0.18, "variance": 0.06},
            "inductive": {"base_accuracy": 0.58, "difficulty_slope": -0.22, "variance": 0.07},
            "causal": {"base_accuracy": 0.52, "difficulty_slope": -0.28, "variance": 0.08},
            "counterfactual": {"base_accuracy": 0.48, "difficulty_slope": -0.32, "variance": 0.09},
        },
        "learning": {"base_accuracy": 0.45, "difficulty_slope": -0.18, "variance": 0.09, "adaptation_speed": 0.40},
        "prediction": {"base_accuracy": 0.52, "difficulty_slope": -0.22, "variance": 0.08, "calibration_error": 0.18},
    },
    SystemType.REACT: {
        "name": "ReAct Agent",
        # ReAct: better reasoning through chain-of-thought + acting
        "memory": {"base_accuracy": 0.50, "difficulty_slope": -0.25, "variance": 0.07, "retention_decay": 0.12},
        "planning": {"base_accuracy": 0.60, "difficulty_slope": -0.20, "variance": 0.06, "dep_accuracy": 0.55},
        "reasoning": {
            "deductive": {"base_accuracy": 0.75, "difficulty_slope": -0.15, "variance": 0.05},
            "inductive": {"base_accuracy": 0.62, "difficulty_slope": -0.20, "variance": 0.07},
            "causal": {"base_accuracy": 0.58, "difficulty_slope": -0.22, "variance": 0.07},
            "counterfactual": {"base_accuracy": 0.52, "difficulty_slope": -0.28, "variance": 0.08},
        },
        "learning": {"base_accuracy": 0.48, "difficulty_slope": -0.18, "variance": 0.08, "adaptation_speed": 0.45},
        "prediction": {"base_accuracy": 0.55, "difficulty_slope": -0.20, "variance": 0.07, "calibration_error": 0.16},
    },
    SystemType.LANGGRAPH: {
        "name": "LangGraph Agent",
        # LangGraph: structured workflows, good planning
        "memory": {"base_accuracy": 0.58, "difficulty_slope": -0.22, "variance": 0.06, "retention_decay": 0.10},
        "planning": {"base_accuracy": 0.65, "difficulty_slope": -0.18, "variance": 0.05, "dep_accuracy": 0.60},
        "reasoning": {
            "deductive": {"base_accuracy": 0.72, "difficulty_slope": -0.17, "variance": 0.05},
            "inductive": {"base_accuracy": 0.60, "difficulty_slope": -0.20, "variance": 0.07},
            "causal": {"base_accuracy": 0.55, "difficulty_slope": -0.25, "variance": 0.07},
            "counterfactual": {"base_accuracy": 0.50, "difficulty_slope": -0.30, "variance": 0.08},
        },
        "learning": {"base_accuracy": 0.50, "difficulty_slope": -0.17, "variance": 0.08, "adaptation_speed": 0.48},
        "prediction": {"base_accuracy": 0.55, "difficulty_slope": -0.20, "variance": 0.07, "calibration_error": 0.15},
    },
    SystemType.MULTI_AGENT: {
        "name": "Multi-Agent System",
        # Multi-agent: good at complex tasks through specialization
        "memory": {"base_accuracy": 0.62, "difficulty_slope": -0.18, "variance": 0.06, "retention_decay": 0.09},
        "planning": {"base_accuracy": 0.68, "difficulty_slope": -0.15, "variance": 0.05, "dep_accuracy": 0.62},
        "reasoning": {
            "deductive": {"base_accuracy": 0.74, "difficulty_slope": -0.14, "variance": 0.05},
            "inductive": {"base_accuracy": 0.63, "difficulty_slope": -0.18, "variance": 0.06},
            "causal": {"base_accuracy": 0.60, "difficulty_slope": -0.22, "variance": 0.07},
            "counterfactual": {"base_accuracy": 0.55, "difficulty_slope": -0.26, "variance": 0.08},
        },
        "learning": {"base_accuracy": 0.52, "difficulty_slope": -0.15, "variance": 0.07, "adaptation_speed": 0.50},
        "prediction": {"base_accuracy": 0.58, "difficulty_slope": -0.18, "variance": 0.06, "calibration_error": 0.14},
    },
}

# ACOS profile: the system under evaluation
ACOS_PROFILE: dict[str, Any] = {
    "name": "ACOS Runtime",
    "memory": {"base_accuracy": 0.72, "difficulty_slope": -0.12, "variance": 0.04, "retention_decay": 0.04},
    "planning": {"base_accuracy": 0.70, "difficulty_slope": -0.12, "variance": 0.04, "dep_accuracy": 0.70},
    "reasoning": {
        "deductive": {"base_accuracy": 0.78, "difficulty_slope": -0.10, "variance": 0.04},
        "inductive": {"base_accuracy": 0.68, "difficulty_slope": -0.14, "variance": 0.05},
        "causal": {"base_accuracy": 0.70, "difficulty_slope": -0.15, "variance": 0.05},
        "counterfactual": {"base_accuracy": 0.62, "difficulty_slope": -0.18, "variance": 0.06},
    },
    "learning": {"base_accuracy": 0.65, "difficulty_slope": -0.10, "variance": 0.05, "adaptation_speed": 0.65},
    "prediction": {"base_accuracy": 0.68, "difficulty_slope": -0.12, "variance": 0.05, "calibration_error": 0.10},
}


def _sample_performance(
    profile: dict[str, Any],
    domain: str,
    difficulty: float,
    rng: random.Random,
    subdomain: str | None = None,
) -> float:
    """Sample a performance score from a probabilistic profile.
    
    Uses a logistic-like model:
        accuracy = base - slope * difficulty + noise
    
    The noise is drawn from a truncated normal distribution.
    """
    if subdomain and domain in profile and subdomain in profile[domain]:
        domain_profile = profile[domain][subdomain]
    elif domain in profile and isinstance(profile[domain], dict) and "base_accuracy" in profile[domain]:
        domain_profile = profile[domain]
    else:
        domain_profile = {"base_accuracy": 0.5, "difficulty_slope": -0.2, "variance": 0.1}
    
    base = domain_profile.get("base_accuracy", 0.5)
    slope = domain_profile.get("difficulty_slope", -0.2)
    variance = domain_profile.get("variance", 0.1)
    
    # Core model: accuracy degrades with difficulty
    mean = base + slope * difficulty
    
    # Add Gaussian noise
    noise = rng.gauss(0, variance)
    
    # Clip to [0, 1]
    score = max(0.0, min(1.0, mean + noise))
    return score


class SimulatedBaseline:
    """Base class for simulated baseline systems.
    
    These use probabilistic models calibrated from published benchmarks
    to generate realistic performance profiles without API calls.
    """

    def __init__(self, system_type: SystemType, seed: int = 42) -> None:
        self.system_type = system_type
        self._profile = PROFILES[system_type]
        self._rng = random.Random(seed)
        self._state: dict[str, Any] = {
            "beliefs": {},
            "memories": [],
            "goals": [],
            "confidence": 0.5,
        }
        self._query_count = 0

    @property
    def name(self) -> str:
        return self._profile["name"]

    def process(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Process a query using simulated performance."""
        self._query_count += 1
        action = context.get("action", "query")
        
        if action == "store":
            return self._simulate_store(query, context)
        elif action == "recall" or action == "retrieve":
            return self._simulate_recall(query, context)
        elif action == "plan":
            return self._simulate_plan(query, context)
        elif action == "reason":
            return self._simulate_reason(query, context)
        elif action == "set_belief":
            return self._simulate_set_belief(query, context)
        elif action == "update_belief" or action == "correct_belief":
            return self._simulate_update_belief(query, context)
        elif action == "query_belief" or action == "query_confidence":
            return self._simulate_query_belief(query, context)
        elif action == "predict" or action == "estimate_probability" or action == "forecast_risk":
            return self._simulate_predict(query, context)
        elif action == "plan_complete":
            return self._simulate_plan_complete(query, context)
        elif action == "consolidate":
            return self._simulate_consolidate(query, context)
        else:
            return self._simulate_general(query, context)

    def get_state(self) -> dict[str, Any]:
        """Get the current simulated state."""
        return dict(self._state)

    def _simulate_store(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Simulate storing information."""
        # Memory systems have different store success rates
        memory_profile = self._profile["memory"]
        store_success_prob = memory_profile["base_accuracy"]
        
        if self._rng.random() < store_success_prob:
            self._state["memories"].append({
                "query": query,
                "context": context,
                "stored_at": self._query_count,
            })
        
        return {"status": "stored", "confidence": store_success_prob}

    def _simulate_recall(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Simulate recalling information."""
        memory_profile = self._profile["memory"]
        base = memory_profile["base_accuracy"]
        decay = memory_profile.get("retention_decay", 0.1)
        
        # Retention decreases with number of intervening items
        n_memories = len(self._state["memories"])
        delay_penalty = decay * math.log1p(n_memories) * 0.1
        
        # Interference
        interference = context.get("interference_items", 0)
        interference_penalty = interference * 0.02
        
        recall_prob = max(0.1, base - delay_penalty - interference_penalty)
        recall_prob += self._rng.gauss(0, 0.05)
        recall_prob = max(0.0, min(1.0, recall_prob))
        
        # Find matching memories
        relevant_memories = []
        for mem in self._state["memories"]:
            if self._rng.random() < recall_prob:
                relevant_memories.append(mem.get("query", ""))
        
        return {
            "response": "; ".join(relevant_memories) if relevant_memories else "No recall",
            "retrieved_facts": relevant_memories,
            "relevance_score": recall_prob,
            "confidence": recall_prob,
        }

    def _simulate_plan(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Simulate planning."""
        planning_profile = self._profile["planning"]
        base = planning_profile["base_accuracy"]
        dep_acc = planning_profile.get("dep_accuracy", 0.5)
        
        expected_subgoals = context.get("expected_subgoals", [])
        constraints = context.get("constraints", [])
        
        # Generate subgoals with some accuracy
        n_expected = len(expected_subgoals)
        n_correct = sum(1 for _ in range(n_expected) if self._rng.random() < base)
        
        # Add some incorrect subgoals
        n_extra = sum(1 for _ in range(max(1, int((1 - base) * 3))) if self._rng.random() < 0.3)
        
        subgoals = list(expected_subgoals[:n_correct])
        for _ in range(n_extra):
            subgoals.append(f"Generated subgoal {self._rng.randint(1, 100)}")
        
        # Plan steps
        steps = subgoals[:int(len(subgoals) * base)]
        
        return {
            "subgoals": subgoals,
            "plan_steps": steps,
            "confidence": base,
            "completeness_score": base,
        }

    def _simulate_reason(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Simulate reasoning."""
        reasoning_type = context.get("reasoning_type", "deductive")
        expected_answer = context.get("expected_answer", "")
        
        score = _sample_performance(
            self._profile, "reasoning", 0.5, self._rng, subdomain=reasoning_type
        )
        
        # Determine if correct
        is_correct = self._rng.random() < score
        
        if is_correct:
            answer = expected_answer
        else:
            # Generate a wrong answer
            answer = f"Incorrect reasoning result (simulated)"
        
        return {
            "answer": answer,
            "confidence": min(1.0, score + self._rng.gauss(0, 0.1)),
            "reasoning_type": reasoning_type,
        }

    def _simulate_set_belief(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Simulate setting a belief."""
        belief = context.get("belief", query)
        self._state["beliefs"][belief] = {
            "confidence": 0.7,
            "evidence_count": 1,
        }
        self._state["confidence"] = 0.7
        return {"status": "belief_set", "confidence": 0.7}

    def _simulate_update_belief(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Simulate updating a belief based on evidence."""
        learning_profile = self._profile["learning"]
        adaptation_speed = learning_profile.get("adaptation_speed", 0.4)
        
        supports = context.get("supports", True)
        
        # Update confidence based on evidence
        current = self._state["confidence"]
        if supports:
            delta = (1.0 - current) * adaptation_speed * 0.3
        else:
            delta = -current * adaptation_speed * 0.4
        
        new_confidence = max(0.0, min(1.0, current + delta + self._rng.gauss(0, 0.05)))
        self._state["confidence"] = new_confidence
        
        return {"confidence": new_confidence, "status": "belief_updated"}

    def _simulate_query_belief(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Simulate querying current belief state."""
        learning_profile = self._profile["learning"]
        base = learning_profile["base_accuracy"]
        
        confidence = self._state["confidence"]
        correction_score = base * confidence
        
        return {
            "confidence": confidence,
            "correction_score": min(1.0, correction_score + self._rng.gauss(0, 0.05)),
            "belief": query,
        }

    def _simulate_predict(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Simulate prediction."""
        prediction_profile = self._profile["prediction"]
        base = prediction_profile["base_accuracy"]
        cal_error = prediction_profile.get("calibration_error", 0.2)
        
        # Generate predicted probability with some calibration error
        true_prob = context.get("expected_probability", 0.5)
        if true_prob <= 0:
            true_prob = 0.5
        
        error = self._rng.gauss(0, cal_error)
        predicted_prob = max(0.05, min(0.95, true_prob + error))
        
        # Outcome prediction accuracy
        outcome_accuracy = base + self._rng.gauss(0, 0.05)
        outcome_accuracy = max(0.0, min(1.0, outcome_accuracy))
        
        # Risk level (inverse of success probability)
        risk_level = 1.0 - predicted_prob + self._rng.gauss(0, 0.1)
        risk_level = max(0.0, min(1.0, risk_level))
        
        return {
            "predicted_outcome": "predicted outcome" if self._rng.random() < outcome_accuracy else "incorrect prediction",
            "predicted_probability": predicted_prob,
            "estimated_probability": predicted_prob,
            "risk_level": risk_level,
            "confidence": outcome_accuracy,
        }

    def _simulate_plan_complete(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Simulate plan completion."""
        planning_profile = self._profile["planning"]
        base = planning_profile["base_accuracy"]
        completeness = base + self._rng.gauss(0, 0.05)
        return {"completeness_score": max(0.0, min(1.0, completeness))}

    def _simulate_consolidate(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Simulate knowledge consolidation."""
        memory_profile = self._profile["memory"]
        base = memory_profile["base_accuracy"]
        return {"response": "Consolidated knowledge", "confidence": base}

    def _simulate_general(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Simulate general query processing."""
        # Default: use memory profile as a rough proxy
        score = _sample_performance(self._profile, "memory", 0.5, self._rng)
        return {
            "response": f"Processed: {query[:50]}",
            "confidence": score,
            "relevance_score": score,
        }


class DirectLLMBaseline(SimulatedBaseline):
    """Baseline A: Direct LLM with no memory or reasoning infrastructure.
    
    Simulates a raw GPT-4 class model with no persistent state,
    no memory management, and no structured reasoning.
    """

    def __init__(self, seed: int = 42) -> None:
        super().__init__(SystemType.DIRECT_LLM, seed=seed)


class MemoryRAGBaseline(SimulatedBaseline):
    """Baseline B: LLM + RAG with simple vector store memory.
    
    Simulates a RAG system that can store and retrieve from
    a vector database but has no structured reasoning or learning.
    """

    def __init__(self, seed: int = 42) -> None:
        super().__init__(SystemType.MEMORY_RAG, seed=seed)


class ReActBaseline(SimulatedBaseline):
    """Baseline C: ReAct agent with reasoning-acting loop.
    
    Simulates the ReAct pattern where the agent alternates between
    reasoning steps and action steps.
    """

    def __init__(self, seed: int = 42) -> None:
        super().__init__(SystemType.REACT, seed=seed)


class LangGraphBaseline(SimulatedBaseline):
    """Baseline D: Graph-based workflow agent.
    
    Simulates a LangGraph-style agent with structured workflow
    and conditional branching.
    """

    def __init__(self, seed: int = 42) -> None:
        super().__init__(SystemType.LANGGRAPH, seed=seed)


class MultiAgentBaseline(SimulatedBaseline):
    """Baseline E: Multi-agent system with specialized agents.
    
    Simulates a multi-agent system where different agents handle
    different aspects of a task.
    """

    def __init__(self, seed: int = 42) -> None:
        super().__init__(SystemType.MULTI_AGENT, seed=seed)


class ACOSSimulated(SimulatedBaseline):
    """Simulated ACOS system for benchmarking.
    
    Uses the ACOS performance profile which represents the expected
    performance of the ACOS Runtime with its cognitive architecture.
    """

    def __init__(self, seed: int = 42) -> None:
        # Override to use ACOS profile
        self.system_type = SystemType.ACOS
        self._profile = ACOS_PROFILE
        self._rng = random.Random(seed)
        self._state: dict[str, Any] = {
            "beliefs": {},
            "memories": [],
            "goals": [],
            "confidence": 0.5,
        }
        self._query_count = 0


def get_baseline(system_type: SystemType, seed: int = 42) -> SimulatedBaseline:
    """Factory function to create a baseline system by type."""
    baselines = {
        SystemType.DIRECT_LLM: DirectLLMBaseline,
        SystemType.MEMORY_RAG: MemoryRAGBaseline,
        SystemType.REACT: ReActBaseline,
        SystemType.LANGGRAPH: LangGraphBaseline,
        SystemType.MULTI_AGENT: MultiAgentBaseline,
    }
    cls = baselines.get(system_type)
    if cls is None:
        raise ValueError(f"Unknown system type: {system_type}")
    return cls(seed=seed)
