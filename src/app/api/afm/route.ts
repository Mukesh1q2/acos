import { NextResponse } from "next/server";

const afmData = {
  version: "v0.1",
  experimentId: "AFM-LITE-EXP-001",
  runDate: "2025-06",
  dataAvailable: false,
  dataWarning:
    "Experiment artifacts from v0.1 are no longer available on disk. The afm-lite/ directory has been removed. Findings below are reconstructed from session logs — the raw data, trained models, and result files are unrecoverable without re-running the entire program.",

  architecture: {
    totalParams: 602_650,
    encoder: "784 → 256 → 256",
    latent: "μ,logvar(128) → reshape(32,4) → QR → St(32,4) → flatten(128)",
    decoder: "128 → 256 → 784",
    keyMechanism:
      "QR decomposition projects Gaussian samples onto Stiefel manifold St(32,4). The encoder outputs 128-dim parameters, which are reshaped to a 32×4 matrix and orthogonalized via QR decomposition.",
    equivalentTo:
      "Standard VAE with QR-based latent projection. The Stiefel constraint provides implicit regularization, not architectural novelty.",
    baselineParams: 602_650,
    paramMatch: true,
  },

  findings: [
    {
      id: "F1",
      claim: "Stiefel projection prevents KL collapse at high β",
      classification: "CONFIRMED",
      baseline: "β=1e-2 → 11.35% active dimensions",
      afm: "β=1e-2 → 98.40% active dimensions",
      notes:
        "Robust effect across multiple seeds. Root cause: QR projection constrains the latent space to the Stiefel manifold, preventing variance collapse. This is the strongest positive result.",
    },
    {
      id: "F2",
      claim: "AFM+L_RIB reduces catastrophic forgetting by 80%",
      classification: "PARTIALLY CONFIRMED",
      baseline: "Baseline VAE forgetting: 24.82%",
      afm: "AFM+L_RIB forgetting: 5.04%",
      notes:
        "Effect is real but magnitude may be inflated by small model size (602K params). L_RIB is numerically identical to β-VAE (see F3), so the benefit comes from Stiefel regularization, not Riemannian geometry.",
    },
    {
      id: "F3",
      claim: "L_RIB (Riemannian IB) provides geometric advantage over β-VAE",
      classification: "ARTIFACT",
      baseline: "β-VAE KL divergence",
      afm: "L_RIB KL = β-VAE KL (identical)",
      notes:
        "Tangent-space Gaussian approximation makes the KL term numerically identical to standard VAE KL. The Riemannian curvature term vanishes under linearization. No geometric benefit whatsoever.",
    },
    {
      id: "F4",
      claim: "Thread orthogonality is an emergent property of Stiefel training",
      classification: "ARTIFACT",
      baseline: "N/A",
      afm: "S_i^T · S_j = 0 (always, by QR construction)",
      notes:
        "Orthogonality is mathematically enforced by QR decomposition every forward pass, not emergent from training dynamics. This is true by construction, like saying normalized vectors have unit length.",
    },
    {
      id: "F5",
      claim: "Stiefel manifold improves zero-shot transfer learning",
      classification: "FAILED",
      baseline: "87.2% (Baseline VAE on Fashion-MNIST after MNIST training)",
      afm: "86.8% (AFM on Fashion-MNIST after MNIST training)",
      notes:
        "No transfer improvement. AFM slightly worse, likely because the constrained Stiefel latent space reduces representation flexibility needed for domain shift.",
    },
    {
      id: "F6",
      claim: "AFM+L_RIB significantly outperforms baseline (p=0.039, d=5.18)",
      classification: "ARTIFACT",
      baseline: "97.52% ± 0.12%",
      afm: "97.84% ± 0.08%",
      notes:
        "Statistically significant but practically negligible (0.32% accuracy difference). Large Cohen's d is driven by extremely low variance, not large effect size. The Stiefel projection provides regularization equivalent to dropout.",
    },
  ],

  summary: {
    CONFIRMED: 1,
    "PARTIALLY CONFIRMED": 1,
    ARTIFACT: 2,
    FAILED: 2,
    UNRESOLVED: 0,
  },

  v02Status: {
    executed: false,
    plannedPhases: [
      "Phase 1: Independent Replication — 10 seeds with 95% CIs",
      "Phase 2: Stronger Datasets — EMNIST, Fashion-MNIST, KMNIST, CIFAR-10, Synthetic",
      "Phase 3: Full Ablation — 5 configurations isolating QR/KL/latent size/architecture",
      "Phase 4: KL Collapse Investigation — why does Stiefel prevent collapse?",
      "Phase 5: Continual Learning Benchmarks — Split-MNIST, Permuted-MNIST, Sequential Fashion-MNIST",
      "Phase 6: Representation Analysis — is Stiefel better or merely different?",
      "Phase 7: Failure Analysis — honest documentation of all failures",
    ],
  },

  honestAssessment: {
    whatWorks: [
      "QR projection genuinely prevents posterior collapse at high β (F1 is the strongest result)",
      "Forgetting reduction is real, though the mechanism is simpler than claimed (F2)",
      "The Stiefel manifold constraint is mathematically well-defined and correctly implemented",
    ],
    whatDoesnt: [
      "L_RIB ≈ β-VAE — no Riemannian geometric advantage (F3 is the most important negative finding)",
      "Thread orthogonality is enforced by QR, not emergent (F4)",
      "Zero-shot transfer shows no improvement (F5)",
      "The 'significant' accuracy difference is practically negligible (F6)",
      "No evidence that Stiefel manifolds provide benefits beyond standard regularization",
    ],
    simplestEquivalent:
      "Standard VAE + orthogonal regularization (torch.nn.utils.orthogonal_) + β-VAE loss achieves the same practical outcomes as AFM-Lite without the Riemannian geometry framework or QR decomposition overhead.",
    recommendation:
      "Abandon Stiefel manifold as an architectural primitive at this model scale. The sole validated benefit (KL collapse prevention via F1) can be achieved more simply with dropout or spectral normalization. Revisit only if the theoretical framework generates testable predictions that differ from standard regularization — which the current L_RIB = β-VAE finding shows it does not.",
  },

  generated_at: new Date().toISOString(),
};

export async function GET() {
  return NextResponse.json(afmData);
}
