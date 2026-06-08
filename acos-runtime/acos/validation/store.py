"""
Database persistence for ACOS Validation Lab results.

Stores validation run results to SQLite for historical tracking.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from acos.validation.models import (
    BenchmarkResult,
    BenchmarkSuiteResult,
    ComparisonResult,
    EmergenceAnalysisResult,
    FailureAnalysisReport,
    ScientificReport,
    TournamentResult,
    ValidationConfig,
)


class ValidationStore:
    """Persist validation results to SQLite.
    
    Usage::
    
        store = ValidationStore("/path/to/validation.db")
        store.initialize()
        run_id = store.save_run(config, report)
        history = store.get_run_history()
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        """Initialize the database connection and create tables."""
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(self._schema())
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _schema(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS validation_runs (
                id TEXT PRIMARY KEY,
                config_json TEXT NOT NULL,
                overall_score REAL DEFAULT 0.0,
                conclusion TEXT DEFAULT '',
                execution_time_ms REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS benchmark_results (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES validation_runs(id),
                benchmark_name TEXT NOT NULL,
                category TEXT NOT NULL,
                system_name TEXT NOT NULL,
                overall_score REAL DEFAULT 0.0,
                test_case_count INTEGER DEFAULT 0,
                execution_time_ms REAL DEFAULT 0.0,
                scores_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS comparison_results (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES validation_runs(id),
                system_a_name TEXT NOT NULL,
                system_b_name TEXT NOT NULL,
                winner TEXT DEFAULT '',
                margin REAL DEFAULT 0.0,
                p_value REAL DEFAULT 1.0,
                effect_size REAL DEFAULT 0.0,
                n_cases INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tournament_results (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES validation_runs(id),
                best_system TEXT DEFAULT '',
                worst_system TEXT DEFAULT '',
                rankings_json TEXT DEFAULT '[]',
                n_cases INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS emergence_results (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES validation_runs(id),
                emergence_type TEXT NOT NULL,
                emergence_score REAL DEFAULT 0.0,
                strongest_emergence TEXT DEFAULT '',
                analysis_summary TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS failure_results (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES validation_runs(id),
                failure_type TEXT NOT NULL,
                detected INTEGER DEFAULT 0,
                severity REAL DEFAULT 0.0,
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_benchmark_run ON benchmark_results(run_id);
            CREATE INDEX IF NOT EXISTS idx_comparison_run ON comparison_results(run_id);
            CREATE INDEX IF NOT EXISTS idx_emergence_run ON emergence_results(run_id);
            CREATE INDEX IF NOT EXISTS idx_failure_run ON failure_results(run_id);
            CREATE INDEX IF NOT EXISTS idx_runs_created ON validation_runs(created_at);
        """

    def save_run(self, config: ValidationConfig, report: ScientificReport) -> str:
        """Save a complete validation run to the database."""
        if not self._conn:
            self.initialize()
        assert self._conn is not None

        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Save main run
        self._conn.execute(
            """INSERT INTO validation_runs
               (id, config_json, overall_score, conclusion, execution_time_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                config.model_dump_json(),
                report.overall_score if hasattr(report, 'overall_score') else 0.0,
                report.conclusion,
                report.total_execution_time_ms,
                now,
            ),
        )

        # Save benchmark results
        for br in report.benchmark_results:
            self._conn.execute(
                """INSERT INTO benchmark_results
                   (id, run_id, benchmark_name, category, system_name,
                    overall_score, test_case_count, execution_time_ms, scores_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    br.id,
                    run_id,
                    br.benchmark_name,
                    br.category.value if hasattr(br.category, 'value') else str(br.category),
                    br.system_name,
                    br.overall_score,
                    br.test_case_count,
                    br.execution_time_ms,
                    json.dumps([s.model_dump() for s in br.scores]),
                    now,
                ),
            )

        # Save comparison results
        for comp in report.comparison_results:
            p_value = comp.significance.p_value if comp.significance else 1.0
            effect_size = comp.significance.effect_size_cohens_d if comp.significance else 0.0
            self._conn.execute(
                """INSERT INTO comparison_results
                   (id, run_id, system_a_name, system_b_name, winner,
                    margin, p_value, effect_size, n_cases, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    comp.id,
                    run_id,
                    comp.system_a_name,
                    comp.system_b_name,
                    comp.winner,
                    comp.margin,
                    p_value,
                    effect_size,
                    comp.n_cases,
                    now,
                ),
            )

        # Save tournament result
        if report.tournament_result:
            tr = report.tournament_result
            self._conn.execute(
                """INSERT INTO tournament_results
                   (id, run_id, best_system, worst_system, rankings_json, n_cases, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    tr.id,
                    run_id,
                    tr.best_system,
                    tr.worst_system,
                    json.dumps(tr.rankings),
                    tr.n_cases,
                    now,
                ),
            )

        # Save emergence results
        if report.emergence_analysis:
            for er in report.emergence_analysis.reports:
                self._conn.execute(
                    """INSERT INTO emergence_results
                       (id, run_id, emergence_type, emergence_score,
                        strongest_emergence, analysis_summary, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        er.id,
                        run_id,
                        er.emergence_type.value if hasattr(er.emergence_type, 'value') else str(er.emergence_type),
                        er.emergence_score,
                        er.strongest_emergence,
                        er.analysis_summary,
                        now,
                    ),
                )

        # Save failure results
        if report.failure_analysis:
            for fr in report.failure_analysis.failure_reports:
                self._conn.execute(
                    """INSERT INTO failure_results
                       (id, run_id, failure_type, detected, severity, description, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        fr.id,
                        run_id,
                        fr.failure_type.value if hasattr(fr.failure_type, 'value') else str(fr.failure_type),
                        1 if fr.detected else 0,
                        fr.severity,
                        fr.description,
                        now,
                    ),
                )

        self._conn.commit()
        return run_id

    def get_run_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent validation run history."""
        if not self._conn:
            self.initialize()
        assert self._conn is not None

        cursor = self._conn.execute(
            "SELECT * FROM validation_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Get a specific validation run with all related data."""
        if not self._conn:
            self.initialize()
        assert self._conn is not None

        cursor = self._conn.execute(
            "SELECT * FROM validation_runs WHERE id = ?",
            (run_id,),
        )
        run = cursor.fetchone()
        if not run:
            return None

        result = dict(run)

        # Get benchmark results
        cursor = self._conn.execute(
            "SELECT * FROM benchmark_results WHERE run_id = ?",
            (run_id,),
        )
        result["benchmarks"] = [dict(row) for row in cursor.fetchall()]

        # Get comparisons
        cursor = self._conn.execute(
            "SELECT * FROM comparison_results WHERE run_id = ?",
            (run_id,),
        )
        result["comparisons"] = [dict(row) for row in cursor.fetchall()]

        # Get emergence results
        cursor = self._conn.execute(
            "SELECT * FROM emergence_results WHERE run_id = ?",
            (run_id,),
        )
        result["emergence"] = [dict(row) for row in cursor.fetchall()]

        # Get failure results
        cursor = self._conn.execute(
            "SELECT * FROM failure_results WHERE run_id = ?",
            (run_id,),
        )
        result["failures"] = [dict(row) for row in cursor.fetchall()]

        return result

    def get_performance_trend(self, system_name: str = "ACOS Runtime", metric: str = "overall_score") -> list[dict[str, Any]]:
        """Get performance trend over time for a specific system."""
        if not self._conn:
            self.initialize()
        assert self._conn is not None

        cursor = self._conn.execute(
            """SELECT r.created_at, b.overall_score, b.benchmark_name, b.category
               FROM benchmark_results b
               JOIN validation_runs r ON b.run_id = r.id
               WHERE b.system_name = ?
               ORDER BY r.created_at""",
            (system_name,),
        )
        return [dict(row) for row in cursor.fetchall()]
