# AFM Phase 4.5C — Beta Sweep Report

**Date**: 2026-06-12 18:31
**Scale**: ~1.33M params (hidden_dim=512)
**Dataset**: Fashion-MNIST | **Epochs**: 15 | **Seed**: 42
**Betas tested**: [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05]

## Accuracy vs Beta

| Config | β=1e-04 | β=5e-04 | β=1e-03 | β=5e-03 | β=1e-02 | β=5e-02 |
|--------|--------|--------|--------|--------|--------|--------|
| beta_vae | 0.8946 | 0.8736 | 0.8678 | 0.3803 † | 0.2836 † | 0.1000 † |
| afm_qr | 0.8914 | 0.8969 | 0.8943 | 0.8923 | 0.8915 | 0.8839 |
| afm_rib | 0.8952 | 0.8950 | 0.8899 | 0.8938 | 0.8904 | 0.8858 |

† = collapsed (accuracy < 15% or active dims < 5%)

## Active Dimensions vs Beta

| Config | β=1e-04 | β=5e-04 | β=1e-03 | β=5e-03 | β=1e-02 | β=5e-02 |
|--------|--------|--------|--------|--------|--------|--------|
| beta_vae | 128 | 127 | 125 | 0 | 0 | 0 |
| afm_qr | 128 | 128 | 128 | 128 | 128 | 127 |
| afm_rib | 128 | 128 | 128 | 128 | 128 | 128 |

## Collapse Thresholds

- **beta_vae**: collapses at β ≥ 5e-03
- **afm_qr**: no collapse in tested range (up to β=5e-02)
- **afm_rib**: no collapse in tested range (up to β=5e-02)

## Key Finding

**AFM+RIB is collapse-resistant**: β-VAE collapses at β ≥ 5e-03, while AFM+RIB shows no collapse up to β=5e-02. The Stiefel projection prevents posterior collapse.