# AFM Integration Audit

**Date:** 2026-03-04  
**Auditor:** Automated Integration Analysis  
**Classification: PARTIALLY CONNECTED (Display-Only)**

---

## Executive Summary

AFM (Attention Flow Manifold) exists as a first-class visual section in the frontend with rich interactive content, but has **ZERO computational backend**. There are no AFM-specific API routes, no neural network code, no training pipeline, and no data sources. The gap between what is displayed to users and what actually exists operationally is **100%**.

---

## 1. Frontend Status: PARTIALLY CONNECTED

The Part 3 section ("AFM Architecture") is fully rendered with the following interactive components:

- **Component Evaluation Table** — HBTA, OTM, NSK/Panini comparisons
- **Architecture Comparison** — Transformer vs RWKV vs Mamba vs AHC v2
- **Radar Chart Visualization** — multi-axis component scoring
- **Mamba-OTM Visualization** — animated layer stack rendering
- **Accordion** — detailed component decision breakdowns
- **Hybrid Verdict Card** — summary recommendation display

### Component Footprint

- **13+ frontend components** reference AFM
- Primary component: `src/components/acos/part3-afm.tsx`
- Supporting references in: architecture diagrams, radar charts, accordion sections, and verdict cards
- **ALL data is hardcoded in the component — no dynamic data feeds**

### Verdict

The frontend presents AFM as a fully realized architectural concept. Users can interact with comparisons, visualizations, and evaluations. None of this data comes from a live backend — it is entirely static/hardcoded.

---

## 2. API Status: DISCONNECTED

| Check | Result |
|-------|--------|
| `/api/afm` endpoint | **DOES NOT EXIST** |
| AFM data in `/api/acos-data` | Single probability value (17) only |
| Chat system prompt | Mentions AFM for LLM awareness only |
| AFM-specific query handling | None |

### Details

- No `/api/afm` route exists anywhere in the codebase
- The only API-level reference to AFM is a single probability value (`17`) embedded in the `/api/acos-data` endpoint
- The chat system's LLM prompt mentions AFM by name so the AI can discuss it conversationally, but this is awareness-only — no AFM computation is triggered by chat queries

### Verdict

AFM has zero API surface. The single probability value in acos-data is decorative, not functional.

---

## 3. Data Status: DISCONNECTED

| Check | Result |
|-------|--------|
| `/home/z/my-project/afm-lite/` directory | **DOES NOT EXIST** |
| AFM result files (JSON/MD) | **NONE FOUND** |
| AFM databases or tables | **NONE FOUND** |
| AFM model weights | **NONE FOUND** |
| Previous experiment artifacts | **ALL MISSING** |

### Details

- The `afm-lite/` directory from the previous session's experiment program does not exist
- No AFM-related JSON or Markdown result files are present anywhere in the project
- No SQLite tables, columns, or records related to AFM exist in any database file
- No model weight files (`.pt`, `.bin`, `.safetensors`, etc.) exist for AFM
- The previous session's AFM-Lite v0.1 experiment code and results are **completely gone**

### Verdict

There is no AFM data of any kind in the project. The data layer is a complete void.

---

## 4. ACOS Runtime Status: DISCONNECTED

Only **2 tangential references** exist in the entire ACOS runtime codebase:

| File | Line | Reference |
|------|------|-----------|
| `acos/models/router.py` | 103 | Mock response string mentioning "ACOS/AFM architecture" |
| `acos/cognitive/unified/cognitive_cycle.py` | 69 | Docstring example mentioning AFM |

### What Does NOT Exist

- No AFM modules (`acos/afm/` does not exist)
- No AFM classes or data structures
- No AFM functions or methods
- No AFM imports or dependencies
- No AFM configuration or initialization code
- No AFM tests

### Verdict

AFM is mentioned in two places as a label/string, never as operational code. The runtime has zero AFM capability.

---

## 5. Mini Services Status: DISCONNECTED

| Check | Result |
|-------|--------|
| AFM-specific mini service | **DOES NOT EXIST** |
| AFM code in acos-runtime mini-service | **NONE** |
| AFM WebSocket handlers | **NONE** |
| AFM background workers | **NONE** |

### Details

- No AFM mini-service exists under `mini-services/`
- The `acos-runtime` mini-service (`mini-services/acos-runtime/`) contains zero AFM-related code
- No WebSocket handlers process AFM events
- No background workers compute AFM metrics

### Verdict

The mini-services layer has no AFM presence whatsoever.

---

## 6. Previous Experiment Data (AFM-Lite v0.1)

The AFM-Lite Experimental Program v0.1 ran in a previous session and produced significant scientific results. **All code and result files from this experiment are now MISSING.**

### Key Experimental Findings (Lost)

| Finding | Detail |
|---------|--------|
| Stiefel prevents KL collapse | Baseline β=1e-2 → 11.35% retention; AFM → 98.40% retention |
| AFM+L_RIB reduces forgetting | 24.82% → 5.04% (80% reduction) |
| Statistical significance | AFM+L_RIB vs baseline: p=0.039, Cohen's d=5.18 |
| L_RIB ≈ β-VAE | Tangent-space approximation erases Riemannian distinction |
| Thread orthogonality | Enforced by QR decomposition, not emergent |
| Zero-shot transfer | Not improved by AFM |

### Status

These results existed in a previous session but the `afm-lite/` directory containing all code, trained models, and result artifacts has been deleted or was never persisted. The findings survive only as notes — the experimental evidence is unrecoverable without re-running the entire program.

---

## Component-by-Component Classification

| Component | Connection Status | Details |
|-----------|------------------|---------|
| Frontend Display | 🟡 PARTIALLY CONNECTED | Renders static AFM architecture theory |
| API Routes | 🔴 DISCONNECTED | No AFM endpoints |
| Data Layer | 🔴 DISCONNECTED | No AFM data exists |
| ACOS Runtime | 🔴 DISCONNECTED | No AFM modules |
| Experiment Results | 🔴 DISCONNECTED | Previous data lost |
| Mini Services | 🔴 DISCONNECTED | No AFM service |

---

## Overall Classification

# PARTIALLY CONNECTED (Display-Only)

AFM is visible in the UI as an architectural concept but has **zero operational capability**. The system presents AFM as a core architectural pillar while possessing no computation, no data, no API, and no runtime support for it.

### Connection Reality

```
┌─────────────────────────────────────────────────────┐
│                  USER-FACING LAYER                   │
│  ┌─────────────────────────────────────────────┐    │
│  │  AFM Architecture Section (Part 3)          │    │
│  │  ✓ Component Evaluation Table               │    │
│  │  ✓ Architecture Comparison Chart            │    │
│  │  ✓ Radar Chart Visualization               │    │
│  │  ✓ Mamba-OTM Animated Visualization         │    │
│  │  ✓ Accordion with Component Decisions       │    │
│  │  ✓ Hybrid Verdict Card                      │    │
│  └─────────────────────────────────────────────┘    │
│                        │                             │
│                   hardcoded data                     │
│                        │                             │
│                        ▼                             │
│  ┌─────────────────────────────────────────────┐    │
│  │         NO BACKEND EXISTS                   │    │
│  │  ✗ No API routes                            │    │
│  │  ✗ No data layer                            │    │
│  │  ✗ No runtime modules                       │    │
│  │  ✗ No mini services                         │    │
│  │  ✗ No experiment results                    │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

### Gap Analysis

| Dimension | Displayed | Actual | Gap |
|-----------|-----------|--------|-----|
| Architecture | Full interactive section | Static hardcoded data | 100% |
| Computation | Implied by visualizations | None | 100% |
| Data | Comparison tables/charts | No data sources | 100% |
| API | Implied by interactive UI | No endpoints | 100% |
| Runtime | Implied by architecture | No modules | 100% |
| Evidence | Previous experiment claimed | All artifacts lost | 100% |

**The gap between display and reality is 100%.**

---

## Recommendations

1. **Acknowledge the gap** — The UI should not present AFM as operational when it is display-only
2. **Recover or re-run experiments** — The AFM-Lite v0.1 results are scientifically valuable but currently unrecoverable
3. **Build API surface** — If AFM is to remain a first-class section, it needs at minimum a `/api/afm` endpoint
4. **Persist experiment data** — Any future experimental results must be committed to version control or persistent storage
5. **Consider scope** — Either invest in making AFM real or reduce the frontend presentation to match reality

---

*End of AFM Integration Audit*
