"""
Pydantic data models for ACOS Runtime.

Defines all data structures used across the system:
- Thread states and types
- Memory types and records
- Agent types and states
- Messages and communication
- Verification and reflection results
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def gen_id() -> str:
    return str(uuid.uuid4())


# ─── Thread Types ──────────────────────────────────────────────────────────────

class ThreadType(str, Enum):
    ANALYSIS = "analysis"
    MEMORY = "memory"
    PLANNING = "planning"
    VERIFICATION = "verification"
    CREATIVE = "creative"


class ThreadStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


class ThreadPriority(int, Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 15


# ─── Memory Types ─────────────────────────────────────────────────────────────

class MemoryType(str, Enum):
    WORKING = "working"        # Short-term, current context
    EPISODIC = "episodic"      # Event-based memories
    SEMANTIC = "semantic"      # Knowledge/fact-based memories


# ─── Agent Types ──────────────────────────────────────────────────────────────

class AgentType(str, Enum):
    RESEARCH = "research"
    PLANNING = "planning"
    MEMORY = "memory"
    VERIFICATION = "verification"


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Core Data Models ─────────────────────────────────────────────────────────

class MemoryRecord(BaseModel):
    """A single memory record stored in the system."""
    id: str = Field(default_factory=gen_id)
    thread_id: str | None = None
    memory_type: MemoryType = MemoryType.WORKING
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None
    created_at: datetime = Field(default_factory=utc_now)
    accessed_at: datetime = Field(default_factory=utc_now)
    access_count: int = 0
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class ThreadMemorySnapshot(BaseModel):
    """Snapshot of a thread's isolated memory space."""
    thread_id: str
    records: list[MemoryRecord] = Field(default_factory=list)
    total_size: int = 0


class Message(BaseModel):
    """A message in the system - either user input or agent output."""
    id: str = Field(default_factory=gen_id)
    role: str  # "user", "assistant", "system", "agent"
    content: str
    thread_id: str | None = None
    agent_type: AgentType | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ThreadState(BaseModel):
    """Complete state of a reasoning thread."""
    id: str = Field(default_factory=gen_id)
    type: ThreadType = ThreadType.ANALYSIS
    status: ThreadStatus = ThreadStatus.PENDING
    priority: ThreadPriority = ThreadPriority.NORMAL
    query: str
    messages: list[Message] = Field(default_factory=list)
    memory: ThreadMemorySnapshot | None = None
    result: str | None = None
    parent_session_id: str | None = None
    agent_type: AgentType | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    error: str | None = None


class AgentOutput(BaseModel):
    """Output from an agent execution."""
    agent_type: AgentType
    thread_id: str
    content: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ReflectionResult(BaseModel):
    """Result from the reflection engine's review."""
    thread_id: str
    original_output: str
    issues_found: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    revised_output: str | None = None
    quality_score: float = Field(default=0.5, ge=0.0, le=1.0)


class VerificationResult(BaseModel):
    """Result from the verification engine's checks."""
    thread_id: str
    content: str
    fact_checks: list[FactCheck] = Field(default_factory=list)
    consistency_score: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    passed: bool = True
    issues: list[str] = Field(default_factory=list)


class FactCheck(BaseModel):
    """A single fact check result."""
    claim: str
    verified: bool
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: str | None = None
    source: str | None = None


class SessionState(BaseModel):
    """Complete state of a user session."""
    id: str = Field(default_factory=gen_id)
    query: str
    threads: list[ThreadState] = Field(default_factory=list)
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    reflections: list[ReflectionResult] = Field(default_factory=list)
    verifications: list[VerificationResult] = Field(default_factory=list)
    final_synthesis: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class ModelInfo(BaseModel):
    """Information about an available LLM model."""
    name: str
    provider: str  # "ollama", "zai-api", "mock"
    capabilities: list[str] = Field(default_factory=list)
    context_window: int = 4096
    is_available: bool = False


class ModelRoutingDecision(BaseModel):
    """A routing decision from the ModelRouter."""
    model_name: str
    provider: str
    reason: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


# ─── API Request/Response Models ──────────────────────────────────────────────

class QueryRequest(BaseModel):
    """A user query to the ACOS Runtime."""
    query: str
    thread_types: list[ThreadType] | None = None
    priority: ThreadPriority = ThreadPriority.NORMAL
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    """Response from the ACOS Runtime."""
    session_id: str
    query: str
    final_synthesis: str
    threads: list[ThreadState]
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    reflections: list[ReflectionResult]
    verifications: list[VerificationResult]
    total_time_ms: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    uptime_seconds: float
    active_threads: int
    memory_records: int
    models_available: int
