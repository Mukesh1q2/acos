# Python Environment Configuration Report

**Date:** 2025-03-04
**Status:** Resolved
**Severity:** High — All Python-backed API endpoints were non-functional

---

## Problem

The Next.js API routes were calling `python3` which resolved to the system Python (`/usr/bin/python3`, Python 3.13.5). This system Python did **NOT** have the required packages installed (aiohttp, numpy, pydantic, etc.). The virtual environment Python at `/home/z/.venv/bin/python3` (Python 3.12.13) has all packages installed and is the correct interpreter to use.

This caused all three Python-backed API endpoints to fail with import errors, returning error responses to the frontend instead of actual data.

---

## Root Cause

Node.js `execSync('python3 ...')` does **not** inherit the shell's virtual environment activation. The `PATH` manipulation that venv activation provides (`source /home/z/.venv/bin/activate`) only affects the current shell session — child processes spawned by Node.js resolve `python3` via the system `PATH`, which points to `/usr/bin/python3`.

| Context | `python3` resolves to | Packages available |
|---|---|---|
| Shell (with venv activated) | `/home/z/.venv/bin/python3` (3.12.13) | All required packages |
| Node.js `execSync('python3')` | `/usr/bin/python3` (3.13.5) | None of the required packages |

**Missing packages in system Python 3.13.5:**
- aiohttp
- numpy
- pydantic
- uvicorn
- fastapi
- aiosqlite
- httpx
- networkx
- rich
- click

---

## Effects

### `/api/scientific-validation`
- **Error message:** `"Python dependencies are missing. Please install required packages (aiohttp, numpy)."`
- **Cause:** `ModuleNotFoundError` for aiohttp/numpy when system Python tried to import them
- **Impact:** Scientific validation dashboard showed empty/error state with no benchmark data

### `/api/validation`
- **Error message:** `"Failed to run Validation Lab"`
- **Cause:** `ModuleNotFoundError` for pydantic when system Python tried to import validation models
- **Impact:** Validation Lab page displayed fallback error UI with no tournament results or health scores

### `/api/acos-runtime`
- **Behavior:** Failed silently or timed out
- **Cause:** Missing dependencies (aiosqlite, etc.) caused the database read script to crash
- **Impact:** Runtime dashboard showed zero concepts, zero beliefs, zero goals

---

## Fix Applied

Changed all API routes to use the absolute path `/home/z/.venv/bin/python3` instead of the bare `python3` command. This ensures Node.js spawns the venv Python directly regardless of `PATH` state.

### Files Modified

#### 1. `src/app/api/validation/route.ts`
- Added `const PYTHON_BIN = "/home/z/.venv/bin/python3";` at the top
- Replaced all `python3` references in `execSync` calls with `${PYTHON_BIN}`
- Affects both GET and POST handlers

```typescript
// Before
const cmd = `python3 "${VALIDATION_SCRIPT}" ${quick ? "--quick" : ""} --seed ${seed}`;

// After
const PYTHON_BIN = "/home/z/.venv/bin/python3";
const cmd = `${PYTHON_BIN} "${VALIDATION_SCRIPT}" ${quick ? "--quick" : ""} --seed ${seed}`;
```

#### 2. `src/app/api/scientific-validation/route.ts`
- Added `const PYTHON_BIN = "/home/z/.venv/bin/python3";` at the top
- Replaced all `python3` references in `execSync` calls with `${PYTHON_BIN}`
- Affects both GET and POST handlers

```typescript
// Before
const result = execSync(`python3 "${SCRIPT}" ${flag}`, { ... });

// After
const PYTHON_BIN = "/home/z/.venv/bin/python3";
const result = execSync(`${PYTHON_BIN} "${SCRIPT}" ${flag}`, { ... });
```

#### 3. `src/app/api/acos-runtime/route.ts`
- Added `const PYTHON_BIN = "/home/z/.venv/bin/python3";` at the top
- Replaced `python3` reference in `execSync` call with `${PYTHON_BIN}`

```typescript
// Before
const result = execSync(`python3 "${READ_DB_SCRIPT}"`, { ... });

// After
const PYTHON_BIN = "/home/z/.venv/bin/python3";
const result = execSync(`${PYTHON_BIN} "${READ_DB_SCRIPT}"`, { ... });
```

#### 4. `mini-services/acos-runtime/index.ts`
- Changed uvicorn spawn from bare `"uvicorn"` to absolute path `"/home/z/.venv/bin/uvicorn"`

```typescript
// Before
const uvicorn = spawn("uvicorn", [ ... ]);

// After
const uvicorn = spawn("/home/z/.venv/bin/uvicorn", [ ... ]);
```

---

## Verification Results

After applying the fix, all three endpoints return valid data:

### `/api/scientific-validation?mode=results`
- **Status:** Working
- **Response:** Returns benchmark results with `Error: None` and `benchmark_results` array populated
- **No import errors**

### `/api/validation?quick=true`
- **Status:** Working
- **Response:** Returns full validation report
  - Tournament winner: ACOS Runtime
  - Health score: 0.9167
  - Complete rankings and emergence data

### `/api/acos-runtime`
- **Status:** Working
- **Response:** Returns runtime data
  - 243 concepts
  - 9 beliefs
  - 6 goals
  - Full cognitive state and statistics

---

## Installed Packages (Venv Python 3.12.13)

The `/home/z/.venv/bin/python3` environment includes all required dependencies:

| Package | Version | Used By |
|---|---|---|
| aiohttp | 3.13.3 | Scientific validation (HTTP client) |
| numpy | 2.1.3 | Scientific validation (numerical computation) |
| pydantic | — | Validation Lab (data models) |
| fastapi | — | ACOS Runtime API server |
| uvicorn | — | ACOS Runtime API server |
| aiosqlite | — | Database access (async SQLite) |
| httpx | — | HTTP client |
| networkx | — | Knowledge graph operations |
| rich | — | CLI output formatting |
| click | — | CLI argument parsing |

---

## Recommendations

### 1. Centralize the Python binary path in a shared config module
**Priority:** Medium

Currently, `PYTHON_BIN` is defined independently in each route file. This creates maintenance risk if the venv path changes (e.g., moving the project, using a different username, or switching to conda).

**Proposed solution:**
```typescript
// src/lib/python-config.ts
export const PYTHON_BIN = process.env.PYTHON_BIN || "/home/z/.venv/bin/python3";
export const UVICORN_BIN = process.env.UVICORN_BIN || "/home/z/.venv/bin/uvicorn";
```

Then import from this single source in all route files. This also enables overriding via environment variables for different deployment targets.

### 2. Add a Python environment health check endpoint
**Priority:** Medium

Add a lightweight endpoint (e.g., `/api/health/python`) that:
- Verifies the Python binary exists and is executable
- Checks that key packages are importable
- Returns the Python version and venv path
- Can be called by monitoring/alerting systems

**Proposed implementation:**
```typescript
// src/app/api/health/python/route.ts
execSync(`${PYTHON_BIN} -c "import aiohttp, numpy, pydantic; print('OK')"`, { timeout: 5000 });
```

### 3. Document the venv dependency in project setup instructions
**Priority:** High

Add to README or setup guide:
- The Python virtual environment must be created at `/home/z/.venv/`
- Required packages must be installed via `pip install -r requirements.txt`
- The `PYTHON_BIN` path must be updated if using a different venv location
- Environment variable `PYTHON_BIN` can override the default path

### 4. Consider using `python3 -m uvicorn` instead of direct uvicorn binary
**Priority:** Low

In `mini-services/acos-runtime/index.ts`, using `${PYTHON_BIN} -m uvicorn` instead of the direct uvicorn binary path would be more consistent with the approach used in the other route files, and would automatically resolve to the correct uvicorn for the Python environment.

---

## Summary

| Item | Before Fix | After Fix |
|---|---|---|
| Python interpreter | `/usr/bin/python3` (3.13.5, no packages) | `/home/z/.venv/bin/python3` (3.12.13, all packages) |
| `/api/scientific-validation` | "Python dependencies missing" error | Returns benchmark data |
| `/api/validation` | "Failed to run Validation Lab" | Returns full validation report |
| `/api/acos-runtime` | Silent failure / timeout | Returns 243 concepts, 9 beliefs, 6 goals |
| `mini-services/acos-runtime` | uvicorn not found in PATH | Starts FastAPI server correctly |

The root issue was a classic environment isolation problem: Node.js child processes do not inherit shell-level virtual environment activation. The fix of using absolute paths to the venv Python binary is the standard and recommended approach for this scenario.
