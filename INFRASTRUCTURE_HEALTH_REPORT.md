# Infrastructure Health Report

## Overall Status: OPERATIONAL (with known limitations)

## Page-by-Page Verification

### 1. Overview Page ✅ WORKING
- URL: http://localhost:3000/ or http://localhost:3000/#overview
- Renders correctly with ACOS branding, architecture visualization, key metrics
- No console errors

### 2. Runtime Dashboard ✅ WORKING
- URL: http://localhost:3000/#runtime
- Shows live cognitive state data from ACOS SQLite database
- Displays: 50% Confidence, 267 sessions, 6 active beliefs, 3 weakened beliefs, 20% goal progress
- Data loads from /api/acos-runtime (now using /home/z/.venv/bin/python3)
- No errors

### 3. Validation Lab ✅ WORKING
- URL: http://localhost:3000/#validation
- Shows tournament winner: ACOS Runtime (score 1.00)
- Emergence Score: 0.171 (1 emergent capability: reasoning)
- Health Score: 0.92 (1 failure detected)
- Cognitive Score: 0.38 (3 strengths, 5 weaknesses)
- Data loads from /api/validation (now using /home/z/.venv/bin/python3)
- No errors

### 4. Scientific Validation ✅ WORKING (with limitations)
- URL: http://localhost:3000/#scientific-validation
- Shows benchmark data after clicking "Refresh"
- Currently displays 7 systems across 6 categories
- LIMITATION: Category names show as "unknown" because question IDs in DB don't match BenchmarkSuite IDs
- LIMITATION: ACOS Avg shows 0.0% because the "unknown" category doesn't match the frontend's expected categories
- Data loads from /api/scientific-validation (now using /home/z/.venv/bin/python3)
- The scores are REAL from actual LLM API calls, not simulated

### 5. AFM Research Panel ✅ WORKING (new)
- URL: http://localhost:3000/#afm-research
- Shows AFM-Lite v0.1 experiment findings
- Displays: 6 findings, architecture details, classification summary, v0.2 status, honest assessment
- Data loads from /api/afm (static data, no Python dependency)
- Warning banner: "Experiment artifacts from v0.1 are no longer available on disk"
- No errors

### 6. Other Sections ✅ WORKING
- Part 1-11, Roadmap, Theorems, Performance, Glossary all load correctly
- No errors observed

## API Endpoints Health

| Endpoint | Status | Python Dependency | Response Time |
|----------|--------|-------------------|---------------|
| /api/acos-data | ✅ | None (static) | ~100ms |
| /api/acos-runtime | ✅ | read_db.py | ~180ms |
| /api/validation | ✅ | run_validation.py | ~1400ms |
| /api/scientific-validation | ✅ | scientific_validation.py | ~280ms (results mode) |
| /api/afm | ✅ | None (static) | ~10ms |
| /api/chat | ✅ | None (z-ai-web-dev-sdk) | varies |

## Python Environment

- System Python: /usr/bin/python3 (3.13.5) — MISSING aiohttp, numpy, pydantic, uvicorn
- Venv Python: /home/z/.venv/bin/python3 (3.12.13) — ALL packages installed
- Fix applied: All API routes now use /home/z/.venv/bin/python3 explicitly
- Mini-service (acos-runtime) now uses /home/z/.venv/bin/uvicorn

## Known Issues

1. **Scientific Validation category mapping**: Question IDs in DB don't match BenchmarkSuite IDs, causing all categories to show as "unknown". This means the heatmap displays 0.0% for all expected categories.

2. **ACOS Runtime latency**: ACOS Runtime takes 30-90 seconds per question in scientific validation benchmarks, causing timeouts. Only 10 of 30 intended runs completed.

3. **Answer matching strictness**: ACOS's verbose responses don't match well against simple ground truths (e.g., "The chemical symbol for gold is Au..." fails to match "Au").

4. **No ablation or statistical test data**: The scientific_validation.db has 0 rows in ablation_results, system_metrics, and statistical_tests tables.

## Console Errors

None detected during testing.

## Recommendations

1. Fix the category mapping in scientific_validation.py to store categories alongside question IDs
2. Run a fresh Quick Benchmark to populate the DB with properly categorized results
3. Increase ACOS Runtime timeout to allow all 30 runs to complete
4. Improve answer extraction for ACOS's verbose outputs
