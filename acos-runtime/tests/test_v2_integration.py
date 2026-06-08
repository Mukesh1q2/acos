"""
Integration Test — ACOS Runtime v0.2 Cognitive Architecture.

Verifies the 8 success criteria:
1. Knowledge Graph exists — create concepts, relationships, verify graph
2. Beliefs persist — create beliefs, close/reopen DB, verify they load
3. Goals persist — create goals, close/reopen DB, verify they load
4. Cognitive State persists — update state, close/reopen, verify loads
5. Knowledge consolidates across sessions — store episodic memories, consolidate, check semantic memory
6. Semantic Memory contains concepts and relationships
7. Reasoning Engine can infer new relationships (transitivity: A→B, B→C → infer A→C)
8. Kernel updates Cognitive State after every session — process query, verify cognitive state is updated
"""

import os
import tempfile

import pytest

from acos.memory.store import StorageBackend
from acos.memory.manager import MemoryManager
from acos.schemas.v2_models import (
    Concept,
    ConceptType,
    Relationship,
    RelationshipType,
    Belief,
    BeliefStatus,
    Evidence,
    Goal,
    GoalPriority,
    GoalStatus,
    InferenceType,
)
from acos.schemas.models import QueryRequest
from acos.cognitive.knowledge_fabric import KnowledgeFabric
from acos.cognitive.belief_system import BeliefState
from acos.cognitive.goal_system import GoalManager
from acos.cognitive.cognitive_state import CognitiveStateEngine
from acos.cognitive.semantic_memory import SemanticMemory
from acos.cognitive.knowledge_consolidator import KnowledgeConsolidator
from acos.cognitive.reasoning_engine import ReasoningEngine
from acos.kernel import CognitiveKernel


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def db_path():
    """Create a temporary database path for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


# ═══════════════════════════════════════════════════════════════════════════════
# Criterion 1: Knowledge Graph exists
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeGraph:
    """Integration test: Knowledge Graph exists with concepts and relationships."""

    @pytest.mark.asyncio
    async def test_knowledge_graph_lifecycle(self, db_path):
        """Create concepts, relationships, verify the graph structure."""
        storage = StorageBackend(db_path=db_path)
        await storage.initialize()

        try:
            fabric = KnowledgeFabric(storage)
            await fabric.initialize()

            # Create concepts
            python = Concept(name="Python", concept_type=ConceptType.CONCRETE, description="Programming language")
            ml = Concept(name="Machine Learning", concept_type=ConceptType.PROCESS, description="AI subfield")
            dl = Concept(name="Deep Learning", concept_type=ConceptType.PROCESS, description="ML using neural networks")

            await fabric.add_concept(python)
            await fabric.add_concept(ml)
            await fabric.add_concept(dl)

            # Create relationships
            r1 = Relationship(
                source_concept_id=dl.id,
                target_concept_id=ml.id,
                relationship_type=RelationshipType.IS_A,
                description="Deep Learning is a kind of Machine Learning",
            )
            r2 = Relationship(
                source_concept_id=ml.id,
                target_concept_id=python.id,
                relationship_type=RelationshipType.DEPENDS_ON,
                description="ML depends on Python",
            )
            await fabric.add_relationship(r1)
            await fabric.add_relationship(r2)

            # Verify graph structure
            stats = fabric.get_stats()
            assert stats["total_concepts"] == 3
            assert stats["total_relationships"] == 2

            # Verify relationships are retrievable
            dl_rels = fabric.get_relationships(dl.id)
            assert len(dl_rels) >= 1
            assert any(r.relationship_type == RelationshipType.IS_A for r in dl_rels)

            # Verify path exists
            path = fabric.get_path(dl.id, python.id)
            assert path is not None, "Should find a path from Deep Learning to Python"
            assert len(path) == 3  # dl -> ml -> python

            # Verify semantic search
            results = await fabric.semantic_search("learning")
            assert len(results) > 0

        finally:
            await storage.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Criterion 2: Beliefs persist across DB restarts
# ═══════════════════════════════════════════════════════════════════════════════

class TestBeliefPersistence:
    """Integration test: Beliefs persist across close/reopen."""

    @pytest.mark.asyncio
    async def test_beliefs_persist_across_restarts(self, db_path):
        """Create beliefs, close/reopen DB, verify they load."""
        # Session 1: Create beliefs
        storage = StorageBackend(db_path=db_path)
        await storage.initialize()

        try:
            bs = BeliefState(storage)
            await bs.initialize()

            b1 = await bs.add_belief("Python is effective for AI", confidence=0.8,
                                     supporting_evidence=[Evidence(content="Industry survey", confidence=0.9)])
            b2 = await bs.add_belief("Rust is fast", confidence=0.7)
            assert b1.id is not None
            assert b2.id is not None
        finally:
            await storage.close()

        # Session 2: Reopen and verify
        storage2 = StorageBackend(db_path=db_path)
        await storage2.initialize()

        try:
            bs2 = BeliefState(storage2)
            await bs2.initialize()

            active = await bs2.get_active_beliefs()
            assert len(active) >= 2

            statements = [b.statement for b in active]
            assert "Python is effective for AI" in statements
            assert "Rust is fast" in statements

            # Verify evidence persisted
            for b in active:
                if b.statement == "Python is effective for AI":
                    assert len(b.supporting_evidence) >= 1
        finally:
            await storage2.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Criterion 3: Goals persist across DB restarts
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoalPersistence:
    """Integration test: Goals persist across close/reopen."""

    @pytest.mark.asyncio
    async def test_goals_persist_across_restarts(self, db_path):
        """Create goals, close/reopen DB, verify they load."""
        # Session 1: Create goals
        storage = StorageBackend(db_path=db_path)
        await storage.initialize()

        try:
            gm = GoalManager(storage)
            await gm.initialize()

            g1 = await gm.create_goal("Build knowledge graph", priority=GoalPriority.HIGH)
            g2 = await gm.create_goal("Implement belief system", priority=GoalPriority.NORMAL)
            await gm.update_progress(g1.id, 0.5)
        finally:
            await storage.close()

        # Session 2: Reopen and verify
        storage2 = StorageBackend(db_path=db_path)
        await storage2.initialize()

        try:
            gm2 = GoalManager(storage2)
            await gm2.initialize()

            g1_loaded = await gm2.get_goal(g1.id)
            assert g1_loaded is not None
            assert g1_loaded.description == "Build knowledge graph"
            assert g1_loaded.progress == 0.5
            assert g1_loaded.priority == GoalPriority.HIGH

            g2_loaded = await gm2.get_goal(g2.id)
            assert g2_loaded is not None
            assert g2_loaded.description == "Implement belief system"

            active = await gm2.get_active_goals()
            assert len(active) >= 2
        finally:
            await storage2.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Criterion 4: Cognitive State persists across DB restarts
# ═══════════════════════════════════════════════════════════════════════════════

class TestCognitiveStatePersistence:
    """Integration test: Cognitive State persists across close/reopen."""

    @pytest.mark.asyncio
    async def test_cognitive_state_persists(self, db_path):
        """Update cognitive state, close/reopen, verify it loads."""
        # Session 1: Update cognitive state
        storage = StorageBackend(db_path=db_path)
        await storage.initialize()

        try:
            engine = CognitiveStateEngine(storage)
            await engine.initialize()

            await engine.begin_session("Test query")
            await engine.update_uncertainty("machine learning", 0.7)
            await engine.add_knowledge_concept("concept-abc")
            await engine.end_session("Test synthesis", 0.85)

            state = await engine.get_state()
            assert state.session_count == 1
        finally:
            await storage.close()

        # Session 2: Reopen and verify
        storage2 = StorageBackend(db_path=db_path)
        await storage2.initialize()

        try:
            engine2 = CognitiveStateEngine(storage2)
            await engine2.initialize()

            state = await engine2.get_state()
            assert state.session_count == 1
            assert state.overall_confidence == 0.85
            assert "machine learning" in state.uncertainty_estimates
            assert "concept-abc" in state.knowledge_graph_concept_ids

            snapshot = await engine2.get_snapshot()
            assert snapshot["session_count"] == 1
        finally:
            await storage2.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Criterion 5: Knowledge consolidates across sessions
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeConsolidation:
    """Integration test: Knowledge consolidates from episodic to semantic memory."""

    @pytest.mark.asyncio
    async def test_consolidation_across_sessions(self, db_path):
        """Store episodic memories, consolidate, check semantic memory."""
        storage = StorageBackend(db_path=db_path)
        await storage.initialize()

        try:
            fabric = KnowledgeFabric(storage)
            await fabric.initialize()

            bs = BeliefState(storage)
            await bs.initialize()

            sem = SemanticMemory(storage)
            await sem.initialize()

            mm = MemoryManager(storage)

            consolidator = KnowledgeConsolidator(fabric, bs, sem, mm)

            # Store episodic memories across two "sessions"
            await mm.store_episodic("s1-thread", "Python is a programming language used for AI.")
            await mm.store_episodic("s1-thread", "TensorFlow is a framework for deep learning.")

            result1 = await consolidator.consolidate_session(
                session_id="session-1",
                thread_ids=["s1-thread"],
                session_summary="Explored Python and AI frameworks.",
            )

            # Second session with more memories
            await mm.store_episodic("s2-thread", "PyTorch is another deep learning framework that uses Python.")
            await mm.store_episodic("s2-thread", "Neural networks improve with more training data.")

            result2 = await consolidator.consolidate_session(
                session_id="session-2",
                thread_ids=["s2-thread"],
                session_summary="Explored PyTorch and neural network training.",
            )

            # Verify consolidation produced results
            total_concepts = result1.concepts_extracted + result2.concepts_extracted
            total_semantic = result1.semantic_entries_created + result2.semantic_entries_created
            assert total_concepts + total_semantic > 0, "Should have extracted or created concepts"

            # Verify semantic memory now contains some concepts
            sem_stats = await sem.get_stats()
            assert sem_stats["total_concepts"] > 0, "Semantic memory should have concepts after consolidation"

        finally:
            await storage.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Criterion 6: Semantic Memory contains concepts and relationships
# ═══════════════════════════════════════════════════════════════════════════════

class TestSemanticMemoryIntegration:
    """Integration test: Semantic Memory holds concepts and relationships."""

    @pytest.mark.asyncio
    async def test_semantic_memory_concepts_and_relationships(self, db_path):
        """Store concepts and relationships, verify retrieval and traversal."""
        storage = StorageBackend(db_path=db_path)
        await storage.initialize()

        try:
            sem = SemanticMemory(storage)
            await sem.initialize()

            # Create a concept graph: Python → IS_A → Language, Python → USED_FOR → AI
            python = Concept(name="Python", concept_type=ConceptType.CONCRETE)
            lang = Concept(name="Language", concept_type=ConceptType.ABSTRACT)
            ai = Concept(name="AI", concept_type=ConceptType.PROCESS)

            await sem.store_concept(python)
            await sem.store_concept(lang)
            await sem.store_concept(ai)

            await sem.link_concepts(python.id, lang.id, RelationshipType.IS_A, "Python is a language")
            await sem.link_concepts(python.id, ai.id, RelationshipType.RELATES_TO, "Python is used for AI")

            # Verify concepts exist
            retrieved = await sem.retrieve_concept(python.id)
            assert retrieved is not None
            assert retrieved.name == "Python"

            # Verify relationships exist
            rels = await sem.get_relationships(python.id)
            assert len(rels) >= 2

            # Verify semantic query
            result = await sem.semantic_query("Python")
            assert result.total_matches >= 1

            # Verify related concepts
            related = await sem.get_related_concepts(python.id, max_depth=2)
            assert len(related) >= 1
            related_names = [c.name for c, _ in related]
            assert "Language" in related_names or "AI" in related_names

            # Verify stats
            stats = await sem.get_stats()
            assert stats["total_concepts"] >= 3
            assert stats["total_relationships"] >= 2

        finally:
            await storage.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Criterion 7: Reasoning Engine can infer new relationships (transitivity)
# ═══════════════════════════════════════════════════════════════════════════════

class TestReasoningEngineIntegration:
    """Integration test: Reasoning Engine infers transitive relationships."""

    @pytest.mark.asyncio
    async def test_transitivity_inference(self, db_path):
        """A→B, B→C → infer A→C (transitive inference)."""
        storage = StorageBackend(db_path=db_path)
        await storage.initialize()

        # Separate DB for reasoning engine audit trail
        fd, rdb_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            fabric = KnowledgeFabric(storage)
            await fabric.initialize()

            bs = BeliefState(storage)
            await bs.initialize()

            engine = ReasoningEngine(fabric, bs, db_path=rdb_path)
            await engine.initialize()

            # Build chain: Cat IS_A Mammal, Mammal IS_A Animal
            # Should infer: Cat IS_A Animal
            cat = Concept(name="Cat", concept_type=ConceptType.CONCRETE)
            mammal = Concept(name="Mammal", concept_type=ConceptType.ABSTRACT)
            animal = Concept(name="Animal", concept_type=ConceptType.ABSTRACT)

            await fabric.add_concept(cat)
            await fabric.add_concept(mammal)
            await fabric.add_concept(animal)

            r1 = Relationship(
                source_concept_id=cat.id,
                target_concept_id=mammal.id,
                relationship_type=RelationshipType.IS_A,
                confidence=0.95,
            )
            r2 = Relationship(
                source_concept_id=mammal.id,
                target_concept_id=animal.id,
                relationship_type=RelationshipType.IS_A,
                confidence=0.95,
            )
            await fabric.add_relationship(r1)
            await fabric.add_relationship(r2)

            # Run inference from cat
            results = await engine.infer_relationships(cat.id, max_depth=3)
            assert len(results) > 0

            # Check for transitive inference Cat → Animal
            transitive_results = [r for r in results if r.inference_type == InferenceType.TRANSITIVITY]
            assert len(transitive_results) >= 1, "Should infer Cat IS_A Animal via transitivity"

            # Verify the inferred relationship mentions Cat and Animal
            cat_animal = [r for r in transitive_results if r.conclusion_concept_id == animal.id]
            assert len(cat_animal) >= 1, "Should infer Cat → Animal"
            assert cat_animal[0].confidence > 0
            assert cat_animal[0].confidence < 1.0  # Should be decayed from 0.95

            await engine.close()

        finally:
            await storage.close()
            os.unlink(rdb_path)


# ═══════════════════════════════════════════════════════════════════════════════
# Criterion 8: Kernel updates Cognitive State after every session
# ═══════════════════════════════════════════════════════════════════════════════

class TestKernelCognitiveStateUpdate:
    """Integration test: Kernel updates Cognitive State after every session."""

    @pytest.mark.asyncio
    async def test_kernel_updates_cognitive_state(self, db_path):
        """Process query, verify cognitive state is updated."""
        kernel = CognitiveKernel(db_path=db_path)
        await kernel.initialize()

        try:
            # Check initial state
            initial_state = await kernel._cognitive_state.get_state()
            initial_sessions = initial_state.session_count

            # Process a query
            request = QueryRequest(query="What is machine learning?")
            response = await kernel.process_query(request)

            assert response.session_id is not None
            assert response.final_synthesis is not None

            # Verify cognitive state was updated
            updated_state = await kernel._cognitive_state.get_state()
            assert updated_state.session_count == initial_sessions + 1, \
                "Session count should increment after processing a query"
            assert updated_state.last_query == "What is machine learning?"

            # Verify snapshot reflects changes
            snapshot = await kernel._cognitive_state.get_snapshot()
            assert snapshot["session_count"] >= 1

        finally:
            await kernel.shutdown()

    @pytest.mark.asyncio
    async def test_kernel_cognitive_state_persists(self, db_path):
        """Cognitive state persists across kernel restarts."""
        # Session 1
        kernel1 = CognitiveKernel(db_path=db_path)
        await kernel1.initialize()

        try:
            await kernel1.process_query(QueryRequest(query="Remember: ACOS has cognitive state"))
        finally:
            await kernel1.shutdown()

        # Session 2 — new kernel instance, same DB
        kernel2 = CognitiveKernel(db_path=db_path)
        await kernel2.initialize()

        try:
            state = await kernel2._cognitive_state.get_state()
            assert state.session_count >= 1, "Cognitive state should persist across kernel restarts"

            # Process another query
            await kernel2.process_query(QueryRequest(query="What do you know?"))
            state2 = await kernel2._cognitive_state.get_state()
            assert state2.session_count >= 2
        finally:
            await kernel2.shutdown()
