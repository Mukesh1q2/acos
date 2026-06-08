"""
AFM-Lite Model Definitions

Baseline:    Encoder → latent z ∈ R^D → Decoder/Classifier
AFM-Lite:    Encoder → Stiefel projection → OTM thread state S ∈ St(d,K) → Decoder/Classifier

Both models have matched parameter counts for fair comparison.
Target: 100k – 1M parameters.
CPU-friendly architecture.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from stiefel import StiefelLayer, stiefel_project_qr, thread_orthogonality


class BaselineModel(nn.Module):
    """
    Baseline model: Encoder → flat latent → Decoder/Classifier

    Architecture:
        Encoder: Linear(input_dim, hidden) → ReLU → Linear(hidden, latent_dim)
        Decoder: Linear(latent_dim, hidden) → ReLU → Linear(hidden, num_classes)

    The latent space is unconstrained (standard Euclidean).
    """

    def __init__(self, input_dim: int = 784, hidden_dim: int = 256,
                 latent_dim: int = 128, num_classes: int = 10):
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.num_classes = num_classes

        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

        # Classifier head
        self.classifier = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_classes),
        )

        # Reconstruction head (for representation quality analysis)
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )

    def encode(self, x: torch.Tensor):
        h = self.encoder(x)
        mu = self.fc_mu(h)
        log_var = self.fc_logvar(h)
        return mu, log_var

    def reparameterize(self, mu: torch.Tensor, log_var: torch.Tensor):
        if self.training:
            std = torch.exp(0.5 * log_var)
            eps = torch.randn_like(std)
            return mu + eps * std
        return mu

    def forward(self, x: torch.Tensor, return_latent: bool = False):
        mu, log_var = self.encode(x)
        z = self.reparameterize(mu, log_var)
        logits = self.classifier(z)
        recon = self.decoder(z)

        if return_latent:
            return logits, recon, z, mu, log_var
        return logits, recon, mu, log_var

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class AFMLiteModel(nn.Module):
    """
    AFM-Lite: Encoder → Stiefel projection → OTM thread state → Decoder/Classifier

    Architecture:
        Encoder: Linear(input_dim, hidden) → ReLU → Linear(hidden, d*K*2)
        Stiefel: Reshape to (d, K), QR projection → S ∈ St(d, K)
        Decoder: Flatten S → Linear(d*K, hidden) → ReLU → Linear(hidden, num_classes)

    The key difference from baseline: the latent space is constrained to the
    Stiefel manifold, enforcing orthogonality between thread states.
    """

    def __init__(self, input_dim: int = 784, hidden_dim: int = 256,
                 d: int = 32, K: int = 4, num_classes: int = 10):
        super().__init__()
        self.input_dim = input_dim
        self.d = d
        self.K = K
        self.latent_dim = d * K  # Match baseline latent size
        self.num_classes = num_classes

        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        # Output mean and log-var for the pre-projection Gaussian
        self.fc_mu = nn.Linear(hidden_dim, d * K)
        self.fc_logvar = nn.Linear(hidden_dim, d * K)

        # Stiefel projection layer
        self.stiefel = StiefelLayer(d=d, K=K, stochastic=True)

        # Classifier head (from flattened Stiefel matrix)
        self.classifier = nn.Sequential(
            nn.Linear(d * K, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_classes),
        )

        # Reconstruction head
        self.decoder = nn.Sequential(
            nn.Linear(d * K, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )

    def encode(self, x: torch.Tensor):
        h = self.encoder(x)
        mu = self.fc_mu(h)
        log_var = self.fc_logvar(h)
        return mu, log_var

    def forward(self, x: torch.Tensor, return_latent: bool = False):
        mu, log_var = self.encode(x)
        S, kl = self.stiefel(mu, log_var)

        # Flatten Stiefel matrix for decoder
        S_flat = S.reshape(S.shape[0], -1)  # (batch, d*K)

        logits = self.classifier(S_flat)
        recon = self.decoder(S_flat)

        if return_latent:
            return logits, recon, S, mu, log_var, kl
        return logits, recon, mu, log_var, kl

    def get_thread_orthogonality(self, x: torch.Tensor) -> dict:
        """Compute thread orthogonality for a batch of inputs."""
        mu, log_var = self.encode(x)
        S, _ = self.stiefel(mu, log_var)
        # Average over batch
        S_mean = S.mean(dim=0)  # (d, K)
        return thread_orthogonality(S_mean)

    def get_thread_interference(self, x: torch.Tensor) -> list:
        """
        Compute pairwise dot products between thread states.

        Returns list of dot(S_i, S_j) for all i < j pairs.
        """
        mu, log_var = self.encode(x)
        S, _ = self.stiefel(mu, log_var)
        batch_size = S.shape[0]

        interferences = []
        for i in range(self.K):
            for j in range(i + 1, self.K):
                # S[:, :, i] and S[:, :, j] are thread states (batch, d)
                dot = torch.sum(S[:, :, i] * S[:, :, j], dim=-1)  # (batch,)
                interferences.append(dot.mean().item())

        return interferences

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class MultiTaskBaseline(nn.Module):
    """
    Multi-task variant of the baseline model with separate task heads.
    """

    def __init__(self, input_dim: int = 784, hidden_dim: int = 256,
                 latent_dim: int = 128, task_classes: list = None):
        super().__init__()
        if task_classes is None:
            task_classes = [10, 10, 10]

        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.num_tasks = len(task_classes)

        # Shared encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

        # Task-specific heads
        self.heads = nn.ModuleList()
        for nc in task_classes:
            self.heads.append(nn.Sequential(
                nn.Linear(latent_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, nc),
            ))

    def forward(self, x: torch.Tensor, task_id: int = 0):
        h = self.encoder(x)
        mu = self.fc_mu(h)
        log_var = self.fc_logvar(h)

        if self.training:
            std = torch.exp(0.5 * log_var)
            eps = torch.randn_like(std)
            z = mu + eps * std
        else:
            z = mu

        logits = self.heads[task_id](z)
        return logits, mu, log_var

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class MultiTaskAFMLite(nn.Module):
    """
    Multi-task variant of AFM-Lite with separate task heads.
    Each task is assigned a dedicated thread in the OTM representation.
    """

    def __init__(self, input_dim: int = 784, hidden_dim: int = 256,
                 d: int = 32, K: int = 4, task_classes: list = None):
        super().__init__()
        if task_classes is None:
            task_classes = [10, 10, 10]

        self.input_dim = input_dim
        self.d = d
        self.K = K
        self.latent_dim = d * K
        self.num_tasks = len(task_classes)

        # Shared encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.fc_mu = nn.Linear(hidden_dim, d * K)
        self.fc_logvar = nn.Linear(hidden_dim, d * K)

        # Stiefel projection
        self.stiefel = StiefelLayer(d=d, K=K, stochastic=True)

        # Task-specific heads (each uses ALL thread states)
        self.heads = nn.ModuleList()
        for nc in task_classes:
            self.heads.append(nn.Sequential(
                nn.Linear(d * K, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, nc),
            ))

    def forward(self, x: torch.Tensor, task_id: int = 0):
        h = self.encoder(x)
        mu = self.fc_mu(h)
        log_var = self.fc_logvar(h)

        S, kl = self.stiefel(mu, log_var)
        S_flat = S.reshape(S.shape[0], -1)

        logits = self.heads[task_id](S_flat)
        return logits, mu, log_var, kl

    def get_thread_orthogonality(self, x: torch.Tensor) -> dict:
        mu, log_var = self.fc_mu(self.encoder(x)), self.fc_logvar(self.encoder(x))
        S, _ = self.stiefel(mu, log_var)
        S_mean = S.mean(dim=0)
        return thread_orthogonality(S_mean)

    def get_thread_interference(self, x: torch.Tensor) -> list:
        mu, log_var = self.fc_mu(self.encoder(x)), self.fc_logvar(self.encoder(x))
        S, _ = self.stiefel(mu, log_var)
        interferences = []
        for i in range(self.K):
            for j in range(i + 1, self.K):
                dot = torch.sum(S[:, :, i] * S[:, :, j], dim=-1)
                interferences.append(dot.mean().item())
        return interferences

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def print_model_summary(model: nn.Module, name: str):
    """Print model architecture summary."""
    total = model.count_parameters()
    print(f"\n{'='*60}")
    print(f"Model: {name}")
    print(f"{'='*60}")
    print(model)
    print(f"\nTotal parameters: {total:,}")
    print(f"Parameter range: {'100k-1M ✓' if 100_000 <= total <= 1_000_000 else 'OUT OF RANGE ✗'}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Quick sanity check
    print("Testing model architectures...")

    baseline = BaselineModel(input_dim=784, hidden_dim=256, latent_dim=128, num_classes=10)
    afm = AFMLiteModel(input_dim=784, hidden_dim=256, d=32, K=4, num_classes=10)

    print_model_summary(baseline, "Baseline")
    print_model_summary(afm, "AFM-Lite")

    # Test forward pass
    x = torch.randn(16, 784)
    with torch.no_grad():
        logits_b, recon_b, mu_b, lv_b = baseline(x)
        logits_a, recon_a, mu_a, lv_a, kl_a = afm(x)

    print(f"Baseline output shape: {logits_b.shape}")
    print(f"AFM-Lite output shape: {logits_a.shape}")
    print(f"AFM-Lite KL: {kl_a.item():.4f}")

    # Test thread orthogonality
    orth = afm.get_thread_orthogonality(x)
    print(f"Thread orthogonality error: {orth['orthogonality_error']:.6f}")
    print(f"Thread dot products: {orth['thread_dot_products']}")
