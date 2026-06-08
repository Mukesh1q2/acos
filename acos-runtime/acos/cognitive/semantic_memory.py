"""
Semantic Memory — concept-based long-term knowledge store with relationships and inference.

Replaces the simple text-based semantic memory from v0.1 with a structured concept
graph that supports:

- Concept CRUD with type classification and confidence tracking
- Directed, typed relationships between concepts (IS_A, PART_OF, CAUSES, etc.)
- Graph traversal (BFS) to discover related concepts at configurable depth
- Transitive relationship inference (if A→B and B→C, infer A→C)
- Natural-language-style keyword query against concept names, descriptions, and properties
- Consolidation from v0.1 episodic MemoryRecord objects into v0.2 concepts
- In-memory concept cache backed by SQLite persistence

Persistence is via the shared ``StorageBackend`` SQLite connection so that all
ACOS subsystems share a single database file.
"""

from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.models import MemoryRecord
from acos.schemas.v2_models import (
    Concept,
    ConceptType,
    Relationship,
    RelationshipType,
    SemanticConcept,
    SemanticQueryResult,
)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _gen_id() -> str:
    return str(uuid.uuid4())


# Simple stop-words for keyword extraction (no NLP library needed)
_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "it", "its", "this",
    "that", "these", "those", "i", "you", "he", "she", "we", "they", "me",
    "him", "her", "us", "them", "my", "your", "his", "our", "their", "what",
    "which", "who", "whom", "whose", "when", "where", "why", "how", "not",
    "no", "nor", "if", "then", "else", "so", "as", "than", "too", "very",
    "just", "about", "also", "some", "any", "each", "every", "all", "both",
    "few", "more", "most", "other", "such", "only", "same", "up", "out",
    "into", "over", "after", "before", "between", "under", "again",
})


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from text using simple heuristics.

    Strategy (no external NLP):
    1. Split on non-alphanumeric boundaries.
    2. Lower-case and drop stop-words and short tokens.
    3. Return de-duplicated, ordered list.
    """
    tokens = re.split(r"[^A-Za-z0-9_-]+", text)
    seen: set[str] = set()
    keywords: list[str] = []
    for tok in tokens:
        low = tok.lower().strip("_-")
        if len(low) < 2 or low in _STOP_WORDS:
            continue
        if low not in seen:
            seen.add(low)
            keywords.append(low)
    return keywords


def _extract_concepts_from_text(text: str) -> list[dict[str, Any]]:
    """Extract candidate concepts from free-form text.

    Heuristics (no NLP libraries):
    - Capitalized terms (multi-word if consecutive capitals) → CONCRETE
    - CamelCase / PascalCase identifiers → CONCRETE (technology names)
    - Quoted strings ("some concept") → ABSTRACT
    - Words following "how to" / "process of" → PROCESS
    - Remaining significant keywords → ABSTRACT
    """
    concepts: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    # 1. Quoted strings → ABSTRACT concepts
    for m in re.finditer(r'"([^"]+)"', text):
        name = m.group(1).strip()
        key = name.lower()
        if key not in seen_names and len(name) > 1:
            seen_names.add(key)
            concepts.append({"name": name, "concept_type": ConceptType.ABSTRACT})

    # 2. Consecutive capitalised words → CONCRETE entities (e.g. "Python 3", "New York")
    for m in re.finditer(r"\b([A-Z][a-z]*(?:\s+[A-Z][a-z]*)+)\b", text):
        name = m.group(1).strip()
        key = name.lower()
        if key not in seen_names and len(name) > 2:
            seen_names.add(key)
            concepts.append({"name": name, "concept_type": ConceptType.CONCRETE})

    # 3. PascalCase / camelCase identifiers (technology names, class names)
    for m in re.finditer(r"\b([A-Z][a-zA-Z0-9]*(?:[A-Z][a-zA-Z0-9]*)+)\b", text):
        name = m.group(1)
        key = name.lower()
        if key not in seen_names and len(name) > 2:
            seen_names.add(key)
            concepts.append({"name": name, "concept_type": ConceptType.CONCRETE})

    # 4. "how to X" / "process of X" patterns → PROCESS
    for m in re.finditer(r"(?:how\s+to|process\s+of|method\s+for|algorithm\s+for)\s+([a-z][\w\s]{2,40}?)", text, re.IGNORECASE):
        name = m.group(1).strip()
        key = name.lower()
        if key not in seen_names and len(name) > 2:
            seen_names.add(key)
            concepts.append({"name": name, "concept_type": ConceptType.PROCESS})

    # 5. Remaining significant keywords → ABSTRACT (fallback)
    keywords = _extract_keywords(text)
    for kw in keywords:
        if kw not in seen_names:
            seen_names.add(kw)
            concepts.append({"name": kw, "concept_type": ConceptType.ABSTRACT})

    return concepts


# ─── Semantic Memory ───────────────────────────────────────────────────────────

class SemanticMemory:
    """Semantic Memory — concept-based long-term knowledge store with relationships and inference.

    This module manages a knowledge graph of *Concepts* connected by typed
    *Relationships*, persisted in SQLite alongside the rest of the ACOS
    data.  A lightweight in-memory cache speeds up repeated lookups.

    Typical lifecycle::

        storage = StorageBackend()
        await storage.initialize()

        sem = SemanticMemory(storage)
        await sem.initialize()

        concept = await sem.store_concept(Concept(name="Python", concept_type=ConceptType.CONCRETE))
        await sem.link_concepts(python_id, programming_id, RelationshipType.IS_A)
        ctx = await sem.retrieve_concept_with_context(python_id)
    """

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        # Internal concept cache for fast retrieval
        self._concept_cache: dict[str, Concept] = {}

    # ─── Properties ──────────────────────────────────────────────────────────

    @property
    def _conn(self):
        """Shortcut to the shared SQLite connection managed by StorageBackend."""
        return self._storage._conn

    # ─── Initialization ──────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create semantic_concepts and semantic_relationships tables if they don't exist."""
        assert self._conn is not None, "StorageBackend must be initialised before SemanticMemory"
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS semantic_concepts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                concept_type TEXT NOT NULL,
                description TEXT DEFAULT '',
                properties TEXT DEFAULT '{}',
                confidence REAL DEFAULT 1.0,
                source_ids TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS semantic_relationships (
                id TEXT PRIMARY KEY,
                source_concept_id TEXT NOT NULL,
                target_concept_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                description TEXT DEFAULT '',
                confidence REAL DEFAULT 0.8,
                weight REAL DEFAULT 1.0,
                source_ids TEXT DEFAULT '[]',
                properties TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_semantic_concepts_name ON semantic_concepts(name);
            CREATE INDEX IF NOT EXISTS idx_semantic_concepts_type ON semantic_concepts(concept_type);
            CREATE INDEX IF NOT EXISTS idx_semantic_rel_source ON semantic_relationships(source_concept_id);
            CREATE INDEX IF NOT EXISTS idx_semantic_rel_target ON semantic_relationships(target_concept_id);
        """)
        await self._conn.commit()

        # Warm the concept cache from the DB
        await self._warm_cache()

    async def _warm_cache(self) -> None:
        """Load all concepts into the in-memory cache for fast lookups."""
        cursor = await self._conn.execute("SELECT * FROM semantic_concepts")
        rows = await cursor.fetchall()
        for row in rows:
            concept = self._row_to_concept(row)
            self._concept_cache[concept.id] = concept

    # ─── Row → Model helpers ─────────────────────────────────────────────────

    @staticmethod
    def _row_to_concept(row) -> Concept:
        """Convert an aiosqlite.Row (or dict-like) to a Concept model."""
        return Concept(
            id=row["id"],
            name=row["name"],
            concept_type=ConceptType(row["concept_type"]),
            description=row["description"] or "",
            properties=json.loads(row["properties"]) if row["properties"] else {},
            confidence=row["confidence"],
            source_ids=json.loads(row["source_ids"]) if row["source_ids"] else [],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            access_count=row["access_count"] or 0,
        )

    @staticmethod
    def _row_to_relationship(row) -> Relationship:
        """Convert an aiosqlite.Row (or dict-like) to a Relationship model."""
        return Relationship(
            id=row["id"],
            source_concept_id=row["source_concept_id"],
            target_concept_id=row["target_concept_id"],
            relationship_type=RelationshipType(row["relationship_type"]),
            description=row["description"] or "",
            confidence=row["confidence"],
            weight=row["weight"],
            source_ids=json.loads(row["source_ids"]) if row["source_ids"] else [],
            properties=json.loads(row["properties"]) if row["properties"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # ─── Store ───────────────────────────────────────────────────────────────

    async def store_concept(self, concept: Concept) -> Concept:
        """Store a concept in semantic memory.

        Persists the concept to SQLite and updates the in-memory cache.
        If a concept with the same ``id`` already exists it is replaced.

        Args:
            concept: The Concept to store.

        Returns:
            The stored Concept (unchanged).
        """
        assert self._conn is not None
        now = _utc_now().isoformat()
        await self._conn.execute(
            """INSERT OR REPLACE INTO semantic_concepts
               (id, name, concept_type, description, properties, confidence,
                source_ids, created_at, updated_at, access_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                concept.id,
                concept.name,
                concept.concept_type.value,
                concept.description,
                json.dumps(concept.properties),
                concept.confidence,
                json.dumps(concept.source_ids),
                concept.created_at.isoformat(),
                concept.updated_at.isoformat() if concept.updated_at else now,
                concept.access_count,
            ),
        )
        await self._conn.commit()
        self._concept_cache[concept.id] = concept
        return concept

    async def store_relationship(self, relationship: Relationship) -> Relationship:
        """Store a relationship between concepts.

        Persists the relationship to SQLite.

        Args:
            relationship: The Relationship to store.

        Returns:
            The stored Relationship (unchanged).
        """
        assert self._conn is not None
        await self._conn.execute(
            """INSERT OR REPLACE INTO semantic_relationships
               (id, source_concept_id, target_concept_id, relationship_type,
                description, confidence, weight, source_ids, properties, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                relationship.id,
                relationship.source_concept_id,
                relationship.target_concept_id,
                relationship.relationship_type.value,
                relationship.description,
                relationship.confidence,
                relationship.weight,
                json.dumps(relationship.source_ids),
                json.dumps(relationship.properties),
                relationship.created_at.isoformat(),
            ),
        )
        await self._conn.commit()
        return relationship

    # ─── Retrieve ────────────────────────────────────────────────────────────

    async def retrieve_concept(self, concept_id: str) -> Concept | None:
        """Get a concept by ID.

        Checks the in-memory cache first, then falls back to the database.
        Updates ``access_count`` and ``updated_at`` on each access.

        Args:
            concept_id: The unique identifier of the concept.

        Returns:
            The Concept if found, otherwise None.
        """
        # Cache hit
        if concept_id in self._concept_cache:
            concept = self._concept_cache[concept_id]
            concept.access_count += 1
            concept.updated_at = _utc_now()
            # Persist the access update asynchronously
            await self._update_concept_access(concept)
            return concept

        # Cache miss → DB
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT * FROM semantic_concepts WHERE id = ?", (concept_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        concept = self._row_to_concept(row)
        concept.access_count += 1
        concept.updated_at = _utc_now()
        await self._update_concept_access(concept)
        self._concept_cache[concept.id] = concept
        return concept

    async def _update_concept_access(self, concept: Concept) -> None:
        """Persist access_count and updated_at incrementally."""
        assert self._conn is not None
        await self._conn.execute(
            "UPDATE semantic_concepts SET access_count = ?, updated_at = ? WHERE id = ?",
            (concept.access_count, concept.updated_at.isoformat(), concept.id),
        )
        await self._conn.commit()

    async def retrieve_concept_by_name(
        self, name: str, fuzzy: bool = True
    ) -> list[Concept]:
        """Find concept(s) by name.

        Args:
            name: The name to search for.
            fuzzy: If True, uses case-insensitive substring matching.
                   If False, requires an exact (case-insensitive) match.

        Returns:
            List of matching Concepts (may be empty).
        """
        assert self._conn is not None
        if fuzzy:
            cursor = await self._conn.execute(
                "SELECT * FROM semantic_concepts WHERE name LIKE ? COLLATE NOCASE",
                (f"%{name}%",),
            )
        else:
            cursor = await self._conn.execute(
                "SELECT * FROM semantic_concepts WHERE name = ? COLLATE NOCASE",
                (name,),
            )
        rows = await cursor.fetchall()
        return [self._row_to_concept(r) for r in rows]

    async def retrieve_concept_with_context(self, concept_id: str) -> SemanticConcept | None:
        """Get a concept PLUS all its relationships and related concept names.

        This is the rich-retrieval method that returns a :class:`SemanticConcept`
        containing the concept itself, its relationships, and the names of all
        directly related concepts.

        Args:
            concept_id: The unique identifier of the concept.

        Returns:
            A SemanticConcept if the concept exists, otherwise None.
        """
        concept = await self.retrieve_concept(concept_id)
        if concept is None:
            return None

        relationships = await self.get_relationships(concept_id)

        # Collect names of all related concepts
        related_names: list[str] = []
        seen_ids: set[str] = set()
        for rel in relationships:
            for cid in (rel.source_concept_id, rel.target_concept_id):
                if cid != concept_id and cid not in seen_ids:
                    seen_ids.add(cid)
                    related_concept = await self.retrieve_concept(cid)
                    if related_concept:
                        related_names.append(related_concept.name)

        # Compute an aggregate confidence from concept + relationships
        rel_confidences = [r.confidence for r in relationships] if relationships else []
        avg_rel_conf = sum(rel_confidences) / len(rel_confidences) if rel_confidences else concept.confidence
        aggregate_confidence = (concept.confidence + avg_rel_conf) / 2.0

        return SemanticConcept(
            concept=concept,
            relationships=relationships,
            related_concept_names=related_names,
            confidence=aggregate_confidence,
            last_accessed=_utc_now(),
        )

    # ─── Semantic Query ──────────────────────────────────────────────────────

    async def semantic_query(self, query: str, limit: int = 10) -> SemanticQueryResult:
        """Natural language query against semantic memory.

        Extracts keywords from the query string and searches concept names,
        descriptions, and property values.  Also follows direct relationships
        of matched concepts to include related concepts in the results.

        Args:
            query: A natural-language query string.
            limit: Maximum number of top-level concepts to return.

        Returns:
            A SemanticQueryResult containing matched concepts and any
            inferred relationships discovered during the search.
        """
        assert self._conn is not None
        keywords = _extract_keywords(query)
        if not keywords:
            return SemanticQueryResult()

        matched_concepts: list[Concept] = []
        seen_ids: set[str] = set()

        # Search by keyword against name, description, and JSON properties
        for kw in keywords:
            cursor = await self._conn.execute(
                """SELECT * FROM semantic_concepts
                   WHERE name LIKE ? COLLATE NOCASE
                      OR description LIKE ? COLLATE NOCASE
                      OR properties LIKE ? COLLATE NOCASE
                   LIMIT ?""",
                (f"%{kw}%", f"%{kw}%", f"%{kw}%", limit),
            )
            rows = await cursor.fetchall()
            for row in rows:
                concept = self._row_to_concept(row)
                if concept.id not in seen_ids:
                    seen_ids.add(concept.id)
                    matched_concepts.append(concept)

        # Follow direct relationships of matched concepts to expand results
        expanded_concepts: list[Concept] = []
        for concept in list(matched_concepts):
            rels = await self.get_relationships(concept.id)
            for rel in rels:
                for cid in (rel.source_concept_id, rel.target_concept_id):
                    if cid not in seen_ids:
                        related = await self.retrieve_concept(cid)
                        if related:
                            seen_ids.add(cid)
                            expanded_concepts.append(related)

        # Build SemanticConcept list (matched concepts first, then expanded)
        all_concepts = matched_concepts + expanded_concepts[:max(0, limit - len(matched_concepts))]
        semantic_concepts: list[SemanticConcept] = []
        for concept in all_concepts:
            ctx = await self.retrieve_concept_with_context(concept.id)
            if ctx:
                semantic_concepts.append(ctx)

        # Discover inferred relationships among matched concepts
        inferred: list[Relationship] = []
        matched_ids = [c.id for c in matched_concepts]
        for i, id_a in enumerate(matched_ids):
            for id_b in matched_ids[i + 1:]:
                inferred.extend(await self.infer_relationship(id_a, id_b))

        # Compute query confidence as mean of matched concept confidences
        if matched_concepts:
            query_conf = sum(c.confidence for c in matched_concepts) / len(matched_concepts)
        else:
            query_conf = 0.0

        return SemanticQueryResult(
            concepts=semantic_concepts[:limit],
            inferred_relationships=inferred,
            total_matches=len(matched_concepts),
            query_confidence=query_conf,
        )

    # ─── Relationships ───────────────────────────────────────────────────────

    async def get_relationships(
        self,
        concept_id: str,
        relationship_type: RelationshipType | None = None,
    ) -> list[Relationship]:
        """Get all relationships involving a concept.

        A relationship is returned if the concept appears as either the
        source or the target.

        Args:
            concept_id: The concept to look up.
            relationship_type: If provided, only return relationships of
                this type.

        Returns:
            List of matching Relationship objects.
        """
        assert self._conn is not None
        if relationship_type is not None:
            cursor = await self._conn.execute(
                """SELECT * FROM semantic_relationships
                   WHERE (source_concept_id = ? OR target_concept_id = ?)
                     AND relationship_type = ?""",
                (concept_id, concept_id, relationship_type.value),
            )
        else:
            cursor = await self._conn.execute(
                """SELECT * FROM semantic_relationships
                   WHERE source_concept_id = ? OR target_concept_id = ?""",
                (concept_id, concept_id),
            )
        rows = await cursor.fetchall()
        return [self._row_to_relationship(r) for r in rows]

    async def get_related_concepts(
        self,
        concept_id: str,
        max_depth: int = 2,
    ) -> list[tuple[Concept, int]]:
        """Get concepts related to this one via relationships.

        Performs a breadth-first traversal up to *max_depth* hops away from
        the starting concept.  Each hop follows both outgoing (source→target)
        and incoming (target→source) relationships.

        Args:
            concept_id: The starting concept.
            max_depth: Maximum number of relationship hops to traverse.

        Returns:
            List of ``(Concept, distance)`` tuples sorted by distance
            (ascending).  The starting concept is NOT included.
        """
        assert self._conn is not None
        visited: dict[str, int] = {concept_id: 0}  # id → distance
        queue: deque[str] = deque([concept_id])

        while queue:
            current_id = queue.popleft()
            current_dist = visited[current_id]
            if current_dist >= max_depth:
                continue

            # Get all relationships for the current concept
            rels = await self.get_relationships(current_id)
            for rel in rels:
                neighbour_id = (
                    rel.target_concept_id
                    if rel.source_concept_id == current_id
                    else rel.source_concept_id
                )
                if neighbour_id not in visited:
                    visited[neighbour_id] = current_dist + 1
                    queue.append(neighbour_id)

        # Build results — skip the starting concept itself
        results: list[tuple[Concept, int]] = []
        for cid, dist in visited.items():
            if cid == concept_id:
                continue
            concept = await self.retrieve_concept(cid)
            if concept:
                results.append((concept, dist))

        results.sort(key=lambda t: t[1])
        return results

    # ─── Inference ───────────────────────────────────────────────────────────

    async def infer_relationship(
        self,
        concept_id_1: str,
        concept_id_2: str,
    ) -> list[Relationship]:
        """Check for a direct or transitive relationship between two concepts.

        If A→B and B→C relationships exist, a transitive relationship A→C
        can be inferred.  The inferred relationship's confidence is the
        product of the confidence values along the path, and its weight is
        the minimum weight on the path.

        Only short transitive chains (up to 4 hops) are explored to keep
        inference tractable.

        Args:
            concept_id_1: Source concept ID.
            concept_id_2: Target concept ID.

        Returns:
            List of inferred Relationship objects.  May be empty if no
            direct or transitive link is found.
        """
        # 1. Check for a direct relationship
        assert self._conn is not None
        cursor = await self._conn.execute(
            """SELECT * FROM semantic_relationships
               WHERE source_concept_id = ? AND target_concept_id = ?""",
            (concept_id_1, concept_id_2),
        )
        direct_rows = await cursor.fetchall()
        if direct_rows:
            return [self._row_to_relationship(r) for r in direct_rows]

        # 2. BFS for transitive paths (up to 4 hops)
        max_hops = 4
        # Each path entry: (current_node, path_of_relationships)
        queue: deque[tuple[str, list[Relationship]]] = deque(
            [(concept_id_1, [])]
        )
        visited_nodes: set[str] = {concept_id_1}
        inferred: list[Relationship] = []

        while queue:
            current_id, path = queue.popleft()
            if len(path) >= max_hops:
                continue

            # Get outgoing relationships from current node
            cursor = await self._conn.execute(
                "SELECT * FROM semantic_relationships WHERE source_concept_id = ?",
                (current_id,),
            )
            rows = await cursor.fetchall()

            for row in rows:
                rel = self._row_to_relationship(row)
                new_path = path + [rel]

                if rel.target_concept_id == concept_id_2:
                    # Found a transitive path!
                    chain_confidence = 1.0
                    chain_weight = float("inf")
                    rel_types: list[RelationshipType] = []

                    for step in new_path:
                        chain_confidence *= step.confidence
                        chain_weight = min(chain_weight, step.weight)
                        rel_types.append(step.relationship_type)

                    # The inferred relationship type follows the first step's type
                    # (this is a simplification; real inference would be type-aware)
                    inferred_type = rel_types[0]

                    # Build a human-readable chain description
                    chain_desc = " → ".join(
                        step.relationship_type.value for step in new_path
                    )

                    inferred_rel = Relationship(
                        id=_gen_id(),
                        source_concept_id=concept_id_1,
                        target_concept_id=concept_id_2,
                        relationship_type=inferred_type,
                        description=f"Inferred via transitive chain: {chain_desc}",
                        confidence=round(chain_confidence, 4),
                        weight=round(chain_weight, 4),
                        properties={
                            "inferred": True,
                            "chain_length": len(new_path),
                            "chain_description": chain_desc,
                        },
                    )
                    inferred.append(inferred_rel)
                elif rel.target_concept_id not in visited_nodes:
                    visited_nodes.add(rel.target_concept_id)
                    queue.append((rel.target_concept_id, new_path))

        return inferred

    # ─── Update ──────────────────────────────────────────────────────────────

    async def update_concept_confidence(
        self, concept_id: str, new_confidence: float
    ) -> Concept | None:
        """Update a concept's confidence score.

        Clamps the new confidence to [0.0, 1.0], persists the update to
        SQLite, and refreshes the cache.

        Args:
            concept_id: The concept to update.
            new_confidence: The new confidence value (will be clamped).

        Returns:
            The updated Concept, or None if the concept was not found.
        """
        concept = await self.retrieve_concept(concept_id)
        if concept is None:
            return None

        concept.confidence = max(0.0, min(1.0, new_confidence))
        concept.updated_at = _utc_now()
        await self.store_concept(concept)  # INSERT OR REPLACE
        return concept

    # ─── Link ────────────────────────────────────────────────────────────────

    async def link_concepts(
        self,
        concept_id_1: str,
        concept_id_2: str,
        relationship_type: RelationshipType = RelationshipType.RELATES_TO,
        description: str = "",
        confidence: float = 0.8,
    ) -> Relationship | None:
        """Create a new directed relationship between two concepts.

        Args:
            concept_id_1: Source concept ID.
            concept_id_2: Target concept ID.
            relationship_type: Type of relationship.
            description: Human-readable description of the relationship.
            confidence: Confidence score for the relationship [0, 1].

        Returns:
            The new Relationship, or None if either concept doesn't exist.
        """
        # Verify both concepts exist
        c1 = await self.retrieve_concept(concept_id_1)
        c2 = await self.retrieve_concept(concept_id_2)
        if c1 is None or c2 is None:
            return None

        relationship = Relationship(
            source_concept_id=concept_id_1,
            target_concept_id=concept_id_2,
            relationship_type=relationship_type,
            description=description,
            confidence=max(0.0, min(1.0, confidence)),
        )
        return await self.store_relationship(relationship)

    # ─── Consolidation from Episodic Memory ──────────────────────────────────

    async def consolidate_from_episodic(
        self, episodic_memories: list[MemoryRecord]
    ) -> dict[str, int]:
        """Bridge between v0.1 episodic memory and v0.2 semantic memory.

        Extracts concepts from the content of episodic MemoryRecord objects,
        creates or updates them in semantic memory, and creates relationships
        between concepts that co-occur in the same memory.

        The concept extraction uses simple heuristics (capitalised terms,
        quoted phrases, PascalCase identifiers, keyword patterns) — no
        external NLP libraries are required.

        Args:
            episodic_memories: A list of v0.1 MemoryRecord objects
                (typically of MemoryType.EPISODIC).

        Returns:
            A dict with keys ``concepts_created``, ``concepts_updated``,
            and ``relationships_created`` containing the respective counts.
        """
        concepts_created = 0
        concepts_updated = 0
        relationships_created = 0

        for memory in episodic_memories:
            # Extract candidate concepts from memory content
            extracted = _extract_concepts_from_text(memory.content)
            if not extracted:
                continue

            memory_concept_ids: list[str] = []

            for item in extracted:
                name = item["name"]
                concept_type = item["concept_type"]

                # Check if concept already exists (by exact name, case-insensitive)
                existing = await self.retrieve_concept_by_name(name, fuzzy=False)
                if existing:
                    # Update existing concept: increment confidence, add source
                    concept = existing[0]
                    concept.source_ids = list(set(concept.source_ids + [memory.id]))
                    concept.confidence = min(1.0, concept.confidence + 0.05)
                    concept.updated_at = _utc_now()
                    await self.store_concept(concept)
                    concepts_updated += 1
                    memory_concept_ids.append(concept.id)
                else:
                    # Create new concept
                    concept = Concept(
                        name=name,
                        concept_type=concept_type,
                        description=f"Extracted from episodic memory",
                        source_ids=[memory.id],
                        confidence=0.6,
                    )
                    await self.store_concept(concept)
                    concepts_created += 1
                    memory_concept_ids.append(concept.id)

            # Create RELATES_TO relationships between co-occurring concepts
            for i in range(len(memory_concept_ids)):
                for j in range(i + 1, len(memory_concept_ids)):
                    id_a = memory_concept_ids[i]
                    id_b = memory_concept_ids[j]

                    # Avoid duplicate relationships
                    if await self._relationship_exists(id_a, id_b):
                        continue

                    rel = Relationship(
                        source_concept_id=id_a,
                        target_concept_id=id_b,
                        relationship_type=RelationshipType.RELATES_TO,
                        description=f"Co-occurred in episodic memory {memory.id}",
                        confidence=0.5,
                        source_ids=[memory.id],
                    )
                    await self.store_relationship(rel)
                    relationships_created += 1

        return {
            "concepts_created": concepts_created,
            "concepts_updated": concepts_updated,
            "relationships_created": relationships_created,
        }

    async def _relationship_exists(
        self, source_id: str, target_id: str
    ) -> bool:
        """Check if a relationship already exists between two concepts (in either direction)."""
        assert self._conn is not None
        cursor = await self._conn.execute(
            """SELECT 1 FROM semantic_relationships
               WHERE (source_concept_id = ? AND target_concept_id = ?)
                  OR (source_concept_id = ? AND target_concept_id = ?)
               LIMIT 1""",
            (source_id, target_id, target_id, source_id),
        )
        row = await cursor.fetchone()
        return row is not None

    # ─── Statistics ──────────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        """Compute summary statistics about the semantic memory.

        Returns a dict containing:

        - ``total_concepts``: Total number of concepts.
        - ``total_relationships``: Total number of relationships.
        - ``concept_type_distribution``: Dict mapping ConceptType → count.
        - ``average_confidence``: Mean confidence across all concepts.
        - ``most_connected_concepts``: Top 5 concepts by relationship count.
        """
        assert self._conn is not None

        # Total concepts
        cursor = await self._conn.execute("SELECT COUNT(*) FROM semantic_concepts")
        total_concepts = (await cursor.fetchone())[0]

        # Total relationships
        cursor = await self._conn.execute("SELECT COUNT(*) FROM semantic_relationships")
        total_relationships = (await cursor.fetchone())[0]

        # Concept type distribution
        cursor = await self._conn.execute(
            "SELECT concept_type, COUNT(*) as cnt FROM semantic_concepts GROUP BY concept_type"
        )
        type_rows = await cursor.fetchall()
        type_distribution = {row["concept_type"]: row["cnt"] for row in type_rows}

        # Average confidence
        cursor = await self._conn.execute(
            "SELECT AVG(confidence) as avg_conf FROM semantic_concepts"
        )
        avg_row = await cursor.fetchone()
        avg_confidence = avg_row["avg_conf"] if avg_row["avg_conf"] is not None else 0.0

        # Most connected concepts (by total relationship count)
        cursor = await self._conn.execute("""
            SELECT concept_id, COUNT(*) as rel_count FROM (
                SELECT source_concept_id AS concept_id FROM semantic_relationships
                UNION ALL
                SELECT target_concept_id AS concept_id FROM semantic_relationships
            ) GROUP BY concept_id
            ORDER BY rel_count DESC
            LIMIT 5
        """)
        conn_rows = await cursor.fetchall()
        most_connected: list[dict[str, Any]] = []
        for row in conn_rows:
            concept = await self.retrieve_concept(row["concept_id"])
            most_connected.append({
                "concept_id": row["concept_id"],
                "name": concept.name if concept else "unknown",
                "relationship_count": row["rel_count"],
            })

        return {
            "total_concepts": total_concepts,
            "total_relationships": total_relationships,
            "concept_type_distribution": type_distribution,
            "average_confidence": round(avg_confidence, 4),
            "most_connected_concepts": most_connected,
        }
