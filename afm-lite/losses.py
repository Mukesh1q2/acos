"""
Loss Functions for AFM-Lite Experiments

Implements:
- L_task: Standard task loss (cross-entropy + optional reconstruction)
- L_RIB: Riemannian Information Bottleneck (from Avadhana Delta, Definition 1.7)
  L_RIB = -E[log p(x_{t+1} | S_t)] + β · KL_R[q(S_t | x_{≤t}) || p_Haar(S_t)]
       = accuracy_term + β · complexity_term

The key hypothesis: L_RIB should produce representations that are:
1. More predictive of the future (better generalization)
2. More compressed (less overfitting)
3. Better for transfer learning
4. More stable under multi-task learning
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


def l_task(logits: torch.Tensor, targets: torch.Tensor,
           recon: torch.Tensor = None, inputs: torch.Tensor = None,
           recon_weight: float = 0.0) -> dict:
    """
    Standard task loss: cross-entropy for classification.

    Optionally includes reconstruction loss (for autoencoder-style training).

    Args:
        logits: Model output logits (batch, num_classes)
        targets: Ground truth labels (batch,)
        recon: Reconstructed input (batch, input_dim), optional
        inputs: Original input (batch, input_dim), optional
        recon_weight: Weight for reconstruction loss

    Returns:
        Dictionary with loss components
    """
    ce_loss = F.cross_entropy(logits, targets)

    result = {
        'total_loss': ce_loss,
        'ce_loss': ce_loss.item(),
        'recon_loss': 0.0,
        'kl_loss': 0.0,
    }

    if recon is not None and inputs is not None and recon_weight > 0:
        recon_loss = F.mse_loss(recon, inputs)
        result['total_loss'] = ce_loss + recon_weight * recon_loss
        result['recon_loss'] = recon_loss.item()

    return result


def l_rib(logits: torch.Tensor, targets: torch.Tensor,
          kl: torch.Tensor, beta: float = 0.01,
          recon: torch.Tensor = None, inputs: torch.Tensor = None,
          recon_weight: float = 0.0) -> dict:
    """
    Riemannian Information Bottleneck loss (Avadhana Delta, Definition 1.7).

    L_RIB = L_task + β · KL_R[q(S|x) || p_Haar(S)]
         = cross-entropy + β · (tangent-space KL approximation)

    The KL term encourages the representation to:
    - Stay close to the Haar (uniform) prior on the Stiefel manifold
    - Not overfit to task-specific features
    - Maintain information that is predictive of the future

    Args:
        logits: Model output logits (batch, num_classes)
        targets: Ground truth labels (batch,)
        kl: Pre-computed KL divergence from the Stiefel layer
        beta: Trade-off parameter between accuracy and complexity
        recon: Reconstructed input, optional
        inputs: Original input, optional
        recon_weight: Weight for reconstruction loss

    Returns:
        Dictionary with loss components
    """
    ce_loss = F.cross_entropy(logits, targets)

    result = {
        'ce_loss': ce_loss.item(),
        'kl_loss': kl.item() if kl is not None else 0.0,
        'recon_loss': 0.0,
        'beta': beta,
    }

    total_loss = ce_loss + beta * kl if kl is not None else ce_loss

    if recon is not None and inputs is not None and recon_weight > 0:
        recon_loss = F.mse_loss(recon, inputs)
        total_loss = total_loss + recon_weight * recon_loss
        result['recon_loss'] = recon_loss.item()

    result['total_loss'] = total_loss
    return result


def l_vae(logits: torch.Tensor, targets: torch.Tensor,
          mu: torch.Tensor, log_var: torch.Tensor,
          beta: float = 1.0,
          recon: torch.Tensor = None, inputs: torch.Tensor = None,
          recon_weight: float = 0.0) -> dict:
    """
    Standard VAE loss (β-VAE) for the baseline model.

    L_VAE = cross-entropy + β · KL[q(z|x) || p(z)]
    where p(z) = N(0, I) (standard Gaussian prior)

    This serves as a fair comparison to L_RIB: both add a KL regularizer,
    but L_RIB uses the Stiefel/Haar prior while L_VAE uses a Gaussian prior.

    Args:
        logits: Model output logits
        targets: Ground truth labels
        mu: Mean of the latent Gaussian
        log_var: Log variance of the latent Gaussian
        beta: β-VAE weight (1.0 = standard VAE, >1 = disentangled)

    Returns:
        Dictionary with loss components
    """
    ce_loss = F.cross_entropy(logits, targets)

    # Standard Gaussian KL: KL[N(μ, σ²) || N(0, I)]
    kl = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())

    total_loss = ce_loss + beta * kl

    result = {
        'ce_loss': ce_loss.item(),
        'kl_loss': kl.item(),
        'recon_loss': 0.0,
        'beta': beta,
    }

    if recon is not None and inputs is not None and recon_weight > 0:
        recon_loss = F.mse_loss(recon, inputs)
        total_loss = total_loss + recon_weight * recon_loss
        result['recon_loss'] = recon_loss.item()

    result['total_loss'] = total_loss
    return result
