# AFM Restoration Report

**Date:** 2026-06-10  
**Status:** ✅ VERIFIED — All files restored with matching SHA256 hashes  
**Source:** Local backup uploaded as `afm-lite.zip` + individual files

---

## Restoration Summary

| Metric | Value |
|--------|-------|
| Total files restored | 13 |
| Total size | 200 KB |
| SHA256 mismatches | **0** |
| Cross-verification (zip vs individual uploads) | **ALL MATCH** |
| Missing files from expected set | **0** |

---

## Directory Tree

```
afm-lite/
├── AFM_EXPERIMENT_REPORT.md     (20,306 bytes)
├── data.py                       (9,058 bytes)
├── experiments.py                (33,324 bytes)
├── losses.py                     (4,914 bytes)
├── models.py                     (11,556 bytes)
├── run_all.py                    (39,080 bytes)
├── stiefel.py                    (9,120 bytes)
├── train.py                      (10,736 bytes)
└── results/
    ├── experiment_a.json         (10,026 bytes)
    ├── experiment_c.json         (15,213 bytes)
    ├── experiment_d.json         (1,494 bytes)
    ├── experiment_e.json         (2,580 bytes)
    └── exp_b_vae.json            (400 bytes)
```

---

## SHA256 Verification

### Source Code

| File | SHA256 | Status |
|------|--------|--------|
| stiefel.py | `d2c4f447...eaca5` | ✅ MATCH |
| models.py | `0f67bec0...f4de4` | ✅ MATCH |
| losses.py | `80686fb8...4900b` | ✅ MATCH |
| data.py | `c758cc96...bcc12` | ✅ MATCH |
| train.py | `4e1b2737...5aa32` | ✅ MATCH |
| experiments.py | `319b11e8...ddf48` | ✅ MATCH |
| run_all.py | `146a38eb...a21e0` | ✅ MATCH |

### Result Files

| File | SHA256 | Status |
|------|--------|--------|
| results/experiment_a.json | `490fc597...e8749` | ✅ MATCH |
| results/experiment_c.json | `99b6e414...57213` | ✅ MATCH |
| results/experiment_d.json | `08123b5f...1942d` | ✅ MATCH |
| results/experiment_e.json | `7fb51088...9fa28` | ✅ MATCH |
| results/exp_b_vae.json | `24edda08...36977` | ✅ MATCH |

### Report

| File | SHA256 | Status |
|------|--------|--------|
| AFM_EXPERIMENT_REPORT.md | `e3cb6007...47d1` | ✅ MATCH |

---

## Data Integrity Verification

### Key Numbers vs Postmortem

The AFM_POSTMORTEM.md (written from session memory in a previous session) references specific numbers. These have been verified against the restored JSON data:

| Claim in Postmortem | Value from Restored JSON | Match? |
|---------------------|-------------------------|--------|
| AFM test accuracy: 97.84% ± 0.08% | 98.39% ± 0.06% | ⚠️ DISCREPANCY |
| Forgetting (baseline): 24.82% | 24.82% | ✅ EXACT MATCH |
| Forgetting (AFM+L_RIB): 5.04% | 5.04% | ✅ EXACT MATCH |
| 80% forgetting reduction | (24.82-5.04)/24.82 = 79.7% | ✅ CORRECT |

### ⚠️ Accuracy Discrepancy

The postmortem states AFM accuracy = 97.84% ± 0.08%. The restored experiment_a.json shows test_acc_mean = 98.39% ± 0.06%.

**This is a 0.55% discrepancy.** Possible explanations:
1. The postmortem may have cited numbers from a different experiment (e.g., baseline vs AFM confusion)
2. The postmortem numbers were from a single run, while the JSON averages 3 seeds
3. A transcription error occurred when writing the postmortem from memory

**Action required:** This must be resolved by re-running Experiment A in Phase 2. The JSON file is the primary source; the postmortem is a secondary source.

---

## Missing Files

The following files from the expected AFM-Lite codebase were NOT present in the backup:

| File | Expected? | Impact |
|------|-----------|--------|
| `requirements.txt` | Yes | Cannot reproduce exact Python environment |
| `pyproject.toml` | Possible | Project config missing |
| `multi_run_stats.json` | Referenced in postmortem | Multi-seed statistical results missing |
| `statistical_tests.json` | Referenced in postmortem | Formal statistical test results missing |
| `seeds.log` | No | Random seeds not recorded |
| Model checkpoints (`.pt`) | No | Not expected (re-trainable) |
| Training logs (`.csv`) | No | Per-epoch metrics not saved |
| `.cache/` data | No | MNIST/Fashion-MNIST cache (regenerable) |

**Critical missing:** `multi_run_stats.json` and `statistical_tests.json` were referenced in the AFM_INTEGRATION_AUDIT as existing in the original afm-lite/results/ directory. Their absence means the statistical significance claims (p=0.039, d=5.18) from the postmortem cannot be verified from the backup.

**This is why Phase 2 (re-running v0.1) is essential.**

---

## Code Audit Summary

### Verified Properties

1. **stiefel.py**: QR projection is correctly implemented with sign correction. `stiefel_kl_complexity()` computes per-sample KL then averages — this was the bug fix from v0.1. The KL is numerically identical to standard VAE KL (confirming the L_RIB = β-VAE finding).

2. **models.py**: Both `BaselineModel` and `AFMLiteModel` have matched parameter counts (602,650). The AFM model correctly applies QR projection via `StiefelLayer`.

3. **losses.py**: `l_rib()` computes `ce + beta * kl` where kl comes from `stiefel_kl_complexity()`. Since stiefel_kl = standard KL, L_RIB = β-VAE. This confirms the mathematical finding.

4. **train.py**: `train_sequential()` correctly evaluates on all tasks after each task. The VAE path for baseline was fixed (includes KL regularization).

5. **data.py**: Uses `sklearn.fetch_openml` for MNIST/Fashion-MNIST with local caching.

---

## Conclusion

**Restoration is VERIFIED.** All 13 files have matching SHA256 hashes between the zip archive and individually uploaded files. The code is complete and internally consistent.

**One discrepancy noted:** The postmortem accuracy number (97.84%) differs from the JSON (98.39%). This must be resolved by re-running experiments.

**Two files missing:** `multi_run_stats.json` and `statistical_tests.json` — statistical significance claims cannot be verified from backup alone.

**Recommendation:** Proceed to Phase 1 (git commit) immediately, then Phase 2 (re-run v0.1 experiments).
