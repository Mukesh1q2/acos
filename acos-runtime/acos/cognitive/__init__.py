"""
ACOS Cognitive modules — v0.2 Cognitive State Engine & Knowledge Fabric.

Provides:
- KnowledgeFabric: Concept graph with extraction, traversal, and search
- BeliefState: Belief management with evidence and confidence evolution
- GoalManager: Goal tracking with priorities, dependencies, and progress
- CognitiveStateEngine: Central internal representation, persists across sessions
- SemanticMemory: Concept-based long-term knowledge with relationships
- KnowledgeConsolidator: Converts episodic memory into semantic knowledge
- ReasoningEngine: Inference, contradiction detection, knowledge gap discovery
"""

from acos.cognitive.knowledge_fabric import KnowledgeFabric
from acos.cognitive.belief_system import BeliefState
from acos.cognitive.goal_system import GoalManager
from acos.cognitive.cognitive_state import CognitiveStateEngine
from acos.cognitive.semantic_memory import SemanticMemory
from acos.cognitive.knowledge_consolidator import KnowledgeConsolidator
from acos.cognitive.reasoning_engine import ReasoningEngine

__all__ = [
    "KnowledgeFabric",
    "BeliefState",
    "GoalManager",
    "CognitiveStateEngine",
    "SemanticMemory",
    "KnowledgeConsolidator",
    "ReasoningEngine",
]
