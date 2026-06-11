"""
AFM-Lite Validation Program v0.2 — Extended Models for Ablation Study

Provides 5 configurations for the ablation study:
1. Baseline + L_task (standard encoder, no constraint)
2. Baseline + β-VAE (standard encoder, KL regularization)
3. AFM without QR (encoder + reshape to (d,K), NO Stiefel projection)
4. AFM with QR (encoder + Stiefel projection, no KL)
5. AFM + L_RIB (encoder + Stiefel projection + KL regularization)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from stiefel import StiefelLayer, stiefel_project_qr


class BaselineLTask(nn.Module):
    """Config 1: Baseline encoder, no regularization."""
    
    def __init__(self, input_dim=784, hidden_dim=256, latent_dim=128, num_classes=10):
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
        )
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)
        
        self.classifier = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, num_classes),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )
    
    def forward(self, x, return_latent=False):
        h = self.encoder(x)
        mu, log_var = self.fc_mu(h), self.fc_logvar(h)
        if self.training:
            z = mu + torch.exp(0.5 * log_var) * torch.randn_like(mu)
        else:
            z = mu
        logits = self.classifier(z)
        recon = self.decoder(z)
        if return_latent:
            return logits, recon, z, mu, log_var
        return logits, recon, mu, log_var
    
    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class BaselineBetaVAE(nn.Module):
    """Config 2: Baseline encoder with β-VAE KL regularization."""
    # Same architecture as BaselineLTask, but loss includes KL term
    # We use the same model class; the loss function adds KL
    pass  # Use BaselineLTask with VAE loss


class AFMWithoutQR(nn.Module):
    """Config 3: Encoder outputs (d,K) matrix but NO Stiefel projection.
    
    This tests whether the constraint itself matters, vs just the reshape.
    The latent is reshaped to (d,K) but left unconstrained.
    Decoder receives the raw (d,K) matrix flattened.
    """
    
    def __init__(self, input_dim=784, hidden_dim=256, d=32, K=4, num_classes=10):
        super().__init__()
        self.input_dim = input_dim
        self.d = d
        self.K = K
        self.latent_dim = d * K
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
        )
        self.fc_mu = nn.Linear(hidden_dim, d * K)
        self.fc_logvar = nn.Linear(hidden_dim, d * K)
        
        self.classifier = nn.Sequential(
            nn.Linear(d * K, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, num_classes),
        )
        self.decoder = nn.Sequential(
            nn.Linear(d * K, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )
    
    def forward(self, x, return_latent=False):
        h = self.encoder(x)
        mu, log_var = self.fc_mu(h), self.fc_logvar(h)
        
        if self.training:
            A = mu + torch.exp(0.5 * log_var) * torch.randn_like(mu)
        else:
            A = mu
        
        # Reshape to (d, K) but DO NOT project to Stiefel
        A_matrix = A.view(A.shape[0], self.d, self.K)
        latent = A_matrix.reshape(A.shape[0], -1)  # Flatten back
        
        logits = self.classifier(latent)
        recon = self.decoder(latent)
        
        if return_latent:
            return logits, recon, A_matrix, mu, log_var
        return logits, recon, mu, log_var
    
    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class AFMWithQR(nn.Module):
    """Config 4: Encoder + Stiefel projection (QR), no KL regularization.
    
    This tests the Stiefel constraint alone, without L_RIB.
    """
    
    def __init__(self, input_dim=784, hidden_dim=256, d=32, K=4, num_classes=10):
        super().__init__()
        self.input_dim = input_dim
        self.d = d
        self.K = K
        self.latent_dim = d * K
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
        )
        self.fc_mu = nn.Linear(hidden_dim, d * K)
        self.fc_logvar = nn.Linear(hidden_dim, d * K)
        
        self.stiefel = StiefelLayer(d=d, K=K, stochastic=True)
        
        self.classifier = nn.Sequential(
            nn.Linear(d * K, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, num_classes),
        )
        self.decoder = nn.Sequential(
            nn.Linear(d * K, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )
    
    def forward(self, x, return_latent=False):
        h = self.encoder(x)
        mu, log_var = self.fc_mu(h), self.fc_logvar(h)
        S, kl = self.stiefel(mu, log_var)
        S_flat = S.reshape(S.shape[0], -1)
        
        logits = self.classifier(S_flat)
        recon = self.decoder(S_flat)
        
        if return_latent:
            return logits, recon, S, mu, log_var, kl
        return logits, recon, mu, log_var, kl
    
    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class AFMWithRIB(nn.Module):
    """Config 5: Encoder + Stiefel projection + L_RIB (KL regularization).
    
    Full AFM-Lite model as used in v0.1.
    """
    
    def __init__(self, input_dim=784, hidden_dim=256, d=32, K=4, num_classes=10):
        super().__init__()
        self.input_dim = input_dim
        self.d = d
        self.K = K
        self.latent_dim = d * K
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
        )
        self.fc_mu = nn.Linear(hidden_dim, d * K)
        self.fc_logvar = nn.Linear(hidden_dim, d * K)
        
        self.stiefel = StiefelLayer(d=d, K=K, stochastic=True)
        
        self.classifier = nn.Sequential(
            nn.Linear(d * K, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, num_classes),
        )
        self.decoder = nn.Sequential(
            nn.Linear(d * K, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )
    
    def forward(self, x, return_latent=False):
        h = self.encoder(x)
        mu, log_var = self.fc_mu(h), self.fc_logvar(h)
        S, kl = self.stiefel(mu, log_var)
        S_flat = S.reshape(S.shape[0], -1)
        
        logits = self.classifier(S_flat)
        recon = self.decoder(S_flat)
        
        if return_latent:
            return logits, recon, S, mu, log_var, kl
        return logits, recon, mu, log_var, kl
    
    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def get_model(config_name, input_dim=784, hidden_dim=256, latent_dim=128,
              d=32, K=4, num_classes=10):
    """Factory function to create models by config name."""
    if config_name == 'baseline_task':
        return BaselineLTask(input_dim, hidden_dim, latent_dim, num_classes)
    elif config_name == 'baseline_vae':
        return BaselineLTask(input_dim, hidden_dim, latent_dim, num_classes)
    elif config_name == 'afm_no_qr':
        return AFMWithoutQR(input_dim, hidden_dim, d, K, num_classes)
    elif config_name == 'afm_qr':
        return AFMWithQR(input_dim, hidden_dim, d, K, num_classes)
    elif config_name == 'afm_rib':
        return AFMWithRIB(input_dim, hidden_dim, d, K, num_classes)
    else:
        raise ValueError(f"Unknown config: {config_name}")


def compute_loss(model, config_name, logits, targets, mu=None, log_var=None,
                 kl=None, beta=0.0, recon=None, inputs=None, recon_weight=0.0):
    """Compute loss for any model configuration."""
    ce = F.cross_entropy(logits, targets)
    
    if config_name == 'baseline_task':
        return ce
    
    elif config_name == 'baseline_vae':
        if mu is not None and log_var is not None and beta > 0:
            kl_vae = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp(), dim=-1).mean()
            return ce + beta * kl_vae
        return ce
    
    elif config_name == 'afm_no_qr':
        # No KL, no Stiefel - just task loss
        # But can optionally add KL in pre-reshape space
        if mu is not None and log_var is not None and beta > 0:
            kl_vae = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp(), dim=-1).mean()
            return ce + beta * kl_vae
        return ce
    
    elif config_name == 'afm_qr':
        # Stiefel projection but no KL weight
        return ce
    
    elif config_name == 'afm_rib':
        if kl is not None and beta > 0:
            return ce + beta * kl
        return ce
    
    return ce


if __name__ == "__main__":
    # Quick sanity check
    x = torch.randn(16, 784)
    
    configs = ['baseline_task', 'afm_no_qr', 'afm_qr', 'afm_rib']
    for cfg in configs:
        model = get_model(cfg)
        params = model.count_parameters()
        
        if cfg in ['afm_qr', 'afm_rib']:
            logits, recon, mu, lv, kl = model(x)
            print(f"{cfg}: params={params:,}, logits={logits.shape}, kl={kl.item():.4f}")
        else:
            logits, recon, mu, lv = model(x)
            print(f"{cfg}: params={params:,}, logits={logits.shape}")
