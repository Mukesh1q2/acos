"""
FastAPI Server for ACOS Runtime v0.2.

Provides REST API endpoints for:
- Processing queries (v0.1 + v0.2)
- Managing threads
- Managing memory
- Health checks
- Session management
- v0.2 Cognitive subsystems: beliefs, goals, cognitive state, knowledge graph, reasoning
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from acos.kernel import CognitiveKernel
from acos.schemas.models import (
    QueryRequest, QueryResponse, HealthResponse,
    ThreadState, ThreadStatus, MemoryRecord, MemoryType,
)
from acos.schemas.v2_models import (
    QueryRequestV2, QueryResponseV2,
    Belief, BeliefCreate, Goal, GoalCreate, GoalPriority,
    CognitiveStateResponse, KnowledgeGraphResponse,
    Evidence,
)


# Global kernel instance
_kernel: CognitiveKernel | None = None
_start_time = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage kernel lifecycle."""
    global _kernel
    _kernel = CognitiveKernel()
    await _kernel.initialize()
    yield
    if _kernel:
        await _kernel.shutdown()


app = FastAPI(
    title="ACOS Runtime v0.2",
    description="Avadhan Cognitive Operating System Runtime — Cognitive State Engine & Knowledge Fabric",
    version="0.2.0",
    lifespan=lifespan,
)


def _get_kernel() -> CognitiveKernel:
    if _kernel is None:
        raise HTTPException(status_code=503, detail="ACOS Runtime not initialized")
    return _kernel


# ─── Query Endpoints ──────────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """Process a query through the full ACOS v0.1 pipeline."""
    kernel = _get_kernel()
    try:
        return await kernel.process_query(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query/v2", response_model=QueryResponseV2)
async def process_query_v2(request: QueryRequestV2) -> QueryResponseV2:
    """Process a query through the full ACOS v0.2 cognitive pipeline."""
    kernel = _get_kernel()
    try:
        return await kernel.process_query_v2(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Thread Endpoints ─────────────────────────────────────────────────────────

@app.get("/threads", response_model=list[ThreadState])
async def list_threads(status: ThreadStatus | None = None):
    """List all threads, optionally filtered by status."""
    kernel = _get_kernel()
    return await kernel._scheduler.list_threads(status=status)


@app.get("/threads/{thread_id}", response_model=ThreadState)
async def get_thread(thread_id: str):
    """Get a thread's current state."""
    kernel = _get_kernel()
    thread = await kernel.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


# ─── Memory Endpoints ─────────────────────────────────────────────────────────

@app.get("/memory/{thread_id}", response_model=list[MemoryRecord])
async def get_thread_memory(
    thread_id: str,
    memory_type: MemoryType | None = None,
    limit: int = 50,
):
    """Retrieve memories for a specific thread."""
    kernel = _get_kernel()
    return await kernel._memory.retrieve(thread_id, memory_type, limit)


@app.get("/memory/search/{query}", response_model=list[MemoryRecord])
async def search_memory(query: str, limit: int = 10):
    """Search across all memories."""
    kernel = _get_kernel()
    return await kernel._memory.search_global(query, limit)


@app.get("/memory/stats")
async def get_memory_stats():
    """Get memory system statistics."""
    kernel = _get_kernel()
    return await kernel._memory.get_stats()


# ─── Session Endpoints ────────────────────────────────────────────────────────

@app.get("/sessions")
async def list_sessions(limit: int = 20):
    """List recent sessions."""
    kernel = _get_kernel()
    return await kernel.list_sessions(limit)


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a session's full state."""
    kernel = _get_kernel()
    session = await kernel.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ─── Health & Stats ───────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    kernel = _get_kernel()
    stats = await kernel.get_stats()
    uptime = time.monotonic() - _start_time
    return HealthResponse(
        status="healthy" if kernel._initialized else "initializing",
        version="0.2.0",
        uptime_seconds=uptime,
        active_threads=stats.get("active_threads", 0),
        memory_records=stats.get("memory", {}).get("total_records", 0),
        models_available=len(stats.get("available_models", [])),
    )


@app.get("/stats")
async def get_stats():
    """Get runtime statistics including v0.2 cognitive subsystems."""
    kernel = _get_kernel()
    return await kernel.get_stats()


# ─── Models ───────────────────────────────────────────────────────────────────

@app.get("/models")
async def list_models():
    """List available LLM models."""
    kernel = _get_kernel()
    return await kernel._router.get_available_models()


# ─── v0.2 Cognitive Subsystem Endpoints ──────────────────────────────────────

@app.get("/cognitive/state", response_model=CognitiveStateResponse)
async def get_cognitive_state():
    """Get the current cognitive state snapshot."""
    kernel = _get_kernel()
    return await kernel.get_cognitive_state()


@app.get("/cognitive/state/full")
async def get_cognitive_state_full():
    """Get the complete cognitive state as a dictionary."""
    kernel = _get_kernel()
    return await kernel._cognitive_state.get_full_state()


@app.get("/cognitive/state/stats")
async def get_cognitive_state_stats():
    """Get cognitive state statistics."""
    kernel = _get_kernel()
    return await kernel._cognitive_state.get_stats()


# ─── Belief Endpoints ─────────────────────────────────────────────────────────

@app.get("/beliefs")
async def list_beliefs(status: str | None = None):
    """List all beliefs, optionally filtered by status."""
    kernel = _get_kernel()
    if status == "active":
        return await kernel._belief_state.get_active_beliefs()
    elif status == "weakened":
        return await kernel._belief_state.get_weakened_beliefs()
    # Return all: active + weakened
    active = await kernel._belief_state.get_active_beliefs()
    weakened = await kernel._belief_state.get_weakened_beliefs()
    return active + weakened


@app.post("/beliefs")
async def create_belief(belief: BeliefCreate):
    """Create a new belief."""
    kernel = _get_kernel()
    new_belief = Belief(
        statement=belief.statement,
        confidence=belief.confidence,
    )
    # Add evidence if provided
    for ev in belief.evidence_for:
        new_belief.supporting_evidence.append(
            Evidence(content=ev, evidence_type="supporting")
        )
    for ev in belief.evidence_against:
        new_belief.contradicting_evidence.append(
            Evidence(content=ev, evidence_type="contradicting")
        )
    result = await kernel._belief_state.add_belief(new_belief)
    # Also update cognitive state
    await kernel._cognitive_state.add_belief_to_state(result)
    return result


@app.get("/beliefs/{belief_id}")
async def get_belief(belief_id: str):
    """Get a specific belief."""
    kernel = _get_kernel()
    belief = await kernel._belief_state.get_belief(belief_id)
    if not belief:
        raise HTTPException(status_code=404, detail="Belief not found")
    return belief


@app.post("/beliefs/{belief_id}/contradict")
async def contradict_belief(belief_id: str, evidence: str = Query(...)):
    """Add contradicting evidence to a belief."""
    kernel = _get_kernel()
    ev = Evidence(content=evidence, evidence_type="contradicting")
    belief = await kernel._belief_state.add_evidence(belief_id, ev)
    if not belief:
        raise HTTPException(status_code=404, detail="Belief not found")
    return belief


@app.get("/beliefs/stats")
async def get_belief_stats():
    """Get belief system statistics."""
    kernel = _get_kernel()
    return await kernel._belief_state.get_stats()


# ─── Goal Endpoints ───────────────────────────────────────────────────────────

@app.get("/goals")
async def list_goals(status: str | None = None):
    """List all goals, optionally filtered by status."""
    kernel = _get_kernel()
    if status == "active":
        return await kernel._goal_manager.get_active_goals()
    elif status == "completed":
        return await kernel._goal_manager.get_completed_goals()
    # Return all active + completed
    active = await kernel._goal_manager.get_active_goals()
    completed = await kernel._goal_manager.get_completed_goals()
    return active + completed


@app.post("/goals")
async def create_goal(goal: GoalCreate):
    """Create a new goal."""
    kernel = _get_kernel()
    new_goal = Goal(
        description=goal.description,
        priority=goal.priority,
        parent_goal_id=goal.parent_goal_id,
    )
    result = await kernel._goal_manager.create_goal(
        description=goal.description,
        priority=goal.priority,
        parent_goal_id=goal.parent_goal_id,
    )
    # Also update cognitive state
    await kernel._cognitive_state.add_goal_to_state(result)
    return result


@app.get("/goals/{goal_id}")
async def get_goal(goal_id: str):
    """Get a specific goal."""
    kernel = _get_kernel()
    goal = await kernel._goal_manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@app.post("/goals/{goal_id}/progress")
async def update_goal_progress(goal_id: str, progress: float = Query(..., ge=0.0, le=1.0)):
    """Update a goal's progress."""
    kernel = _get_kernel()
    goal = await kernel._goal_manager.update_progress(goal_id, progress)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@app.get("/goals/stats")
async def get_goal_stats():
    """Get goal system statistics."""
    kernel = _get_kernel()
    return await kernel._goal_manager.get_stats()


# ─── Knowledge Graph Endpoints ────────────────────────────────────────────────

@app.get("/knowledge/graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph():
    """Get the full knowledge graph."""
    kernel = _get_kernel()
    return await kernel.get_knowledge_graph()


@app.get("/knowledge/concepts")
async def list_concepts():
    """List all concepts in the knowledge fabric."""
    kernel = _get_kernel()
    try:
        return await kernel._knowledge_fabric.get_all_concepts()
    except Exception:
        return []


@app.get("/knowledge/concepts/{concept_id}")
async def get_concept(concept_id: str):
    """Get a specific concept."""
    kernel = _get_kernel()
    concept = await kernel._knowledge_fabric.get_concept(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    return concept


@app.get("/knowledge/search")
async def search_knowledge(q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)):
    """Search the knowledge fabric semantically."""
    kernel = _get_kernel()
    results = await kernel._knowledge_fabric.semantic_search(q, limit)
    return results


@app.post("/knowledge/extract")
async def extract_knowledge(text: str = Query(..., min_length=1)):
    """Extract concepts, entities, and relationships from text."""
    kernel = _get_kernel()
    concepts = kernel._knowledge_fabric.extract_concepts(text)
    entities = kernel._knowledge_fabric.extract_entities(text)
    relationships = kernel._knowledge_fabric.extract_relationships(text, concepts)
    return {
        "concepts": [c.model_dump(mode="json") for c in concepts],
        "entities": [e.model_dump(mode="json") for e in entities],
        "relationships": [r.model_dump(mode="json") for r in relationships],
    }


@app.get("/knowledge/stats")
async def get_knowledge_stats():
    """Get knowledge fabric statistics."""
    kernel = _get_kernel()
    return kernel._knowledge_fabric.get_stats()


# ─── Reasoning Endpoints ──────────────────────────────────────────────────────

@app.post("/reasoning/infer")
async def infer_relationships(
    source_concept_id: str = Query(...),
    target_concept_id: str = Query(...),
):
    """Infer relationships between two concepts."""
    kernel = _get_kernel()
    results = await kernel._reasoning_engine.infer_relationships(
        source_concept_id, target_concept_id
    )
    return [r.model_dump(mode="json") for r in results]


@app.get("/reasoning/contradictions")
async def find_contradictions():
    """Find contradictions in the knowledge base."""
    kernel = _get_kernel()
    results = await kernel._reasoning_engine.detect_contradictions()
    return [r.model_dump(mode="json") for r in results]


@app.get("/reasoning/gaps")
async def find_knowledge_gaps():
    """Discover missing knowledge in the graph."""
    kernel = _get_kernel()
    results = await kernel._reasoning_engine.discover_knowledge_gaps()
    return [g.model_dump(mode="json") for g in results]


# ─── Semantic Memory Endpoints ────────────────────────────────────────────────

@app.get("/semantic/search")
async def search_semantic(q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)):
    """Search semantic memory."""
    kernel = _get_kernel()
    result = await kernel._semantic_memory.semantic_query(q, limit)
    return result.model_dump(mode="json")


@app.get("/semantic/stats")
async def get_semantic_stats():
    """Get semantic memory statistics."""
    kernel = _get_kernel()
    return await kernel._semantic_memory.get_stats()


# ─── Trace Endpoints ──────────────────────────────────────────────────────────

@app.get("/traces/stats")
async def get_trace_stats():
    """Get aggregate trace statistics across all sessions."""
    kernel = _get_kernel()
    try:
        stats = await kernel._trace_logger.get_trace_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/traces/{session_id}")
async def get_traces(session_id: str):
    """Get all traces for a specific session."""
    kernel = _get_kernel()
    try:
        traces = await kernel._trace_logger.get_traces(session_id)
        if not traces:
            raise HTTPException(status_code=404, detail="No traces found for this session")
        return traces
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def create_app(db_path: str | None = None) -> FastAPI:
    """Create a FastAPI app with custom configuration."""
    if db_path:
        global _kernel

        @asynccontextmanager
        async def custom_lifespan(app: FastAPI):
            global _kernel
            _kernel = CognitiveKernel(db_path=db_path)
            await _kernel.initialize()
            yield
            if _kernel:
                await _kernel.shutdown()

        return FastAPI(
            title="ACOS Runtime v0.2",
            version="0.2.0",
            lifespan=custom_lifespan,
        )
    return app
