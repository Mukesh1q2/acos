# Reproducibility Status

**Generated:** 2025-06-11  
**Repository:** https://github.com/Mukesh1q2/acos.git  

---

## Confidence Classification

Every major report and finding is classified by reproducibility confidence.

### Classification Key

| Level | Meaning |
|-------|---------|
| **HIGH** | Source code + data on GitHub. Can be re-run and verified. |
| **MEDIUM** | Source code on GitHub. Results may differ slightly across runs but directionally reproducible. |
| **LOW** | Results exist in JSON/reports but raw data was lost. Re-running may not reproduce exact numbers. |
| **UNVERIFIABLE** | Claims based on conversation-only memory, no disk-backed evidence. |

---

## AFM Reports

### AFM_EXPERIMENT_REPORT.md — **MEDIUM**

- **Evidence**: v0.1 experiment JSONs present (`results/experiment_*.json`, `exp_b_vae.json`)
- **Risk**: JSON numbers were transcribed from a now-deleted original run. Phase 2 reproduction confirmed directionally similar results but not exact matches.
- **Verifiable**: Yes, by re-running `python run_all.py`
- **Key finding**: AFM+L_RIB reduces forgetting from 24.82% → 5.04% (80% reduction)

### AFM_RESTORATION_REPORT.md — **HIGH**

- **Evidence**: SHA256 hashes computed at restoration time, file counts verified
- **Risk**: Hashes were computed against the restored files, which were then committed
- **Verifiable**: Yes, by checking git commit `1dc6f4d`

### AFM_GIT_STATUS_REPORT.md — **HIGH**

- **Evidence**: Git status output from Phase 1 commit
- **Verifiable**: Yes, by checking git history

### AFM_V01_REPRODUCTION_REPORT.md — **MEDIUM**

- **Evidence**: Phase 2 re-ran experiments A, C, E and compared with restored JSONs
- **Risk**: Numbers may differ by random seed but directionally consistent
- **Verifiable**: Yes, by re-running `python phase2_reproduction.py`

### AFM_VALIDATION_REPORT_V02_REAL.md — **MEDIUM**

- **Evidence**: v0.2 Fashion-MNIST ablation JSON present (`results_v02/ablation_fashion_mnist.json`)
- **Risk**: Full v0.2 (4 datasets × 5 ablations) was NOT completed — only Fashion-MNIST ablation ran to completion
- **Verifiable**: Partially. Fashion-MNIST results reproducible. EMNIST/KMNIST/CIFAR-10 not yet run.

### AFM_FINAL_POSTMORTEM.md — **LOW → MEDIUM**

- **Evidence**: Postmortem transcribed findings from experiment JSONs (which are on GitHub)
- **Risk**: Some findings (F5 zero-shot transfer, F6 statistical significance) reference data that was in deleted files
- **Verifiable**: Core findings (F1-F4) verifiable from JSONs. F5-F6 require re-running experiments.

### AFM_FORENSIC_REPORT.md — **HIGH**

- **Evidence**: Forensic analysis of git history, filesystem, and container lifecycle
- **Verifiable**: Yes, all claims backed by git log and filesystem inspection

### AFM_REPRODUCIBILITY_PROTOCOL.md — **HIGH**

- **Evidence**: Protocol document defining commit tiers and verification steps
- **Verifiable**: Yes, the protocol was followed

### AFM_INTEGRATION_AUDIT.md — **MEDIUM**

- **Evidence**: Audit of AFM-ACOS integration based on code inspection
- **Verifiable**: Yes, by inspecting the codebase

---

## ACOS Reports

### ACOS_ACTIVATION_REPORT.md — **MEDIUM**

- **Evidence**: ACOS runtime code on GitHub, activation data in `acos-runtime/data/activation_report.json`
- **Risk**: Runtime databases (acos.db) not on GitHub — were excluded due to size
- **Verifiable**: Yes, by running `python run_activation.py`

### ACOS_ARCHITECTURAL_REALITY_REPORT.md — **MEDIUM**

- **Evidence**: Based on code inspection of tracked files
- **Verifiable**: Yes, by comparing report claims against actual code

### ACOS_WHITEPAPER_VS_REALITY_AUDIT.md — **MEDIUM**

- **Evidence**: Based on code inspection comparing whitepaper claims to implementation
- **Verifiable**: Yes, by comparing report against actual code

---

## Infrastructure Reports

### INFRASTRUCTURE_HEALTH_REPORT.md — **LOW**

- **Evidence**: Point-in-time snapshot of container state
- **Risk**: Container state changes on restart. Not reproducible.
- **Verifiable**: No. Specific disk/memory numbers are historical.

### PYTHON_ENVIRONMENT_REPORT.md — **MEDIUM**

- **Evidence**: `pip_freeze_container.txt` and `python_version.txt` are tracked in git
- **Verifiable**: Yes, by comparing pip_freeze against current environment

### SCIENTIFIC_VALIDATION_AUDIT.md — **MEDIUM**

- **Evidence**: Based on `scientific_validation.py` code and validation database (excluded from git)
- **Risk**: Database not on GitHub; validation results require re-running
- **Verifiable**: Yes, by running `python scientific_validation.py`

---

## Summary Table

| Report | Confidence | Disk-Backed | Re-runnable |
|--------|-----------|-------------|-------------|
| AFM_EXPERIMENT_REPORT.md | MEDIUM | ✅ JSONs | ✅ |
| AFM_RESTORATION_REPORT.md | HIGH | ✅ Git | ✅ |
| AFM_GIT_STATUS_REPORT.md | HIGH | ✅ Git | ✅ |
| AFM_V01_REPRODUCTION_REPORT.md | MEDIUM | ✅ Code | ✅ |
| AFM_VALIDATION_REPORT_V02_REAL.md | MEDIUM | ✅ Partial JSONs | ⚠️ Partial |
| AFM_FINAL_POSTMORTEM.md | LOW→MEDIUM | ✅ JSONs (partial) | ⚠️ Partial |
| AFM_FORENSIC_REPORT.md | HIGH | ✅ Git | ✅ |
| AFM_REPRODUCIBILITY_PROTOCOL.md | HIGH | ✅ Git | ✅ |
| AFM_INTEGRATION_AUDIT.md | MEDIUM | ✅ Code | ✅ |
| ACOS_ACTIVATION_REPORT.md | MEDIUM | ✅ JSON | ✅ |
| ACOS_ARCHITECTURAL_REALITY_REPORT.md | MEDIUM | ✅ Code | ✅ |
| ACOS_WHITEPAPER_VS_REALITY_AUDIT.md | MEDIUM | ✅ Code | ✅ |
| INFRASTRUCTURE_HEALTH_REPORT.md | LOW | ❌ Point-in-time | ❌ |
| PYTHON_ENVIRONMENT_REPORT.md | MEDIUM | ✅ pip_freeze | ✅ |
| SCIENTIFIC_VALIDATION_AUDIT.md | MEDIUM | ✅ Code | ✅ |

---

## Key AFM Findings — Reproducibility Assessment

| Finding | Claim | Confidence | Evidence |
|---------|-------|-----------|----------|
| F1 | AFM+L_RIB reduces forgetting by 80% (24.82% → 5.04%) | MEDIUM | experiment_c.json, re-confirmed in Phase 2 |
| F2 | QR projection prevents KL collapse at high β | MEDIUM | experiment_a.json |
| F3 | L_RIB numerically identical to β-VAE (tangent-space approximation) | HIGH | losses.py code + mathematical proof |
| F4 | Stiefel geometry enforced by QR, not emergent | HIGH | models.py code inspection |
| F5 | Zero-shot transfer to Fashion-MNIST | LOW | Original data deleted; not yet re-run in v0.2 |
| F6 | Statistical significance of forgetting reduction | LOW | Original data deleted; Phase 2 partial |

---

## What Would Improve Confidence

1. **Complete v0.2 execution** (all 4 datasets × 5 ablations) — would upgrade F5, F6 to MEDIUM/HIGH
2. **Re-run Phase 2 reproduction** with fixed random seeds — would upgrade F1, F2 to HIGH
3. **Scale to 1M parameters** — would provide new evidence for or against AFM's value
4. **RSSM prototype** — would test predictive representation claim
