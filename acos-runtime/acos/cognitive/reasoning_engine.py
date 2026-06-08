"""
Reasoning Engine — inference, contradiction detection, and knowledge gap discovery.

Capabilities:
- Transitive and implication inference over the knowledge graph
- Contradiction detection across beliefs and knowledge relationships
- Knowledge gap discovery (isolated concepts, missing links, weak beliefs)
- Planning support via goal-relevant gap identification
- Deductive reasoning from premises to conclusions
- Inference validation (circular reasoning, premise existence, confidence)

All I/O methods are async.  Results are persisted to SQLite for audit trail.
KnowledgeFabric and BeliefState are injected via the constructor and accessed
through duck-typing — they are **not** imported directly.
"""

from __future__ import annotations

import json
import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from acos.schemas.v2_models import (
    Belief,
    BeliefStatus,
    Concept,
    ContradictionResult,
    InferenceResult,
    InferenceType,
    KnowledgeGap,
    Relationship,
    RelationshipType,
)

# ─── Constants ────────────────────────────────────────────────────────────────

DEFAULT_DB_PATH = str(
    Path(__file__).parent.parent.parent / "data" / "reasoning.db"
)

OPPOSITE_TERMS: dict[str, str] = {
    "best": "worst",
    "worst": "best",
    "increase": "decrease",
    "decrease": "increase",
    "true": "false",
    "false": "true",
    "always": "never",
    "never": "always",
    "possible": "impossible",
    "impossible": "possible",
    "support": "contradict",
    "contradict": "support",
    "good": "bad",
    "bad": "good",
    "positive": "negative",
    "negative": "positive",
    "enable": "disable",
    "disable": "enable",
    "accept": "reject",
    "reject": "accept",
}

# Relationship types that are transitive — A→B and B→C implies A→C
TRANSITIVE_RELATIONSHIPS: set[RelationshipType] = {
    RelationshipType.DEPENDS_ON,
    RelationshipType.IS_A,
    RelationshipType.PART_OF,
    RelationshipType.PRECEDES,
    RelationshipType.IMPLIES,
    RelationshipType.CAUSES,
}

# Mapping from transitive rel type to the inference type used
REL_TYPE_TO_INFERENCE: dict[RelationshipType, InferenceType] = {
    RelationshipType.DEPENDS_ON: InferenceType.TRANSITIVITY,
    RelationshipType.IS_A: InferenceType.TRANSITIVITY,
    RelationshipType.PART_OF: InferenceType.TRANSITIVITY,
    RelationshipType.PRECEDES: InferenceType.TRANSITIVITY,
    RelationshipType.IMPLIES: InferenceType.TRANSITIVITY,
    RelationshipType.CAUSES: InferenceType.TRANSITIVITY,
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _gen_id() -> str:
    return str(uuid.uuid4())


def _contains_negation(stmt1: str, stmt2: str) -> bool:
    """Return True if one statement is a negation of the other.

    Detects patterns like 'X is Y' vs 'X is not Y', or 'X can Y' vs
    'X cannot Y'.
    """
    s1 = stmt1.lower().strip()
    s2 = stmt2.lower().strip()

    negation_words = ["not ", "never ", "cannot ", "can't ", "doesn't ", "does not ", "is not ", "isn't "]
    for neg in negation_words:
        # If s1 contains negation and s2 has the same text without it
        if neg in s1:
            candidate = s1.replace(neg, "", 1)
            if candidate == s2 or candidate.strip() == s2.strip():
                return True
        if neg in s2:
            candidate = s2.replace(neg, "", 1)
            if candidate == s1 or candidate.strip() == s1.strip():
                return True
    return False


def _contains_opposite_terms(stmt1: str, stmt2: str) -> bool:
    """Return True if the two statements contain opposite terms."""
    words1 = set(stmt1.lower().split())
    words2 = set(stmt2.lower().split())
    for w1 in words1:
        if w1 in OPPOSITE_TERMS and OPPOSITE_TERMS[w1] in words2:
            return True
    return False


# ─── ReasoningEngine ──────────────────────────────────────────────────────────


class ReasoningEngine:
    """Reasoning Engine — inference, contradiction detection, and knowledge gap discovery.

    Parameters
    ----------
    knowledge_fabric : Any
        An object providing async access to the knowledge graph.  Expected
        duck-typed methods:

        - ``async get_concept(concept_id: str) -> Concept | None``
        - ``async get_all_concepts() -> list[Concept]``
        - ``async get_relationships_for_concept(concept_id: str) -> list[Relationship]``
        - ``async get_all_relationships() -> list[Relationship]``
        - ``async get_concepts_by_ids(concept_ids: list[str]) -> list[Concept]``

    belief_state : Any
        An object providing async access to the belief system.  Expected
        duck-typed methods:

        - ``async get_all_beliefs() -> list[Belief]``
        - ``async get_active_beliefs() -> list[Belief]``
        - ``async get_belief(belief_id: str) -> Belief | None``

    db_path : str | None
        Path to the SQLite database used for the audit trail.  Defaults to
        ``<project_root>/data/reasoning.db``.
    """

    def __init__(
        self,
        knowledge_fabric: Any,
        belief_state: Any,
        db_path: str | None = None,
    ) -> None:
        self._fabric = knowledge_fabric
        self._beliefs = belief_state
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn: aiosqlite.Connection | None = None

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Open the SQLite connection and create audit tables."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self) -> None:
        """Close the SQLite connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _create_tables(self) -> None:
        """Create the audit-trail tables if they don't exist."""
        assert self._conn is not None
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS inference_results (
                id TEXT PRIMARY KEY,
                inference_type TEXT NOT NULL,
                premise_concept_ids TEXT DEFAULT '[]',
                conclusion_concept_id TEXT,
                conclusion_description TEXT NOT NULL,
                relationship_type TEXT DEFAULT 'implies',
                confidence REAL DEFAULT 0.6,
                reasoning_chain TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS contradiction_results (
                id TEXT PRIMARY KEY,
                belief_id_1 TEXT,
                belief_id_2 TEXT,
                concept_id_1 TEXT,
                concept_id_2 TEXT,
                description TEXT NOT NULL,
                severity REAL DEFAULT 0.5,
                resolution_suggestion TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                related_concept_ids TEXT DEFAULT '[]',
                importance REAL DEFAULT 0.5,
                suggested_query TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_inference_type
                ON inference_results(inference_type);
            CREATE INDEX IF NOT EXISTS idx_contradiction_severity
                ON contradiction_results(severity);
            CREATE INDEX IF NOT EXISTS idx_gap_importance
                ON knowledge_gaps(importance);
        """)
        await self._conn.commit()

    # ─── Persistence helpers ────────────────────────────────────────────────

    async def _persist_inference(self, result: InferenceResult) -> None:
        if self._conn is None:
            return
        await self._conn.execute(
            """INSERT OR REPLACE INTO inference_results
               (id, inference_type, premise_concept_ids, conclusion_concept_id,
                conclusion_description, relationship_type, confidence,
                reasoning_chain, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.id,
                result.inference_type.value,
                json.dumps(result.premise_concept_ids),
                result.conclusion_concept_id,
                result.conclusion_description,
                result.relationship_type.value,
                result.confidence,
                json.dumps(result.reasoning_chain),
                result.created_at.isoformat(),
            ),
        )
        await self._conn.commit()

    async def _persist_contradiction(self, result: ContradictionResult) -> None:
        if self._conn is None:
            return
        await self._conn.execute(
            """INSERT OR REPLACE INTO contradiction_results
               (id, belief_id_1, belief_id_2, concept_id_1, concept_id_2,
                description, severity, resolution_suggestion, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.id,
                result.belief_id_1,
                result.belief_id_2,
                result.concept_id_1,
                result.concept_id_2,
                result.description,
                result.severity,
                result.resolution_suggestion,
                result.created_at.isoformat(),
            ),
        )
        await self._conn.commit()

    async def _persist_gap(self, gap: KnowledgeGap) -> None:
        if self._conn is None:
            return
        await self._conn.execute(
            """INSERT OR REPLACE INTO knowledge_gaps
               (id, description, related_concept_ids, importance,
                suggested_query, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                gap.id,
                gap.description,
                json.dumps(gap.related_concept_ids),
                gap.importance,
                gap.suggested_query,
                gap.created_at.isoformat(),
            ),
        )
        await self._conn.commit()

    # ─── Fabric / Belief accessors (with graceful fallback) ─────────────────

    async def _get_concept(self, concept_id: str) -> Concept | None:
        try:
            return await self._fabric.get_concept(concept_id)
        except Exception:
            return None

    async def _get_all_concepts(self) -> list[Concept]:
        try:
            return await self._fabric.get_all_concepts()
        except Exception:
            return []

    async def _get_relationships_for_concept(
        self, concept_id: str
    ) -> list[Relationship]:
        try:
            return await self._fabric.get_relationships_for_concept(concept_id)
        except Exception:
            return []

    async def _get_all_relationships(self) -> list[Relationship]:
        try:
            return await self._fabric.get_all_relationships()
        except Exception:
            return []

    async def _get_active_beliefs(self) -> list[Belief]:
        try:
            return await self._beliefs.get_active_beliefs()
        except Exception:
            pass
        try:
            all_beliefs = await self._beliefs.get_all_beliefs()
            return [b for b in all_beliefs if b.status == BeliefStatus.ACTIVE]
        except Exception:
            return []

    async def _get_all_beliefs(self) -> list[Belief]:
        try:
            return await self._beliefs.get_all_beliefs()
        except Exception:
            return []

    # ─── 1. infer_relationships ────────────────────────────────────────────

    async def infer_relationships(
        self,
        concept_id: str,
        max_depth: int = 3,
    ) -> list[InferenceResult]:
        """Discover relationships reachable from *concept_id* through the graph.

        Applies two inference rules:

        * **Transitivity** — if A→B (DEPENDS_ON) and B→C (DEPENDS_ON), infer
          A→C (DEPENDS_ON).  Same for IS_A, PART_OF, PRECEDES, CAUSES.
        * **Implication** — if A→B (IMPLIES) and B→C (IMPLIES), infer A→C
          (IMPLIES).

        Confidence decays with chain length: ``base_confidence ^ n`` where
        *base_confidence* is the average of all relationship confidences in the
        chain and *n* is the chain length.

        Parameters
        ----------
        concept_id:
            The starting concept.
        max_depth:
            Maximum traversal depth (default 3).

        Returns
        -------
        list[InferenceResult]
            All inferred relationships discovered via traversal.
        """
        root = await self._get_concept(concept_id)
        if root is None:
            return []

        # Build adjacency from all relationships for efficient traversal
        all_rels = await self._get_all_relationships()
        outgoing: dict[str, list[Relationship]] = defaultdict(list)
        for rel in all_rels:
            outgoing[rel.source_concept_id].append(rel)

        results: list[InferenceResult] = []
        visited_chains: set[str] = set()  # deduplicate by chain signature

        # BFS traversal collecting chains
        # Each queue entry: (current_concept_id, chain_of_concept_ids,
        #                    chain_of_relationships)
        queue: list[tuple[str, list[str], list[Relationship]]] = [
            (concept_id, [concept_id], [])
        ]

        while queue:
            current_id, concept_chain, rel_chain = queue.pop(0)
            depth = len(rel_chain)

            if depth >= max_depth:
                continue

            for rel in outgoing.get(current_id, []):
                next_id = rel.target_concept_id

                # Prevent circular chains
                if next_id in concept_chain:
                    continue

                new_concept_chain = concept_chain + [next_id]
                new_rel_chain = rel_chain + [rel]

                # Check if this chain of relationship types is transitive
                chain_rel_types = {r.relationship_type for r in new_rel_chain}

                # --- Transitive inference (all rels same transitive type) ---
                if (
                    len(chain_rel_types) == 1
                    and chain_rel_types.intersection(TRANSITIVE_RELATIONSHIPS)
                ):
                    chain_type = chain_rel_types.pop()
                    # Only emit if the chain length > 1 (i.e. we inferred
                    # something not directly in the graph)
                    if len(new_rel_chain) > 1:
                        signature = "->".join(new_concept_chain) + f"[{chain_type.value}]"
                        if signature not in visited_chains:
                            visited_chains.add(signature)
                            avg_conf = (
                                sum(r.confidence for r in new_rel_chain)
                                / len(new_rel_chain)
                            )
                            confidence = avg_conf ** len(new_rel_chain)

                            # Build reasoning chain
                            steps: list[str] = []
                            for i, r in enumerate(new_rel_chain):
                                src_name = new_concept_chain[i]
                                tgt_name = new_concept_chain[i + 1]
                                steps.append(
                                    f"{src_name} --[{r.relationship_type.value}]--> {tgt_name} "
                                    f"(conf={r.confidence:.2f})"
                                )
                            steps.append(
                                f"Inferred: {new_concept_chain[0]} --[{chain_type.value}]--> "
                                f"{new_concept_chain[-1]} (conf={confidence:.2f})"
                            )

                            source_name = root.name if concept_chain[0] == concept_id else concept_chain[0]
                            target_concept = await self._get_concept(next_id)
                            target_name = target_concept.name if target_concept else next_id

                            inference = InferenceResult(
                                inference_type=InferenceType.TRANSITIVITY,
                                premise_concept_ids=list(new_concept_chain),
                                conclusion_concept_id=next_id,
                                conclusion_description=(
                                    f"{source_name} {chain_type.value} {target_name} "
                                    f"(inferred via transitive chain)"
                                ),
                                relationship_type=chain_type,
                                confidence=confidence,
                                reasoning_chain=steps,
                            )
                            results.append(inference)
                            await self._persist_inference(inference)

                # --- Implication chain (IMPLIES → IMPLIES) ---
                elif all(
                    r.relationship_type == RelationshipType.IMPLIES
                    for r in new_rel_chain
                ):
                    if len(new_rel_chain) > 1:
                        signature = "->".join(new_concept_chain) + "[implies_chain]"
                        if signature not in visited_chains:
                            visited_chains.add(signature)
                            avg_conf = (
                                sum(r.confidence for r in new_rel_chain)
                                / len(new_rel_chain)
                            )
                            confidence = avg_conf ** len(new_rel_chain)

                            steps = []
                            for i, r in enumerate(new_rel_chain):
                                steps.append(
                                    f"{new_concept_chain[i]} --[implies]--> "
                                    f"{new_concept_chain[i + 1]} "
                                    f"(conf={r.confidence:.2f})"
                                )
                            steps.append(
                                f"Inferred: {new_concept_chain[0]} implies "
                                f"{new_concept_chain[-1]} (conf={confidence:.2f})"
                            )

                            source_name = root.name if concept_chain[0] == concept_id else concept_chain[0]
                            target_concept = await self._get_concept(next_id)
                            target_name = target_concept.name if target_concept else next_id

                            inference = InferenceResult(
                                inference_type=InferenceType.TRANSITIVITY,
                                premise_concept_ids=list(new_concept_chain),
                                conclusion_concept_id=next_id,
                                conclusion_description=(
                                    f"{source_name} implies {target_name} "
                                    f"(inferred via implication chain)"
                                ),
                                relationship_type=RelationshipType.IMPLIES,
                                confidence=confidence,
                                reasoning_chain=steps,
                            )
                            results.append(inference)
                            await self._persist_inference(inference)

                # Continue traversal regardless
                queue.append((next_id, new_concept_chain, new_rel_chain))

        # Also produce direct-inference results for immediate neighbours
        # (single-hop with slight confidence reduction)
        for rel in outgoing.get(concept_id, []):
            target_concept = await self._get_concept(rel.target_concept_id)
            target_name = target_concept.name if target_concept else rel.target_concept_id

            signature = f"{concept_id}->{rel.target_concept_id}[{rel.relationship_type.value}][direct]"
            if signature not in visited_chains:
                visited_chains.add(signature)

                inference = InferenceResult(
                    inference_type=InferenceType.DEDUCTION,
                    premise_concept_ids=[concept_id],
                    conclusion_concept_id=rel.target_concept_id,
                    conclusion_description=(
                        f"{root.name} {rel.relationship_type.value} {target_name} "
                        f"(direct relationship)"
                    ),
                    relationship_type=rel.relationship_type,
                    confidence=rel.confidence * 0.9,
                    reasoning_chain=[
                        f"Direct relationship: {root.name} --[{rel.relationship_type.value}]--> "
                        f"{target_name} (conf={rel.confidence:.2f})"
                    ],
                )
                results.append(inference)
                await self._persist_inference(inference)

        return results

    # ─── 2. detect_contradictions ──────────────────────────────────────────

    async def detect_contradictions(self) -> list[ContradictionResult]:
        """Scan all beliefs and knowledge-graph relationships for contradictions.

        Detection strategies:

        1. **Belief pairs** — opposite terms or negation in active belief
           statements.
        2. **Knowledge graph** — A SUPPORTS B and A CONTRADICTS B for similar
           B/C; A IS_A B and A IS_A C where B and C are contradictory.
        3. **Severity** — direct: 0.9, indirect (through chain): 0.5–0.8,
           weak (opposite terms only): 0.3–0.5.

        Returns
        -------
        list[ContradictionResult]
            All contradictions found, sorted by severity (descending).
        """
        results: list[ContradictionResult] = []
        seen_pairs: set[frozenset[str]] = set()  # avoid duplicates

        # --- Strategy 1: Belief-belief contradictions ---
        active_beliefs = await self._get_active_beliefs()
        for i, b1 in enumerate(active_beliefs):
            for b2 in active_beliefs[i + 1:]:
                pair_key = frozenset({b1.id, b2.id})
                if pair_key in seen_pairs:
                    continue

                severity = 0.0
                description = ""

                # Negation check (strongest)
                if _contains_negation(b1.statement, b2.statement):
                    severity = 0.9
                    description = (
                        f"Direct negation: '{b1.statement}' vs '{b2.statement}'"
                    )
                # Opposite-terms check (weaker)
                elif _contains_opposite_terms(b1.statement, b2.statement):
                    severity = 0.4
                    description = (
                        f"Opposite terms detected: '{b1.statement}' vs "
                        f"'{b2.statement}'"
                    )

                if severity > 0:
                    seen_pairs.add(pair_key)
                    # Resolution: reduce confidence of the weaker belief
                    weaker = b1 if b1.confidence <= b2.confidence else b2
                    stronger = b2 if b1.confidence <= b2.confidence else b1
                    resolution = (
                        f"Consider weakening belief '{weaker.statement}' "
                        f"(confidence {weaker.confidence:.2f}) in favour of "
                        f"'{stronger.statement}' (confidence {stronger.confidence:.2f}), "
                        f"or seek additional evidence."
                    )
                    cr = ContradictionResult(
                        belief_id_1=b1.id,
                        belief_id_2=b2.id,
                        description=description,
                        severity=severity,
                        resolution_suggestion=resolution,
                    )
                    results.append(cr)
                    await self._persist_contradiction(cr)

        # --- Strategy 2: Knowledge-graph contradictions ---
        all_rels = await self._get_all_relationships()

        # Index: source_concept_id -> list[Relationship]
        by_source: dict[str, list[Relationship]] = defaultdict(list)
        for rel in all_rels:
            by_source[rel.source_concept_id].append(rel)

        for source_id, rels in by_source.items():
            supports = [r for r in rels if r.relationship_type == RelationshipType.SUPPORTS]
            contradicts = [r for r in rels if r.relationship_type == RelationshipType.CONTRADICTS]

            # If A SUPPORTS B and A CONTRADICTS C where B and C are similar
            for s_rel in supports:
                for c_rel in contradicts:
                    target_s = s_rel.target_concept_id
                    target_c = c_rel.target_concept_id
                    if target_s == target_c:
                        # Direct: same concept is both supported and contradicted
                        pair_key = frozenset({s_rel.id, c_rel.id})
                        if pair_key in seen_pairs:
                            continue
                        seen_pairs.add(pair_key)

                        source_concept = await self._get_concept(source_id)
                        source_name = source_concept.name if source_concept else source_id
                        target_concept = await self._get_concept(target_s)
                        target_name = target_concept.name if target_concept else target_s

                        cr = ContradictionResult(
                            concept_id_1=source_id,
                            concept_id_2=target_s,
                            description=(
                                f"Concept '{source_name}' both SUPPORTS and "
                                f"CONTRADICTS '{target_name}'"
                            ),
                            severity=0.9,
                            resolution_suggestion=(
                                f"Resolve: '{source_name}' cannot both support "
                                f"and contradict '{target_name}'. Re-examine the "
                                f"evidence and remove or weaken one relationship."
                            ),
                        )
                        results.append(cr)
                        await self._persist_contradiction(cr)
                    else:
                        # Indirect: A supports B, A contradicts C — check if
                        # B SIMILAR_TO C (via any path)
                        all_rels_map = await self._get_all_relationships()
                        similar_pairs = {
                            (r.source_concept_id, r.target_concept_id)
                            for r in all_rels_map
                            if r.relationship_type == RelationshipType.SIMILAR_TO
                        }
                        b_c_similar = (
                            (target_s, target_c) in similar_pairs
                            or (target_c, target_s) in similar_pairs
                        )
                        if b_c_similar:
                            pair_key = frozenset({s_rel.id, c_rel.id})
                            if pair_key in seen_pairs:
                                continue
                            seen_pairs.add(pair_key)

                            source_concept = await self._get_concept(source_id)
                            source_name = source_concept.name if source_concept else source_id
                            t_s = await self._get_concept(target_s)
                            t_c = await self._get_concept(target_c)
                            ts_name = t_s.name if t_s else target_s
                            tc_name = t_c.name if t_c else target_c

                            cr = ContradictionResult(
                                concept_id_1=target_s,
                                concept_id_2=target_c,
                                description=(
                                    f"'{source_name}' SUPPORTS '{ts_name}' and "
                                    f"CONTRADICTS '{tc_name}', which are similar"
                                ),
                                severity=0.6,
                                resolution_suggestion=(
                                    f"'{ts_name}' and '{tc_name}' are similar yet "
                                    f"receive conflicting signals from '{source_name}'. "
                                    f"Clarify the distinction or consolidate."
                                ),
                            )
                            results.append(cr)
                            await self._persist_contradiction(cr)

            # If A IS_A B and A IS_A C where B and C contradict each other
            is_a_rels = [r for r in rels if r.relationship_type == RelationshipType.IS_A]
            for i_idx, r1 in enumerate(is_a_rels):
                for r2 in is_a_rels[i_idx + 1:]:
                    t1 = r1.target_concept_id
                    t2 = r2.target_concept_id
                    # Check if B contradicts C or C contradicts B
                    contradicts_between = any(
                        rr.relationship_type == RelationshipType.CONTRADICTS
                        and (
                            (rr.source_concept_id == t1 and rr.target_concept_id == t2)
                            or (rr.source_concept_id == t2 and rr.target_concept_id == t1)
                        )
                        for rr in all_rels
                    )
                    if contradicts_between:
                        pair_key = frozenset({r1.id, r2.id})
                        if pair_key in seen_pairs:
                            continue
                        seen_pairs.add(pair_key)

                        source_concept = await self._get_concept(source_id)
                        source_name = source_concept.name if source_concept else source_id
                        tc1 = await self._get_concept(t1)
                        tc2 = await self._get_concept(t2)
                        n1 = tc1.name if tc1 else t1
                        n2 = tc2.name if tc2 else t2

                        cr = ContradictionResult(
                            concept_id_1=t1,
                            concept_id_2=t2,
                            description=(
                                f"'{source_name}' IS_A '{n1}' and IS_A '{n2}', "
                                f"but '{n1}' and '{n2}' contradict each other"
                            ),
                            severity=0.7,
                            resolution_suggestion=(
                                f"'{source_name}' cannot simultaneously be a kind of "
                                f"both '{n1}' and '{n2}' if they contradict. "
                                f"Re-evaluate the classification."
                            ),
                        )
                        results.append(cr)
                        await self._persist_contradiction(cr)

        # Sort by severity descending
        results.sort(key=lambda r: r.severity, reverse=True)
        return results

    # ─── 3. discover_knowledge_gaps ────────────────────────────────────────

    async def discover_knowledge_gaps(self) -> list[KnowledgeGap]:
        """Identify gaps in the knowledge graph and belief system.

        Gap types:

        1. **Isolated concepts** — concepts with 0–1 relationships
           (importance 0.7).
        2. **Missing links** — A→B and B→C exist but A→C doesn't
           (importance 0.5).
        3. **Low-evidence beliefs** — beliefs with fewer than 2 supporting
           evidence items (importance 0.6).

        Returns
        -------
        list[KnowledgeGap]
            All discovered gaps, sorted by importance (descending).
        """
        gaps: list[KnowledgeGap] = []
        seen_descriptions: set[str] = set()

        all_concepts = await self._get_all_concepts()
        all_rels = await self._get_all_relationships()

        # Index: concept_id -> set of related concept_ids
        neighbours: dict[str, set[str]] = defaultdict(set)
        # Index: concept_id -> list of relationship objects
        concept_rels: dict[str, list[Relationship]] = defaultdict(list)
        for rel in all_rels:
            neighbours[rel.source_concept_id].add(rel.target_concept_id)
            neighbours[rel.target_concept_id].add(rel.source_concept_id)
            concept_rels[rel.source_concept_id].append(rel)
            concept_rels[rel.target_concept_id].append(rel)

        # --- 1. Isolated concepts ---
        for concept in all_concepts:
            n_rels = len(concept_rels.get(concept.id, []))
            if n_rels <= 1:
                desc = f"Isolated concept: '{concept.name}' has only {n_rels} relationship(s)"
                if desc not in seen_descriptions:
                    seen_descriptions.add(desc)
                    gap = KnowledgeGap(
                        description=desc,
                        related_concept_ids=[concept.id],
                        importance=0.7,
                        suggested_query=f"What is {concept.name} related to?",
                    )
                    gaps.append(gap)
                    await self._persist_gap(gap)

        # --- 2. Missing links (transitive gap) ---
        # If A→B and B→C exist but A→C doesn't
        existing_pairs: set[frozenset[str]] = set()
        for rel in all_rels:
            existing_pairs.add(frozenset({rel.source_concept_id, rel.target_concept_id}))

        # Build directed adjacency
        directed: dict[str, set[str]] = defaultdict(set)
        for rel in all_rels:
            directed[rel.source_concept_id].add(rel.target_concept_id)

        checked_pairs: set[frozenset[str]] = set()
        for a_id, b_set in directed.items():
            for b_id in b_set:
                for c_id in directed.get(b_id, set()):
                    if c_id == a_id:
                        continue
                    pair = frozenset({a_id, c_id})
                    if pair in checked_pairs:
                        continue
                    checked_pairs.add(pair)
                    # Check if direct A→C relationship exists
                    if c_id not in directed.get(a_id, set()):
                        a_concept = await self._get_concept(a_id)
                        c_concept = await self._get_concept(c_id)
                        a_name = a_concept.name if a_concept else a_id
                        c_name = c_concept.name if c_concept else c_id

                        desc = (
                            f"Missing link: '{a_name}' → '{c_name}' "
                            f"(reachable via intermediate, no direct relationship)"
                        )
                        if desc not in seen_descriptions:
                            seen_descriptions.add(desc)
                            gap = KnowledgeGap(
                                description=desc,
                                related_concept_ids=[a_id, c_id],
                                importance=0.5,
                                suggested_query=f"How does {a_name} relate to {c_name}?",
                            )
                            gaps.append(gap)
                            await self._persist_gap(gap)

        # --- 3. Low-evidence beliefs ---
        all_beliefs = await self._get_all_beliefs()
        for belief in all_beliefs:
            supporting_count = len(belief.supporting_evidence)
            if supporting_count < 2:
                desc = (
                    f"Low-evidence belief: '{belief.statement}' has only "
                    f"{supporting_count} supporting evidence(s)"
                )
                if desc not in seen_descriptions:
                    seen_descriptions.add(desc)
                    gap = KnowledgeGap(
                        description=desc,
                        related_concept_ids=belief.related_concept_ids,
                        importance=0.6,
                        suggested_query=f"What evidence supports {belief.statement}?",
                    )
                    gaps.append(gap)
                    await self._persist_gap(gap)

        # Sort by importance descending
        gaps.sort(key=lambda g: g.importance, reverse=True)
        return gaps

    # ─── 4. support_planning ───────────────────────────────────────────────

    async def support_planning(
        self,
        goal_description: str,
        max_suggestions: int = 5,
    ) -> list[KnowledgeGap]:
        """Identify knowledge gaps relevant to a goal and suggest subgoals.

        The method:

        1. Searches for concepts related to the goal description keywords.
        2. Discovers gaps connected to those concepts.
        3. Ranks gaps by proximity and importance.
        4. Returns up to *max_suggestions* gaps with subgoal suggestions.

        Parameters
        ----------
        goal_description:
            A natural-language description of the goal.
        max_suggestions:
            Maximum number of KnowledgeGap objects to return.

        Returns
        -------
        list[KnowledgeGap]
            Gaps relevant to the goal, limited to *max_suggestions*.
        """
        # Extract keywords from goal description (simple tokenisation)
        goal_lower = goal_description.lower()
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "and", "but", "or", "nor", "not", "so",
            "yet", "both", "either", "neither", "each", "every", "all",
            "any", "few", "more", "most", "other", "some", "such", "no",
            "only", "own", "same", "than", "too", "very", "just", "because",
            "how", "what", "when", "where", "which", "who", "whom", "why",
            "this", "that", "these", "those", "i", "me", "my", "we", "our",
            "you", "your", "he", "him", "his", "she", "her", "it", "its",
            "they", "them", "their",
        }
        keywords = [
            w for w in goal_lower.split()
            if w not in stop_words and len(w) > 2
        ]

        # Find concepts whose names or descriptions match keywords
        all_concepts = await self._get_all_concepts()
        matched_concept_ids: set[str] = set()
        for concept in all_concepts:
            text = f"{concept.name} {concept.description}".lower()
            if any(kw in text for kw in keywords):
                matched_concept_ids.add(concept.id)

        # Find beliefs related to the goal keywords
        all_beliefs = await self._get_all_beliefs()
        related_belief_ids: set[str] = set()
        for belief in all_beliefs:
            if any(kw in belief.statement.lower() for kw in keywords):
                related_belief_ids.add(belief.id)
                matched_concept_ids.update(belief.related_concept_ids)

        if not matched_concept_ids and not related_belief_ids:
            # No direct matches — return general gaps
            all_gaps = await self.discover_knowledge_gaps()
            return all_gaps[:max_suggestions]

        # Gather gaps specifically relevant to matched concepts
        relevant_gaps: list[KnowledgeGap] = []
        seen_descriptions: set[str] = set()

        # 1. Isolated matched concepts
        all_rels = await self._get_all_relationships()
        concept_rels: dict[str, list[Relationship]] = defaultdict(list)
        for rel in all_rels:
            concept_rels[rel.source_concept_id].append(rel)
            concept_rels[rel.target_concept_id].append(rel)

        for cid in matched_concept_ids:
            concept = await self._get_concept(cid)
            if concept is None:
                continue
            n_rels = len(concept_rels.get(cid, []))
            if n_rels <= 1:
                desc = (
                    f"Goal-relevant isolated concept: '{concept.name}' "
                    f"has only {n_rels} relationship(s)"
                )
                if desc not in seen_descriptions:
                    seen_descriptions.add(desc)
                    gap = KnowledgeGap(
                        description=desc,
                        related_concept_ids=[cid],
                        importance=0.8,  # higher importance because goal-relevant
                        suggested_query=(
                            f"To achieve goal '{goal_description}', "
                            f"what is {concept.name} related to?"
                        ),
                    )
                    relevant_gaps.append(gap)
                    await self._persist_gap(gap)

        # 2. Low-evidence beliefs related to the goal
        for belief in all_beliefs:
            if belief.id not in related_belief_ids:
                continue
            supporting_count = len(belief.supporting_evidence)
            if supporting_count < 2:
                desc = (
                    f"Goal-relevant low-evidence belief: "
                    f"'{belief.statement}' has only {supporting_count} "
                    f"supporting evidence(s)"
                )
                if desc not in seen_descriptions:
                    seen_descriptions.add(desc)
                    gap = KnowledgeGap(
                        description=desc,
                        related_concept_ids=belief.related_concept_ids,
                        importance=0.7,
                        suggested_query=(
                            f"To achieve goal '{goal_description}', "
                            f"what evidence supports: {belief.statement}?"
                        ),
                    )
                    relevant_gaps.append(gap)
                    await self._persist_gap(gap)

        # 3. Missing links between matched concepts
        directed: dict[str, set[str]] = defaultdict(set)
        for rel in all_rels:
            directed[rel.source_concept_id].add(rel.target_concept_id)

        matched_list = list(matched_concept_ids)
        for a_id in matched_list:
            for b_id in directed.get(a_id, set()):
                if b_id not in matched_concept_ids:
                    continue
                for c_id in directed.get(b_id, set()):
                    if c_id not in matched_concept_ids or c_id == a_id:
                        continue
                    if c_id not in directed.get(a_id, set()):
                        a_c = await self._get_concept(a_id)
                        c_c = await self._get_concept(c_id)
                        a_name = a_c.name if a_c else a_id
                        c_name = c_c.name if c_c else c_id
                        desc = (
                            f"Goal-relevant missing link: '{a_name}' → '{c_name}'"
                        )
                        if desc not in seen_descriptions:
                            seen_descriptions.add(desc)
                            gap = KnowledgeGap(
                                description=desc,
                                related_concept_ids=[a_id, c_id],
                                importance=0.6,
                                suggested_query=(
                                    f"To achieve goal '{goal_description}', "
                                    f"how does {a_name} relate to {c_name}?"
                                ),
                            )
                            relevant_gaps.append(gap)
                            await self._persist_gap(gap)

        # Sort by importance descending and cap
        relevant_gaps.sort(key=lambda g: g.importance, reverse=True)
        return relevant_gaps[:max_suggestions]

    # ─── 5. deduce ─────────────────────────────────────────────────────────

    async def deduce(
        self,
        premise_concept_ids: list[str],
        target_concept_id: str | None = None,
    ) -> list[InferenceResult]:
        """Deduce relationships from premise concepts.

        If *target_concept_id* is provided, attempt to find a reasoning path
        from the premises to the target.  If no target is given, find all
        concepts deducible from the premises.

        Parameters
        ----------
        premise_concept_ids:
            Concept IDs serving as starting premises.
        target_concept_id:
            Optional target concept to reach.

        Returns
        -------
        list[InferenceResult]
            Inferred relationships from premises.
        """
        if not premise_concept_ids:
            return []

        # Verify premises exist
        valid_premises: list[str] = []
        for pid in premise_concept_ids:
            concept = await self._get_concept(pid)
            if concept is not None:
                valid_premises.append(pid)

        if not valid_premises:
            return []

        # Build directed adjacency from all relationships
        all_rels = await self._get_all_relationships()
        outgoing: dict[str, list[Relationship]] = defaultdict(list)
        for rel in all_rels:
            outgoing[rel.source_concept_id].append(rel)

        results: list[InferenceResult] = []
        visited: set[str] = set()

        if target_concept_id is not None:
            # --- Targeted deduction: find path from any premise to target ---
            # BFS from each premise, looking for the target
            found_paths: list[tuple[list[str], list[Relationship]]] = []

            for start_id in valid_premises:
                # BFS queue entries: (current_id, concept_chain, rel_chain)
                queue: list[tuple[str, list[str], list[Relationship]]] = [
                    (start_id, [start_id], [])
                ]
                local_visited: set[str] = {start_id}

                while queue:
                    current_id, concept_chain, rel_chain = queue.pop(0)

                    if current_id == target_concept_id and len(rel_chain) > 0:
                        found_paths.append((list(concept_chain), list(rel_chain)))
                        continue  # keep looking for shorter/better paths

                    if len(rel_chain) >= 5:
                        continue  # depth limit for deduction

                    for rel in outgoing.get(current_id, []):
                        next_id = rel.target_concept_id
                        if next_id in concept_chain:
                            continue  # no cycles
                        if next_id in local_visited and next_id != target_concept_id:
                            continue
                        local_visited.add(next_id)
                        queue.append((
                            next_id,
                            concept_chain + [next_id],
                            rel_chain + [rel],
                        ))

            # Convert found paths to InferenceResults
            for concept_chain, rel_chain in found_paths:
                avg_conf = (
                    sum(r.confidence for r in rel_chain) / len(rel_chain)
                    if rel_chain
                    else 0.5
                )
                confidence = avg_conf ** len(rel_chain) if rel_chain else 0.0

                steps: list[str] = []
                for i, r in enumerate(rel_chain):
                    steps.append(
                        f"{concept_chain[i]} --[{r.relationship_type.value}]--> "
                        f"{concept_chain[i + 1]} (conf={r.confidence:.2f})"
                    )

                # Determine inference type from the chain
                if len(rel_chain) == 1:
                    inf_type = InferenceType.DEDUCTION
                else:
                    chain_types = {r.relationship_type for r in rel_chain}
                    if chain_types.issubset(TRANSITIVE_RELATIONSHIPS):
                        inf_type = InferenceType.TRANSITIVITY
                    elif all(
                        r.relationship_type == RelationshipType.IMPLIES
                        for r in rel_chain
                    ):
                        inf_type = InferenceType.TRANSITIVITY
                    else:
                        inf_type = InferenceType.DEDUCTION

                start_concept = await self._get_concept(concept_chain[0])
                end_concept = await self._get_concept(concept_chain[-1])
                start_name = start_concept.name if start_concept else concept_chain[0]
                end_name = end_concept.name if end_concept else concept_chain[-1]

                steps.append(
                    f"Deduced: {start_name} → {end_name} "
                    f"(via {len(rel_chain)}-step chain, conf={confidence:.2f})"
                )

                inference = InferenceResult(
                    inference_type=inf_type,
                    premise_concept_ids=concept_chain,
                    conclusion_concept_id=target_concept_id,
                    conclusion_description=(
                        f"{start_name} can be linked to {end_name} "
                        f"via a {len(rel_chain)}-step reasoning chain"
                    ),
                    relationship_type=rel_chain[-1].relationship_type,
                    confidence=confidence,
                    reasoning_chain=steps,
                )
                results.append(inference)
                await self._persist_inference(inference)

        else:
            # --- Untargeted deduction: find all reachable concepts ---
            reachable: dict[str, tuple[list[str], list[Relationship]]] = {}

            for start_id in valid_premises:
                queue: list[tuple[str, list[str], list[Relationship]]] = [
                    (start_id, [start_id], [])
                ]
                local_visited: set[str] = {start_id}

                while queue:
                    current_id, concept_chain, rel_chain = queue.pop(0)

                    if current_id not in reachable or len(rel_chain) < len(reachable[current_id][1]):
                        reachable[current_id] = (list(concept_chain), list(rel_chain))

                    if len(rel_chain) >= 5:
                        continue

                    for rel in outgoing.get(current_id, []):
                        next_id = rel.target_concept_id
                        if next_id in concept_chain:
                            continue
                        if next_id in local_visited:
                            continue
                        local_visited.add(next_id)
                        queue.append((
                            next_id,
                            concept_chain + [next_id],
                            rel_chain + [rel],
                        ))

            # Remove the premise concepts themselves from results
            for cid, (concept_chain, rel_chain) in reachable.items():
                if cid in valid_premises and not rel_chain:
                    continue  # skip starting points with no chain

                avg_conf = (
                    sum(r.confidence for r in rel_chain) / len(rel_chain)
                    if rel_chain
                    else 0.5
                )
                confidence = avg_conf ** len(rel_chain) if rel_chain else 0.5

                steps: list[str] = []
                for i, r in enumerate(rel_chain):
                    steps.append(
                        f"{concept_chain[i]} --[{r.relationship_type.value}]--> "
                        f"{concept_chain[i + 1]} (conf={r.confidence:.2f})"
                    )

                start_concept = await self._get_concept(concept_chain[0])
                end_concept = await self._get_concept(cid)
                start_name = start_concept.name if start_concept else concept_chain[0]
                end_name = end_concept.name if end_concept else cid

                if rel_chain:
                    inf_type = InferenceType.DEDUCTION
                    if len(rel_chain) > 1:
                        chain_types = {r.relationship_type for r in rel_chain}
                        if chain_types.issubset(TRANSITIVE_RELATIONSHIPS):
                            inf_type = InferenceType.TRANSITIVITY
                else:
                    inf_type = InferenceType.DEDUCTION

                steps.append(
                    f"Deduced: {start_name} → {end_name} "
                    f"(conf={confidence:.2f})"
                )

                inference = InferenceResult(
                    inference_type=inf_type,
                    premise_concept_ids=concept_chain,
                    conclusion_concept_id=cid,
                    conclusion_description=(
                        f"{start_name} can reach {end_name} "
                        f"via {len(rel_chain)}-step chain"
                    ),
                    relationship_type=(
                        rel_chain[-1].relationship_type if rel_chain else RelationshipType.RELATES_TO
                    ),
                    confidence=confidence,
                    reasoning_chain=steps,
                )
                results.append(inference)
                await self._persist_inference(inference)

        return results

    # ─── 6. validate_inference ─────────────────────────────────────────────

    async def validate_inference(
        self,
        inference_result: InferenceResult,
    ) -> tuple[bool, str]:
        """Check whether an inference is valid.

        Validation checks:

        1. All premise concepts exist in the knowledge graph.
        2. The reasoning chain contains no circular references.
        3. The confidence value is appropriate for the chain length.
        4. The conclusion concept exists (if provided).

        Parameters
        ----------
        inference_result:
            The inference to validate.

        Returns
        -------
        tuple[bool, str]
            ``(is_valid, reason)`` — *is_valid* is True when all checks pass.
        """
        # --- 1. Premise concepts exist ---
        for pid in inference_result.premise_concept_ids:
            concept = await self._get_concept(pid)
            if concept is None:
                return (
                    False,
                    f"Premise concept '{pid}' does not exist in the knowledge graph",
                )

        # --- 2. No circular reasoning ---
        seen: set[str] = set()
        for pid in inference_result.premise_concept_ids:
            if pid in seen:
                return (
                    False,
                    f"Circular reasoning detected: concept '{pid}' appears "
                    f"multiple times in the premise chain",
                )
            seen.add(pid)

        # Also check that conclusion is not in premises in a circular way.
        # In transitive inference the conclusion concept is naturally the last
        # element of the premise chain, which is fine.  Circular reasoning
        # occurs when the conclusion is the *first* premise (A→B→A) or appears
        # in the middle of the chain.
        if inference_result.conclusion_concept_id and len(inference_result.premise_concept_ids) > 1:
            non_terminal_premises = inference_result.premise_concept_ids[:-1]
            if inference_result.conclusion_concept_id in non_terminal_premises:
                return (
                    False,
                    f"Circular reasoning: conclusion concept "
                    f"'{inference_result.conclusion_concept_id}' appears as a "
                    f"non-terminal premise in the chain",
                )

        # --- 3. Confidence is appropriate ---
        chain_length = len(inference_result.premise_concept_ids)
        if chain_length > 1:
            # For transitive chains, confidence should decrease with length
            # The maximum reasonable confidence for a chain of length n is
            # 1.0^n = 1.0, but realistically it should be well below 1.0
            # for longer chains.
            max_reasonable_conf = 0.95 ** (chain_length - 1)
            if inference_result.confidence > max_reasonable_conf + 0.05:
                return (
                    False,
                    f"Confidence {inference_result.confidence:.2f} is too high "
                    f"for a {chain_length}-step chain "
                    f"(expected ≤ {max_reasonable_conf:.2f})",
                )

        if inference_result.confidence < 0.0 or inference_result.confidence > 1.0:
            return (
                False,
                f"Confidence {inference_result.confidence} is out of valid range [0, 1]",
            )

        # --- 4. Conclusion concept exists (if specified) ---
        if inference_result.conclusion_concept_id:
            concept = await self._get_concept(inference_result.conclusion_concept_id)
            if concept is None:
                return (
                    False,
                    f"Conclusion concept '{inference_result.conclusion_concept_id}' "
                    f"does not exist in the knowledge graph",
                )

        # --- 5. Reasoning chain is non-empty for non-trivial inferences ---
        if (
            len(inference_result.premise_concept_ids) > 1
            and not inference_result.reasoning_chain
        ):
            return (
                False,
                "Reasoning chain is empty for a multi-premise inference",
            )

        return (True, "Inference is valid")
