"""
Unit tests for ACOS Runtime v0.2 cognitive modules.

Tests each module in isolation:
- KnowledgeFabric
- BeliefState
- GoalManager
- CognitiveStateEngine
- SemanticMemory
- KnowledgeConsolidator
- ReasoningEngine
"""

import os
import tempfile

import pytest

from acos.memory.store import StorageBackend
from acos.memory.manager import MemoryManager
from acos.schemas.v2_models import (
    Concept,
    ConceptType,
    Entity,
    Relationship,
    RelationshipType,
    Belief,
    BeliefStatus,
    Evidence,
    Goal,
    GoalPriority,
    GoalStatus,
    CognitiveState,
)
from acos.schemas.models import MemoryRecord, MemoryType
from acos.cognitive.knowledge_fabric import KnowledgeFabric
from acos.cognitive.belief_system import BeliefState
from acos.cognitive.goal_system import GoalManager
from acos.cognitive.cognitive_state import CognitiveStateEngine
from acos.cognitive.semantic_memory import SemanticMemory
from acos.cognitive.knowledge_consolidator import KnowledgeConsolidator
from acos.cognitive.reasoning_engine import ReasoningEngine


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def db_path():
    """Create a temporary database path for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
async def storage(db_path):
    """Create and initialise a StorageBackend for testing."""
    s = StorageBackend(db_path=db_path)
    await s.initialize()
    yield s
    await s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# KnowledgeFabric
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeFabric:
    """Unit tests for KnowledgeFabric."""

    @pytest.mark.asyncio
    async def test_extract_concepts(self, storage):
        """extract_concepts extracts from text."""
        fabric = KnowledgeFabric(storage)
        await fabric.initialize()

        concepts = fabric.extract_concepts(
            '"Machine Learning" is a method for training models using Python.'
        )
        assert len(concepts) > 0
        # Quoted phrase should appear
        names = [c.name.lower() for c in concepts]
        assert any("machine learning" in n for n in names)

    @pytest.mark.asyncio
    async def test_extract_entities(self, storage):
        """extract_entities extracts named entities."""
        fabric = KnowledgeFabric(storage)
        await fabric.initialize()

        entities = fabric.extract_entities(
            'Dr. Alan Turing used Python 3.12 on 2024-01-15 and measured 100 ms.'
        )
        assert len(entities) > 0
        etypes = {e.entity_type for e in entities}
        # Should find at least a technology and a date/quantity entity
        assert len(etypes) > 0

    @pytest.mark.asyncio
    async def test_add_and_get_concept(self, storage):
        """add_concept / get_concept round-trip."""
        fabric = KnowledgeFabric(storage)
        await fabric.initialize()

        concept = Concept(name="Python", concept_type=ConceptType.CONCRETE, description="A language")
        added = await fabric.add_concept(concept)
        assert added.id == concept.id

        retrieved = await fabric.get_concept(concept.id)
        assert retrieved is not None
        assert retrieved.name == "Python"
        assert retrieved.access_count >= 1  # get_concept bumps access_count

    @pytest.mark.asyncio
    async def test_find_concept_by_name(self, storage):
        """find_concept_by_name resolves with fuzzy matching."""
        fabric = KnowledgeFabric(storage)
        await fabric.initialize()

        concept = Concept(name="Quantum Computing", concept_type=ConceptType.ABSTRACT)
        await fabric.add_concept(concept)

        # Exact match
        found = await fabric.find_concept_by_name("Quantum Computing")
        assert found is not None
        assert found.id == concept.id

        # Partial match
        found_partial = await fabric.find_concept_by_name("quantum")
        assert found_partial is not None

    @pytest.mark.asyncio
    async def test_add_and_get_relationships(self, storage):
        """add_relationship / get_relationships round-trip."""
        fabric = KnowledgeFabric(storage)
        await fabric.initialize()

        c1 = Concept(name="Python", concept_type=ConceptType.CONCRETE)
        c2 = Concept(name="Programming Language", concept_type=ConceptType.ABSTRACT)
        await fabric.add_concept(c1)
        await fabric.add_concept(c2)

        rel = Relationship(
            source_concept_id=c1.id,
            target_concept_id=c2.id,
            relationship_type=RelationshipType.IS_A,
            description="Python is a programming language",
        )
        await fabric.add_relationship(rel)

        rels = fabric.get_relationships(c1.id)
        assert len(rels) >= 1
        assert any(r.relationship_type == RelationshipType.IS_A for r in rels)

    @pytest.mark.asyncio
    async def test_semantic_search(self, storage):
        """semantic_search returns results matching query."""
        fabric = KnowledgeFabric(storage)
        await fabric.initialize()

        concept = Concept(name="Neural Networks", concept_type=ConceptType.ABSTRACT, description="Deep learning architecture")
        await fabric.add_concept(concept)

        results = await fabric.semantic_search("neural")
        assert len(results) > 0
        # Results are (Concept, score) tuples
        found_names = [c.name for c, _score in results]
        assert "Neural Networks" in found_names

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns proper structure."""
        fabric = KnowledgeFabric(storage)
        await fabric.initialize()

        c = Concept(name="Test", concept_type=ConceptType.ABSTRACT)
        await fabric.add_concept(c)

        stats = fabric.get_stats()
        assert "total_concepts" in stats
        assert "total_entities" in stats
        assert "total_relationships" in stats
        assert "concept_type_distribution" in stats
        assert "relationship_type_distribution" in stats
        assert stats["total_concepts"] >= 1

    @pytest.mark.asyncio
    async def test_extract_relationships(self, storage):
        """extract_relationships detects relationships from text."""
        fabric = KnowledgeFabric(storage)
        await fabric.initialize()

        concepts = [
            Concept(name="Python", concept_type=ConceptType.CONCRETE),
            Concept(name="Language", concept_type=ConceptType.ABSTRACT),
        ]
        rels = fabric.extract_relationships("Python is a Language", concepts)
        # Should detect at least a co-occurrence or is_a relationship
        assert len(rels) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# BeliefState
# ═══════════════════════════════════════════════════════════════════════════════

class TestBeliefState:
    """Unit tests for BeliefState."""

    @pytest.mark.asyncio
    async def test_add_belief(self, storage):
        """add_belief creates new beliefs."""
        bs = BeliefState(storage)
        await bs.initialize()

        belief = await bs.add_belief("Python is the best language", confidence=0.8)
        assert belief.id is not None
        assert belief.statement == "Python is the best language"
        assert belief.confidence == 0.8
        assert belief.status == BeliefStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_update_confidence(self, storage):
        """update_confidence adjusts scores."""
        bs = BeliefState(storage)
        await bs.initialize()

        belief = await bs.add_belief("Test belief", confidence=0.7)
        updated = await bs.update_confidence(belief.id, -0.3)
        assert abs(updated.confidence - 0.4) < 0.01
        assert updated.version == 2
        assert updated.parent_belief_id == belief.id

    @pytest.mark.asyncio
    async def test_add_supporting_evidence(self, storage):
        """add_evidence with supporting evidence increases confidence."""
        bs = BeliefState(storage)
        await bs.initialize()

        belief = await bs.add_belief("The sky is blue", confidence=0.5)
        evidence = Evidence(content="Observation on clear day", evidence_type="supporting", confidence=0.9)
        updated = await bs.add_evidence(belief.id, evidence)
        assert updated.confidence > 0.5
        assert len(updated.supporting_evidence) == 1

    @pytest.mark.asyncio
    async def test_add_contradicting_evidence(self, storage):
        """add_evidence with contradicting evidence decreases confidence."""
        bs = BeliefState(storage)
        await bs.initialize()

        belief = await bs.add_belief("The sky is green", confidence=0.7)
        evidence = Evidence(content="Scientific measurement", evidence_type="contradicting", confidence=0.9)
        updated = await bs.add_evidence(belief.id, evidence)
        assert updated.confidence < 0.7
        assert len(updated.contradicting_evidence) == 1

    @pytest.mark.asyncio
    async def test_find_contradictions(self, storage):
        """find_contradictions detects conflicting beliefs."""
        bs = BeliefState(storage)
        await bs.initialize()

        await bs.add_belief("This is the best approach", confidence=0.8)
        await bs.add_belief("This is the worst approach", confidence=0.7)

        contradictions = await bs.find_contradictions()
        assert len(contradictions) >= 1
        # Each contradiction is (b1, b2, reason)
        _b1, _b2, reason = contradictions[0]
        assert "best" in reason.lower() or "worst" in reason.lower() or "opposite" in reason.lower()

    @pytest.mark.asyncio
    async def test_evolve_belief(self, storage):
        """evolve_belief creates new version."""
        bs = BeliefState(storage)
        await bs.initialize()

        belief = await bs.add_belief("Old statement", confidence=0.5)
        evolved = await bs.evolve_belief(belief.id, "New statement", 0.8, reason="New evidence")
        assert evolved.statement == "New statement"
        assert evolved.confidence == 0.8
        assert evolved.parent_belief_id == belief.id
        assert evolved.version == 2

        # Old belief should be superseded
        old = await bs.get_belief(belief.id)
        assert old is not None
        assert old.status == BeliefStatus.SUPERSEDED

    @pytest.mark.asyncio
    async def test_get_active_beliefs(self, storage):
        """get_active_beliefs returns only active beliefs."""
        bs = BeliefState(storage)
        await bs.initialize()

        # Use very different statements to avoid similarity-based merging
        b1 = await bs.add_belief("The sky is blue on clear days", confidence=0.7)
        b2 = await bs.add_belief("Python supports object-oriented programming", confidence=0.6)

        active = await bs.get_active_beliefs()
        assert len(active) >= 2
        assert all(b.status == BeliefStatus.ACTIVE for b in active)

    @pytest.mark.asyncio
    async def test_get_weakened_beliefs(self, storage):
        """get_weakened_beliefs returns weakened beliefs."""
        bs = BeliefState(storage)
        await bs.initialize()

        belief = await bs.add_belief("Will be weakened", confidence=0.3)
        # Lower confidence below 0.2 to trigger WEAKENED status
        # update_confidence creates a new version, so old one becomes SUPERSEDED
        weakened = await bs.update_confidence(belief.id, -0.15)
        # new confidence = 0.15, which is < 0.2 => WEAKENED
        assert weakened.status == BeliefStatus.WEAKENED

        weakened_list = await bs.get_weakened_beliefs()
        assert len(weakened_list) >= 1

    @pytest.mark.asyncio
    async def test_add_belief_with_evidence(self, storage):
        """add_belief with initial evidence."""
        bs = BeliefState(storage)
        await bs.initialize()

        evidence = Evidence(content="Initial proof", evidence_type="supporting", confidence=0.9)
        belief = await bs.add_belief(
            "Test with evidence",
            confidence=0.6,
            supporting_evidence=[evidence],
        )
        assert len(belief.supporting_evidence) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# GoalManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoalManager:
    """Unit tests for GoalManager."""

    @pytest.mark.asyncio
    async def test_create_goal(self, storage):
        """create_goal creates a new goal."""
        gm = GoalManager(storage)
        await gm.initialize()

        goal = await gm.create_goal("Build the belief system", priority=GoalPriority.HIGH)
        assert goal.id is not None
        assert goal.description == "Build the belief system"
        assert goal.priority == GoalPriority.HIGH
        assert goal.status == GoalStatus.ACTIVE
        assert goal.progress == 0.0

    @pytest.mark.asyncio
    async def test_update_progress(self, storage):
        """update_progress adjusts goal progress."""
        gm = GoalManager(storage)
        await gm.initialize()

        goal = await gm.create_goal("Test goal", priority=GoalPriority.NORMAL)
        updated = await gm.update_progress(goal.id, 0.5)
        assert updated.progress == 0.5

    @pytest.mark.asyncio
    async def test_complete_goal(self, storage):
        """complete_goal marks goal as completed."""
        gm = GoalManager(storage)
        await gm.initialize()

        goal = await gm.create_goal("Test goal")
        completed = await gm.complete_goal(goal.id)
        assert completed.status == GoalStatus.COMPLETED
        assert completed.progress == 1.0
        assert completed.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_progress_auto_completes(self, storage):
        """update_progress auto-completes at progress=1.0."""
        gm = GoalManager(storage)
        await gm.initialize()

        goal = await gm.create_goal("Auto-complete test")
        updated = await gm.update_progress(goal.id, 1.0)
        assert updated.status == GoalStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_abandon_goal_cascades(self, storage):
        """abandon_goal cascades to subgoals."""
        gm = GoalManager(storage)
        await gm.initialize()

        parent = await gm.create_goal("Parent goal")
        sub1 = await gm.create_goal("Subgoal 1", parent_goal_id=parent.id)
        sub2 = await gm.create_goal("Subgoal 2", parent_goal_id=parent.id)

        # Verify subgoals are linked
        parent_check = await gm.get_goal(parent.id)
        assert len(parent_check.subgoal_ids) == 2

        # Abandon parent — subgoals should also be abandoned
        await gm.abandon_goal(parent.id)

        for sid in [sub1.id, sub2.id]:
            sub = await gm.get_goal(sid)
            assert sub.status == GoalStatus.ABANDONED

    @pytest.mark.asyncio
    async def test_decompose_goal(self, storage):
        """decompose_goal creates subgoals."""
        gm = GoalManager(storage)
        await gm.initialize()

        parent = await gm.create_goal("Build system", priority=GoalPriority.HIGH)
        subgoals = await gm.decompose_goal(parent.id, ["Design", "Implement", "Test"])

        assert len(subgoals) == 3
        for sg in subgoals:
            assert sg.parent_goal_id == parent.id
            assert sg.status == GoalStatus.ACTIVE

        # Subgoals should be sequential (each depends on previous)
        assert len(subgoals[1].dependency_ids) == 1
        assert subgoals[1].dependency_ids[0] == subgoals[0].id

    @pytest.mark.asyncio
    async def test_get_next_actionable_goals(self, storage):
        """get_next_actionable_goals returns goals with met dependencies."""
        gm = GoalManager(storage)
        await gm.initialize()

        # Goal with no dependencies — should be actionable
        g1 = await gm.create_goal("No-dep goal", priority=GoalPriority.HIGH)
        actionable = await gm.get_next_actionable_goals()
        assert any(g.id == g1.id for g in actionable)

        # Goal with unmet dependency — should NOT be actionable
        g2 = await gm.create_goal("Dependent goal", dependency_ids=[g1.id])
        actionable = await gm.get_next_actionable_goals()
        assert not any(g.id == g2.id for g in actionable)

        # Complete g1 → g2 should now be actionable
        await gm.complete_goal(g1.id)
        actionable = await gm.get_next_actionable_goals()
        assert any(g.id == g2.id for g in actionable)


# ═══════════════════════════════════════════════════════════════════════════════
# CognitiveStateEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestCognitiveStateEngine:
    """Unit tests for CognitiveStateEngine."""

    @pytest.mark.asyncio
    async def test_get_state_and_save(self, storage):
        """get_state / save round-trip."""
        engine = CognitiveStateEngine(storage)
        await engine.initialize()

        state = await engine.get_state()
        assert state is not None
        assert state.id is not None

        # Modify and save
        state.overall_confidence = 0.75
        await engine.save()

        # Re-read
        state2 = await engine.get_state()
        assert state2.overall_confidence == 0.75

    @pytest.mark.asyncio
    async def test_update_beliefs(self, storage):
        """update_beliefs syncs active beliefs into cognitive state."""
        engine = CognitiveStateEngine(storage)
        await engine.initialize()

        belief = Belief(statement="Test belief", confidence=0.7, status=BeliefStatus.ACTIVE)
        await engine.update_beliefs([belief])

        state = await engine.get_state()
        assert len(state.beliefs) == 1
        assert state.beliefs[0].statement == "Test belief"

    @pytest.mark.asyncio
    async def test_update_goals(self, storage):
        """update_goals syncs active goals into cognitive state."""
        engine = CognitiveStateEngine(storage)
        await engine.initialize()

        goal = Goal(description="Test goal", status=GoalStatus.ACTIVE)
        await engine.update_goals([goal])

        state = await engine.get_state()
        assert len(state.goals) == 1
        assert state.goals[0].description == "Test goal"

    @pytest.mark.asyncio
    async def test_begin_and_end_session(self, storage):
        """begin_session / end_session update tracking."""
        engine = CognitiveStateEngine(storage)
        await engine.initialize()

        await engine.begin_session("What is ACOS?")
        state = await engine.get_state()
        assert state.session_count == 1
        assert state.last_query == "What is ACOS?"

        await engine.end_session("ACOS is a cognitive OS", 0.85)
        state = await engine.get_state()
        assert state.last_synthesis is not None
        assert state.overall_confidence == 0.85
        assert state.active_thread_ids == []

    @pytest.mark.asyncio
    async def test_get_snapshot(self, storage):
        """get_snapshot returns structured dict."""
        engine = CognitiveStateEngine(storage)
        await engine.initialize()

        snapshot = await engine.get_snapshot()
        assert "state_id" in snapshot
        assert "active_beliefs" in snapshot
        assert "active_goals" in snapshot
        assert "overall_confidence" in snapshot
        assert "session_count" in snapshot

    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """get_stats returns proper structure."""
        engine = CognitiveStateEngine(storage)
        await engine.initialize()

        stats = await engine.get_stats()
        assert "session_count" in stats
        assert "active_beliefs" in stats
        assert "active_goals" in stats
        assert "knowledge_concepts" in stats
        assert "overall_confidence" in stats

    @pytest.mark.asyncio
    async def test_uncertainty_tracking(self, storage):
        """Uncertainty estimates can be set and retrieved."""
        engine = CognitiveStateEngine(storage)
        await engine.initialize()

        await engine.update_uncertainty("quantum physics", 0.9)
        u = await engine.get_uncertainty("quantum physics")
        assert u == 0.9

    @pytest.mark.asyncio
    async def test_knowledge_concept_tracking(self, storage):
        """Knowledge graph concept references can be managed."""
        engine = CognitiveStateEngine(storage)
        await engine.initialize()

        await engine.add_knowledge_concept("concept-123")
        state = await engine.get_state()
        assert "concept-123" in state.knowledge_graph_concept_ids


# ═══════════════════════════════════════════════════════════════════════════════
# SemanticMemory
# ═══════════════════════════════════════════════════════════════════════════════

class TestSemanticMemory:
    """Unit tests for SemanticMemory."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_concept(self, storage):
        """store_concept / retrieve_concept round-trip."""
        sem = SemanticMemory(storage)
        await sem.initialize()

        concept = Concept(name="Python", concept_type=ConceptType.CONCRETE, description="A programming language")
        await sem.store_concept(concept)

        retrieved = await sem.retrieve_concept(concept.id)
        assert retrieved is not None
        assert retrieved.name == "Python"

    @pytest.mark.asyncio
    async def test_store_relationship(self, storage):
        """store_relationship persists a relationship."""
        sem = SemanticMemory(storage)
        await sem.initialize()

        c1 = Concept(name="A", concept_type=ConceptType.ABSTRACT)
        c2 = Concept(name="B", concept_type=ConceptType.ABSTRACT)
        await sem.store_concept(c1)
        await sem.store_concept(c2)

        rel = Relationship(
            source_concept_id=c1.id,
            target_concept_id=c2.id,
            relationship_type=RelationshipType.IS_A,
        )
        await sem.store_relationship(rel)

        rels = await sem.get_relationships(c1.id)
        assert len(rels) >= 1
        assert rels[0].relationship_type == RelationshipType.IS_A

    @pytest.mark.asyncio
    async def test_semantic_query(self, storage):
        """semantic_query returns matching concepts."""
        sem = SemanticMemory(storage)
        await sem.initialize()

        concept = Concept(name="Deep Learning", concept_type=ConceptType.PROCESS, description="Neural network training")
        await sem.store_concept(concept)

        result = await sem.semantic_query("deep learning")
        assert result.total_matches >= 1
        assert len(result.concepts) >= 1

    @pytest.mark.asyncio
    async def test_get_related_concepts(self, storage):
        """get_related_concepts finds concepts via relationships."""
        sem = SemanticMemory(storage)
        await sem.initialize()

        c1 = Concept(name="Python", concept_type=ConceptType.CONCRETE)
        c2 = Concept(name="Programming", concept_type=ConceptType.ABSTRACT)
        await sem.store_concept(c1)
        await sem.store_concept(c2)

        await sem.link_concepts(c1.id, c2.id, RelationshipType.IS_A)

        related = await sem.get_related_concepts(c1.id, max_depth=2)
        assert len(related) >= 1
        # related is list of (Concept, distance)
        related_ids = [c.id for c, _dist in related]
        assert c2.id in related_ids

    @pytest.mark.asyncio
    async def test_retrieve_concept_by_name(self, storage):
        """retrieve_concept_by_name finds concepts by name."""
        sem = SemanticMemory(storage)
        await sem.initialize()

        concept = Concept(name="Transformer", concept_type=ConceptType.PROCESS)
        await sem.store_concept(concept)

        found = await sem.retrieve_concept_by_name("Transformer", fuzzy=False)
        assert len(found) >= 1
        assert found[0].name == "Transformer"

        found_fuzzy = await sem.retrieve_concept_by_name("trans", fuzzy=True)
        assert len(found_fuzzy) >= 1

    @pytest.mark.asyncio
    async def test_link_concepts(self, storage):
        """link_concepts creates a relationship between two concepts."""
        sem = SemanticMemory(storage)
        await sem.initialize()

        c1 = Concept(name="Cat", concept_type=ConceptType.CONCRETE)
        c2 = Concept(name="Animal", concept_type=ConceptType.ABSTRACT)
        await sem.store_concept(c1)
        await sem.store_concept(c2)

        rel = await sem.link_concepts(c1.id, c2.id, RelationshipType.IS_A, "A cat is an animal")
        assert rel is not None
        assert rel.relationship_type == RelationshipType.IS_A


# ═══════════════════════════════════════════════════════════════════════════════
# KnowledgeConsolidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeConsolidator:
    """Unit tests for KnowledgeConsolidator."""

    @pytest.mark.asyncio
    async def test_consolidate_session(self, storage):
        """consolidate_session with episodic memories."""
        # Set up all required subsystems
        fabric = KnowledgeFabric(storage)
        await fabric.initialize()

        bs = BeliefState(storage)
        await bs.initialize()

        sem = SemanticMemory(storage)
        await sem.initialize()

        mm = MemoryManager(storage)

        consolidator = KnowledgeConsolidator(fabric, bs, sem, mm)

        # Store some episodic memories
        await mm.store_episodic("thread-1", "Python is a programming language used for machine learning.")
        await mm.store_episodic("thread-1", "Neural networks achieve high accuracy on image classification.")

        result = await consolidator.consolidate_session(
            session_id="test-session-1",
            thread_ids=["thread-1"],
            session_summary="Explored Python and machine learning concepts.",
        )

        # Verify ConsolidationResult
        assert result is not None
        assert result.consolidation_time_ms > 0
        # At least some concepts should have been extracted
        assert result.concepts_extracted + result.semantic_entries_created > 0


# ═══════════════════════════════════════════════════════════════════════════════
# ReasoningEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestReasoningEngine:
    """Unit tests for ReasoningEngine."""

    @pytest.mark.asyncio
    async def test_infer_relationships(self, storage):
        """infer_relationships discovers transitive inferences."""
        fabric = KnowledgeFabric(storage)
        await fabric.initialize()

        bs = BeliefState(storage)
        await bs.initialize()

        # Use temp DB for reasoning engine
        fd, rdb_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            engine = ReasoningEngine(fabric, bs, db_path=rdb_path)
            await engine.initialize()

            # Create A → B → C chain with IS_A
            a = Concept(name="Mammal", concept_type=ConceptType.ABSTRACT)
            b = Concept(name="Animal", concept_type=ConceptType.ABSTRACT)
            c = Concept(name="Living Thing", concept_type=ConceptType.ABSTRACT)
            await fabric.add_concept(a)
            await fabric.add_concept(b)
            await fabric.add_concept(c)

            r1 = Relationship(source_concept_id=a.id, target_concept_id=b.id, relationship_type=RelationshipType.IS_A, confidence=0.9)
            r2 = Relationship(source_concept_id=b.id, target_concept_id=c.id, relationship_type=RelationshipType.IS_A, confidence=0.9)
            await fabric.add_relationship(r1)
            await fabric.add_relationship(r2)

            results = await engine.infer_relationships(a.id, max_depth=3)
            assert len(results) > 0
            # Should infer transitive A → C
            transitive = [r for r in results if r.inference_type == InferenceType.TRANSITIVITY]
            assert len(transitive) >= 1, "Should infer transitive relationship A→C"

            await engine.close()
        finally:
            os.unlink(rdb_path)

    @pytest.mark.asyncio
    async def test_detect_contradictions(self, storage):
        """detect_contradictions finds conflicting beliefs."""
        fabric = KnowledgeFabric(storage)
        await fabric.initialize()

        bs = BeliefState(storage)
        await bs.initialize()

        fd, rdb_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            engine = ReasoningEngine(fabric, bs, db_path=rdb_path)
            await engine.initialize()

            # Create contradictory beliefs
            await bs.add_belief("This is the best approach", confidence=0.8)
            await bs.add_belief("This is the worst approach", confidence=0.7)

            contradictions = await engine.detect_contradictions()
            assert len(contradictions) >= 1

            await engine.close()
        finally:
            os.unlink(rdb_path)

    @pytest.mark.asyncio
    async def test_discover_knowledge_gaps(self, storage):
        """discover_knowledge_gaps identifies isolated concepts."""
        fabric = KnowledgeFabric(storage)
        await fabric.initialize()

        bs = BeliefState(storage)
        await bs.initialize()

        fd, rdb_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            engine = ReasoningEngine(fabric, bs, db_path=rdb_path)
            await engine.initialize()

            # Add an isolated concept (no relationships)
            c = Concept(name="IsolatedTopic", concept_type=ConceptType.ABSTRACT)
            await fabric.add_concept(c)

            gaps = await engine.discover_knowledge_gaps()
            assert len(gaps) >= 1
            # At least one gap should mention the isolated concept
            assert any("IsolatedTopic" in g.description or "isolated" in g.description.lower() for g in gaps)

            await engine.close()
        finally:
            os.unlink(rdb_path)


# Need to import InferenceType for the test
from acos.schemas.v2_models import InferenceType
