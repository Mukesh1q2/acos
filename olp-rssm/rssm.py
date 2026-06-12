"""
OLP-RSSM: RSSM Variants for Phase 5

Four conditions:
1. Vanilla RSSM       — standard VAE latent space
2. RSSM + β-VAE      — standard VAE with β-weighted KL
3. RSSM + OLP         — Stiefel projection (QR only), no KL
4. RSSM + OLP + KL    — Stiefel projection with β-weighted KL

Architecture: Deterministic path (GRU) + Stochastic path (Gaussian or Stiefel)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
try:
    from .stiefel import StiefelProjection, StiefelFlatten
except ImportError:
    from stiefel import StiefelProjection, StiefelFlatten


class DeterministicPath(nn.Module):
    """
    Deterministic state evolution via GRU.
    h_t = GRU(h_{t-1}, z_{t-1})
    
    This is shared across all 4 conditions.
    """
    
    def __init__(self, hidden_dim: int, latent_dim: int):
        super().__init__()
        self.gru = nn.GRUCell(hidden_dim + latent_dim, hidden_dim)
        self.hidden_dim = hidden_dim
    
    def forward(self, h_prev: torch.Tensor, z_prev: torch.Tensor) -> torch.Tensor:
        """
        Args:
            h_prev: (batch, hidden_dim) previous deterministic state
            z_prev: (batch, latent_dim) previous stochastic state
        Returns:
            h_t: (batch, hidden_dim) next deterministic state
        """
        inp = torch.cat([h_prev, z_prev], dim=-1)
        h_t = self.gru(inp, h_prev)
        return h_t


class GaussianStochastic(nn.Module):
    """
    Standard Gaussian stochastic path.
    Used in Vanilla RSSM and RSSM+β-VAE.
    
    Prior: μ_prior, σ_prior from deterministic state
    Posterior: μ_post, σ_post from deterministic state + observation
    """
    
    def __init__(self, hidden_dim: int, latent_dim: int, obs_dim: int):
        super().__init__()
        self.latent_dim = latent_dim
        
        # Prior network: h_t -> μ, σ
        self.prior_mu = nn.Linear(hidden_dim, latent_dim)
        self.prior_logvar = nn.Linear(hidden_dim, latent_dim)
        
        # Posterior network: (h_t, o_t) -> μ, σ
        self.post_mu = nn.Linear(hidden_dim + obs_dim, latent_dim)
        self.post_logvar = nn.Linear(hidden_dim + obs_dim, latent_dim)
    
    def prior(self, h_t: torch.Tensor):
        mu = self.prior_mu(h_t)
        logvar = self.prior_logvar(h_t)
        logvar = torch.clamp(logvar, -10, 10)
        return mu, logvar
    
    def posterior(self, h_t: torch.Tensor, o_t: torch.Tensor):
        inp = torch.cat([h_t, o_t], dim=-1)
        mu = self.post_mu(inp)
        logvar = self.post_logvar(inp)
        logvar = torch.clamp(logvar, -10, 10)
        return mu, logvar
    
    def sample(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def kl_divergence(self, mu_post: torch.Tensor, logvar_post: torch.Tensor,
                       mu_prior: torch.Tensor, logvar_prior: torch.Tensor) -> torch.Tensor:
        """
        KL[q(z|x) || p(z)] for diagonal Gaussians.
        Per-sample KL (not batch-summed).
        """
        var_post = torch.exp(logvar_post)
        var_prior = torch.exp(logvar_prior)
        
        kl = 0.5 * (
            logvar_prior - logvar_post 
            + (var_post + (mu_post - mu_prior)**2) / var_prior 
            - 1
        )
        return kl.sum(dim=-1)  # Sum over latent dimensions, NOT over batch


class OLPStochastic(nn.Module):
    """
    OLP stochastic path: QR projection onto Stiefel manifold.
    Used in RSSM+OLP and RSSM+OLP+KL.
    
    Instead of sampling from a Gaussian, we:
    1. Generate a raw latent via Gaussian
    2. Project onto St(d,K) via QR decomposition
    3. Flatten back to latent_dim = d*K
    
    This guarantees full-rank representations (no collapse).
    """
    
    def __init__(self, hidden_dim: int, latent_dim: int, obs_dim: int,
                 d_stiefel: int, K_stiefel: int):
        super().__init__()
        self.latent_dim = latent_dim
        self.d_stiefel = d_stiefel
        self.K_stiefel = K_stiefel
        
        assert d_stiefel * K_stiefel == latent_dim, \
            f"latent_dim ({latent_dim}) must equal d*K ({d_stiefel}*{K_stiefel}={d_stiefel*K_stiefel})"
        
        # Prior network: h_t -> raw Stiefel input
        self.prior_raw = nn.Linear(hidden_dim, latent_dim)
        
        # Posterior network: (h_t, o_t) -> raw Stiefel input
        self.post_raw = nn.Linear(hidden_dim + obs_dim, latent_dim)
        
        # Stiefel projection
        self.stiefel = StiefelProjection(d_stiefel, K_stiefel)
        self.stiefel_flat = StiefelFlatten(d_stiefel, K_stiefel)
        
        # For KL computation: we need mu/logvar of the raw Gaussian
        # We model the raw input as Gaussian mean, with learned logvar
        self.prior_logvar = nn.Parameter(torch.zeros(latent_dim))
        self.post_logvar = nn.Parameter(torch.zeros(latent_dim))
    
    def prior(self, h_t: torch.Tensor):
        raw_mu = self.prior_raw(h_t)
        logvar = self.prior_logvar.expand_as(raw_mu)
        logvar = torch.clamp(logvar, -10, 10)
        return raw_mu, logvar
    
    def posterior(self, h_t: torch.Tensor, o_t: torch.Tensor):
        inp = torch.cat([h_t, o_t], dim=-1)
        raw_mu = self.post_raw(inp)
        logvar = self.post_logvar.expand_as(raw_mu)
        logvar = torch.clamp(logvar, -10, 10)
        return raw_mu, logvar
    
    def sample(self, raw_mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """
        Sample raw Gaussian, then project onto Stiefel via QR.
        """
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        raw = raw_mu + eps * std
        
        # QR projection
        S = self.stiefel(raw)
        z = self.stiefel_flat(S)
        return z
    
    def kl_divergence(self, mu_post: torch.Tensor, logvar_post: torch.Tensor,
                       mu_prior: torch.Tensor, logvar_prior: torch.Tensor) -> torch.Tensor:
        """
        KL of the raw Gaussians (before QR projection).
        This is the only honest KL we can compute.
        The actual KL on the Stiefel manifold would require
        the matrix Fisher normalizing constant, which we deliberately
        do NOT implement (see AFM Phase 4.6 finding: L_RIB ≈ β-VAE).
        """
        var_post = torch.exp(logvar_post)
        var_prior = torch.exp(logvar_prior)
        
        kl = 0.5 * (
            logvar_prior - logvar_post
            + (var_post + (mu_post - mu_prior)**2) / var_prior
            - 1
        )
        return kl.sum(dim=-1)


class ObservationEncoder(nn.Module):
    """Encode observation into a flat vector. Works with any image size."""
    
    def __init__(self, in_channels: int = 1, obs_dim: int = 256, image_size: int = 32):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, 32, 4, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, 4, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 128, 4, stride=2, padding=1),
            nn.ReLU(),
        )
        # Compute the spatial size after 3 stride-2 convolutions
        # With padding=1, kernel=4, stride=2: output = (input + 2*1 - 4)/2 + 1 = (input)/2
        # So after 3 layers: input/8
        final_size = image_size // 8
        self.fc = nn.Linear(128 * final_size * final_size, obs_dim)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv(x)
        x = x.view(x.shape[0], -1)
        return self.fc(x)


class ObservationDecoder(nn.Module):
    """Decode latent state into observation reconstruction. Works with any image size."""
    
    def __init__(self, latent_dim: int, hidden_dim: int, out_channels: int = 1,
                 image_size: int = 32):
        super().__init__()
        self.image_size = image_size
        final_size = image_size // 8
        self.fc = nn.Linear(latent_dim + hidden_dim, 128 * final_size * final_size)
        self.deconv = nn.Sequential(
            nn.ConvTranspose2d(128, 64, 4, stride=2, padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(64, 32, 4, stride=2, padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(32, out_channels, 4, stride=2, padding=1),
        )
    
    def forward(self, z: torch.Tensor, h: torch.Tensor) -> torch.Tensor:
        inp = torch.cat([z, h], dim=-1)
        x = self.fc(inp)
        final_size = self.image_size // 8
        x = x.view(x.shape[0], 128, final_size, final_size)
        x = self.deconv(x)
        return x


# ── Composite Models ──────────────────────────────────────────────────────

class VanillaRSSM(nn.Module):
    """
    Condition 1: Vanilla RSSM
    Standard VAE latent space, β=0 (no KL weighting).
    """
    
    def __init__(self, hidden_dim=256, latent_dim=64, obs_dim=256,
                 in_channels=1, out_channels=1, image_size=32):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.condition = "vanilla"
        
        self.encoder = ObservationEncoder(in_channels, obs_dim, image_size)
        self.decoder = ObservationDecoder(latent_dim, hidden_dim, out_channels, image_size)
        self.det_path = DeterministicPath(hidden_dim, latent_dim)
        self.stoch_path = GaussianStochastic(hidden_dim, latent_dim, obs_dim)
    
    def forward(self, obs_seq, training=True):
        """
        Process a sequence of observations.
        
        Args:
            obs_seq: (batch, seq_len, C, H, W)
            training: if True, use posterior; if False, use prior
        
        Returns:
            dict with reconstructions, latents, KL terms
        """
        batch_size, seq_len = obs_seq.shape[:2]
        device = obs_seq.device
        
        # Initialize
        h = torch.zeros(batch_size, self.hidden_dim, device=device)
        z = torch.zeros(batch_size, self.latent_dim, device=device)
        
        reconstructions = []
        kl_terms = []
        z_list = []
        h_list = []
        mu_post_list = []
        mu_prior_list = []
        logvar_post_list = []
        logvar_prior_list = []
        
        for t in range(seq_len):
            o_t = obs_seq[:, t]
            o_enc = self.encoder(o_t)
            
            # Deterministic update
            h = self.det_path(h, z)
            
            # Stochastic path
            mu_prior, logvar_prior = self.stoch_path.prior(h)
            mu_post, logvar_post = self.stoch_path.posterior(h, o_enc)
            
            if training:
                z = self.stoch_path.sample(mu_post, logvar_post)
                kl = self.stoch_path.kl_divergence(mu_post, logvar_post,
                                                     mu_prior, logvar_prior)
                kl_terms.append(kl)
            else:
                z = self.stoch_path.sample(mu_prior, logvar_prior)
            
            # Decode
            recon = self.decoder(z, h)
            reconstructions.append(recon)
            z_list.append(z)
            h_list.append(h)
            mu_post_list.append(mu_post)
            mu_prior_list.append(mu_prior)
            logvar_post_list.append(logvar_post)
            logvar_prior_list.append(logvar_prior)
        
        return {
            'reconstructions': torch.stack(reconstructions, dim=1),
            'kl_terms': torch.stack(kl_terms, dim=1) if kl_terms else None,
            'latents': torch.stack(z_list, dim=1),
            'hiddens': torch.stack(h_list, dim=1),
            'mu_post': torch.stack(mu_post_list, dim=1),
            'mu_prior': torch.stack(mu_prior_list, dim=1),
            'logvar_post': torch.stack(logvar_post_list, dim=1),
            'logvar_prior': torch.stack(logvar_prior_list, dim=1),
        }
    
    def compute_loss(self, obs_seq, beta=0.0):
        """Compute reconstruction + β·KL loss."""
        out = self.forward(obs_seq, training=True)
        
        # Reconstruction loss (MSE per sample)
        recon = out['reconstructions']
        target = obs_seq
        recon_loss = F.mse_loss(recon, target, reduction='none')
        recon_loss = recon_loss.view(recon_loss.shape[0], recon_loss.shape[1], -1).mean(dim=-1)
        
        # KL loss
        if out['kl_terms'] is not None:
            kl_loss = out['kl_terms'].mean(dim=-1)  # Average over time
            total_loss = recon_loss.mean() + beta * kl_loss.mean()
        else:
            kl_loss = torch.tensor(0.0)
            total_loss = recon_loss.mean()
        
        return {
            'total_loss': total_loss,
            'recon_loss': recon_loss.mean(),
            'kl_loss': kl_loss.mean() if isinstance(kl_loss, torch.Tensor) else kl_loss,
        }


class BetaVAE_RSSM(VanillaRSSM):
    """
    Condition 2: RSSM + β-VAE
    Same as Vanilla but with β-weighted KL.
    Just use VanillaRSSM with beta > 0.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.condition = "beta_vae"


class OLP_RSSM(nn.Module):
    """
    Condition 3: RSSM + OLP (QR only)
    Stiefel projection replaces standard Gaussian sampling.
    No KL regularization (beta=0).
    """
    
    def __init__(self, hidden_dim=256, latent_dim=64, obs_dim=256,
                 d_stiefel=16, K_stiefel=4,
                 in_channels=1, out_channels=1, image_size=32):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.d_stiefel = d_stiefel
        self.K_stiefel = K_stiefel
        self.condition = "olp"
        
        assert d_stiefel * K_stiefel == latent_dim
        
        self.encoder = ObservationEncoder(in_channels, obs_dim, image_size)
        self.decoder = ObservationDecoder(latent_dim, hidden_dim, out_channels, image_size)
        self.det_path = DeterministicPath(hidden_dim, latent_dim)
        self.stoch_path = OLPStochastic(hidden_dim, latent_dim, obs_dim,
                                          d_stiefel, K_stiefel)
    
    def forward(self, obs_seq, training=True):
        batch_size, seq_len = obs_seq.shape[:2]
        device = obs_seq.device
        
        h = torch.zeros(batch_size, self.hidden_dim, device=device)
        z = torch.zeros(batch_size, self.latent_dim, device=device)
        
        reconstructions = []
        kl_terms = []
        z_list = []
        h_list = []
        mu_post_list = []
        mu_prior_list = []
        logvar_post_list = []
        logvar_prior_list = []
        
        for t in range(seq_len):
            o_t = obs_seq[:, t]
            o_enc = self.encoder(o_t)
            
            h = self.det_path(h, z)
            
            mu_prior, logvar_prior = self.stoch_path.prior(h)
            mu_post, logvar_post = self.stoch_path.posterior(h, o_enc)
            
            if training:
                z = self.stoch_path.sample(mu_post, logvar_post)
                kl = self.stoch_path.kl_divergence(mu_post, logvar_post,
                                                     mu_prior, logvar_prior)
                kl_terms.append(kl)
            else:
                z = self.stoch_path.sample(mu_prior, logvar_prior)
            
            recon = self.decoder(z, h)
            reconstructions.append(recon)
            z_list.append(z)
            h_list.append(h)
            mu_post_list.append(mu_post)
            mu_prior_list.append(mu_prior)
            logvar_post_list.append(logvar_post)
            logvar_prior_list.append(logvar_prior)
        
        return {
            'reconstructions': torch.stack(reconstructions, dim=1),
            'kl_terms': torch.stack(kl_terms, dim=1) if kl_terms else None,
            'latents': torch.stack(z_list, dim=1),
            'hiddens': torch.stack(h_list, dim=1),
            'mu_post': torch.stack(mu_post_list, dim=1),
            'mu_prior': torch.stack(mu_prior_list, dim=1),
            'logvar_post': torch.stack(logvar_post_list, dim=1),
            'logvar_prior': torch.stack(logvar_prior_list, dim=1),
        }
    
    def compute_loss(self, obs_seq, beta=0.0):
        out = self.forward(obs_seq, training=True)
        
        recon = out['reconstructions']
        target = obs_seq
        recon_loss = F.mse_loss(recon, target, reduction='none')
        recon_loss = recon_loss.view(recon_loss.shape[0], recon_loss.shape[1], -1).mean(dim=-1)
        
        if out['kl_terms'] is not None and beta > 0:
            kl_loss = out['kl_terms'].mean(dim=-1)
            total_loss = recon_loss.mean() + beta * kl_loss.mean()
        else:
            kl_loss = torch.tensor(0.0)
            total_loss = recon_loss.mean()
        
        return {
            'total_loss': total_loss,
            'recon_loss': recon_loss.mean(),
            'kl_loss': kl_loss.mean() if isinstance(kl_loss, torch.Tensor) else kl_loss,
        }


class OLP_KL_RSSM(OLP_RSSM):
    """
    Condition 4: RSSM + OLP + KL
    Same as OLP_RSSM but with β-weighted KL on the raw Gaussian.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.condition = "olp_kl"


# ── Factory ────────────────────────────────────────────────────────────────

CONDITIONS = {
    'vanilla': VanillaRSSM,
    'beta_vae': BetaVAE_RSSM,
    'olp': OLP_RSSM,
    'olp_kl': OLP_KL_RSSM,
}


def build_model(condition: str, hidden_dim=256, latent_dim=64,
                d_stiefel=16, K_stiefel=4, obs_dim=256,
                in_channels=1, out_channels=1, image_size=32) -> nn.Module:
    """
    Build an RSSM model for the given condition.
    """
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}. Choose from {list(CONDITIONS.keys())}")
    
    kwargs = dict(
        hidden_dim=hidden_dim,
        latent_dim=latent_dim,
        obs_dim=obs_dim,
        in_channels=in_channels,
        out_channels=out_channels,
        image_size=image_size,
    )
    
    if condition in ('olp', 'olp_kl'):
        kwargs['d_stiefel'] = d_stiefel
        kwargs['K_stiefel'] = K_stiefel
    
    return CONDITIONS[condition](**kwargs)
