"""
Pydantic data models for ACOS Runtime v0.2 — Cognitive State Engine & Knowledge Fabric.

Extends v0.1 models with:
- Knowledge Fabric: concepts, entities, relationships, knowledge graph
- Belief System: beliefs with evidence, contradictions, confidence evolution
- Goal System: goals with priorities, dependencies, progress tracking
- Cognitive State: central internal representation
- Semantic Memory: concept-based retrieval with relationships
- Reasoning: inference results, contradiction detection, knowledge gaps
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def gen_id() -> str:
    return str(uuid.uuid4())


# ─── Knowledge Fabric Models ──────────────────────────────────────────────────

class ConceptType(str, Enum):
    ABSTRACT = "abstract"       # Abstract concept (e.g., "intelligence")
    CONCRETE = "concrete"       # Concrete entity (e.g., "Python 3.12")
    PROCESS = "process"         # Process/algorithm (e.g., "gradient descent")
    PROPERTY = "property"       # Property/attribute (e.g., "accuracy")
    EVENT = "event"             # Event/occurrence (e.g., "training completed")


class RelationshipType(str, Enum):
    IS_A = "is_a"               # Inheritance/taxonomy
    PART_OF = "part_of"         # Composition
    DEPENDS_ON = "depends_on"   # Dependency
    RELATES_TO = "relates_to"   # Generic relation
    CONTRADICTS = "contradicts" # Contradiction
    SUPPORTS = "supports"       # Evidence/support
    PRECEDES = "precedes"       # Temporal ordering
    CAUSES = "causes"           # Causation
    IMPLIES = "implies"         # Logical implication
    SIMILAR_TO = "similar_to"   # Similarity


class Concept(BaseModel):
    """A concept in the knowledge graph."""
    id: str = Field(default_factory=gen_id)
    name: str
    concept_type: ConceptType = ConceptType.ABSTRACT
    description: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_ids: list[str] = Field(default_factory=list)  # Memory record IDs
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    access_count: int = 0


class Entity(BaseModel):
    """A named entity extracted from content."""
    id: str = Field(default_factory=gen_id)
    name: str
    entity_type: str = "generic"  # person, org, technology, etc.
    description: str = ""
    mentions: int = 1
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    source_ids: list[str] = Field(default_factory=list)
    concept_id: str | None = None  # Link to knowledge graph concept
    created_at: datetime = Field(default_factory=utc_now)


class Relationship(BaseModel):
    """A relationship between two concepts in the knowledge graph."""
    id: str = Field(default_factory=gen_id)
    source_concept_id: str
    target_concept_id: str
    relationship_type: RelationshipType = RelationshipType.RELATES_TO
    description: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    weight: float = Field(default=1.0, ge=0.0)
    source_ids: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class SourceReference(BaseModel):
    """A reference to the source of knowledge."""
    id: str = Field(default_factory=gen_id)
    memory_id: str | None = None   # Link to MemoryRecord
    thread_id: str | None = None
    session_id: str | None = None
    content_snippet: str = ""
    timestamp: datetime = Field(default_factory=utc_now)


# ─── Belief System Models ─────────────────────────────────────────────────────

class BeliefStatus(str, Enum):
    ACTIVE = "active"           # Currently believed
    WEAKENED = "weakened"       # Confidence reduced by contradiction
    SUPERSEDED = "superseded"   # Replaced by a newer belief
    ABANDONED = "abandoned"     # No longer held


class Evidence(BaseModel):
    """Evidence supporting or contradicting a belief."""
    id: str = Field(default_factory=gen_id)
    content: str
    evidence_type: str = "supporting"  # "supporting" or "contradicting"
    source_id: str | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utc_now)


class Belief(BaseModel):
    """A belief held by the cognitive system."""
    id: str = Field(default_factory=gen_id)
    statement: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: BeliefStatus = BeliefStatus.ACTIVE
    supporting_evidence: list[Evidence] = Field(default_factory=list)
    contradicting_evidence: list[Evidence] = Field(default_factory=list)
    related_concept_ids: list[str] = Field(default_factory=list)
    parent_belief_id: str | None = None  # For belief evolution tracking
    version: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ─── Goal System Models ───────────────────────────────────────────────────────

class GoalStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    PAUSED = "paused"


class GoalPriority(int, Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 15


class Goal(BaseModel):
    """A goal tracked by the cognitive system."""
    id: str = Field(default_factory=gen_id)
    description: str
    status: GoalStatus = GoalStatus.ACTIVE
    priority: GoalPriority = GoalPriority.NORMAL
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    parent_goal_id: str | None = None
    subgoal_ids: list[str] = Field(default_factory=list)
    dependency_ids: list[str] = Field(default_factory=list)  # Must complete before this
    related_concept_ids: list[str] = Field(default_factory=list)
    related_belief_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


# ─── Cognitive State Models ───────────────────────────────────────────────────

class CognitiveState(BaseModel):
    """
    Central internal representation of ACOS cognitive state.
    
    This is the 'conscious state' of the system — everything the system
    'knows', 'believes', 'wants', and 'remembers' at a given point in time.
    
    Every session updates this state, and it persists across sessions.
    """
    id: str = Field(default_factory=gen_id)
    beliefs: list[Belief] = Field(default_factory=list)
    goals: list[Goal] = Field(default_factory=list)
    active_thread_ids: list[str] = Field(default_factory=list)
    recent_memory_ids: list[str] = Field(default_factory=list)
    uncertainty_estimates: dict[str, float] = Field(default_factory=dict)
    knowledge_graph_concept_ids: list[str] = Field(default_factory=list)
    session_count: int = 0
    last_query: str | None = None
    last_synthesis: str | None = None
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ─── Semantic Memory Models ───────────────────────────────────────────────────

class SemanticConcept(BaseModel):
    """A concept stored in semantic memory with relationship context."""
    concept: Concept
    relationships: list[Relationship] = Field(default_factory=list)
    related_concept_names: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    last_accessed: datetime = Field(default_factory=utc_now)


class SemanticQueryResult(BaseModel):
    """Result of a semantic memory query."""
    concepts: list[SemanticConcept] = Field(default_factory=list)
    inferred_relationships: list[Relationship] = Field(default_factory=list)
    total_matches: int = 0
    query_confidence: float = Field(default=0.5, ge=0.0, le=1.0)


# ─── Reasoning Engine Models ──────────────────────────────────────────────────

class InferenceType(str, Enum):
    DEDUCTION = "deduction"       # A->B, A, therefore B
    INDUCTION = "induction"       # Pattern from observations
    ABDUCTION = "abduction"       # Best explanation
    TRANSITIVITY = "transitivity" # A->B, B->C, therefore A->C
    ANALOGY = "analogy"           # Similarity-based inference


class InferenceResult(BaseModel):
    """Result of a reasoning inference."""
    id: str = Field(default_factory=gen_id)
    inference_type: InferenceType
    premise_concept_ids: list[str] = Field(default_factory=list)
    conclusion_concept_id: str | None = None
    conclusion_description: str
    relationship_type: RelationshipType = RelationshipType.IMPLIES
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    reasoning_chain: list[str] = Field(default_factory=list)  # Step-by-step reasoning
    created_at: datetime = Field(default_factory=utc_now)


class ContradictionResult(BaseModel):
    """A detected contradiction in beliefs or knowledge."""
    id: str = Field(default_factory=gen_id)
    belief_id_1: str | None = None
    belief_id_2: str | None = None
    concept_id_1: str | None = None
    concept_id_2: str | None = None
    description: str
    severity: float = Field(default=0.5, ge=0.0, le=1.0)
    resolution_suggestion: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class KnowledgeGap(BaseModel):
    """A discovered gap in the knowledge graph."""
    id: str = Field(default_factory=gen_id)
    description: str
    related_concept_ids: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    suggested_query: str | None = None  # Query that could fill the gap
    created_at: datetime = Field(default_factory=utc_now)


# ─── Knowledge Consolidation Models ───────────────────────────────────────────

class ConsolidationResult(BaseModel):
    """Result of a knowledge consolidation pass."""
    concepts_extracted: int = 0
    entities_extracted: int = 0
    relationships_extracted: int = 0
    beliefs_updated: int = 0
    beliefs_created: int = 0
    memories_consolidated: int = 0
    semantic_entries_created: int = 0
    consolidation_time_ms: float = 0.0


# ─── Updated API Models for v0.2 ──────────────────────────────────────────────

class QueryRequestV2(BaseModel):
    """Enhanced query request for v0.2 with cognitive state awareness."""
    query: str
    thread_types: list[str] | None = None  # ThreadType values
    priority: int = 5
    metadata: dict[str, Any] = Field(default_factory=dict)
    update_cognitive_state: bool = True  # Whether to update cognitive state


class QueryResponseV2(BaseModel):
    """Enhanced query response for v0.2 with cognitive state info."""
    session_id: str
    query: str
    final_synthesis: str
    threads: list[dict[str, Any]] = Field(default_factory=list)
    agent_outputs: list[dict[str, Any]] = Field(default_factory=list)
    reflections: list[dict[str, Any]] = Field(default_factory=list)
    verifications: list[dict[str, Any]] = Field(default_factory=list)
    consolidation: ConsolidationResult | None = None
    cognitive_state_snapshot: dict[str, Any] = Field(default_factory=dict)
    beliefs_affected: list[str] = Field(default_factory=list)
    goals_affected: list[str] = Field(default_factory=list)
    knowledge_graph_changes: list[str] = Field(default_factory=list)
    total_time_ms: float


class BeliefCreate(BaseModel):
    """Request body for creating a new belief."""
    statement: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_for: list[str] = Field(default_factory=list)
    evidence_against: list[str] = Field(default_factory=list)
    category: str = "general"


class GoalCreate(BaseModel):
    """Request body for creating a new goal."""
    description: str
    priority: GoalPriority = GoalPriority.NORMAL
    category: str = "general"
    parent_goal_id: str | None = None


class CognitiveStateResponse(BaseModel):
    """API response for cognitive state queries."""
    state_id: str
    active_beliefs: int = 0
    weakened_beliefs: int = 0
    active_goals: int = 0
    knowledge_concepts: int = 0
    overall_confidence: float = 0.5
    session_count: int = 0
    last_query: str | None = None
    last_updated: datetime = Field(default_factory=utc_now)
    uncertainty_topics: list[str] = Field(default_factory=list)


class KnowledgeGraphResponse(BaseModel):
    """API response for knowledge graph queries."""
    concepts: list[Concept]
    relationships: list[Relationship]
    entities: list[Entity]
    total_concepts: int
    total_relationships: int
