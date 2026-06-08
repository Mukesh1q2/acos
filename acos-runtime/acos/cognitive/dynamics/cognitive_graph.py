"""
Cognitive Graph — unify concepts, beliefs, goals, memories, and plans into one graph structure.

Uses NetworkX for in-memory graph operations with SQLite persistence.
The graph provides:
- Unified representation of all cognitive elements as nodes
- Typed edges between any elements (cross-domain relationships)
- Graph traversal and neighbourhood queries
- Centrality and importance metrics
- Attention-weighted pathfinding

This is the "connective tissue" that binds all cognitive subsystems together.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import networkx as nx

from acos.memory.store import StorageBackend
from acos.schemas.v3_models import (
    CognitiveNode,
    CognitiveNodeType,
    CognitiveEdge,
    CognitiveEdgeType,
    gen_id,
    utc_now,
)


class CognitiveGraph:
    """Cognitive Graph — unified NetworkX graph for all cognitive elements.

    Usage::

        store = StorageBackend()
        await store.initialize()

        cg = CognitiveGraph(store)
        await cg.initialize()

        node = await cg.add_node("concept-123", CognitiveNodeType.CONCEPT, label="Python")
        await cg.add_edge("concept-123", "belief-456", CognitiveEdgeType.SUPPORTS)
        neighbors = await cg.get_neighbors("concept-123")
    """

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._graph: nx.DiGraph = nx.DiGraph()
        self._nodes: dict[str, CognitiveNode] = {}
        self._edges: dict[str, CognitiveEdge] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load existing graph."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS cognitive_nodes (
                id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                label TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                confidence REAL DEFAULT 0.5,
                attention_score REAL DEFAULT 0.0,
                activation_level REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cognitive_edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                confidence REAL DEFAULT 0.8,
                properties TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_cog_nodes_type
                ON cognitive_nodes(node_type);
            CREATE INDEX IF NOT EXISTS idx_cog_nodes_attention
                ON cognitive_nodes(attention_score);
            CREATE INDEX IF NOT EXISTS idx_cog_edges_source
                ON cognitive_edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_cog_edges_target
                ON cognitive_edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_cog_edges_type
                ON cognitive_edges(edge_type);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        assert conn is not None

        # Load nodes
        cursor = await conn.execute("SELECT * FROM cognitive_nodes")
        rows = await cursor.fetchall()
        for row in rows:
            node = self._row_to_node(row)
            self._nodes[node.id] = node
            self._graph.add_node(node.id, data=node)

        # Load edges
        cursor = await conn.execute("SELECT * FROM cognitive_edges")
        rows = await cursor.fetchall()
        for row in rows:
            edge = self._row_to_edge(row)
            self._edges[edge.id] = edge
            if edge.source_id in self._nodes and edge.target_id in self._nodes:
                self._graph.add_edge(
                    edge.source_id, edge.target_id, data=edge
                )

    # ─── Row ↔ Model helpers ────────────────────────────────────────────────

    @staticmethod
    def _row_to_node(row: Any) -> CognitiveNode:
        return CognitiveNode(
            id=row["id"],
            node_type=CognitiveNodeType(row["node_type"]),
            label=row["label"],
            properties=json.loads(row["properties"]) if row["properties"] else {},
            confidence=row["confidence"],
            attention_score=row["attention_score"],
            activation_level=row["activation_level"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_edge(row: Any) -> CognitiveEdge:
        return CognitiveEdge(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            edge_type=CognitiveEdgeType(row["edge_type"]),
            weight=row["weight"],
            confidence=row["confidence"],
            properties=json.loads(row["properties"]) if row["properties"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    async def _save_node(self, node: CognitiveNode) -> None:
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            """INSERT OR REPLACE INTO cognitive_nodes
               (id, node_type, label, properties, confidence, attention_score,
                activation_level, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node.id,
                node.node_type.value,
                node.label,
                json.dumps(node.properties),
                node.confidence,
                node.attention_score,
                node.activation_level,
                node.created_at.isoformat(),
                node.updated_at.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_edge(self, edge: CognitiveEdge) -> None:
        conn = self._storage._conn
        assert conn is not None
        await conn.execute(
            """INSERT OR REPLACE INTO cognitive_edges
               (id, source_id, target_id, edge_type, weight, confidence,
                properties, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                edge.id,
                edge.source_id,
                edge.target_id,
                edge.edge_type.value,
                edge.weight,
                edge.confidence,
                json.dumps(edge.properties),
                edge.created_at.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Core API ───────────────────────────────────────────────────────────

    async def add_node(
        self,
        element_id: str,
        node_type: CognitiveNodeType,
        label: str,
        confidence: float = 0.5,
        properties: dict[str, Any] | None = None,
    ) -> CognitiveNode:
        """Add or update a node in the cognitive graph.

        Args:
            element_id: ID of the element (concept, belief, goal, etc.).
            node_type: Type of the cognitive element.
            label: Human-readable label.
            confidence: Initial confidence.
            properties: Additional properties.

        Returns:
            The CognitiveNode.
        """
        if element_id in self._nodes:
            existing = self._nodes[element_id]
            existing.label = label
            existing.confidence = confidence
            if properties:
                existing.properties.update(properties)
            existing.updated_at = utc_now()
            await self._save_node(existing)
            return existing

        node = CognitiveNode(
            id=element_id,
            node_type=node_type,
            label=label,
            confidence=confidence,
            properties=properties or {},
        )
        self._nodes[element_id] = node
        self._graph.add_node(element_id, data=node)
        await self._save_node(node)
        return node

    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: CognitiveEdgeType,
        weight: float = 1.0,
        confidence: float = 0.8,
        properties: dict[str, Any] | None = None,
    ) -> CognitiveEdge | None:
        """Add a directed edge between two nodes.

        Both nodes must exist in the graph.

        Args:
            source_id: Source node ID.
            target_id: Target node ID.
            edge_type: Type of the relationship.
            weight: Edge weight.
            confidence: Confidence in this edge.
            properties: Additional properties.

        Returns:
            The CognitiveEdge, or None if either node doesn't exist.
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        # Check for duplicate edge
        for existing_edge in self._edges.values():
            if (existing_edge.source_id == source_id and
                    existing_edge.target_id == target_id and
                    existing_edge.edge_type == edge_type):
                # Update existing
                existing_edge.weight = weight
                existing_edge.confidence = confidence
                if properties:
                    existing_edge.properties.update(properties)
                await self._save_edge(existing_edge)
                return existing_edge

        edge = CognitiveEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
            confidence=confidence,
            properties=properties or {},
        )
        self._edges[edge.id] = edge
        self._graph.add_edge(source_id, target_id, data=edge)
        await self._save_edge(edge)
        return edge

    async def get_node(self, element_id: str) -> CognitiveNode | None:
        """Get a node by ID."""
        return self._nodes.get(element_id)

    async def get_neighbors(
        self,
        element_id: str,
        edge_type: CognitiveEdgeType | None = None,
        direction: str = "both",
    ) -> list[tuple[CognitiveNode, CognitiveEdge]]:
        """Get neighboring nodes and the edges connecting them.

        Args:
            element_id: The node to find neighbors for.
            edge_type: Optional filter by edge type.
            direction: "incoming", "outgoing", or "both".

        Returns:
            List of (neighbor_node, edge) tuples.
        """
        if element_id not in self._nodes:
            return []

        results: list[tuple[CognitiveNode, CognitiveEdge]] = []

        if direction in ("outgoing", "both"):
            for _, target, data in self._graph.out_edges(element_id, data=True):
                edge = data.get("data")
                if edge_type and edge and edge.edge_type != edge_type:
                    continue
                neighbor = self._nodes.get(target)
                if neighbor and edge:
                    results.append((neighbor, edge))

        if direction in ("incoming", "both"):
            for source, _, data in self._graph.in_edges(element_id, data=True):
                edge = data.get("data")
                if edge_type and edge and edge.edge_type != edge_type:
                    continue
                neighbor = self._nodes.get(source)
                if neighbor and edge:
                    results.append((neighbor, edge))

        return results

    async def get_shortest_path(
        self, source_id: str, target_id: str
    ) -> list[str] | None:
        """Find the shortest path between two nodes.

        Returns:
            List of node IDs along the path, or None if no path exists.
        """
        try:
            return nx.shortest_path(self._graph, source_id, target_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    async def get_important_nodes(self, limit: int = 10) -> list[tuple[CognitiveNode, float]]:
        """Get the most important nodes by centrality.

        Uses betweenness centrality with attention weighting.

        Args:
            limit: Maximum nodes to return.

        Returns:
            List of (node, centrality_score) tuples sorted by centrality.
        """
        if not self._nodes:
            return []

        try:
            centrality = nx.betweenness_centrality(self._graph)
        except Exception:
            # Fallback: degree centrality
            centrality = {}
            for node_id in self._nodes:
                centrality[node_id] = self._graph.degree(node_id)

        # Weight by attention score
        weighted: list[tuple[CognitiveNode, float]] = []
        for node_id, score in centrality.items():
            node = self._nodes.get(node_id)
            if node:
                weighted_score = score * (1.0 + node.attention_score)
                weighted.append((node, weighted_score))

        weighted.sort(key=lambda x: x[1], reverse=True)
        return weighted[:limit]

    async def update_activation(
        self, element_id: str, activation_delta: float
    ) -> CognitiveNode | None:
        """Update a node's activation level.

        Activation spreads through the graph: highly activated nodes
        activate their neighbors (spreading activation).

        Args:
            element_id: The node to update.
            activation_delta: Change in activation level.

        Returns:
            The updated node, or None.
        """
        node = self._nodes.get(element_id)
        if node is None:
            return None

        node.activation_level = max(0.0, min(1.0, node.activation_level + activation_delta))
        node.updated_at = utc_now()
        await self._save_node(node)
        return node

    async def spread_activation(
        self, decay: float = 0.8, threshold: float = 0.1
    ) -> int:
        """Spread activation from highly activated nodes to neighbors.

        For each node with activation > threshold, propagate a fraction
        (decay) of the activation to its neighbors.

        Args:
            decay: Activation decay factor [0, 1].
            threshold: Minimum activation to trigger spreading.

        Returns:
            Number of nodes whose activation changed.
        """
        changes = 0
        new_activations: dict[str, float] = {}

        for node_id, node in self._nodes.items():
            if node.activation_level > threshold:
                # Spread to neighbors
                for _, target_id, edge_data in self._graph.out_edges(node_id, data=True):
                    edge = edge_data.get("data")
                    if edge is None:
                        continue
                    propagation = node.activation_level * decay * edge.weight * edge.confidence
                    current = new_activations.get(target_id, self._nodes[target_id].activation_level)
                    new_activations[target_id] = min(1.0, current + propagation * 0.1)

        for node_id, new_act in new_activations.items():
            node = self._nodes.get(node_id)
            if node and abs(node.activation_level - new_act) > 0.001:
                node.activation_level = new_act
                node.updated_at = utc_now()
                await self._save_node(node)
                changes += 1

        return changes

    async def get_subgraph(
        self,
        node_ids: list[str],
        depth: int = 1,
    ) -> dict[str, Any]:
        """Extract a subgraph around the given nodes.

        Args:
            node_ids: Seed nodes.
            depth: Number of hops to include.

        Returns:
            Dict with 'nodes' and 'edges' lists.
        """
        collected_nodes: set[str] = set(node_ids)
        current_frontier = set(node_ids)

        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in current_frontier:
                if nid in self._graph:
                    for neighbor in self._graph.neighbors(nid):
                        if neighbor not in collected_nodes:
                            next_frontier.add(neighbor)
                    for predecessor in self._graph.predecessors(nid):
                        if predecessor not in collected_nodes:
                            next_frontier.add(predecessor)
            collected_nodes.update(next_frontier)
            current_frontier = next_frontier

        nodes = [self._nodes[nid] for nid in collected_nodes if nid in self._nodes]
        edges = [
            self._edges[eid] for eid, edge in self._edges.items()
            if edge.source_id in collected_nodes and edge.target_id in collected_nodes
        ]

        return {"nodes": nodes, "edges": edges}

    async def get_nodes_by_type(self, node_type: CognitiveNodeType) -> list[CognitiveNode]:
        """Get all nodes of a given type."""
        return [n for n in self._nodes.values() if n.node_type == node_type]

    async def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        by_type: dict[str, int] = {}
        for node in self._nodes.values():
            key = node.node_type.value
            by_type[key] = by_type.get(key, 0) + 1

        by_edge_type: dict[str, int] = {}
        for edge in self._edges.values():
            key = edge.edge_type.value
            by_edge_type[key] = by_edge_type.get(key, 0) + 1

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "nodes_by_type": by_type,
            "edges_by_type": by_edge_type,
            "density": nx.density(self._graph) if self._nodes else 0.0,
            "is_connected": nx.is_weakly_connected(self._graph) if self._nodes else False,
        }
