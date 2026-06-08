"""
FastAPI Server for ACOS Runtime.

Provides REST API endpoints for:
- Processing queries
- Managing threads
- Managing memory
- Health checks
- Session management
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException

from acos.kernel import CognitiveKernel
from acos.schemas.models import (
    QueryRequest, QueryResponse, HealthResponse,
    ThreadState, ThreadStatus, MemoryRecord, MemoryType,
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
    title="ACOS Runtime",
    description="Avadhan Cognitive Operating System Runtime v0.1",
    version="0.1.0",
    lifespan=lifespan,
)


def _get_kernel() -> CognitiveKernel:
    if _kernel is None:
        raise HTTPException(status_code=503, detail="ACOS Runtime not initialized")
    return _kernel


# ─── Query Endpoints ──────────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """Process a query through the full ACOS pipeline."""
    kernel = _get_kernel()
    try:
        return await kernel.process_query(request)
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
        version="0.1.0",
        uptime_seconds=uptime,
        active_threads=stats.get("active_threads", 0),
        memory_records=stats.get("memory", {}).get("total_records", 0),
        models_available=len(stats.get("available_models", [])),
    )


@app.get("/stats")
async def get_stats():
    """Get runtime statistics."""
    kernel = _get_kernel()
    return await kernel.get_stats()


# ─── Models ───────────────────────────────────────────────────────────────────

@app.get("/models")
async def list_models():
    """List available LLM models."""
    kernel = _get_kernel()
    return await kernel._router.get_available_models()


def create_app(db_path: str | None = None) -> FastAPI:
    """Create a FastAPI app with custom configuration."""
    if db_path:
        # Override the kernel creation with custom db_path
        global _kernel

        @asynccontextmanager
        async def custom_lifespan(app: FastAPI):
            global _kernel
            _kernel = CognitiveKernel(db_path=db_path)
            await _kernel.initialize()
            yield
            if _kernel:
                await _kernel.shutdown()

        app = FastAPI(
            title="ACOS Runtime",
            version="0.1.0",
            lifespan=custom_lifespan,
        )
        # Re-register all routes
        for route in app.routes:
            pass  # Routes already registered
    return app
