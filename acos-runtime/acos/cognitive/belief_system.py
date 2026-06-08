"""
Belief System — manages beliefs with evidence, contradictions, and confidence evolution.

Part of the ACOS Runtime v0.2 Cognitive Architecture.  This module provides the
``BeliefState`` class, the single entry-point for creating, querying, and
evolving beliefs that the cognitive system holds about the world.

Key concepts
------------
* **Belief** – a proposition the system holds with a confidence score.
* **Evidence** – supporting or contradicting observations attached to a belief.
* **Confidence evolution** – confidence is adjusted by evidence using a
  Bayesian-inspired update rule (see ``_apply_evidence``).
* **Contradiction detection** – keyword / opposite-term heuristics surface
  conflicting beliefs for resolution.
* **Belief versioning** – when a belief is evolved or superseded, a new version
  is created and linked to the old one via ``parent_belief_id``.

Persistence
-----------
All beliefs are stored in a SQLite table (``beliefs``) managed through
:class:`~acos.memory.store.StorageBackend`.  List fields (evidence, concept
IDs) are serialised as JSON strings.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

import aiosqlite

from acos.schemas.v2_models import (
    Belief,
    BeliefStatus,
    Evidence,
    gen_id,
    utc_now,
)
from acos.memory.store import StorageBackend

# ─── Similarity threshold for "similar" belief statements ────────────────────
_STATEMENT_SIMILARITY_THRESHOLD = 0.80

# ─── Opposite-term pairs used by contradiction detection ─────────────────────
_OPPOSITE_PAIRS: list[tuple[str, str]] = [
    ("best", "worst"),
    ("good", "bad"),
    ("increase", "decrease"),
    ("rise", "fall"),
    ("positive", "negative"),
    ("true", "false"),
    ("always", "never"),
    ("possible", "impossible"),
    ("effective", "ineffective"),
    ("safe", "dangerous"),
    ("fast", "slow"),
    ("easy", "hard"),
    ("cheap", "expensive"),
    ("reliable", "unreliable"),
    ("efficient", "inefficient"),
    ("strong", "weak"),
    ("important", "unimportant"),
    ("necessary", "unnecessary"),
    ("better", "worse"),
    ("more", "less"),
    ("higher", "lower"),
    ("bigger", "smaller"),
    ("hot", "cold"),
    ("light", "dark"),
    ("open", "closed"),
    ("accept", "reject"),
    ("succeed", "fail"),
    ("win", "lose"),
    ("create", "destroy"),
    ("build", "tear down"),
]


class BeliefState:
    """Belief State — manages beliefs with evidence, contradictions, and confidence evolution.

    Usage::

        store = StorageBackend()
        await store.initialize()

        bs = BeliefState(store)
        await bs.initialize()

        belief = await bs.add_belief(
            statement="Python is the best language for AI",
            confidence=0.8,
            supporting_evidence=[Evidence(content="TIOBE index 2024", confidence=0.9)],
        )
    """

    def __init__(self, store: StorageBackend) -> None:
        self._store = store

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create the ``beliefs`` table and indexes if they do not exist."""
        assert self._store._conn is not None, "StorageBackend must be initialized first"
        await self._store._conn.executescript("""
            CREATE TABLE IF NOT EXISTS beliefs (
                id TEXT PRIMARY KEY,
                statement TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                status TEXT NOT NULL DEFAULT 'active',
                supporting_evidence TEXT DEFAULT '[]',
                contradicting_evidence TEXT DEFAULT '[]',
                related_concept_ids TEXT DEFAULT '[]',
                parent_belief_id TEXT,
                version INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_beliefs_status ON beliefs(status);
            CREATE INDEX IF NOT EXISTS idx_beliefs_parent ON beliefs(parent_belief_id);
        """)
        await self._store._conn.commit()

    # ─── Persistence helpers ────────────────────────────────────────────────

    async def _save_belief(self, belief: Belief) -> None:
        """Insert or replace a belief row in SQLite."""
        assert self._store._conn is not None
        await self._store._conn.execute(
            """INSERT OR REPLACE INTO beliefs
               (id, statement, confidence, status, supporting_evidence,
                contradicting_evidence, related_concept_ids, parent_belief_id,
                version, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                belief.id,
                belief.statement,
                belief.confidence,
                belief.status.value,
                json.dumps([e.model_dump(mode="json") for e in belief.supporting_evidence]),
                json.dumps([e.model_dump(mode="json") for e in belief.contradicting_evidence]),
                json.dumps(belief.related_concept_ids),
                belief.parent_belief_id,
                belief.version,
                belief.created_at.isoformat(),
                belief.updated_at.isoformat(),
            ),
        )
        await self._store._conn.commit()

    def _row_to_belief(self, row: aiosqlite.Row) -> Belief:
        """Convert a SQLite row to a Belief Pydantic model."""
        return Belief(
            id=row["id"],
            statement=row["statement"],
            confidence=row["confidence"],
            status=BeliefStatus(row["status"]),
            supporting_evidence=[Evidence(**e) for e in json.loads(row["supporting_evidence"])],
            contradicting_evidence=[Evidence(**e) for e in json.loads(row["contradicting_evidence"])],
            related_concept_ids=json.loads(row["related_concept_ids"]),
            parent_belief_id=row["parent_belief_id"],
            version=row["version"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    async def _fetch_belief(self, belief_id: str) -> Belief | None:
        """Retrieve a single belief by ID from SQLite."""
        assert self._store._conn is not None
        cursor = await self._store._conn.execute(
            "SELECT * FROM beliefs WHERE id = ?", (belief_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_belief(row)

    # ─── Core API ───────────────────────────────────────────────────────────

    async def add_belief(
        self,
        statement: str,
        confidence: float = 0.5,
        supporting_evidence: list[Evidence] | None = None,
        related_concept_ids: list[str] | None = None,
    ) -> Belief:
        """Create a new Belief, or merge evidence into an existing similar one.

        If a belief with a sufficiently similar statement (≥ 80 % textual
        similarity) already exists *and* is in an active state, the new
        evidence is merged into that belief instead of creating a duplicate.

        Parameters
        ----------
        statement:
            The propositional claim.
        confidence:
            Initial confidence in [0, 1].
        supporting_evidence:
            Optional list of :class:`Evidence` objects.
        related_concept_ids:
            IDs of related knowledge-graph concepts.

        Returns
        -------
        Belief
            The newly created *or* updated Belief object.
        """
        supporting_evidence = supporting_evidence or []
        related_concept_ids = related_concept_ids or []

        # Check for similar existing beliefs — but skip merging if they contradict
        active = await self.get_active_beliefs()
        for existing in active:
            if self._statement_similarity(statement, existing.statement) >= _STATEMENT_SIMILARITY_THRESHOLD:
                # Do not merge if the beliefs contradict each other;
                # they should coexist so the contradiction can be detected
                # and explicitly resolved.
                if self._check_contradiction(
                    Belief(statement=statement, confidence=confidence),
                    existing,
                ):
                    continue
                # Merge evidence into existing belief
                existing.supporting_evidence.extend(supporting_evidence)
                new_concepts = set(existing.related_concept_ids) | set(related_concept_ids)
                existing.related_concept_ids = list(new_concepts)
                # Average confidences weighted by evidence count
                total_evidence = len(existing.supporting_evidence) + len(existing.contradicting_evidence)
                if total_evidence > 0:
                    existing.confidence = (existing.confidence + confidence) / 2.0
                else:
                    existing.confidence = confidence
                existing.updated_at = utc_now()
                await self._save_belief(existing)
                return existing

        belief = Belief(
            statement=statement,
            confidence=confidence,
            supporting_evidence=supporting_evidence,
            related_concept_ids=related_concept_ids,
        )
        await self._save_belief(belief)
        return belief

    async def update_confidence(self, belief_id: str, delta: float) -> Belief:
        """Adjust belief confidence by *delta*, clamping to [0, 1].

        Status transitions based on the resulting confidence:
        * confidence < 0.2  →  WEAKENED
        * confidence < 0.1  →  ABANDONED

        A new version of the belief is created each time; the old version
        remains in the database with its original status and is linked via
        ``parent_belief_id``.

        Parameters
        ----------
        belief_id:
            ID of the belief to update.
        delta:
            Amount to add to current confidence (−1.0 … +1.0).

        Returns
        -------
        Belief
            The newly created version of the belief.

        Raises
        ------
        ValueError
            If the belief does not exist.
        """
        old = await self._fetch_belief(belief_id)
        if old is None:
            raise ValueError(f"Belief {belief_id} not found")

        new_confidence = max(0.0, min(1.0, old.confidence + delta))

        # Determine new status
        new_status = old.status
        if new_confidence < 0.1:
            new_status = BeliefStatus.ABANDONED
        elif new_confidence < 0.2:
            new_status = BeliefStatus.WEAKENED

        # Create new version
        new_belief = Belief(
            statement=old.statement,
            confidence=new_confidence,
            status=new_status,
            supporting_evidence=list(old.supporting_evidence),
            contradicting_evidence=list(old.contradicting_evidence),
            related_concept_ids=list(old.related_concept_ids),
            parent_belief_id=old.id,
            version=old.version + 1,
        )

        # Mark old belief as superseded
        old.status = BeliefStatus.SUPERSEDED
        old.updated_at = utc_now()
        await self._save_belief(old)

        # Save new version
        await self._save_belief(new_belief)
        return new_belief

    async def add_evidence(self, belief_id: str, evidence: Evidence) -> Belief:
        """Add supporting or contradicting evidence to a belief.

        Confidence is adjusted using the Bayesian-inspired update rule:

        * **Supporting**:
          ``new = old + (1 − old) × evidence.confidence × 0.3``
        * **Contradicting**:
          ``new = old × (1 − evidence.confidence × 0.3)``

        After the update, status transitions are applied (WEAKENED < 0.2,
        ABANDONED < 0.1).

        Parameters
        ----------
        belief_id:
            ID of the target belief.
        evidence:
            An :class:`Evidence` object whose ``evidence_type`` is either
            ``"supporting"`` or ``"contradicting"``.

        Returns
        -------
        Belief
            The updated belief.

        Raises
        ------
        ValueError
            If the belief does not exist.
        """
        belief = await self._fetch_belief(belief_id)
        if belief is None:
            raise ValueError(f"Belief {belief_id} not found")

        # Apply confidence update
        new_confidence = self._apply_evidence(belief.confidence, evidence)

        # Attach evidence
        if evidence.evidence_type == "supporting":
            belief.supporting_evidence.append(evidence)
        else:
            belief.contradicting_evidence.append(evidence)

        belief.confidence = new_confidence

        # Status transitions
        if new_confidence < 0.1:
            belief.status = BeliefStatus.ABANDONED
        elif new_confidence < 0.2:
            belief.status = BeliefStatus.WEAKENED

        belief.updated_at = utc_now()
        await self._save_belief(belief)
        return belief

    async def find_contradictions(self) -> list[tuple[Belief, Belief, str]]:
        """Find all pairs of active beliefs that contradict each other.

        Detection uses two heuristics:

        1. **Negation**: one belief contains "not" + the other's core claim.
        2. **Opposite terms**: both beliefs contain terms from a known
           opposite-pair (e.g. "best" vs "worst").

        Returns
        -------
        list of (belief_1, belief_2, reason)
            Each tuple contains the two conflicting beliefs and a human-
            readable reason string.
        """
        active = await self.get_active_beliefs()
        contradictions: list[tuple[Belief, Belief, str]] = []

        for i, b1 in enumerate(active):
            for b2 in active[i + 1:]:
                reason = self._check_contradiction(b1, b2)
                if reason:
                    contradictions.append((b1, b2, reason))

        return contradictions

    async def get_active_beliefs(self) -> list[Belief]:
        """Return all beliefs with ACTIVE status."""
        assert self._store._conn is not None
        cursor = await self._store._conn.execute(
            "SELECT * FROM beliefs WHERE status = ? ORDER BY updated_at DESC",
            (BeliefStatus.ACTIVE.value,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_belief(r) for r in rows]

    async def get_weakened_beliefs(self) -> list[Belief]:
        """Return all beliefs with WEAKENED status."""
        assert self._store._conn is not None
        cursor = await self._store._conn.execute(
            "SELECT * FROM beliefs WHERE status = ? ORDER BY updated_at DESC",
            (BeliefStatus.WEAKENED.value,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_belief(r) for r in rows]

    async def get_belief(self, belief_id: str) -> Belief | None:
        """Retrieve a single belief by ID.

        Returns ``None`` if the belief does not exist.
        """
        return await self._fetch_belief(belief_id)

    async def get_belief_history(self, belief_id: str) -> list[Belief]:
        """Get all versions of a belief by traversing the parent chain.

        The returned list is ordered from oldest to newest version.  If the
        given belief ID is the latest version, the history includes all
        predecessors reachable via ``parent_belief_id`` links *plus* the
        belief itself.

        Parameters
        ----------
        belief_id:
            ID of any version in the chain.

        Returns
        -------
        list[Belief]
            Chronological list of belief versions (oldest first).
        """
        # Walk backwards from the given belief to the root
        chain: list[Belief] = []
        current = await self._fetch_belief(belief_id)
        if current is None:
            return []

        # Collect from current backwards through parents
        visited: set[str] = set()
        while current is not None:
            if current.id in visited:
                break  # safety: prevent infinite loops
            visited.add(current.id)
            chain.append(current)
            if current.parent_belief_id:
                current = await self._fetch_belief(current.parent_belief_id)
            else:
                current = None

        # Also find any newer versions that reference this belief as parent
        # (in case the user passed an older version)
        assert self._store._conn is not None
        cursor = await self._store._conn.execute(
            "SELECT * FROM beliefs WHERE parent_belief_id = ?",
            (belief_id,),
        )
        child_rows = await cursor.fetchall()
        for row in child_rows:
            child = self._row_to_belief(row)
            if child.id not in visited:
                chain.insert(0, child)  # newer goes first, we'll reverse below

        # Reverse so oldest is first
        chain.reverse()
        return chain

    async def resolve_contradiction(
        self,
        belief_id_1: str,
        belief_id_2: str,
        resolution: str,
    ) -> tuple[Belief, Belief]:
        """Resolve a contradiction between two beliefs.

        Parameters
        ----------
        belief_id_1, belief_id_2:
            IDs of the conflicting beliefs.
        resolution:
            One of ``"keep_first"``, ``"keep_second"``, ``"merge"``,
            or ``"abandon_both"``.

        Returns
        -------
        tuple[Belief, Belief]
            The two beliefs after resolution is applied.

        Raises
        ------
        ValueError
            If either belief does not exist, or if *resolution* is invalid.
        """
        b1 = await self._fetch_belief(belief_id_1)
        b2 = await self._fetch_belief(belief_id_2)
        if b1 is None:
            raise ValueError(f"Belief {belief_id_1} not found")
        if b2 is None:
            raise ValueError(f"Belief {belief_id_2} not found")

        now = utc_now()

        if resolution == "keep_first":
            b2.status = BeliefStatus.ABANDONED
            b2.updated_at = now
        elif resolution == "keep_second":
            b1.status = BeliefStatus.ABANDONED
            b1.updated_at = now
        elif resolution == "merge":
            # Merge: combine evidence, average confidence, abandon second
            b1.supporting_evidence.extend(b2.supporting_evidence)
            b1.contradicting_evidence.extend(b2.contradicting_evidence)
            b1.related_concept_ids = list(
                set(b1.related_concept_ids) | set(b2.related_concept_ids)
            )
            b1.confidence = (b1.confidence + b2.confidence) / 2.0
            b1.updated_at = now
            b2.status = BeliefStatus.ABANDONED
            b2.updated_at = now
        elif resolution == "abandon_both":
            b1.status = BeliefStatus.ABANDONED
            b1.updated_at = now
            b2.status = BeliefStatus.ABANDONED
            b2.updated_at = now
        else:
            raise ValueError(
                f"Invalid resolution '{resolution}'. "
                "Must be one of: keep_first, keep_second, merge, abandon_both"
            )

        await self._save_belief(b1)
        await self._save_belief(b2)
        return (b1, b2)

    async def evolve_belief(
        self,
        belief_id: str,
        new_statement: str,
        new_confidence: float,
        reason: str = "",
    ) -> Belief:
        """Create a new version of a belief, superseding the old one.

        The old belief is marked as SUPERSEDED.  The new belief has
        ``parent_belief_id`` set to the old belief's ID and its version
        incremented by one.

        Parameters
        ----------
        belief_id:
            ID of the belief to evolve.
        new_statement:
            Updated propositional claim.
        new_confidence:
            New confidence value in [0, 1].
        reason:
            Optional human-readable reason for the evolution (not stored on
            the belief model itself but can be attached as evidence).

        Returns
        -------
        Belief
            The newly created belief version.

        Raises
        ------
        ValueError
            If the belief does not exist.
        """
        old = await self._fetch_belief(belief_id)
        if old is None:
            raise ValueError(f"Belief {belief_id} not found")

        # Mark old as superseded
        old.status = BeliefStatus.SUPERSEDED
        old.updated_at = utc_now()
        await self._save_belief(old)

        # Create evolved belief
        evolution_evidence = Evidence(
            content=f"Evolved from belief '{old.statement}': {reason}" if reason else f"Evolved from belief '{old.statement}'",
            evidence_type="supporting",
            confidence=0.9,
        )

        new_belief = Belief(
            statement=new_statement,
            confidence=new_confidence,
            status=BeliefStatus.ACTIVE,
            supporting_evidence=[evolution_evidence],
            contradicting_evidence=[],
            related_concept_ids=list(old.related_concept_ids),
            parent_belief_id=old.id,
            version=old.version + 1,
        )
        await self._save_belief(new_belief)
        return new_belief

    async def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics about beliefs.

        Returns
        -------
        dict
            ``count_by_status`` – dict mapping status name → count
            ``total`` – total number of beliefs
            ``average_confidence`` – mean confidence of all beliefs
            ``active_average_confidence`` – mean confidence of active beliefs
        """
        assert self._store._conn is not None
        cursor = await self._store._conn.execute(
            "SELECT status, COUNT(*) as cnt, AVG(confidence) as avg_conf FROM beliefs GROUP BY status"
        )
        rows = await cursor.fetchall()

        count_by_status: dict[str, int] = {}
        total = 0
        weighted_confidence = 0.0
        active_total = 0
        active_weighted_confidence = 0.0

        for row in rows:
            status = row["status"]
            cnt = row["cnt"]
            avg_conf = row["avg_conf"]
            count_by_status[status] = cnt
            total += cnt
            weighted_confidence += avg_conf * cnt
            if status == BeliefStatus.ACTIVE.value:
                active_total = cnt
                active_weighted_confidence = avg_conf * cnt

        avg_confidence = weighted_confidence / total if total > 0 else 0.0
        active_avg = active_weighted_confidence / active_total if active_total > 0 else 0.0

        return {
            "count_by_status": count_by_status,
            "total": total,
            "average_confidence": round(avg_confidence, 4),
            "active_average_confidence": round(active_avg, 4),
        }

    # ─── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _apply_evidence(current_confidence: float, evidence: Evidence) -> float:
        """Apply the confidence evolution algorithm.

        Supporting:
            ``new = old + (1 − old) × evidence.confidence × 0.3``

        Contradicting:
            ``new = old × (1 − evidence.confidence × 0.3)``
        """
        if evidence.evidence_type == "supporting":
            new = current_confidence + (1.0 - current_confidence) * evidence.confidence * 0.3
        else:
            new = current_confidence * (1.0 - evidence.confidence * 0.3)
        return max(0.0, min(1.0, new))

    @staticmethod
    def _statement_similarity(a: str, b: str) -> float:
        """Compute textual similarity between two statements using SequenceMatcher."""
        return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

    @staticmethod
    def _check_contradiction(b1: Belief, b2: Belief) -> str | None:
        """Check if two beliefs contradict each other.

        Returns a reason string if a contradiction is detected, or ``None``.
        """
        s1 = b1.statement.lower()
        s2 = b2.statement.lower()

        # Heuristic 1: one statement contains "not" + core of the other
        words1 = set(s1.split())
        words2 = set(s2.split())

        # If one has "not" and the other doesn't, check if the rest is similar
        has_not_1 = "not" in words1
        has_not_2 = "not" in words2

        if has_not_1 and not has_not_2:
            # Remove "not" from s1 and check similarity to s2
            s1_clean = s1.replace("not ", "").replace("not", "")
            sim = SequenceMatcher(None, s1_clean.strip(), s2).ratio()
            if sim >= 0.75:
                return f"Negation contradiction: '{b1.statement}' vs '{b2.statement}'"

        if has_not_2 and not has_not_1:
            s2_clean = s2.replace("not ", "").replace("not", "")
            sim = SequenceMatcher(None, s1, s2_clean.strip()).ratio()
            if sim >= 0.75:
                return f"Negation contradiction: '{b1.statement}' vs '{b2.statement}'"

        # Heuristic 2: opposite terms
        for term_a, term_b in _OPPOSITE_PAIRS:
            if (term_a in s1 and term_b in s2) or (term_b in s1 and term_a in s2):
                return (
                    f"Opposite terms ('{term_a}' vs '{term_b}'): "
                    f"'{b1.statement}' vs '{b2.statement}'"
                )

        return None
