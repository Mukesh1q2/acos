"""
Knowledge Consolidator — converts episodic memory into semantic knowledge.

Responsibilities:
- Convert episodic memory into semantic memory
- Extract concepts from conversations/content
- Update knowledge graph with new concepts and relationships
- Update beliefs based on accumulated evidence
- Bridge between v0.1 episodic memory and v0.2 semantic memory
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from acos.schemas.v2_models import (
    Concept, ConceptType, Relationship, RelationshipType,
    Entity, Evidence, Belief, ConsolidationResult,
)
from acos.schemas.models import MemoryRecord, MemoryType


class KnowledgeConsolidator:
    """
    Knowledge Consolidator for ACOS v0.2.
    
    Converts episodic memories into persistent semantic knowledge by:
    1. Reading episodic memories
    2. Extracting concepts and entities
    3. Building/updating the knowledge graph
    4. Updating beliefs based on evidence
    5. Creating semantic memory entries
    """

    def __init__(self, knowledge_fabric: Any, belief_state: Any, semantic_memory: Any, memory_manager: Any):
        """
        Initialize the consolidator.
        
        Args:
            knowledge_fabric: KnowledgeFabric instance for graph operations
            belief_state: BeliefState instance for belief management
            semantic_memory: SemanticMemory instance for concept storage
            memory_manager: MemoryManager instance for v0.1 memory access
        """
        self._fabric = knowledge_fabric
        self._beliefs = belief_state
        self._semantic = semantic_memory
        self._memory = memory_manager

    async def consolidate_session(
        self,
        session_id: str,
        thread_ids: list[str],
        session_summary: str,
    ) -> ConsolidationResult:
        """
        Consolidate all episodic memories from a session into semantic knowledge.
        
        This is the main entry point — called after each session completes.
        
        Process:
        1. Retrieve all episodic memories from the session threads
        2. Extract concepts and entities from those memories
        3. Add/update concepts in the knowledge graph
        4. Extract and create relationships
        5. Update beliefs based on session evidence
        6. Create semantic memory entries
        7. Return consolidation statistics
        """
        start_time = time.monotonic()
        result = ConsolidationResult()

        # 1. Gather all episodic memories from session threads
        all_memories: list[MemoryRecord] = []
        for thread_id in thread_ids:
            try:
                episodic = await self._memory.retrieve_episodic(thread_id)
                all_memories.extend(episodic)
            except Exception:
                pass

        if not all_memories:
            # Also try working memories
            for thread_id in thread_ids:
                try:
                    working = await self._memory.retrieve_working(thread_id)
                    all_memories.extend(working)
                except Exception:
                    pass

        if not all_memories:
            result.consolidation_time_ms = (time.monotonic() - start_time) * 1000
            return result

        # 2. Extract concepts and entities from all memories
        all_concepts: list[Concept] = []
        all_entities: list[Entity] = []
        all_relationships: list[Relationship] = []

        for memory in all_memories:
            try:
                # Extract concepts
                concepts = self._fabric.extract_concepts(memory.content)
                all_concepts.extend(concepts)

                # Extract entities
                entities = self._fabric.extract_entities(memory.content)
                all_entities.extend(entities)

                # Extract relationships between concepts
                relationships = self._fabric.extract_relationships(memory.content, concepts)
                all_relationships.extend(relationships)
            except Exception:
                continue

        # Also extract from session summary
        try:
            summary_concepts = self._fabric.extract_concepts(session_summary)
            summary_entities = self._fabric.extract_entities(session_summary)
            summary_rels = self._fabric.extract_relationships(session_summary, summary_concepts)
            all_concepts.extend(summary_concepts)
            all_entities.extend(summary_entities)
            all_relationships.extend(summary_rels)
        except Exception:
            pass

        # 3. Add/update concepts in the knowledge graph
        concept_id_map: dict[str, str] = {}  # name -> id mapping
        for concept in all_concepts:
            try:
                # Check if concept already exists
                existing = await self._fabric.find_concept_by_name(concept.name)
                if existing:
                    # Update existing concept confidence
                    concept_id_map[concept.name] = existing[0].id
                    await self._fabric.link_to_memory(existing[0].id, memory.id if hasattr(memory, 'id') else "")
                else:
                    # Add new concept
                    added = await self._fabric.add_concept(concept)
                    concept_id_map[concept.name] = added.id
                    result.concepts_extracted += 1
            except Exception:
                continue

        # 4. Add relationships to the knowledge graph
        for rel in all_relationships:
            try:
                # Resolve concept IDs from names
                source_name = rel.source_concept_id  # May be a name placeholder
                target_name = rel.target_concept_id

                # Try to find actual concept IDs
                source_id = concept_id_map.get(source_name, source_name)
                target_id = concept_id_map.get(target_name, target_name)

                if source_id and target_id:
                    rel.source_concept_id = source_id
                    rel.target_concept_id = target_id
                    await self._fabric.add_relationship(rel)
                    result.relationships_extracted += 1
            except Exception:
                continue

        # 5. Add entities
        for entity in all_entities:
            try:
                existing = await self._fabric.find_concept_by_name(entity.name)
                if not existing:
                    await self._fabric.add_entity(entity)
                    result.entities_extracted += 1
            except Exception:
                continue

        # 6. Update beliefs based on session evidence
        beliefs_affected = await self._update_beliefs_from_session(all_memories, session_summary)
        result.beliefs_updated = beliefs_affected.get("updated", 0)
        result.beliefs_created = beliefs_affected.get("created", 0)

        # 7. Create semantic memory entries
        semantic_count = await self._create_semantic_entries(all_concepts, all_relationships)
        result.semantic_entries_created = semantic_count

        # 8. Consolidate episodic into semantic via SemanticMemory
        try:
            consolidate_count = await self._semantic.consolidate_from_episodic(all_memories)
            result.memories_consolidated = consolidate_count
        except Exception:
            pass

        result.consolidation_time_ms = (time.monotonic() - start_time) * 1000
        return result

    async def consolidate_episodic_to_semantic(
        self,
        thread_id: str,
    ) -> ConsolidationResult:
        """
        Consolidate a single thread's episodic memories into semantic knowledge.
        
        Lighter-weight version for per-thread consolidation.
        """
        start_time = time.monotonic()
        result = ConsolidationResult()

        # Get episodic memories
        try:
            memories = await self._memory.retrieve_episodic(thread_id)
        except Exception:
            memories = []

        if not memories:
            try:
                memories = await self._memory.retrieve_working(thread_id)
            except Exception:
                result.consolidation_time_ms = (time.monotonic() - start_time) * 1000
                return result

        # Extract and store
        all_concepts: list[Concept] = []
        for mem in memories:
            try:
                concepts = self._fabric.extract_concepts(mem.content)
                entities = self._fabric.extract_entities(mem.content)
                relationships = self._fabric.extract_relationships(mem.content, concepts)

                for concept in concepts:
                    existing = await self._fabric.find_concept_by_name(concept.name)
                    if not existing:
                        await self._fabric.add_concept(concept)
                        all_concepts.append(concept)
                        result.concepts_extracted += 1

                for entity in entities:
                    await self._fabric.add_entity(entity)
                    result.entities_extracted += 1

                for rel in relationships:
                    await self._fabric.add_relationship(rel)
                    result.relationships_extracted += 1
            except Exception:
                continue

        # Create semantic entries
        semantic_count = await self._create_semantic_entries(all_concepts, [])
        result.semantic_entries_created = semantic_count

        result.consolidation_time_ms = (time.monotonic() - start_time) * 1000
        return result

    async def _update_beliefs_from_session(
        self,
        memories: list[MemoryRecord],
        session_summary: str,
    ) -> dict[str, int]:
        """
        Update beliefs based on evidence from session memories.
        
        Scans memory content for claim-like statements and updates beliefs.
        """
        updated = 0
        created = 0

        # Collect all text content
        all_text = session_summary + "\n" + "\n".join(m.content for m in memories)

        # Extract claim-like patterns
        claims = self._extract_claims(all_text)

        for claim in claims:
            try:
                # Check if a similar belief already exists
                existing = await self._find_similar_belief(claim)

                if existing:
                    # Add as supporting evidence
                    evidence = Evidence(
                        content=claim,
                        evidence_type="supporting",
                        confidence=0.6,
                    )
                    await self._beliefs.add_evidence(existing.id, evidence)
                    updated += 1
                else:
                    # Create new belief from claim
                    await self._beliefs.add_belief(
                        statement=claim,
                        confidence=0.5,
                        supporting_evidence=[Evidence(
                            content=f"Observed in session",
                            evidence_type="supporting",
                            confidence=0.5,
                        )],
                    )
                    created += 1
            except Exception:
                continue

        return {"updated": updated, "created": created}

    def _extract_claims(self, text: str) -> list[str]:
        """
        Extract claim-like statements from text.
        
        Looks for patterns like:
        - "X is Y"
        - "X performs best on Y"
        - "X achieves Y%"
        - "X improves Y by Z"
        """
        claims = []
        sentences = text.replace("!", ".").replace("?", ".").split(".")

        claim_patterns = [
            # "X is/are Y"
            lambda s: any(f" {kw} " in f" {s} " for kw in [" is ", " are ", " was ", " were "]),
            # "X performs/achieves Y"
            lambda s: any(kw in s.lower() for kw in ["performs", "achieves", "improves", "outperforms", "reduces", "increases"]),
            # "X best/worst Y"
            lambda s: any(kw in s.lower() for kw in ["best", "worst", "optimal", "superior", "inferior"]),
            # Quantified claims
            lambda s: any(c in s for c in ["%", "x faster", "x better", "x less"]),
        ]

        for sentence in sentences:
            s = sentence.strip()
            if len(s) < 15 or len(s) > 200:
                continue
            if any(pattern(s) for pattern in claim_patterns):
                claims.append(s)

        return claims[:20]  # Limit claims per consolidation

    async def _find_similar_belief(self, claim: str) -> Any:
        """Find an existing belief similar to a claim."""
        try:
            active = await self._beliefs.get_active_beliefs()
            claim_lower = claim.lower()

            for belief in active:
                # Simple similarity: check if key terms overlap
                belief_terms = set(belief.statement.lower().split())
                claim_terms = set(claim_lower.split())
                overlap = belief_terms & claim_terms
                if len(overlap) >= 2 and len(overlap) / max(len(claim_terms), 1) >= 0.4:
                    return belief
        except Exception:
            pass
        return None

    async def _create_semantic_entries(
        self,
        concepts: list[Concept],
        relationships: list[Relationship],
    ) -> int:
        """Create semantic memory entries from concepts and relationships."""
        count = 0
        for concept in concepts:
            try:
                existing = await self._semantic.retrieve_concept_by_name(concept.name, fuzzy=True)
                if not existing:
                    await self._semantic.store_concept(concept)
                    count += 1
            except Exception:
                continue

        for rel in relationships:
            try:
                await self._semantic.store_relationship(rel)
                count += 1
            except Exception:
                continue

        return count

    async def get_stats(self) -> dict[str, Any]:
        """Get consolidation statistics."""
        try:
            fabric_stats = await self._fabric.get_stats()
        except Exception:
            fabric_stats = {}

        try:
            belief_stats = await self._beliefs.get_stats()
        except Exception:
            belief_stats = {}

        try:
            semantic_stats = await self._semantic.get_stats()
        except Exception:
            semantic_stats = {}

        return {
            "knowledge_graph": fabric_stats,
            "beliefs": belief_stats,
            "semantic_memory": semantic_stats,
        }
