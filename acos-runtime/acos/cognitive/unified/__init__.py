"""
ACOS Runtime v0.5 — Unified Cognitive Architecture.

This package unifies all previous subsystems into a coherent cognitive system
with a complete cognitive loop:

Observe → Understand → Update Beliefs → Update Goals → Update Cognitive State
→ Predict Future → Simulate Alternatives → Select Action → Execute →
Measure Outcome → Learn → Evolve

Modules:
- world_model_engine: Enhanced world model with risk/uncertainty estimation
- active_learning: Prediction error tracking and model improvement
- cognitive_manifold: Unified latent representation of cognitive state
- goal_competition: Dynamic goal prioritization
- attention_economy: Limited cognitive resource allocation
- enhanced_causal: Causal chains, root cause analysis, forecasting
- self_model: Self-awareness of strengths, weaknesses, performance
- cognitive_cycle: The core runtime loop
- evaluation: Benchmarks and metrics
"""

from acos.cognitive.unified.world_model_engine import WorldModelEngine
from acos.cognitive.unified.active_learning import ActiveLearningLoop
from acos.cognitive.unified.cognitive_manifold import CognitiveStateManifold
from acos.cognitive.unified.goal_competition import GoalCompetitionEngine
from acos.cognitive.unified.attention_economy import AttentionEconomy
from acos.cognitive.unified.enhanced_causal import EnhancedCausalReasoner
from acos.cognitive.unified.self_model import SelfModel
from acos.cognitive.unified.cognitive_cycle import CognitiveCycle
from acos.cognitive.unified.evaluation import EvaluationFramework

__all__ = [
    "WorldModelEngine",
    "ActiveLearningLoop",
    "CognitiveStateManifold",
    "GoalCompetitionEngine",
    "AttentionEconomy",
    "EnhancedCausalReasoner",
    "SelfModel",
    "CognitiveCycle",
    "EvaluationFramework",
]
