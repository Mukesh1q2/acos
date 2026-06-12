# AFM Phase 4.5B — Forgetting Statistics Report

**Date**: 2026-06-12 18:18
**Scale**: ~1.33M params (hidden_dim=512)
**Protocol**: Split-Fashion-MNIST (5 tasks × 2 classes each)
**Seeds**: [0, 42, 84, 126, 168] | **Epochs/task**: 5
**BETA**: 0.01 | **LR**: 0.001

## Average Forgetting (mean ± 95% CI)

| Config | Avg Forgetting | 95% CI |
|--------|---------------|--------|
| baseline | 0.2574 | [0.2552, 0.2595] |
| afm_task | 0.2530 | [0.2275, 0.2784] |
| afm_rib | 0.3129 | [0.2789, 0.3469] |

## Per-Task Forgetting

| Config | Task 0 | Task 1 | Task 2 | Task 3 |
|--------|--------|--------|--------|--------|
| baseline | 0.4836 | 0.4655 | 0.0420 | 0.0384 |
| afm_task | 0.4858 | 0.4168 | 0.0534 | 0.0558 |
| afm_rib | 0.4862 | 0.4719 | 0.1245 | 0.1689 |

## Baseline vs AFM vs AFM+RIB

- Baseline avg forgetting: **0.2574**
- AFM (task only) avg forgetting: **0.2530**
- AFM+RIB avg forgetting: **0.3129**
- AFM task forgetting reduction vs baseline: **1.7%**
- AFM+RIB forgetting reduction vs baseline: **-21.6%**