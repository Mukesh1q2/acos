# AFM Git Status Report

**Date:** 2026-06-10  
**Tag:** `afm-v0.1-restored`

---

## Commits Made

| Commit | Message | Files |
|--------|---------|-------|
| `b3d2358` | Source code from local backup | 8 files (3,433 insertions) |
| `11a6328` | Experiment result JSONs | 5 files (1,232 insertions) |
| `b46c99a` | Restoration verification report | 1 file (146 insertions) |
| `95d6acb` | Container Python environment | 2 files |

## Tag

- `afm-v0.1-restored` — marks the verified restoration point

## Git-tracked AFM files

```
afm-lite/
├── AFM_EXPERIMENT_REPORT.md        ✅ Tier 1 — committed
├── data.py                          ✅ Tier 1 — committed
├── experiments.py                   ✅ Tier 1 — committed
├── losses.py                        ✅ Tier 1 — committed
├── models.py                        ✅ Tier 1 — committed
├── run_all.py                       ✅ Tier 1 — committed
├── stiefel.py                       ✅ Tier 1 — committed
├── train.py                         ✅ Tier 1 — committed
├── pip_freeze_container.txt         ✅ Tier 2 — committed
├── python_version.txt               ✅ Tier 2 — committed
└── results/
    ├── experiment_a.json            ✅ Tier 1 — committed
    ├── experiment_c.json            ✅ Tier 1 — committed
    ├── experiment_d.json            ✅ Tier 1 — committed
    ├── experiment_e.json            ✅ Tier 1 — committed
    └── exp_b_vae.json               ✅ Tier 1 — committed
```

## Untracked files

None. All afm-lite files are tracked.

## Missing from backup (not tracked, cannot commit)

| File | Status | Impact |
|------|--------|--------|
| `multi_run_stats.json` | NOT in backup | p=0.039, d=5.18 claims unverifiable |
| `statistical_tests.json` | NOT in backup | Same |
| `requirements.txt` | NOT in backup | Environment reproduction incomplete |
| Model checkpoints | NOT in backup | Re-trainable, not needed |

## Next Steps

Phase 2 requires installing PyTorch, then re-running Experiments A, C, E to verify the restored data against fresh computation.
