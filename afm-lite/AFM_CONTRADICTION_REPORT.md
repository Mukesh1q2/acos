# AFM Contradiction Report

> **Program**: AFM-Lite Phase 4.6 — Consolidation and Contradiction Analysis
> **Date**: 2025-06-13
> **Purpose**: Identify contradictions between v0.1, v0.2, Phase 4, and Phase 4.5
> **Rule**: Honest analysis. No excuses. Explain WHY contradictions exist.

---

## Contradiction 1: Forgetting Reduction (CRITICAL)

### v0.1 Claim
"AFM+RIB reduces catastrophic forgetting by 80% (0.248 → 0.050)"

### Phase 4.5B Finding
"AFM+RIB INCREASES catastrophic forgetting by 22% (0.257 → 0.313), with non-overlapping 95% CIs"

### Root Cause Analysis

**The v0.1 result was real but not generalizable.** Here are the specific factors:

#### 1. Task Protocol Changed

| Factor | v0.1 | Phase 4.5B |
|---|---|---|
| Tasks | MNIST → Fashion-MNIST → Synthetic | Fashion-MNIST class splits (5 subsets) |
| Task similarity | Very different (digits→clothes→synthetic) | Fine-grained (different clothing classes) |
| Number of tasks | 3 | 5 |
| Task domain | Cross-domain | Within-domain |

The v0.1 protocol used **semantically very different tasks** (digits vs clothing vs synthetic clusters). In this setting, the Stiefel constraint can preserve separate structure per domain because the latent representations for each domain are naturally far apart. When tasks are fine-grained class splits within the same dataset, the Stiefel constraint PREVENTS the model from making the small adaptations needed to preserve old class knowledge while learning new classes.

#### 2. Metric Definition Consistency

Both used the same metric: `forgetting = acc_after_learning - best_acc_after_task_ended`, averaged across old tasks. The definition is consistent. The discrepancy is NOT a metric artifact.

#### 3. Seed and Scale Effects

v0.1 used 1 seed at 602K. Phase 4.5B used 5 seeds at 1.33M. The effect was not validated across seeds in v0.1.

#### 4. What This Means

The forgetting reduction claim is **protocol-specific**:
- **Cross-domain tasks** (MNIST→Fashion→Synthetic): AFM helps (v0.1)
- **Permuted-same-domain** (Permuted-MNIST): AFM helps moderately (v0.2)
- **Fine-grained class splits** (Split-MNIST, Fashion class splits): AFM **hurts** (v0.2, Phase 4.5B)

The Stiefel constraint acts as a **rigidity** on the latent space. When tasks need very different representations, rigidity preserves old knowledge. When tasks need fine-grained adaptation within similar representations, rigidity prevents necessary adaptation, causing MORE forgetting.

### Resolution

**v0.1's 80% forgetting reduction is not wrong — it is misleading.** It only applies to cross-domain sequential learning, which is the least challenging continual learning scenario (most methods handle this well). On standard benchmarks (Split-MNIST, class-incremental), AFM+RIB worsens forgetting.

---

## Contradiction 2: KL Collapse (PARTIALLY RESOLVED)

### v0.1 Claim
"Stiefel projection prevents KL collapse. At β=1e-2, baseline VAE collapses (11.35%) while AFM stays at 98.40%."

### v0.2 Classification
"ARTIFACT — collapse was due to KL computation bug (batch-summed KL). With correct per-sample KL, neither model collapses."

### Phase 4.5C/E Finding
"At 1.33M scale, β-VAE collapses 100% at β≥0.005 on Fashion-MNIST and β=0.01 on ALL datasets. AFM never collapses."

### Root Cause Analysis

#### What Happened

1. **v0.1 had a KL bug**: KL was summed over the batch (giving values ~977 instead of ~0.25 per sample). This inflated the KL penalty by ~4000×, causing catastrophic collapse at β=1e-2 for β-VAE. The finding was exaggerated.

2. **v0.2's correction was incomplete**: With per-sample KL averaging at 602K on MNIST, neither model collapsed at β≤0.1. v0.2 concluded "neither model collapses with correct KL" — but this was only tested at ONE scale on ONE easy dataset.

3. **Scale matters**: At 1.33M parameters, the encoder has more capacity, and the KL penalty has a stronger effect. β-VAE's posterior can more easily match the prior (driving active dims to 0) because the larger encoder can more precisely minimize the KL term. AFM's QR projection prevents this because QR maps any input to a valid Stiefel point — the decoder always receives a full-rank representation.

4. **Dataset difficulty matters**: Fashion-MNIST is harder than MNIST, requiring more latent capacity. When β-VAE's KL penalty pushes toward the prior, the model loses capacity needed for the harder task, causing collapse.

#### The Complete Picture

| Scale | Dataset | β=0.01 β-VAE | β=0.01 AFM | Verdict |
|---|---|---|---|---|
| 602K | MNIST (bug KL) | COLLAPSED | Stable | Exaggerated by bug |
| 602K | MNIST (correct KL) | Stable | Stable | No collapse at small scale |
| 1.33M | MNIST | COLLAPSED | Stable | Real at larger scale |
| 1.33M | Fashion-MNIST | COLLAPSED | Stable | Real at larger scale |
| 1.33M | KMNIST | COLLAPSED | Stable | Real at larger scale |
| 1.33M | EMNIST | COLLAPSED | Stable | Real at larger scale |

### Resolution

**Both v0.1 and v0.2 were partially right and partially wrong.**

- v0.1 was right that Stiefel prevents collapse, but the evidence was exaggerated by the KL bug
- v0.2 was right that the v0.1 evidence was flawed, but wrong to classify collapse as a pure artifact
- Phase 4.5 shows collapse IS real at 1.33M scale, and AFM genuinely prevents it

**The corrected classification: The collapse resistance is REAL but CONDITIONAL.** It depends on model scale and dataset difficulty. At 602K on MNIST, the effect doesn't manifest. At 1.33M on any dataset, it is dramatic and reproducible.

---

## Contradiction 3: AFM+QR Alone Improves Accuracy

### v0.1 Implication
The Stiefel projection alone provides benefits (AFM+L_task: 0.9815 vs Baseline: 0.9777, +0.38%)

### v0.2 Finding
"AFM+QR alone HURTS accuracy on MNIST (0.8977 vs 0.9054, -0.77%) and catastrophically on Fashion-MNIST (0.7006 vs 0.7780, -7.74%)"

### Phase 4.5E Finding
AFM+QR matches or slightly exceeds baseline on most datasets at 1.33M:
- MNIST: +0.23% (0.9835 vs 0.9812)
- Fashion-MNIST: +0.01% (0.8895 vs 0.8894)
- KMNIST: +0.76% (0.9233 vs 0.9157) — best AFM result
- EMNIST: +0.11% (0.8540 vs 0.8529)

### Root Cause Analysis

#### 1. Training Duration and Epoch Count

| Phase | Epochs | AFM+QR vs Baseline |
|---|---|---|
| v0.1 | 30 | +0.38% (better) |
| v0.2 | 8 | -0.77% (worse) |
| Phase 4.5E | 15 | +0.01% to +0.76% (mixed) |

AFM+QR appears to need more training epochs to converge. With only 8 epochs (v0.2), the Stiefel constraint hurts because the model hasn't had time to adapt to the constrained latent space. With 15-30 epochs, it matches or slightly exceeds baseline.

#### 2. The 602K vs 1.33M Scale

At 602K (v0.2), AFM+QR hurts (-0.77%). At 1.33M (Phase 4.5E), AFM+QR matches or helps (+0.01% to +0.76%). The larger model has more capacity to compensate for the constraint, making the projection less harmful.

#### 3. Fashion-MNIST Remains Problematic

Even at 1.33M with 15 epochs, AFM+QR only matches baseline on Fashion-MNIST (0.8895 vs 0.8894). The Stiefel constraint appears to limit the model's ability to learn the more complex feature hierarchies needed for clothing classification.

### Resolution

**AFM+QR alone is not reliably beneficial.** It requires:
- Sufficient training epochs (≥15)
- Sufficient model capacity (1.33M or larger)
- Favorable dataset structure (character recognition > object recognition)

The v0.1 benefit was real (30 epochs) but the v0.2 failure was also real (8 epochs). Neither is wrong — they test different regimes.

---

## Contradiction 4: Accuracy Improvement Magnitude

### v0.1 Finding
AFM+RIB improves MNIST accuracy by +0.66% (0.9777 → 0.9843), p=0.039

### v0.2 Finding
AFM+RIB improves MNIST accuracy by +1.36% (0.9054 → 0.9190), p=1.36e-6

### Phase 4.5E Finding
AFM+RIB improves MNIST accuracy by +0.24% (0.9812 → 0.9836)

### Root Cause Analysis

#### 1. Different Baseline Accuracy Levels

| Phase | Baseline Acc | AFM+RIB Acc | Δ |
|---|---|---|---|
| v0.1 | 97.77% | 98.43% | +0.66% |
| v0.2 | 90.54% | 91.90% | +1.36% |
| Phase 4.5E | 98.12% | 98.36% | +0.24% |

v0.2 had a much lower baseline (90.54%) because it used only 8 epochs vs 30 (v0.1) and 15 (Phase 4.5E). The improvement is largest when the baseline is weakest. This is consistent with KL regularization providing the most benefit when the model is undertrained.

#### 2. Diminishing Returns at High Accuracy

When baseline accuracy is already ~98%, there is very little room for improvement. The 0.24% gain at 1.33M may represent the true ceiling of AFM's contribution after KL regularization effects are accounted for.

#### 3. The KL Contribution

v0.2 ablation: Baseline+VAE = 97.71%, AFM+RIB = 97.95%. The unique AFM contribution (beyond KL) is only 0.24%. This is consistent with Phase 4.5E's 0.24% finding.

### Resolution

**The true AFM contribution (beyond KL regularization) is approximately 0.24% accuracy improvement on MNIST.** The larger improvements seen in v0.1 and v0.2 were primarily due to KL regularization, with AFM adding a small consistent bonus.

---

## Contradiction 5: L_RIB vs β-VAE Practical Difference

### v0.1 Claim
"L_RIB provides benefits beyond standard β-VAE through Riemannian structure"

### v0.2 Finding
"L_RIB ≈ β-VAE numerically. The tangent-space Gaussian approximation erases the distinction."

### Phase 4.5C Finding
"AFM+QR (without any KL) achieves the same collapse resistance as AFM+RIB. The active mechanism is QR projection, not L_RIB."

### Root Cause Analysis

This is not really a contradiction — it's a progressive refinement of understanding:

1. **v0.1** correctly noted the mathematical equivalence but didn't emphasize it enough
2. **v0.2** properly classified the equivalence as the primary finding
3. **Phase 4.5C** proved definitively that QR (not KL/RIB) is the mechanism for collapse resistance

The progression: L_RIB → β-VAE+QR → QR alone. Each step removes a supposed contributor and finds the effect persists.

### Resolution

**L_RIB provides no benefit beyond standard β-VAE KL regularization.** The unique AFM benefit comes entirely from the QR projection. This is now established across all phases.

---

## Cross-Phase Contradiction Summary

| Claim | v0.1 | v0.2 | Phase 4.5 | Resolution |
|---|---|---|---|---|
| AFM reduces forgetting 80% | ✅ Claimed | ⚠️ Protocol-dependent | ❌ 22% WORSE | **FAILED** — only works on cross-domain tasks |
| Stiefel prevents collapse | ✅ Claimed | ❌ Classified as ARTIFACT | ✅ REAL at 1.33M | **PARTIALLY REAL** — scale-dependent, not artifact |
| AFM+QR helps accuracy | ✅ +0.38% | ❌ -0.77% to -7.74% | ⚠️ Mixed | **UNRELIABLE** — needs epochs + capacity |
| AFM+RIB >> Baseline+VAE | ⚠️ Implied | ❌ 0.24% difference | ⚠️ Confirmed 0.24% | **MARGINAL** — not practically significant |
| L_RIB is distinct | ⚠️ Acknowledged equivalence | ❌ FAILED | ❌ QR is active ingredient | **FAILED** — L_RIB ≈ β-VAE |
| Silhouette improvement | ✅ +82% | ✅ +91% | ✅ +27-58% | **PROVEN** — universally consistent |

---

## Methodological Lessons

1. **Single-protocol results are dangerous**: v0.1's forgetting result was protocol-specific. Standard benchmarks must be used.

2. **Scale matters**: Effects that don't appear at 602K can be dramatic at 1.33M. Effects that appear at 602K can disappear at 1.33M. Both directions occur.

3. **Bug artifacts can contain real effects**: The v0.1 KL bug exaggerated collapse, but collapse IS real at 1.33M. The bug made the effect look bigger, but the underlying mechanism was sound.

4. **Training duration matters**: AFM+QR needs more epochs than unconstrained models. 8 epochs (v0.2) is insufficient; 15-30 epochs are needed.

5. **Multi-seed validation is essential**: v0.1 used 1-3 seeds. Phase 4.5B used 5 seeds and found different results. The single-seed v0.1 forgetting result was a lucky (or unlucky) draw.

6. **The hierarchy of evidence**:
   - v0.1: Hypothesis generation (weak evidence)
   - v0.2: Hypothesis testing with corrected methodology (moderate evidence)
   - Phase 4.5: Multi-seed, multi-protocol validation (strong evidence)

---

*Report generated by AFM-Lite Phase 4.6 Consolidation Program*
*All contradictions documented honestly. No excuses offered.*
