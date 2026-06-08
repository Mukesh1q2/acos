"""
Enhanced Causal Reasoner — extends v0.4 CausalReasoner with chain discovery,
root-cause analysis, causal forecasting, influence computation, and path finding.

Wraps the v0.4 CausalReasoner and builds on its causal link store to provide:
- Multi-hop causal chain discovery
- Backward root-cause analysis
- Forward causal forecasting with time delays
- Causal influence scores
- Source-to-target path search
"""

from __future__ import annotations

import json
from collections import deque
from datetime import datetime
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v4_models import (
    CausalDirection,
    CausalLink,
    CausalStrength,
)
from acos.schemas.v5_models import (
    CausalChain,
    CausalForecast,
    RootCauseAnalysisResult,
    gen_id,
    utc_now,
)


# Mapping from CausalStrength enum to a numeric weight for aggregation.
_STRENGTH_WEIGHT: dict[CausalStrength, float] = {
    CausalStrength.NECESSARY: 1.0,
    CausalStrength.SUFFICIENT: 0.8,
    CausalStrength.CONTRIBUTING: 0.5,
    CausalStrength.INHIBITING: 0.3,
}


class EnhancedCausalReasoner:
    """Extended causal reasoner that adds chain, root-cause, forecast, and
    influence capabilities on top of the v0.4 CausalReasoner.

    Usage::

        store = StorageBackend()
        await store.initialize()

        base = CausalReasoner(store, transition_graph)
        await base.initialize()

        ecr = EnhancedCausalReasoner(store, base)
        await ecr.initialize()

        chains = await ecr.discover_causal_chains("element_A")
        rca   = await ecr.analyze_root_cause("element_Z")
        fc    = await ecr.forecast_from_cause("element_A", time_horizon=60.0)
        infl  = await ecr.compute_causal_influence("element_A")
        paths = await ecr.find_causal_paths("element_A", "element_Z")
    """

    def __init__(
        self,
        storage: StorageBackend,
        base_causal_reasoner: Any,  # CausalReasoner (v0.4)
    ) -> None:
        self._storage = storage
        self._base = base_causal_reasoner
        # Local caches for chains / forecasts persisted to our own tables
        self._chains: dict[str, CausalChain] = {}
        self._forecasts: dict[str, CausalForecast] = {}
        self._rca_results: dict[str, RootCauseAnalysisResult] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load previously persisted data."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS ecr_causal_chains (
                id TEXT PRIMARY KEY,
                chain_ids TEXT NOT NULL,
                labels TEXT NOT NULL,
                cumulative_confidence REAL DEFAULT 1.0,
                total_strength REAL DEFAULT 0.0,
                length INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ecr_causal_forecasts (
                id TEXT PRIMARY KEY,
                current_cause TEXT NOT NULL,
                predicted_effects TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.3,
                time_horizon REAL DEFAULT 0.0,
                reasoning_chain TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ecr_root_cause_analyses (
                id TEXT PRIMARY KEY,
                observed_effect TEXT NOT NULL,
                root_causes TEXT DEFAULT '[]',
                contributing_factors TEXT DEFAULT '[]',
                analysis_depth INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.3,
                reasoning_chain TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_ecr_chains_length
                ON ecr_causal_chains(length);
            CREATE INDEX IF NOT EXISTS idx_ecr_fc_cause
                ON ecr_causal_forecasts(current_cause);
            CREATE INDEX IF NOT EXISTS idx_ecr_rca_effect
                ON ecr_root_cause_analyses(observed_effect);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        if conn is None:
            return

        # Load chains
        cursor = await conn.execute("SELECT * FROM ecr_causal_chains")
        rows = await cursor.fetchall()
        for row in rows:
            chain = CausalChain(
                id=row["id"],
                chain=json.loads(row["chain_ids"]),
                labels=json.loads(row["labels"]),
                cumulative_confidence=row["cumulative_confidence"],
                total_strength=row["total_strength"],
                length=row["length"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            self._chains[chain.id] = chain

        # Load forecasts
        cursor = await conn.execute("SELECT * FROM ecr_causal_forecasts")
        rows = await cursor.fetchall()
        for row in rows:
            forecast = CausalForecast(
                id=row["id"],
                current_cause=row["current_cause"],
                predicted_effects=json.loads(row["predicted_effects"]) if row["predicted_effects"] else [],
                confidence=row["confidence"],
                time_horizon=row["time_horizon"],
                reasoning_chain=json.loads(row["reasoning_chain"]) if row["reasoning_chain"] else [],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            self._forecasts[forecast.id] = forecast

        # Load RCA results
        cursor = await conn.execute("SELECT * FROM ecr_root_cause_analyses")
        rows = await cursor.fetchall()
        for row in rows:
            rca = RootCauseAnalysisResult(
                id=row["id"],
                observed_effect=row["observed_effect"],
                root_causes=json.loads(row["root_causes"]) if row["root_causes"] else [],
                contributing_factors=json.loads(row["contributing_factors"]) if row["contributing_factors"] else [],
                analysis_depth=row["analysis_depth"],
                confidence=row["confidence"],
                reasoning_chain=json.loads(row["reasoning_chain"]) if row["reasoning_chain"] else [],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            self._rca_results[rca.id] = rca

    # ─── Persistence helpers ────────────────────────────────────────────────

    async def _save_chain(self, chain: CausalChain) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO ecr_causal_chains
               (id, chain_ids, labels, cumulative_confidence, total_strength,
                length, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                chain.id,
                json.dumps(chain.chain),
                json.dumps(chain.labels),
                chain.cumulative_confidence,
                chain.total_strength,
                chain.length,
                json.dumps(chain.metadata),
                chain.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_forecast(self, forecast: CausalForecast) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO ecr_causal_forecasts
               (id, current_cause, predicted_effects, confidence,
                time_horizon, reasoning_chain, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                forecast.id,
                forecast.current_cause,
                json.dumps(forecast.predicted_effects),
                forecast.confidence,
                forecast.time_horizon,
                json.dumps(forecast.reasoning_chain),
                json.dumps(forecast.metadata),
                forecast.created_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_rca(self, rca: RootCauseAnalysisResult) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO ecr_root_cause_analyses
               (id, observed_effect, root_causes, contributing_factors,
                analysis_depth, confidence, reasoning_chain, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rca.id,
                rca.observed_effect,
                json.dumps(rca.root_causes),
                json.dumps(rca.contributing_factors),
                rca.analysis_depth,
                rca.confidence,
                json.dumps(rca.reasoning_chain),
                json.dumps(rca.metadata),
                rca.created_at.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Internal graph helpers ─────────────────────────────────────────────

    def _forward_links(self, element_id: str) -> list[CausalLink]:
        """Return causal links where *element_id* is the cause."""
        return [
            link
            for link in self._base._causal_links.values()
            if link.cause_id == element_id
            and link.direction in (CausalDirection.FORWARD, CausalDirection.BIDIRECTIONAL)
        ]

    def _backward_links(self, element_id: str) -> list[CausalLink]:
        """Return causal links where *element_id* is the effect."""
        return [
            link
            for link in self._base._causal_links.values()
            if link.effect_id == element_id
            and link.direction in (CausalDirection.FORWARD, CausalDirection.BIDIRECTIONAL)
        ]

    @staticmethod
    def _strength_weight(strength: CausalStrength) -> float:
        return _STRENGTH_WEIGHT.get(strength, 0.5)

    # ─── 1. Discover Causal Chains ──────────────────────────────────────────

    async def discover_causal_chains(
        self,
        start_id: str,
        max_depth: int = 5,
    ) -> list[CausalChain]:
        """Follow forward causal links from *start_id* through multiple hops.

        A -> B -> C forms one chain.  Every distinct path is returned (not
        just the single best one).

        * ``cumulative_confidence`` = product of all link confidences
        * ``total_strength``        = sum of strength-weighted values
          (NECESSARY=1.0, SUFFICIENT=0.8, CONTRIBUTING=0.5, INHIBITING=0.3)
        """
        links_map = self._base._causal_links

        # Build adjacency: cause_id -> list of CausalLink
        forward_adj: dict[str, list[CausalLink]] = {}
        for link in links_map.values():
            if link.direction in (CausalDirection.FORWARD, CausalDirection.BIDIRECTIONAL):
                forward_adj.setdefault(link.cause_id, []).append(link)

        chains: list[CausalChain] = []

        # BFS/DFS over paths — each stack entry:
        #   (current_element_id, visited_set, link_path)
        stack: list[tuple[str, set[str], list[CausalLink]]] = [
            (start_id, {start_id}, [])
        ]

        while stack:
            current_id, visited, path = stack.pop()
            if path:  # record the chain even if it can't extend further
                cum_conf = 1.0
                total_str = 0.0
                chain_ids: list[str] = []
                labels: list[str] = []

                # The chain includes the start node + every effect node
                chain_ids.append(path[0].cause_id)
                labels.append(path[0].cause_label)
                for lnk in path:
                    cum_conf *= lnk.confidence
                    total_str += self._strength_weight(lnk.strength)
                    chain_ids.append(lnk.effect_id)
                    labels.append(lnk.effect_label)

                chain_obj = CausalChain(
                    chain=chain_ids,
                    labels=labels,
                    cumulative_confidence=round(cum_conf, 8),
                    total_strength=round(total_str, 4),
                    length=len(path),
                    metadata={"start_id": start_id},
                )
                chains.append(chain_obj)

            if len(path) >= max_depth:
                continue

            for lnk in forward_adj.get(current_id, []):
                next_id = lnk.effect_id
                if next_id in visited:
                    continue
                stack.append((next_id, visited | {next_id}, path + [lnk]))

        # Persist discovered chains
        for ch in chains:
            self._chains[ch.id] = ch
            await self._save_chain(ch)

        # Sort by descending cumulative confidence
        chains.sort(key=lambda c: c.cumulative_confidence, reverse=True)
        return chains

    # ─── 2. Analyze Root Cause ──────────────────────────────────────────────

    async def analyze_root_cause(
        self,
        observed_effect: str,
        max_depth: int = 5,
    ) -> RootCauseAnalysisResult:
        """Trace BACKWARD from *observed_effect* through causal links.

        * Root causes  = chains whose starting cause has no known cause itself.
        * Contributing factors = chains whose starting cause has other causes.
        * Results sorted by cumulative confidence.
        """
        links_map = self._base._causal_links

        # Build backward adjacency: effect_id -> list of CausalLink
        backward_adj: dict[str, list[CausalLink]] = {}
        for link in links_map.values():
            if link.direction in (CausalDirection.FORWARD, CausalDirection.BIDIRECTIONAL):
                backward_adj.setdefault(link.effect_id, []).append(link)

        # Also build forward adjacency so we can check "has known cause"
        forward_adj: dict[str, list[CausalLink]] = {}
        for link in links_map.values():
            if link.direction in (CausalDirection.FORWARD, CausalDirection.BIDIRECTIONAL):
                forward_adj.setdefault(link.cause_id, []).append(link)

        # BFS backward: each entry (current_effect_id, visited, link_path)
        # We collect ALL backward chains.
        all_chains: list[tuple[list[CausalLink], float, float]] = []
        stack: list[tuple[str, set[str], list[CausalLink]]] = [
            (observed_effect, {observed_effect}, [])
        ]

        while stack:
            current_id, visited, path = stack.pop()
            if path:
                cum_conf = 1.0
                total_str = 0.0
                for lnk in path:
                    cum_conf *= lnk.confidence
                    total_str += self._strength_weight(lnk.strength)
                # Path is already in cause→effect order (built by prepending)
                all_chains.append((list(path), round(cum_conf, 8), round(total_str, 4)))

            if len(path) >= max_depth:
                continue

            for lnk in backward_adj.get(current_id, []):
                cause_id = lnk.cause_id
                if cause_id in visited:
                    continue
                stack.append((cause_id, visited | {cause_id}, [lnk] + path))

        # Classify: root causes vs contributing factors
        root_causes: list[dict[str, Any]] = []
        contributing_factors: list[dict[str, Any]] = []

        for path, cum_conf, total_str in all_chains:
            start_cause_id = path[0].cause_id
            start_cause_label = path[0].cause_label
            # A node is a root cause if nothing else causes it — i.e. it
            # has no incoming causal links (no entry in backward_adj).
            has_known_cause = bool(backward_adj.get(start_cause_id))
            entry: dict[str, Any] = {
                "cause_id": start_cause_id,
                "cause_label": start_cause_label,
                "confidence": cum_conf,
                "total_strength": total_str,
                "chain": [lnk.cause_id for lnk in path] + [path[-1].effect_id],
                "chain_labels": [lnk.cause_label for lnk in path] + [path[-1].effect_label],
                "evidence_count": sum(lnk.supporting_observations for lnk in path),
            }
            if has_known_cause:
                contributing_factors.append(entry)
            else:
                root_causes.append(entry)

        # Sort each by confidence descending
        root_causes.sort(key=lambda x: x["confidence"], reverse=True)
        contributing_factors.sort(key=lambda x: x["confidence"], reverse=True)

        # Overall confidence
        if root_causes:
            confidence = max(rc["confidence"] for rc in root_causes) * 0.8
        elif contributing_factors:
            confidence = max(cf["confidence"] for cf in contributing_factors) * 0.5
        else:
            confidence = 0.1

        reasoning_chain: list[str] = [
            f"Root-cause analysis for effect '{observed_effect}'",
            f"Found {len(root_causes)} root cause(s) and {len(contributing_factors)} contributing factor(s)",
            f"Analysis depth: {max_depth}",
        ]
        if root_causes:
            reasoning_chain.append(
                f"Top root cause: {root_causes[0]['cause_label']} "
                f"(confidence={root_causes[0]['confidence']:.3f})"
            )

        result = RootCauseAnalysisResult(
            observed_effect=observed_effect,
            root_causes=root_causes,
            contributing_factors=contributing_factors,
            analysis_depth=max_depth,
            confidence=round(confidence, 4),
            reasoning_chain=reasoning_chain,
        )
        self._rca_results[result.id] = result
        await self._save_rca(result)
        return result

    # ─── 3. Forecast From Cause ────────────────────────────────────────────

    async def forecast_from_cause(
        self,
        cause_id: str,
        time_horizon: float = 0.0,
    ) -> CausalForecast:
        """Given a cause, predict what effects will follow.

        Follows forward chains, estimates probability per effect, includes
        time delays from transition duration data, and considers cascading
        effects (A -> B -> C).
        """
        links_map = self._base._causal_links

        # Build forward adjacency
        forward_adj: dict[str, list[CausalLink]] = {}
        for link in links_map.values():
            if link.direction in (CausalDirection.FORWARD, CausalDirection.BIDIRECTIONAL):
                forward_adj.setdefault(link.cause_id, []).append(link)

        predicted_effects: list[dict[str, Any]] = []
        visited: set[str] = {cause_id}
        queue: list[tuple[str, float, float]] = [(cause_id, 1.0, 0.0)]
        reasoning_chain: list[str] = [
            f"Forecasting from cause '{cause_id}'",
            f"Time horizon: {time_horizon}s",
        ]

        # BFS forward — accumulate cascading effects
        while queue:
            current_id, cum_prob, elapsed_time = queue.pop(0)

            for lnk in forward_adj.get(current_id, []):
                next_id = lnk.effect_id
                if next_id in visited:
                    continue
                visited.add(next_id)

                # Probability of this effect = cumulative so far * link confidence
                effect_prob = cum_prob * lnk.confidence
                # Estimate time delay: use metadata["avg_duration"] if present,
                # otherwise use a default based on strength
                avg_duration = lnk.metadata.get("avg_duration", 0.0)
                if avg_duration == 0.0:
                    # Heuristic: stronger causes tend to manifest faster
                    avg_duration = (1.0 - self._strength_weight(lnk.strength)) * 10.0
                time_delay = elapsed_time + avg_duration

                # Skip effects beyond the time horizon (if specified)
                if time_horizon > 0.0 and time_delay > time_horizon:
                    continue

                predicted_effects.append({
                    "effect_id": next_id,
                    "effect_label": lnk.effect_label,
                    "probability": round(effect_prob, 6),
                    "time_delay": round(time_delay, 4),
                    "mechanism": lnk.mechanism or "unknown",
                    "strength": lnk.strength.value,
                })

                # Continue cascading
                queue.append((next_id, effect_prob, time_delay))

        # Sort by probability descending
        predicted_effects.sort(key=lambda e: e["probability"], reverse=True)

        # Overall confidence
        if predicted_effects:
            confidence = predicted_effects[0]["probability"] * 0.7
        else:
            confidence = 0.1

        reasoning_chain.append(
            f"Predicted {len(predicted_effects)} effect(s)"
        )

        result = CausalForecast(
            current_cause=cause_id,
            predicted_effects=predicted_effects,
            confidence=round(confidence, 4),
            time_horizon=time_horizon,
            reasoning_chain=reasoning_chain,
        )
        self._forecasts[result.id] = result
        await self._save_forecast(result)
        return result

    # ─── 4. Compute Causal Influence ────────────────────────────────────────

    async def compute_causal_influence(
        self,
        element_id: str,
    ) -> float:
        """How much influence does *element_id* have on the rest of the system?

        Computed as::

            influence = sum(confidence * strength_weight) for all outgoing links
                      + 0.5 * influence(direct_effect)  (recursive, capped at depth 3)
        """
        memo: dict[str, float] = {}

        def _influence(eid: str, depth: int) -> float:
            if eid in memo:
                return memo[eid]
            if depth > 3:
                return 0.0

            direct = 0.0
            for lnk in self._forward_links(eid):
                direct += lnk.confidence * self._strength_weight(lnk.strength)

            indirect = 0.0
            for lnk in self._forward_links(eid):
                indirect += 0.5 * _influence(lnk.effect_id, depth + 1)

            total = direct + indirect
            memo[eid] = total
            return total

        return round(_influence(element_id, depth=0), 6)

    # ─── 5. Find Causal Paths ───────────────────────────────────────────────

    async def find_causal_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 6,
    ) -> list[CausalChain]:
        """Find all causal paths from *source_id* to *target_id*.

        Uses BFS through causal links.  Returns every distinct path with
        cumulative confidence.
        """
        links_map = self._base._causal_links

        # Build forward adjacency
        forward_adj: dict[str, list[CausalLink]] = {}
        for link in links_map.values():
            if link.direction in (CausalDirection.FORWARD, CausalDirection.BIDIRECTIONAL):
                forward_adj.setdefault(link.cause_id, []).append(link)

        paths: list[CausalChain] = []
        # BFS queue: (current_id, visited, link_path)
        queue: deque[tuple[str, set[str], list[CausalLink]]] = deque()
        queue.append((source_id, {source_id}, []))

        while queue:
            current_id, visited, path = queue.popleft()

            if current_id == target_id and path:
                cum_conf = 1.0
                total_str = 0.0
                chain_ids = [path[0].cause_id]
                labels = [path[0].cause_label]
                for lnk in path:
                    cum_conf *= lnk.confidence
                    total_str += self._strength_weight(lnk.strength)
                    chain_ids.append(lnk.effect_id)
                    labels.append(lnk.effect_label)

                chain_obj = CausalChain(
                    chain=chain_ids,
                    labels=labels,
                    cumulative_confidence=round(cum_conf, 8),
                    total_strength=round(total_str, 4),
                    length=len(path),
                    metadata={"source_id": source_id, "target_id": target_id},
                )
                paths.append(chain_obj)
                continue

            if len(path) >= max_depth:
                continue

            for lnk in forward_adj.get(current_id, []):
                next_id = lnk.effect_id
                if next_id in visited:
                    continue
                queue.append((next_id, visited | {next_id}, path + [lnk]))

        # Persist
        for ch in paths:
            self._chains[ch.id] = ch
            await self._save_chain(ch)

        paths.sort(key=lambda c: c.cumulative_confidence, reverse=True)
        return paths

    # ─── Stats ──────────────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        """Return summary statistics for the enhanced causal reasoner."""
        total_chains = len(self._chains)
        total_forecasts = len(self._forecasts)
        total_rca = len(self._rca_results)
        total_base_links = len(self._base._causal_links)

        avg_chain_conf = 0.0
        avg_chain_len = 0.0
        if total_chains > 0:
            avg_chain_conf = sum(c.cumulative_confidence for c in self._chains.values()) / total_chains
            avg_chain_len = sum(c.length for c in self._chains.values()) / total_chains

        avg_forecast_conf = 0.0
        if total_forecasts > 0:
            avg_forecast_conf = sum(f.confidence for f in self._forecasts.values()) / total_forecasts

        return {
            "base_causal_links": total_base_links,
            "discovered_chains": total_chains,
            "average_chain_confidence": round(avg_chain_conf, 4),
            "average_chain_length": round(avg_chain_len, 2),
            "total_forecasts": total_forecasts,
            "average_forecast_confidence": round(avg_forecast_conf, 4),
            "total_root_cause_analyses": total_rca,
        }
