"""
ACOS Cognitive Dynamics — v0.3 Cognitive Dynamics Engine.

Provides:
- AttentionManager: Track active concepts, goals, beliefs with focus scores
- UncertaintyEngine: Track unknowns, conflicts, missing evidence, confidence changes
- PlanState: Plans, subplans, dependencies, expected/actual outcomes
- CognitiveGraph: Unified NetworkX graph for concepts, beliefs, goals, memories, plans
- StateEvolutionEngine: dS/dt = F(S) state evolution
- CounterfactualReasoner: What-if reasoning, alternatives
- CognitiveDynamicsEngine: Core orchestrator for belief updates, goal competition, etc.
"""

from acos.cognitive.dynamics.attention import AttentionManager
from acos.cognitive.dynamics.uncertainty import UncertaintyEngine
from acos.cognitive.dynamics.plan_state import PlanState
from acos.cognitive.dynamics.cognitive_graph import CognitiveGraph
from acos.cognitive.dynamics.state_evolution import StateEvolutionEngine
from acos.cognitive.dynamics.counterfactual import CounterfactualReasoner
from acos.cognitive.dynamics.engine import CognitiveDynamicsEngine

__all__ = [
    "AttentionManager",
    "UncertaintyEngine",
    "PlanState",
    "CognitiveGraph",
    "StateEvolutionEngine",
    "CounterfactualReasoner",
    "CognitiveDynamicsEngine",
]
