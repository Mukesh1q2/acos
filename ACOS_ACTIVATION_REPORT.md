# ACOS Runtime Activation Report

**Generated**: 2026-06-08  
**Activation Run**: 100 queries through `process_query_v2()`  
**Database**: `/home/z/my-project/acos-runtime/data/acos.db`  
**Report Version**: 1.0  

---

## 1. Queries Executed

| Metric | Value |
|--------|-------|
| Total queries | 100 |
| Successful | 100 |
| Failed | 0 |
| Total time | 65.60s |
| Average query time | 0.64s |
| Real LLM verified | Yes |

All 100 queries completed successfully through the full `process_query_v2()` pipeline with zero failures at the top level.

---

## 2. Tables Populated (with Row Counts)

### Tables WITH Data (22 of 61)

| Table | Rows | Version | Subsystem |
|-------|------|---------|-----------|
| `cognitive_traces` | 1,852 | Trace | TraceLogger |
| `relationships` | 138,441 | v0.2 | KnowledgeFabric |
| `semantic_relationships` | 144,543 | v0.2 | SemanticMemory |
| `state_deltas` | 6,546 | v0.3 | StateEvolutionEngine |
| `memory_records` | 980 | v0.1 | MemoryManager |
| `uncertainty_entries` | 1,300 | v0.3 | UncertaintyEngine |
| `predictions` | 600 | v0.4 | WorldModel |
| `semantic_concepts` | 397 | v0.2 | SemanticMemory |
| `goal_forecasts` | 500 | v0.4 | GoalForecastEngine |
| `concepts` | 201 | v0.2 | KnowledgeFabric |
| `session_states` | 100 | v0.1 | StorageBackend |
| `state_vectors` | 101 | v0.4 | StateTransitionGraph |
| `state_transitions` | 100 | v0.4 | WorldModel |
| `attention_focus` | 102 | v0.3 | AttentionManager |
| `goal_forecast_reports` | 100 | v0.4 | GoalForecastEngine |
| `counterfactual_scenarios` | 100 | v0.3 | CounterfactualReasoner |
| `counterfactual_results` | 100 | v0.3 | CounterfactualReasoner |
| `evolution_results` | 100 | v0.3 | StateEvolutionEngine |
| `entities` | 12 | v0.2 | KnowledgeFabric |
| `beliefs` | 8 | v0.2 | BeliefState |
| `goals` | 6 | v0.2 | GoalManager |
| `cognitive_states` | 1 | v0.2 | CognitiveStateEngine |

**Total rows**: 296,190

### Tables EMPTY (39 of 61)

| Table | Version | Classification |
|-------|---------|---------------|
| `agent_outputs` | v0.1 | DISCONNECTED — stored in memory, never persisted |
| `thread_states` | v0.1 | DISCONNECTED — stored in memory, never persisted |
| `verification_results` | v0.1 | DISCONNECTED — results kept in session objects |
| `reflection_results` | v0.1 | DISCONNECTED — results kept in session objects |
| `cognitive_nodes` | v0.3 | DISCONNECTED — cognitive_graph never populated |
| `cognitive_edges` | v0.3 | DISCONNECTED — cognitive_graph never populated |
| `plans` | v0.3 | SCHEMA ONLY — PlanState never produces data |
| `outcome_predictions` | v0.4 | DISCONNECTED — OutcomePredictor never called |
| `simulation_runs` | v0.4 | DISCONNECTED — SimulationEngine never called |
| `scenario_comparisons` | v0.4 | DISCONNECTED — SimulationEngine never called |
| `causal_links` | v0.4 | DISCONNECTED — CausalReasoner never produces links |
| `intervention_results` | v0.4 | DISCONNECTED — CausalReasoner never called |
| `causal_discoveries` | v0.4 | DISCONNECTED — CausalReasoner never called |
| `world_model_state` | v0.4 | DISCONNECTED — no state persisted |
| `source_references` | v0.2 | SCHEMA ONLY — never populated |
| `all_prediction_errors` | v0.5 | DISCONNECTED — ActiveLearningLoop core never called |
| `all_prediction_belief_map` | v0.5 | DISCONNECTED — ActiveLearningLoop core never called |
| `all_confidence_map` | v0.5 | DISCONNECTED — ActiveLearningLoop core never called |
| `attention_allocations` | v0.5 | DISCONNECTED — AttentionEconomy never called |
| `attention_budget_config` | v0.5 | DISCONNECTED — AttentionEconomy never called |
| `ecr_causal_chains` | v0.5 | DISCONNECTED — EnhancedCausalReasoner never called |
| `ecr_causal_forecasts` | v0.5 | DISCONNECTED — EnhancedCausalReasoner never called |
| `ecr_root_cause_analyses` | v0.5 | DISCONNECTED — EnhancedCausalReasoner never called |
| `goal_competition_entries` | v0.5 | DISCONNECTED — GoalCompetitionEngine never called |
| `goal_competition_results` | v0.5 | DISCONNECTED — GoalCompetitionEngine never called |
| `manifold_points` | v0.5 | DISCONNECTED — CognitiveStateManifold never called |
| `manifold_clusters` | v0.5 | DISCONNECTED — CognitiveStateManifold never called |
| `manifold_state` | v0.5 | DISCONNECTED — CognitiveStateManifold never called |
| `self_performance_records` | v0.5 | DISCONNECTED — SelfModel never called |
| `self_model_preferences` | v0.5 | DISCONNECTED — SelfModel never called |
| `wme_future_predictions` | v0.5 | DISCONNECTED — WorldModelEngine core never called |
| `wme_action_estimates` | v0.5 | DISCONNECTED — WorldModelEngine core never called |
| `wme_error_history` | v0.5 | DISCONNECTED — WorldModelEngine core never called |
| `wme_goal_risk_factors` | v0.5 | DISCONNECTED — WorldModelEngine core never called |
| `ef_metric_measurements` | v0.5 | DISCONNECTED — EvaluationFramework never called |
| `ef_evaluation_reports` | v0.5 | DISCONNECTED — EvaluationFramework never called |
| `cognitive_cycle_traces` | v0.5 | DISCONNECTED — CognitiveCycle never called |
| `phase_results` | v0.5 | DISCONNECTED — CognitiveCycle never called |
| `sqlite_sequence` | — | Internal SQLite table |

---

## 3. Runtime Traces Captured

| Phase | Traces | Success Rate | Avg Duration (ms) |
|-------|--------|-------------|-------------------|
| reasoning | 252 | 100% | 0.0 |
| observe | 100 | 100% | 0.0 |
| attention | 100 | 100% | 0.02 |
| memory | 100 | 100% | 0.57 |
| beliefs | 100 | **10%** | 0.43 |
| goals | 100 | 100% | 0.26 |
| knowledge | 100 | 100% | 0.68 |
| consolidation | 100 | 100% | 551.51 |
| reflection | 100 | 100% | 0.17 |
| verification | 100 | 100% | 0.12 |
| uncertainty | 100 | 100% | 49.83 |
| synthesis | 100 | 100% | 0.06 |
| dynamics | 100 | 100% | 22.43 |
| prediction | 100 | 100% | 3.42 |
| counterfactual | 100 | 100% | 0.35 |
| world_model | 100 | 100% | 0.29 |
| active_learning | 100 | 100% | 0.01 |

**Total traces**: 1,852 across 100 sessions  
**Overall success rate**: 95.14%  
**Overall avg duration**: 34.03 ms  

### Critical Finding: Beliefs Phase 90% Failure Rate

The `beliefs` phase has a 90% failure rate. This means `get_active_beliefs()` fails 9 out of 10 times. Only 8 belief records exist in the database — the belief system is nearly non-functional during the activation pipeline.

---

## 4. Components Actually Used During Runtime

### v0.1 — Core Infrastructure (ACTIVE)

| Component | Status | Evidence |
|-----------|--------|----------|
| CognitiveKernel | **ACTIVE** | 100 queries processed |
| StorageBackend | **ACTIVE** | All DB writes |
| MemoryManager | **ACTIVE** | 980 memory_records |
| ThreadScheduler | **ACTIVE** | 252 reasoning threads |
| ModelRouter | **ACTIVE** | Routes to z-ai-api + mock |
| ResearchAgent | **ACTIVE** | Called per ANALYSIS thread |
| PlanningAgent | **ACTIVE** | Called per PLANNING thread |
| MemoryAgent | **ACTIVE** | Called per MEMORY thread |
| VerificationAgent | **ACTIVE** | Called per VERIFICATION thread |
| ReflectionEngine | **ACTIVE** | 100 reflection traces |
| VerificationEngine | **ACTIVE** | 100 verification traces |

### v0.2 — Cognitive Layer (ACTIVE)

| Component | Status | Evidence |
|-----------|--------|----------|
| KnowledgeFabric | **ACTIVE** | 201 concepts, 138,441 relationships |
| BeliefState | **PARTIALLY ACTIVE** | 8 beliefs, 90% failure in pipeline |
| GoalManager | **ACTIVE** | 6 goals, 100 goal traces |
| CognitiveStateEngine | **ACTIVE** | 1 cognitive_state, session tracking |
| SemanticMemory | **ACTIVE** | 397 concepts, 144,543 relationships |
| KnowledgeConsolidator | **ACTIVE** | 100 consolidation traces (slowest: avg 551ms) |
| ReasoningEngine | **PARTIALLY ACTIVE** | Initialized but only called indirectly |

### v0.3 — Dynamics Layer (ACTIVE)

| Component | Status | Evidence |
|-----------|--------|----------|
| CognitiveDynamicsEngine | **ACTIVE** | 100 dynamics traces |
| AttentionManager | **ACTIVE** | 102 attention_focus entries |
| UncertaintyEngine | **ACTIVE** | 1,300 uncertainty entries |
| StateEvolutionEngine | **ACTIVE** | 6,546 state_deltas, 100 evolution results |
| CounterfactualReasoner | **ACTIVE** | 100 scenarios, 100 results |
| CognitiveGraph | **DISCONNECTED** | 0 nodes, 0 edges — tables exist but empty |
| PlanState | **SCHEMA ONLY** | 0 rows in plans table |

### v0.4 — Predictive Layer (PARTIALLY ACTIVE)

| Component | Status | Evidence |
|-----------|--------|----------|
| WorldModel | **ACTIVE** | 100 state_transitions, 600 predictions |
| StateTransitionGraph | **ACTIVE** | 101 state_vectors (via WorldModel) |
| GoalForecastEngine | **ACTIVE** | 500 forecasts, 100 reports |
| OutcomePredictor | **DISCONNECTED** | 0 rows — never called in pipeline |
| SimulationEngine | **DISCONNECTED** | 0 rows — never called in pipeline |
| CausalReasoner | **DISCONNECTED** | 0 rows — never produces data |

### v0.5 — Unified Architecture (DISCONNECTED)

| Component | Status | Evidence |
|-----------|--------|----------|
| WorldModelEngine | **DISCONNECTED** | 0 rows in all wme_* tables |
| ActiveLearningLoop | **DISCONNECTED** | Only `get_stats()` called in trace, not core methods |
| CognitiveStateManifold | **DISCONNECTED** | 0 rows in all manifold_* tables |
| GoalCompetitionEngine | **DISCONNECTED** | 0 rows in goal_competition_* tables |
| AttentionEconomy | **DISCONNECTED** | 0 rows in attention_allocations/budget_config |
| EnhancedCausalReasoner | **DISCONNECTED** | 0 rows in all ecr_* tables |
| SelfModel | **DISCONNECTED** | 0 rows in self_* tables |
| CognitiveCycle | **DISCONNECTED** | 0 rows in cognitive_cycle_traces/phase_results |
| EvaluationFramework | **DISCONNECTED** | 0 rows in ef_* tables |

### Validation Layer (SIMULATION)

| Component | Status | Evidence |
|-----------|--------|----------|
| ACOSSimulated | **SIMULATION** | Hand-tuned profiles, no real computation |
| BenchmarkSuite | **ACTIVE** (in validation only) | Produces benchmark scores |
| ABTestEngine | **ACTIVE** (in validation only) | Statistical comparisons |
| FailureAnalyzer | **ACTIVE** (in validation only) | Failure detection |
| EmergentBehaviorAnalyzer | **ACTIVE** (in validation only) | Emergence detection |
| ScientificReportGenerator | **ACTIVE** (in validation only) | Report generation |
| ACOSReal | **NEW** | Replaces simulated profiles with real runtime data |

---

## 5. Components Never Used

The following components exist in code but are **never invoked** during the `process_query_v2()` pipeline:

1. **CognitiveGraph** — `add_node()` and `add_edge()` are never called by the kernel pipeline. The graph is initialized but empty.
2. **PlanState** — Creates tables but no plan is ever created during runtime.
3. **OutcomePredictor** — Wraps the transition graph but `predict_outcome()` is never called.
4. **SimulationEngine** — `simulate()` is never called. The v0.4 prediction cycle only uses WorldModel directly.
5. **CausalReasoner** — `discover_causal_links()` is never called. Zero causal links exist.
6. **WorldModelEngine** — All 4 tables empty. `predict_future_state()`, `estimate_action_outcome()` never called.
7. **ActiveLearningLoop** — Only `get_stats()` is called as a trace, never `measure_prediction_error()` or `run_learning_cycle()`.
8. **CognitiveStateManifold** — Never called. No points, clusters, or state ever created.
9. **GoalCompetitionEngine** — Never called. No competition entries or results.
10. **AttentionEconomy** — Never called. No allocations or budget config.
11. **EnhancedCausalReasoner** — Never called. No chains, forecasts, or root cause analyses.
12. **SelfModel** — Never called. No performance records or model preferences.
13. **CognitiveCycle** — `run()` and `run_unified()` are never called. The kernel pipeline doesn't use it.
14. **EvaluationFramework** — Never called. No metric measurements or evaluation reports.
15. **ReasoningEngine** — Initialized but `reason()` is never called directly; agents bypass it.

---

## 6. Performance Bottlenecks

| Bottleneck | Phase | Avg Duration | % of Total |
|------------|-------|-------------|-----------|
| Knowledge Consolidation | consolidation | 551.51 ms | **86.2%** |
| Uncertainty Update | uncertainty | 49.83 ms | 7.8% |
| Cognitive Dynamics | dynamics | 22.43 ms | 3.5% |
| Prediction Cycle | prediction | 3.42 ms | 0.5% |
| All other phases | — | ~2.5 ms | 0.4% |

**Single Dominant Bottleneck**: Knowledge consolidation consumes 86.2% of total pipeline time. This is where `KnowledgeConsolidator.consolidate_session()` extracts concepts, relationships, and beliefs from session data. With 138,441 relationships and growing, this will only get slower.

**Belief System Failure**: 90% of belief loading attempts fail, making the belief system essentially non-functional. This suggests the BeliefState persistence or retrieval is broken.

---

## 7. Single Points of Failure

1. **Knowledge Consolidation** — If consolidation fails or times out, no new knowledge is extracted. It's the sole path from session data to the knowledge graph. Failure here means the system stops learning.

2. **ModelRouter** — If the z-ai-api backend goes down, the system falls back to MockBackend. During activation, only 1 real LLM call was made vs 1,308 mock calls. The system is overwhelmingly mock-driven.

3. **SQLite Database** — All persistence goes through a single SQLite file. No replication, no WAL mode optimization visible. Lock contention under concurrent access would be catastrophic.

4. **CognitiveKernel Singleton** — The kernel is a single object. No clustering, no horizontal scaling. One kernel crash = total system failure.

5. **BeliefState Persistence** — 90% failure rate in belief retrieval. If beliefs can't be loaded, the pipeline continues with empty belief context, making all belief-aware reasoning vacuous.

---

## 8. Cognitive Coverage

### What ACOS Actually Does Per Query

```
Observe (load cognitive state)
  → Memory (begin session tracking)
    → Attention (determine thread types)
      → Goals (check if query relates to goals)
        → Beliefs (load beliefs — 90% FAILURE)
          → Knowledge (extract concepts, spawn threads)
            → Reasoning (4 parallel agents)
              → Reflection (review outputs)
                → Verification (check outputs)
                  → Consolidation (extract knowledge — 86% of time)
                    → Uncertainty Update
                      → Synthesis (build final answer)
                        → Dynamics Cycle (attention, uncertainty, evolution)
                          → Prediction Cycle (world model, goal forecasts)
                            → Counterfactual (what-if analysis)
                              → World Model Stats
                                → Active Learning Stats (just get_stats())
```

### What ACOS Does NOT Do Per Query

- Does NOT project cognitive state onto the manifold
- Does NOT run goal competition
- Does NOT allocate attention budget
- Does NOT discover causal chains
- Does NOT forecast causal effects
- Does NOT analyze root causes
- Does NOT record self-model performance
- Does NOT run the cognitive cycle loop
- Does NOT evaluate its own metrics
- Does NOT measure prediction errors
- Does NOT update beliefs from errors
- Does NOT update confidence from errors
- Does NOT update world model from errors
- Does NOT simulate alternatives
- Does NOT run outcome prediction

---

## 9. Runtime Statistics

| Metric | Value |
|--------|-------|
| Total queries processed | 100 |
| Total pipeline phases executed | ~1,852 |
| Total database rows | 296,190 |
| Tables with data | 22 / 61 (36%) |
| Tables empty | 39 / 61 (64%) |
| Overall trace success rate | 95.14% |
| Average query time | 639ms |
| Slowest phase | consolidation (551ms avg) |
| Fastest phase | observe (0.0ms avg) |
| Reasoning threads per query | ~2.5 (252 / 100) |
| Belief failure rate | 90% |
| v0.5 subsystem tables populated | 0 / 23 |

---

## 10. Real LLM Usage Statistics

| Metric | Value |
|--------|-------|
| Real LLM calls (z-ai-api) | 1 |
| Mock LLM calls | 1,308 |
| Real LLM avg latency | 0.419s |
| Mock LLM avg latency | 0.000003s |
| Real LLM fraction | 0.076% |
| Mock LLM fraction | 99.924% |

**The system is 99.9% mock-driven.** Only 1 out of 1,309 LLM calls went to the real backend. This means:
- Agent outputs are canned mock responses
- Reflections are synthetic
- Verifications are synthetic
- The "cognitive reasoning" is entirely simulated at the LLM level

The Z-AI API backend was registered and available but the ModelRouter's routing logic overwhelmingly selects the mock backend for actual agent calls.

---

## 11. Classification Table for ALL Subsystems

| # | Subsystem | Version | Classification | Rationale |
|---|-----------|---------|---------------|-----------|
| 1 | CognitiveKernel | v0.1 | **ACTIVE** | Central orchestrator, all 100 queries pass through it |
| 2 | StorageBackend | v0.1 | **ACTIVE** | All DB reads/writes, 296K rows |
| 3 | MemoryManager | v0.1 | **ACTIVE** | 980 memory_records stored |
| 4 | ThreadScheduler | v0.1 | **ACTIVE** | Creates and manages 252 threads |
| 5 | ModelRouter | v0.1 | **ACTIVE** | Routes 1,309 calls (1 real + 1,308 mock) |
| 6 | ResearchAgent | v0.1 | **ACTIVE** | Executes ANALYSIS threads |
| 7 | PlanningAgent | v0.1 | **ACTIVE** | Executes PLANNING threads |
| 8 | MemoryAgent | v0.1 | **ACTIVE** | Executes MEMORY threads |
| 9 | VerificationAgent | v0.1 | **ACTIVE** | Executes VERIFICATION threads |
| 10 | ReflectionEngine | v0.1 | **ACTIVE** | 100 reflection traces, cross-contradiction detection |
| 11 | VerificationEngine | v0.1 | **ACTIVE** | 100 verification traces, cross-verification |
| 12 | KnowledgeFabric | v0.2 | **ACTIVE** | 201 concepts, 138K relationships |
| 13 | BeliefState | v0.2 | **PARTIALLY ACTIVE** | 8 beliefs, 90% failure rate in pipeline |
| 14 | GoalManager | v0.2 | **ACTIVE** | 6 goals, 100 goal traces |
| 15 | CognitiveStateEngine | v0.2 | **ACTIVE** | Session tracking, state management |
| 16 | SemanticMemory | v0.2 | **ACTIVE** | 397 concepts, 144K relationships |
| 17 | KnowledgeConsolidator | v0.2 | **ACTIVE** | Dominant bottleneck (551ms), extracts knowledge |
| 18 | ReasoningEngine | v0.2 | **PARTIALLY ACTIVE** | Initialized but never called directly in pipeline |
| 19 | CognitiveDynamicsEngine | v0.3 | **ACTIVE** | Orchestrates v0.3 cycle, 100 traces |
| 20 | AttentionManager | v0.3 | **ACTIVE** | 102 attention_focus entries |
| 21 | UncertaintyEngine | v0.3 | **ACTIVE** | 1,300 uncertainty entries |
| 22 | StateEvolutionEngine | v0.3 | **ACTIVE** | 6,546 state_deltas |
| 23 | CounterfactualReasoner | v0.3 | **ACTIVE** | 100 scenarios, 100 results |
| 24 | CognitiveGraph | v0.3 | **DISCONNECTED** | 0 nodes, 0 edges — initialized but never populated |
| 25 | PlanState | v0.3 | **SCHEMA ONLY** | Creates table, no plan records ever written |
| 26 | WorldModel | v0.4 | **ACTIVE** | 100 transitions, 600 predictions |
| 27 | StateTransitionGraph | v0.4 | **ACTIVE** | 101 state_vectors (via WorldModel) |
| 28 | GoalForecastEngine | v0.4 | **ACTIVE** | 500 forecasts, 100 reports |
| 29 | OutcomePredictor | v0.4 | **DISCONNECTED** | 0 outcome_predictions — never called |
| 30 | SimulationEngine | v0.4 | **DISCONNECTED** | 0 simulation_runs — never called |
| 31 | CausalReasoner | v0.4 | **DISCONNECTED** | 0 causal_links — never produces data |
| 32 | WorldModelEngine | v0.5 | **DISCONNECTED** | 0 rows in all 4 tables — core never called |
| 33 | ActiveLearningLoop | v0.5 | **DISCONNECTED** | Only `get_stats()` called, core logic unused |
| 34 | CognitiveStateManifold | v0.5 | **DISCONNECTED** | 0 rows in all 3 tables — never called |
| 35 | GoalCompetitionEngine | v0.5 | **DISCONNECTED** | 0 rows in 2 tables — never called |
| 36 | AttentionEconomy | v0.5 | **DISCONNECTED** | 0 rows in 2 tables — never called |
| 37 | EnhancedCausalReasoner | v0.5 | **DISCONNECTED** | 0 rows in 3 tables — never called |
| 38 | SelfModel | v0.5 | **DISCONNECTED** | 0 rows in 2 tables — never called |
| 39 | CognitiveCycle | v0.5 | **DISCONNECTED** | 0 rows in 2 tables — `run()` never called |
| 40 | EvaluationFramework | v0.5 | **DISCONNECTED** | 0 rows in 2 tables — never called |
| 41 | ACOSSimulated | Validation | **SIMULATION** | Hand-tuned profiles, no real computation |
| 42 | ACOSReal | Validation | **NEW** | Replaces simulated with real runtime data |
| 43 | TraceLogger | Trace | **ACTIVE** | 1,852 traces recorded |

---

## 12. Dead Code Inventory

### Dead During Runtime (exists in code, never executed during pipeline)

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| CognitiveGraph.add_node() | cognitive/dynamics/cognitive_graph.py | Dead in runtime | Called only in CognitiveCycle (itself dead) |
| CognitiveGraph.add_edge() | cognitive/dynamics/cognitive_graph.py | Dead in runtime | Same as above |
| CognitiveGraph.get_shortest_path() | cognitive/dynamics/cognitive_graph.py | Dead | Never called anywhere |
| PlanState.create_plan() | cognitive/dynamics/plan_state.py | Dead | Table exists, no plans created |
| PlanState.update_step() | cognitive/dynamics/plan_state.py | Dead | Never called |
| OutcomePredictor.predict_outcome() | cognitive/predictive/outcome_predictor.py | Dead | Never called in pipeline |
| OutcomePredictor.update_from_observation() | cognitive/predictive/outcome_predictor.py | Dead | Never called |
| SimulationEngine.simulate() | cognitive/predictive/simulation_engine.py | Dead | Never called |
| SimulationEngine.compare_scenarios() | cognitive/predictive/simulation_engine.py | Dead | Never called |
| CausalReasoner.discover_causal_links() | cognitive/predictive/causal_reasoner.py | Dead | Never called |
| CausalReasoner.suggest_intervention() | cognitive/predictive/causal_reasoner.py | Dead | Never called |
| WorldModelEngine.predict_future_state() | cognitive/unified/world_model_engine.py | Dead | Never called |
| WorldModelEngine.estimate_action_outcome() | cognitive/unified/world_model_engine.py | Dead | Never called |
| WorldModelEngine.learn_state_transitions() | cognitive/unified/world_model_engine.py | Dead | Never called |
| ActiveLearningLoop.measure_prediction_error() | cognitive/unified/active_learning.py | Dead | Never called |
| ActiveLearningLoop.run_learning_cycle() | cognitive/unified/active_learning.py | Dead | Never called |
| ActiveLearningLoop.update_beliefs_from_error() | cognitive/unified/active_learning.py | Dead | Never called |
| ActiveLearningLoop.update_confidence_from_error() | cognitive/unified/active_learning.py | Dead | Never called |
| ActiveLearningLoop.update_world_model_from_error() | cognitive/unified/active_learning.py | Dead | Never called |
| CognitiveStateManifold.project_belief() | cognitive/unified/cognitive_manifold.py | Dead | Never called |
| CognitiveStateManifold.project_goal() | cognitive/unified/cognitive_manifold.py | Dead | Never called |
| CognitiveStateManifold.find_clusters() | cognitive/unified/cognitive_manifold.py | Dead | Never called |
| CognitiveStateManifold.evolve() | cognitive/unified/cognitive_manifold.py | Dead | Never called |
| GoalCompetitionEngine.enter_competition() | cognitive/unified/goal_competition.py | Dead | Never called |
| GoalCompetitionEngine.run_competition() | cognitive/unified/goal_competition.py | Dead | Never called |
| AttentionEconomy.allocate() | cognitive/unified/attention_economy.py | Dead | Never called |
| AttentionEconomy.run_economy_cycle() | cognitive/unified/attention_economy.py | Dead | Never called |
| EnhancedCausalReasoner.discover_causal_chains() | cognitive/unified/enhanced_causal.py | Dead | Never called |
| EnhancedCausalReasoner.analyze_root_cause() | cognitive/unified/enhanced_causal.py | Dead | Never called |
| EnhancedCausalReasoner.forecast_from_cause() | cognitive/unified/enhanced_causal.py | Dead | Never called |
| SelfModel.record_performance() | cognitive/unified/self_model.py | Dead | Never called |
| SelfModel.assess_strengths() | cognitive/unified/self_model.py | Dead | Never called |
| CognitiveCycle.run() | cognitive/unified/cognitive_cycle.py | Dead | Never called |
| CognitiveCycle.run_unified() | cognitive/unified/cognitive_cycle.py | Dead | Never called |
| EvaluationFramework.measure_belief_accuracy() | cognitive/unified/evaluation.py | Dead | Never called |
| EvaluationFramework.run_full_evaluation() | cognitive/unified/evaluation.py | Dead | Never called |

### Placeholder Methods (return defaults or do nothing meaningful)

| Component | Method | Returns |
|-----------|--------|---------|
| ReasoningEngine | `reason()` | Never called — agents bypass it |
| BeliefState | `get_active_beliefs()` | Fails 90% of the time |
| ActiveLearningLoop | `get_stats()` | Returns zeros — no actual error records |

### Only Used in Tests

| Component | File | Test Coverage |
|-----------|------|-------------|
| All v0.5 unified modules | cognitive/unified/*.py | Tests exist, pass — but runtime never calls them |
| Validation modules | validation/*.py | ValidationLab tests pass — but use simulated data |
| CognitiveCycle.run() | cognitive/unified/cognitive_cycle.py | Test covers it, runtime ignores it |

### Decorative Components (appear functional but add no value)

| Component | Why Decorative |
|-----------|---------------|
| CognitiveCycle | 17-phase loop that duplicates what process_query_v2 already does. Never called from the kernel. |
| EvaluationFramework | Measures metrics that are never collected during runtime. |
| SelfModel | Records performance that is never observed. Strengths/weaknesses are always defaults. |
| AttentionEconomy | Allocates attention that no consumer uses. |
| GoalCompetitionEngine | Competes goals that are never entered into competition. |
| EnhancedCausalReasoner | Discovers chains from zero causal links. |
| WorldModelEngine | Predicts from a world model that already predicts. Redundant wrapper. |
| ActiveLearningLoop | Measures errors from predictions that are never verified. |

---

## 13. Final Answers

### "Which parts of ACOS are truly alive?"

The **truly alive** parts of ACOS are those that process real data, produce persistent state, and contribute to the output:

1. **The Core Pipeline** (v0.1): CognitiveKernel → ThreadScheduler → Agents → Reflection → Verification. This is the beating heart. It works, processes queries, and produces real output.

2. **Knowledge Infrastructure** (v0.2): KnowledgeFabric + SemanticMemory + KnowledgeConsolidator. These accumulate 282K+ relationships and 397 semantic concepts. They're the system's long-term memory. But consolidation is painfully slow (551ms).

3. **Dynamics Cycle** (v0.3): AttentionManager + UncertaintyEngine + StateEvolutionEngine + CounterfactualReasoner. These run every query and produce real data (1,300+ uncertainty entries, 6,546 state deltas, 100 counterfactual scenarios).

4. **Predictive Core** (v0.4): WorldModel + GoalForecastEngine. These make 600 predictions and 500 forecasts. The world model learns state transitions from observed queries.

5. **Trace Logger**: Records 1,852 traces with 95% success rate. The only v0.5-adjacent component that's actually active.

These components handle ~100% of the cognitive work. They represent roughly **40% of the total codebase by module count** but produce **100% of the runtime value**.

### "Which parts merely exist?"

The **merely existing** parts are numerous and expensive:

1. **All 9 v0.5 subsystems** are completely disconnected from the runtime pipeline. They are initialized (tables created, data loaded), but their core methods are never called. They exist as scaffolding for a future that hasn't been wired up. **0 out of 23 v0.5 database tables have data.**

2. **3 of 6 v0.3 subsystems** are dead: CognitiveGraph, PlanState, and (partially) the dynamics engine's internal coordination.

3. **3 of 6 v0.4 subsystems** are dead: OutcomePredictor, SimulationEngine, CausalReasoner. They exist in code, have tables, but produce zero rows.

4. **The BeliefState system** is effectively dead — 90% failure rate means it contributes nothing to the cognitive pipeline despite being architecturally central.

5. **The entire Validation Layer** uses simulated (ACOSSimulated) rather than real (ACOSReal) performance data. Tournament results, emergence scores, and cognitive metrics are all based on hand-tuned probabilistic profiles, not actual runtime behavior.

6. **99.9% of LLM calls** go to the MockBackend. The system's "reasoning," "reflection," and "verification" are all synthetic.

**In summary**: ACOS has the architecture of a cognitive system, but only about 40% of its modules are truly alive. The remaining 60% — particularly the entire v0.5 "Unified Cognitive Architecture" — exists as code and tests but contributes nothing to the runtime. The system processes queries, accumulates knowledge, and runs dynamics cycles, but it does not learn from errors, compete for goals, allocate attention budget, discover causal chains, model itself, run cognitive cycles, or evaluate its own performance. These are all decorative — they exist but are not alive.

The gap between what ACOS appears to be (a 40+ module cognitive architecture) and what it actually does (a ~15 module query pipeline with dynamics) is the most important finding of this activation.

---

## Appendix A: Phase 7 — ACOSReal Implementation

Created `ACOSReal` class in `acos/validation/baselines.py` that replaces the hand-tuned `ACOSSimulated` profiles with scores derived from the actual runtime database:

- Reads real trace statistics (phase success rates, durations)
- Reads real table row counts as evidence of cognitive activity  
- Computes domain-specific scores (memory, planning, reasoning, learning, prediction) from observed data
- Provides `process_query()` async method that runs queries through the real CognitiveKernel
- Falls back gracefully when the kernel is unavailable
- Exported from `acos/validation/__init__.py`

## Appendix B: Method Coverage Summary

| Subsystem | Total Methods | Called in Runtime | Never Called |
|-----------|--------------|------------------|-------------|
| CognitiveKernel | 8 | 8 | 0 |
| KnowledgeFabric | 10 | 4 | 6 |
| BeliefState | 8 | 2 | 6 |
| GoalManager | 7 | 3 | 4 |
| CognitiveDynamicsEngine | 4 | 2 | 2 |
| AttentionManager | 6 | 4 | 2 |
| UncertaintyEngine | 6 | 4 | 2 |
| StateEvolutionEngine | 3 | 2 | 1 |
| CounterfactualReasoner | 3 | 1 | 2 |
| WorldModel | 6 | 3 | 3 |
| GoalForecastEngine | 4 | 2 | 2 |
| WorldModelEngine | 8 | 1 (get_stats) | 7 |
| ActiveLearningLoop | 10 | 1 (get_stats) | 9 |
| CognitiveStateManifold | 10 | 0 | 10 |
| GoalCompetitionEngine | 6 | 0 | 6 |
| AttentionEconomy | 8 | 0 | 8 |
| EnhancedCausalReasoner | 6 | 0 | 6 |
| SelfModel | 8 | 0 | 8 |
| CognitiveCycle | 4 | 0 | 4 |
| EvaluationFramework | 10 | 0 | 10 |

**Estimated total methods**: ~150  
**Called during runtime**: ~40 (27%)  
**Never called during runtime**: ~110 (73%)
