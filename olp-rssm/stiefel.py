"""
OLP-RSSM: Stiefel Manifold Projection via QR Decomposition

This is the surviving mechanism from AFM-Lite Phase 4.6.
QR projection maps any non-degenerate matrix to the Stiefel manifold St(d,K).
This guarantees a full-rank representation, preventing posterior collapse.

No RIB. No Haar priors. No manifold-specific losses.
Just QR decomposition. That's it.
"""

import torch
import torch.nn as nn


class StiefelProjection(nn.Module):
    """
    Projects a latent vector onto the Stiefel manifold St(d, K) via QR decomposition.
    
    Input: z of shape (batch, d*K)
    Output: S of shape (batch, d, K) where S^T S = I_K
    
    The QR decomposition ensures:
    1. The output is always on the Stiefel manifold
    2. The representation is always full-rank (no collapse)
    3. Gradients flow through via autograd
    """
    
    def __init__(self, d: int, K: int):
        super().__init__()
        self.d = d
        self.K = K
    
    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """
        Args:
            z: (batch, d*K) raw latent representation
        Returns:
            S: (batch, d, K) Stiefel manifold point
        """
        batch_size = z.shape[0]
        # Reshape to matrix
        M = z.view(batch_size, self.d, self.K)
        
        # QR decomposition
        Q, R = torch.linalg.qr(M, mode='reduced')
        
        # Ensure consistent sign (diagonal of R should be positive)
        # This prevents sign ambiguity in QR decomposition
        diag_sign = torch.sign(torch.diagonal(R, dim1=-2, dim2=-1))
        # Handle zero diagonals
        diag_sign = torch.where(
            diag_sign == 0, 
            torch.ones_like(diag_sign), 
            diag_sign
        )
        Q = Q * diag_sign.unsqueeze(1)  # Broadcast across rows
        
        return Q


class StiefelFlatten(nn.Module):
    """
    Flattens Stiefel point for downstream processing.
    (batch, d, K) -> (batch, d*K)
    """
    
    def __init__(self, d: int, K: int):
        super().__init__()
        self.d = d
        self.K = K
    
    def forward(self, S: torch.Tensor) -> torch.Tensor:
        return S.reshape(S.shape[0], self.d * self.K)
