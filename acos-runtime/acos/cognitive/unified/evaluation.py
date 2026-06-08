"""
Evaluation Framework — benchmarks and performance measurement for ACOS Runtime v0.5.

Tracks cognitive performance across multiple dimensions:
- Belief accuracy
- Goal completion rate
- Prediction accuracy
- Contradiction resolution rate
- Uncertainty calibration
- Planning quality
- Memory retrieval quality

All MetricMeasurement records are persisted to SQLite for historical tracking.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v5_models import (
    EvaluationReport,
    HistoricalPerformance,
    MetricMeasurement,
    MetricType,
    gen_id,
    utc_now,
)


class EvaluationFramework:
    """Create benchmarks and measure performance across cognitive dimensions.

    Usage::

        store = StorageBackend()
        await store.initialize()

        ef = EvaluationFramework(store)
        await ef.initialize()

        # Measure individual metrics
        m = await ef.measure_belief_accuracy(beliefs_with_outcomes)

        # Run a full evaluation
        report = await ef.run_full_evaluation(beliefs=b, goals=g, predictions=p)

        # Track over time
        history = await ef.get_historical_performance(MetricType.BELIEF_ACCURACY)
    """

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._measurements: dict[str, MetricMeasurement] = {}
        self._reports: dict[str, EvaluationReport] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load previously persisted data."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS ef_metric_measurements (
                id TEXT PRIMARY KEY,
                metric_type TEXT NOT NULL,
                value REAL DEFAULT 0.0,
                baseline REAL DEFAULT 0.0,
                improvement REAL DEFAULT 0.0,
                sample_size INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.5,
                context TEXT DEFAULT '',
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ef_evaluation_reports (
                id TEXT PRIMARY KEY,
                measurements TEXT DEFAULT '[]',
                overall_score REAL DEFAULT 0.0,
                strongest_dimension TEXT DEFAULT '',
                weakest_dimension TEXT DEFAULT '',
                improvement_areas TEXT DEFAULT '[]',
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_ef_mm_type
                ON ef_metric_measurements(metric_type);
            CREATE INDEX IF NOT EXISTS idx_ef_mm_ts
                ON ef_metric_measurements(timestamp);
            CREATE INDEX IF NOT EXISTS idx_ef_report_ts
                ON ef_evaluation_reports(timestamp);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        if conn is None:
            return

        # Load measurements
        cursor = await conn.execute("SELECT * FROM ef_metric_measurements")
        rows = await cursor.fetchall()
        for row in rows:
            mm = MetricMeasurement(
                id=row["id"],
                metric_type=MetricType(row["metric_type"]),
                value=row["value"],
                baseline=row["baseline"],
                improvement=row["improvement"],
                sample_size=row["sample_size"],
                confidence=row["confidence"],
                context=row["context"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )
            self._measurements[mm.id] = mm

        # Load reports
        cursor = await conn.execute("SELECT * FROM ef_evaluation_reports")
        rows = await cursor.fetchall()
        for row in rows:
            measurements_data = json.loads(row["measurements"]) if row["measurements"] else []
            measurements = [MetricMeasurement(**m) for m in measurements_data]
            report = EvaluationReport(
                id=row["id"],
                measurements=measurements,
                overall_score=row["overall_score"],
                strongest_dimension=row["strongest_dimension"],
                weakest_dimension=row["weakest_dimension"],
                improvement_areas=json.loads(row["improvement_areas"]) if row["improvement_areas"] else [],
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )
            self._reports[report.id] = report

    # ─── Persistence helpers ────────────────────────────────────────────────

    async def _save_measurement(self, mm: MetricMeasurement) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO ef_metric_measurements
               (id, metric_type, value, baseline, improvement,
                sample_size, confidence, context, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mm.id,
                mm.metric_type.value,
                mm.value,
                mm.baseline,
                mm.improvement,
                mm.sample_size,
                mm.confidence,
                mm.context,
                mm.timestamp.isoformat(),
            ),
        )
        await conn.commit()

    async def _save_report(self, report: EvaluationReport) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO ef_evaluation_reports
               (id, measurements, overall_score, strongest_dimension,
                weakest_dimension, improvement_areas, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                report.id,
                json.dumps([m.model_dump(mode="json") for m in report.measurements]),
                report.overall_score,
                report.strongest_dimension,
                report.weakest_dimension,
                json.dumps(report.improvement_areas),
                report.timestamp.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Metric: Belief Accuracy ────────────────────────────────────────────

    async def measure_belief_accuracy(
        self,
        beliefs_with_outcomes: list[dict[str, Any]],
        baseline: float = 0.0,
    ) -> MetricMeasurement:
        """Measure how well belief confidence matches actual correctness.

        Args:
            beliefs_with_outcomes: Each dict must contain:
                - ``confidence`` (float): the belief's confidence level
                - ``actual_correctness`` (float): 1.0 if correct, 0.0 if not
            baseline: Previous baseline to compare against.

        Returns:
            MetricMeasurement where value = 1.0 - avg(|confidence - actual|).
        """
        if not beliefs_with_outcomes:
            mm = MetricMeasurement(
                metric_type=MetricType.BELIEF_ACCURACY,
                value=0.0,
                baseline=baseline,
                improvement=0.0,
                sample_size=0,
                confidence=0.0,
                context="no data",
            )
            self._measurements[mm.id] = mm
            await self._save_measurement(mm)
            return mm

        total_error = 0.0
        for b in beliefs_with_outcomes:
            conf = float(b.get("confidence", 0.5))
            actual = float(b.get("actual_correctness", 0.0))
            total_error += abs(conf - actual)

        accuracy = 1.0 - (total_error / len(beliefs_with_outcomes))
        accuracy = max(0.0, min(1.0, accuracy))

        # Confidence in this measurement scales with sample size
        conf = min(1.0, len(beliefs_with_outcomes) / 20.0)

        mm = MetricMeasurement(
            metric_type=MetricType.BELIEF_ACCURACY,
            value=round(accuracy, 6),
            baseline=baseline,
            improvement=round(accuracy - baseline, 6),
            sample_size=len(beliefs_with_outcomes),
            confidence=round(conf, 4),
            context=f"n={len(beliefs_with_outcomes)}",
        )
        self._measurements[mm.id] = mm
        await self._save_measurement(mm)
        return mm

    # ─── Metric: Goal Completion Rate ───────────────────────────────────────

    async def measure_goal_completion_rate(
        self,
        goals: list[dict[str, Any]],
        baseline: float = 0.0,
    ) -> MetricMeasurement:
        """Measure the rate of completed goals.

        Args:
            goals: Each dict must contain:
                - ``completed`` (bool): whether the goal was completed
            baseline: Previous baseline.

        Returns:
            MetricMeasurement where value = completed / total.
        """
        if not goals:
            mm = MetricMeasurement(
                metric_type=MetricType.GOAL_COMPLETION_RATE,
                value=0.0,
                baseline=baseline,
                improvement=0.0,
                sample_size=0,
                confidence=0.0,
                context="no data",
            )
            self._measurements[mm.id] = mm
            await self._save_measurement(mm)
            return mm

        completed = sum(1 for g in goals if g.get("completed", False))
        rate = completed / len(goals)
        conf = min(1.0, len(goals) / 10.0)

        mm = MetricMeasurement(
            metric_type=MetricType.GOAL_COMPLETION_RATE,
            value=round(rate, 6),
            baseline=baseline,
            improvement=round(rate - baseline, 6),
            sample_size=len(goals),
            confidence=round(conf, 4),
            context=f"completed={completed}/{len(goals)}",
        )
        self._measurements[mm.id] = mm
        await self._save_measurement(mm)
        return mm

    # ─── Metric: Prediction Accuracy ────────────────────────────────────────

    async def measure_prediction_accuracy(
        self,
        predictions: list[dict[str, Any]],
        baseline: float = 0.0,
    ) -> MetricMeasurement:
        """Measure prediction accuracy for verified predictions.

        Args:
            predictions: Each dict must contain:
                - ``prediction_error`` (float): |predicted - actual|
                  (only for verified predictions; unverified ones are skipped)
            baseline: Previous baseline.

        Returns:
            MetricMeasurement where value = 1.0 - avg(prediction_error).
        """
        verified = [p for p in predictions if p.get("prediction_error") is not None]
        if not verified:
            mm = MetricMeasurement(
                metric_type=MetricType.PREDICTION_ACCURACY,
                value=0.0,
                baseline=baseline,
                improvement=0.0,
                sample_size=0,
                confidence=0.0,
                context="no verified predictions",
            )
            self._measurements[mm.id] = mm
            await self._save_measurement(mm)
            return mm

        total_error = sum(float(p["prediction_error"]) for p in verified)
        accuracy = 1.0 - (total_error / len(verified))
        accuracy = max(0.0, min(1.0, accuracy))
        conf = min(1.0, len(verified) / 15.0)

        mm = MetricMeasurement(
            metric_type=MetricType.PREDICTION_ACCURACY,
            value=round(accuracy, 6),
            baseline=baseline,
            improvement=round(accuracy - baseline, 6),
            sample_size=len(verified),
            confidence=round(conf, 4),
            context=f"verified={len(verified)}/{len(predictions)}",
        )
        self._measurements[mm.id] = mm
        await self._save_measurement(mm)
        return mm

    # ─── Metric: Contradiction Resolution ───────────────────────────────────

    async def measure_contradiction_resolution(
        self,
        contradictions: list[dict[str, Any]],
        baseline: float = 0.0,
    ) -> MetricMeasurement:
        """Measure the rate of resolved contradictions.

        Args:
            contradictions: Each dict must contain:
                - ``resolved`` (bool): whether the contradiction was resolved
            baseline: Previous baseline.

        Returns:
            MetricMeasurement where value = resolved / total.
        """
        if not contradictions:
            mm = MetricMeasurement(
                metric_type=MetricType.CONTRADICTION_RESOLUTION_RATE,
                value=0.0,
                baseline=baseline,
                improvement=0.0,
                sample_size=0,
                confidence=0.0,
                context="no data",
            )
            self._measurements[mm.id] = mm
            await self._save_measurement(mm)
            return mm

        resolved = sum(1 for c in contradictions if c.get("resolved", False))
        rate = resolved / len(contradictions)
        conf = min(1.0, len(contradictions) / 10.0)

        mm = MetricMeasurement(
            metric_type=MetricType.CONTRADICTION_RESOLUTION_RATE,
            value=round(rate, 6),
            baseline=baseline,
            improvement=round(rate - baseline, 6),
            sample_size=len(contradictions),
            confidence=round(conf, 4),
            context=f"resolved={resolved}/{len(contradictions)}",
        )
        self._measurements[mm.id] = mm
        await self._save_measurement(mm)
        return mm

    # ─── Metric: Uncertainty Calibration ────────────────────────────────────

    async def measure_uncertainty_calibration(
        self,
        predictions: list[dict[str, Any]],
        baseline: float = 0.0,
    ) -> MetricMeasurement:
        """Measure how well predicted probability matches observed frequency.

        Uses binning: group predictions by predicted probability into bins,
        then compute avg(|predicted_prob - observed_freq|) across bins.

        Args:
            predictions: Each dict must contain:
                - ``predicted_prob`` (float): the predicted probability
                - ``actual_outcome`` (float): 1.0 if happened, 0.0 if not
            baseline: Previous baseline.

        Returns:
            MetricMeasurement where value = 1.0 - avg calibration error.
        """
        verified = [
            p for p in predictions
            if p.get("predicted_prob") is not None and p.get("actual_outcome") is not None
        ]
        if not verified:
            mm = MetricMeasurement(
                metric_type=MetricType.UNCERTAINTY_CALIBRATION,
                value=0.0,
                baseline=baseline,
                improvement=0.0,
                sample_size=0,
                confidence=0.0,
                context="no verified predictions",
            )
            self._measurements[mm.id] = mm
            await self._save_measurement(mm)
            return mm

        # Bin predictions into 10 equal-width bins [0.0, 0.1), [0.1, 0.2), ... [0.9, 1.0]
        num_bins = 10
        bins: dict[int, list[tuple[float, float]]] = {i: [] for i in range(num_bins)}
        for p in verified:
            prob = float(p["predicted_prob"])
            outcome = float(p["actual_outcome"])
            bin_idx = min(int(prob * num_bins), num_bins - 1)
            bins[bin_idx].append((prob, outcome))

        # Compute calibration error per bin
        total_error = 0.0
        bins_used = 0
        for bin_idx in range(num_bins):
            items = bins[bin_idx]
            if not items:
                continue
            avg_predicted = sum(prob for prob, _ in items) / len(items)
            avg_observed = sum(outcome for _, outcome in items) / len(items)
            total_error += abs(avg_predicted - avg_observed)
            bins_used += 1

        if bins_used == 0:
            calibration = 0.0
        else:
            calibration = 1.0 - (total_error / bins_used)
        calibration = max(0.0, min(1.0, calibration))

        conf = min(1.0, len(verified) / 30.0)

        mm = MetricMeasurement(
            metric_type=MetricType.UNCERTAINTY_CALIBRATION,
            value=round(calibration, 6),
            baseline=baseline,
            improvement=round(calibration - baseline, 6),
            sample_size=len(verified),
            confidence=round(conf, 4),
            context=f"bins_used={bins_used}/{num_bins}",
        )
        self._measurements[mm.id] = mm
        await self._save_measurement(mm)
        return mm

    # ─── Metric: Planning Quality ───────────────────────────────────────────

    async def measure_planning_quality(
        self,
        plans: list[dict[str, Any]],
        baseline: float = 0.0,
    ) -> MetricMeasurement:
        """Measure planning quality.

        Quality = avg(plan.overall_confidence * plan_progress) for plans.

        Args:
            plans: Each dict must contain:
                - ``overall_confidence`` (float): plan confidence
                - ``progress`` (float): plan progress [0, 1]
            baseline: Previous baseline.

        Returns:
            MetricMeasurement with the computed quality score.
        """
        if not plans:
            mm = MetricMeasurement(
                metric_type=MetricType.PLANNING_QUALITY,
                value=0.0,
                baseline=baseline,
                improvement=0.0,
                sample_size=0,
                confidence=0.0,
                context="no data",
            )
            self._measurements[mm.id] = mm
            await self._save_measurement(mm)
            return mm

        total_quality = 0.0
        for p in plans:
            conf = float(p.get("overall_confidence", 0.5))
            progress = float(p.get("progress", 0.0))
            total_quality += conf * progress

        quality = total_quality / len(plans)
        quality = max(0.0, min(1.0, quality))
        conf = min(1.0, len(plans) / 10.0)

        mm = MetricMeasurement(
            metric_type=MetricType.PLANNING_QUALITY,
            value=round(quality, 6),
            baseline=baseline,
            improvement=round(quality - baseline, 6),
            sample_size=len(plans),
            confidence=round(conf, 4),
            context=f"n={len(plans)}",
        )
        self._measurements[mm.id] = mm
        await self._save_measurement(mm)
        return mm

    # ─── Metric: Memory Retrieval Quality ───────────────────────────────────

    async def measure_memory_retrieval_quality(
        self,
        retrieval_results: list[dict[str, Any]],
        baseline: float = 0.0,
    ) -> MetricMeasurement:
        """Measure memory retrieval quality.

        Quality = avg(relevance_score) for retrieved memories.

        Args:
            retrieval_results: Each dict must contain:
                - ``relevance_score`` (float): relevance of the retrieved memory
            baseline: Previous baseline.

        Returns:
            MetricMeasurement with the average relevance score.
        """
        if not retrieval_results:
            mm = MetricMeasurement(
                metric_type=MetricType.MEMORY_RETRIEVAL_QUALITY,
                value=0.0,
                baseline=baseline,
                improvement=0.0,
                sample_size=0,
                confidence=0.0,
                context="no data",
            )
            self._measurements[mm.id] = mm
            await self._save_measurement(mm)
            return mm

        total_relevance = sum(float(r.get("relevance_score", 0.0)) for r in retrieval_results)
        quality = total_relevance / len(retrieval_results)
        quality = max(0.0, min(1.0, quality))
        conf = min(1.0, len(retrieval_results) / 20.0)

        mm = MetricMeasurement(
            metric_type=MetricType.MEMORY_RETRIEVAL_QUALITY,
            value=round(quality, 6),
            baseline=baseline,
            improvement=round(quality - baseline, 6),
            sample_size=len(retrieval_results),
            confidence=round(conf, 4),
            context=f"n={len(retrieval_results)}",
        )
        self._measurements[mm.id] = mm
        await self._save_measurement(mm)
        return mm

    # ─── Full Evaluation ────────────────────────────────────────────────────

    async def run_full_evaluation(
        self,
        beliefs: list[dict[str, Any]] | None = None,
        goals: list[dict[str, Any]] | None = None,
        predictions: list[dict[str, Any]] | None = None,
        contradictions: list[dict[str, Any]] | None = None,
        plans: list[dict[str, Any]] | None = None,
    ) -> EvaluationReport:
        """Run all applicable metrics and produce a comprehensive report.

        Identifies the strongest and weakest dimensions and lists
        improvement areas.
        """
        measurements: list[MetricMeasurement] = []

        if beliefs is not None:
            mm = await self.measure_belief_accuracy(beliefs)
            measurements.append(mm)

        if goals is not None:
            mm = await self.measure_goal_completion_rate(goals)
            measurements.append(mm)

        if predictions is not None:
            mm_acc = await self.measure_prediction_accuracy(predictions)
            measurements.append(mm_acc)

            mm_cal = await self.measure_uncertainty_calibration(predictions)
            measurements.append(mm_cal)

        if contradictions is not None:
            mm = await self.measure_contradiction_resolution(contradictions)
            measurements.append(mm)

        if plans is not None:
            mm = await self.measure_planning_quality(plans)
            measurements.append(mm)

        # Determine overall score
        if measurements:
            overall_score = sum(m.value for m in measurements) / len(measurements)
        else:
            overall_score = 0.0

        # Strongest / weakest dimension
        strongest = ""
        weakest = ""
        improvement_areas: list[str] = []

        if measurements:
            by_value = sorted(measurements, key=lambda m: m.value, reverse=True)
            strongest = by_value[0].metric_type.value
            weakest = by_value[-1].metric_type.value

            # Improvement areas: any dimension below 0.5
            for m in measurements:
                if m.value < 0.5:
                    improvement_areas.append(
                        f"{m.metric_type.value}: {m.value:.3f} (below threshold 0.5)"
                    )
                elif m.improvement < 0.0:
                    improvement_areas.append(
                        f"{m.metric_type.value}: regressed by {abs(m.improvement):.3f}"
                    )

        report = EvaluationReport(
            measurements=measurements,
            overall_score=round(overall_score, 6),
            strongest_dimension=strongest,
            weakest_dimension=weakest,
            improvement_areas=improvement_areas,
        )
        self._reports[report.id] = report
        await self._save_report(report)
        return report

    # ─── Historical Performance ─────────────────────────────────────────────

    async def get_historical_performance(
        self,
        metric_type: MetricType | None = None,
    ) -> list[HistoricalPerformance]:
        """Track metrics over time.

        Args:
            metric_type: If provided, filter to this metric type.
                If None, return history for all metric types.

        Returns:
            List of HistoricalPerformance records, one per metric type.
        """
        # Group measurements by metric type
        by_type: dict[MetricType, list[MetricMeasurement]] = {}
        for mm in self._measurements.values():
            if metric_type is not None and mm.metric_type != metric_type:
                continue
            by_type.setdefault(mm.metric_type, []).append(mm)

        results: list[HistoricalPerformance] = []
        for mtype, mms in by_type.items():
            # Sort by timestamp
            sorted_mms = sorted(mms, key=lambda m: m.timestamp)

            values = [m.value for m in sorted_mms]
            current_value = values[-1] if values else 0.0
            best_value = max(values) if values else 0.0
            worst_value = min(values) if values else 0.0

            # Determine trend
            if len(values) >= 3:
                recent = values[-3:]
                if recent[-1] > recent[0]:
                    trend = "improving"
                elif recent[-1] < recent[0]:
                    trend = "declining"
                else:
                    trend = "stable"
            elif len(values) >= 2:
                if values[-1] > values[-2]:
                    trend = "improving"
                elif values[-1] < values[-2]:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"

            hp = HistoricalPerformance(
                metric_type=mtype,
                measurements=sorted_mms,
                trend=trend,
                current_value=round(current_value, 6),
                best_value=round(best_value, 6),
                worst_value=round(worst_value, 6),
            )
            results.append(hp)

        return results

    # ─── Stats ──────────────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        """Return summary statistics for the evaluation framework."""
        total_measurements = len(self._measurements)
        total_reports = len(self._reports)

        by_type: dict[str, int] = {}
        for mm in self._measurements.values():
            key = mm.metric_type.value
            by_type[key] = by_type.get(key, 0) + 1

        avg_value = 0.0
        avg_confidence = 0.0
        if total_measurements > 0:
            avg_value = sum(m.value for m in self._measurements.values()) / total_measurements
            avg_confidence = sum(m.confidence for m in self._measurements.values()) / total_measurements

        avg_overall_score = 0.0
        if total_reports > 0:
            avg_overall_score = sum(r.overall_score for r in self._reports.values()) / total_reports

        return {
            "total_measurements": total_measurements,
            "total_reports": total_reports,
            "measurements_by_type": by_type,
            "average_metric_value": round(avg_value, 4),
            "average_measurement_confidence": round(avg_confidence, 4),
            "average_overall_score": round(avg_overall_score, 4),
        }
