#!/usr/bin/env python3
"""
ACOS Runtime — Database Table Activation Script

Creates ALL missing v0.3, v0.4, and v0.5 database tables in the ACOS runtime.
Uses the EXACT CREATE TABLE IF NOT EXISTS SQL from each module.

This script is idempotent — safe to run multiple times.

Usage:
    python activate_tables.py
"""

import sqlite3
import os
import sys

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "acos.db")

# ─── v0.3 (Dynamics) — 9 tables ──────────────────────────────────────────────

V03_TABLES = {
    # From dynamics/attention.py
    "attention_focus": """
        CREATE TABLE IF NOT EXISTS attention_focus (
            id TEXT PRIMARY KEY,
            target_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            focus_score REAL DEFAULT 1.0,
            reinforcement_count INTEGER DEFAULT 0,
            last_reinforced TEXT NOT NULL,
            decay_rate REAL DEFAULT 0.05,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_attention_target
            ON attention_focus(target_id);
        CREATE INDEX IF NOT EXISTS idx_attention_type
            ON attention_focus(target_type);
        CREATE INDEX IF NOT EXISTS idx_attention_score
            ON attention_focus(focus_score);
    """,

    # From dynamics/cognitive_graph.py
    "cognitive_nodes": """
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

        CREATE INDEX IF NOT EXISTS idx_cog_nodes_type
            ON cognitive_nodes(node_type);
        CREATE INDEX IF NOT EXISTS idx_cog_nodes_attention
            ON cognitive_nodes(attention_score);
    """,

    # From dynamics/cognitive_graph.py
    "cognitive_edges": """
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

        CREATE INDEX IF NOT EXISTS idx_cog_edges_source
            ON cognitive_edges(source_id);
        CREATE INDEX IF NOT EXISTS idx_cog_edges_target
            ON cognitive_edges(target_id);
        CREATE INDEX IF NOT EXISTS idx_cog_edges_type
            ON cognitive_edges(edge_type);
    """,

    # From dynamics/counterfactual.py
    "counterfactual_scenarios": """
        CREATE TABLE IF NOT EXISTS counterfactual_scenarios (
            id TEXT PRIMARY KEY,
            scenario_type TEXT NOT NULL,
            premise TEXT NOT NULL,
            original_state TEXT DEFAULT '{}',
            modified_state TEXT DEFAULT '{}',
            predicted_outcomes TEXT DEFAULT '[]',
            affected_belief_ids TEXT DEFAULT '[]',
            affected_goal_ids TEXT DEFAULT '[]',
            affected_concept_ids TEXT DEFAULT '[]',
            confidence REAL DEFAULT 0.3,
            reasoning_chain TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_cf_type
            ON counterfactual_scenarios(scenario_type);
        CREATE INDEX IF NOT EXISTS idx_cf_premise
            ON counterfactual_scenarios(premise);
    """,

    # From dynamics/counterfactual.py
    "counterfactual_results": """
        CREATE TABLE IF NOT EXISTS counterfactual_results (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            scenario_type TEXT NOT NULL,
            scenarios TEXT DEFAULT '[]',
            best_scenario_id TEXT,
            overall_confidence REAL DEFAULT 0.0,
            reasoning_time_ms REAL DEFAULT 0.0,
            created_at TEXT NOT NULL
        );
    """,

    # From dynamics/state_evolution.py
    "state_deltas": """
        CREATE TABLE IF NOT EXISTS state_deltas (
            id TEXT PRIMARY KEY,
            operator TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            before_value REAL DEFAULT 0.0,
            after_value REAL DEFAULT 0.0,
            delta REAL DEFAULT 0.0,
            reason TEXT DEFAULT '',
            evidence_ids TEXT DEFAULT '[]',
            timestamp TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_deltas_operator
            ON state_deltas(operator);
        CREATE INDEX IF NOT EXISTS idx_deltas_target
            ON state_deltas(target_id);
    """,

    # From dynamics/state_evolution.py
    "evolution_results": """
        CREATE TABLE IF NOT EXISTS evolution_results (
            id TEXT PRIMARY KEY,
            deltas TEXT DEFAULT '[]',
            beliefs_reinforced INTEGER DEFAULT 0,
            beliefs_weakened INTEGER DEFAULT 0,
            concepts_promoted INTEGER DEFAULT 0,
            concepts_suppressed INTEGER DEFAULT 0,
            contradictions_resolved INTEGER DEFAULT 0,
            total_changes INTEGER DEFAULT 0,
            evolution_time_ms REAL DEFAULT 0.0,
            timestamp TEXT NOT NULL
        );
    """,

    # From dynamics/uncertainty.py
    "uncertainty_entries": """
        CREATE TABLE IF NOT EXISTS uncertainty_entries (
            id TEXT PRIMARY KEY,
            uncertainty_type TEXT NOT NULL,
            description TEXT NOT NULL,
            related_ids TEXT DEFAULT '[]',
            severity REAL DEFAULT 0.5,
            impact_on_planning REAL DEFAULT 0.5,
            resolution_suggestion TEXT DEFAULT '',
            is_resolved INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_uncertainty_type
            ON uncertainty_entries(uncertainty_type);
        CREATE INDEX IF NOT EXISTS idx_uncertainty_severity
            ON uncertainty_entries(severity);
        CREATE INDEX IF NOT EXISTS idx_uncertainty_resolved
            ON uncertainty_entries(is_resolved);
    """,

    # From dynamics/plan_state.py
    "plans": """
        CREATE TABLE IF NOT EXISTS plans (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft',
            steps TEXT DEFAULT '[]',
            subplan_ids TEXT DEFAULT '[]',
            parent_plan_id TEXT,
            dependency_ids TEXT DEFAULT '[]',
            expected_outcome TEXT DEFAULT '',
            actual_outcome TEXT DEFAULT '',
            overall_confidence REAL DEFAULT 0.5,
            related_goal_ids TEXT DEFAULT '[]',
            related_belief_ids TEXT DEFAULT '[]',
            related_concept_ids TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status);
        CREATE INDEX IF NOT EXISTS idx_plans_parent ON plans(parent_plan_id);
    """,
}

# ─── v0.4 (Predictive) — 12 tables ───────────────────────────────────────────

V04_TABLES = {
    # From predictive/state_transition_graph.py
    "state_transitions": """
        CREATE TABLE IF NOT EXISTS state_transitions (
            id TEXT PRIMARY KEY,
            source_state TEXT NOT NULL,
            target_state TEXT NOT NULL,
            action TEXT DEFAULT '',
            transition_type TEXT NOT NULL,
            frequency INTEGER DEFAULT 1,
            confidence REAL DEFAULT 0.5,
            cost REAL DEFAULT 0.0,
            duration_estimate REAL DEFAULT 0.0,
            preconditions TEXT DEFAULT '[]',
            side_effects TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_st_source
            ON state_transitions(source_state);
        CREATE INDEX IF NOT EXISTS idx_st_target
            ON state_transitions(target_state);
        CREATE INDEX IF NOT EXISTS idx_st_action
            ON state_transitions(action);
    """,

    # From predictive/state_transition_graph.py
    "state_vectors": """
        CREATE TABLE IF NOT EXISTS state_vectors (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            features TEXT DEFAULT '{}',
            belief_ids TEXT DEFAULT '[]',
            goal_ids TEXT DEFAULT '[]',
            concept_ids TEXT DEFAULT '[]',
            uncertainty_level REAL DEFAULT 0.0,
            timestamp TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_sv_label
            ON state_vectors(label);
    """,

    # From predictive/world_model.py
    "predictions": """
        CREATE TABLE IF NOT EXISTS predictions (
            id TEXT PRIMARY KEY,
            prediction_type TEXT NOT NULL,
            description TEXT NOT NULL,
            source_state TEXT DEFAULT '',
            predicted_state TEXT DEFAULT '',
            action TEXT DEFAULT '',
            goal_id TEXT,
            confidence REAL DEFAULT 0.5,
            time_horizon REAL DEFAULT 0.0,
            probability REAL DEFAULT 0.5,
            transition_ids TEXT DEFAULT '[]',
            assumptions TEXT DEFAULT '[]',
            reasoning_chain TEXT DEFAULT '[]',
            is_verified INTEGER DEFAULT 0,
            actual_outcome TEXT,
            prediction_error REAL,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            verified_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_pred_type
            ON predictions(prediction_type);
        CREATE INDEX IF NOT EXISTS idx_pred_source
            ON predictions(source_state);
        CREATE INDEX IF NOT EXISTS idx_pred_goal
            ON predictions(goal_id);
    """,

    # From predictive/world_model.py
    "world_model_state": """
        CREATE TABLE IF NOT EXISTS world_model_state (
            id TEXT PRIMARY KEY,
            total_transitions INTEGER DEFAULT 0,
            total_predictions INTEGER DEFAULT 0,
            verified_predictions INTEGER DEFAULT 0,
            average_prediction_accuracy REAL DEFAULT 0.0,
            model_confidence REAL DEFAULT 0.0,
            timestamp TEXT NOT NULL
        );
    """,

    # From predictive/goal_forecast.py
    "goal_forecasts": """
        CREATE TABLE IF NOT EXISTS goal_forecasts (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            goal_description TEXT DEFAULT '',
            feasibility TEXT NOT NULL,
            success_probability REAL DEFAULT 0.5,
            failure_probability REAL DEFAULT 0.5,
            estimated_steps_remaining INTEGER DEFAULT 0,
            estimated_duration REAL DEFAULT 0.0,
            estimated_completion_date TEXT,
            blocking_factors TEXT DEFAULT '[]',
            risk_factors TEXT DEFAULT '[]',
            dependency_risks TEXT DEFAULT '[]',
            recommended_next_actions TEXT DEFAULT '[]',
            prerequisite_goals TEXT DEFAULT '[]',
            alternative_approaches TEXT DEFAULT '[]',
            supporting_transition_ids TEXT DEFAULT '[]',
            supporting_causal_ids TEXT DEFAULT '[]',
            simulation_run_ids TEXT DEFAULT '[]',
            confidence REAL DEFAULT 0.5,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_gf_goal
            ON goal_forecasts(goal_id);
        CREATE INDEX IF NOT EXISTS idx_gf_feasibility
            ON goal_forecasts(feasibility);
    """,

    # From predictive/goal_forecast.py
    "goal_forecast_reports": """
        CREATE TABLE IF NOT EXISTS goal_forecast_reports (
            id TEXT PRIMARY KEY,
            forecasts TEXT DEFAULT '[]',
            total_goals_assessed INTEGER DEFAULT 0,
            achievable_count INTEGER DEFAULT 0,
            unlikely_count INTEGER DEFAULT 0,
            infeasible_count INTEGER DEFAULT 0,
            top_priority_action TEXT DEFAULT '',
            overall_confidence REAL DEFAULT 0.5,
            created_at TEXT NOT NULL
        );
    """,

    # From predictive/outcome_predictor.py
    "outcome_predictions": """
        CREATE TABLE IF NOT EXISTS outcome_predictions (
            id TEXT PRIMARY KEY,
            action TEXT NOT NULL,
            context TEXT DEFAULT '',
            success_probability REAL DEFAULT 0.5,
            failure_probability REAL DEFAULT 0.5,
            partial_success_probability REAL DEFAULT 0.0,
            expected_duration REAL DEFAULT 0.0,
            expected_resources REAL DEFAULT 0.0,
            duration_variance REAL DEFAULT 0.0,
            risk_factors TEXT DEFAULT '[]',
            mitigating_factors TEXT DEFAULT '[]',
            worst_case_outcome TEXT DEFAULT '',
            best_case_outcome TEXT DEFAULT '',
            confidence REAL DEFAULT 0.5,
            supporting_transition_ids TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_op_action
            ON outcome_predictions(action);
    """,

    # From predictive/simulation_engine.py
    "simulation_runs": """
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

        CREATE INDEX IF NOT EXISTS idx_sim_status
            ON simulation_runs(status);
        CREATE INDEX IF NOT EXISTS idx_sim_goal
            ON simulation_runs(goal_id);
    """,

    # From predictive/simulation_engine.py
    "scenario_comparisons": """
        CREATE TABLE IF NOT EXISTS scenario_comparisons (
            id TEXT PRIMARY KEY,
            scenario_ids TEXT DEFAULT '[]',
            best_scenario_id TEXT,
            comparison_criteria TEXT DEFAULT '[]',
            rankings TEXT DEFAULT '[]',
            summary TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
    """,

    # From predictive/causal_reasoner.py
    "causal_links": """
        CREATE TABLE IF NOT EXISTS causal_links (
            id TEXT PRIMARY KEY,
            cause_id TEXT NOT NULL,
            cause_label TEXT NOT NULL,
            effect_id TEXT NOT NULL,
            effect_label TEXT NOT NULL,
            direction TEXT NOT NULL,
            strength TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            supporting_observations INTEGER DEFAULT 0,
            contradicting_observations INTEGER DEFAULT 0,
            intervention_evidence INTEGER DEFAULT 0,
            mechanism TEXT DEFAULT '',
            mediator_ids TEXT DEFAULT '[]',
            confounder_ids TEXT DEFAULT '[]',
            preconditions TEXT DEFAULT '[]',
            context_description TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_cl_cause
            ON causal_links(cause_id);
        CREATE INDEX IF NOT EXISTS idx_cl_effect
            ON causal_links(effect_id);
        CREATE INDEX IF NOT EXISTS idx_cl_strength
            ON causal_links(strength);
    """,

    # From predictive/causal_reasoner.py
    "intervention_results": """
        CREATE TABLE IF NOT EXISTS intervention_results (
            id TEXT PRIMARY KEY,
            intervention_target TEXT NOT NULL,
            intervention_value TEXT NOT NULL,
            original_value TEXT DEFAULT '',
            predicted_effects TEXT DEFAULT '[]',
            affected_goal_ids TEXT DEFAULT '[]',
            affected_belief_ids TEXT DEFAULT '[]',
            causal_paths TEXT DEFAULT '[]',
            confidence REAL DEFAULT 0.3,
            reasoning_chain TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );
    """,

    # From predictive/causal_reasoner.py
    "causal_discoveries": """
        CREATE TABLE IF NOT EXISTS causal_discoveries (
            id TEXT PRIMARY KEY,
            discovered_links TEXT DEFAULT '[]',
            rejected_links TEXT DEFAULT '[]',
            ambiguous_links TEXT DEFAULT '[]',
            confidence_threshold REAL DEFAULT 0.5,
            total_observations_used INTEGER DEFAULT 0,
            discovery_time_ms REAL DEFAULT 0.0,
            created_at TEXT NOT NULL
        );
    """,
}

# ─── v0.5 (Unified) — 23 tables ──────────────────────────────────────────────

V05_TABLES = {
    # From unified/self_model.py
    "self_performance_records": """
        CREATE TABLE IF NOT EXISTS self_performance_records (
            id TEXT PRIMARY KEY,
            dimension TEXT NOT NULL,
            score REAL NOT NULL DEFAULT 0.5,
            context TEXT NOT NULL DEFAULT '',
            session_id TEXT,
            timestamp TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_perf_dimension
            ON self_performance_records(dimension);
        CREATE INDEX IF NOT EXISTS idx_perf_timestamp
            ON self_performance_records(timestamp);
    """,

    # From unified/self_model.py
    "self_model_preferences": """
        CREATE TABLE IF NOT EXISTS self_model_preferences (
            id TEXT PRIMARY KEY,
            model_a TEXT NOT NULL,
            model_b TEXT NOT NULL,
            preferred TEXT NOT NULL,
            domain TEXT NOT NULL DEFAULT '',
            confidence REAL NOT NULL DEFAULT 0.5,
            evidence_count INTEGER NOT NULL DEFAULT 0,
            last_updated TEXT NOT NULL,
            created_at TEXT NOT NULL,
            lookup_key TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_pref_domain
            ON self_model_preferences(domain);
        CREATE INDEX IF NOT EXISTS idx_pref_lookup
            ON self_model_preferences(lookup_key);
    """,

    # From unified/active_learning.py
    "all_prediction_errors": """
        CREATE TABLE IF NOT EXISTS all_prediction_errors (
            id TEXT PRIMARY KEY,
            prediction_id TEXT NOT NULL,
            predicted_value TEXT DEFAULT '',
            actual_value TEXT DEFAULT '',
            absolute_error REAL DEFAULT 0.0,
            squared_error REAL DEFAULT 0.0,
            learning_signal TEXT NOT NULL DEFAULT 'partial',
            belief_ids_updated TEXT DEFAULT '[]',
            confidence_before REAL DEFAULT 0.5,
            confidence_after REAL DEFAULT 0.5,
            world_model_updated INTEGER DEFAULT 0,
            reflection TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_all_pe_prediction
            ON all_prediction_errors(prediction_id);
        CREATE INDEX IF NOT EXISTS idx_all_pe_signal
            ON all_prediction_errors(learning_signal);
        CREATE INDEX IF NOT EXISTS idx_all_pe_created
            ON all_prediction_errors(created_at);
    """,

    # From unified/active_learning.py
    "all_prediction_belief_map": """
        CREATE TABLE IF NOT EXISTS all_prediction_belief_map (
            id TEXT PRIMARY KEY,
            prediction_id TEXT NOT NULL,
            belief_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_all_pbm_prediction
            ON all_prediction_belief_map(prediction_id);
        CREATE INDEX IF NOT EXISTS idx_all_pbm_belief
            ON all_prediction_belief_map(belief_id);
    """,

    # From unified/active_learning.py
    "all_confidence_map": """
        CREATE TABLE IF NOT EXISTS all_confidence_map (
            prediction_id TEXT PRIMARY KEY,
            confidence REAL DEFAULT 0.5,
            updated_at TEXT NOT NULL
        );
    """,

    # From unified/cognitive_manifold.py
    "manifold_points": """
        CREATE TABLE IF NOT EXISTS manifold_points (
            id TEXT PRIMARY KEY,
            element_id TEXT NOT NULL,
            element_type TEXT NOT NULL,
            label TEXT DEFAULT '',
            features TEXT DEFAULT '{}',
            cluster_id TEXT,
            activation_level REAL DEFAULT 0.0,
            last_activated TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_mp_element
            ON manifold_points(element_id);
        CREATE INDEX IF NOT EXISTS idx_mp_type
            ON manifold_points(element_type);
        CREATE INDEX IF NOT EXISTS idx_mp_cluster
            ON manifold_points(cluster_id);
    """,

    # From unified/cognitive_manifold.py
    "manifold_clusters": """
        CREATE TABLE IF NOT EXISTS manifold_clusters (
            id TEXT PRIMARY KEY,
            label TEXT DEFAULT '',
            point_ids TEXT DEFAULT '[]',
            centroid_features TEXT DEFAULT '{}',
            coherence REAL DEFAULT 0.0,
            dominant_type TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_mc_dominant
            ON manifold_clusters(dominant_type);
    """,

    # From unified/cognitive_manifold.py
    "manifold_state": """
        CREATE TABLE IF NOT EXISTS manifold_state (
            id TEXT PRIMARY KEY,
            total_points INTEGER DEFAULT 0,
            total_clusters INTEGER DEFAULT 0,
            average_activation REAL DEFAULT 0.0,
            dimensionality INTEGER DEFAULT 10,
            dominant_cluster_id TEXT,
            timestamp TEXT NOT NULL
        );
    """,

    # From unified/attention_economy.py
    "attention_allocations": """
        CREATE TABLE IF NOT EXISTS attention_allocations (
            id TEXT PRIMARY KEY,
            target_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            allocated_amount REAL NOT NULL DEFAULT 0.0,
            priority_reason TEXT NOT NULL DEFAULT '',
            decay_rate REAL NOT NULL DEFAULT 0.05,
            granted_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_alloc_target
            ON attention_allocations(target_id);
        CREATE INDEX IF NOT EXISTS idx_alloc_type
            ON attention_allocations(target_type);
        CREATE INDEX IF NOT EXISTS idx_alloc_amount
            ON attention_allocations(allocated_amount);
    """,

    # From unified/attention_economy.py
    "attention_budget_config": """
        CREATE TABLE IF NOT EXISTS attention_budget_config (
            id TEXT PRIMARY KEY,
            total_budget REAL NOT NULL DEFAULT 100.0,
            updated_at TEXT NOT NULL
        );
    """,

    # From unified/enhanced_causal.py
    "ecr_causal_chains": """
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

        CREATE INDEX IF NOT EXISTS idx_ecr_chains_length
            ON ecr_causal_chains(length);
    """,

    # From unified/enhanced_causal.py
    "ecr_causal_forecasts": """
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

        CREATE INDEX IF NOT EXISTS idx_ecr_fc_cause
            ON ecr_causal_forecasts(current_cause);
    """,

    # From unified/enhanced_causal.py
    "ecr_root_cause_analyses": """
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

        CREATE INDEX IF NOT EXISTS idx_ecr_rca_effect
            ON ecr_root_cause_analyses(observed_effect);
    """,

    # From unified/goal_competition.py
    "goal_competition_entries": """
        CREATE TABLE IF NOT EXISTS goal_competition_entries (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            goal_description TEXT DEFAULT '',
            importance REAL DEFAULT 0.5,
            urgency REAL DEFAULT 0.5,
            uncertainty REAL DEFAULT 0.5,
            expected_reward REAL DEFAULT 0.5,
            dependency_satisfaction REAL DEFAULT 0.5,
            attention_score REAL DEFAULT 0.0,
            progress_momentum REAL DEFAULT 0.0,
            composite_score REAL DEFAULT 0.0,
            rank INTEGER DEFAULT 0,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_gce_goal
            ON goal_competition_entries(goal_id);
        CREATE INDEX IF NOT EXISTS idx_gce_rank
            ON goal_competition_entries(rank);
    """,

    # From unified/goal_competition.py
    "goal_competition_results": """
        CREATE TABLE IF NOT EXISTS goal_competition_results (
            id TEXT PRIMARY KEY,
            entries TEXT DEFAULT '[]',
            winner_id TEXT,
            total_goals_competed INTEGER DEFAULT 0,
            competition_time_ms REAL DEFAULT 0.0,
            factor_weights TEXT DEFAULT '{}',
            timestamp TEXT NOT NULL
        );
    """,

    # From unified/world_model_engine.py
    "wme_future_predictions": """
        CREATE TABLE IF NOT EXISTS wme_future_predictions (
            id TEXT PRIMARY KEY,
            predicted_state TEXT NOT NULL,
            probability REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            risk_level TEXT NOT NULL DEFAULT 'medium',
            risk_factors TEXT DEFAULT '[]',
            time_horizon_seconds REAL DEFAULT 0.0,
            assumptions TEXT DEFAULT '[]',
            reasoning_chain TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_wme_fp_state
            ON wme_future_predictions(predicted_state);
    """,

    # From unified/world_model_engine.py
    "wme_action_estimates": """
        CREATE TABLE IF NOT EXISTS wme_action_estimates (
            id TEXT PRIMARY KEY,
            action TEXT NOT NULL,
            expected_outcome TEXT DEFAULT '',
            success_probability REAL DEFAULT 0.5,
            failure_probability REAL DEFAULT 0.5,
            uncertainty REAL DEFAULT 0.5,
            expected_duration REAL DEFAULT 0.0,
            expected_cost REAL DEFAULT 0.0,
            risk_factors TEXT DEFAULT '[]',
            confidence REAL DEFAULT 0.5,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_wme_ae_action
            ON wme_action_estimates(action);
    """,

    # From unified/world_model_engine.py
    "wme_error_history": """
        CREATE TABLE IF NOT EXISTS wme_error_history (
            id TEXT PRIMARY KEY,
            source_state TEXT NOT NULL,
            predicted_state TEXT NOT NULL,
            actual_state TEXT NOT NULL,
            error REAL NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_wme_eh_source
            ON wme_error_history(source_state);
    """,

    # From unified/world_model_engine.py
    "wme_goal_risk_factors": """
        CREATE TABLE IF NOT EXISTS wme_goal_risk_factors (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            risk_factor TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_wme_grf_goal
            ON wme_goal_risk_factors(goal_id);
    """,

    # From unified/evaluation.py
    "ef_metric_measurements": """
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

        CREATE INDEX IF NOT EXISTS idx_ef_mm_type
            ON ef_metric_measurements(metric_type);
        CREATE INDEX IF NOT EXISTS idx_ef_mm_ts
            ON ef_metric_measurements(timestamp);
    """,

    # From unified/evaluation.py
    "ef_evaluation_reports": """
        CREATE TABLE IF NOT EXISTS ef_evaluation_reports (
            id TEXT PRIMARY KEY,
            measurements TEXT DEFAULT '[]',
            overall_score REAL DEFAULT 0.0,
            strongest_dimension TEXT DEFAULT '',
            weakest_dimension TEXT DEFAULT '',
            improvement_areas TEXT DEFAULT '[]',
            timestamp TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_ef_report_ts
            ON ef_evaluation_reports(timestamp);
    """,

    # From unified/cognitive_cycle.py
    "cognitive_cycle_traces": """
        CREATE TABLE IF NOT EXISTS cognitive_cycle_traces (
            id TEXT PRIMARY KEY,
            query TEXT DEFAULT '',
            total_duration_ms REAL DEFAULT 0.0,
            phases_completed INTEGER DEFAULT 0,
            phases_failed INTEGER DEFAULT 0,
            final_synthesis TEXT DEFAULT '',
            learning_applied INTEGER DEFAULT 0,
            world_model_updated INTEGER DEFAULT 0,
            beliefs_changed INTEGER DEFAULT 0,
            goals_reprioritized INTEGER DEFAULT 0,
            predictions_made INTEGER DEFAULT 0,
            prediction_errors_measured INTEGER DEFAULT 0,
            self_model_updated INTEGER DEFAULT 0,
            phase_results TEXT DEFAULT '[]',
            timestamp TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_cct_query
            ON cognitive_cycle_traces(query);
        CREATE INDEX IF NOT EXISTS idx_cct_timestamp
            ON cognitive_cycle_traces(timestamp);
    """,

    # From unified/cognitive_cycle.py
    "phase_results": """
        CREATE TABLE IF NOT EXISTS phase_results (
            id TEXT PRIMARY KEY,
            cycle_trace_id TEXT NOT NULL,
            phase TEXT NOT NULL,
            success INTEGER DEFAULT 1,
            duration_ms REAL DEFAULT 0.0,
            items_processed INTEGER DEFAULT 0,
            items_produced INTEGER DEFAULT 0,
            summary TEXT DEFAULT '',
            errors TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            timestamp TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_pr_cycle
            ON phase_results(cycle_trace_id);
    """,
}


def get_existing_tables(conn: sqlite3.Connection) -> set:
    """Get the set of existing table names in the database."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return {row[0] for row in cursor.fetchall()}


def get_defined_tables() -> dict[str, str]:
    """Get all defined table names and their version source."""
    defined = {}
    for name in V03_TABLES:
        defined[name] = "v0.3"
    for name in V04_TABLES:
        defined[name] = "v0.4"
    for name in V05_TABLES:
        defined[name] = "v0.5"
    return defined


def activate():
    """Main activation function."""
    print("=" * 70)
    print("ACOS Runtime — Database Table Activation Script")
    print("=" * 70)
    print()

    # Check database exists
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Creating new database...")
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    # Get existing tables before activation
    existing_before = get_existing_tables(conn)
    print(f"Tables before activation: {len(existing_before)}")
    print()

    defined_tables = get_defined_tables()
    print(f"Total tables to ensure: {len(defined_tables)}")
    print(f"  v0.3 (Dynamics):   {len(V03_TABLES)} tables")
    print(f"  v0.4 (Predictive): {len(V04_TABLES)} tables")
    print(f"  v0.5 (Unified):    {len(V05_TABLES)} tables")
    print()

    # Track which tables were newly created
    newly_created = []
    already_exists = []
    errors = []

    # Activate v0.3 tables
    print("─── Activating v0.3 (Dynamics) tables ───")
    for table_name, sql in V03_TABLES.items():
        status = "EXISTS" if table_name in existing_before else "CREATING"
        print(f"  [{status}] {table_name}")
        try:
            conn.executescript(sql)
            conn.commit()
            if table_name not in existing_before:
                newly_created.append(("v0.3", table_name))
            else:
                already_exists.append(("v0.3", table_name))
        except Exception as e:
            errors.append(("v0.3", table_name, str(e)))
            print(f"  [ERROR] {table_name}: {e}")

    # Activate v0.4 tables
    print()
    print("─── Activating v0.4 (Predictive) tables ───")
    for table_name, sql in V04_TABLES.items():
        status = "EXISTS" if table_name in existing_before else "CREATING"
        print(f"  [{status}] {table_name}")
        try:
            conn.executescript(sql)
            conn.commit()
            if table_name not in existing_before:
                newly_created.append(("v0.4", table_name))
            else:
                already_exists.append(("v0.4", table_name))
        except Exception as e:
            errors.append(("v0.4", table_name, str(e)))
            print(f"  [ERROR] {table_name}: {e}")

    # Activate v0.5 tables
    print()
    print("─── Activating v0.5 (Unified) tables ───")
    for table_name, sql in V05_TABLES.items():
        status = "EXISTS" if table_name in existing_before else "CREATING"
        print(f"  [{status}] {table_name}")
        try:
            conn.executescript(sql)
            conn.commit()
            if table_name not in existing_before:
                newly_created.append(("v0.5", table_name))
            else:
                already_exists.append(("v0.5", table_name))
        except Exception as e:
            errors.append(("v0.5", table_name, str(e)))
            print(f"  [ERROR] {table_name}: {e}")

    # Verify all tables exist
    print()
    print("─── Verification ───")
    existing_after = get_existing_tables(conn)
    all_expected = set(defined_tables.keys())
    missing = all_expected - existing_after

    # Count by version
    v03_active = sum(1 for t in existing_after if t in V03_TABLES)
    v04_active = sum(1 for t in existing_after if t in V04_TABLES)
    v05_active = sum(1 for t in existing_after if t in V05_TABLES)

    print(f"  Total tables in DB after activation: {len(existing_after)}")
    print(f"  v0.3 tables active: {v03_active}/{len(V03_TABLES)}")
    print(f"  v0.4 tables active: {v04_active}/{len(V04_TABLES)}")
    print(f"  v0.5 tables active: {v05_active}/{len(V05_TABLES)}")
    print(f"  Newly created: {len(newly_created)}")
    print(f"  Already existed: {len(already_exists)}")
    print(f"  Missing: {len(missing)}")

    if newly_created:
        print()
        print("  Newly created tables:")
        for version, table_name in sorted(newly_created):
            print(f"    [{version}] {table_name}")

    if missing:
        print()
        print("  MISSING TABLES (still not found after activation):")
        for table_name in sorted(missing):
            print(f"    [{defined_tables[table_name]}] {table_name}")

    if errors:
        print()
        print("  ERRORS encountered:")
        for version, table_name, error in errors:
            print(f"    [{version}] {table_name}: {error}")

    # Print summary report
    print()
    print("=" * 70)
    print("ACTIVATION REPORT")
    print("=" * 70)
    print(f"  Defined tables:  {len(defined_tables)}")
    print(f"  Active tables:   {len(existing_after & all_expected)}")
    print(f"  Missing tables:  {len(missing)}")
    print(f"  Errors:          {len(errors)}")
    print()

    if not missing and not errors:
        print("  ✓ ALL TABLES ACTIVATED SUCCESSFULLY")
    elif not missing:
        print("  ⚠ All tables exist but some errors occurred during activation")
    else:
        print("  ✗ SOME TABLES ARE STILL MISSING")

    conn.close()
    return len(missing) == 0


if __name__ == "__main__":
    success = activate()
    sys.exit(0 if success else 1)
