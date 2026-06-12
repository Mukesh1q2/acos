# OLP Phase 5 — Orthogonal Latent Projection in RSSM

> **Project**: OLP (Orthogonal Latent Projection)
> **Origin**: Surviving mechanism from AFM-Lite Phase 4.6
> **Target**: Predictive world models (RSSM architectures)
> **Question**: Can OLP improve latent stability inside RSSM?

## What survived from AFM-Lite

- QR projection prevents posterior collapse (PARTIALLY_PROVEN)
- QR projection improves silhouette score (PROVEN)
- RIB theory FAILED — no benefit beyond β-VAE
- Forgetting claims FAILED — worsens on standard benchmarks
- Universal superiority FAILED — dataset-specific only

## OLP Philosophy

No architecture prestige. No attachment to previous ideas.
Only mechanisms that repeatedly survive stronger tests are allowed to continue.

## Conditions

1. Vanilla RSSM
2. RSSM + β-VAE
3. RSSM + OLP (QR only)
4. RSSM + OLP + KL

## Datasets

- Moving-MNIST (first)
- Pendulum (after success)
- CartPole (after success)
- DMControl (only after clear success)

## Metrics

1. Prediction MSE
2. Long rollout error
3. Latent collapse
4. Active dimensions
5. Representation drift
6. Silhouette score
7. Training stability
8. Runtime cost

## Classification System

- PROVEN
- PARTIALLY_PROVEN
- FAILED
- UNKNOWN

## Failure Policy

If RSSM+OLP performs the same as RSSM: mark OLP as FAILED.
If OLP hurts performance: document it. Do not rescue it with additional complexity.

## Final Question

Not "How can we save OLP?"
But: "Does OLP deserve to exist?"

Evidence alone decides.
