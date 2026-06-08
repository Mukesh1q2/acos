"""
Cognitive State Manifold — unified latent representation of the entire cognitive state.

Responsibilities:
- Project beliefs, goals, memories, concepts, uncertainties, and plans into a
  common state space defined by meaningful features
- Compute similarity between manifold points via cosine similarity
- Cluster related cognitive elements via greedy coherence grouping
- Evolve the manifold over time (decay, activation)
- Persist all manifold points and clusters to SQLite

The manifold uses a 10-dimensional feature space per point:
  confidence, urgency, importance, activation, uncertainty,
  connectivity, recency, relevance, complexity, familiarity

Each projection method (project_belief, project_goal, etc.) maps domain-specific
attributes onto these shared features with meaningful, non-placeholder values.
"""

from __future__ import annotations

import json
import math
import time as time_mod
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v5_models import (
    ManifoldCluster,
    ManifoldPoint,
    ManifoldProjectionType,
    ManifoldState,
    gen_id,
    utc_now,
)

# ─── Canonical feature order ─────────────────────────────────────────────────
# Every ManifoldPoint.features dict MUST contain these keys in this order so
# that _features_to_vector produces a consistent vector for cosine similarity.
FEATURE_KEYS: list[str] = [
    "confidence",
    "urgency",
    "importance",
    "activation",
    "uncertainty",
    "connectivity",
    "recency",
    "relevance",
    "complexity",
    "familiarity",
]

# Recency half-life in seconds — after this long, recency drops to 0.5
RECENCY_HALF_LIFE = 3600.0  # 1 hour


def _features_to_vector(features: dict[str, float]) -> list[float]:
    """Convert a feature dict to a canonical list following FEATURE_KEYS order."""
    return [features.get(k, 0.0) for k in FEATURE_KEYS]


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two equal-length float vectors."""
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    denom = math.sqrt(norm_a) * math.sqrt(norm_b)
    if denom < 1e-12:
        return 0.0
    return dot / denom


def _recency_from_datetime(dt: datetime, now: datetime | None = None) -> float:
    """Convert a datetime to a recency score in [0, 1].

    recency = 2^(-elapsed / half_life), so it decays exponentially.
    Just now → 1.0; one half-life ago → 0.5; long ago → ~0.
    """
    if now is None:
        now = utc_now()
    elapsed = max(0.0, (now - dt).total_seconds())
    return 2.0 ** (-elapsed / RECENCY_HALF_LIFE)


class CognitiveStateManifold:
    """Cognitive State Manifold — unified latent representation of cognitive state.

    Usage::

        store = StorageBackend()
        await store.initialize()

        manifold = CognitiveStateManifold(store)
        await manifold.initialize()

        # Project a belief
        from acos.schemas.v2_models import Belief
        belief = Belief(statement="Python is great", confidence=0.9)
        point = await manifold.project_belief(belief)

        # Project a goal
        from acos.schemas.v2_models import Goal, GoalPriority
        goal = Goal(description="Learn Rust", priority=GoalPriority.HIGH, progress=0.2)
        gpoint = await manifold.project_goal(goal)

        # Compute similarity
        sim = manifold.compute_similarity(point.id, gpoint.id)

        # Find clusters
        clusters = await manifold.find_clusters(min_coherence=0.5)

        # Evolve over time
        evolved = await manifold.evolve(time_elapsed_seconds=300)
    """

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._points: dict[str, ManifoldPoint] = {}
        self._clusters: dict[str, ManifoldCluster] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize the manifold: create tables and load existing data."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS manifold_points (
                id TEXT PRIMARY KEY,
                element_id TEXT NOT NULL,
                element_type TEXT NOT NULL,
                label TEXT DEFAULT '',
                features TEXT DEFAULT '{}',
                cluster_id TEXT,
                activation_level REAL DEFAULT 0.0,
                last_activated TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS manifold_clusters (
                id TEXT PRIMARY KEY,
                label TEXT DEFAULT '',
                point_ids TEXT DEFAULT '[]',
                centroid_features TEXT DEFAULT '{}',
                coherence REAL DEFAULT 0.0,
                dominant_type TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS manifold_state (
                id TEXT PRIMARY KEY,
                total_points INTEGER DEFAULT 0,
                total_clusters INTEGER DEFAULT 0,
                average_activation REAL DEFAULT 0.0,
                dimensionality INTEGER DEFAULT 10,
                dominant_cluster_id TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_mp_element
                ON manifold_points(element_id);
            CREATE INDEX IF NOT EXISTS idx_mp_type
                ON manifold_points(element_type);
            CREATE INDEX IF NOT EXISTS idx_mp_cluster
                ON manifold_points(cluster_id);
            CREATE INDEX IF NOT EXISTS idx_mc_dominant
                ON manifold_clusters(dominant_type);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        """Load all manifold points and clusters from SQLite."""
        conn = self._storage._conn
        if conn is None:
            return

        # Load points
        cursor = await conn.execute("SELECT * FROM manifold_points")
        rows = await cursor.fetchall()
        for row in rows:
            point = ManifoldPoint(
                id=row["id"],
                element_id=row["element_id"],
                element_type=ManifoldProjectionType(row["element_type"]),
                label=row["label"],
                features=json.loads(row["features"]) if row["features"] else {},
                cluster_id=row["cluster_id"],
                activation_level=row["activation_level"],
                last_activated=datetime.fromisoformat(row["last_activated"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            self._points[point.id] = point

        # Load clusters
        cursor = await conn.execute("SELECT * FROM manifold_clusters")
        rows = await cursor.fetchall()
        for row in rows:
            cluster = ManifoldCluster(
                id=row["id"],
                label=row["label"],
                point_ids=json.loads(row["point_ids"]) if row["point_ids"] else [],
                centroid_features=json.loads(row["centroid_features"]) if row["centroid_features"] else {},
                coherence=row["coherence"],
                dominant_type=ManifoldProjectionType(row["dominant_type"]) if row["dominant_type"] else None,
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            self._clusters[cluster.id] = cluster

    # ─── Persistence helpers ───────────────────────────────────────────────

    async def _save_point(self, point: ManifoldPoint) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO manifold_points
               (id, element_id, element_type, label, features, cluster_id,
                activation_level, last_activated, metadata, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                point.id,
                point.element_id,
                point.element_type.value,
                point.label,
                json.dumps(point.features),
                point.cluster_id,
                point.activation_level,
                point.last_activated.isoformat(),
                json.dumps(point.metadata),
                point.created_at.isoformat(),
                point.updated_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_cluster(self, cluster: ManifoldCluster) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO manifold_clusters
               (id, label, point_ids, centroid_features, coherence,
                dominant_type, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                cluster.id,
                cluster.label,
                json.dumps(cluster.point_ids),
                json.dumps(cluster.centroid_features),
                cluster.coherence,
                cluster.dominant_type.value if cluster.dominant_type else None,
                cluster.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_manifold_state(self, state: ManifoldState) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO manifold_state
               (id, total_points, total_clusters, average_activation,
                dimensionality, dominant_cluster_id, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                state.id,
                state.total_points,
                state.total_clusters,
                state.average_activation,
                state.dimensionality,
                state.dominant_cluster_id,
                state.timestamp.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Projection methods ────────────────────────────────────────────────

    async def project_belief(
        self,
        belief: Any,
        relevance: float = 0.5,
        context_query: str = "",
    ) -> ManifoldPoint:
        """Project a belief into the manifold.

        Maps belief attributes onto the unified feature space:
        - confidence ← belief.confidence
        - urgency ← low for beliefs (they are observations, not imperatives)
        - importance ← derived from evidence count and confidence
        - activation ← high for recently updated beliefs
        - uncertainty ← 1 − confidence
        - connectivity ← based on number of related concepts
        - recency ← exponential decay from last update
        - relevance ← provided or computed from context
        - complexity ← based on evidence diversity
        - familiarity ← based on version count and access history

        Args:
            belief: A Belief model (v2_models.Belief or compatible).
            relevance: Current relevance to active context [0, 1].
            context_query: Optional context query for relevance adjustment.

        Returns:
            A ManifoldPoint representing this belief in the manifold.
        """
        now = utc_now()

        # Extract belief attributes with safe defaults
        confidence = getattr(belief, "confidence", 0.5)
        supporting = getattr(belief, "supporting_evidence", [])
        contradicting = getattr(belief, "contracting_evidence", [])
        related_concepts = getattr(belief, "related_concept_ids", [])
        updated_at = getattr(belief, "updated_at", now)
        version = getattr(belief, "version", 1)
        statement = getattr(belief, "statement", "")
        status = getattr(belief, "status", None)

        # ── Compute features ────────────────────────────────────────────
        feat_confidence = confidence

        # Beliefs are not inherently urgent; slight urgency if contradicted
        feat_urgency = min(1.0, len(contradicting) * 0.15)

        # Importance: more evidence + higher confidence → more important
        total_evidence = len(supporting) + len(contradicting)
        feat_importance = min(1.0, (total_evidence * 0.1) + (confidence * 0.4) + 0.1)

        # Activation: recently updated beliefs are more activated
        # Active status gives a boost; weakened/superseded gives less
        status_str = status.value if status else "active"
        status_boost = {"active": 0.3, "weakened": 0.15, "superseded": 0.05, "abandoned": 0.0}
        recency_score = _recency_from_datetime(updated_at, now)
        feat_activation = min(1.0, recency_score + status_boost.get(status_str, 0.1))

        # Uncertainty: inverse of confidence, boosted by contradicting evidence
        feat_uncertainty = min(1.0, (1.0 - confidence) + len(contradicting) * 0.1)

        # Connectivity: based on how many related concepts this belief has
        feat_connectivity = min(1.0, len(related_concepts) * 0.15 + 0.05)

        # Recency: exponential decay from last update
        feat_recency = recency_score

        # Relevance: from context or default
        feat_relevance = relevance

        # Complexity: more evidence (especially contradicting) → more complex
        feat_complexity = min(1.0, (total_evidence * 0.08) + (len(contradicting) * 0.15) + 0.1)

        # Familiarity: higher version = more familiar; more evidence = more familiar
        feat_familiarity = min(1.0, (version * 0.1) + (len(supporting) * 0.05) + 0.2)

        features = {
            "confidence": feat_confidence,
            "urgency": feat_urgency,
            "importance": feat_importance,
            "activation": feat_activation,
            "uncertainty": feat_uncertainty,
            "connectivity": feat_connectivity,
            "recency": feat_recency,
            "relevance": feat_relevance,
            "complexity": feat_complexity,
            "familiarity": feat_familiarity,
        }

        # Check if a point for this element already exists
        existing = self._find_point_by_element(belief.id, ManifoldProjectionType.BELIEF)
        if existing is not None:
            existing.features = features
            existing.activation_level = feat_activation
            existing.last_activated = now
            existing.updated_at = now
            await self._save_point(existing)
            return existing

        point = ManifoldPoint(
            element_id=belief.id,
            element_type=ManifoldProjectionType.BELIEF,
            label=statement[:100] if statement else f"belief_{belief.id[:8]}",
            features=features,
            activation_level=feat_activation,
            last_activated=now,
            metadata={"statement_preview": statement[:200] if statement else ""},
        )
        self._points[point.id] = point
        await self._save_point(point)
        return point

    async def project_goal(
        self,
        goal: Any,
        relevance: float = 0.5,
        dependency_met: bool | None = None,
    ) -> ManifoldPoint:
        """Project a goal into the manifold.

        Maps goal attributes onto the unified feature space:
        - confidence ← based on progress and dependency status
        - urgency ← derived from priority and inverse of progress
        - importance ← from goal priority
        - activation ← high for active goals, low for completed/abandoned
        - uncertainty ← based on remaining progress and unmet dependencies
        - connectivity ← from related concepts and beliefs
        - recency ← exponential decay from last update
        - relevance ← provided or computed
        - complexity ← based on subgoals and dependencies
        - familiarity ← based on progress (further along = more familiar)

        Args:
            goal: A Goal model (v2_models.Goal or compatible).
            relevance: Current relevance to active context [0, 1].
            dependency_met: Whether dependencies are satisfied (None = auto-check).

        Returns:
            A ManifoldPoint representing this goal in the manifold.
        """
        now = utc_now()

        # Extract goal attributes with safe defaults
        priority = getattr(goal, "priority", 5)
        progress = getattr(goal, "progress", 0.0)
        subgoal_ids = getattr(goal, "subgoal_ids", [])
        dependency_ids = getattr(goal, "dependency_ids", [])
        related_concepts = getattr(goal, "related_concept_ids", [])
        related_beliefs = getattr(goal, "related_belief_ids", [])
        updated_at = getattr(goal, "updated_at", now)
        description = getattr(goal, "description", "")
        status = getattr(goal, "status", None)
        metadata = getattr(goal, "metadata", {})

        # Normalise priority to [0, 1] — GoalPriority enum values are 1, 5, 10, 15
        if isinstance(priority, int):
            priority_norm = min(1.0, priority / 15.0)
        else:
            priority_norm = min(1.0, int(priority) / 15.0)

        status_str = status.value if status else "active"

        # Determine dependency satisfaction
        if dependency_met is None:
            # If no explicit info, use metadata or heuristic
            deps_met_count = metadata.get("deps_met_count", 0)
            total_deps = len(dependency_ids)
            dep_sat = deps_met_count / total_deps if total_deps > 0 else 1.0
        else:
            dep_sat = 1.0 if dependency_met else 0.0

        # ── Compute features ────────────────────────────────────────────
        # Confidence: high progress + deps met → confident
        feat_confidence = min(1.0, (progress * 0.5) + (dep_sat * 0.3) + 0.2)

        # Urgency: high priority + low progress = urgent
        feat_urgency = min(1.0, priority_norm * 0.6 + (1.0 - progress) * 0.3 + 0.1)

        # Importance: directly from priority
        feat_importance = priority_norm

        # Activation: active goals are highly activated
        status_activation = {
            "active": 0.7,
            "paused": 0.3,
            "completed": 0.1,
            "abandoned": 0.0,
        }
        recency_score = _recency_from_datetime(updated_at, now)
        feat_activation = min(1.0, status_activation.get(status_str, 0.3) + recency_score * 0.3)

        # Uncertainty: more remaining work + unmet deps = more uncertain
        feat_uncertainty = min(1.0, (1.0 - progress) * 0.4 + (1.0 - dep_sat) * 0.3 + 0.1)

        # Connectivity: related concepts + beliefs + subgoals + dependencies
        total_links = len(related_concepts) + len(related_beliefs) + len(subgoal_ids) + len(dependency_ids)
        feat_connectivity = min(1.0, total_links * 0.1 + 0.05)

        # Recency
        feat_recency = recency_score

        # Relevance
        feat_relevance = relevance

        # Complexity: more subgoals and dependencies = more complex
        feat_complexity = min(1.0, (len(subgoal_ids) * 0.1) + (len(dependency_ids) * 0.15) + 0.1)

        # Familiarity: more progress = more familiar with the goal
        feat_familiarity = min(1.0, progress * 0.5 + 0.2)

        features = {
            "confidence": feat_confidence,
            "urgency": feat_urgency,
            "importance": feat_importance,
            "activation": feat_activation,
            "uncertainty": feat_uncertainty,
            "connectivity": feat_connectivity,
            "recency": feat_recency,
            "relevance": feat_relevance,
            "complexity": feat_complexity,
            "familiarity": feat_familiarity,
        }

        existing = self._find_point_by_element(goal.id, ManifoldProjectionType.GOAL)
        if existing is not None:
            existing.features = features
            existing.activation_level = feat_activation
            existing.last_activated = now
            existing.updated_at = now
            await self._save_point(existing)
            return existing

        point = ManifoldPoint(
            element_id=goal.id,
            element_type=ManifoldProjectionType.GOAL,
            label=description[:100] if description else f"goal_{goal.id[:8]}",
            features=features,
            activation_level=feat_activation,
            last_activated=now,
            metadata={"description_preview": description[:200] if description else ""},
        )
        self._points[point.id] = point
        await self._save_point(point)
        return point

    async def project_concept(
        self,
        concept: Any,
        relationship_count: int = 0,
        relevance: float = 0.5,
    ) -> ManifoldPoint:
        """Project a concept into the manifold.

        Maps concept attributes onto the unified feature space:
        - confidence ← concept.confidence
        - urgency ← low for concepts (they are referential, not imperative)
        - importance ← based on relationship count and source count
        - activation ← based on access count and recency
        - uncertainty ← inverse of confidence
        - connectivity ← based on relationship count
        - recency ← exponential decay from last access
        - relevance ← provided or computed
        - complexity ← based on concept type (abstract > concrete)
        - familiarity ← based on access count

        Args:
            concept: A Concept model (v2_models.Concept or compatible).
            relationship_count: Number of relationships this concept participates in.
            relevance: Current relevance to active context [0, 1].

        Returns:
            A ManifoldPoint representing this concept in the manifold.
        """
        now = utc_now()

        confidence = getattr(concept, "confidence", 1.0)
        concept_type = getattr(concept, "concept_type", None)
        source_ids = getattr(concept, "source_ids", [])
        access_count = getattr(concept, "access_count", 0)
        properties = getattr(concept, "properties", {})
        updated_at = getattr(concept, "updated_at", now)
        name = getattr(concept, "name", "")

        type_str = concept_type.value if concept_type else "abstract"

        # ── Compute features ────────────────────────────────────────────
        feat_confidence = confidence

        # Concepts are not urgent; slight urgency if low confidence (need validation)
        feat_urgency = min(1.0, (1.0 - confidence) * 0.3)

        # Importance: more relationships + more sources → more important
        feat_importance = min(1.0, (relationship_count * 0.08) + (len(source_ids) * 0.05) + 0.1)

        # Activation: based on access count (logarithmic) and recency
        access_activation = min(0.5, math.log1p(access_count) * 0.1)
        recency_score = _recency_from_datetime(updated_at, now)
        feat_activation = min(1.0, access_activation + recency_score * 0.5)

        # Uncertainty: inverse of confidence
        feat_uncertainty = 1.0 - confidence

        # Connectivity: directly from relationship count
        feat_connectivity = min(1.0, relationship_count * 0.1 + 0.05)

        # Recency
        feat_recency = recency_score

        # Relevance
        feat_relevance = relevance

        # Complexity: abstract concepts are more complex than concrete ones
        type_complexity = {
            "abstract": 0.7,
            "process": 0.6,
            "property": 0.3,
            "event": 0.5,
            "concrete": 0.2,
        }
        feat_complexity = min(1.0, type_complexity.get(type_str, 0.4) + len(properties) * 0.02)

        # Familiarity: more accesses = more familiar
        feat_familiarity = min(1.0, math.log1p(access_count) * 0.15 + 0.2)

        features = {
            "confidence": feat_confidence,
            "urgency": feat_urgency,
            "importance": feat_importance,
            "activation": feat_activation,
            "uncertainty": feat_uncertainty,
            "connectivity": feat_connectivity,
            "recency": feat_recency,
            "relevance": feat_relevance,
            "complexity": feat_complexity,
            "familiarity": feat_familiarity,
        }

        existing = self._find_point_by_element(concept.id, ManifoldProjectionType.CONCEPT)
        if existing is not None:
            existing.features = features
            existing.activation_level = feat_activation
            existing.last_activated = now
            existing.updated_at = now
            await self._save_point(existing)
            return existing

        point = ManifoldPoint(
            element_id=concept.id,
            element_type=ManifoldProjectionType.CONCEPT,
            label=name[:100] if name else f"concept_{concept.id[:8]}",
            features=features,
            activation_level=feat_activation,
            last_activated=now,
            metadata={"concept_type": type_str},
        )
        self._points[point.id] = point
        await self._save_point(point)
        return point

    async def project_plan(
        self,
        plan: Any,
        relevance: float = 0.5,
        step_completion_rate: float = 0.0,
    ) -> ManifoldPoint:
        """Project a plan into the manifold.

        Maps plan attributes onto the unified feature space:
        - confidence ← based on step completion and action success rate
        - urgency ← derived from deadline proximity and step completion
        - importance ← from plan priority / criticality
        - activation ← active plans are highly activated
        - uncertainty ← based on remaining steps and past failures
        - connectivity ← from related goal and concept links
        - recency ← exponential decay from last update
        - relevance ← provided or computed
        - complexity ← based on number of steps and branches
        - familiarity ← based on how often similar plans have succeeded

        Args:
            plan: A plan-like object with attributes: id, name/description,
                  status, steps, related_goal_id, priority, deadline, etc.
            relevance: Current relevance to active context [0, 1].
            step_completion_rate: Fraction of plan steps completed [0, 1].

        Returns:
            A ManifoldPoint representing this plan in the manifold.
        """
        now = utc_now()

        plan_id = getattr(plan, "id", "")
        name = getattr(plan, "name", getattr(plan, "description", ""))
        status = getattr(plan, "status", "active")
        steps = getattr(plan, "steps", [])
        priority = getattr(plan, "priority", 5)
        deadline = getattr(plan, "deadline", None)
        related_goal_id = getattr(plan, "related_goal_id", None)
        updated_at = getattr(plan, "updated_at", now)
        metadata = getattr(plan, "metadata", {})

        priority_norm = min(1.0, int(priority) / 15.0) if isinstance(priority, (int,)) else 0.5
        status_str = status.value if hasattr(status, "value") else str(status)
        num_steps = len(steps) if isinstance(steps, list) else 0

        # Deadline urgency
        deadline_urgency = 0.0
        if deadline is not None:
            try:
                if isinstance(deadline, datetime):
                    remaining = (deadline - now).total_seconds()
                else:
                    remaining = (datetime.fromisoformat(str(deadline)) - now).total_seconds()
                # Urgency ramps up as deadline approaches
                if remaining < 0:
                    deadline_urgency = 1.0  # Overdue!
                elif remaining < 3600:
                    deadline_urgency = 0.9  # Less than 1 hour
                elif remaining < 86400:
                    deadline_urgency = 0.6  # Less than 1 day
                else:
                    deadline_urgency = max(0.0, 1.0 - remaining / 604800)  # Decay over a week
            except (ValueError, TypeError):
                deadline_urgency = 0.2

        # ── Compute features ────────────────────────────────────────────
        feat_confidence = min(1.0, step_completion_rate * 0.5 + 0.3)

        # Urgency: deadline proximity + low completion + high priority
        feat_urgency = min(1.0, deadline_urgency * 0.5 + (1.0 - step_completion_rate) * 0.3 + priority_norm * 0.2)

        # Importance: priority-driven
        feat_importance = priority_norm

        # Activation: active plans are highly activated
        status_activation = {"active": 0.7, "paused": 0.3, "completed": 0.1, "abandoned": 0.0}
        recency_score = _recency_from_datetime(updated_at, now)
        feat_activation = min(1.0, status_activation.get(status_str, 0.3) + recency_score * 0.3)

        # Uncertainty: more remaining steps = more uncertain
        remaining_frac = 1.0 - step_completion_rate
        feat_uncertainty = min(1.0, remaining_frac * 0.5 + (num_steps * 0.03) + 0.1)

        # Connectivity: related goal + step links
        total_links = (1 if related_goal_id else 0) + num_steps
        feat_connectivity = min(1.0, total_links * 0.08 + 0.05)

        # Recency
        feat_recency = recency_score

        # Relevance
        feat_relevance = relevance

        # Complexity: more steps = more complex
        feat_complexity = min(1.0, num_steps * 0.1 + 0.1)

        # Familiarity: based on step completion rate
        feat_familiarity = min(1.0, step_completion_rate * 0.4 + 0.2)

        features = {
            "confidence": feat_confidence,
            "urgency": feat_urgency,
            "importance": feat_importance,
            "activation": feat_activation,
            "uncertainty": feat_uncertainty,
            "connectivity": feat_connectivity,
            "recency": feat_recency,
            "relevance": feat_relevance,
            "complexity": feat_complexity,
            "familiarity": feat_familiarity,
        }

        existing = self._find_point_by_element(plan_id, ManifoldProjectionType.PLAN)
        if existing is not None:
            existing.features = features
            existing.activation_level = feat_activation
            existing.last_activated = now
            existing.updated_at = now
            await self._save_point(existing)
            return existing

        point = ManifoldPoint(
            element_id=plan_id,
            element_type=ManifoldProjectionType.PLAN,
            label=name[:100] if name else f"plan_{plan_id[:8]}",
            features=features,
            activation_level=feat_activation,
            last_activated=now,
            metadata={"step_count": num_steps, "step_completion_rate": step_completion_rate},
        )
        self._points[point.id] = point
        await self._save_point(point)
        return point

    # ─── Similarity & Clustering ───────────────────────────────────────────

    def compute_similarity(self, point_a_id: str, point_b_id: str) -> float:
        """Compute cosine similarity between two manifold points.

        Args:
            point_a_id: ID of the first ManifoldPoint.
            point_b_id: ID of the second ManifoldPoint.

        Returns:
            Cosine similarity in [-1, 1] (practically [0, 1] for non-negative features).
        """
        pa = self._points.get(point_a_id)
        pb = self._points.get(point_b_id)
        if pa is None or pb is None:
            return 0.0
        vec_a = _features_to_vector(pa.features)
        vec_b = _features_to_vector(pb.features)
        return _cosine_similarity(vec_a, vec_b)

    async def find_clusters(self, min_coherence: float = 0.5) -> list[ManifoldCluster]:
        """Cluster related points using greedy coherence grouping.

        For each point, find all other points within the similarity threshold
        (min_coherence). Group them into clusters such that each cluster contains
        points that are mutually similar enough.

        The algorithm:
        1. Compute pairwise similarities for all points.
        2. For each unassigned point, find all unassigned neighbours above threshold.
        3. Form a cluster from the seed point + its neighbours.
        4. Compute centroid and coherence for the cluster.
        5. Repeat until all points are assigned or isolated.

        Args:
            min_coherence: Minimum cosine similarity to group points together [0, 1].

        Returns:
            List of ManifoldCluster objects.
        """
        # Clear old clusters
        self._clusters.clear()

        points = list(self._points.values())
        assigned: set[str] = set()

        # Pre-compute feature vectors
        vectors = {p.id: _features_to_vector(p.features) for p in points}

        for point in points:
            if point.id in assigned:
                continue

            # Find neighbours above threshold
            neighbours: list[str] = []
            for other in points:
                if other.id in assigned or other.id == point.id:
                    continue
                sim = _cosine_similarity(vectors[point.id], vectors[other.id])
                if sim >= min_coherence:
                    neighbours.append(other.id)

            # Include the seed point itself
            cluster_point_ids = [point.id] + neighbours
            if len(cluster_point_ids) < 2:
                # Isolated point — skip clustering
                point.cluster_id = None
                await self._save_point(point)
                continue

            # Mark all as assigned
            for pid in cluster_point_ids:
                assigned.add(pid)

            # Compute centroid features
            centroid: dict[str, float] = {}
            for key in FEATURE_KEYS:
                vals = [self._points[pid].features.get(key, 0.0) for pid in cluster_point_ids]
                centroid[key] = sum(vals) / len(vals)

            # Compute coherence: average pairwise similarity within cluster
            total_sim = 0.0
            pair_count = 0
            for i, pid_a in enumerate(cluster_point_ids):
                for pid_b in cluster_point_ids[i + 1:]:
                    total_sim += _cosine_similarity(vectors[pid_a], vectors[pid_b])
                    pair_count += 1
            coherence = total_sim / pair_count if pair_count > 0 else 0.0

            # Determine dominant type
            type_counts: dict[str, int] = {}
            for pid in cluster_point_ids:
                t = self._points[pid].element_type.value
                type_counts[t] = type_counts.get(t, 0) + 1
            dominant_type_str = max(type_counts, key=type_counts.get)  # type: ignore
            dominant_type = ManifoldProjectionType(dominant_type_str)

            # Create label from dominant type + count
            label = f"{dominant_type_str}_cluster_{len(self._clusters) + 1}"

            cluster = ManifoldCluster(
                label=label,
                point_ids=cluster_point_ids,
                centroid_features=centroid,
                coherence=coherence,
                dominant_type=dominant_type,
            )

            # Update points with cluster assignment
            for pid in cluster_point_ids:
                self._points[pid].cluster_id = cluster.id
                await self._save_point(self._points[pid])

            self._clusters[cluster.id] = cluster
            await self._save_cluster(cluster)

        return list(self._clusters.values())

    # ─── Activation & Evolution ────────────────────────────────────────────

    def get_active_points(self, threshold: float = 0.3) -> list[ManifoldPoint]:
        """Return all manifold points with activation_level >= threshold.

        Args:
            threshold: Minimum activation level [0, 1].

        Returns:
            List of ManifoldPoint objects above the threshold.
        """
        return [p for p in self._points.values() if p.activation_level >= threshold]

    async def evolve(self, time_elapsed_seconds: float = 60.0) -> int:
        """Evolve the manifold: decay activations and update recency.

        Activation decays exponentially over time. Points that were recently
        accessed maintain higher activation; those left idle decay toward zero.

        The decay formula is:
            new_activation = old_activation × exp(-decay_rate × elapsed)

        Recency is also recalculated relative to the new "now".

        Args:
            time_elapsed_seconds: Simulated time elapsed since last evolution.

        Returns:
            Number of points whose activation changed.
        """
        now = utc_now()
        evolved_count = 0

        # Decay rate: activation halves every ~10 minutes (600s)
        decay_rate = 0.0012  # ln(2)/600 ≈ 0.00116, rounded up slightly

        for point in self._points.values():
            old_activation = point.activation_level

            # Apply exponential decay
            new_activation = old_activation * math.exp(-decay_rate * time_elapsed_seconds)

            # Recalculate recency based on actual last_activated time
            new_recency = _recency_from_datetime(point.last_activated, now)

            # Update features
            point.activation_level = max(0.0, min(1.0, new_activation))
            point.features["activation"] = point.activation_level
            point.features["recency"] = new_recency
            point.updated_at = now

            if abs(old_activation - point.activation_level) > 0.001:
                evolved_count += 1

            await self._save_point(point)

        return evolved_count

    # ─── State Access ──────────────────────────────────────────────────────

    async def get_state(self) -> ManifoldState:
        """Get current manifold state summary."""
        total_points = len(self._points)
        total_clusters = len(self._clusters)

        avg_activation = 0.0
        if total_points > 0:
            avg_activation = sum(p.activation_level for p in self._points.values()) / total_points

        dominant_cluster_id: str | None = None
        if self._clusters:
            # Dominant cluster = largest by point count
            dominant_cluster_id = max(
                self._clusters.keys(),
                key=lambda cid: len(self._clusters[cid].point_ids),
            )

        state = ManifoldState(
            total_points=total_points,
            total_clusters=total_clusters,
            average_activation=avg_activation,
            dimensionality=len(FEATURE_KEYS),
            dominant_cluster_id=dominant_cluster_id,
        )
        await self._save_manifold_state(state)
        return state

    async def get_point(self, point_id: str) -> ManifoldPoint | None:
        """Get a specific manifold point by ID."""
        return self._points.get(point_id)

    async def get_points_by_type(self, element_type: ManifoldProjectionType) -> list[ManifoldPoint]:
        """Get all manifold points of a given element type."""
        return [p for p in self._points.values() if p.element_type == element_type]

    async def get_cluster(self, cluster_id: str) -> ManifoldCluster | None:
        """Get a specific cluster by ID."""
        return self._clusters.get(cluster_id)

    async def get_stats(self) -> dict[str, Any]:
        """Get manifold statistics."""
        state = await self.get_state()

        by_type: dict[str, int] = {}
        for p in self._points.values():
            key = p.element_type.value
            by_type[key] = by_type.get(key, 0) + 1

        avg_feature_values: dict[str, float] = {}
        if self._points:
            for key in FEATURE_KEYS:
                vals = [p.features.get(key, 0.0) for p in self._points.values()]
                avg_feature_values[key] = round(sum(vals) / len(vals), 4)

        return {
            "total_points": state.total_points,
            "total_clusters": state.total_clusters,
            "average_activation": round(state.average_activation, 4),
            "dimensionality": state.dimensionality,
            "points_by_type": by_type,
            "average_feature_values": avg_feature_values,
            "dominant_cluster_id": state.dominant_cluster_id,
        }

    # ─── Private helpers ──────────────────────────────────────────────────

    def _find_point_by_element(
        self, element_id: str, element_type: ManifoldProjectionType
    ) -> ManifoldPoint | None:
        """Find an existing manifold point by its source element ID and type."""
        for point in self._points.values():
            if point.element_id == element_id and point.element_type == element_type:
                return point
        return None
