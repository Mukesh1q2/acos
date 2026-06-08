"""
Trace Logger for ACOS CognitiveKernel.

Records the full cognition chain for every query processed through
the ACOS pipeline. Each pipeline phase is traced with timing,
inputs, outputs, success/failure status, and error details.

Traces are stored in the main acos.db SQLite database in a
`cognitive_traces` table.
"""

from __future__ import annotations

import aiosqlite
import json
import uuid
from datetime import datetime, timezone
from typing import Any


class TraceLogger:
    """
    Logs cognitive pipeline traces to the ACOS database.

    Each trace record captures:
    - Which pipeline phase was executed
    - What inputs were provided (JSON summary)
    - What outputs were produced (JSON summary)
    - How long the phase took (milliseconds)
    - Whether the phase succeeded or failed
    - Error details if the phase failed
    - Optional metadata for additional context
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create the cognitive_traces table if it doesn't exist."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_table()

    async def _create_table(self) -> None:
        assert self._conn is not None
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS cognitive_traces (
                trace_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                thread_id TEXT,
                phase TEXT NOT NULL,
                input_summary TEXT NOT NULL DEFAULT '{}',
                output_summary TEXT NOT NULL DEFAULT '{}',
                duration_ms REAL NOT NULL DEFAULT 0.0,
                success INTEGER NOT NULL DEFAULT 1,
                error TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_traces_session ON cognitive_traces(session_id);
            CREATE INDEX IF NOT EXISTS idx_traces_phase ON cognitive_traces(phase);
            CREATE INDEX IF NOT EXISTS idx_traces_created ON cognitive_traces(created_at);
        """)
        await self._conn.commit()

    async def trace_phase(
        self,
        session_id: str,
        phase: str,
        input_summary: dict[str, Any] | str,
        output_summary: dict[str, Any] | str,
        duration_ms: float,
        success: bool,
        error: str | None = None,
        thread_id: str | None = None,
        metadata: dict[str, Any] | str | None = None,
    ) -> str:
        """
        Log a trace record for a pipeline phase.

        Args:
            session_id: The session this trace belongs to.
            phase: Which pipeline phase (observe, memory, beliefs, etc.).
            input_summary: JSON-serializable summary of phase inputs.
            output_summary: JSON-serializable summary of phase outputs.
            duration_ms: How long the phase took in milliseconds.
            success: Whether the phase completed successfully.
            error: Error message if the phase failed.
            thread_id: Optional thread ID if the phase is thread-specific.
            metadata: Optional additional metadata.

        Returns:
            The trace_id of the created trace record.
        """
        trace_id = str(uuid.uuid4())

        # Normalize summaries to JSON strings
        if isinstance(input_summary, dict):
            input_json = json.dumps(input_summary, default=str)
        else:
            input_json = str(input_summary)

        if isinstance(output_summary, dict):
            output_json = json.dumps(output_summary, default=str)
        else:
            output_json = str(output_summary)

        if isinstance(metadata, dict):
            metadata_json = json.dumps(metadata, default=str)
        elif metadata is not None:
            metadata_json = str(metadata)
        else:
            metadata_json = None

        created_at = datetime.now(timezone.utc).isoformat()

        try:
            if self._conn is not None:
                await self._conn.execute(
                    """INSERT INTO cognitive_traces
                       (trace_id, session_id, thread_id, phase, input_summary,
                        output_summary, duration_ms, success, error, metadata, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        trace_id,
                        session_id,
                        thread_id,
                        phase,
                        input_json,
                        output_json,
                        duration_ms,
                        1 if success else 0,
                        error,
                        metadata_json,
                        created_at,
                    ),
                )
                await self._conn.commit()
        except Exception:
            # Non-blocking: tracing failure must not break the pipeline.
            # Silently swallow the error.
            pass

        return trace_id

    async def get_traces(self, session_id: str) -> list[dict[str, Any]]:
        """
        Get all traces for a session, ordered by creation time.

        Args:
            session_id: The session ID to look up.

        Returns:
            A list of trace dictionaries.
        """
        if self._conn is None:
            return []

        try:
            cursor = await self._conn.execute(
                """SELECT trace_id, session_id, thread_id, phase, input_summary,
                          output_summary, duration_ms, success, error, metadata, created_at
                   FROM cognitive_traces
                   WHERE session_id = ?
                   ORDER BY created_at ASC""",
                (session_id,),
            )
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                results.append({
                    "trace_id": row["trace_id"],
                    "session_id": row["session_id"],
                    "thread_id": row["thread_id"],
                    "phase": row["phase"],
                    "input_summary": json.loads(row["input_summary"]) if row["input_summary"] else {},
                    "output_summary": json.loads(row["output_summary"]) if row["output_summary"] else {},
                    "duration_ms": row["duration_ms"],
                    "success": bool(row["success"]),
                    "error": row["error"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                    "created_at": row["created_at"],
                })
            return results
        except Exception:
            return []

    async def get_trace_stats(self) -> dict[str, Any]:
        """
        Get aggregate statistics across all traces.

        Returns:
            A dictionary with total traces, per-phase counts,
            success rates, average durations, etc.
        """
        if self._conn is None:
            return {}

        try:
            # Total count
            cursor = await self._conn.execute(
                "SELECT COUNT(*) as total FROM cognitive_traces"
            )
            row = await cursor.fetchone()
            total_traces = row["total"] if row else 0

            # Per-phase stats
            cursor = await self._conn.execute(
                """SELECT phase,
                          COUNT(*) as count,
                          SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                          SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failure_count,
                          AVG(duration_ms) as avg_duration_ms,
                          MIN(duration_ms) as min_duration_ms,
                          MAX(duration_ms) as max_duration_ms
                   FROM cognitive_traces
                   GROUP BY phase
                   ORDER BY count DESC"""
            )
            rows = await cursor.fetchall()
            phase_stats = []
            for row in rows:
                phase_stats.append({
                    "phase": row["phase"],
                    "count": row["count"],
                    "success_count": row["success_count"],
                    "failure_count": row["failure_count"],
                    "success_rate": row["success_count"] / max(row["count"], 1),
                    "avg_duration_ms": round(row["avg_duration_ms"], 2) if row["avg_duration_ms"] else 0,
                    "min_duration_ms": round(row["min_duration_ms"], 2) if row["min_duration_ms"] else 0,
                    "max_duration_ms": round(row["max_duration_ms"], 2) if row["max_duration_ms"] else 0,
                })

            # Total sessions traced
            cursor = await self._conn.execute(
                "SELECT COUNT(DISTINCT session_id) as total_sessions FROM cognitive_traces"
            )
            row = await cursor.fetchone()
            total_sessions = row["total_sessions"] if row else 0

            # Overall success rate
            cursor = await self._conn.execute(
                """SELECT
                     SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as total_success,
                     COUNT(*) as total
                   FROM cognitive_traces"""
            )
            row = await cursor.fetchone()
            overall_success_rate = (row["total_success"] / max(row["total"], 1)) if row else 0

            # Overall average duration
            cursor = await self._conn.execute(
                "SELECT AVG(duration_ms) as avg_duration FROM cognitive_traces"
            )
            row = await cursor.fetchone()
            avg_duration = round(row["avg_duration"], 2) if row and row["avg_duration"] else 0

            return {
                "total_traces": total_traces,
                "total_sessions_traced": total_sessions,
                "overall_success_rate": round(overall_success_rate, 4),
                "overall_avg_duration_ms": avg_duration,
                "phase_stats": phase_stats,
            }
        except Exception:
            return {
                "total_traces": 0,
                "total_sessions_traced": 0,
                "overall_success_rate": 0,
                "overall_avg_duration_ms": 0,
                "phase_stats": [],
            }

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
