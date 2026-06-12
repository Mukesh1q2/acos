# AFM Phase 4.6 — Master Report

> **Program**: AFM-Lite Phase 4.6 — Consolidation and Contradiction Analysis
> **Date**: 2025-06-13
> **Data Sources**: v0.1 (602K, 3 seeds), v0.2 (602K, 10 seeds), Phase 4.5A-E (1.33M, 3-5 seeds)
> **Total Experimental Runs**: ~120+ individual training runs across all phases
> **Rule**: Evidence over elegance. Honest reporting. No selective presentation.

---

## The Four Questions

### 1. What Survived?

**Three effects survived stronger testing:**

#### A. Stiefel Projection Prevents Posterior Collapse (PARTIALLY PROVEN)

This is the most valuable surviving effect. At 1.33M parameter scale, β-VAE with β≥0.005 collapses 100% of the time (16/16 seeds across 4 datasets). AFM's QR projection prevents collapse entirely (0/16 seeds collapsed).

The mechanism is algebraic, not learned: QR decomposition guarantees a non-degenerate representation. The decoder always receives a full-rank Stiefel point, breaking the collapse feedback loop.

**Why only PARTIALLY PROVEN**: The effect is scale-dependent. At 602K on MNIST with correct per-sample KL, neither model collapses. The benefit only manifests at 1.33M scale where β-VAE's collapse vulnerability increases.

**Quantitative summary**:
| Scale | Dataset | β-VAE collapse rate | AFM collapse rate |
|---|---|---|---|
| 602K, MNIST | 0% | 0% | (No collapse at small scale) |
| 1.33M, MNIST | 100% | 0% | |
| 1.33M, Fashion-MNIST | 100% | 0% | |
| 1.33M, KMNIST | 100% | 0% | |
| 1.33M, EMNIST | 100% | 0% | |

#### B. Stiefel Projection Improves Representation Quality (PROVEN)

The most robust finding across all phases. AFM produces better-clustered latent representations as measured by silhouette score, in 100% of tested conditions:

| Scale | Dataset | Baseline Sil | AFM Best Sil | Improvement |
|---|---|---|---|---|
| 602K | MNIST | 0.371 | 0.676 | +82% |
| 602K | MNIST (v0.2) | 0.335 | 0.641 | +91% |
| 1.33M | MNIST | 0.512 | 0.667 | +30% |
| 1.33M | Fashion-MNIST | 0.321 | 0.437 | +36% |
| 1.33M | KMNIST | 0.308 | 0.416 | +35% |
| 1.33M | EMNIST | 0.120 | 0.190 | +58% |

**Critical caveat**: Better silhouette does not reliably translate to better downstream task performance. Fashion-MNIST shows better representations but equal or worse accuracy.

#### C. Small Accuracy Improvement on MNIST-type Data (PARTIALLY PROVEN)

AFM+RIB provides a statistically significant but practically marginal accuracy improvement on MNIST:
- v0.1: +0.66% (p=0.039, d=5.179)
- v0.2: +1.36% (p=1.36e-6, d=3.48)
- Phase 4.5E: +0.24% at 1.33M

However, 80% of this improvement comes from KL regularization (standard β-VAE), not from the Stiefel projection. The unique AFM contribution beyond β-VAE is approximately 0.24%.

---

### 2. What Failed?

**Four effects failed stronger testing:**

#### A. AFM Reduces Catastrophic Forgetting (FAILED)

The v0.1 claim of 80% forgetting reduction does NOT survive multi-seed validation at 1.33M scale.

**v0.1**: Baseline forgetting = 0.248, AFM+RIB = 0.050 (80% reduction) ✅
**v0.2 Split-MNIST**: Baseline = 0.100, AFM+RIB = 0.352 (3.5× WORSE) ❌
**Phase 4.5B**: Baseline = 0.257, AFM+RIB = 0.313 (22% WORSE, CIs non-overlapping) ❌

The v0.1 result was protocol-specific (cross-domain tasks where Stiefel rigidity helps). On standard benchmarks (Split-MNIST, class-incremental), AFM worsens forgetting. The Stiefel constraint is a **rigidity** that helps when tasks need different subspaces but hurts when tasks need fine-grained shared adaptation.

#### B. L_RIB Is Distinct from β-VAE (FAILED)

The tangent-space Gaussian approximation makes L_RIB numerically identical to β-VAE's standard Gaussian KL. The 0.24% accuracy difference between AFM+RIB and Baseline+VAE is within noise. Phase 4.5C proves AFM+QR (without any KL) also prevents collapse — the active mechanism is QR, not RIB.

#### C. AFM+QR Alone Improves Accuracy (FAILED)

At 602K with 8 epochs, AFM+QR hurts accuracy on MNIST (-0.77%) and Fashion-MNIST (-7.74%). At 1.33M with 15 epochs, AFM+QR matches baseline on Fashion-MNIST (+0.01%) and slightly helps on KMNIST (+0.76%). The Stiefel projection alone is unreliable — it requires sufficient training epochs and model capacity.

#### D. AFM Works on All Datasets (FAILED)

AFM+RIB underperforms baseline on Fashion-MNIST (v0.2: -1.0%) and EMNIST (Phase 4.5E: -0.13%). The silhouette improvement generalizes but the accuracy improvement does not. AFM works best on character/digit recognition and provides no advantage on object/shape classification.

---

### 3. What Contradicts Previous Claims?

**Three major contradictions:**

#### Contradiction 1: Forgetting Reduction Direction Reversal

| Phase | Protocol | AFM Effect |
|---|---|---|
| v0.1 | Cross-domain (3 tasks) | 80% REDUCTION ✅ |
| v0.2 | Split-MNIST | 3.5× WORSE ❌ |
| Phase 4.5B | Class splits (5 tasks, 5 seeds) | 22% WORSE ❌ |

**Why**: The Stiefel constraint acts as latent space rigidity. When tasks are semantically different, rigidity preserves old knowledge. When tasks are fine-grained, rigidity prevents necessary adaptation, causing MORE forgetting.

**Impact**: This completely undermines the most dramatic v0.1 claim. The forgetting reduction was not wrong — it was cherry-picked by protocol.

#### Contradiction 2: KL Collapse Classification Reversal

| Phase | Verdict | Evidence |
|---|---|---|
| v0.1 | "Stiefel prevents collapse" | Baseline collapses at β=0.01 |
| v0.2 | "Collapse was ARTIFACT" | Correct KL, neither model collapses at 602K |
| Phase 4.5 | "Collapse is REAL at 1.33M" | β-VAE collapses 100% at β≥0.005 |

**Why**: v0.2's "ARTIFACT" classification was premature. It was based on 602K MNIST only. At 1.33M scale, collapse is pervasive for β-VAE. The v0.1 KL bug exaggerated the effect but didn't create it from nothing.

**Impact**: The collapse resistance is rehabilitated as a real (scale-dependent) effect, but the original v0.1 evidence is tainted by the bug. An honest paper must acknowledge both the bug and the scale-dependency.

#### Contradiction 3: L_RIB Contribution Attribution

| Phase | Claim |
|---|---|
| v0.1 | "L_RIB provides benefits through Riemannian structure" |
| v0.2 | "L_RIB ≈ β-VAE numerically; improvement comes from KL" |
| Phase 4.5C | "QR (not KL) is the mechanism for collapse resistance" |

**Why**: Progressive ablation removed supposed contributors one at a time:
1. Remove L_RIB → AFM+QR still works → L_RIB not needed
2. Remove KL → AFM+QR still resists collapse → KL not needed for collapse
3. Remove QR → β-VAE collapses → QR is the active ingredient

**Impact**: The entire RIB theoretical framework provides no practical benefit. The only value is the QR projection, which is standard linear algebra, not a novel objective.

---

### 4. Is AFM Worthy of Phase 5?

**Answer: NO — in its current form.**

Phase 5 (RSSM integration, world models, agent architectures) is not warranted based on the evidence:

#### Reasons Against Phase 5

1. **No universal forgetting benefit**: AFM worsens forgetting on standard benchmarks. A world model that forgets MORE is worse than useless — it's harmful.

2. **No task performance advantage**: The 0.24% accuracy improvement beyond β-VAE is negligible. A world model needs representations that work, not representations that look slightly better in silhouette.

3. **The theoretical framework failed**: L_RIB ≈ β-VAE. OTM orthogonality is enforced, not emergent. PIB doesn't improve transfer. There is no theoretical foundation for why AFM would help in a world model.

4. **Scale effects are concerning**: The benefits of AFM diminish at 1.33M while its harms (worse forgetting) amplify. At the 10M-100M scale of world models, AFM may be even more harmful.

5. **The minimal architecture is trivial**: β-VAE + QR projection. This is a one-line code change, not an architecture that needs RSSM integration.

#### What WOULD Make Phase 5 Warranted

1. **If collapse resistance is the goal**: A targeted study comparing QR projection vs free bits vs KL annealing vs other collapse prevention methods on large-scale VAEs. This would be a methods paper, not a world model paper.

2. **If representation quality is the goal**: A study on whether Stiefel-constrained representations provide benefits in downstream tasks (generation, anomaly detection, fairness). Better clustering that doesn't help downstream is not enough.

3. **If continual learning is the goal**: A fundamentally different approach is needed. The current AFM worsens forgetting on standard benchmarks. Simply adding AFM to RSSM would likely make the world model forget more, not less.

4. **If RIB is the goal**: Implement the full matrix Fisher KL (with normalizing constant Z(κ)). Only then can we test whether the Riemannian structure provides any benefit over standard Gaussian KL.

---

## Consolidated Evidence Summary

### Hypothesis Classification

| Hypothesis | Classification | Confidence | Key Evidence |
|---|---|---|---|
| H1: Stiefel prevents collapse | **PARTIALLY_PROVEN** | High | 16/16 β-VAE collapsed at 1.33M, 0/16 AFM collapsed. Scale-dependent. |
| H2: AFM reduces forgetting | **FAILED** | Very High | Phase 4.5B: AFM+RIB 22% worse (CI non-overlap). Standard benchmarks fail. |
| H3: AFM improves representations | **PROVEN** | Very High | +25-58% silhouette across ALL conditions. 100% consistency. |
| H4: L_RIB distinct from β-VAE | **FAILED** | Very High | Numerical identity. 0.24% difference. QR is active ingredient. |
| H5: AFM improves accuracy | **PARTIALLY_PROVEN** | Medium | Significant on MNIST. 0.24% beyond β-VAE. Dataset-dependent. |
| H6: AFM generalizes | **PARTIALLY_PROVEN** | Medium | Silhouette generalizes. Accuracy does not. Character-data affinity. |

### Effect Magnitude Summary

| Effect | Magnitude | Direction | Reliability |
|---|---|---|---|
| Collapse resistance | 0% vs 100% collapse | Positive | High (at 1.33M) |
| Silhouette improvement | +25-58% | Positive | Very High |
| Accuracy beyond β-VAE | +0.24% | Positive (barely) | Low |
| Forgetting (standard) | +22% worse | **Negative** | High |
| Forgetting (cross-domain) | -80% better | Positive | Medium (protocol-specific) |

### Mechanism Attribution

| Effect | Primary Mechanism | RIB Contribution |
|---|---|---|
| Collapse resistance | QR projection (100%) | None |
| Silhouette improvement | QR projection (~70%), KL (~30%) | None beyond KL |
| Accuracy improvement | KL regularization (~80%), QR (~20%) | None beyond KL |
| Forgetting (cross-domain) | QR rigidity + KL | Minor |
| Forgetting (fine-grained) | QR rigidity (harmful) | None |

### Minimal Architecture

**β-VAE + QR projection** — reproduces all surviving effects without L_RIB, Haar prior, or thread specialization.

### Publication Readiness

**WORKSHOP_READY** — one strong finding (collapse prevention), one moderate finding (silhouette), multiple honest failures.

---

## Deliverables Generated

| File | Description |
|---|---|
| `AFM_MASTER_RESULTS.json` | Complete statistical database across all phases |
| `AFM_HYPOTHESIS_STATUS.md` | H1-H6 classification with evidence |
| `AFM_CONTRADICTION_REPORT.md` | Cross-phase contradiction analysis |
| `AFM_MECHANISM_REPORT.md` | Mechanism attribution for each effect |
| `AFM_MINIMAL_ARCHITECTURE_REPORT.md` | Minimal architecture reproducing surviving effects |
| `AFM_PUBLICATION_READINESS.md` | Publication readiness assessment |
| `AFM_PHASE46_MASTER_REPORT.md` | This document |

---

## Final Statement

The AFM-Lite experimental program has been an exercise in intellectual honesty. We began with a bold claim — that the Avadhana Delta's mathematical framework provides measurable benefits — and subjected it to progressively stronger testing.

**What we found**:
- The Stiefel projection (QR decomposition) is a genuinely useful technique for preventing posterior collapse in β-VAEs at scale. This is real and reproducible.
- The Stiefel projection consistently improves representation quality (silhouette). This is the most robust finding.
- The L_RIB objective provides no benefit beyond standard β-VAE. The theoretical distinction is real but is lost in the practical approximation.
- The forgetting reduction claim was protocol-specific and reverses on standard benchmarks.
- The "something more" claims — emergent orthogonality, automatic thread specialization, universal improvement — all failed.

**What AFM actually is**: β-VAE with a QR projection. A one-line code change that prevents collapse and improves representation structure. Useful, but not transformative.

**What AFM is not**: A cognitive architecture component, a fundamentally new learning objective, or a universal improvement technique.

The honest conclusion is that AFM-Lite is an interesting negative result with one genuinely useful engineering insight. The mathematical framework is elegant, but elegance does not guarantee empirical power. What survives is what survives.

---

*Report generated by AFM-Lite Phase 4.6 Consolidation Program*
*All evidence collected, all contradictions documented, all failures reported.*
*Phase 5 (RSSM/world models) is NOT recommended without fundamental changes.*
*STOP here. Do not proceed to Phase 5 without explicit user instruction.*
