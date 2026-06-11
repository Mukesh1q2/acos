#!/usr/bin/env python3
"""
AFM-RSSM: Recurrent State-Space Model Comparison
==================================================

Builds a minimal RSSM (Recurrent State-Space Model) world model prototype
to compare against AFM. Tests whether Stiefel projection can replace the
stochastic state in a recurrent model.

Architecture:
  - Encoder: Linear(784, 256) -> ReLU -> Linear(256, 64) (deterministic state)
  - Prior: Linear(64, 32) (stochastic state prior mu, logvar)
  - Posterior: Linear(64+32, 32) (stochastic state posterior mu, logvar given observation)
  - RSSM transition: GRU(64+32, 64) (recurrent state update)
  - Decoder: Linear(64+32, 256) -> ReLU -> Linear(256, 784)
  - Classifier: Linear(64+32, 10)

Models compared:
  1. GRU Baseline: Encoder -> GRU -> Classifier (no stochastic state)
  2. Vanilla RSSM: Encoder -> RSSM -> Decoder/Classifier
  3. AFM-RSSM: Replace RSSM stochastic state with Stiefel projection

Task:
  - Sequential prediction on MNIST: sequences of 5 consecutive digits
    from the same class
  - Given z(t), predict z(t+1) and classify the digit

Metrics:
  - Prediction loss (MSE of z(t+1) prediction)
  - Classification accuracy
  - Representation stability (cosine sim of states across timesteps)

Output:
  - results_v02/rssm_results.json
  - /home/z/my-project/AFM_RSSM_REPORT.md

Usage:
  python /home/z/my-project/afm-lite/run_rssm.py
"""

import sys
sys.path.insert(0, '/home/z/my-project/afm-lite')

import os
import json
import time
import pickle
import warnings
from collections import defaultdict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

from stiefel import StiefelLayer, stiefel_project_qr, stiefel_kl_complexity, thread_orthogonality

# ---------------------------------------------------------------------------
# Global configuration
# ---------------------------------------------------------------------------
DEVICE = 'cpu'
RESULTS_DIR = '/home/z/my-project/afm-lite/results_v02'
CACHE_DIR = '/home/z/my-project/afm-lite/.cache'
REPORT_PATH = '/home/z/my-project/AFM_RSSM_REPORT.md'

# Architecture
ENCODER_HIDDEN = 256
DET_STATE_DIM = 64
STOCH_STATE_DIM = 32  # 16 for mu + 16 for logvar
COMBINED_DIM = DET_STATE_DIM + STOCH_STATE_DIM  # 96
DECODER_HIDDEN = 256
NUM_CLASSES = 10
INPUT_DIM = 784

# AFM-RSSM specific
AFM_D = 8       # Stiefel manifold row dimension
AFM_K = 4       # Stiefel manifold column dimension (= number of threads)
AFM_STOCH_DIM = AFM_D * AFM_K  # 32 — matches STOCH_STATE_DIM

# Sequential task
SEQ_LENGTH = 5
BATCH_SIZE = 128
EPOCHS = 15
LR = 1e-3
BETA_KL = 0.01   # KL weight
SEED = 42


# ===========================================================================
# Utility helpers
# ===========================================================================

def numpy_safe(obj):
    """Recursively convert numpy types for JSON serialization."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.float32, np.float64, np.floating)):
        return float(obj)
    if isinstance(obj, (np.int32, np.int64, np.integer)):
        return int(obj)
    if isinstance(obj, dict):
        return {k: numpy_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [numpy_safe(v) for v in obj]
    if isinstance(obj, torch.Tensor):
        return numpy_safe(obj.detach().cpu().numpy())
    return obj


def save_json(name, data):
    """Save results dict to JSON in results directory."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f'{name}.json')
    with open(path, 'w') as f:
        json.dump(numpy_safe(data), f, indent=2, default=str)
    print(f"  [SAVE] {path}")
    return path


def set_seed(seed):
    """Set random seed for reproducibility."""
    torch.manual_seed(seed)
    np.random.seed(seed)


# ===========================================================================
# Sequential MNIST dataset
# ===========================================================================

def create_sequential_mnist(batch_size=128, seq_length=5, seed=42):
    """
    Create sequential MNIST dataset where each 'sequence' is `seq_length`
    consecutive digits from the same class.

    For each class, we sort digits by index and create sliding windows.
    Task: given z(t), predict z(t+1) and classify the digit.

    Returns:
        train_loader, test_loader (each yields (X_seq, y_seq) of shape
        (batch, seq_length, 784) and (batch, seq_length))
    """
    cache_path = os.path.join(CACHE_DIR, 'mnist.pkl')

    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
        X_train, y_train = data['X_train'], data['y_train']
        X_test, y_test = data['X_test'], data['y_test']
    else:
        print("  Downloading MNIST via fetch_openml...")
        from sklearn.datasets import fetch_openml
        mnist = fetch_openml('mnist_784', version=1, as_frame=False)
        X, y = mnist.data.astype(np.float32), mnist.target.astype(int)
        X_train, X_test = X[:60000], X[60000:]
        y_train, y_test = y[:60000], y[60000:]
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump({'X_train': X_train, 'y_train': y_train,
                         'X_test': X_test, 'y_test': y_test}, f)

    X_train = X_train.astype(np.float32) / 255.0
    X_test = X_test.astype(np.float32) / 255.0

    def build_sequences(X, y, seq_length, seed):
        """Build sequences of same-class digits."""
        rng = np.random.RandomState(seed)
        sequences_x = []
        sequences_y = []

        # Group indices by class
        class_indices = {}
        for i, label in enumerate(y):
            label = int(label)
            if label not in class_indices:
                class_indices[label] = []
            class_indices[label].append(i)

        # Create sequences from each class
        for label, indices in class_indices.items():
            # Shuffle within class for variety
            indices = rng.permutation(indices).tolist()
            # Create sliding windows
            n_seqs = len(indices) // seq_length
            for s in range(n_seqs):
                seq_idx = indices[s * seq_length : (s + 1) * seq_length]
                seq_x = X[seq_idx]  # (seq_length, 784)
                seq_y = np.array([y[i] for i in seq_idx], dtype=np.int64)
                sequences_x.append(seq_x)
                sequences_y.append(seq_y)

        return np.array(sequences_x, dtype=np.float32), np.array(sequences_y, dtype=np.int64)

    print("  Building sequential training data...")
    train_seq_x, train_seq_y = build_sequences(X_train, y_train, seq_length, seed)
    print("  Building sequential test data...")
    test_seq_x, test_seq_y = build_sequences(X_test, y_test, seq_length, seed + 1)

    print(f"  Train sequences: {len(train_seq_x)}, Test sequences: {len(test_seq_x)}")
    print(f"  Sequence shape: {train_seq_x.shape}, Label shape: {train_seq_y.shape}")

    # Cap to max sequences for manageable training time
    MAX_TRAIN = 20000
    MAX_TEST = 4000
    if len(train_seq_x) > MAX_TRAIN:
        sel = np.random.RandomState(seed).choice(len(train_seq_x), MAX_TRAIN, replace=False)
        train_seq_x = train_seq_x[sel]
        train_seq_y = train_seq_y[sel]
    if len(test_seq_x) > MAX_TEST:
        sel = np.random.RandomState(seed + 1).choice(len(test_seq_x), MAX_TEST, replace=False)
        test_seq_x = test_seq_x[sel]
        test_seq_y = test_seq_y[sel]

    train_ds = TensorDataset(
        torch.FloatTensor(train_seq_x),
        torch.LongTensor(train_seq_y),
    )
    test_ds = TensorDataset(
        torch.FloatTensor(test_seq_x),
        torch.LongTensor(test_seq_y),
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    return train_loader, test_loader


# ===========================================================================
# Model 1: GRU Baseline (no stochastic state)
# ===========================================================================

class GRUBaseline(nn.Module):
    """
    GRU Baseline: Encoder -> GRU -> Classifier
    No stochastic state. Purely deterministic recurrent model.
    """

    def __init__(self, input_dim=784, encoder_hidden=256, det_state_dim=64,
                 num_classes=10):
        super().__init__()
        self.input_dim = input_dim
        self.det_state_dim = det_state_dim
        self.num_classes = num_classes

        # Encoder: x -> deterministic features
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, encoder_hidden),
            nn.ReLU(),
            nn.Linear(encoder_hidden, det_state_dim),
            nn.ReLU(),
        )

        # GRU for temporal transition
        self.gru = nn.GRUCell(det_state_dim, det_state_dim)

        # Classifier from deterministic state
        self.classifier = nn.Linear(det_state_dim, num_classes)

        # Predictor: predict next state from current state
        self.predictor = nn.Linear(det_state_dim, det_state_dim)

    def forward(self, x_seq):
        """
        Forward pass through sequence.

        Args:
            x_seq: (batch, seq_length, input_dim)

        Returns:
            logits: (batch, seq_length, num_classes)
            pred_loss: scalar, MSE of next-state prediction
            states: (batch, seq_length, det_state_dim) for stability analysis
        """
        batch_size, seq_len, _ = x_seq.shape

        # Initialize hidden state
        h = torch.zeros(batch_size, self.det_state_dim, device=x_seq.device)

        all_logits = []
        all_states = []
        all_pred_errors = []

        for t in range(seq_len):
            x_t = x_seq[:, t, :]  # (batch, input_dim)

            # Encode observation
            enc = self.encoder(x_t)  # (batch, det_state_dim)

            # GRU transition
            h = self.gru(enc, h)  # (batch, det_state_dim)

            # Predict next state from current
            h_pred = self.predictor(h)  # (batch, det_state_dim)

            all_logits.append(self.classifier(h))
            all_states.append(h)

            # Prediction loss: predict next encoded observation
            if t < seq_len - 1:
                with torch.no_grad():
                    enc_next = self.encoder(x_seq[:, t + 1, :])
                pred_error = F.mse_loss(h_pred, enc_next)
                all_pred_errors.append(pred_error)

        logits = torch.stack(all_logits, dim=1)  # (batch, seq_len, num_classes)
        states = torch.stack(all_states, dim=1)  # (batch, seq_len, det_state_dim)
        avg_pred_loss = torch.stack(all_pred_errors).mean() if all_pred_errors else torch.tensor(0.0)

        return logits, avg_pred_loss, states

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ===========================================================================
# Model 2: Vanilla RSSM
# ===========================================================================

class VanillaRSSM(nn.Module):
    """
    Vanilla RSSM: Encoder -> Prior/Posterior stochastic state -> GRU -> Decoder/Classifier

    Architecture:
      - Encoder: Linear(784, 256) -> ReLU -> Linear(256, 64) -> deterministic state h
      - Prior: Linear(64, 32) -> mu_prior, logvar_prior
      - Posterior: Linear(64+32, 32) -> mu_post, logvar_post (given observation)
      - GRU: (64+32, 64) -> recurrent state update
      - Classifier: Linear(96, 10)
      - Decoder: Linear(96, 256) -> ReLU -> Linear(256, 784)
    """

    def __init__(self, input_dim=784, encoder_hidden=256, det_state_dim=64,
                 stoch_state_dim=32, decoder_hidden=256, num_classes=10):
        super().__init__()
        self.input_dim = input_dim
        self.det_state_dim = det_state_dim
        self.stoch_state_dim = stoch_state_dim
        self.combined_dim = det_state_dim + stoch_state_dim
        self.num_classes = num_classes

        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, encoder_hidden),
            nn.ReLU(),
            nn.Linear(encoder_hidden, det_state_dim),
            nn.ReLU(),
        )

        # Prior: from deterministic state to stochastic prior
        self.prior_mu = nn.Linear(det_state_dim, stoch_state_dim)
        self.prior_logvar = nn.Linear(det_state_dim, stoch_state_dim)

        # Posterior: from (deterministic state + encoded observation) to stochastic posterior
        # In RSSM, posterior receives the current observation
        self.post_mu = nn.Linear(det_state_dim + det_state_dim, stoch_state_dim)
        self.post_logvar = nn.Linear(det_state_dim + det_state_dim, stoch_state_dim)

        # GRU: update deterministic state given (det + stoch)
        self.gru = nn.GRUCell(det_state_dim + stoch_state_dim, det_state_dim)

        # Classifier
        self.classifier = nn.Linear(det_state_dim + stoch_state_dim, num_classes)

        # Decoder (for reconstruction)
        self.decoder = nn.Sequential(
            nn.Linear(det_state_dim + stoch_state_dim, decoder_hidden),
            nn.ReLU(),
            nn.Linear(decoder_hidden, input_dim),
        )

        # Predictor: predict next combined state
        self.predictor = nn.Linear(det_state_dim + stoch_state_dim, det_state_dim)

    def reparameterize(self, mu, logvar):
        """Reparameterization trick."""
        if self.training:
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            return mu + eps * std
        return mu

    def forward(self, x_seq):
        """
        Forward pass through sequence.

        Args:
            x_seq: (batch, seq_length, input_dim)

        Returns:
            logits: (batch, seq_length, num_classes)
            recon: (batch, seq_length, input_dim)
            pred_loss: scalar, MSE of next-state prediction
            kl_loss: scalar, KL divergence
            states: (batch, seq_length, combined_dim) for stability analysis
        """
        batch_size, seq_len, _ = x_seq.shape

        # Initialize hidden state
        h = torch.zeros(batch_size, self.det_state_dim, device=x_seq.device)

        all_logits = []
        all_states = []
        all_recon = []
        all_pred_errors = []
        total_kl = 0.0
        kl_count = 0

        for t in range(seq_len):
            x_t = x_seq[:, t, :]  # (batch, input_dim)

            # Encode observation
            enc = self.encoder(x_t)  # (batch, det_state_dim)

            # Prior stochastic state (from current deterministic state)
            mu_prior = self.prior_mu(h)
            logvar_prior = self.prior_logvar(h)

            # Posterior stochastic state (conditioned on observation)
            post_input = torch.cat([h, enc], dim=-1)  # (batch, 2*det_state_dim)
            mu_post = self.post_mu(post_input)
            logvar_post = self.post_logvar(post_input)

            # Sample stochastic state
            z = self.reparameterize(mu_post, logvar_post)

            # KL divergence: KL[N(mu_post, var_post) || N(mu_prior, var_prior)]
            kl = 0.5 * torch.sum(
                logvar_prior - logvar_post
                + (torch.exp(logvar_post) + (mu_post - mu_prior).pow(2))
                / torch.exp(logvar_prior)
                - 1,
                dim=-1
            ).mean()
            total_kl += kl
            kl_count += 1

            # Combined state
            combined = torch.cat([h, z], dim=-1)  # (batch, combined_dim)

            # Classifier and decoder
            logits = self.classifier(combined)
            recon = self.decoder(combined)

            # GRU transition: update deterministic state
            h = self.gru(combined.detach(), h)  # Detach to prevent gradient through GRU input

            # Predict next encoded observation
            h_pred = self.predictor(combined)

            all_logits.append(logits)
            all_recon.append(recon)
            all_states.append(combined)

            if t < seq_len - 1:
                with torch.no_grad():
                    enc_next = self.encoder(x_seq[:, t + 1, :])
                pred_error = F.mse_loss(h_pred, enc_next)
                all_pred_errors.append(pred_error)

        logits = torch.stack(all_logits, dim=1)
        recon = torch.stack(all_recon, dim=1)
        states = torch.stack(all_states, dim=1)
        avg_pred_loss = torch.stack(all_pred_errors).mean() if all_pred_errors else torch.tensor(0.0)
        avg_kl = total_kl / max(kl_count, 1)

        return logits, recon, avg_pred_loss, avg_kl, states

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ===========================================================================
# Model 3: AFM-RSSM (Stiefel projection replaces stochastic state)
# ===========================================================================

class AFMRSSM(nn.Module):
    """
    AFM-RSSM: Replace the RSSM stochastic state with Stiefel projection.

    Key difference from Vanilla RSSM:
    - Instead of sampling z ~ N(mu, var) in Euclidean space,
      we project onto the Stiefel manifold: S = QR(mu + noise)
    - The stochastic state is now a point on St(d, K)
    - KL divergence uses the Stiefel/Haar prior approximation

    Architecture:
      - Encoder: Linear(784, 256) -> ReLU -> Linear(256, 64) -> deterministic state h
      - Prior: Linear(64, d*K) -> reshape to (d, K) -> Stiefel projection
      - Posterior: Linear(64+64, d*K) -> reshape to (d, K) -> Stiefel projection
      - GRU: (64+d*K, 64) -> recurrent state update
      - Classifier: Linear(64+d*K, 10)
      - Decoder: Linear(64+d*K, 256) -> ReLU -> Linear(256, 784)
    """

    def __init__(self, input_dim=784, encoder_hidden=256, det_state_dim=64,
                 d_stiefel=8, k_stiefel=4, decoder_hidden=256, num_classes=10):
        super().__init__()
        self.input_dim = input_dim
        self.det_state_dim = det_state_dim
        self.d_stiefel = d_stiefel
        self.k_stiefel = k_stiefel
        self.stoch_dim = d_stiefel * k_stiefel  # 32
        self.combined_dim = det_state_dim + self.stoch_dim
        self.num_classes = num_classes

        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, encoder_hidden),
            nn.ReLU(),
            nn.Linear(encoder_hidden, det_state_dim),
            nn.ReLU(),
        )

        # Prior: from deterministic state to Stiefel pre-projection params
        self.prior_mu = nn.Linear(det_state_dim, self.stoch_dim)
        self.prior_logvar = nn.Linear(det_state_dim, self.stoch_dim)

        # Posterior: from (deterministic state + encoded observation) to Stiefel params
        self.post_mu = nn.Linear(det_state_dim + det_state_dim, self.stoch_dim)
        self.post_logvar = nn.Linear(det_state_dim + det_state_dim, self.stoch_dim)

        # Stiefel projection layers
        self.stiefel_prior = StiefelLayer(d=d_stiefel, K=k_stiefel, stochastic=True)
        self.stiefel_posterior = StiefelLayer(d=d_stiefel, K=k_stiefel, stochastic=True)

        # GRU: update deterministic state given (det + stoch)
        self.gru = nn.GRUCell(det_state_dim + self.stoch_dim, det_state_dim)

        # Classifier
        self.classifier = nn.Linear(det_state_dim + self.stoch_dim, num_classes)

        # Decoder (for reconstruction)
        self.decoder = nn.Sequential(
            nn.Linear(det_state_dim + self.stoch_dim, decoder_hidden),
            nn.ReLU(),
            nn.Linear(decoder_hidden, input_dim),
        )

        # Predictor: predict next encoded observation
        self.predictor = nn.Linear(det_state_dim + self.stoch_dim, det_state_dim)

    def forward(self, x_seq):
        """
        Forward pass through sequence.

        Args:
            x_seq: (batch, seq_length, input_dim)

        Returns:
            logits: (batch, seq_length, num_classes)
            recon: (batch, seq_length, input_dim)
            pred_loss: scalar, MSE of next-state prediction
            kl_loss: scalar, Stiefel KL divergence
            states: (batch, seq_length, combined_dim) for stability analysis
        """
        batch_size, seq_len, _ = x_seq.shape

        # Initialize hidden state
        h = torch.zeros(batch_size, self.det_state_dim, device=x_seq.device)

        all_logits = []
        all_states = []
        all_recon = []
        all_pred_errors = []
        total_kl = 0.0
        kl_count = 0

        for t in range(seq_len):
            x_t = x_seq[:, t, :]  # (batch, input_dim)

            # Encode observation
            enc = self.encoder(x_t)  # (batch, det_state_dim)

            # Prior stochastic state (from current deterministic state)
            mu_prior = self.prior_mu(h)
            logvar_prior = self.prior_logvar(h)
            S_prior, kl_prior = self.stiefel_prior(mu_prior, logvar_prior)

            # Posterior stochastic state (conditioned on observation)
            post_input = torch.cat([h, enc], dim=-1)  # (batch, 2*det_state_dim)
            mu_post = self.post_mu(post_input)
            logvar_post = self.post_logvar(post_input)
            S_post, kl_post = self.stiefel_posterior(mu_post, logvar_post)

            # Use posterior during training, prior during eval
            if self.training:
                z = S_post.reshape(batch_size, -1)  # (batch, d*K)
                kl = kl_post if kl_post is not None else torch.tensor(0.0)
            else:
                z = S_prior.reshape(batch_size, -1)
                kl = kl_prior if kl_prior is not None else torch.tensor(0.0)

            total_kl += kl
            kl_count += 1

            # Combined state
            combined = torch.cat([h, z], dim=-1)  # (batch, combined_dim)

            # Classifier and decoder
            logits = self.classifier(combined)
            recon = self.decoder(combined)

            # GRU transition: update deterministic state
            h = self.gru(combined.detach(), h)

            # Predict next encoded observation
            h_pred = self.predictor(combined)

            all_logits.append(logits)
            all_recon.append(recon)
            all_states.append(combined)

            if t < seq_len - 1:
                with torch.no_grad():
                    enc_next = self.encoder(x_seq[:, t + 1, :])
                pred_error = F.mse_loss(h_pred, enc_next)
                all_pred_errors.append(pred_error)

        logits = torch.stack(all_logits, dim=1)
        recon = torch.stack(all_recon, dim=1)
        states = torch.stack(all_states, dim=1)
        avg_pred_loss = torch.stack(all_pred_errors).mean() if all_pred_errors else torch.tensor(0.0)
        avg_kl = total_kl / max(kl_count, 1)

        return logits, recon, avg_pred_loss, avg_kl, states

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ===========================================================================
# Training and evaluation
# ===========================================================================

def train_one_epoch_gru(model, loader, optimizer, device='cpu'):
    """Train GRU baseline for one epoch."""
    model.train()
    metrics = defaultdict(list)

    for x_seq, y_seq in loader:
        x_seq, y_seq = x_seq.to(device), y_seq.to(device)
        batch_size, seq_len, _ = x_seq.shape

        optimizer.zero_grad()
        logits, pred_loss, states = model(x_seq)

        # Classification loss (all timesteps)
        ce_loss = F.cross_entropy(
            logits.reshape(-1, model.num_classes),
            y_seq.reshape(-1)
        )

        total_loss = ce_loss + 0.5 * pred_loss

        total_loss.backward()
        # Gradient clipping for RNN stability
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        with torch.no_grad():
            acc = (logits.argmax(-1) == y_seq).float().mean().item()

        metrics['total_loss'].append(total_loss.item())
        metrics['ce_loss'].append(ce_loss.item())
        metrics['pred_loss'].append(pred_loss.item())
        metrics['accuracy'].append(acc)

    return {k: float(np.mean(v)) for k, v in metrics.items()}


def train_one_epoch_rssm(model, loader, optimizer, model_type='vanilla',
                         beta=0.01, device='cpu'):
    """Train RSSM model (vanilla or AFM) for one epoch."""
    model.train()
    metrics = defaultdict(list)

    for x_seq, y_seq in loader:
        x_seq, y_seq = x_seq.to(device), y_seq.to(device)

        optimizer.zero_grad()

        if model_type == 'vanilla':
            logits, recon, pred_loss, kl_loss, states = model(x_seq)
        else:  # afm
            logits, recon, pred_loss, kl_loss, states = model(x_seq)

        # Classification loss
        ce_loss = F.cross_entropy(
            logits.reshape(-1, model.num_classes),
            y_seq.reshape(-1)
        )

        # Reconstruction loss
        recon_loss = F.mse_loss(recon, x_seq)

        # Total loss: CE + pred + recon + beta * KL
        total_loss = ce_loss + 0.5 * pred_loss + 0.1 * recon_loss + beta * kl_loss

        total_loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        with torch.no_grad():
            acc = (logits.argmax(-1) == y_seq).float().mean().item()

        metrics['total_loss'].append(total_loss.item())
        metrics['ce_loss'].append(ce_loss.item())
        metrics['pred_loss'].append(pred_loss.item())
        metrics['recon_loss'].append(recon_loss.item())
        metrics['kl_loss'].append(kl_loss.item() if isinstance(kl_loss, torch.Tensor) else float(kl_loss))
        metrics['accuracy'].append(acc)

    return {k: float(np.mean(v)) for k, v in metrics.items()}


def evaluate_model(model, loader, model_type='gru', device='cpu'):
    """
    Evaluate model on sequential data.

    Returns:
        Dict with accuracy, prediction loss, representation stability
    """
    model.eval()
    total_correct = 0
    total_samples = 0
    pred_losses = []
    all_states = []

    with torch.no_grad():
        for x_seq, y_seq in loader:
            x_seq, y_seq = x_seq.to(device), y_seq.to(device)

            if model_type == 'gru':
                logits, pred_loss, states = model(x_seq)
            else:
                logits, recon, pred_loss, kl_loss, states = model(x_seq)

            total_correct += (logits.argmax(-1) == y_seq).sum().item()
            total_samples += y_seq.numel()
            pred_losses.append(pred_loss.item() if isinstance(pred_loss, torch.Tensor) else float(pred_loss))
            all_states.append(states.cpu())

    accuracy = total_correct / total_samples
    avg_pred_loss = np.mean(pred_losses)

    # Compute representation stability: cosine similarity between
    # states at adjacent timesteps, averaged across the sequence
    all_states_cat = torch.cat(all_states, dim=0)  # (N, seq_len, dim)
    stabilities = []
    for t in range(all_states_cat.shape[1] - 1):
        s_t = all_states_cat[:, t, :]     # (N, dim)
        s_t1 = all_states_cat[:, t + 1, :]  # (N, dim)
        cos_sim = F.cosine_similarity(s_t, s_t1, dim=-1)  # (N,)
        stabilities.append(cos_sim.mean().item())

    avg_stability = np.mean(stabilities) if stabilities else 0.0

    # Also compute per-timestep accuracy
    # Re-run to get per-timestep accuracy
    per_timestep_acc = []
    with torch.no_grad():
        for x_seq, y_seq in loader:
            x_seq, y_seq = x_seq.to(device), y_seq.to(device)
            if model_type == 'gru':
                logits, _, _ = model(x_seq)
            else:
                logits, _, _, _, _ = model(x_seq)
            # logits: (batch, seq_len, num_classes)
            for t in range(logits.shape[1]):
                acc_t = (logits[:, t, :].argmax(-1) == y_seq[:, t]).float().mean().item()
                if len(per_timestep_acc) <= t:
                    per_timestep_acc.append([])
                per_timestep_acc[t].append(acc_t)

    per_timestep_acc_avg = [np.mean(accs) for accs in per_timestep_acc]

    return {
        'accuracy': accuracy,
        'pred_loss': avg_pred_loss,
        'representation_stability': avg_stability,
        'per_timestep_stability': stabilities,
        'per_timestep_accuracy': per_timestep_acc_avg,
    }


def train_full(model, train_loader, test_loader, model_type='gru',
               epochs=15, lr=1e-3, beta=0.01, device='cpu', verbose=True):
    """Full training loop with metric recording."""
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    history = []
    best_acc = 0.0
    t0 = time.time()

    for epoch in range(epochs):
        ep_start = time.time()

        # Train
        if model_type == 'gru':
            train_m = train_one_epoch_gru(model, train_loader, optimizer, device)
        else:
            train_m = train_one_epoch_rssm(
                model, train_loader, optimizer,
                model_type=model_type, beta=beta, device=device
            )

        # Evaluate
        eval_m = evaluate_model(model, test_loader, model_type, device)

        scheduler.step()
        ep_time = time.time() - ep_start

        if eval_m['accuracy'] > best_acc:
            best_acc = eval_m['accuracy']

        ep_record = {
            'epoch': epoch,
            'train_total_loss': train_m['total_loss'],
            'train_ce_loss': train_m['ce_loss'],
            'train_pred_loss': train_m['pred_loss'],
            'train_accuracy': train_m['accuracy'],
            'test_accuracy': eval_m['accuracy'],
            'test_pred_loss': eval_m['pred_loss'],
            'test_rep_stability': eval_m['representation_stability'],
            'epoch_time': ep_time,
        }
        if 'kl_loss' in train_m:
            ep_record['train_kl_loss'] = train_m['kl_loss']
        if 'recon_loss' in train_m:
            ep_record['train_recon_loss'] = train_m['recon_loss']

        history.append(ep_record)

        if verbose and (epoch + 1) % 3 == 0:
            print(f"    Epoch {epoch+1}/{epochs}: "
                  f"loss={train_m['total_loss']:.4f} "
                  f"ce={train_m['ce_loss']:.4f} "
                  f"pred={train_m['pred_loss']:.4f} "
                  f"train_acc={train_m['accuracy']:.4f} "
                  f"test_acc={eval_m['accuracy']:.4f} "
                  f"stab={eval_m['representation_stability']:.4f} "
                  f"t={ep_time:.1f}s")

    total_time = time.time() - t0

    # Final evaluation with full metrics
    final_eval = evaluate_model(model, test_loader, model_type, device)

    return {
        'history': history,
        'best_test_acc': best_acc,
        'final_test_acc': final_eval['accuracy'],
        'final_pred_loss': final_eval['pred_loss'],
        'final_rep_stability': final_eval['representation_stability'],
        'per_timestep_stability': final_eval['per_timestep_stability'],
        'per_timestep_accuracy': final_eval['per_timestep_accuracy'],
        'total_time': total_time,
    }


# ===========================================================================
# Main experiment
# ===========================================================================

def run_rssm_experiment():
    """Run the RSSM comparison experiment."""

    print("=" * 70)
    print("AFM-RSSM: Recurrent State-Space Model Comparison")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Step 1: Print model architectures and parameter counts
    # ------------------------------------------------------------------
    print("\n[1] Model Architecture Comparison")
    print("-" * 50)

    set_seed(SEED)
    gru_model = GRUBaseline(
        input_dim=INPUT_DIM, encoder_hidden=ENCODER_HIDDEN,
        det_state_dim=DET_STATE_DIM, num_classes=NUM_CLASSES,
    )
    rssm_model = VanillaRSSM(
        input_dim=INPUT_DIM, encoder_hidden=ENCODER_HIDDEN,
        det_state_dim=DET_STATE_DIM, stoch_state_dim=STOCH_STATE_DIM,
        decoder_hidden=DECODER_HIDDEN, num_classes=NUM_CLASSES,
    )
    afm_rssm_model = AFMRSSM(
        input_dim=INPUT_DIM, encoder_hidden=ENCODER_HIDDEN,
        det_state_dim=DET_STATE_DIM, d_stiefel=AFM_D, k_stiefel=AFM_K,
        decoder_hidden=DECODER_HIDDEN, num_classes=NUM_CLASSES,
    )

    model_info = {
        'gru_baseline': {
            'params': gru_model.count_parameters(),
            'architecture': 'Encoder -> GRU -> Classifier (no stochastic state)',
            'det_state_dim': DET_STATE_DIM,
            'stoch_state_dim': 0,
        },
        'vanilla_rssm': {
            'params': rssm_model.count_parameters(),
            'architecture': 'Encoder -> Prior/Posterior -> GRU -> Decoder/Classifier',
            'det_state_dim': DET_STATE_DIM,
            'stoch_state_dim': STOCH_STATE_DIM,
        },
        'afm_rssm': {
            'params': afm_rssm_model.count_parameters(),
            'architecture': 'Encoder -> Stiefel Prior/Posterior -> GRU -> Decoder/Classifier',
            'det_state_dim': DET_STATE_DIM,
            'stoch_state_dim': AFM_STOCH_DIM,
            'stiefel_d': AFM_D,
            'stiefel_K': AFM_K,
        },
    }

    for name, info in model_info.items():
        print(f"  {name}: {info['params']:,} params")
        print(f"    Architecture: {info['architecture']}")
        print(f"    det_state={info['det_state_dim']}, stoch_state={info['stoch_state_dim']}")

    # ------------------------------------------------------------------
    # Step 2: Load sequential MNIST
    # ------------------------------------------------------------------
    print(f"\n[2] Loading sequential MNIST (seq_length={SEQ_LENGTH})...")
    train_loader, test_loader = create_sequential_mnist(
        batch_size=BATCH_SIZE, seq_length=SEQ_LENGTH, seed=SEED
    )

    # ------------------------------------------------------------------
    # Step 3: Train all 3 models
    # ------------------------------------------------------------------
    print(f"\n[3] Training 3 models ({EPOCHS} epochs, batch_size={BATCH_SIZE}, seed={SEED})")
    print("=" * 70)

    all_results = {}

    # --- GRU Baseline ---
    print("\n  === GRU Baseline ===")
    set_seed(SEED)
    gru_model = GRUBaseline(
        input_dim=INPUT_DIM, encoder_hidden=ENCODER_HIDDEN,
        det_state_dim=DET_STATE_DIM, num_classes=NUM_CLASSES,
    )
    gru_result = train_full(
        gru_model, train_loader, test_loader,
        model_type='gru', epochs=EPOCHS, lr=LR,
        device=DEVICE, verbose=True,
    )
    all_results['gru_baseline'] = {
        'model_type': 'gru',
        'param_count': gru_model.count_parameters(),
        **gru_result,
    }
    print(f"  => Best acc: {gru_result['best_test_acc']:.4f}, "
          f"Stability: {gru_result['final_rep_stability']:.4f}")

    # --- Vanilla RSSM ---
    print("\n  === Vanilla RSSM ===")
    set_seed(SEED)
    rssm_model = VanillaRSSM(
        input_dim=INPUT_DIM, encoder_hidden=ENCODER_HIDDEN,
        det_state_dim=DET_STATE_DIM, stoch_state_dim=STOCH_STATE_DIM,
        decoder_hidden=DECODER_HIDDEN, num_classes=NUM_CLASSES,
    )
    rssm_result = train_full(
        rssm_model, train_loader, test_loader,
        model_type='vanilla', epochs=EPOCHS, lr=LR, beta=BETA_KL,
        device=DEVICE, verbose=True,
    )
    all_results['vanilla_rssm'] = {
        'model_type': 'vanilla',
        'param_count': rssm_model.count_parameters(),
        **rssm_result,
    }
    print(f"  => Best acc: {rssm_result['best_test_acc']:.4f}, "
          f"Stability: {rssm_result['final_rep_stability']:.4f}")

    # --- AFM-RSSM ---
    print("\n  === AFM-RSSM ===")
    set_seed(SEED)
    afm_model = AFMRSSM(
        input_dim=INPUT_DIM, encoder_hidden=ENCODER_HIDDEN,
        det_state_dim=DET_STATE_DIM, d_stiefel=AFM_D, k_stiefel=AFM_K,
        decoder_hidden=DECODER_HIDDEN, num_classes=NUM_CLASSES,
    )
    afm_result = train_full(
        afm_model, train_loader, test_loader,
        model_type='afm', epochs=EPOCHS, lr=LR, beta=BETA_KL,
        device=DEVICE, verbose=True,
    )
    all_results['afm_rssm'] = {
        'model_type': 'afm',
        'param_count': afm_model.count_parameters(),
        **afm_result,
    }
    print(f"  => Best acc: {afm_result['best_test_acc']:.4f}, "
          f"Stability: {afm_result['final_rep_stability']:.4f}")

    # ------------------------------------------------------------------
    # Step 4: Compute comparison metrics
    # ------------------------------------------------------------------
    print(f"\n[4] Comparison Summary")
    print("=" * 70)

    comparison = {}
    for name in ['gru_baseline', 'vanilla_rssm', 'afm_rssm']:
        r = all_results[name]
        comparison[name] = {
            'accuracy': r['best_test_acc'],
            'final_accuracy': r['final_test_acc'],
            'prediction_loss': r['final_pred_loss'],
            'rep_stability': r['final_rep_stability'],
            'per_timestep_stability': r['per_timestep_stability'],
            'per_timestep_accuracy': r['per_timestep_accuracy'],
            'param_count': r['param_count'],
            'training_time': r['total_time'],
        }
        print(f"\n  {name}:")
        print(f"    Best Accuracy:    {r['best_test_acc']:.4f}")
        print(f"    Final Accuracy:   {r['final_test_acc']:.4f}")
        print(f"    Prediction Loss:  {r['final_pred_loss']:.4f}")
        print(f"    Rep. Stability:   {r['final_rep_stability']:.4f}")
        print(f"    Params:           {r['param_count']:,}")
        print(f"    Training Time:    {r['total_time']:.1f}s")

    # Per-timestep breakdown
    print(f"\n  Per-Timestep Accuracy:")
    print(f"  {'Timestep':<10} {'GRU':<12} {'RSSM':<12} {'AFM-RSSM':<12}")
    for t in range(SEQ_LENGTH):
        gru_acc = comparison['gru_baseline']['per_timestep_accuracy'][t] if t < len(comparison['gru_baseline']['per_timestep_accuracy']) else 0
        rssm_acc = comparison['vanilla_rssm']['per_timestep_accuracy'][t] if t < len(comparison['vanilla_rssm']['per_timestep_accuracy']) else 0
        afm_acc = comparison['afm_rssm']['per_timestep_accuracy'][t] if t < len(comparison['afm_rssm']['per_timestep_accuracy']) else 0
        print(f"  {t:<10} {gru_acc:<12.4f} {rssm_acc:<12.4f} {afm_acc:<12.4f}")

    print(f"\n  Per-Timestep Representation Stability (cosine sim):")
    print(f"  {'Timestep':<10} {'GRU':<12} {'RSSM':<12} {'AFM-RSSM':<12}")
    for t in range(SEQ_LENGTH - 1):
        gru_s = comparison['gru_baseline']['per_timestep_stability'][t] if t < len(comparison['gru_baseline']['per_timestep_stability']) else 0
        rssm_s = comparison['vanilla_rssm']['per_timestep_stability'][t] if t < len(comparison['vanilla_rssm']['per_timestep_stability']) else 0
        afm_s = comparison['afm_rssm']['per_timestep_stability'][t] if t < len(comparison['afm_rssm']['per_timestep_stability']) else 0
        print(f"  t{t}->t{t+1}   {gru_s:<12.4f} {rssm_s:<12.4f} {afm_s:<12.4f}")

    # ------------------------------------------------------------------
    # Step 5: Save results
    # ------------------------------------------------------------------
    print(f"\n[5] Saving results...")

    full_results = {
        'experiment': 'rssm',
        'description': 'RSSM world model prototype comparison with AFM',
        'config': {
            'seq_length': SEQ_LENGTH,
            'batch_size': BATCH_SIZE,
            'epochs': EPOCHS,
            'lr': LR,
            'beta_kl': BETA_KL,
            'seed': SEED,
            'device': DEVICE,
            'encoder_hidden': ENCODER_HIDDEN,
            'det_state_dim': DET_STATE_DIM,
            'stoch_state_dim': STOCH_STATE_DIM,
            'afm_d': AFM_D,
            'afm_k': AFM_K,
            'decoder_hidden': DECODER_HIDDEN,
        },
        'model_info': model_info,
        'results': all_results,
        'comparison': comparison,
    }

    save_json('rssm_results', full_results)

    # ------------------------------------------------------------------
    # Step 6: Generate report
    # ------------------------------------------------------------------
    print(f"\n[6] Generating report: {REPORT_PATH}")
    report = generate_report(model_info, all_results, comparison)
    with open(REPORT_PATH, 'w') as f:
        f.write(report)
    print(f"  [SAVE] {REPORT_PATH}")

    print("\n" + "=" * 70)
    print("EXPERIMENT COMPLETE")
    print("=" * 70)

    return full_results


# ===========================================================================
# Report generation
# ===========================================================================

def generate_report(model_info, all_results, comparison):
    """Generate markdown report for the RSSM experiment."""

    lines = []
    lines.append("# AFM-RSSM Comparison Report")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("This report compares three recurrent model architectures on a sequential")
    lines.append("prediction task built from MNIST. The goal is to evaluate whether the")
    lines.append("Stiefel manifold projection from AFM can replace the standard Gaussian")
    lines.append("stochastic state in a Recurrent State-Space Model (RSSM).")
    lines.append("")
    lines.append(f"- **Task**: Sequential prediction on MNIST (sequences of {SEQ_LENGTH} same-class digits)")
    lines.append(f"- **Sequence length**: {SEQ_LENGTH}")
    lines.append(f"- **Batch size**: {BATCH_SIZE}")
    lines.append(f"- **Epochs**: {EPOCHS}")
    lines.append(f"- **Seed**: {SEED}")
    lines.append(f"- **KL weight (beta)**: {BETA_KL}")
    lines.append(f"- **Device**: {DEVICE}")
    lines.append("")

    # Models
    lines.append("## 1. Model Architectures")
    lines.append("")
    lines.append("| Model | Architecture | Parameters | Det State | Stoch State |")
    lines.append("|-------|-------------|------------|-----------|-------------|")
    for name, info in model_info.items():
        lines.append(f"| {name} | {info['architecture']} | {info['params']:,} | "
                     f"{info['det_state_dim']} | {info['stoch_state_dim']} |")
    lines.append("")
    lines.append("### Key difference:")
    lines.append("- **GRU Baseline**: No stochastic state — purely deterministic transitions")
    lines.append("- **Vanilla RSSM**: Stochastic state sampled from Gaussian (standard RSSM)")
    lines.append("- **AFM-RSSM**: Stochastic state projected onto St(d=8, K=4) Stiefel manifold")
    lines.append("")

    # Accuracy
    lines.append("## 2. Classification Accuracy")
    lines.append("")
    lines.append("| Model | Best Accuracy | Final Accuracy |")
    lines.append("|-------|--------------|----------------|")
    for name in ['gru_baseline', 'vanilla_rssm', 'afm_rssm']:
        c = comparison[name]
        lines.append(f"| {name} | {c['accuracy']:.4f} | {c['final_accuracy']:.4f} |")
    lines.append("")

    # Prediction loss
    lines.append("## 3. Next-State Prediction Loss")
    lines.append("")
    lines.append("MSE between predicted next encoded observation and actual next encoded observation.")
    lines.append("")
    lines.append("| Model | Prediction Loss |")
    lines.append("|-------|----------------|")
    for name in ['gru_baseline', 'vanilla_rssm', 'afm_rssm']:
        c = comparison[name]
        lines.append(f"| {name} | {c['prediction_loss']:.4f} |")
    lines.append("")

    # Representation stability
    lines.append("## 4. Representation Stability")
    lines.append("")
    lines.append("Average cosine similarity between states at adjacent timesteps.")
    lines.append("Higher = more stable (less drift between timesteps).")
    lines.append("")
    lines.append("| Model | Avg Stability |")
    lines.append("|-------|-------------|")
    for name in ['gru_baseline', 'vanilla_rssm', 'afm_rssm']:
        c = comparison[name]
        lines.append(f"| {name} | {c['rep_stability']:.4f} |")
    lines.append("")

    # Per-timestep accuracy
    lines.append("## 5. Per-Timestep Accuracy")
    lines.append("")
    lines.append("| Timestep | GRU Baseline | Vanilla RSSM | AFM-RSSM |")
    lines.append("|----------|-------------|-------------|----------|")
    for t in range(SEQ_LENGTH):
        gru_acc = comparison['gru_baseline']['per_timestep_accuracy'][t] if t < len(comparison['gru_baseline']['per_timestep_accuracy']) else 0
        rssm_acc = comparison['vanilla_rssm']['per_timestep_accuracy'][t] if t < len(comparison['vanilla_rssm']['per_timestep_accuracy']) else 0
        afm_acc = comparison['afm_rssm']['per_timestep_accuracy'][t] if t < len(comparison['afm_rssm']['per_timestep_accuracy']) else 0
        lines.append(f"| t={t} | {gru_acc:.4f} | {rssm_acc:.4f} | {afm_acc:.4f} |")
    lines.append("")

    # Per-timestep stability
    lines.append("## 6. Per-Timestep Representation Stability")
    lines.append("")
    lines.append("| Transition | GRU Baseline | Vanilla RSSM | AFM-RSSM |")
    lines.append("|-----------|-------------|-------------|----------|")
    for t in range(SEQ_LENGTH - 1):
        gru_s = comparison['gru_baseline']['per_timestep_stability'][t] if t < len(comparison['gru_baseline']['per_timestep_stability']) else 0
        rssm_s = comparison['vanilla_rssm']['per_timestep_stability'][t] if t < len(comparison['vanilla_rssm']['per_timestep_stability']) else 0
        afm_s = comparison['afm_rssm']['per_timestep_stability'][t] if t < len(comparison['afm_rssm']['per_timestep_stability']) else 0
        lines.append(f"| t{t}->t{t+1} | {gru_s:.4f} | {rssm_s:.4f} | {afm_s:.4f} |")
    lines.append("")

    # Training curves
    lines.append("## 7. Per-Epoch Training Curves")
    lines.append("")
    for model_name in ['gru_baseline', 'vanilla_rssm', 'afm_rssm']:
        r = all_results[model_name]
        lines.append(f"### {model_name}")
        lines.append("")
        lines.append("| Epoch | Train Loss | CE Loss | Pred Loss | Train Acc | Test Acc | Stability | Time |")
        lines.append("|-------|-----------|---------|-----------|-----------|----------|-----------|------|")
        for ep in r['history']:
            kl_str = f" | KL: {ep.get('train_kl_loss', 0):.4f}" if 'train_kl_loss' in ep else ""
            lines.append(f"| {ep['epoch']+1} | {ep['train_total_loss']:.4f} | "
                        f"{ep['train_ce_loss']:.4f} | {ep['train_pred_loss']:.4f} | "
                        f"{ep['train_accuracy']:.4f} | {ep['test_accuracy']:.4f} | "
                        f"{ep['test_rep_stability']:.4f} | {ep['epoch_time']:.1f}s |")
        lines.append("")

    # Key findings
    lines.append("## 8. Key Findings")
    lines.append("")

    # Compute deltas
    gru_acc = comparison['gru_baseline']['accuracy']
    rssm_acc = comparison['vanilla_rssm']['accuracy']
    afm_acc = comparison['afm_rssm']['accuracy']

    gru_stab = comparison['gru_baseline']['rep_stability']
    rssm_stab = comparison['vanilla_rssm']['rep_stability']
    afm_stab = comparison['afm_rssm']['rep_stability']

    lines.append("### Does adding a stochastic state help?")
    lines.append("")
    if rssm_acc > gru_acc + 0.005:
        lines.append(f"**YES**: Vanilla RSSM ({rssm_acc:.4f}) outperforms GRU baseline ({gru_acc:.4f}) "
                     f"by {(rssm_acc - gru_acc)*100:+.2f}%.")
    elif rssm_acc < gru_acc - 0.005:
        lines.append(f"**NO**: Vanilla RSSM ({rssm_acc:.4f}) underperforms GRU baseline ({gru_acc:.4f}) "
                     f"by {(rssm_acc - gru_acc)*100:+.2f}%.")
    else:
        lines.append(f"**MIXED**: Vanilla RSSM ({rssm_acc:.4f}) and GRU baseline ({gru_acc:.4f}) "
                     f"perform similarly ({(rssm_acc - gru_acc)*100:+.2f}%).")
    lines.append("")

    lines.append("### Does Stiefel projection help in the RSSM setting?")
    lines.append("")
    if afm_acc > rssm_acc + 0.005:
        lines.append(f"**YES**: AFM-RSSM ({afm_acc:.4f}) outperforms Vanilla RSSM ({rssm_acc:.4f}) "
                     f"by {(afm_acc - rssm_acc)*100:+.2f}%.")
        lines.append("The Stiefel manifold constraint provides a structural benefit over")
        lines.append("standard Gaussian stochastic states in this recurrent setting.")
    elif afm_acc < rssm_acc - 0.005:
        lines.append(f"**NO**: AFM-RSSM ({afm_acc:.4f}) underperforms Vanilla RSSM ({rssm_acc:.4f}) "
                     f"by {(afm_acc - rssm_acc)*100:+.2f}%.")
        lines.append("The Stiefel constraint may be too restrictive for the RSSM transition model,")
        lines.append("limiting the expressiveness of the stochastic state.")
    else:
        lines.append(f"**NEUTRAL**: AFM-RSSM ({afm_acc:.4f}) and Vanilla RSSM ({rssm_acc:.4f}) "
                     f"perform similarly ({(afm_acc - rssm_acc)*100:+.2f}%).")
        lines.append("The Stiefel projection neither helps nor hurts in this setting.")
    lines.append("")

    lines.append("### Representation stability comparison")
    lines.append("")
    lines.append(f"- GRU Baseline stability: {gru_stab:.4f}")
    lines.append(f"- Vanilla RSSM stability: {rssm_stab:.4f}")
    lines.append(f"- AFM-RSSM stability:     {afm_stab:.4f}")
    lines.append("")
    if afm_stab > rssm_stab and afm_stab > gru_stab:
        lines.append("**AFM-RSSM has the most stable representations.** This is consistent with")
        lines.append("the hypothesis that Stiefel projection anchors the latent geometry.")
    elif afm_stab < rssm_stab:
        lines.append("**AFM-RSSM does NOT improve representation stability** over Vanilla RSSM.")
        lines.append("The Stiefel constraint does not inherently stabilize recurrent transitions.")
    else:
        lines.append("Representation stability is similar across models.")
    lines.append("")

    # Honest assessment
    lines.append("## 9. Honest Assessment")
    lines.append("")
    lines.append("### What this experiment CAN tell us:")
    lines.append("- Whether Stiefel projection is viable as a stochastic state in RSSM")
    lines.append("- Relative accuracy of GRU vs RSSM vs AFM-RSSM on this specific task")
    lines.append("- Whether Stiefel states change representation stability")
    lines.append("")
    lines.append("### What this experiment CANNOT tell us:")
    lines.append("- Whether results generalize to more complex environments (e.g., Atari)")
    lines.append("- Whether the Stiefel constraint helps with planning or imagination")
    lines.append("- Whether the benefit (or lack thereof) is due to the QR projection")
    lines.append("  specifically vs. the manifold constraint in general")
    lines.append("- Whether results hold with different RSSM hyperparameters")
    lines.append("")
    lines.append("### Known limitations:")
    lines.append("- Single seed (SEED=42). Statistical claims require multi-seed runs.")
    lines.append("- The sequential MNIST task is relatively simple — all models may")
    lines.append("  converge to similar accuracy, making differentiation difficult.")
    lines.append("- The sequence length (5) may be too short for recurrent advantages")
    lines.append("  to emerge. Longer sequences would better test the RSSM.")
    lines.append("- The GRU baseline has fewer parameters than the RSSM variants.")
    lines.append("  This is by design (comparing architectures, not parameter counts),")
    lines.append("  but it complicates interpretation.")
    lines.append("- MNIST digits within a class are not truly sequential, so the")
    lines.append("  'prediction' task is somewhat artificial.")
    lines.append("")

    lines.append("## 10. Raw Data")
    lines.append("")
    lines.append("Full results saved to: `results_v02/rssm_results.json`")
    lines.append("")

    return "\n".join(lines)


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == '__main__':
    results = run_rssm_experiment()
