# Scientific Validation Audit

**Date:** 2026-03-04  
**Auditor:** Automated audit against live database and source code  
**Scope:** `acos-runtime/scientific_validation.py`, `data/scientific_validation.db`

---

## 1. What Is Being Measured?

Accuracy on **120 benchmark questions** across 6 categories (20 questions each):

| Category | Description | Example Question | Ground Truth |
|----------|-------------|------------------|--------------|
| **MMLU** | Multiple choice knowledge | "What is the chemical symbol for gold?" | `Au` |
| **GSM8K** | Multi-step math | "A store sells apples for $2 each and oranges for $3 each. If Sarah buys 4 apples and 3 oranges, how much does she spend?" | `$17` |
| **HotpotQA** | Multi-hop reasoning | "The element whose symbol is Fe was named after which planet in Roman mythology?" | `Mars` |
| **ARC** | Science reasoning | "Which of the following is an example of a chemical change? (A) melting ice (B) burning wood (C) dissolving sugar (D) cutting paper" | `B` |
| **Logic** | Logical deduction | "If all cats are animals, and all animals need water, do all cats need water?" | `yes` |
| **Commonsense** | Common sense reasoning | "If you put a metal spoon in a hot pot of soup, what will happen to the handle?" | `it will get hot` |

> **CRITICAL NOTE:** These questions are **hard-coded** in `scientific_validation.py` (lines 476–644, class `BenchmarkSuite`), NOT sourced from official MMLU/GSM8K/ARC datasets. They are **synthetic approximations** created by the developer. The category labels borrow the names of well-known benchmarks but the actual questions are original and have not been validated against any standardized test corpus.

---

## 2. Against Which Baseline?

Six baseline systems, each making **real LLM API calls** via `aiohttp` to the Z-AI API at `http://localhost:3000/api/chat`:

| # | System | Implementation | Description |
|---|--------|---------------|-------------|
| 1 | **Direct LLM** | `DirectLLM` class | Query sent directly to LLM with concise-answer prompt, no context |
| 2 | **LLM + RAG** | `LLMPlusRAG` class | LLM with simple word-overlap memory retrieval (in-memory list) |
| 3 | **ReAct Agent** | `ReActAgent` class | 3-iteration thought-action-observation loop |
| 4 | **LangGraph-style** | `LangGraphStyle` class | Multi-step pipeline with planning phase |
| 5 | **Minimal Multi-Agent** | `MinimalMultiAgent` class | 3 specialized agents with voting |
| 6 | **CrewAI-style** | `CrewAIStyle` class | Role-based agent collaboration |

Plus the system under test:

| # | System | Implementation | Description |
|---|--------|---------------|-------------|
| 7 | **ACOS Runtime** | `ACOSClient` class | Calls the ACOS CognitiveKernel at `http://localhost:3031/query/v2` |

All baselines share the same `LLMClient` and thus the same underlying LLM. The only variable is the orchestration pattern. ACOS uses its own API and internal cognitive pipeline.

---

## 3. Is the Score Real?

**YES — scores come from actual LLM API calls.** The data is not fabricated or simulated.

### Evidence of authenticity:

| Signal | Finding |
|--------|---------|
| **Latency values** | Realistic and varied — Direct LLM averages ~753ms, ACOS ranges from 1.9s to 96.8s |
| **Answer text** | Shows real LLM outputs with natural language variation, not templated responses |
| **Errors recorded** | HTTP 500 errors, connection resets, and timeouts are recorded honestly (15 `Direct_LLM` runs failed with 500s) |
| **ACOS boilerplate** | 7 of 10 ACOS answers contain generic "Research Analysis:" or "Strategic Plan:" boilerplate — a real failure mode, not hidden |
| **Timestamps** | Present in DB with `created_at` defaulting to `datetime('now')` |

### Database Verification (live query, 205 total rows):

```
Table                  | Row Count
-----------------------|----------
benchmark_questions    | 2,160    (accumulated across 18 runs × 120 questions)
validation_runs        | 205
ablation_results       | 0        ← EMPTY
statistical_tests      | 0        ← EMPTY
system_metrics         | 0        ← EMPTY
```

---

## 4. Current Results

### Accuracy and Latency by System

| Rank | System | Accuracy | Correct / Total | Avg Latency | Completed Runs |
|------|--------|----------|-----------------|-------------|----------------|
| 1 | Direct LLM | **63.3%** | 19 / 30 | 753ms | 30 |
| 2 | LLM + RAG | **60.0%** | 18 / 30 | 412ms | 30 |
| 3 | LangGraph-style | **40.0%** | 12 / 30 | 2,833ms | 30 |
| 4 | ACOS Runtime | **30.0%** | 3 / 10 | 33,707ms | 10 |
| 5 | Minimal Multi-Agent | **23.3%** | 7 / 30 | 1,107ms | 30 |
| 5 | ReAct Agent | **23.3%** | 7 / 30 | 547ms | 30 |
| 7 | CrewAI-style | **16.7%** | 5 / 30 | 1,748ms | 30 |

Additionally, 15 `Direct_LLM` (underscore variant) runs recorded **0% accuracy** due to HTTP 500 errors — these appear to be from an earlier run with a different system name format.

---

## 5. Issues with the Comparison

### 5.1 Sample Size Imbalance

ACOS Runtime has only **10 completed runs** compared to 30 for every other system. Many ACOS queries timed out at the 120-second limit. This makes the ACOS accuracy estimate unreliable — a single correct/incorrect answer swings the rate by 10 percentage points.

### 5.2 Extreme Latency Disparity

ACOS is **45x slower** than Direct LLM (33.7s vs 0.75s). The ACOS cognitive pipeline invokes multiple internal subsystems (belief system, goal system, memory, reflection, verification, planning agents) for each query. This latency includes:

- CognitiveKernel orchestration overhead
- Multiple internal LLM calls within ACOS
- Network round-trips between subsystems

### 5.3 Answer Matching Bias Against Verbose Outputs

ACOS produces **verbose synthesis responses** that frequently fail to match simple ground truths:

| Question | Ground Truth | ACOS Answer (truncated) | Match? |
|----------|-------------|------------------------|--------|
| "Chemical symbol for gold?" | `Au` | `"The chemical symbol for gold is Au, which comes from its Latin name 'aurum'... In synthesizing this answer, I note..."` | **NO** |
| "Gas plants absorb?" | `carbon dioxide` | `"Strategic Plan: Phase 1: Requirements gathering..."` (boilerplate) | **NO** |
| "Positively charged particle?" | `proton` | `"# Synthesis: Positively Charged Particles... the **proton** is the particle..."` | **YES** |

The `answers_match()` function (lines 371–432) has 5 matching strategies — exact match, letter choice, numeric, containment, keyword overlap — but containment match requires the ground truth string to appear in the normalized prediction. When ACOS wraps the answer in markdown headers and synthesis commentary, the containment check may still work (e.g., "au" appears in the gold answer), but only if normalization strips enough. In practice, the "Au" vs. "aurum" case causes a false negative because `normalize_answer` lowercases and strips articles, leaving "au" contained in "aurum" — but only the containment check at line 406 catches this, and only if `len(gt_norm) > 2` is false for "au" (it is, so containment is skipped). **This is a bug.**

### 5.4 ACOS Boilerplate Failure Mode

**7 out of 10 ACOS Runtime answers** contain generic boilerplate:

- **"Research Analysis: Based on the query, I've identified three key areas for investigation: 1. Historical context and precedent patterns 2. Current stat..."** — appears for math, science, and commonsense questions
- **"Strategic Plan: Phase 1: Requirements gathering and constraint analysis Phase 2: Architecture design..."** — appears for simple factual questions

This indicates the ACOS CognitiveKernel's planning/research agents are generating generic framework responses instead of engaging with the actual question content. Only 3 of 10 ACOS answers showed genuine engagement with the query. This is a **real architectural failure**, not a measurement artifact.

### 5.5 Missing Analytical Components

Three critical database tables are **completely empty**:

| Table | Rows | Purpose |
|-------|------|---------|
| `ablation_results` | **0** | Disabling individual ACOS subsystems to measure their contribution |
| `statistical_tests` | **0** | Cohen's d, p-values, confidence intervals for pairwise comparisons |
| `system_metrics` | **0** | Aggregated per-system metrics (hallucination rate, memory utilization, etc.) |

The code infrastructure for these exists (dataclasses `AblationResult`, `StatisticalTest`, `SystemMetrics` are defined; the `--ablation` and `--report` CLI flags are documented) but the actual computation has **never been run**. The `--ablation` flag would require ACOS to support disabling individual subsystems, which appears unimplemented.

### 5.6 No Per-Category Breakdown

The database does not store category information in the `validation_runs` table. The `question_id` field contains UUIDs (e.g., `09538f9a`) with no category prefix, making per-category analysis impossible without joining back to `benchmark_questions`. No per-category results have been computed or stored.

### 5.7 Questions Are Synthetic

The 120 questions are hand-crafted approximations of benchmark categories, not drawn from official MMLU, GSM8K, HotpotQA, or ARC datasets. This means:

- Results cannot be compared against published benchmarks
- Difficulty distribution may not match the real datasets
- Some ground truth answers are ambiguous (e.g., "The river that flows through Paris is a tributary of which larger river?" → ground truth is "Seine", but the Seine is not a tributary of a larger river in the typical sense — it flows into the English Channel)
- Question quality varies; some MMLU questions are trivially easy ("What is the capital of Japan?")

### 5.8 Small Effective Sample Size

With only 30 questions per system (5 per category in `--quick` mode), the statistical power of any comparison is very low. The 95% confidence interval for Direct LLM's 63.3% accuracy on 30 questions is approximately ±17.4 percentage points (Wilson interval), meaning the true accuracy could be anywhere from ~46% to ~78%.

---

## 6. Answer Matching Algorithm Review

The `answers_match()` function (lines 371–432) applies 5 strategies in sequence:

1. **Exact match** after normalization (lowercase, strip prefixes, remove articles, strip punctuation)
2. **Letter choice match** for A/B/C/D selections via regex
3. **Numeric match** for GSM8K/MMLU/ARC categories
4. **Containment match** — ground truth contained in prediction or vice versa (only if `len > 2`)
5. **Keyword overlap** — ≥80% of ground-truth keywords present in prediction

### Known issues:

- **Containment threshold bug**: Single-character and two-character ground truths (like "Au") skip containment matching due to `len(gt_norm) > 2` check, even when the answer is clearly present
- **No semantic matching**: "it will get hot" vs "the handle will become hot to the touch" requires semantic understanding beyond keyword overlap
- **Over-generous keyword overlap**: The 80% threshold with simple word splitting can produce false positives on verbose ACOS outputs that happen to contain ground-truth words in unrelated contexts
- **No fuzzy numeric matching**: "$86.40" vs "$86.4" or "2.4 hours" vs "2 hours 24 minutes" are not handled

---

## 7. What's Missing

| Missing Component | Impact | Effort to Add |
|-------------------|--------|---------------|
| Ablation studies | Cannot determine which ACOS subsystems help vs. hurt | High — requires ACOS to support subsystem disabling |
| Statistical significance tests | Cannot determine if accuracy differences are real or noise | Medium — data exists, just needs computation |
| Per-category breakdown | Cannot identify where ACOS excels vs. fails | Low — requires DB join + computation |
| System-level aggregated metrics | No hallucination rate, memory utilization, or verification usefulness data | Low — dataclass exists, needs population |
| Latency-constrained comparison | ACOS gets 45x more time per question | Medium — requires re-running with equal time budgets |
| Better answer extraction for ACOS | Verbose ACOS outputs unfairly penalized | Medium — regex/LLM-based extraction |
| Official benchmark questions | Results not comparable to published work | Medium — integrate real MMLU/GSM8K datasets |
| Larger sample size (full mode) | Quick mode (30 Q) has very low statistical power | Low — just run `--full` (120 Q) |
| Confidence intervals on all metrics | No uncertainty quantification | Low — standard statistical computation |

---

## 8. Conclusion

### The scores are REAL but the comparison is UNFAIR to ACOS — and ACOS has real architectural problems.

**The good:**
- No simulated or fabricated data — every score comes from a live LLM API call
- Errors and failures are recorded honestly
- The baseline implementations are genuine (they really do call the LLM with different prompting strategies)
- The measurement infrastructure is well-designed (async, retry logic, proper timing)

**The bad:**
- ACOS Runtime returns **generic boilerplate for 70% of queries** — this is a real architectural failure, not a measurement artifact
- ACOS is **45x slower** than Direct LLM with **half the accuracy**
- Answer matching has bugs that penalize verbose outputs (2-char ground truths skip containment)
- 3 of 5 analytical tables are empty — no statistical rigor applied
- Questions are synthetic, not from standardized benchmarks
- Sample size (30 per system) is too small for reliable conclusions

**The ugly:**
- ACOS's CognitiveKernel appears to route simple questions through a planning/research pipeline that produces generic framework responses instead of answers. Questions about math, science, and commonsense all receive the same "Research Analysis: Based on the query, I've identified three key areas for investigation..." boilerplate. This suggests a fundamental issue with how the ACOS query pipeline processes incoming questions.

### Recommendations for a Fair Comparison

1. **Fix answer extraction**: Add a post-processing step that extracts the direct answer from ACOS's verbose synthesis output (regex or secondary LLM call)
2. **Complete all 30 ACOS runs**: Increase timeout or optimize ACOS to reduce the 120s timeout rate
3. **Equalize time budgets**: Compare all systems at the same latency ceiling (e.g., 5s, 30s, 120s)
4. **Run statistical tests**: Compute Cohen's d, p-values, and confidence intervals from existing data
5. **Run ablation studies**: Disable ACOS subsystems one at a time to identify which help vs. hurt
6. **Fix the containment bug**: Lower the `len(gt_norm) > 2` threshold to `len(gt_norm) >= 2`
7. **Use official benchmark questions**: Replace synthetic questions with actual MMLU/GSM8K/ARC items
8. **Run in full mode**: Use all 120 questions per system instead of quick mode's 30

---

## Appendix A: ACOS Runtime Answer Samples

### Successful ACOS answers (3/10):

**Q:** "What particle has a positive charge in an atom?"  
**GT:** `proton`  
**ACOS:** `"# Synthesis: Positively Charged Particles in an Atom\n\n## Direct Answer\n\nIn an atom, the **proton** is the particle that carries a positive electric ch..."`  
**Result:** MATCH (keyword overlap caught "proton")

**Q:** "What is the speed of light in vacuum approximately?"  
**GT:** `A`  
**ACOS:** `"Research Analysis:\nBased on the query, I've identified three key areas for investigation:\n1. Historical context and precedent patterns\n2. Current stat..."`  
**Result:** MATCH (somehow passed despite boilerplate — likely letter extraction from the underlying data)

### Failed ACOS answers (7/10):

**Q:** "What is the chemical symbol for gold?"  
**GT:** `Au`  
**ACOS:** `"The chemical symbol for gold is Au, which comes from its Latin name 'aurum'... In synthesizing this answer, I note that while the reasoning threads pro..."`  
**Result:** NO MATCH — "au" is 2 chars, containment check skipped due to `len > 2` threshold

**Q:** "A store sells apples for $2 each..."  
**GT:** `$17`  
**ACOS:** `"Research Analysis:\nBased on the query, I've identified three key areas for investigation:\n1. Historical context and precedent patterns\n2. Current stat..."`  
**Result:** NO MATCH — pure boilerplate, no answer

## Appendix B: Database Schema

```sql
-- validation_runs (205 rows)
CREATE TABLE validation_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    system_name TEXT NOT NULL,
    question_id TEXT NOT NULL,
    question_text TEXT NOT NULL,
    ground_truth TEXT NOT NULL,
    model_used TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    token_estimate INTEGER NOT NULL,
    memory_retrievals INTEGER NOT NULL DEFAULT 0,
    belief_activations INTEGER NOT NULL DEFAULT 0,
    goal_activations INTEGER NOT NULL DEFAULT 0,
    reflection_output TEXT DEFAULT '',
    verification_output TEXT DEFAULT '',
    final_answer TEXT NOT NULL,
    success INTEGER NOT NULL,
    error TEXT,
    created_at TEXT DEFAULT datetime('now')
);

-- ablation_results (0 rows)
-- statistical_tests (0 rows)  
-- system_metrics (0 rows)
-- benchmark_questions (2,160 rows — accumulated across runs)
```
