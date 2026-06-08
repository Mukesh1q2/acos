"""
Knowledge Fabric — concept graph with extraction, traversal, and search.

Provides the core knowledge representation layer for ACOS Runtime v0.2.
The KnowledgeFabric maintains an in-memory NetworkX directed graph for fast
traversal operations and a SQLite backing store for persistence.

Key capabilities:
- Rule-based concept / entity / relationship extraction from text
- Graph construction and traversal (BFS, shortest-path)
- Semantic (keyword) search with relevance ranking
- Memory provenance linking
- Graph statistics
"""

from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import networkx as nx

from acos.memory.store import StorageBackend
from acos.schemas.v2_models import (
    Concept,
    ConceptType,
    Entity,
    Relationship,
    RelationshipType,
    SourceReference,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _gen_id() -> str:
    return str(uuid.uuid4())


# ─── Stop-words (minimal set — no external deps) ─────────────────────────────

_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "must", "need", "dare",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further",
        "then", "once", "here", "there", "when", "where", "why", "how",
        "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "just", "because", "but", "and", "or",
        "if", "while", "about", "up", "also", "this", "that", "these",
        "those", "it", "its", "he", "she", "they", "them", "their",
        "we", "us", "our", "you", "your", "i", "me", "my", "which",
        "who", "whom", "what", "whose",
    }
)


# ─── Relationship extraction patterns ────────────────────────────────────────

_RELATIONSHIP_PATTERNS: list[tuple[re.Pattern[str], RelationshipType, str]] = [
    # (compiled regex, relationship_type, source_group / target_group order)
    # "X is a Y", "X is an Y"
    (
        re.compile(
            r"\b([A-Z][\w\s]+?)\s+is\s+(?:a|an)\s+([A-Z][\w\s]+?)\b",
            re.IGNORECASE,
        ),
        RelationshipType.IS_A,
        "source_is_target",
    ),
    # "X is part of Y"
    (
        re.compile(
            r"\b([A-Z][\w\s]+?)\s+is\s+part\s+of\s+([A-Z][\w\s]+?)\b",
            re.IGNORECASE,
        ),
        RelationshipType.PART_OF,
        "source_is_target",
    ),
    # "X depends on Y"
    (
        re.compile(
            r"\b([A-Z][\w\s]+?)\s+depends?\s+on\s+([A-Z][\w\s]+?)\b",
            re.IGNORECASE,
        ),
        RelationshipType.DEPENDS_ON,
        "source_is_target",
    ),
    # "X causes Y"
    (
        re.compile(
            r"\b([A-Z][\w\s]+?)\s+causes?\s+([A-Z][\w\s]+?)\b",
            re.IGNORECASE,
        ),
        RelationshipType.CAUSES,
        "source_is_target",
    ),
    # "X implies Y"
    (
        re.compile(
            r"\b([A-Z][\w\s]+?)\s+implies?\s+([A-Z][\w\s]+?)\b",
            re.IGNORECASE,
        ),
        RelationshipType.IMPLIES,
        "source_is_target",
    ),
    # "X is similar to Y"
    (
        re.compile(
            r"\b([A-Z][\w\s]+?)\s+is\s+similar\s+to\s+([A-Z][\w\s]+?)\b",
            re.IGNORECASE,
        ),
        RelationshipType.SIMILAR_TO,
        "source_is_target",
    ),
    # "X contradicts Y"
    (
        re.compile(
            r"\b([A-Z][\w\s]+?)\s+contradicts?\s+([A-Z][\w\s]+?)\b",
            re.IGNORECASE,
        ),
        RelationshipType.CONTRADICTS,
        "source_is_target",
    ),
    # "X supports Y"
    (
        re.compile(
            r"\b([A-Z][\w\s]+?)\s+supports?\s+([A-Z][\w\s]+?)\b",
            re.IGNORECASE,
        ),
        RelationshipType.SUPPORTS,
        "source_is_target",
    ),
    # "X precedes Y"
    (
        re.compile(
            r"\b([A-Z][\w\s]+?)\s+precedes?\s+([A-Z][\w\s]+?)\b",
            re.IGNORECASE,
        ),
        RelationshipType.PRECEDES,
        "source_is_target",
    ),
]


# ─── Main Class ───────────────────────────────────────────────────────────────


class KnowledgeFabric:
    """Knowledge Fabric — concept graph with extraction, traversal, and search.

    The fabric combines:
    * A **NetworkX DiGraph** for fast in-memory traversal (BFS, shortest path,
      neighbourhood queries).
    * A **SQLite** backing store (via ``StorageBackend``) for durable persistence.

    Typical lifecycle::

        store = StorageBackend()
        await store.initialize()

        fabric = KnowledgeFabric(store)
        await fabric.initialize()          # creates tables, loads graph

        concepts = fabric.extract_concepts("Python is a programming language")
        for c in concepts:
            await fabric.add_concept(c)

        results = await fabric.semantic_search("programming")
    """

    # ── Construction & Initialisation ───────────────────────────────────────

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._graph: nx.DiGraph = nx.DiGraph()
        # Lookup helpers — populated from DB on initialise
        self._concepts: dict[str, Concept] = {}
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}

    # ------------------------------------------------------------------
    # Async lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Create DB tables (if needed) and load existing data into the graph."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        """Ensure all Knowledge Fabric tables exist in the SQLite DB."""
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS concepts (
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

            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                entity_type TEXT DEFAULT 'generic',
                description TEXT DEFAULT '',
                mentions INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.8,
                source_ids TEXT DEFAULT '[]',
                concept_id TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS relationships (
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

            CREATE TABLE IF NOT EXISTS source_references (
                id TEXT PRIMARY KEY,
                memory_id TEXT,
                thread_id TEXT,
                session_id TEXT,
                content_snippet TEXT DEFAULT '',
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(name);
            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
            CREATE INDEX IF NOT EXISTS idx_relationships_source
                ON relationships(source_concept_id);
            CREATE INDEX IF NOT EXISTS idx_relationships_target
                ON relationships(target_concept_id);
            """
        )
        await conn.commit()

    async def _load_from_db(self) -> None:
        """Load all persisted concepts, entities, and relationships into memory."""
        conn = self._storage._conn
        assert conn is not None

        # ── concepts ──
        cursor = await conn.execute("SELECT * FROM concepts")
        rows = await cursor.fetchall()
        for row in rows:
            concept = self._row_to_concept(row)
            self._concepts[concept.id] = concept
            self._graph.add_node(concept.id, concept=concept)

        # ── entities ──
        cursor = await conn.execute("SELECT * FROM entities")
        rows = await cursor.fetchall()
        for row in rows:
            entity = self._row_to_entity(row)
            self._entities[entity.id] = entity

        # ── relationships ──
        cursor = await conn.execute("SELECT * FROM relationships")
        rows = await cursor.fetchall()
        for row in rows:
            rel = self._row_to_relationship(row)
            self._relationships[rel.id] = rel
            # Only add edge if both endpoint concepts exist
            if rel.source_concept_id in self._concepts and rel.target_concept_id in self._concepts:
                self._graph.add_edge(
                    rel.source_concept_id,
                    rel.target_concept_id,
                    relationship=rel,
                )

    # ------------------------------------------------------------------
    # Row → Pydantic mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_concept(row: Any) -> Concept:
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
            access_count=row["access_count"],
        )

    @staticmethod
    def _row_to_entity(row: Any) -> Entity:
        return Entity(
            id=row["id"],
            name=row["name"],
            entity_type=row["entity_type"] or "generic",
            description=row["description"] or "",
            mentions=row["mentions"],
            confidence=row["confidence"],
            source_ids=json.loads(row["source_ids"]) if row["source_ids"] else [],
            concept_id=row["concept_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_relationship(row: Any) -> Relationship:
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

    # ──────────────────────────────────────────────────────────────────────
    # 1. Concept Extraction
    # ──────────────────────────────────────────────────────────────────────

    def extract_concepts(self, text: str) -> list[Concept]:
        """Extract concepts from *text* using rule-based heuristics.

        Strategies:
        1. **Quoted phrases** — anything inside double-quotes.
        2. **Capitalised multi-word phrases** — sequences of 2+ title-cased
           words (skip sentence-initial position heuristically).
        3. **Technical identifiers** — ``camelCase``, ``snake_case``, dotted
           names like ``module.submodule.Class``.
        4. **Known technical suffixes** — words ending in *-tion*, *-ment*,
           *-ness*, *-ity*, *-ism*, *-ology*, *-graphy*.
        5. **High-frequency nouns** — words that appear ≥ 2 times, are not
           stop-words, and are longer than 3 characters.

        Each extracted concept is assigned a :class:`ConceptType` based on
        simple heuristics and a confidence score reflecting extraction
        certainty.
        """
        if not text or not text.strip():
            return []

        concepts: list[Concept] = []
        seen_names: set[str] = set()  # deduplicate by lowercased name

        # 1. Quoted phrases — high confidence
        for match in re.finditer(r'"([^"]{2,80})"', text):
            name = match.group(1).strip()
            key = name.lower()
            if key not in seen_names:
                seen_names.add(key)
                ctype = self._classify_concept_type(name)
                concepts.append(
                    Concept(
                        name=name,
                        concept_type=ctype,
                        description=f"Extracted from text: «{name}»",
                        confidence=0.9,
                    )
                )

        # 2. Capitalised multi-word phrases — first word title-cased,
        #    subsequent words may be any case.  This catches phrases like
        #    "Machine learning", "Natural language", "Deep learning".
        #    We limit phrases to 2-4 words and exclude common verbs
        #    that typically follow a concept name.

        _common_verbs = frozenset({
            "is", "are", "was", "were", "be", "been", "being",
            "has", "have", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might",
            "can", "must", "shall", "need",
            "goes", "go", "comes", "come", "makes", "make",
            "gets", "get", "takes", "take", "gives", "give",
            "depends", "causes", "implies", "supports", "precedes",
            "contradicts", "uses", "requires", "allows", "enables",
        })

        def _is_phrase_word(w: str) -> bool:
            """Return True if *w* is likely part of a noun phrase."""
            return len(w) >= 2 and w.lower() not in _common_verbs and w.lower() not in _STOP_WORDS

        # Extract candidate multi-word phrases (2–4 words, first word capitalised)
        for match in re.finditer(
            r"\b([A-Z][a-zA-Z]+(?:\s+[a-zA-Z]{2,}){1,3})\b", text
        ):
            raw = match.group(1).strip()
            # Trim trailing words that are common verbs
            words = raw.split()
            end = len(words)
            for i in range(1, len(words)):
                if words[i].lower() in _common_verbs or words[i].lower() in _STOP_WORDS:
                    end = i
                    break
            if end < 2:
                continue  # single word — handled elsewhere
            phrase_words = words[:end]
            name = " ".join(phrase_words)
            key = name.lower()
            if key not in seen_names and len(name) > 3:
                seen_names.add(key)
                ctype = self._classify_concept_type(name)
                # Higher confidence if not at sentence start
                start_pos = match.start()
                is_sentence_start = start_pos == 0 or (
                    start_pos > 1 and text[start_pos - 2] in ".!?"
                )
                concepts.append(
                    Concept(
                        name=name,
                        concept_type=ctype,
                        description=f"Extracted from text: \u00ab{name}\u00bb",
                        confidence=0.8 if not is_sentence_start else 0.65,
                    )
                )

        # 3. Single capitalised words — likely proper nouns or domain terms.
        #    Mid-sentence position (e.g. "... using Python for ...") is higher
        #    confidence than sentence-initial (which could be a common word
        #    that just got capitalised).
        #    Mid-sentence:
        for match in re.finditer(r"(?<=[a-z,;:]\s)([A-Z][a-z]{2,})\b", text):
            name = match.group(1).strip()
            key = name.lower()
            if key not in seen_names and key not in _STOP_WORDS:
                seen_names.add(key)
                ctype = self._classify_concept_type(name)
                concepts.append(
                    Concept(
                        name=name,
                        concept_type=ctype,
                        description=f"Capitalised term: {name}",
                        confidence=0.75,
                    )
                )

        #    Sentence-initial: only accept if the word is NOT a common
        #    English word (longer heuristic check) and not a stop-word.
        _common_sentence_starters = frozenset({
            "the", "this", "that", "these", "those", "there", "then",
            "they", "their", "them", "we", "when", "where", "what",
            "which", "while", "with", "without", "after", "although",
            "although", "because", "before", "between", "both", "but",
            "each", "every", "for", "from", "however", "if", "in",
            "instead", "it", "its", "just", "many", "more", "most",
            "neither", "never", "no", "nor", "not", "once", "only",
            "or", "since", "so", "some", "still", "such", "than",
            "therefore", "though", "thus", "until", "upon", "yet",
        })
        for match in re.finditer(r"(?:^|[.!?]\s)([A-Z][a-z]{2,})\b", text):
            name = match.group(1).strip()
            key = name.lower()
            if (
                key not in seen_names
                and key not in _STOP_WORDS
                and key not in _common_sentence_starters
            ):
                seen_names.add(key)
                ctype = self._classify_concept_type(name)
                concepts.append(
                    Concept(
                        name=name,
                        concept_type=ctype,
                        description=f"Sentence-initial term: {name}",
                        confidence=0.6,
                    )
                )

        # 4. Technical identifiers — camelCase, snake_case, dotted names
        for match in re.finditer(
            r"\b([a-z]+[A-Z][a-zA-Z]*|[a-z]+(?:_[a-z]+){1,}|[A-Z][a-zA-Z]*(?:\.[A-Z][a-zA-Z]*)+)\b",
            text,
        ):
            name = match.group(1).strip()
            key = name.lower()
            if key not in seen_names and len(name) > 2:
                seen_names.add(key)
                concepts.append(
                    Concept(
                        name=name,
                        concept_type=ConceptType.PROCESS,
                        description=f"Technical term: {name}",
                        confidence=0.85,
                    )
                )

        # 5. Suffix-based extraction — words ending in characteristic
        #    suffixes that signal abstract concepts or processes.
        suffix_pattern = (
            r"\b([A-Za-z]{4,}(?:"
            r"tion|sion|ment|ness|ity|ism|ology|graphy|ics|dom|ship|ance|ence"
            r"|ing|able|ible|al|ive|ous|ful|less|er|or"
            r"))\b"
        )
        for match in re.finditer(suffix_pattern, text):
            name = match.group(1).strip()
            key = name.lower()
            if key not in seen_names and key not in _STOP_WORDS and len(name) > 4:
                seen_names.add(key)
                ctype = self._classify_concept_type(name)
                concepts.append(
                    Concept(
                        name=name,
                        concept_type=ctype,
                        description=f"Extracted concept: {name}",
                        confidence=0.65,
                    )
                )

        # 6. High-frequency content words (appear >= 2 times, not stop-words)
        word_freq: dict[str, int] = defaultdict(int)
        for word in re.findall(r"\b([A-Za-z]{4,})\b", text):
            wl = word.lower()
            if wl not in _STOP_WORDS:
                word_freq[wl] += 1

        for word_lower, freq in word_freq.items():
            if freq >= 2 and word_lower not in seen_names:
                seen_names.add(word_lower)
                # Use the first original-cased occurrence
                original = word_lower
                for m in re.finditer(rf"\b({re.escape(word_lower)})\b", text, re.IGNORECASE):
                    original = m.group(1)
                    break
                ctype = self._classify_concept_type(original)
                concepts.append(
                    Concept(
                        name=original,
                        concept_type=ctype,
                        description=f"Frequent term ({freq} occurrences)",
                        confidence=min(0.5 + 0.1 * freq, 0.9),
                    )
                )

        return concepts

    # ------------------------------------------------------------------
    # Concept-type heuristic
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_concept_type(name: str) -> ConceptType:
        """Heuristically assign a ConceptType to an extracted name."""
        lower = name.lower()

        # Process indicators
        process_keywords = (
            "algorithm", "method", "process", "procedure", "function",
            "operation", "protocol", "technique", "approach", "strategy",
            "pipeline", "workflow", "framework",
        )
        if any(kw in lower for kw in process_keywords):
            return ConceptType.PROCESS

        # Event indicators
        event_keywords = (
            "event", "trigger", "completion", "failure", "success",
            "start", "end", "initiation", "termination", "occurrence",
        )
        if any(kw in lower for kw in event_keywords):
            return ConceptType.EVENT

        # Property indicators
        property_keywords = (
            "accuracy", "precision", "recall", "speed", "rate", "score",
            "level", "index", "factor", "metric", "measure", "value",
            "threshold", "capacity", "efficiency",
        )
        if any(kw in lower for kw in property_keywords):
            return ConceptType.PROPERTY

        # Concrete indicators — versioned names, proper nouns, etc.
        if re.search(r"\d", name):  # contains digits → likely concrete/versioned
            return ConceptType.CONCRETE
        if name.isupper() and len(name) > 1:  # ALL CAPS → acronym / concrete
            return ConceptType.CONCRETE

        # Default
        return ConceptType.ABSTRACT

    # ──────────────────────────────────────────────────────────────────────
    # 2. Entity Extraction
    # ──────────────────────────────────────────────────────────────────────

    def extract_entities(self, text: str) -> list[Entity]:
        """Extract named entities from *text* using rule-based heuristics.

        Detects:
        * **Names** — sequences of capitalised words (2+ tokens) not at
          sentence start.
        * **Technical terms** — identifiers with ``camelCase``,
          ``snake_case``, versioned names (e.g. ``Python 3.12``).
        * **Quantities** — number + unit pairs (``5 kg``, ``100 ms``).
        * **Dates** — common date patterns (ISO-ish, Month Day, etc.).
        * **Proper nouns in quotes** — single-word quoted terms.
        """
        if not text or not text.strip():
            return []

        entities: list[Entity] = []
        seen_names: set[str] = set()

        # 1. Named persons / organisations — capitalised multi-word
        #    after a non-sentence-ending character
        for match in re.finditer(
            r"(?<=[a-z,;:\"'\s])([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", text
        ):
            name = match.group(1).strip()
            key = name.lower()
            if key not in seen_names:
                seen_names.add(key)
                etype = self._classify_entity_type(name)
                entities.append(
                    Entity(
                        name=name,
                        entity_type=etype,
                        description=f"Named entity: {name}",
                        confidence=0.8,
                    )
                )

        # 2. Technical terms
        for match in re.finditer(
            r"\b([a-z]+[A-Z][a-zA-Z]*|[a-z]+(?:_[a-z]+){1,}|[A-Z][a-zA-Z]*(?:\.[A-Z][a-zA-Z]*)+)\b",
            text,
        ):
            name = match.group(1).strip()
            key = name.lower()
            if key not in seen_names and len(name) > 2:
                seen_names.add(key)
                entities.append(
                    Entity(
                        name=name,
                        entity_type="technology",
                        description=f"Technical entity: {name}",
                        confidence=0.85,
                    )
                )

        # 3. Versioned / numbered names — e.g. "Python 3.12", "GPT-4"
        for match in re.finditer(
            r"\b([A-Z][a-zA-Z]*(?:[-\s]\d[\d.]*)+)", text
        ):
            name = match.group(1).strip()
            key = name.lower()
            if key not in seen_names:
                seen_names.add(key)
                entities.append(
                    Entity(
                        name=name,
                        entity_type="technology",
                        description=f"Versioned entity: {name}",
                        confidence=0.9,
                    )
                )

        # 4. Quantities — number + unit
        for match in re.finditer(
            r"\b(\d+(?:\.\d+)?)\s*(ms|s|kg|g|mb|gb|tb|kb|hz|mhz|ghz|px|pt|km|mi|ft|in|cm|mm|%|percent)\b",
            text,
            re.IGNORECASE,
        ):
            quantity = f"{match.group(1)} {match.group(2)}"
            key = quantity.lower()
            if key not in seen_names:
                seen_names.add(key)
                entities.append(
                    Entity(
                        name=quantity,
                        entity_type="quantity",
                        description=f"Quantity: {quantity}",
                        confidence=0.95,
                    )
                )

        # 5. Date patterns
        for match in re.finditer(
            r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s*\d{4})\b",
            text,
        ):
            date_str = match.group(1).strip()
            key = date_str.lower()
            if key not in seen_names:
                seen_names.add(key)
                entities.append(
                    Entity(
                        name=date_str,
                        entity_type="date",
                        description=f"Date: {date_str}",
                        confidence=0.9,
                    )
                )

        # 6. Single-word proper nouns in quotes
        for match in re.finditer(r'"([A-Z][a-z]+)"', text):
            name = match.group(1).strip()
            key = name.lower()
            if key not in seen_names and key not in _STOP_WORDS:
                seen_names.add(key)
                entities.append(
                    Entity(
                        name=name,
                        entity_type="proper_noun",
                        description=f"Quoted proper noun: {name}",
                        confidence=0.7,
                    )
                )

        return entities

    # ------------------------------------------------------------------
    # Entity-type heuristic
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_entity_type(name: str) -> str:
        """Heuristically assign an entity type string to an extracted name."""
        lower = name.lower()

        person_indicators = ("mr", "mrs", "dr", "prof", "sir", "president")
        if any(lower.startswith(p) for p in person_indicators):
            return "person"

        org_indicators = ("inc", "corp", "ltd", "llc", "university", "institute", "foundation", "company")
        if any(ind in lower for ind in org_indicators):
            return "organisation"

        tech_indicators = (
            "python", "java", "rust", "docker", "kubernetes", "api", "http",
            "sql", "redis", "postgres", "linux", "aws", "gcp", "azure",
            "react", "vue", "angular", "node", "tensorflow", "pytorch",
        )
        if any(ind in lower for ind in tech_indicators):
            return "technology"

        location_indicators = ("city", "country", "state", "river", "mountain", "lake", "island")
        if any(ind in lower for ind in location_indicators):
            return "location"

        return "generic"

    # ──────────────────────────────────────────────────────────────────────
    # 3. Relationship Extraction
    # ──────────────────────────────────────────────────────────────────────

    def extract_relationships(
        self,
        text: str,
        concepts: list[Concept],
    ) -> list[Relationship]:
        """Infer relationships between *concepts* found in *text*.

        Uses linguistic pattern matching to detect common relationship
        patterns such as ``"X is a Y"``, ``"X depends on Y"``, etc.

        The *concepts* list is used to resolve matched names to concept IDs.
        If a pattern refers to names that are not in *concepts*, a new
        (placeholder) Concept is **not** created — the match is skipped.
        Callers that want auto-creation should merge extracted concepts into
        the fabric first.

        A fallback co-occurrence heuristic also creates ``RELATES_TO``
        edges between concepts that appear in the same sentence.
        """
        if not text or not text.strip() or not concepts:
            return []

        relationships: list[Relationship] = []
        seen_pairs: set[tuple[str, str, str]] = set()  # (src, tgt, type)

        # Build name → concept lookup (case-insensitive)
        name_to_concept: dict[str, Concept] = {}
        for concept in concepts:
            name_to_concept[concept.name.lower()] = concept
            # Also index individual words for partial matches
            for word in concept.name.split():
                if word.lower() not in name_to_concept:
                    name_to_concept[word.lower()] = concept

        # ── Pattern-based extraction ──
        for pattern, rel_type, _order in _RELATIONSHIP_PATTERNS:
            for match in pattern.finditer(text):
                source_name = match.group(1).strip()
                target_name = match.group(2).strip()

                src_concept = self._resolve_concept(source_name, name_to_concept)
                tgt_concept = self._resolve_concept(target_name, name_to_concept)

                if src_concept is None or tgt_concept is None:
                    continue
                if src_concept.id == tgt_concept.id:
                    continue

                pair_key = (src_concept.id, tgt_concept.id, rel_type.value)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                relationships.append(
                    Relationship(
                        source_concept_id=src_concept.id,
                        target_concept_id=tgt_concept.id,
                        relationship_type=rel_type,
                        description=f"{source_name} → {rel_type.value} → {target_name}",
                        confidence=0.8,
                    )
                )

        # ── Co-occurrence heuristic ──
        # Split text into sentences; if two concepts appear in the same
        # sentence, add a RELATES_TO edge (lower confidence).
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sentence in sentences:
            found_in_sentence: list[Concept] = []
            for concept in concepts:
                # Check if concept name (or its core word) appears in sentence
                cname = concept.name.lower()
                if cname in sentence.lower():
                    found_in_sentence.append(concept)
                    continue
                # Check individual words
                for word in concept.name.split():
                    if len(word) > 3 and word.lower() in sentence.lower():
                        found_in_sentence.append(concept)
                        break

            # Create RELATES_TO pairs
            for i in range(len(found_in_sentence)):
                for j in range(i + 1, len(found_in_sentence)):
                    c1 = found_in_sentence[i]
                    c2 = found_in_sentence[j]
                    if c1.id == c2.id:
                        continue
                    # Avoid duplicating an already-extracted relationship
                    pair_key_forward = (c1.id, c2.id, RelationshipType.RELATES_TO.value)
                    pair_key_backward = (c2.id, c1.id, RelationshipType.RELATES_TO.value)
                    if pair_key_forward in seen_pairs or pair_key_backward in seen_pairs:
                        continue
                    seen_pairs.add(pair_key_forward)

                    relationships.append(
                        Relationship(
                            source_concept_id=c1.id,
                            target_concept_id=c2.id,
                            relationship_type=RelationshipType.RELATES_TO,
                            description=f"Co-occurrence: {c1.name} ↔ {c2.name}",
                            confidence=0.5,
                        )
                    )

        return relationships

    # ------------------------------------------------------------------
    # Concept-name resolution helper
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_concept(
        name: str,
        lookup: dict[str, Concept],
    ) -> Concept | None:
        """Try to resolve a raw name string to a Concept from *lookup*.

        Resolution order:
        1. Exact lower-case match.
        2. Strip trailing whitespace/punctuation and retry.
        3. Match on the first word only.
        4. Substring match (any lookup key contained in *name*).
        """
        lower = name.lower().strip()

        # 1. Exact
        if lower in lookup:
            return lookup[lower]

        # 2. Stripped
        stripped = lower.rstrip(".,;:!?")
        if stripped in lookup:
            return lookup[stripped]

        # 3. First word
        first_word = lower.split()[0] if lower.split() else lower
        if first_word in lookup:
            return lookup[first_word]

        # 4. Substring — find a lookup key that is a substring of the name
        for key, concept in lookup.items():
            if key in lower or lower in key:
                return concept

        return None

    # ──────────────────────────────────────────────────────────────────────
    # 4. Knowledge Graph Operations
    # ──────────────────────────────────────────────────────────────────────

    async def add_concept(self, concept: Concept) -> Concept:
        """Add *concept* to the in-memory graph **and** persist to SQLite.

        If a concept with the same ``id`` already exists it is replaced
        (upsert semantics).
        """
        self._concepts[concept.id] = concept
        self._graph.add_node(concept.id, concept=concept)
        await self._persist_concept(concept)
        return concept

    async def add_relationship(self, relationship: Relationship) -> Relationship:
        """Add *relationship* as a directed edge in the graph and persist.

        Both endpoint concepts must already exist in the fabric; otherwise
        the relationship is persisted but the graph edge is skipped.
        """
        self._relationships[relationship.id] = relationship
        # Only add the edge if both endpoints exist
        if (
            relationship.source_concept_id in self._concepts
            and relationship.target_concept_id in self._concepts
        ):
            self._graph.add_edge(
                relationship.source_concept_id,
                relationship.target_concept_id,
                relationship=relationship,
            )
        await self._persist_relationship(relationship)
        return relationship

    async def add_entity(self, entity: Entity) -> Entity:
        """Add *entity* and persist to SQLite."""
        self._entities[entity.id] = entity
        await self._persist_entity(entity)
        return entity

    async def get_concept(self, concept_id: str) -> Concept | None:
        """Retrieve a concept by ID (memory-first, falls back to DB)."""
        concept = self._concepts.get(concept_id)
        if concept is not None:
            # Bump access count
            concept.access_count += 1
            concept.updated_at = _utc_now()
            self._concepts[concept_id] = concept
            await self._persist_concept(concept)
            return concept

        # Fallback: try DB
        conn = self._storage._conn
        assert conn is not None
        cursor = await conn.execute(
            "SELECT * FROM concepts WHERE id = ?", (concept_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        concept = self._row_to_concept(row)
        concept.access_count += 1
        concept.updated_at = _utc_now()
        self._concepts[concept_id] = concept
        self._graph.add_node(concept_id, concept=concept)
        await self._persist_concept(concept)
        return concept

    async def find_concept_by_name(self, name: str) -> Concept | None:
        """Find a concept by name with fuzzy matching.

        Resolution order:
        1. Exact (case-insensitive) match against in-memory concepts.
        2. Substring match — concept name contains *name* or vice-versa.
        3. Word-level overlap — any word in *name* matches a word in a
           concept name.
        """
        lower = name.lower().strip()
        if not lower:
            return None

        # 1. Exact
        for concept in self._concepts.values():
            if concept.name.lower() == lower:
                return concept

        # 2. Substring
        for concept in self._concepts.values():
            cname = concept.name.lower()
            if lower in cname or cname in lower:
                return concept

        # 3. Word overlap
        name_words = set(lower.split())
        best: Concept | None = None
        best_overlap = 0
        for concept in self._concepts.values():
            cwords = set(concept.name.lower().split())
            overlap = len(name_words & cwords)
            if overlap > best_overlap:
                best_overlap = overlap
                best = concept

        return best

    def get_related_concepts(
        self,
        concept_id: str,
        max_depth: int = 2,
    ) -> list[tuple[Concept, int]]:
        """Traverse the graph from *concept_id* up to *max_depth* hops.

        Returns a list of ``(concept, distance)`` pairs, sorted by
        distance then by concept name.  The starting concept itself is
        **not** included.
        """
        if concept_id not in self._graph:
            return []

        visited: dict[str, int] = {}  # node_id → distance
        frontier: list[tuple[str, int]] = [(concept_id, 0)]

        while frontier:
            node, dist = frontier.pop(0)
            if node in visited:
                continue
            visited[node] = dist
            if dist < max_depth:
                # Traverse both successors and predecessors (undirected BFS)
                for neighbour in self._graph.successors(node):
                    if neighbour not in visited:
                        frontier.append((neighbour, dist + 1))
                for neighbour in self._graph.predecessors(node):
                    if neighbour not in visited:
                        frontier.append((neighbour, dist + 1))

        results: list[tuple[Concept, int]] = []
        for node_id, distance in visited.items():
            if node_id == concept_id:
                continue
            concept = self._concepts.get(node_id)
            if concept is not None:
                results.append((concept, distance))

        results.sort(key=lambda pair: (pair[1], pair[0].name.lower()))
        return results

    def get_relationships(self, concept_id: str) -> list[Relationship]:
        """Return all relationships where *concept_id* is source or target."""
        results: list[Relationship] = []
        for rel in self._relationships.values():
            if (
                rel.source_concept_id == concept_id
                or rel.target_concept_id == concept_id
            ):
                results.append(rel)
        return results

    def get_path(
        self,
        concept_id_1: str,
        concept_id_2: str,
    ) -> list[str] | None:
        """Return the shortest path (list of concept IDs) between two concepts.

        Uses an **undirected** view of the graph so edges in either
        direction are traversable.  Returns ``None`` if no path exists.
        """
        if concept_id_1 not in self._graph or concept_id_2 not in self._graph:
            return None
        try:
            undirected = self._graph.to_undirected()
            path = nx.shortest_path(undirected, concept_id_1, concept_id_2)
            return path  # type: ignore[no-any-return]
        except nx.NetworkXNoPath:
            return None

    # ──────────────────────────────────────────────────────────────────────
    # 5. Semantic Search
    # ──────────────────────────────────────────────────────────────────────

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[tuple[Concept, float]]:
        """Search concepts by keyword / name / description.

        Returns a list of ``(concept, relevance_score)`` pairs sorted by
        descending relevance.  The relevance score combines:

        * **Name match** — exact (1.0), prefix (0.8), substring (0.6),
          word overlap (0.4).
        * **Description match** — query terms found in description (+0.3).
        * **Confidence boost** — concept confidence multiplied by 0.2.

        All matching is case-insensitive.
        """
        if not query or not query.strip():
            return []

        query_lower = query.lower().strip()
        query_words = set(query_lower.split())

        scored: list[tuple[Concept, float]] = []

        # Also search DB for concepts not yet in memory
        conn = self._storage._conn
        assert conn is not None
        cursor = await conn.execute(
            """SELECT * FROM concepts
               WHERE name LIKE ? OR description LIKE ?
               ORDER BY confidence DESC""",
            (f"%{query_lower}%", f"%{query_lower}%"),
        )
        db_rows = await cursor.fetchall()
        for row in db_rows:
            concept = self._row_to_concept(row)
            if concept.id not in self._concepts:
                self._concepts[concept.id] = concept
                self._graph.add_node(concept.id, concept=concept)

        for concept in self._concepts.values():
            score = self._compute_relevance(concept, query_lower, query_words)
            if score > 0:
                scored.append((concept, score))

        scored.sort(key=lambda pair: (-pair[1], pair[0].name.lower()))
        return scored[:limit]

    @staticmethod
    def _compute_relevance(
        concept: Concept,
        query_lower: str,
        query_words: set[str],
    ) -> float:
        """Compute a relevance score for *concept* against the search query."""
        name_lower = concept.name.lower()
        desc_lower = concept.description.lower()
        score = 0.0

        # ── Name matching ──
        if name_lower == query_lower:
            score += 1.0
        elif name_lower.startswith(query_lower):
            score += 0.8
        elif query_lower in name_lower:
            score += 0.6
        else:
            # Word-level overlap
            name_words = set(name_lower.split())
            overlap = len(query_words & name_words)
            if overlap > 0:
                score += 0.4 * (overlap / max(len(query_words), 1))

        # ── Description matching ──
        if desc_lower:
            desc_words = set(desc_lower.split())
            overlap = len(query_words & desc_words)
            if overlap > 0:
                score += 0.3 * (overlap / max(len(query_words), 1))
            elif query_lower in desc_lower:
                score += 0.2

        # ── Confidence boost ──
        score += concept.confidence * 0.2

        return score

    # ──────────────────────────────────────────────────────────────────────
    # 6. Memory Linking
    # ──────────────────────────────────────────────────────────────────────

    async def link_to_memory(
        self,
        concept_id: str,
        memory_id: str,
        source_reference: SourceReference | None = None,
    ) -> bool:
        """Link a concept to a memory record for provenance tracking.

        Adds *memory_id* to the concept's ``source_ids`` list (if not
        already present) and optionally stores a :class:`SourceReference`.

        Returns ``True`` if the link was created, ``False`` if the concept
        was not found or the link already existed.
        """
        concept = self._concepts.get(concept_id)
        if concept is None:
            return False

        if memory_id in concept.source_ids:
            return False  # already linked

        concept.source_ids.append(memory_id)
        concept.updated_at = _utc_now()
        self._concepts[concept_id] = concept
        await self._persist_concept(concept)

        # Optionally persist the source reference
        if source_reference is not None:
            await self._persist_source_reference(source_reference)
        else:
            # Auto-create a minimal source reference
            ref = SourceReference(
                memory_id=memory_id,
                content_snippet=f"Linked to concept: {concept.name}",
            )
            await self._persist_source_reference(ref)

        return True

    # ──────────────────────────────────────────────────────────────────────
    # 7. Graph Statistics
    # ──────────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics about the knowledge graph.

        Returns a dictionary with:
        * ``total_concepts``, ``total_entities``, ``total_relationships``
        * ``concept_type_distribution`` — dict mapping ConceptType → count
        * ``relationship_type_distribution`` — dict mapping RelationshipType → count
        * ``average_connectivity`` — mean degree (undirected)
        * ``connected_components`` — number of weakly connected components
        """
        # Concept type distribution
        concept_type_dist: dict[str, int] = defaultdict(int)
        for concept in self._concepts.values():
            concept_type_dist[concept.concept_type.value] += 1

        # Relationship type distribution
        rel_type_dist: dict[str, int] = defaultdict(int)
        for rel in self._relationships.values():
            rel_type_dist[rel.relationship_type.value] += 1

        # Average connectivity (undirected degree)
        num_nodes = self._graph.number_of_nodes()
        if num_nodes > 0:
            undirected = self._graph.to_undirected()
            avg_connectivity = sum(d for _, d in undirected.degree()) / num_nodes
        else:
            avg_connectivity = 0.0

        # Connected components
        if num_nodes > 0:
            components = nx.number_weakly_connected_components(self._graph)
        else:
            components = 0

        return {
            "total_concepts": len(self._concepts),
            "total_entities": len(self._entities),
            "total_relationships": len(self._relationships),
            "concept_type_distribution": dict(concept_type_dist),
            "relationship_type_distribution": dict(rel_type_dist),
            "average_connectivity": round(avg_connectivity, 3),
            "connected_components": components,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Persistence helpers (async)
    # ──────────────────────────────────────────────────────────────────────

    async def _persist_concept(self, concept: Concept) -> None:
        """Upsert a concept row into SQLite."""
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            """INSERT OR REPLACE INTO concepts
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
                concept.updated_at.isoformat(),
                concept.access_count,
            ),
        )
        await conn.commit()

    async def _persist_entity(self, entity: Entity) -> None:
        """Upsert an entity row into SQLite."""
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            """INSERT OR REPLACE INTO entities
               (id, name, entity_type, description, mentions, confidence,
                source_ids, concept_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entity.id,
                entity.name,
                entity.entity_type,
                entity.description,
                entity.mentions,
                entity.confidence,
                json.dumps(entity.source_ids),
                entity.concept_id,
                entity.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _persist_relationship(self, rel: Relationship) -> None:
        """Upsert a relationship row into SQLite."""
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            """INSERT OR REPLACE INTO relationships
               (id, source_concept_id, target_concept_id, relationship_type,
                description, confidence, weight, source_ids, properties,
                created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rel.id,
                rel.source_concept_id,
                rel.target_concept_id,
                rel.relationship_type.value,
                rel.description,
                rel.confidence,
                rel.weight,
                json.dumps(rel.source_ids),
                json.dumps(rel.properties),
                rel.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _persist_source_reference(self, ref: SourceReference) -> None:
        """Insert a source reference row into SQLite."""
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            """INSERT OR REPLACE INTO source_references
               (id, memory_id, thread_id, session_id, content_snippet,
                timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                ref.id,
                ref.memory_id,
                ref.thread_id,
                ref.session_id,
                ref.content_snippet,
                ref.timestamp.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Bulk Accessor Methods (used by CognitiveKernel) ────────────────────

    async def get_all_concepts(self) -> list[Concept]:
        """Return all concepts currently in the fabric."""
        return list(self._concepts.values())

    async def get_all_relationships(self) -> list[Relationship]:
        """Return all relationships currently in the fabric."""
        return list(self._relationships.values())

    async def get_all_entities(self) -> list[Entity]:
        """Return all entities currently in the fabric."""
        return list(self._entities.values())
