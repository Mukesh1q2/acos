"""
SQLite-based storage backend for ACOS memory system.

Provides persistent storage for:
- Memory records (working, episodic, semantic)
- Thread states
- Session states
- Agent outputs
"""

from __future__ import annotations

import aiosqlite
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from acos.schemas.models import (
    MemoryRecord, MemoryType, ThreadState, ThreadStatus,
    SessionState, AgentOutput, ReflectionResult, VerificationResult,
)


DEFAULT_DB_PATH = str(Path(__file__).parent.parent.parent / "data" / "acos.db")


class StorageBackend:
    """SQLite-based persistent storage for ACOS."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create database tables if they don't exist."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _create_tables(self) -> None:
        assert self._conn is not None
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS memory_records (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                embedding TEXT,
                created_at TEXT NOT NULL,
                accessed_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                importance REAL DEFAULT 0.5
            );

            CREATE INDEX IF NOT EXISTS idx_memory_thread ON memory_records(thread_id);
            CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_records(memory_type);

            CREATE TABLE IF NOT EXISTS thread_states (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                query TEXT NOT NULL,
                messages TEXT DEFAULT '[]',
                result TEXT,
                parent_session_id TEXT,
                agent_type TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS session_states (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                threads TEXT DEFAULT '[]',
                agent_outputs TEXT DEFAULT '[]',
                reflections TEXT DEFAULT '[]',
                verifications TEXT DEFAULT '[]',
                final_synthesis TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS agent_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reflection_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                original_output TEXT NOT NULL,
                issues_found TEXT DEFAULT '[]',
                contradictions TEXT DEFAULT '[]',
                improvements TEXT DEFAULT '[]',
                revised_output TEXT,
                quality_score REAL DEFAULT 0.5
            );

            CREATE TABLE IF NOT EXISTS verification_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                content TEXT NOT NULL,
                fact_checks TEXT DEFAULT '[]',
                consistency_score REAL DEFAULT 0.5,
                confidence_score REAL DEFAULT 0.5,
                passed INTEGER DEFAULT 1,
                issues TEXT DEFAULT '[]'
            );
        """)
        await self._conn.commit()

    # ─── Memory Records ──────────────────────────────────────────────────────

    async def store_memory(self, record: MemoryRecord) -> None:
        assert self._conn is not None
        await self._conn.execute(
            """INSERT OR REPLACE INTO memory_records
               (id, thread_id, memory_type, content, metadata, embedding,
                created_at, accessed_at, access_count, importance)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.id, record.thread_id, record.memory_type.value,
                record.content, json.dumps(record.metadata),
                json.dumps(record.embedding) if record.embedding else None,
                record.created_at.isoformat(), record.accessed_at.isoformat(),
                record.access_count, record.importance,
            ),
        )
        await self._conn.commit()

    async def retrieve_memory(self, record_id: str) -> MemoryRecord | None:
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT * FROM memory_records WHERE id = ?", (record_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_memory_record(row)

    async def query_memories(
        self,
        thread_id: str | None = None,
        memory_type: MemoryType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryRecord]:
        assert self._conn is not None
        conditions = []
        params: list[Any] = []
        if thread_id:
            conditions.append("thread_id = ?")
            params.append(thread_id)
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type.value)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])
        cursor = await self._conn.execute(
            f"SELECT * FROM memory_records WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params,
        )
        rows = await cursor.fetchall()
        return [self._row_to_memory_record(r) for r in rows]

    async def search_memories(self, query: str, limit: int = 10) -> list[MemoryRecord]:
        """Simple keyword-based search. For vector search, upgrade to Qdrant."""
        assert self._conn is not None
        cursor = await self._conn.execute(
            """SELECT * FROM memory_records
               WHERE content LIKE ? ORDER BY importance DESC, created_at DESC LIMIT ?""",
            (f"%{query}%", limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_memory_record(r) for r in rows]

    async def delete_memory(self, record_id: str) -> bool:
        assert self._conn is not None
        cursor = await self._conn.execute(
            "DELETE FROM memory_records WHERE id = ?", (record_id,)
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def count_memories(
        self, thread_id: str | None = None, memory_type: MemoryType | None = None
    ) -> int:
        assert self._conn is not None
        conditions = []
        params: list[Any] = []
        if thread_id:
            conditions.append("thread_id = ?")
            params.append(thread_id)
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type.value)
        where = " AND ".join(conditions) if conditions else "1=1"
        cursor = await self._conn.execute(
            f"SELECT COUNT(*) FROM memory_records WHERE {where}", params
        )
        row = await cursor.fetchone()
        return row[0]

    # ─── Thread States ────────────────────────────────────────────────────────

    async def save_thread(self, thread: ThreadState) -> None:
        assert self._conn is not None
        await self._conn.execute(
            """INSERT OR REPLACE INTO thread_states
               (id, type, status, priority, query, messages, result,
                parent_session_id, agent_type, created_at, updated_at,
                completed_at, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                thread.id, thread.type.value, thread.status.value,
                thread.priority.value, thread.query,
                json.dumps([m.model_dump(mode="json") for m in thread.messages]),
                thread.result, thread.parent_session_id,
                thread.agent_type.value if thread.agent_type else None,
                thread.created_at.isoformat(), thread.updated_at.isoformat(),
                thread.completed_at.isoformat() if thread.completed_at else None,
                thread.error,
            ),
        )
        await self._conn.commit()

    async def load_thread(self, thread_id: str) -> ThreadState | None:
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT * FROM thread_states WHERE id = ?", (thread_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        from acos.schemas.models import Message, ThreadType, AgentType
        return ThreadState(
            id=row["id"],
            type=ThreadType(row["type"]),
            status=ThreadStatus(row["status"]),
            priority=row["priority"],
            query=row["query"],
            messages=[Message(**m) for m in json.loads(row["messages"])],
            result=row["result"],
            parent_session_id=row["parent_session_id"],
            agent_type=AgentType(row["agent_type"]) if row["agent_type"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error=row["error"],
        )

    async def list_threads(
        self, status: ThreadStatus | None = None, limit: int = 50
    ) -> list[ThreadState]:
        assert self._conn is not None
        if status:
            cursor = await self._conn.execute(
                "SELECT * FROM thread_states WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status.value, limit),
            )
        else:
            cursor = await self._conn.execute(
                "SELECT * FROM thread_states ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            thread = await self.load_thread(row["id"])
            if thread:
                results.append(thread)
        return results

    # ─── Session States ───────────────────────────────────────────────────────

    async def save_session(self, session: SessionState) -> None:
        assert self._conn is not None
        await self._conn.execute(
            """INSERT OR REPLACE INTO session_states
               (id, query, threads, agent_outputs, reflections,
                verifications, final_synthesis, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session.id, session.query,
                json.dumps([t.model_dump(mode="json") for t in session.threads]),
                json.dumps([a.model_dump(mode="json") for a in session.agent_outputs]),
                json.dumps([r.model_dump(mode="json") for r in session.reflections]),
                json.dumps([v.model_dump(mode="json") for v in session.verifications]),
                session.final_synthesis,
                session.created_at.isoformat(),
                session.completed_at.isoformat() if session.completed_at else None,
            ),
        )
        await self._conn.commit()

    async def load_session(self, session_id: str) -> SessionState | None:
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT * FROM session_states WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return SessionState(
            id=row["id"],
            query=row["query"],
            threads=[ThreadState(**t) for t in json.loads(row["threads"])],
            agent_outputs=[AgentOutput(**a) for a in json.loads(row["agent_outputs"])],
            reflections=[ReflectionResult(**r) for r in json.loads(row["reflections"])],
            verifications=[VerificationResult(**v) for v in json.loads(row["verifications"])],
            final_synthesis=row["final_synthesis"],
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )

    # ─── Helper ───────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_memory_record(row: aiosqlite.Row) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            thread_id=row["thread_id"],
            memory_type=MemoryType(row["memory_type"]),
            content=row["content"],
            metadata=json.loads(row["metadata"]),
            embedding=json.loads(row["embedding"]) if row["embedding"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            accessed_at=datetime.fromisoformat(row["accessed_at"]),
            access_count=row["access_count"],
            importance=row["importance"],
        )
