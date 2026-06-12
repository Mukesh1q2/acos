# AFM Phase 4.5D — Latent Geometry Study Report

**Date**: 2026-06-12 18:44
**Scale**: ~1.33M params (hidden_dim=512)
**Dataset**: Fashion-MNIST | **Epochs**: 15 | **Seed**: 42
**BETA**: 0.01

## Accuracy by Geometry and Config

| Geometry | baseline | afm_task | afm_qr | afm_rib |
|----------|--------|--------|--------|--------|
| (16,8)=128 | 0.8890 | 0.8938 | 0.8896 | 0.8904 |
| (64,2)=128 | 0.8890 | 0.8953 | 0.8902 | 0.8910 |
| (32,4)=128 [current] | 0.8890 | 0.8942 | 0.8915 | 0.8904 |
| (32,8)=256 | 0.8904 | 0.8897 | 0.8908 | 0.8885 |

## Silhouette Score by Geometry

| Geometry | baseline | afm_task | afm_qr | afm_rib |
|----------|--------|--------|--------|--------|
| (16,8)=128 | 0.3322 | 0.4129 | 0.2648 | 0.2491 |
| (64,2)=128 | 0.3322 | 0.4572 | 0.5253 | 0.5143 |
| (32,4)=128 [current] | 0.3322 | 0.4412 | 0.4138 | 0.3878 |
| (32,8)=256 | 0.3314 | 0.4181 | 0.4101 | 0.4026 |

## Average Forgetting by Geometry

| Geometry | baseline | afm_task | afm_qr | afm_rib |
|----------|--------|--------|--------|--------|
| (16,8)=128 | 0.2727 | 0.2593 | 0.2649 | 0.2680 |
| (64,2)=128 | 0.2727 | 0.2848 | 0.2485 | 0.3030 |
| (32,4)=128 [current] | 0.2727 | 0.2794 | 0.2534 | 0.2714 |
| (32,8)=256 | 0.1034 | 0.2736 | 0.4896 | 0.2955 |

## Geometry Analysis

- **(16,8)=128**: Many short threads (K=8, d=16). More orthogonal directions, but each thread has limited capacity.
- **(64,2)=128**: Few long threads (K=2, d=64). Fewer orthogonal directions, but each thread carries more information.
- **(32,4)=128**: Current default. Balanced thread count and dimension.
- **(32,8)=256**: More threads with same dimension, but larger total latent space.

**Best AFM+RIB geometry**: (64,2)=128 (accuracy=0.8910)