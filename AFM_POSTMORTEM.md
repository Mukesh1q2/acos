# AFM-Lite Postmortem

## Executive Summary

The AFM-Lite Experimental Program (v0.1) tested whether the mathematical ideas from the Avadhana Delta paper — Stiefel manifold parameterization, Riemannian Information Bottleneck (L_RIB), and Orthogonal Thread Memory (OTM) — provide measurable benefits on a small (602K param) model. The program ran 5 experiments (A-E) across MNIST classification, KL collapse analysis, multi-seed statistical testing, continual learning, and zero-shot transfer.

**Result: The core architectural claims did not survive empirical testing.**

## 1. Which Hypotheses Failed

### H1: L_RIB provides a geometrically meaningful loss function ❌ FAILED
- **Claim**: The Riemannian Information Bottleneck (L_RIB) leverages the curvature of the Stiefel manifold to provide a geometrically superior regularization compared to standard β-VAE.
- **Reality**: The tangent-space Gaussian approximation used in L_RIB makes the KL term numerically identical to standard β-VAE KL. The Riemannian curvature term vanishes under linearization. L_RIB = β-VAE, not approximately, but exactly.
- **Impact**: This is the most damaging finding. The entire theoretical motivation for the Stiefel manifold in the loss function is undermined. There is no geometric benefit.

### H2: Thread orthogonality emerges from Stiefel training ❌ FAILED  
- **Claim**: Training on the Stiefel manifold naturally produces orthogonal thread states, which is a form of structured disentanglement.
- **Reality**: Orthogonality is enforced by QR decomposition every forward pass. It is true by construction, not emergent. Claiming this as a "property" is like claiming that normalized vectors have unit length as an emergent property of normalization.
- **Impact**: The OTM (Orthogonal Thread Memory) concept is an engineering choice, not a scientific discovery.

### H3: Stiefel manifold improves zero-shot transfer ❌ FAILED
- **Claim**: The structured latent space provided by the Stiefel manifold should improve generalization to new tasks.
- **Reality**: AFM achieved 86.8% on Fashion-MNIST after training on MNIST, vs. 87.2% for baseline. No improvement. The constrained Stiefel latent space actually reduces representation flexibility needed for domain shift.
- **Impact**: The Stiefel constraint does not provide the inductive bias that was theorized.

## 2. Which Hypotheses Survived

### H4: Stiefel projection prevents KL collapse ✅ CONFIRMED
- **Claim**: The orthogonal constraint on the latent space prevents posterior collapse at high β values.
- **Reality**: At β=1e-2, baseline VAE retains only 11.35% of latent dimensions active, while AFM retains 98.40%. This is a robust effect.
- **However**: The mechanism is simple regularization, not Riemannian geometry. Any orthogonal constraint (including PyTorch's built-in `torch.nn.utils.orthogonal_`) would likely produce similar results.
- **Verdict**: The effect is real but the explanation is wrong.

### H5: AFM reduces catastrophic forgetting ⚠️ PARTIALLY CONFIRMED
- **Claim**: AFM+L_RIB reduces catastrophic forgetting in continual learning.
- **Reality**: Baseline forgetting was 24.82%, AFM+L_RIB forgetting was 5.04% (80% reduction).
- **However**: Since L_RIB = β-VAE, the benefit comes from Stiefel regularization acting as implicit regularizer, not from Riemannian geometry. The effect magnitude may be inflated by the small model size (602K params).
- **Verdict**: The effect is real but the mechanism is standard regularization.

## 3. Which Effects Were Artifacts

### The "significant" accuracy difference (p=0.039, Cohen's d=5.18) ❌ ARTIFACT
- AFM accuracy: 97.84% ± 0.08%, Baseline: 97.52% ± 0.12%
- The 0.32% absolute difference is statistically significant but practically negligible
- The large Cohen's d (5.18) is driven by extremely low variance, not large effect size
- This is a textbook example of statistical significance without practical significance

### The "emergent" thread orthogonality ❌ ARTIFACT
- S_i^T · S_j = 0 is always true because QR decomposition enforces it
- This is not a finding; it's a tautology

## 4. Simplest Equivalent Architecture

A standard VAE with:
- β-VAE loss (identical to L_RIB)
- Orthogonal regularization via `torch.nn.utils.orthogonal_()` or spectral normalization
- Standard dropout (provides similar regularization to Stiefel projection)

achieves the same practical outcomes as AFM-Lite without:
- Riemannian geometry framework
- QR decomposition overhead
- Stiefel manifold optimization complexity
- Cayley retraction computational cost

The Stiefel manifold is a valid mathematical object, but at this model scale and with the tangent-space approximation, it provides zero benefits over simpler alternatives.

## 5. Recommendation

**Do not proceed with AFM v0.2 or any Stiefel-based architecture at this scale.**

The single validated benefit (KL collapse prevention via F1) can be achieved more simply:
1. Use standard β-VAE loss
2. Add orthogonal regularization as a simple loss term
3. Use spectral normalization or dropout

**If Stiefel manifold research is to continue**, it must:
1. Generate testable predictions that differ from standard regularization
2. Demonstrate benefits on models >10M parameters where the manifold structure might matter
3. Avoid the tangent-space approximation that erases the Riemannian distinction
4. Provide a theoretical framework where curvature actually affects the optimization trajectory

**Current evidence does not justify the engineering complexity of the Stiefel pipeline.**

---

*Truth is more important than architecture prestige.*
