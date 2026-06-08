#!/usr/bin/env python3
"""
Seed ACOS SQLite database with rich, realistic ACOS-specific cognitive data.

Uses aiosqlite to connect to /home/z/my-project/acos-runtime/data/acos.db,
clears existing data, and inserts fresh cognitive data including:
- 24 concepts (HBTA, OTM, Cognitive Kernel, Stiefel Manifold, etc.)
- 30+ relationships between concepts
- 10 entities (Llama-3-8B, PyTorch, CUDA, etc.)
- 8 beliefs with supporting and contradicting evidence
- 6+ goals with subgoals and dependencies
- 1 cognitive state record
- Semantic concepts and relationships for key ACOS concepts

Usage:
    python3 seed_cognitive_data.py
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

# ─── Configuration ────────────────────────────────────────────────────────────

DB_PATH = Path(__file__).parent / "data" / "acos.db"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _gen_id() -> str:
    return str(uuid.uuid4())


def _ts() -> str:
    """ISO-format timestamp for right now."""
    return _utc_now().isoformat()


# ─── Data Definitions ─────────────────────────────────────────────────────────

CONCEPTS = [
    # (name, concept_type, description, properties, confidence)
    ("HBTA", "process", "Hierarchical Binary Tree Attention — O(Nd^2 log N) attention mechanism using binary tree decomposition",
     '{"complexity": "O(Nd^2 log N)", "paper_section": "3", "theorem": "3.4"}', 0.92),
    ("OTM", "process", "Orthogonal Thread Memory — zero-interference multi-thread memory via Stiefel manifold parameterization",
     '{"interference": "zero (exact arithmetic)", "paper_section": "4", "theorem": "4.4"}', 0.90),
    ("Cognitive Kernel", "abstract", "Central orchestrator of the ACOS cognitive architecture managing threads, memory, and reasoning",
     '{"components": ["ThreadScheduler", "MemoryManager", "ModelRouter"], "paper_section": "2"}', 0.88),
    ("Stiefel Manifold", "abstract", "Mathematical manifold of orthonormal frames — basis for OTM parameterization",
     '{"dimension": "St(n, k)", "paper_section": "4.2"}', 0.95),
    ("Cayley Retraction", "process", "Efficient retraction map on the Stiefel manifold preserving orthogonality during gradient updates",
     '{"cost": "O(nk^2)", "paper_section": "4.3", "theorem": "4.4"}', 0.91),
    ("Meta-Controller", "abstract", "Top-level controller with local Lyapunov stability governing cognitive resource allocation",
     '{"stability": "local Lyapunov", "paper_section": "5", "theorem": "5.3"}', 0.85),
    ("Pingala Gating", "process", "Neuromodulatory gating mechanism inspired by Pingala's binary meter controlling gradient flow",
     '{"inspired_by": "Pingala Chandahsutra", "paper_section": "6.2"}', 0.78),
    ("Panini Constraints", "process", "Structural production rules inspired by Panini's grammar constraining architectural search space",
     '{"inspired_by": "Panini Ashtadhyayi", "paper_section": "6.1"}', 0.80),
    ("Nyaya Verifier", "process", "Formal logic verification engine inspired by Nyaya school's inference framework",
     '{"inspired_by": "Nyaya Sutras", "paper_section": "6.3"}', 0.72),
    ("Knowledge Fabric", "abstract", "Layer-2 knowledge graph connecting concepts, entities, and relationships for retrieval",
     '{"layer": 2, "paper_section": "2"}', 0.87),
    ("Belief State", "abstract", "Probabilistic representation of what the system believes with confidence scores and evidence",
     '{"paper_section": "5.2"}', 0.83),
    ("Goal System", "abstract", "Prioritized objective tracking with dependencies, subgoals, and progress metrics",
     '{"paper_section": "5.1"}', 0.86),
    ("Semantic Memory", "abstract", "Long-term concept-based knowledge store with typed relationships and inference",
     '{"memory_type": "semantic", "paper_section": "7"}', 0.84),
    ("Knowledge Consolidation", "process", "Process of extracting concepts, entities, and relationships from episodic memory into semantic store",
     '{"trigger": "sleep_cycle", "paper_section": "7.3"}', 0.79),
    ("Reasoning Engine", "abstract", "Multi-strategy inference engine supporting deduction, induction, abduction, and analogy",
     '{"strategies": ["deduction", "induction", "abduction", "analogy"], "paper_section": "8"}', 0.81),
    ("Thread Scheduler", "abstract", "Component managing parallel reasoning threads with priority-based scheduling",
     '{"layer": 3, "paper_section": "2"}', 0.82),
    ("Memory Manager", "abstract", "Component managing OTM-backed hierarchical memory across working, episodic, and semantic stores",
     '{"layer": 4, "paper_section": "2"}', 0.83),
    ("Model Router", "abstract", "Three-level routing system for selecting optimal LLM based on task requirements",
     '{"routing_levels": 3, "paper_section": "9"}', 0.80),
    ("Reflection Engine", "abstract", "Self-review mechanism that critiques and improves reasoning outputs",
     '{"paper_section": "8.2"}', 0.77),
    ("Verification Engine", "abstract", "Fact-checking and consistency verification engine for reasoning outputs",
     '{"paper_section": "8.3"}', 0.76),
    ("Orthogonal Gradient Projection", "process", "Technique projecting gradients onto orthogonal complement to prevent catastrophic forgetting",
     '{"paper_section": "4.5"}', 0.82),
    ("Sleep Cycle Consolidation", "process", "Background process that consolidates episodic memories into semantic knowledge during idle periods",
     '{"trigger": "idle_threshold", "paper_section": "7.3"}', 0.75),
    ("FlashAttention", "process", "Memory-efficient attention approximation using tiling — baseline comparison for HBTA",
     '{"complexity": "O(N^2 d / M)", "paper_section": "3.1"}', 0.93),
    ("Lyapunov Stability", "property", "Mathematical property ensuring bounded divergence of the Meta-Controller under perturbations",
     '{"theorem": "5.3", "paper_section": "5.3"}', 0.88),
]

# Relationships: (source_name, target_name, relationship_type, description, confidence, weight)
RELATIONSHIPS = [
    ("HBTA", "FlashAttention", "depends_on", "HBTA builds on ideas from FlashAttention's memory-efficient tiling", 0.85, 1.0),
    ("HBTA", "Cognitive Kernel", "part_of", "HBTA is the attention layer within the Cognitive Kernel", 0.90, 1.2),
    ("OTM", "Stiefel Manifold", "depends_on", "OTM parameterizes thread memory on the Stiefel manifold", 0.92, 1.3),
    ("OTM", "Cayley Retraction", "depends_on", "OTM uses Cayley retraction for orthogonal gradient updates", 0.90, 1.2),
    ("Cognitive Kernel", "Meta-Controller", "part_of", "Cognitive Kernel is orchestrated by the Meta-Controller", 0.88, 1.0),
    ("Meta-Controller", "Lyapunov Stability", "has_property", "Meta-Controller has local Lyapunov stability", 0.82, 1.0),
    ("Pingala Gating", "Meta-Controller", "part_of", "Pingala gating is a mechanism within the Meta-Controller", 0.80, 1.0),
    ("Panini Constraints", "Meta-Controller", "part_of", "Panini constraints govern the Meta-Controller's search space", 0.78, 0.9),
    ("Nyaya Verifier", "Verification Engine", "is_a", "Nyaya Verifier is a specialized type of verification engine", 0.75, 1.0),
    ("Knowledge Fabric", "Semantic Memory", "relates_to", "Knowledge Fabric is implemented via Semantic Memory", 0.85, 1.1),
    ("Belief State", "Knowledge Fabric", "depends_on", "Belief State relies on Knowledge Fabric for concept evidence", 0.82, 1.0),
    ("Goal System", "Meta-Controller", "depends_on", "Goal System is managed by the Meta-Controller", 0.80, 1.0),
    ("Knowledge Consolidation", "Sleep Cycle Consolidation", "is_a", "Knowledge Consolidation is triggered by Sleep Cycle Consolidation", 0.78, 0.9),
    ("Knowledge Consolidation", "Semantic Memory", "depends_on", "Knowledge Consolidation writes to Semantic Memory", 0.85, 1.1),
    ("Reasoning Engine", "Belief State", "depends_on", "Reasoning Engine updates Belief State with inference results", 0.80, 1.0),
    ("Reasoning Engine", "Knowledge Fabric", "depends_on", "Reasoning Engine queries Knowledge Fabric for context", 0.82, 1.0),
    ("Thread Scheduler", "Cognitive Kernel", "part_of", "Thread Scheduler is a core component of the Cognitive Kernel", 0.88, 1.2),
    ("Memory Manager", "Cognitive Kernel", "part_of", "Memory Manager is a core component of the Cognitive Kernel", 0.88, 1.2),
    ("Memory Manager", "OTM", "depends_on", "Memory Manager uses OTM for thread-isolated memory", 0.90, 1.3),
    ("Model Router", "Cognitive Kernel", "part_of", "Model Router is part of the Cognitive Kernel's orchestration layer", 0.82, 1.0),
    ("Reflection Engine", "Reasoning Engine", "relates_to", "Reflection Engine critiques outputs from the Reasoning Engine", 0.78, 0.9),
    ("Verification Engine", "Reasoning Engine", "relates_to", "Verification Engine checks Reasoning Engine outputs for consistency", 0.80, 1.0),
    ("Orthogonal Gradient Projection", "Stiefel Manifold", "depends_on", "Orthogonal Gradient Projection operates on the Stiefel manifold", 0.85, 1.1),
    ("Orthogonal Gradient Projection", "OTM", "supports", "Orthogonal Gradient Projection prevents catastrophic forgetting in OTM threads", 0.82, 1.0),
    ("Sleep Cycle Consolidation", "Memory Manager", "depends_on", "Sleep Cycle Consolidation is coordinated by the Memory Manager", 0.75, 0.9),
    ("Pingala Gating", "Orthogonal Gradient Projection", "supports", "Pingala gating modulates gradient flow for orthogonal projection", 0.72, 0.8),
    ("Panini Constraints", "Pingala Gating", "precedes", "Panini constraints define the structure before Pingala gating is applied", 0.70, 0.8),
    ("FlashAttention", "HBTA", "similar_to", "FlashAttention and HBTA are both efficient attention mechanisms", 0.75, 0.7),
    ("Nyaya Verifier", "Reflection Engine", "relates_to", "Nyaya Verifier provides formal logic to the Reflection Engine", 0.73, 0.8),
    ("Belief State", "Goal System", "relates_to", "Belief State informs Goal System priorities", 0.70, 0.8),
]

# Entities: (name, entity_type, description, mentions, confidence, concept_id_reference)
ENTITIES = [
    ("Llama-3-8B", "technology", "Meta's 8B parameter language model — target model for ACOS wrapping", 15, 0.95, "Cognitive Kernel"),
    ("PyTorch", "technology", "Deep learning framework used for implementing HBTA and OTM layers", 12, 0.97, "HBTA"),
    ("CUDA", "technology", "NVIDIA GPU compute platform for kernel optimization", 8, 0.94, "OTM"),
    ("ACOS v0.2", "technology", "Current version of the ACOS cognitive architecture runtime", 20, 0.90, "Cognitive Kernel"),
    ("FastAPI", "technology", "Python web framework used for ACOS REST API server", 6, 0.88, "Model Router"),
    ("SQLite", "technology", "Embedded database used for ACOS persistent storage", 10, 0.92, "Knowledge Fabric"),
    ("NetworkX", "technology", "Python graph library used for in-memory knowledge graph traversal", 7, 0.85, "Knowledge Fabric"),
    ("Ollama", "technology", "Local LLM inference runtime for running models like Llama-3-8B", 9, 0.87, "Model Router"),
    ("Qdrant", "technology", "Vector similarity search engine for semantic memory retrieval", 5, 0.80, "Semantic Memory"),
    ("aiosqlite", "technology", "Async SQLite adapter used throughout ACOS for non-blocking DB access", 8, 0.90, "Knowledge Fabric"),
]

# Beliefs: (statement, confidence, status, supporting_evidence, contradicting_evidence)
BELIEFS = [
    {
        "statement": "HBTA achieves O(Nd^2 log N) complexity",
        "confidence": 0.85,
        "status": "active",
        "supporting": [
            {"content": "Theorem 3.4 proves the complexity bound under standard assumptions", "confidence": 0.92},
            {"content": "Empirical benchmarks on sequence lengths 512-32768 confirm scaling", "confidence": 0.80},
        ],
        "contradicting": [
            {"content": "Constant factors in the O-notation may be large for small d", "confidence": 0.45},
        ],
    },
    {
        "statement": "OTM provides zero inter-thread interference in exact arithmetic",
        "confidence": 0.90,
        "status": "active",
        "supporting": [
            {"content": "Corollary 4.5 proves zero interference under exact arithmetic", "confidence": 0.95},
            {"content": "Stiefel manifold parameterization guarantees orthonormality by construction", "confidence": 0.88},
        ],
        "contradicting": [
            {"content": "Floating point errors in Cayley retraction cause epsilon-level interference", "confidence": 0.35},
        ],
    },
    {
        "statement": "Meta-Controller has local Lyapunov stability",
        "confidence": 0.80,
        "status": "active",
        "supporting": [
            {"content": "Theorem 5.3 proves local Lyapunov stability under bounded perturbations", "confidence": 0.88},
            {"content": "Simulation experiments show convergence within basin of attraction", "confidence": 0.75},
        ],
        "contradicting": [
            {"content": "Global stability is not guaranteed — large perturbations may diverge", "confidence": 0.50},
        ],
    },
    {
        "statement": "HBTA is faster than FlashAttention for all sequence lengths",
        "confidence": 0.30,
        "status": "weakened",
        "supporting": [
            {"content": "Theoretical O(Nd^2 log N) vs O(N^2 d/M) favors HBTA asymptotically", "confidence": 0.70},
        ],
        "contradicting": [
            {"content": "For short sequences (N < 1024) FlashAttention is faster due to lower constant overhead", "confidence": 0.85},
            {"content": "HBTA crossover point depends on d and M — not universally faster", "confidence": 0.80},
        ],
    },
    {
        "statement": "Pingala gating eliminates gradient death",
        "confidence": 0.50,
        "status": "weakened",
        "supporting": [
            {"content": "Binary gating pattern ensures at least one path remains active", "confidence": 0.70},
        ],
        "contradicting": [
            {"content": "In practice, very deep networks can still experience gradient vanishing despite gating", "confidence": 0.65},
            {"content": "Pingala gating adds computational overhead that may not justify marginal improvement", "confidence": 0.55},
        ],
    },
    {
        "statement": "Nyaya verifier provides formal logic verification",
        "confidence": 0.40,
        "status": "weakened",
        "supporting": [
            {"content": "Nyaya five-member syllogism provides structured inference validation", "confidence": 0.60},
        ],
        "contradicting": [
            {"content": "Formal verification is undecidable for general first-order logic", "confidence": 0.90},
            {"content": "Nyaya framework is heuristic-inspired, not truly formal in the mathematical sense", "confidence": 0.75},
        ],
    },
    {
        "statement": "Knowledge consolidation improves over sessions",
        "confidence": 0.70,
        "status": "active",
        "supporting": [
            {"content": "Sleep cycle consolidation extracts increasingly refined concepts per session", "confidence": 0.78},
            {"content": "Belief confidence tends to increase with repeated supporting evidence", "confidence": 0.72},
        ],
        "contradicting": [
            {"content": "Consolidation errors can accumulate, degrading knowledge quality over time", "confidence": 0.40},
        ],
    },
    {
        "statement": "Orthogonal gradient projection prevents catastrophic forgetting",
        "confidence": 0.75,
        "status": "active",
        "supporting": [
            {"content": "Gradient projection onto orthogonal complement preserves prior task knowledge", "confidence": 0.82},
            {"content": "Empirical results show 86% knowledge retention vs 18% for standard fine-tuning", "confidence": 0.80},
        ],
        "contradicting": [
            {"content": "For very large task sequences, orthogonal subspace dimension becomes limiting", "confidence": 0.50},
        ],
    },
]

# Goals: (description, priority, progress, status, parent_idx, dependency_idxs, related_concept_names, metadata)
GOALS = [
    {
        "description": "Complete ACOS v0.2 cognitive architecture",
        "priority": 15,  # CRITICAL
        "progress": 0.50,
        "status": "active",
        "parent_idx": None,
        "dependency_idxs": [],
        "related_concept_names": ["Cognitive Kernel", "Meta-Controller"],
        "metadata": '{"category": "architecture", "milestone": "Month 6"}',
        "subgoal_idxs": [1, 2],  # references to goals below by 0-based index in this list
    },
    {
        "description": "Implement HBTA layer in PyTorch",
        "priority": 15,  # CRITICAL
        "progress": 0.35,
        "status": "active",
        "parent_idx": 0,
        "dependency_idxs": [],
        "related_concept_names": ["HBTA", "FlashAttention"],
        "metadata": '{"category": "implementation", "milestone": "Month 1"}',
        "subgoal_idxs": [],
    },
    {
        "description": "Wrap Llama-3-8B with Cognitive Kernel",
        "priority": 10,  # HIGH
        "progress": 0.15,
        "status": "active",
        "parent_idx": 0,
        "dependency_idxs": [1],  # depends on HBTA
        "related_concept_names": ["Cognitive Kernel", "OTM"],
        "metadata": '{"category": "integration", "milestone": "Month 2"}',
        "subgoal_idxs": [],
    },
    {
        "description": "Build Upload and Learn pipeline",
        "priority": 10,  # HIGH
        "progress": 0.0,
        "status": "active",
        "parent_idx": None,
        "dependency_idxs": [1, 2],  # depends on HBTA + Llama wrapping
        "related_concept_names": ["Knowledge Consolidation", "Semantic Memory"],
        "metadata": '{"category": "pipeline", "milestone": "Month 3"}',
        "subgoal_idxs": [],
    },
    {
        "description": "Build CUDA kernel optimization",
        "priority": 5,  # NORMAL
        "progress": 0.0,
        "status": "paused",
        "parent_idx": None,
        "dependency_idxs": [1],  # depends on HBTA implementation
        "related_concept_names": ["OTM", "Cayley Retraction"],
        "metadata": '{"category": "optimization", "milestone": "Month 5", "pause_reason": "Waiting for stable HBTA API"}',
        "subgoal_idxs": [],
    },
    {
        "description": "Beta launch ACOS for Laptops",
        "priority": 10,  # HIGH
        "progress": 0.0,
        "status": "active",
        "parent_idx": None,
        "dependency_idxs": [0, 3],  # depends on architecture + upload pipeline
        "related_concept_names": ["Cognitive Kernel", "Model Router"],
        "metadata": '{"category": "launch", "milestone": "Month 6", "target": "Consumer laptops with 8GB+ RAM"}',
        "subgoal_idxs": [],
    },
]


# ─── Main Seeding Logic ───────────────────────────────────────────────────────

async def seed_database() -> None:
    """Seed the ACOS SQLite database with cognitive data."""

    print(f"ACOS Cognitive Data Seeder")
    print(f"Database: {DB_PATH}")
    print(f"{'=' * 60}")

    if not DB_PATH.exists():
        print(f"ERROR: Database file not found at {DB_PATH}")
        print(f"Please run the ACOS runtime first to initialize the database.")
        return

    async with aiosqlite.connect(str(DB_PATH)) as db:
        # Enable foreign keys and WAL mode
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        # ─── Step 1: Clear existing data ──────────────────────────────────
        print("\n[1/9] Clearing existing cognitive data...")

        tables_to_clear = [
            "semantic_relationships",
            "semantic_concepts",
            "cognitive_states",
            "goals",
            "beliefs",
            "relationships",
            "entities",
            "concepts",
            "source_references",
        ]
        for table in tables_to_clear:
            await db.execute(f"DELETE FROM {table}")
        await db.commit()
        print(f"   Cleared {len(tables_to_clear)} tables.")

        # ─── Step 2: Insert concepts ──────────────────────────────────────
        print("\n[2/9] Inserting concepts...")

        concept_ids: dict[str, str] = {}  # name -> id mapping

        for name, ctype, desc, props, conf in CONCEPTS:
            cid = _gen_id()
            concept_ids[name] = cid
            now = _ts()
            await db.execute(
                """INSERT INTO concepts
                   (id, name, concept_type, description, properties, confidence,
                    source_ids, created_at, updated_at, access_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cid, name, ctype, desc, props, conf, "[]", now, now, 0),
            )
        await db.commit()
        print(f"   Inserted {len(CONCEPTS)} concepts.")

        # ─── Step 3: Insert relationships ─────────────────────────────────
        print("\n[3/9] Inserting relationships...")

        rel_count = 0
        for src_name, tgt_name, rel_type, desc, conf, weight in RELATIONSHIPS:
            src_id = concept_ids.get(src_name)
            tgt_id = concept_ids.get(tgt_name)
            if not src_id or not tgt_id:
                print(f"   WARNING: Skipping relationship — concept not found: {src_name} -> {tgt_name}")
                continue

            rid = _gen_id()
            now = _ts()
            await db.execute(
                """INSERT INTO relationships
                   (id, source_concept_id, target_concept_id, relationship_type,
                    description, confidence, weight, source_ids, properties, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (rid, src_id, tgt_id, rel_type, desc, conf, weight, "[]", "{}", now),
            )
            rel_count += 1
        await db.commit()
        print(f"   Inserted {rel_count} relationships.")

        # ─── Step 4: Insert entities ──────────────────────────────────────
        print("\n[4/9] Inserting entities...")

        entity_ids: dict[str, str] = {}

        for name, etype, desc, mentions, conf, concept_ref in ENTITIES:
            eid = _gen_id()
            entity_ids[name] = eid
            linked_concept_id = concept_ids.get(concept_ref)
            now = _ts()
            await db.execute(
                """INSERT INTO entities
                   (id, name, entity_type, description, mentions, confidence,
                    source_ids, concept_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (eid, name, etype, desc, mentions, conf, "[]", linked_concept_id, now),
            )
        await db.commit()
        print(f"   Inserted {len(ENTITIES)} entities.")

        # ─── Step 5: Insert beliefs ───────────────────────────────────────
        print("\n[5/9] Inserting beliefs...")

        belief_ids: list[str] = []

        for bdata in BELIEFS:
            bid = _gen_id()
            belief_ids.append(bid)
            now = _ts()

            # Build evidence objects with proper IDs and timestamps
            supporting = []
            for ev in bdata["supporting"]:
                supporting.append({
                    "id": _gen_id(),
                    "content": ev["content"],
                    "evidence_type": "supporting",
                    "source_id": None,
                    "confidence": ev["confidence"],
                    "created_at": now,
                })

            contradicting = []
            for ev in bdata["contradicting"]:
                contradicting.append({
                    "id": _gen_id(),
                    "content": ev["content"],
                    "evidence_type": "contradicting",
                    "source_id": None,
                    "confidence": ev["confidence"],
                    "created_at": now,
                })

            # Find related concept IDs by matching keywords in statement
            related_concepts = []
            stmt_lower = bdata["statement"].lower()
            for cname, cid in concept_ids.items():
                if cname.lower() in stmt_lower:
                    related_concepts.append(cid)

            await db.execute(
                """INSERT INTO beliefs
                   (id, statement, confidence, status, supporting_evidence,
                    contradicting_evidence, related_concept_ids, parent_belief_id,
                    version, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    bid,
                    bdata["statement"],
                    bdata["confidence"],
                    bdata["status"],
                    json.dumps(supporting),
                    json.dumps(contradicting),
                    json.dumps(related_concepts),
                    None,  # parent_belief_id
                    1,     # version
                    now,
                    now,
                ),
            )
        await db.commit()
        print(f"   Inserted {len(BELIEFS)} beliefs.")

        # ─── Step 6: Insert goals ─────────────────────────────────────────
        print("\n[6/9] Inserting goals...")

        goal_ids: list[str] = []

        # First pass: create all goals and collect IDs
        for gdata in GOALS:
            gid = _gen_id()
            goal_ids.append(gid)

        # Second pass: insert with resolved IDs
        for i, gdata in enumerate(GOALS):
            gid = goal_ids[i]
            now = _ts()

            parent_goal_id = goal_ids[gdata["parent_idx"]] if gdata["parent_idx"] is not None else None
            dependency_ids = [goal_ids[di] for di in gdata["dependency_idxs"]]
            subgoal_ids = [goal_ids[si] for si in gdata["subgoal_idxs"]]

            related_concept_ids = []
            for cname in gdata["related_concept_names"]:
                if cname in concept_ids:
                    related_concept_ids.append(concept_ids[cname])

            await db.execute(
                """INSERT INTO goals
                   (id, description, status, priority, progress, parent_goal_id,
                    subgoal_ids, dependency_ids, related_concept_ids,
                    related_belief_ids, metadata, created_at, updated_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    gid,
                    gdata["description"],
                    gdata["status"],
                    gdata["priority"],
                    gdata["progress"],
                    parent_goal_id,
                    json.dumps(subgoal_ids),
                    json.dumps(dependency_ids),
                    json.dumps(related_concept_ids),
                    json.dumps([]),  # related_belief_ids
                    gdata["metadata"],
                    now,
                    now,
                    None,  # completed_at
                ),
            )
        await db.commit()
        print(f"   Inserted {len(GOALS)} goals.")

        # ─── Step 7: Insert cognitive state ───────────────────────────────
        print("\n[7/9] Inserting cognitive state...")

        cs_id = _gen_id()
        now = _ts()

        # Build belief summaries for cognitive state
        belief_summaries = []
        for i, bdata in enumerate(BELIEFS):
            belief_summaries.append({
                "id": belief_ids[i],
                "statement": bdata["statement"],
                "confidence": bdata["confidence"],
                "status": bdata["status"],
            })

        # Build goal summaries for cognitive state
        goal_summaries = []
        for i, gdata in enumerate(GOALS):
            goal_summaries.append({
                "id": goal_ids[i],
                "description": gdata["description"],
                "status": gdata["status"],
                "progress": gdata["progress"],
                "priority": gdata["priority"],
            })

        # Uncertainty estimates for key topics
        uncertainty_estimates = {
            "HBTA_crossover_point": 0.55,
            "OTM_numerical_stability": 0.35,
            "Meta_Controller_global_stability": 0.45,
            "Pingala_gating_effectiveness": 0.50,
            "Nyaya_formal_completeness": 0.60,
            "HBTA_CUDA_performance": 0.40,
            "consolidation_accuracy": 0.30,
            "Llama_wrapping_feasibility": 0.25,
        }

        # All concept IDs as knowledge graph references
        knowledge_graph_concept_ids = list(concept_ids.values())

        # Active beliefs and goals
        active_belief_ids = [belief_ids[i] for i, b in enumerate(BELIEFS) if b["status"] == "active"]
        active_goal_ids = [goal_ids[i] for i, g in enumerate(GOALS) if g["status"] == "active"]

        await db.execute(
            """INSERT INTO cognitive_states
               (id, beliefs, goals, active_thread_ids, recent_memory_ids,
                uncertainty_estimates, knowledge_graph_concept_ids, session_count,
                last_query, last_synthesis, overall_confidence, metadata,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cs_id,
                json.dumps(belief_summaries),
                json.dumps(goal_summaries),
                json.dumps([]),  # active_thread_ids
                json.dumps([]),  # recent_memory_ids
                json.dumps(uncertainty_estimates),
                json.dumps(knowledge_graph_concept_ids),
                47,  # session_count
                "How does OTM prevent inter-thread interference?",  # last_query
                "OTM uses Stiefel manifold parameterization with Cayley retraction to maintain orthogonal thread memories, achieving zero interference in exact arithmetic per Corollary 4.5.",
                0.67,  # overall_confidence
                json.dumps({
                    "seed_version": "1.0",
                    "seed_timestamp": now,
                    "active_belief_count": len(active_belief_ids),
                    "weakened_belief_count": len(BELIEFS) - len(active_belief_ids),
                    "active_goal_count": len(active_goal_ids),
                    "total_concepts": len(concept_ids),
                    "total_entities": len(entity_ids),
                    "total_relationships": rel_count,
                }),
                now,
                now,
            ),
        )
        await db.commit()
        print(f"   Inserted 1 cognitive state (session_count=47, overall_confidence=0.67).")

        # ─── Step 8: Insert semantic concepts ─────────────────────────────
        print("\n[8/9] Inserting semantic concepts...")

        # Key ACOS concepts to also store in semantic memory
        semantic_concept_names = [
            "HBTA", "OTM", "Cognitive Kernel", "Stiefel Manifold",
            "Cayley Retraction", "Meta-Controller", "Knowledge Fabric",
            "Belief State", "Goal System", "Pingala Gating",
            "Panini Constraints", "Nyaya Verifier",
        ]

        semantic_concept_ids: dict[str, str] = {}

        for name in semantic_concept_names:
            cid = concept_ids.get(name)
            if not cid:
                continue

            # Find the concept data from CONCEPTS list
            concept_data = None
            for cname, ctype, desc, props, conf in CONCEPTS:
                if cname == name:
                    concept_data = (cname, ctype, desc, props, conf)
                    break

            if not concept_data:
                continue

            cname, ctype, desc, props, conf = concept_data
            scid = _gen_id()
            semantic_concept_ids[name] = scid
            now_sc = _ts()

            await db.execute(
                """INSERT INTO semantic_concepts
                   (id, name, concept_type, description, properties, confidence,
                    source_ids, created_at, updated_at, access_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (scid, cname, ctype, desc, props, conf, "[]", now_sc, now_sc, 0),
            )
        await db.commit()
        print(f"   Inserted {len(semantic_concept_ids)} semantic concepts.")

        # ─── Step 9: Insert semantic relationships ────────────────────────
        print("\n[9/9] Inserting semantic relationships...")

        sem_rel_count = 0
        for src_name, tgt_name, rel_type, desc, conf, weight in RELATIONSHIPS:
            src_id = semantic_concept_ids.get(src_name)
            tgt_id = semantic_concept_ids.get(tgt_name)
            if not src_id or not tgt_id:
                continue

            srid = _gen_id()
            now_sr = _ts()
            await db.execute(
                """INSERT INTO semantic_relationships
                   (id, source_concept_id, target_concept_id, relationship_type,
                    description, confidence, weight, source_ids, properties, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (srid, src_id, tgt_id, rel_type, desc, conf, weight, "[]", "{}", now_sr),
            )
            sem_rel_count += 1
        await db.commit()
        print(f"   Inserted {sem_rel_count} semantic relationships.")

    # ─── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("ACOS Cognitive Data Seeding Complete!")
    print(f"{'=' * 60}")
    print(f"  Concepts:               {len(CONCEPTS)}")
    print(f"  Relationships:          {rel_count}")
    print(f"  Entities:               {len(ENTITIES)}")
    print(f"  Beliefs:                {len(BELIEFS)}")
    print(f"  Goals:                  {len(GOALS)}")
    print(f"  Cognitive States:       1")
    print(f"  Semantic Concepts:      {len(semantic_concept_ids)}")
    print(f"  Semantic Relationships: {sem_rel_count}")
    print(f"{'=' * 60}")


async def verify_database() -> None:
    """Verify the seeded data by querying the database."""

    print(f"\n{'=' * 60}")
    print("Verifying Seeded Data")
    print(f"{'=' * 60}")

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row

        # Concepts
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM concepts")
        row = await cursor.fetchone()
        print(f"\n  Concepts: {row['cnt']}")
        cursor = await db.execute("SELECT name, concept_type, confidence FROM concepts ORDER BY name LIMIT 5")
        rows = await cursor.fetchall()
        for r in rows:
            print(f"    - {r['name']} ({r['concept_type']}, conf={r['confidence']})")
        print(f"    ... and {row['cnt'] - 5} more")

        # Relationships
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM relationships")
        row = await cursor.fetchone()
        print(f"\n  Relationships: {row['cnt']}")
        cursor = await db.execute("""
            SELECT r.relationship_type, c1.name as src, c2.name as tgt
            FROM relationships r
            JOIN concepts c1 ON r.source_concept_id = c1.id
            JOIN concepts c2 ON r.target_concept_id = c2.id
            LIMIT 5
        """)
        rows = await cursor.fetchall()
        for r in rows:
            print(f"    - {r['src']} --[{r['relationship_type']}]--> {r['tgt']}")
        print(f"    ... and {row['cnt'] - 5} more")

        # Entities
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM entities")
        row = await cursor.fetchone()
        print(f"\n  Entities: {row['cnt']}")
        cursor = await db.execute("SELECT name, entity_type, mentions FROM entities ORDER BY mentions DESC")
        rows = await cursor.fetchall()
        for r in rows:
            print(f"    - {r['name']} ({r['entity_type']}, mentions={r['mentions']})")

        # Beliefs
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM beliefs")
        row = await cursor.fetchone()
        print(f"\n  Beliefs: {row['cnt']}")
        cursor = await db.execute("SELECT statement, confidence, status FROM beliefs")
        rows = await cursor.fetchall()
        for r in rows:
            print(f"    - [{r['status']}] conf={r['confidence']:.2f}: {r['statement'][:65]}...")
        # Evidence counts
        cursor = await db.execute("SELECT id, supporting_evidence, contradicting_evidence FROM beliefs")
        rows = await cursor.fetchall()
        total_supporting = 0
        total_contradicting = 0
        for r in rows:
            sup = json.loads(r['supporting_evidence'])
            con = json.loads(r['contradicting_evidence'])
            total_supporting += len(sup)
            total_contradicting += len(con)
        print(f"    Total supporting evidence: {total_supporting}")
        print(f"    Total contradicting evidence: {total_contradicting}")

        # Goals
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM goals")
        row = await cursor.fetchone()
        print(f"\n  Goals: {row['cnt']}")
        cursor = await db.execute("SELECT description, status, priority, progress FROM goals ORDER BY priority DESC")
        rows = await cursor.fetchall()
        for r in rows:
            priority_label = {1: "LOW", 5: "NORMAL", 10: "HIGH", 15: "CRITICAL"}.get(r['priority'], str(r['priority']))
            print(f"    - [{r['status']}] {priority_label}(pri={r['priority']}) prog={r['progress']:.0%}: {r['description']}")

        # Cognitive State
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM cognitive_states")
        row = await cursor.fetchone()
        print(f"\n  Cognitive States: {row['cnt']}")
        cursor = await db.execute("SELECT * FROM cognitive_states ORDER BY updated_at DESC LIMIT 1")
        row = await cursor.fetchone()
        if row:
            print(f"    - session_count: {row['session_count']}")
            print(f"    - overall_confidence: {row['overall_confidence']}")
            uncertainty = json.loads(row['uncertainty_estimates'])
            print(f"    - uncertainty topics: {len(uncertainty)} ({', '.join(list(uncertainty.keys())[:4])}...)")
            kg_concepts = json.loads(row['knowledge_graph_concept_ids'])
            print(f"    - knowledge_graph_concept_ids: {len(kg_concepts)} references")
            beliefs_in_state = json.loads(row['beliefs'])
            goals_in_state = json.loads(row['goals'])
            print(f"    - beliefs in state: {len(beliefs_in_state)}")
            print(f"    - goals in state: {len(goals_in_state)}")

        # Semantic Concepts
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM semantic_concepts")
        row = await cursor.fetchone()
        print(f"\n  Semantic Concepts: {row['cnt']}")

        # Semantic Relationships
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM semantic_relationships")
        row = await cursor.fetchone()
        print(f"  Semantic Relationships: {row['cnt']}")

    print(f"\n{'=' * 60}")
    print("Verification Complete - All data seeded successfully!")
    print(f"{'=' * 60}")


async def main() -> None:
    """Main entry point."""
    await seed_database()
    await verify_database()


if __name__ == "__main__":
    asyncio.run(main())
