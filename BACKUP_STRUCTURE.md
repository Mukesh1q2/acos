# Backup Structure

**Generated:** 2025-06-11  
**Repository:** https://github.com/Mukesh1q2/acos.git  

---

## Overview

This document classifies every file in the project as either **tracked source** (preserved on GitHub) or **generated artifact** (excluded from git, regenerated locally).

---

## Tracked Source (Preserved on GitHub — 320 files, 6.1 MB)

### AFM-Lite Research Code (25 files)

```
afm-lite/
├── stiefel.py              # Stiefel manifold operations
├── models.py               # AFM encoder/decoder architecture
├── losses.py               # L_RIB, β-VAE, KL divergence
├── data.py                 # Dataset loading
├── train.py                # Training loop
├── experiments.py          # Experiment runner
├── run_all.py              # Run all v0.1 experiments
├── phase2_reproduction.py  # Phase 2 reproduction
├── run_v02.py              # v0.2 full validation
├── run_v02_targeted.py     # v0.2 targeted ablations
├── run_scale_1m.py         # 1M parameter scaling
├── run_rssm.py             # RSSM world model prototype
├── run_phase2.sh           # Phase 2 shell runner
├── run_v02_background.sh   # v0.2 background runner
├── pip_freeze_container.txt # Python package list at experiment time
├── python_version.txt       # Python version at experiment time
├── AFM_EXPERIMENT_REPORT.md # v0.1 experiment report
├── results/
│   ├── experiment_a.json    # Baseline vs AFM
│   ├── exp_b_vae.json       # β-VAE comparison
│   ├── experiment_c.json     # Continual learning
│   ├── experiment_d.json     # Representation analysis
│   └── experiment_e.json     # Statistical tests
└── results_v02/
    ├── ablation_fashion_mnist.json  # v0.2 ablation
    └── statistical_tests.json       # v0.2 stats
```

### ACOS Runtime (97 files)

```
acos-runtime/
├── README.md
├── pyproject.toml
├── scientific_validation.py
├── activate_tables.py
├── read_db.py
├── run_100_queries.py
├── run_100_queries_v2.py
├── run_activation.py
├── run_validation.py
├── seed_cognitive_data.py
├── tests/               # 11 test files
├── acos/
│   ├── kernel.py
│   ├── cli.py
│   ├── scheduler.py
│   ├── trace_logger.py
│   ├── agents/          # 6 files
│   ├── api/             # 2 files
│   ├── cognitive/       # 15 files + subdirs
│   ├── engines/         # 3 files
│   ├── memory/          # 4 files
│   ├── models/          # 2 files
│   ├── schemas/         # 6 files
│   └── validation/      # 11 files
└── data/
    └── activation_report.json
```

### Reports (15 files)

```
ACOS_ACTIVATION_REPORT.md
ACOS_ARCHITECTURAL_REALITY_REPORT.md
ACOS_WHITEPAPER_VS_REALITY_AUDIT.md
AFM_FINAL_POSTMORTEM.md
AFM_FORENSIC_REPORT.md
AFM_GIT_STATUS_REPORT.md
AFM_INTEGRATION_AUDIT.md
AFM_POSTMORTEM.md
AFM_REPRODUCIBILITY_PROTOCOL.md
AFM_RESTORATION_REPORT.md
AFM_V01_REPRODUCTION_REPORT.md
AFM_VALIDATION_REPORT_V02_REAL.md
INFRASTRUCTURE_HEALTH_REPORT.md
PYTHON_ENVIRONMENT_REPORT.md
SCIENTIFIC_VALIDATION_AUDIT.md
```

### Next.js Frontend (112 files)

```
src/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   └── api/          # 7 API routes
├── components/
│   ├── acos/         # 42 ACOS components
│   └── ui/           # 45 shadcn/ui components
├── hooks/            # 2 hooks
└── lib/              # 2 utilities
```

### Configs (9 files)

```
package.json
tsconfig.json
next.config.ts
prisma/schema.prisma
Caddyfile
components.json
eslint.config.mjs
tailwind.config.ts
mini-services/acos-runtime/package.json
```

### Other Tracked Files

```
.gitignore
worklog.md
bun.lock
public/               # 4 static assets
upload/               # 8 uploaded files (PDFs, .md, source copies)
agent-ctx/            # 18 agent context files
.zscripts/            # 6 build/dev scripts
examples/websocket/   # 2 WebSocket examples
```

---

## Generated Artifacts (NOT on GitHub — Regenerated Locally)

### Dataset Caches (1.05 GB)

| Path | Size | Regeneration |
|------|------|-------------|
| `afm-lite/.cache/mnist.pkl` | 420 MB | `python -c "from data import get_mnist; get_mnist()"` |
| `afm-lite/.cache/fashion_mnist.pkl` | 420 MB | `python -c "from data import get_fashion_mnist; get_fashion_mnist()"` |
| `afm-lite/.cache/kmnist.pkl` | 210 MB | `python -c "from data import get_kmnist; get_kmnist()"` |
| `afm-lite/.cache/torchvision/` | 73 MB | Auto-downloaded by torchvision |

### Runtime Databases (127 MB)

| Path | Size | Regeneration |
|------|------|-------------|
| `acos-runtime/data/acos.db` | 127 MB | `python run_activation.py` |
| `acos-runtime/data/scientific_validation.db` | — | `python scientific_validation.py` |
| `acos-runtime/data/validation.db` | — | `python run_validation.py` |
| `acos-runtime/data/reasoning.db` | — | Auto-created at runtime |
| `db/custom.db` | 24 KB | `bun run db:push` |

### Build Artifacts (1.7 GB)

| Path | Size | Regeneration |
|------|------|-------------|
| `node_modules/` | 1.2 GB | `bun install` |
| `.next/` | 504 MB | `bun run dev` |

### Other Generated

| Path | Size | Regeneration |
|------|------|-------------|
| `.venv/` | ~2 GB | `python -m venv .venv && pip install -r requirements.txt` |
| `download/` | 29 MB | QA screenshots (non-essential) |
| `skills/` | 60 MB | Internal tools (non-essential) |

---

## Reproduction Steps (From Clean Clone)

```bash
# 1. Clone repository
git clone https://github.com/Mukesh1q2/acos.git
cd acos

# 2. Install Node.js dependencies
bun install

# 3. Setup database
bun run db:push

# 4. Start Next.js dev server
bun run dev

# 5. Setup Python environment (for AFM experiments)
python -m venv .venv
source .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install numpy scipy scikit-learn matplotlib

# 6. Run AFM experiments (datasets auto-download)
cd afm-lite
python run_all.py  # v0.1 experiments
python run_v02.py  # v0.2 validation

# 7. Setup ACOS runtime
cd ../acos-runtime
pip install -e .
python run_activation.py
```
