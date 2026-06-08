"""
Simulation Engine — support future rollouts and scenario comparison.

Supports:
- Future rollouts: simulate a sequence of actions and their outcomes
- Multi-step planning: simulate plans step by step
- Alternative futures: generate multiple possible trajectories
- Scenario comparison: compare different scenarios and rank them

Uses the World Model's transition graph to simulate transitions
and estimate cumulative probabilities and costs.
"""

from __future__ import annotations

import json
import time as time_mod
from datetime import datetime, timezone
from typing import Any

from acos.memory.store import StorageBackend
from acos.schemas.v4_models import (
    SimulationRun,
    SimulationStep,
    SimulationStatus,
    ScenarioComparison,
    gen_id,
    utc_now,
)
from acos.cognitive.predictive.state_transition_graph import StateTransitionGraph


class SimulationEngine:
    """Simulation Engine — simulate future trajectories and compare scenarios.

    Usage::

        store = StorageBackend()
        await store.initialize()

        se = SimulationEngine(store, transition_graph)
        await se.initialize()

        # Run a simulation
        run = await se.simulate(
            initial_state="beginner",
            planned_actions=["study", "practice", "test"],
            max_steps=5,
        )

        # Compare scenarios
        comparison = await se.compare_scenarios([
            ("Conservative", "beginner", ["study", "study", "test"]),
            ("Aggressive", "beginner", ["study", "test", "test"]),
        ])
    """

    # Maximum number of alternative branches to explore per step
    MAX_BRANCHES_PER_STEP = 3

    def __init__(
        self,
        storage: StorageBackend,
        transition_graph: StateTransitionGraph,
    ) -> None:
        self._storage = storage
        self._transition_graph = transition_graph
        self._runs: dict[str, SimulationRun] = {}

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create DB tables and load existing runs."""
        await self._create_tables()
        await self._load_from_db()

    async def _create_tables(self) -> None:
        conn = self._storage._conn
        assert conn is not None, "StorageBackend must be initialised first"
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS simulation_runs (
                id TEXT PRIMARY KEY,
                name TEXT DEFAULT '',
                description TEXT DEFAULT '',
                status TEXT NOT NULL,
                initial_state TEXT DEFAULT '',
                planned_actions TEXT DEFAULT '[]',
                max_steps INTEGER DEFAULT 10,
                confidence_threshold REAL DEFAULT 0.1,
                steps TEXT DEFAULT '[]',
                final_state TEXT DEFAULT '',
                total_cost REAL DEFAULT 0.0,
                final_probability REAL DEFAULT 1.0,
                goal_achieved INTEGER DEFAULT 0,
                goal_id TEXT,
                alternative_run_ids TEXT DEFAULT '[]',
                is_best_alternative INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS scenario_comparisons (
                id TEXT PRIMARY KEY,
                scenario_ids TEXT DEFAULT '[]',
                best_scenario_id TEXT,
                comparison_criteria TEXT DEFAULT '[]',
                rankings TEXT DEFAULT '[]',
                summary TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_sim_status
                ON simulation_runs(status);
            CREATE INDEX IF NOT EXISTS idx_sim_goal
                ON simulation_runs(goal_id);
        """)
        await conn.commit()

    async def _load_from_db(self) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        cursor = await conn.execute("SELECT * FROM simulation_runs")
        rows = await cursor.fetchall()
        for row in rows:
            steps_data = json.loads(row["steps"]) if row["steps"] else []
            steps = [SimulationStep(**s) for s in steps_data]
            run = SimulationRun(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                status=SimulationStatus(row["status"]),
                initial_state=row["initial_state"],
                planned_actions=json.loads(row["planned_actions"]) if row["planned_actions"] else [],
                max_steps=row["max_steps"],
                confidence_threshold=row["confidence_threshold"],
                steps=steps,
                final_state=row["final_state"],
                total_cost=row["total_cost"],
                final_probability=row["final_probability"],
                goal_achieved=bool(row["goal_achieved"]),
                goal_id=row["goal_id"],
                alternative_run_ids=json.loads(row["alternative_run_ids"]) if row["alternative_run_ids"] else [],
                is_best_alternative=bool(row["is_best_alternative"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            )
            self._runs[run.id] = run

    async def _save_run(self, run: SimulationRun) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO simulation_runs
               (id, name, description, status, initial_state, planned_actions,
                max_steps, confidence_threshold, steps, final_state, total_cost,
                final_probability, goal_achieved, goal_id, alternative_run_ids,
                is_best_alternative, metadata, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run.id,
                run.name,
                run.description,
                run.status.value,
                run.initial_state,
                json.dumps(run.planned_actions),
                run.max_steps,
                run.confidence_threshold,
                json.dumps([s.model_dump(mode="json") for s in run.steps]),
                run.final_state,
                run.total_cost,
                run.final_probability,
                int(run.goal_achieved),
                run.goal_id,
                json.dumps(run.alternative_run_ids),
                int(run.is_best_alternative),
                json.dumps(run.metadata),
                run.created_at.isoformat(),
                run.completed_at.isoformat() if run.completed_at else None,
            ),
        )
        await conn.commit()

    async def _save_comparison(self, comparison: ScenarioComparison) -> None:
        conn = self._storage._conn
        if conn is None:
            return
        await conn.execute(
            """INSERT OR REPLACE INTO scenario_comparisons
               (id, scenario_ids, best_scenario_id, comparison_criteria,
                rankings, summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                comparison.id,
                json.dumps(comparison.scenario_ids),
                comparison.best_scenario_id,
                json.dumps(comparison.comparison_criteria),
                json.dumps(comparison.rankings),
                comparison.summary,
                comparison.created_at.isoformat(),
            ),
        )
        await conn.commit()

    # ─── Core Simulation Methods ────────────────────────────────────────────

    async def simulate(
        self,
        initial_state: str,
        planned_actions: list[str] | None = None,
        max_steps: int = 10,
        confidence_threshold: float = 0.1,
        goal_target_state: str = "",
        name: str = "",
        description: str = "",
    ) -> SimulationRun:
        """Run a forward simulation from an initial state.

        Simulates executing a sequence of planned actions, predicting
        state transitions at each step. If no planned actions are given,
        explores the most probable transitions.

        Args:
            initial_state: Starting state.
            planned_actions: Actions to simulate in order.
            max_steps: Maximum number of simulation steps.
            confidence_threshold: Stop if cumulative probability drops below this.
            goal_target_state: Target state for goal achievement check.
            name: Human-readable name for this simulation.
            description: Description of the simulation.

        Returns:
            SimulationRun with all steps and outcomes.
        """
        start_time = time_mod.monotonic()

        run = SimulationRun(
            name=name,
            description=description,
            status=SimulationStatus.RUNNING,
            initial_state=initial_state,
            planned_actions=planned_actions or [],
            max_steps=max_steps,
            confidence_threshold=confidence_threshold,
            goal_id=goal_target_state or None,
        )

        # Ensure the initial state exists
        if initial_state not in [s.label for s in await self._transition_graph.get_all_states()]:
            await self._transition_graph.register_state(initial_state)

        current_state = initial_state
        cumulative_probability = 1.0
        cumulative_cost = 0.0

        for step_num in range(max_steps):
            # Determine the action for this step
            if planned_actions and step_num < len(planned_actions):
                action = planned_actions[step_num]
            else:
                action = ""  # Any action

            # Find the most probable transition
            transitions = await self._transition_graph.get_transitions_from(current_state)
            if action:
                transitions = [t for t in transitions if t.action == action]

            if not transitions:
                # No transitions available — simulation ends
                step = SimulationStep(
                    step_number=step_num,
                    state=current_state,
                    action=action,
                    predicted_next_state=current_state,  # Stay in place
                    transition_confidence=0.0,
                    cumulative_cost=cumulative_cost,
                    cumulative_probability=cumulative_probability,
                    observations=["No transitions available — simulation stalled"],
                )
                run.steps.append(step)
                break

            # Pick the most confident transition
            best_transition = max(transitions, key=lambda t: t.confidence)

            cumulative_probability *= best_transition.confidence
            cumulative_cost += best_transition.cost

            step = SimulationStep(
                step_number=step_num,
                state=current_state,
                action=best_transition.action or action,
                predicted_next_state=best_transition.target_state,
                transition_confidence=best_transition.confidence,
                cumulative_cost=cumulative_cost,
                cumulative_probability=cumulative_probability,
                observations=[
                    f"Transition: {best_transition.source_state} -> {best_transition.target_state}",
                    f"Confidence: {best_transition.confidence:.3f}",
                    f"Cost: {best_transition.cost:.3f}",
                    f"Side effects: {best_transition.side_effects[:3]}",
                ],
                metadata={"transition_id": best_transition.id},
            )
            run.steps.append(step)

            # Move to next state
            current_state = best_transition.target_state

            # Check goal achievement
            if goal_target_state and current_state == goal_target_state:
                run.goal_achieved = True
                break

            # Check confidence threshold
            if cumulative_probability < confidence_threshold:
                step.observations.append(
                    f"Confidence dropped below threshold ({cumulative_probability:.3f} < {confidence_threshold})"
                )
                break

        # Finalize
        run.final_state = current_state
        run.total_cost = cumulative_cost
        run.final_probability = cumulative_probability
        run.status = SimulationStatus.COMPLETED
        run.completed_at = utc_now()

        await self._save_run(run)
        self._runs[run.id] = run
        return run

    async def simulate_alternatives(
        self,
        initial_state: str,
        action_sets: list[list[str]],
        max_steps: int = 10,
        goal_target_state: str = "",
    ) -> list[SimulationRun]:
        """Simulate multiple alternative action sequences.

        Args:
            initial_state: Starting state for all alternatives.
            action_sets: List of action sequences to simulate.
            max_steps: Maximum steps per simulation.
            goal_target_state: Target state for goal checking.

        Returns:
            List of SimulationRun, one per action sequence.
        """
        runs = []
        for i, actions in enumerate(action_sets):
            run = await self.simulate(
                initial_state=initial_state,
                planned_actions=actions,
                max_steps=max_steps,
                goal_target_state=goal_target_state,
                name=f"Alternative {i + 1}",
                description=f"Action sequence: {' -> '.join(actions)}",
            )
            runs.append(run)

        # Mark the best alternative
        if runs:
            best = max(runs, key=lambda r: (
                r.final_probability * 2 +  # Weight probability
                (1.0 if r.goal_achieved else 0.0) * 3 -  # Strong weight for goal achievement
                r.total_cost * 0.1  # Slight penalty for cost
            ))
            best.is_best_alternative = True
            # Link alternatives
            for run in runs:
                run.alternative_run_ids = [r.id for r in runs if r.id != run.id]
            await self._save_run(best)

        return runs

    async def compare_scenarios(
        self,
        scenarios: list[tuple[str, str, list[str]]],
        goal_target_state: str = "",
        max_steps: int = 10,
    ) -> ScenarioComparison:
        """Compare multiple simulation scenarios.

        Each scenario is a (name, initial_state, actions) tuple.

        Args:
            scenarios: List of (name, initial_state, actions) tuples.
            goal_target_state: Target state for goal checking.
            max_steps: Maximum steps per simulation.

        Returns:
            ScenarioComparison with rankings.
        """
        runs: list[SimulationRun] = []

        for name, initial_state, actions in scenarios:
            run = await self.simulate(
                initial_state=initial_state,
                planned_actions=actions,
                max_steps=max_steps,
                goal_target_state=goal_target_state,
                name=name,
            )
            runs.append(run)

        # Rank scenarios by a composite score
        def score_run(run: SimulationRun) -> float:
            return (
                run.final_probability * 2.0 +
                (3.0 if run.goal_achieved else 0.0) -
                run.total_cost * 0.1 +
                len(run.steps) * 0.05  # Slight bonus for longer paths (more progress)
            )

        ranked = sorted(runs, key=score_run, reverse=True)

        rankings = []
        for i, run in enumerate(ranked):
            rankings.append({
                "rank": i + 1,
                "run_id": run.id,
                "name": run.name,
                "score": score_run(run),
                "final_probability": run.final_probability,
                "total_cost": run.total_cost,
                "steps": len(run.steps),
                "goal_achieved": run.goal_achieved,
            })

        best = ranked[0] if ranked else None
        summary = f"Compared {len(scenarios)} scenarios. "
        if best:
            summary += f"Best: '{best.name}' (p={best.final_probability:.3f}, cost={best.total_cost:.3f})"

        comparison = ScenarioComparison(
            scenario_ids=[r.id for r in runs],
            best_scenario_id=best.id if best else None,
            comparison_criteria=["probability", "cost", "goal_achievement", "progress"],
            rankings=rankings,
            summary=summary,
        )
        await self._save_comparison(comparison)
        return comparison

    async def rollout(
        self,
        initial_state: str,
        num_rollouts: int = 5,
        max_steps: int = 10,
        goal_target_state: str = "",
    ) -> list[SimulationRun]:
        """Run multiple stochastic rollouts from an initial state.

        Each rollout follows the most probable transitions, but explores
        different branches to get a distribution of outcomes.

        Args:
            initial_state: Starting state.
            num_rollouts: Number of rollouts to run.
            max_steps: Maximum steps per rollout.
            goal_target_state: Target state.

        Returns:
            List of SimulationRun from each rollout.
        """
        runs = []
        for i in range(num_rollouts):
            # For each rollout, we simulate following the transition graph
            # but at each step, we pick from the top transitions (not always the best)
            run = await self._stochastic_rollout(
                initial_state=initial_state,
                max_steps=max_steps,
                goal_target_state=goal_target_state,
                rollout_index=i,
            )
            runs.append(run)

        return runs

    async def _stochastic_rollout(
        self,
        initial_state: str,
        max_steps: int,
        goal_target_state: str,
        rollout_index: int,
    ) -> SimulationRun:
        """Run a single stochastic rollout.

        At each step, picks from the top transitions with a preference
        determined by the rollout index (to explore different branches).
        """
        run = SimulationRun(
            name=f"Rollout {rollout_index + 1}",
            status=SimulationStatus.RUNNING,
            initial_state=initial_state,
            max_steps=max_steps,
            goal_id=goal_target_state or None,
        )

        current_state = initial_state
        cumulative_probability = 1.0
        cumulative_cost = 0.0

        for step_num in range(max_steps):
            transitions = await self._transition_graph.get_transitions_from(current_state)

            if not transitions:
                break

            # Pick a transition: for rollout diversity, pick based on index
            # Even rollouts take the best, odd rollouts take alternatives
            if rollout_index % 2 == 0 or len(transitions) == 1:
                chosen = transitions[0]  # Best transition (already sorted by confidence)
            else:
                # Pick from top transitions
                idx = min(rollout_index % len(transitions), self.MAX_BRANCHES_PER_STEP - 1)
                chosen = transitions[idx]

            cumulative_probability *= chosen.confidence
            cumulative_cost += chosen.cost

            step = SimulationStep(
                step_number=step_num,
                state=current_state,
                action=chosen.action,
                predicted_next_state=chosen.target_state,
                transition_confidence=chosen.confidence,
                cumulative_cost=cumulative_cost,
                cumulative_probability=cumulative_probability,
            )
            run.steps.append(step)

            current_state = chosen.target_state

            if goal_target_state and current_state == goal_target_state:
                run.goal_achieved = True
                break

            if cumulative_probability < 0.05:
                break

        run.final_state = current_state
        run.total_cost = cumulative_cost
        run.final_probability = cumulative_probability
        run.status = SimulationStatus.COMPLETED
        run.completed_at = utc_now()

        await self._save_run(run)
        self._runs[run.id] = run
        return run

    # ─── Access Methods ─────────────────────────────────────────────────────

    async def get_run(self, run_id: str) -> SimulationRun | None:
        """Get a specific simulation run."""
        return self._runs.get(run_id)

    async def get_stats(self) -> dict[str, Any]:
        """Get simulation engine statistics."""
        total = len(self._runs)
        completed = sum(1 for r in self._runs.values() if r.status == SimulationStatus.COMPLETED)
        goal_achieved = sum(1 for r in self._runs.values() if r.goal_achieved)

        avg_probability = 0.0
        avg_cost = 0.0
        if completed > 0:
            completed_runs = [r for r in self._runs.values() if r.status == SimulationStatus.COMPLETED]
            avg_probability = sum(r.final_probability for r in completed_runs) / completed
            avg_cost = sum(r.total_cost for r in completed_runs) / completed

        return {
            "total_runs": total,
            "completed_runs": completed,
            "goal_achieved_runs": goal_achieved,
            "avg_final_probability": round(avg_probability, 4),
            "avg_total_cost": round(avg_cost, 4),
        }
