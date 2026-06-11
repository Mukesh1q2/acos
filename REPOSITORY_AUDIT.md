# Repository Audit

**Generated:** 2025-06-11  
**Repository:** https://github.com/Mukesh1q2/acos.git  
**Branch:** main  

---

## Content Verification Checklist

| Check | Status | Details |
|-------|--------|---------|
| AFM source files present | ✅ | 12 Python files |
| AFM JSON experiment outputs present | ✅ | 7 JSON files |
| AFM experiment report present | ✅ | AFM_EXPERIMENT_REPORT.md |
| ACOS runtime present | ✅ | 97 files (kernel, cognitive, agents, etc.) |
| Root reports present | ✅ | 15 major reports |
| Config files present | ✅ | 9 config files |
| Next.js source present | ✅ | 112 files under src/ |
| No dataset caches | ✅ | 0 .cache/ files in git |
| No .db files | ✅ | 0 .db files in git |
| No node_modules | ✅ | 0 node_modules/ files in git |
| No .next build | ✅ | 0 .next/ files in git |
| No .pkl files | ✅ | 0 .pkl files in git |
| No .env secrets | ✅ | 0 .env files in git |

---

## AFM Source Files (12)

| File | Purpose |
|------|---------|
| `afm-lite/stiefel.py` | Stiefel manifold operations (QR decomposition) |
| `afm-lite/models.py` | AFM encoder/decoder architecture |
| `afm-lite/losses.py` | L_RIB, β-VAE, KL divergence losses |
| `afm-lite/data.py` | Dataset loading (MNIST, Fashion-MNIST, KMNIST, etc.) |
| `afm-lite/train.py` | Training loop |
| `afm-lite/experiments.py` | Experiment runner |
| `afm-lite/run_all.py` | Run all v0.1 experiments |
| `afm-lite/phase2_reproduction.py` | Phase 2 reproduction script |
| `afm-lite/run_v02.py` | v0.2 full validation |
| `afm-lite/run_v02_targeted.py` | v0.2 targeted experiments |
| `afm-lite/run_scale_1m.py` | 1M parameter scaling script |
| `afm-lite/run_rssm.py` | RSSM world model prototype |

## AFM Experiment Results (7)

| File | Content |
|------|---------|
| `afm-lite/results/experiment_a.json` | v0.1 Baseline vs AFM |
| `afm-lite/results/experiment_b_vae.json` | β-VAE comparison |
| `afm-lite/results/experiment_c.json` | Continual learning |
| `afm-lite/results/experiment_d.json` | Representation analysis |
| `afm-lite/results/experiment_e.json` | Statistical tests |
| `afm-lite/results_v02/ablation_fashion_mnist.json` | v0.2 ablation on Fashion-MNIST |
| `afm-lite/results_v02/statistical_tests.json` | v0.2 statistical validation |

## Root Reports (15)

| Report | Subject |
|--------|---------|
| `ACOS_ACTIVATION_REPORT.md` | ACOS runtime activation |
| `ACOS_ARCHITECTURAL_REALITY_REPORT.md` | Architecture vs reality audit |
| `ACOS_WHITEPAPER_VS_REALITY_AUDIT.md` | Whitepaper claims audit |
| `AFM_FINAL_POSTMORTEM.md` | AFM final scientific assessment |
| `AFM_FORENSIC_REPORT.md` | Forensic investigation of deleted files |
| `AFM_GIT_STATUS_REPORT.md` | Git status after Phase 1 |
| `AFM_INTEGRATION_AUDIT.md` | AFM-ACOS integration audit |
| `AFM_POSTMORTEM.md` | Original AFM postmortem |
| `AFM_REPRODUCIBILITY_PROTOCOL.md` | Reproducibility protocol |
| `AFM_RESTORATION_REPORT.md` | Phase 0 restoration report |
| `AFM_V01_REPRODUCTION_REPORT.md` | Phase 2 reproduction results |
| `AFM_VALIDATION_REPORT_V02_REAL.md` | Phase 3 v0.2 validation |
| `INFRASTRUCTURE_HEALTH_REPORT.md` | Infrastructure status |
| `PYTHON_ENVIRONMENT_REPORT.md` | Python environment audit |
| `SCIENTIFIC_VALIDATION_AUDIT.md` | Scientific validation audit |

## ACOS Runtime (97 files)

Core modules:
- `acos/kernel.py` — Cognitive kernel
- `acos/cognitive/` — Belief system, goal system, knowledge fabric, reasoning engine, semantic memory
- `acos/cognitive/dynamics/` — Attention, cognitive graph, counterfactual, engine, plan state, state evolution, uncertainty
- `acos/cognitive/predictive/` — Causal reasoner, goal forecast, outcome predictor, simulation engine, state transition graph, world model
- `acos/cognitive/unified/` — Active learning, attention economy, cognitive cycle, cognitive manifold, enhanced causal, evaluation, goal competition, self model, world model engine
- `acos/agents/` — Base, memory, planning, research, verification
- `acos/engines/` — Reflection, verification
- `acos/memory/` — Manager, OTM, store
- `acos/models/` — Router
- `acos/validation/` — A/B testing, baselines, benchmarks, cognitive metrics, emergent behavior, failure analysis, report generator, test generator
- `acos/api/` — Server
- Tests: 11 test files

## Config Files (9)

| File | Purpose |
|------|---------|
| `package.json` | Node.js project config |
| `tsconfig.json` | TypeScript config |
| `next.config.ts` | Next.js config |
| `prisma/schema.prisma` | Database schema |
| `Caddyfile` | Gateway config |
| `components.json` | shadcn/ui config |
| `eslint.config.mjs` | ESLint config |
| `mini-services/acos-runtime/package.json` | ACOS microservice config |
| `tailwind.config.ts` | Tailwind CSS config |

---

## Items Correctly Excluded

| Excluded | Size | Regeneration Method |
|----------|------|---------------------|
| `afm-lite/.cache/` | 1.05 GB | Auto-downloaded by `data.py` on first run |
| `acos-runtime/data/*.db` | 127 MB | Auto-created by ACOS runtime |
| `node_modules/` | 1.2 GB | `bun install` |
| `.next/` | 504 MB | `bun run dev` |
| `.env` | 24 B | User must provide |
| `download/` | 29 MB | QA screenshots (non-essential) |
| `skills/` | 60 MB | Internal tools (non-essential) |

---

## Conclusion

**Repository is clean and ready for GitHub publication.** All source code, experiment results, reports, and configs are tracked. No dataset caches, databases, build artifacts, or secrets are included. Total push size: ~6.1 MB.
