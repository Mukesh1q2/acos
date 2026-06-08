"""
Stiefel Manifold Operations for AFM-Lite

Implements the core mathematical operations on the Stiefel manifold St(d, K)
as defined in the Avadhana Delta paper.

St(d, K) = { S ∈ R^{d×K} : S^T S = I_K }

Key operations:
- Projection via QR decomposition (retraction)
- Cayley retraction for smooth updates
- Geodesic distance (principal angles)
- Thread orthogonality measurement
"""

import torch
import torch.nn as nn
import math


def stiefel_project_qr(A: torch.Tensor) -> torch.Tensor:
    """
    Project a matrix A ∈ R^{d×K} onto the Stiefel manifold St(d, K)
    using QR decomposition with sign correction.

    This is the standard retraction: Retr(A) = qf(A) where qf extracts
    the Q factor with positive diagonal of R.

    Supports both single matrix (d, K) and batched (batch, d, K) inputs.
    Uses vectorized torch.linalg.qr for batched inputs.

    Args:
        A: Matrix of shape (batch, d, K) or (d, K)

    Returns:
        S: Orthogonal matrix on St(d, K), same shape as input
    """
    Q, R = torch.linalg.qr(A)

    # Sign correction: ensure diagonal of R is positive
    # This makes the retraction well-defined (unique Q)
    if A.dim() == 2:
        signs = torch.sign(torch.diag(R))
        signs[signs == 0] = 1
        Q = Q * signs.unsqueeze(0)
    else:
        # Batched: R has shape (batch, K, K), diagonal per batch
        diag_R = torch.diagonal(R, dim1=-2, dim2=-1)  # (batch, K)
        signs = torch.sign(diag_R)  # (batch, K)
        signs[signs == 0] = 1
        Q = Q * signs.unsqueeze(1)  # Broadcast over d dimension

    return Q


def stiefel_project_cayley(W: torch.Tensor, S_ref: torch.Tensor) -> torch.Tensor:
    """
    Cayley retraction on the Stiefel manifold.

    Given a tangent vector V ∈ T_S St(d,K), where V = WS - S(W^T S) for
    skew-symmetric parameterization, compute:
        Retr_S(V) = (I - V/2)^{-1}(I + V/2) @ S

    Args:
        W: Skew-symmetric parameter matrix (d, d) or (batch, d, d)
        S_ref: Current point on St(d, K) (d, K) or (batch, d, K)

    Returns:
        New point on St(d, K)
    """
    V = W @ S_ref  # Tangent vector in T_S St(d,K)
    I = torch.eye(V.shape[-2], device=V.device, dtype=V.dtype)
    if V.dim() == 3:
        I = I.unsqueeze(0).expand(V.shape[0], -1, -1)

    # Cayley retraction: S_new = (I - V/2)^{-1} @ (I + V/2) @ S_ref
    # Solve (I - V/2) @ X = (I + V/2) @ S_ref
    lhs = I - V / 2
    rhs = (I + V / 2) @ S_ref
    S_new = torch.linalg.solve(lhs, rhs)
    return S_new


def stiefel_distance(S1: torch.Tensor, S2: torch.Tensor) -> torch.Tensor:
    """
    Compute the geodesic distance between two points on St(d, K).

    Uses principal angles: d_R(S1, S2) = ||θ||_2
    where cos(θ_i) = σ_i(S1^T S2) are the singular values of S1^T S2.

    Args:
        S1: Point on St(d, K), shape (d, K) or (batch, d, K)
        S2: Point on St(d, K), same shape

    Returns:
        Geodesic distance (scalar or batch)
    """
    M = S1.transpose(-2, -1) @ S2  # (K, K) or (batch, K, K)
    # Singular values = cosines of principal angles
    singular_values = torch.linalg.svdvals(M)  # (K,) or (batch, K)
    # Clamp to [0, 1] for numerical stability
    cos_angles = torch.clamp(singular_values, -1.0, 1.0)
    angles = torch.acos(cos_angles)  # Principal angles in [0, pi/2]
    # Geodesic distance = Frobenius norm of angle vector
    distance = torch.norm(angles, dim=-1)
    return distance


def thread_orthogonality(S: torch.Tensor) -> dict:
    """
    Measure orthogonality of thread states in a Stiefel matrix.

    For S ∈ St(d, K), compute S^T S and measure how close it is to I_K.

    Args:
        S: Stiefel matrix, shape (d, K) or (batch, d, K)

    Returns:
        Dictionary with:
        - 'gram': S^T S (should be I_K for perfect orthogonality)
        - 'orthogonality_error': ||S^T S - I_K||_F
        - 'thread_dot_products': off-diagonal elements of S^T S
        - 'min_singular_value': minimum singular value of S^T S
    """
    if S.dim() == 2:
        gram = S.T @ S  # (K, K)
    else:
        # For batch, take mean
        grams = []
        for i in range(S.shape[0]):
            grams.append(S[i].T @ S[i])
        gram = torch.stack(grams).mean(0)

    K = gram.shape[0]
    I_K = torch.eye(K, device=gram.device, dtype=gram.dtype)

    orth_error = torch.norm(gram - I_K, p='fro').item()

    # Off-diagonal elements (inter-thread dot products)
    off_diag = gram.clone()
    off_diag.fill_diagonal_(0)
    thread_dots = off_diag[off_diag != 0].tolist() if off_diag.numel() > K else []

    # Minimum singular value
    sv = torch.linalg.svdvals(gram)
    min_sv = sv.min().item()
    max_sv = sv.max().item()

    return {
        'gram': gram.detach(),
        'orthogonality_error': orth_error,
        'thread_dot_products': thread_dots,
        'min_singular_value': min_sv,
        'max_singular_value': max_sv,
        'condition_number': max_sv / max(min_sv, 1e-10),
    }


def stiefel_kl_complexity(mu: torch.Tensor, log_var: torch.Tensor, d: int, K: int) -> torch.Tensor:
    """
    Compute the KL divergence KL[q(S|x) || p_Haar(S)] using the tangent-space
    Gaussian approximation from the Avadhana Delta paper (Definition 1.7).

    The practical approximation (from Section 1.5):
        KL_R[q || p_Haar] ≈ (1/2)[tr(Σ) + ||μ||² − K − log det(Σ)]

    Since we parameterize the pre-projection space as Gaussian with mean μ and
    variance σ², this becomes the standard Gaussian KL:
        KL = (1/2) * [Σ σ²_i + Σ μ²_i - D - Σ log(σ²_i)]

    where D = d * K is the dimensionality of the pre-projection space.

    CRITICAL: Computed PER SAMPLE, then averaged over batch.
    This matches the standard VAE KL computation.

    This is an approximation to the true Riemannian KL, valid when the
    variance is small (concentrated distribution near the Stiefel point).

    Args:
        mu: Mean of the pre-projection Gaussian, shape (batch, d*K)
        log_var: Log variance, same shape as mu
        d: Stiefel manifold dimension
        K: Number of threads

    Returns:
        KL divergence (scalar, averaged over batch)
    """
    D = d * K  # Latent dimensionality per sample
    # Per-sample KL: KL[N(μ, σ²) || N(0, I)] for D-dimensional Gaussian
    # = 0.5 * sum_d(mu_d^2 + sigma_d^2 - 1 - log(sigma_d^2))
    kl_per_sample = 0.5 * torch.sum(
        mu ** 2 + torch.exp(log_var) - 1 - log_var,
        dim=-1  # Sum over latent dimensions, keep batch dim
    )
    return kl_per_sample.mean()  # Average over batch


def skew_symmetric(A: torch.Tensor) -> torch.Tensor:
    """
    Convert a matrix to skew-symmetric form: W = (A - A^T) / 2

    Args:
        A: Square matrix (d, d) or (batch, d, d)

    Returns:
        Skew-symmetric matrix W
    """
    return (A - A.transpose(-2, -1)) / 2


class StiefelLayer(nn.Module):
    """
    Stiefel Projection Layer for AFM-Lite.

    Takes a latent vector, reshapes it to a (d, K) matrix,
    and projects onto the Stiefel manifold using QR decomposition.

    For the stochastic variant (used with L_RIB), the encoder outputs
    both mean and log-variance, and we use the reparameterization trick
    before projection.

    Architecture:
        Input (dim_in) → reshape to (d, K) → QR projection → St(d, K)

    The QR projection is differentiable (PyTorch autograd supports it),
    so gradients flow through the Stiefel constraint.
    """

    def __init__(self, d: int, K: int, stochastic: bool = True):
        """
        Args:
            d: Dimension of the Stiefel manifold (rows)
            K: Number of threads (columns)
            stochastic: If True, output mean and log_var for L_RIB
        """
        super().__init__()
        self.d = d
        self.K = K
        self.stochastic = stochastic

    def forward(self, mu: torch.Tensor, log_var: torch.Tensor = None):
        """
        Project onto the Stiefel manifold.

        Args:
            mu: Mean matrix, shape (batch, d*K) or (batch, d, K)
            log_var: Log variance, same shape (only used if stochastic)

        Returns:
            S: Stiefel matrix (batch, d, K)
            kl: KL divergence (scalar, only if stochastic)
        """
        batch_size = mu.shape[0]

        # Reshape to matrix form
        if mu.dim() == 2:
            A = mu.view(batch_size, self.d, self.K)
        else:
            A = mu

        if self.stochastic and log_var is not None and self.training:
            # Reparameterization trick in pre-projection space
            std = torch.exp(0.5 * log_var)
            if log_var.dim() == 2:
                std = std.view(batch_size, self.d, self.K)
            eps = torch.randn_like(std)
            A = A + std * eps

        # QR projection onto Stiefel manifold
        S = stiefel_project_qr(A)

        # Compute KL if stochastic
        kl = None
        if self.stochastic and log_var is not None:
            kl = stiefel_kl_complexity(
                mu.view(batch_size, -1),
                log_var.view(batch_size, -1),
                self.d, self.K
            )

        return S, kl
