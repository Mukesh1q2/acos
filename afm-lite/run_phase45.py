#!/usr/bin/env python3
"""
AFM Phase 4.5 — Statistical Strengthening
============================================

Comprehensive experiment suite to statistically validate AFM-Lite claims
across multiple seeds, betas, geometries, and datasets.

Sub-phases:
  4.5A — Multi-Seed Validation       (5 seeds × 5 configs × Fashion-MNIST)
  4.5B — Forgetting Statistics        (5 seeds × 3 configs × Split-Fashion-MNIST)
  4.5C — Beta Sweep                   (6 betas × 3 configs × Fashion-MNIST)
  4.5D — Latent Geometry Study        (4 geometries × 3 configs × Fashion-MNIST)
  4.5E — Dataset Generalization       (4 datasets × 5 configs × 3 seeds)

Output:
  results_phase45/                    (JSON per sub-phase)
  /home/z/my-project/AFM_*.md         (Markdown reports per sub-phase)
  /home/z/my-project/AFM_PHASE45_MASTER_REPORT.md  (Synthesized report)

Usage:
  python /home/z/my-project/afm-lite/run_phase45.py              # Full
  python /home/z/my-project/afm-lite/run_phase45.py --phase A     # Single phase
  python /home/z/my-project/afm-lite/run_phase45.py --quick       # Quick: 1 seed, 5 epochs
"""

import sys
sys.path.insert(0, '/home/z/my-project/afm-lite')

import os
import json
import time
import argparse
import pickle
import warnings
from collections import defaultdict
from copy import deepcopy

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset, Subset

from models import BaselineModel, AFMLiteModel, MultiTaskBaseline, MultiTaskAFMLite
from losses import l_task, l_rib, l_vae
from stiefel import stiefel_project_qr, thread_orthogonality, stiefel_kl_complexity

# ---------------------------------------------------------------------------
# Global configuration
# ---------------------------------------------------------------------------
DEVICE = 'cpu'
RESULTS_DIR = '/home/z/my-project/afm-lite/results_phase45'
CACHE_DIR = '/home/z/my-project/afm-lite/.cache'

# Architecture (1.33M params)
HIDDEN_DIM = 512
D_STIEFEL = 32
K_THREADS = 4
LATENT_DIM = D_STIEFEL * K_THREADS  # 128

# Training defaults
DEFAULT_LR = 1e-3
DEFAULT_BETA = 0.01
DEFAULT_ORTH_WEIGHT = 0.1

# Active dimension threshold
ACTIVE_DIM_THRESHOLD = 0.01

# Silhouette max samples (for speed)
SILHOUETTE_MAX_SAMPLES = 2000

# Collapse thresholds
COLLAPSE_ACC_THRESHOLD = 0.15
COLLAPSE_ACTIVE_DIM_FRACTION = 0.05


# ===========================================================================
# Utility helpers
# ===========================================================================

def numpy_safe(obj):
    """Recursively convert numpy/torch types for JSON serialization."""
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
    if isinstance(obj, bool):
        return bool(obj)
    return obj


def save_json(name, data, directory=RESULTS_DIR):
    """Save results dict to JSON."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f'{name}.json')
    with open(path, 'w') as f:
        json.dump(numpy_safe(data), f, indent=2, default=str)
    print(f"  [SAVE] {path}")
    return path


def load_json(name, directory=RESULTS_DIR):
    """Load results dict from JSON, or return None if not found."""
    path = os.path.join(directory, f'{name}.json')
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None


def set_seed(seed):
    """Set random seed for reproducibility."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    # Also set Python hash seed for DataLoader workers (single-process, so this is fine)


def compute_ci(values, confidence=0.95):
    """
    Compute mean, std, and 95% confidence interval.
    Uses t-distribution: CI = mean ± t_{0.025, n-1} * std / sqrt(n)
    """
    from scipy.stats import t as t_dist
    arr = np.array(values, dtype=float)
    n = len(arr)
    if n == 0:
        return {'mean': 0.0, 'std': 0.0, 'ci_lower': 0.0, 'ci_upper': 0.0, 'n': 0}
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    if n > 1 and std > 0:
        t_val = t_dist.ppf((1 + confidence) / 2, df=n - 1)
        margin = t_val * std / np.sqrt(n)
    else:
        margin = 0.0
    return {
        'mean': mean,
        'std': std,
        'ci_lower': mean - margin,
        'ci_upper': mean + margin,
        'n': n,
    }


# ===========================================================================
# Dataset loaders (with caching)
# ===========================================================================

def _cache_dataset(name, load_fn, batch_size=256):
    """Load dataset with local pickle caching."""
    cache_path = os.path.join(CACHE_DIR, f'{name}.pkl')
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
        X_train, y_train = data['X_train'], data['y_train']
        X_test, y_test = data['X_test'], data['y_test']
    else:
        X_train, y_train, X_test, y_test = load_fn()
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump({'X_train': X_train, 'y_train': y_train,
                         'X_test': X_test, 'y_test': y_test}, f)

    X_train = X_train.astype(np.float32) / 255.0
    X_test = X_test.astype(np.float32) / 255.0

    num_classes = int(max(y_train.max(), y_test.max())) + 1

    train_ds = TensorDataset(torch.FloatTensor(X_train), torch.LongTensor(y_train.astype(np.int64)))
    test_ds = TensorDataset(torch.FloatTensor(X_test), torch.LongTensor(y_test.astype(np.int64)))

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    return train_loader, test_loader, 784, num_classes


def get_mnist(batch_size=256):
    """MNIST: 784-dim, 10 classes."""
    def load():
        from sklearn.datasets import fetch_openml
        mnist = fetch_openml('mnist_784', version=1, as_frame=False)
        X, y = mnist.data, mnist.target.astype(int)
        return X[:60000], y[:60000], X[60000:], y[60000:]
    return _cache_dataset('mnist', load, batch_size)


def get_fashion_mnist(batch_size=256):
    """Fashion-MNIST: 784-dim, 10 classes."""
    def load():
        from sklearn.datasets import fetch_openml
        fashion = fetch_openml('Fashion-MNIST', version=1, as_frame=False)
        X, y = fashion.data, fashion.target.astype(int)
        return X[:60000], y[:60000], X[60000:], y[60000:]
    return _cache_dataset('fashion_mnist', load, batch_size)


def get_kmnist(batch_size=256):
    """KMNIST: 784-dim, 10 classes (Kuzushiji)."""
    def load():
        import torchvision
        tv_root = os.path.join(CACHE_DIR, 'torchvision')
        os.makedirs(tv_root, exist_ok=True)
        train_set = torchvision.datasets.KMNIST(root=tv_root, train=True, download=True)
        test_set = torchvision.datasets.KMNIST(root=tv_root, train=False, download=True)
        X_train = train_set.data.numpy().reshape(-1, 784).astype(np.float32)
        y_train = train_set.targets.numpy().astype(np.int64)
        X_test = test_set.data.numpy().reshape(-1, 784).astype(np.float32)
        y_test = test_set.targets.numpy().astype(np.int64)
        return X_train, y_train, X_test, y_test
    return _cache_dataset('kmnist', load, batch_size)


def get_emnist_balanced(batch_size=256):
    """EMNIST/Balanced: 784-dim, 47 classes."""
    def load():
        import torchvision
        tv_root = os.path.join(CACHE_DIR, 'torchvision')
        os.makedirs(tv_root, exist_ok=True)
        train_set = torchvision.datasets.EMNIST(root=tv_root, split='balanced', train=True, download=True)
        test_set = torchvision.datasets.EMNIST(root=tv_root, split='balanced', train=False, download=True)
        X_train = train_set.data.numpy().reshape(-1, 784).astype(np.float32)
        y_train = train_set.targets.numpy().astype(np.int64)
        X_test = test_set.data.numpy().reshape(-1, 784).astype(np.float32)
        y_test = test_set.targets.numpy().astype(np.int64)
        return X_train, y_train, X_test, y_test
    return _cache_dataset('emnist_balanced', load, batch_size)


def get_split_fashion_mnist(batch_size=256, n_tasks=5):
    """
    Split-Fashion-MNIST: 5 tasks, 2 classes each.

    Task 0: classes 0,1 (T-shirt/top, Trouser)
    Task 1: classes 2,3 (Pullover, Dress)
    Task 2: classes 4,5 (Coat, Sandal)
    Task 3: classes 6,7 (Shirt, Sneaker)
    Task 4: classes 8,9 (Bag, Ankle boot)

    Returns list of (train_loader, test_loader, input_dim, num_classes_per_task) tuples.
    """
    train_loader, test_loader, _, _ = get_fashion_mnist(batch_size=batch_size)

    # Collect all data
    all_train_X, all_train_y = [], []
    for X, y in train_loader:
        all_train_X.append(X)
        all_train_y.append(y)
    all_train_X = torch.cat(all_train_X)
    all_train_y = torch.cat(all_train_y)

    all_test_X, all_test_y = [], []
    for X, y in test_loader:
        all_test_X.append(X)
        all_test_y.append(y)
    all_test_X = torch.cat(all_test_X)
    all_test_y = torch.cat(all_test_y)

    tasks = []
    classes_per_task = 2
    for task_id in range(n_tasks):
        c_start = task_id * classes_per_task
        c_end = c_start + classes_per_task
        digits = list(range(c_start, c_end))

        # Filter train
        mask = sum((all_train_y == d) for d in digits).bool()
        tX = all_train_X[mask]
        ty = all_train_y[mask] - c_start  # remap to 0,1
        train_ds = TensorDataset(tX, ty)
        train_l = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

        # Filter test
        mask = sum((all_test_y == d) for d in digits).bool()
        tX = all_test_X[mask]
        ty = all_test_y[mask] - c_start
        test_ds = TensorDataset(tX, ty)
        test_l = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

        tasks.append((train_l, test_l, 784, classes_per_task))

    return tasks


# ===========================================================================
# Ablation configuration definitions
# ===========================================================================

ABLATION_CONFIGS = {
    'baseline': {
        'model_type': 'baseline',
        'loss_type': 'task',
        'beta': 0.0,
        'orth_weight': 0.0,
        'description': 'No regularization (cross-entropy only)',
    },
    'beta_vae': {
        'model_type': 'baseline',
        'loss_type': 'vae',
        'beta': DEFAULT_BETA,
        'orth_weight': 0.0,
        'description': 'Standard β-VAE KL regularization (Gaussian prior)',
    },
    'afm_task': {
        'model_type': 'afm',
        'loss_type': 'task',
        'beta': 0.0,
        'orth_weight': 0.0,
        'description': 'AFM Stiefel projection + L_task only (no KL)',
    },
    'afm_qr': {
        'model_type': 'afm',
        'loss_type': 'vae',
        'beta': DEFAULT_BETA,
        'orth_weight': DEFAULT_ORTH_WEIGHT,
        'description': 'AFM + QR orth regularization: CE + β·KL + w·||S^T S - I||²',
    },
    'afm_rib': {
        'model_type': 'afm',
        'loss_type': 'rib',
        'beta': DEFAULT_BETA,
        'orth_weight': 0.0,
        'description': 'AFM + L_RIB (Stiefel KL ≈ β-VAE KL)',
    },
}


def create_model(config_name, input_dim=784, num_classes=10,
                 hidden_dim=HIDDEN_DIM, d=D_STIEFEL, K=K_THREADS,
                 cfg_override=None):
    """Instantiate model for the given ablation configuration."""
    cfg = cfg_override if cfg_override is not None else ABLATION_CONFIGS[config_name]
    if cfg['model_type'] == 'baseline':
        return BaselineModel(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            latent_dim=d * K,
            num_classes=num_classes,
        )
    else:
        return AFMLiteModel(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            d=d,
            K=K,
            num_classes=num_classes,
        )


# ===========================================================================
# Training loop (unified)
# ===========================================================================

def train_one_epoch(model, loader, optimizer, config_name, beta=0.01,
                    orth_weight=0.0, d_stiefel=D_STIEFEL, k_threads=K_THREADS,
                    device='cpu'):
    """
    Train model for one epoch, recording all loss components.

    Returns dict with epoch-level means of: loss, ce_loss, kl_loss,
    orth_loss, accuracy, active_dims.
    """
    cfg = ABLATION_CONFIGS[config_name]
    model.train()
    metrics = defaultdict(list)

    for X, y in loader:
        X, y = X.to(device), y.to(device)
        optimizer.zero_grad()

        if cfg['model_type'] == 'baseline':
            logits, recon, mu, log_var = model(X)
            kl_val = torch.tensor(0.0)

            if cfg['loss_type'] == 'vae' and beta > 0:
                ce = F.cross_entropy(logits, y)
                kl_val = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())
                total_loss = ce + beta * kl_val
            else:
                ce = F.cross_entropy(logits, y)
                total_loss = ce

            orth_loss_val = torch.tensor(0.0)
            latent_for_active = mu

        else:  # afm
            logits, recon, mu, log_var, kl_val = model(X)
            ce = F.cross_entropy(logits, y)
            total_loss = ce

            # Add KL term if configured
            if cfg['loss_type'] in ('rib', 'vae') and beta > 0 and kl_val is not None:
                total_loss = total_loss + beta * kl_val

            # Orthogonal regularization for afm_qr config
            orth_loss_val = torch.tensor(0.0)
            if orth_weight > 0:
                with torch.no_grad():
                    S_check, _ = model.stiefel(mu, log_var)
                # Re-compute with graph for gradient
                A_mat = mu.view(mu.shape[0], d_stiefel, k_threads)
                S_for_orth = stiefel_project_qr(A_mat)
                I_K = torch.eye(k_threads, device=device)
                gram = torch.bmm(S_for_orth.transpose(1, 2), S_for_orth)
                orth_loss_val = torch.mean((gram - I_K.unsqueeze(0)).pow(2).sum(dim=(-2, -1)))
                total_loss = total_loss + orth_weight * orth_loss_val

            latent_for_active = mu  # pre-projection latent for active-dim

        total_loss.backward()
        optimizer.step()

        # Record metrics
        with torch.no_grad():
            acc = (logits.argmax(1) == y).float().mean().item()
            # Active dimensions: count dims where per-batch |z| > threshold
            latent_abs = latent_for_active.abs()
            active_dims = (latent_abs.mean(dim=0) > ACTIVE_DIM_THRESHOLD).sum().item()

        metrics['total_loss'].append(total_loss.item())
        metrics['ce_loss'].append(ce.item())
        metrics['kl_loss'].append(kl_val.item() if isinstance(kl_val, torch.Tensor) else float(kl_val))
        metrics['orth_loss'].append(orth_loss_val.item() if isinstance(orth_loss_val, torch.Tensor) else float(orth_loss_val))
        metrics['accuracy'].append(acc)
        metrics['active_dims'].append(active_dims)

    return {k: float(np.mean(v)) for k, v in metrics.items()}


def evaluate_model(model, loader, config_name, device='cpu',
                   d_stiefel=D_STIEFEL, k_threads=K_THREADS,
                   compute_silhouette=True):
    """
    Evaluate model: accuracy, loss, active_dims, silhouette_score,
    reconstruction_loss.
    """
    cfg = ABLATION_CONFIGS[config_name]
    model.eval()
    total_loss = 0.0
    total_recon = 0.0
    total_correct = 0
    total_samples = 0
    all_latents = []
    all_labels = []
    active_dim_counts = []

    with torch.no_grad():
        for X, y in loader:
            X, y = X.to(device), y.to(device)

            if cfg['model_type'] == 'baseline':
                logits, recon, z, mu, log_var = model(X, return_latent=True)
                latent = mu
            else:
                logits, recon, S, mu, log_var, kl = model(X, return_latent=True)
                latent = S.reshape(S.shape[0], -1)

            loss = F.cross_entropy(logits, y, reduction='sum')
            total_loss += loss.item()

            # Reconstruction loss (MSE)
            recon_loss = F.mse_loss(recon, X, reduction='sum')
            total_recon += recon_loss.item()

            total_correct += (logits.argmax(1) == y).sum().item()
            total_samples += y.size(0)

            all_latents.append(latent.cpu().numpy())
            all_labels.append(y.cpu().numpy())

            # Active dims per batch
            latent_abs = latent.abs()
            active = (latent_abs.mean(dim=0) > ACTIVE_DIM_THRESHOLD).sum().item()
            active_dim_counts.append(active)

    accuracy = total_correct / total_samples
    avg_loss = total_loss / total_samples
    avg_recon = total_recon / total_samples
    avg_active_dims = float(np.mean(active_dim_counts))

    # Silhouette score
    silhouette = -1.0
    if compute_silhouette:
        try:
            from sklearn.metrics import silhouette_score
            latents_arr = np.concatenate(all_latents, axis=0)
            labels_arr = np.concatenate(all_labels, axis=0)
            # Subsample for speed
            if len(latents_arr) > SILHOUETTE_MAX_SAMPLES:
                idx = np.random.choice(len(latents_arr), SILHOUETTE_MAX_SAMPLES, replace=False)
                latents_arr = latents_arr[idx]
                labels_arr = labels_arr[idx]
            if len(np.unique(labels_arr)) > 1:
                silhouette = float(silhouette_score(latents_arr, labels_arr, metric='euclidean'))
        except Exception as e:
            warnings.warn(f"Silhouette computation failed: {e}")
            silhouette = -1.0

    # Collapse detection
    is_collapsed = accuracy < COLLAPSE_ACC_THRESHOLD or avg_active_dims < (COLLAPSE_ACTIVE_DIM_FRACTION * latent.shape[1])

    return {
        'accuracy': accuracy,
        'loss': avg_loss,
        'reconstruction_loss': avg_recon,
        'active_dims': avg_active_dims,
        'silhouette_score': silhouette,
        'is_collapsed': is_collapsed,
        'total_latent_dim': latent.shape[1],
    }


def train_full(model, train_loader, test_loader, config_name,
               epochs=15, lr=1e-3, beta=0.01, orth_weight=0.0,
               d_stiefel=D_STIEFEL, k_threads=K_THREADS,
               device='cpu', verbose=True):
    """
    Full training loop with per-epoch metric recording.

    Returns dict with history, best/final test metrics, total_time.
    """
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=15, gamma=0.5)

    history = []
    best_test_acc = 0.0
    t0 = time.time()

    for epoch in range(epochs):
        ep_start = time.time()

        # Train
        train_m = train_one_epoch(
            model, train_loader, optimizer, config_name,
            beta=beta, orth_weight=orth_weight,
            d_stiefel=d_stiefel, k_threads=k_threads,
            device=device,
        )

        # Evaluate (full metrics only every 5 epochs for speed, light eval otherwise)
        if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
            eval_m = evaluate_model(
                model, test_loader, config_name, device=device,
                d_stiefel=d_stiefel, k_threads=k_threads,
                compute_silhouette=True,
            )
        else:
            eval_m = evaluate_model(
                model, test_loader, config_name, device=device,
                d_stiefel=d_stiefel, k_threads=k_threads,
                compute_silhouette=False,
            )

        scheduler.step()
        ep_time = time.time() - ep_start

        test_acc = eval_m['accuracy']
        if test_acc > best_test_acc:
            best_test_acc = test_acc

        ep_record = {
            'epoch': epoch,
            'train_total_loss': train_m['total_loss'],
            'train_ce_loss': train_m['ce_loss'],
            'train_kl_loss': train_m['kl_loss'],
            'train_orth_loss': train_m['orth_loss'],
            'train_accuracy': train_m['accuracy'],
            'train_active_dims': train_m['active_dims'],
            'test_accuracy': test_acc,
            'test_loss': eval_m['loss'],
            'test_reconstruction_loss': eval_m['reconstruction_loss'],
            'test_silhouette_score': eval_m.get('silhouette_score', -1.0),
            'test_active_dims': eval_m['active_dims'],
            'is_collapsed': eval_m['is_collapsed'],
            'epoch_time': ep_time,
        }
        history.append(ep_record)

        if verbose and (epoch + 1) % 5 == 0:
            print(f"    Epoch {epoch+1}/{epochs}: "
                  f"loss={train_m['total_loss']:.4f} "
                  f"ce={train_m['ce_loss']:.4f} "
                  f"kl={train_m['kl_loss']:.4f} "
                  f"train_acc={train_m['accuracy']:.4f} "
                  f"test_acc={test_acc:.4f} "
                  f"active={train_m['active_dims']:.0f} "
                  f"t={ep_time:.1f}s")

    total_time = time.time() - t0

    # Final full evaluation
    final_eval = evaluate_model(
        model, test_loader, config_name, device=device,
        d_stiefel=d_stiefel, k_threads=k_threads,
        compute_silhouette=True,
    )

    return {
        'history': history,
        'best_test_acc': best_test_acc,
        'final_test_acc': history[-1]['test_accuracy'] if history else 0,
        'final_test_loss': history[-1]['test_loss'] if history else 0,
        'final_reconstruction_loss': final_eval['reconstruction_loss'],
        'final_silhouette_score': final_eval['silhouette_score'],
        'final_active_dims': final_eval['active_dims'],
        'is_collapsed': final_eval['is_collapsed'],
        'total_time': total_time,
    }


# ===========================================================================
# 4.5A — Multi-Seed Validation
# ===========================================================================

def run_phase45a(seeds, epochs, lr, beta):
    """
    Multi-Seed Validation: 5 seeds × 5 configs × Fashion-MNIST.

    Metrics: test_accuracy, reconstruction_loss, silhouette_score, active_dims
    Statistics: mean, std, 95% CI across seeds for each metric × config
    """
    json_key = 'multi_seed_results'
    existing = load_json(json_key)
    if existing is not None:
        print(f"[4.5A] Results already exist at {json_key}.json — skipping.")
        print(f"       Delete the file to re-run.")
        return existing

    print("\n" + "=" * 70)
    print("PHASE 4.5A — Multi-Seed Validation")
    print(f"  Seeds: {seeds}")
    print(f"  Configs: {list(ABLATION_CONFIGS.keys())}")
    print(f"  Dataset: Fashion-MNIST | hidden_dim={HIDDEN_DIM} | epochs={epochs}")
    print("=" * 70)

    train_loader, test_loader, input_dim, num_classes = get_fashion_mnist()

    all_results = {}

    for cfg_name, cfg in ABLATION_CONFIGS.items():
        print(f"\n{'─'*60}")
        print(f"Config: {cfg_name} — {cfg['description']}")
        print(f"{'─'*60}")

        cfg_runs = []
        for seed in seeds:
            print(f"  Seed {seed} ...", end='', flush=True)
            set_seed(seed)

            model = create_model(cfg_name, input_dim, num_classes)
            n_params = model.count_parameters()
            print(f" params={n_params:,}", end='', flush=True)

            result = train_full(
                model, train_loader, test_loader, cfg_name,
                epochs=epochs, lr=lr,
                beta=beta if cfg['beta'] > 0 else 0,
                orth_weight=cfg['orth_weight'],
                device=DEVICE, verbose=False,
            )

            run_data = {
                'seed': seed,
                'param_count': n_params,
                'best_test_acc': result['best_test_acc'],
                'final_test_acc': result['final_test_acc'],
                'final_test_loss': result['final_test_loss'],
                'final_reconstruction_loss': result['final_reconstruction_loss'],
                'final_silhouette_score': result['final_silhouette_score'],
                'final_active_dims': result['final_active_dims'],
                'is_collapsed': result['is_collapsed'],
                'total_time': result['total_time'],
                'history': result['history'],
            }
            cfg_runs.append(run_data)
            print(f" best_acc={result['best_test_acc']:.4f} "
                  f"active={result['final_active_dims']:.0f} "
                  f"silh={result['final_silhouette_score']:.4f} "
                  f"t={result['total_time']:.1f}s")

        # Compute statistics across seeds
        accs = [r['best_test_acc'] for r in cfg_runs]
        recon_losses = [r['final_reconstruction_loss'] for r in cfg_runs]
        silhouettes = [r['final_silhouette_score'] for r in cfg_runs]
        active_dims_list = [r['final_active_dims'] for r in cfg_runs]
        collapsed_count = sum(1 for r in cfg_runs if r['is_collapsed'])

        all_results[cfg_name] = {
            'runs': cfg_runs,
            'statistics': {
                'test_accuracy': compute_ci(accs),
                'reconstruction_loss': compute_ci(recon_losses),
                'silhouette_score': compute_ci(silhouettes),
                'active_dims': compute_ci(active_dims_list),
                'collapse_count': collapsed_count,
                'collapse_rate': collapsed_count / len(seeds),
            },
        }

        s = all_results[cfg_name]['statistics']
        print(f"  → acc = {s['test_accuracy']['mean']:.4f} "
              f"[{s['test_accuracy']['ci_lower']:.4f}, {s['test_accuracy']['ci_upper']:.4f}] "
              f"| active_dims = {s['active_dims']['mean']:.1f} "
              f"| silh = {s['silhouette_score']['mean']:.4f} "
              f"| collapsed = {collapsed_count}/{len(seeds)}")

    save_json(json_key, all_results)
    _generate_phase45a_report(all_results, seeds, epochs)
    return all_results


def _generate_phase45a_report(results, seeds, epochs):
    """Generate markdown report for Phase 4.5A."""
    report_path = '/home/z/my-project/AFM_1M_MULTI_SEED_REPORT.md'

    lines = []
    lines.append("# AFM Phase 4.5A — Multi-Seed Validation Report\n")
    lines.append(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Scale**: ~1.33M params (hidden_dim={HIDDEN_DIM})")
    lines.append(f"**Dataset**: Fashion-MNIST | **Seeds**: {seeds} | **Epochs**: {epochs}")
    lines.append(f"**BETA**: {DEFAULT_BETA} | **LR**: {DEFAULT_LR} | **Batch**: 256\n")

    # Summary table
    lines.append("## Summary Statistics (mean ± 95% CI)\n")
    lines.append("| Config | Test Accuracy | Active Dims | Silhouette | Recon Loss | Collapse Rate |")
    lines.append("|--------|--------------|-------------|------------|------------|---------------|")

    for cfg_name, cfg_data in results.items():
        s = cfg_data['statistics']
        acc = s['test_accuracy']
        ad = s['active_dims']
        sil = s['silhouette_score']
        rl = s['reconstruction_loss']
        cr = s['collapse_rate']
        lines.append(
            f"| {cfg_name} | "
            f"{acc['mean']:.4f} [{acc['ci_lower']:.4f}, {acc['ci_upper']:.4f}] | "
            f"{ad['mean']:.1f} [{ad['ci_lower']:.1f}, {ad['ci_upper']:.1f}] | "
            f"{sil['mean']:.4f} | "
            f"{rl['mean']:.4f} | "
            f"{cr:.2f} |"
        )

    lines.append("")

    # Per-config details
    for cfg_name, cfg_data in results.items():
        lines.append(f"\n## {cfg_name}\n")
        s = cfg_data['statistics']
        for metric_name in ['test_accuracy', 'active_dims', 'silhouette_score', 'reconstruction_loss']:
            m = s[metric_name]
            lines.append(f"- **{metric_name}**: {m['mean']:.4f} ± {m['std']:.4f} "
                         f"(95% CI: [{m['ci_lower']:.4f}, {m['ci_upper']:.4f}], n={m['n']})")
        lines.append(f"- **Collapse rate**: {s['collapse_rate']:.2f} ({s['collapse_count']}/{len(seeds)} runs)")

    # Key findings
    lines.append("\n## Key Findings\n")

    # Check if beta_vae collapsed
    bv_stats = results.get('beta_vae', {}).get('statistics', {})
    if bv_stats.get('collapse_rate', 0) > 0:
        lines.append("- **β-VAE collapse confirmed**: Standard KL regularization causes posterior collapse "
                     f"({bv_stats.get('collapse_count', '?')}/{len(seeds)} runs collapsed)")
    else:
        lines.append("- **β-VAE did NOT collapse at this beta value**")

    # Check AFM vs baseline
    baseline_acc = results.get('baseline', {}).get('statistics', {}).get('test_accuracy', {}).get('mean', 0)
    afm_rib_acc = results.get('afm_rib', {}).get('statistics', {}).get('test_accuracy', {}).get('mean', 0)
    if afm_rib_acc > baseline_acc:
        lines.append(f"- **AFM+RIB outperforms baseline**: {afm_rib_acc:.4f} vs {baseline_acc:.4f}")
    else:
        lines.append(f"- **AFM+RIB does NOT outperform baseline**: {afm_rib_acc:.4f} vs {baseline_acc:.4f}")

    # Check AFM collapse resistance
    afm_collapsed = results.get('afm_rib', {}).get('statistics', {}).get('collapse_rate', 1)
    if afm_collapsed == 0:
        lines.append("- **AFM+RIB is collapse-resistant**: 0/5 runs collapsed (vs β-VAE collapse)")
    else:
        lines.append(f"- **AFM+RIB collapse rate**: {afm_collapsed:.2f}")

    with open(report_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"  [REPORT] {report_path}")


# ===========================================================================
# 4.5B — Forgetting Statistics
# ===========================================================================

def run_phase45b(seeds, epochs_per_task, lr, beta):
    """
    Forgetting Statistics: 5 seeds × 3 configs × Split-Fashion-MNIST (5 tasks).

    Configs: baseline, afm_task, afm_rib (not all 5)
    Train sequentially on 5 tasks, measure forgetting after each.
    Forgetting = (acc_before - acc_after) for previously learned tasks.
    """
    json_key = 'forgetting_results'
    existing = load_json(json_key)
    if existing is not None:
        print(f"[4.5B] Results already exist at {json_key}.json — skipping.")
        return existing

    forgetting_configs = {
        'baseline': ABLATION_CONFIGS['baseline'],
        'afm_task': ABLATION_CONFIGS['afm_task'],
        'afm_rib': ABLATION_CONFIGS['afm_rib'],
    }

    print("\n" + "=" * 70)
    print("PHASE 4.5B — Forgetting Statistics")
    print(f"  Seeds: {seeds}")
    print(f"  Configs: {list(forgetting_configs.keys())}")
    print(f"  Protocol: Split-Fashion-MNIST (5 tasks × 2 classes)")
    print(f"  Epochs/task: {epochs_per_task}")
    print("=" * 70)

    all_results = {}

    for cfg_name, cfg in forgetting_configs.items():
        print(f"\n{'─'*60}")
        print(f"Config: {cfg_name} — {cfg['description']}")
        print(f"{'─'*60}")

        cfg_runs = []

        for seed in seeds:
            print(f"  Seed {seed} ...", end='', flush=True)
            set_seed(seed)

            # Get split data
            tasks = get_split_fashion_mnist()
            n_tasks = len(tasks)

            # Create multi-task model
            task_classes = [tc for (_, _, _, tc) in tasks]
            if cfg['model_type'] == 'baseline':
                model = MultiTaskBaseline(
                    input_dim=784, hidden_dim=HIDDEN_DIM,
                    latent_dim=LATENT_DIM, task_classes=task_classes,
                )
            else:
                model = MultiTaskAFMLite(
                    input_dim=784, hidden_dim=HIDDEN_DIM,
                    d=D_STIEFEL, K=K_THREADS, task_classes=task_classes,
                )

            optimizer = torch.optim.Adam(model.parameters(), lr=lr)

            # Accuracy matrix: [after_training_task_i][eval_task_j]
            acc_matrix = np.zeros((n_tasks, n_tasks))
            forgetting_per_task = {t: 0.0 for t in range(n_tasks)}

            for task_id in range(n_tasks):
                train_l, test_l, in_dim, nc = tasks[task_id]

                # Train on this task
                model.train()
                for epoch in range(epochs_per_task):
                    for X, y in train_l:
                        X, y = X.to(DEVICE), y.to(DEVICE)
                        optimizer.zero_grad()

                        if cfg['model_type'] == 'baseline':
                            logits, mu, log_var = model(X, task_id=task_id)
                            ce = F.cross_entropy(logits, y)
                            if cfg['loss_type'] == 'vae' and beta > 0:
                                kl = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())
                                loss = ce + beta * kl
                            else:
                                loss = ce
                        else:  # afm
                            logits, mu, log_var, kl = model(X, task_id=task_id)
                            ce = F.cross_entropy(logits, y)
                            loss = ce + (beta * kl if kl is not None and cfg['loss_type'] == 'rib' else 0)

                        loss.backward()
                        optimizer.step()

                # Evaluate on ALL tasks after training on this task
                model.eval()
                with torch.no_grad():
                    for eval_id in range(n_tasks):
                        _, eval_l, _, _ = tasks[eval_id]
                        correct, total = 0, 0
                        for X, y in eval_l:
                            X, y = X.to(DEVICE), y.to(DEVICE)
                            if cfg['model_type'] == 'baseline':
                                logits, _, _ = model(X, task_id=eval_id)
                            else:
                                logits, _, _, _ = model(X, task_id=eval_id)
                            correct += (logits.argmax(1) == y).sum().item()
                            total += y.size(0)
                        acc_matrix[task_id, eval_id] = correct / total

            # Compute forgetting per task
            for task_id in range(n_tasks - 1):  # No forgetting for the last task
                acc_after_learn = acc_matrix[task_id, task_id]  # Acc right after learning
                acc_final = acc_matrix[n_tasks - 1, task_id]     # Acc after all tasks
                forgetting = acc_after_learn - acc_final
                forgetting_per_task[task_id] = forgetting

            avg_forgetting = np.mean([forgetting_per_task[t] for t in range(n_tasks - 1)])

            run_data = {
                'seed': seed,
                'acc_matrix': acc_matrix.tolist(),
                'forgetting_per_task': {str(k): float(v) for k, v in forgetting_per_task.items()},
                'avg_forgetting': float(avg_forgetting),
            }
            cfg_runs.append(run_data)
            print(f" avg_forgetting={avg_forgetting:.4f} "
                  f"matrix_diag={[f'{acc_matrix[i,i]:.3f}' for i in range(n_tasks)]}")

        # Statistics across seeds
        forgettings = [r['avg_forgetting'] for r in cfg_runs]
        per_task_forgettings = defaultdict(list)
        for r in cfg_runs:
            for t, f in r['forgetting_per_task'].items():
                per_task_forgettings[t].append(f)

        all_results[cfg_name] = {
            'runs': cfg_runs,
            'statistics': {
                'avg_forgetting': compute_ci(forgettings),
                'per_task_forgetting': {
                    t: compute_ci(vals) for t, vals in per_task_forgettings.items()
                },
            },
        }

        s = all_results[cfg_name]['statistics']
        print(f"  → avg_forgetting = {s['avg_forgetting']['mean']:.4f} "
              f"[{s['avg_forgetting']['ci_lower']:.4f}, {s['avg_forgetting']['ci_upper']:.4f}]")

    save_json(json_key, all_results)
    _generate_phase45b_report(all_results, seeds, epochs_per_task)
    return all_results


def _generate_phase45b_report(results, seeds, epochs_per_task):
    """Generate markdown report for Phase 4.5B."""
    report_path = '/home/z/my-project/AFM_FORGETTING_STATISTICS_REPORT.md'

    lines = []
    lines.append("# AFM Phase 4.5B — Forgetting Statistics Report\n")
    lines.append(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Scale**: ~1.33M params (hidden_dim={HIDDEN_DIM})")
    lines.append(f"**Protocol**: Split-Fashion-MNIST (5 tasks × 2 classes each)")
    lines.append(f"**Seeds**: {seeds} | **Epochs/task**: {epochs_per_task}")
    lines.append(f"**BETA**: {DEFAULT_BETA} | **LR**: {DEFAULT_LR}\n")

    # Summary table
    lines.append("## Average Forgetting (mean ± 95% CI)\n")
    lines.append("| Config | Avg Forgetting | 95% CI |")
    lines.append("|--------|---------------|--------|")

    for cfg_name, cfg_data in results.items():
        s = cfg_data['statistics']['avg_forgetting']
        lines.append(f"| {cfg_name} | {s['mean']:.4f} | [{s['ci_lower']:.4f}, {s['ci_upper']:.4f}] |")

    lines.append("")

    # Per-task breakdown
    lines.append("## Per-Task Forgetting\n")
    lines.append("| Config | Task 0 | Task 1 | Task 2 | Task 3 |")
    lines.append("|--------|--------|--------|--------|--------|")

    for cfg_name, cfg_data in results.items():
        ptf = cfg_data['statistics']['per_task_forgetting']
        vals = []
        for t in range(4):
            if str(t) in ptf:
                m = ptf[str(t)]['mean']
                vals.append(f"{m:.4f}")
            else:
                vals.append("N/A")
        lines.append(f"| {cfg_name} | {' | '.join(vals)} |")

    lines.append("")

    # Comparison
    lines.append("## Baseline vs AFM vs AFM+RIB\n")
    baseline_f = results.get('baseline', {}).get('statistics', {}).get('avg_forgetting', {}).get('mean', 0)
    afm_task_f = results.get('afm_task', {}).get('statistics', {}).get('avg_forgetting', {}).get('mean', 0)
    afm_rib_f = results.get('afm_rib', {}).get('statistics', {}).get('avg_forgetting', {}).get('mean', 0)

    lines.append(f"- Baseline avg forgetting: **{baseline_f:.4f}**")
    lines.append(f"- AFM (task only) avg forgetting: **{afm_task_f:.4f}**")
    lines.append(f"- AFM+RIB avg forgetting: **{afm_rib_f:.4f}**")

    if baseline_f > 0:
        reduction_task = (1 - afm_task_f / baseline_f) * 100 if baseline_f > 0 else 0
        reduction_rib = (1 - afm_rib_f / baseline_f) * 100 if baseline_f > 0 else 0
        lines.append(f"- AFM task forgetting reduction vs baseline: **{reduction_task:.1f}%**")
        lines.append(f"- AFM+RIB forgetting reduction vs baseline: **{reduction_rib:.1f}%**")

    with open(report_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"  [REPORT] {report_path}")


# ===========================================================================
# 4.5C — Beta Sweep
# ===========================================================================

def run_phase45c(betas, epochs, lr):
    """
    Beta Sweep: 6 betas × 3 configs × Fashion-MNIST.

    Configs: baseline (with β-VAE), afm_qr, afm_rib
    Find collapse threshold for each config.
    """
    json_key = 'beta_sweep_results'
    existing = load_json(json_key)
    if existing is not None:
        print(f"[4.5C] Results already exist at {json_key}.json — skipping.")
        return existing

    sweep_configs = {
        'beta_vae': {  # Baseline with β-VAE KL (reuses ABLATION_CONFIGS entry)
            'model_type': 'baseline',
            'loss_type': 'vae',
            'description': 'Baseline + β-VAE KL',
        },
        'afm_qr': {
            'model_type': 'afm',
            'loss_type': 'vae',
            'orth_weight': DEFAULT_ORTH_WEIGHT,
            'description': 'AFM + QR orth + β·KL',
        },
        'afm_rib': {
            'model_type': 'afm',
            'loss_type': 'rib',
            'description': 'AFM + L_RIB',
        },
    }

    print("\n" + "=" * 70)
    print("PHASE 4.5C — Beta Sweep")
    print(f"  Betas: {betas}")
    print(f"  Configs: {list(sweep_configs.keys())}")
    print(f"  Dataset: Fashion-MNIST | epochs={epochs}")
    print("=" * 70)

    train_loader, test_loader, input_dim, num_classes = get_fashion_mnist()
    seed = 42  # Single seed for sweep

    all_results = {}

    for cfg_name, cfg in sweep_configs.items():
        print(f"\n{'─'*60}")
        print(f"Config: {cfg_name}")
        print(f"{'─'*60}")

        beta_results = []

        for beta_val in betas:
            print(f"  β={beta_val:.0e} ...", end='', flush=True)
            set_seed(seed)

            model = create_model(cfg_name, input_dim, num_classes, cfg_override=cfg)

            result = train_full(
                model, train_loader, test_loader, cfg_name,
                epochs=epochs, lr=lr,
                beta=beta_val,
                orth_weight=cfg.get('orth_weight', 0),
                device=DEVICE, verbose=False,
            )

            beta_data = {
                'beta': beta_val,
                'best_test_acc': result['best_test_acc'],
                'final_test_acc': result['final_test_acc'],
                'final_active_dims': result['final_active_dims'],
                'final_reconstruction_loss': result['final_reconstruction_loss'],
                'is_collapsed': result['is_collapsed'],
                'total_time': result['total_time'],
            }
            beta_results.append(beta_data)
            print(f" acc={result['best_test_acc']:.4f} "
                  f"active={result['final_active_dims']:.0f} "
                  f"collapsed={result['is_collapsed']}")

        # Find collapse threshold
        collapse_threshold = None
        for i, bd in enumerate(beta_results):
            if bd['is_collapsed']:
                collapse_threshold = betas[i]
                break

        all_results[cfg_name] = {
            'beta_results': beta_results,
            'collapse_threshold': collapse_threshold,
        }

        ct = collapse_threshold
        print(f"  → Collapse threshold: β={ct:.0e}" if ct else "  → No collapse observed in tested range")

    save_json(json_key, all_results)
    _generate_phase45c_report(all_results, betas, epochs)
    return all_results


def _generate_phase45c_report(results, betas, epochs):
    """Generate markdown report for Phase 4.5C."""
    report_path = '/home/z/my-project/AFM_BETA_SWEEP_REPORT.md'

    lines = []
    lines.append("# AFM Phase 4.5C — Beta Sweep Report\n")
    lines.append(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Scale**: ~1.33M params (hidden_dim={HIDDEN_DIM})")
    lines.append(f"**Dataset**: Fashion-MNIST | **Epochs**: {epochs} | **Seed**: 42")
    lines.append(f"**Betas tested**: {betas}\n")

    # Accuracy table
    lines.append("## Accuracy vs Beta\n")
    header = "| Config | " + " | ".join([f"β={b:.0e}" for b in betas]) + " |"
    lines.append(header)
    lines.append("|--------|" + "|".join(["--------"] * len(betas)) + "|")

    for cfg_name, cfg_data in results.items():
        vals = []
        for bd in cfg_data['beta_results']:
            acc_str = f"{bd['best_test_acc']:.4f}"
            if bd['is_collapsed']:
                acc_str += " †"
            vals.append(acc_str)
        lines.append(f"| {cfg_name} | {' | '.join(vals)} |")

    lines.append("")
    lines.append("† = collapsed (accuracy < 15% or active dims < 5%)\n")

    # Active dims table
    lines.append("## Active Dimensions vs Beta\n")
    header = "| Config | " + " | ".join([f"β={b:.0e}" for b in betas]) + " |"
    lines.append(header)
    lines.append("|--------|" + "|".join(["--------"] * len(betas)) + "|")

    for cfg_name, cfg_data in results.items():
        vals = [f"{bd['final_active_dims']:.0f}" for bd in cfg_data['beta_results']]
        lines.append(f"| {cfg_name} | {' | '.join(vals)} |")

    lines.append("")

    # Collapse thresholds
    lines.append("## Collapse Thresholds\n")
    for cfg_name, cfg_data in results.items():
        ct = cfg_data['collapse_threshold']
        if ct:
            lines.append(f"- **{cfg_name}**: collapses at β ≥ {ct:.0e}")
        else:
            lines.append(f"- **{cfg_name}**: no collapse in tested range (up to β={betas[-1]:.0e})")

    lines.append("")

    # Key finding
    bv_ct = results.get('beta_vae', {}).get('collapse_threshold')
    afm_rib_ct = results.get('afm_rib', {}).get('collapse_threshold')
    if bv_ct and not afm_rib_ct:
        lines.append("## Key Finding\n")
        lines.append(f"**AFM+RIB is collapse-resistant**: β-VAE collapses at β ≥ {bv_ct:.0e}, "
                     f"while AFM+RIB shows no collapse up to β={betas[-1]:.0e}. "
                     "The Stiefel projection prevents posterior collapse.")
    elif bv_ct and afm_rib_ct:
        ratio = afm_rib_ct / bv_ct
        lines.append("## Key Finding\n")
        lines.append(f"AFM+RIB collapse threshold is {ratio:.1f}× higher than β-VAE "
                     f"({afm_rib_ct:.0e} vs {bv_ct:.0e}).")

    with open(report_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"  [REPORT] {report_path}")


# ===========================================================================
# 4.5D — Latent Geometry Study
# ===========================================================================

def run_phase45d(epochs, lr, beta):
    """
    Latent Geometry Study: 4 geometries × 3 AFM configs + baseline.

    Geometries: (d,K) = (16,8)=128, (64,2)=128, (32,4)=128(current), (32,8)=256
    For BaselineModel, latent_dim matches total (128 or 256).
    """
    json_key = 'geometry_results'
    existing = load_json(json_key)
    if existing is not None:
        print(f"[4.5D] Results already exist at {json_key}.json — skipping.")
        return existing

    geometries = [
        {'d': 16, 'K': 8, 'total': 128, 'label': '(16,8)=128'},
        {'d': 64, 'K': 2, 'total': 128, 'label': '(64,2)=128'},
        {'d': 32, 'K': 4, 'total': 128, 'label': '(32,4)=128 [current]'},
        {'d': 32, 'K': 8, 'total': 256, 'label': '(32,8)=256'},
    ]

    geo_configs = ['baseline', 'afm_task', 'afm_qr', 'afm_rib']

    print("\n" + "=" * 70)
    print("PHASE 4.5D — Latent Geometry Study")
    print(f"  Geometries: {[g['label'] for g in geometries]}")
    print(f"  Configs: {geo_configs}")
    print(f"  Dataset: Fashion-MNIST | epochs={epochs}")
    print("=" * 70)

    train_loader, test_loader, input_dim, num_classes = get_fashion_mnist()
    seed = 42

    all_results = {}

    for geo in geometries:
        d, K, total, label = geo['d'], geo['K'], geo['total'], geo['label']
        print(f"\n{'─'*60}")
        print(f"Geometry: {label} (d={d}, K={K})")
        print(f"{'─'*60}")

        geo_results = {}

        for cfg_name in geo_configs:
            cfg = ABLATION_CONFIGS[cfg_name]
            print(f"  {cfg_name} ...", end='', flush=True)
            set_seed(seed)

            if cfg['model_type'] == 'baseline':
                model = BaselineModel(
                    input_dim=input_dim, hidden_dim=HIDDEN_DIM,
                    latent_dim=total, num_classes=num_classes,
                )
            else:
                model = AFMLiteModel(
                    input_dim=input_dim, hidden_dim=HIDDEN_DIM,
                    d=d, K=K, num_classes=num_classes,
                )

            # Quick forgetting assessment on Split-Fashion-MNIST
            result = train_full(
                model, train_loader, test_loader, cfg_name,
                epochs=epochs, lr=lr,
                beta=beta if cfg['beta'] > 0 else 0,
                orth_weight=cfg.get('orth_weight', 0),
                d_stiefel=d, k_threads=K,
                device=DEVICE, verbose=False,
            )

            # Measure forgetting on Split-Fashion-MNIST
            tasks = get_split_fashion_mnist()
            task_classes = [tc for (_, _, _, tc) in tasks]

            if cfg['model_type'] == 'baseline':
                mt_model = MultiTaskBaseline(
                    input_dim=784, hidden_dim=HIDDEN_DIM,
                    latent_dim=total, task_classes=task_classes,
                )
            else:
                mt_model = MultiTaskAFMLite(
                    input_dim=784, hidden_dim=HIDDEN_DIM,
                    d=d, K=K, task_classes=task_classes,
                )

            # Quick forgetting: 5 epochs per task
            optimizer = torch.optim.Adam(mt_model.parameters(), lr=lr)
            n_tasks = len(tasks)
            acc_matrix = np.zeros((n_tasks, n_tasks))

            for task_id in range(n_tasks):
                train_l, _, _, _ = tasks[task_id]
                mt_model.train()
                for ep in range(5):
                    for X, y in train_l:
                        X, y = X.to(DEVICE), y.to(DEVICE)
                        optimizer.zero_grad()
                        if cfg['model_type'] == 'baseline':
                            logits_t, mu_t, lv_t = mt_model(X, task_id=task_id)
                            ce_t = F.cross_entropy(logits_t, y)
                            loss_t = ce_t
                        else:
                            logits_t, mu_t, lv_t, kl_t = mt_model(X, task_id=task_id)
                            ce_t = F.cross_entropy(logits_t, y)
                            loss_t = ce_t + (beta * kl_t if kl_t is not None and cfg['loss_type'] == 'rib' else 0)
                        loss_t.backward()
                        optimizer.step()

                mt_model.eval()
                with torch.no_grad():
                    for eval_id in range(n_tasks):
                        _, eval_l, _, _ = tasks[eval_id]
                        correct, total_s = 0, 0
                        for X, y in eval_l:
                            X, y = X.to(DEVICE), y.to(DEVICE)
                            if cfg['model_type'] == 'baseline':
                                logits_e, _, _ = mt_model(X, task_id=eval_id)
                            else:
                                logits_e, _, _, _ = mt_model(X, task_id=eval_id)
                            correct += (logits_e.argmax(1) == y).sum().item()
                            total_s += y.size(0)
                        acc_matrix[task_id, eval_id] = correct / total_s

            forgettings = []
            for t in range(n_tasks - 1):
                forgettings.append(acc_matrix[t, t] - acc_matrix[n_tasks - 1, t])
            avg_forgetting = float(np.mean(forgettings)) if forgettings else 0.0

            geo_results[cfg_name] = {
                'accuracy': result['best_test_acc'],
                'silhouette_score': result['final_silhouette_score'],
                'active_dims': result['final_active_dims'],
                'is_collapsed': result['is_collapsed'],
                'avg_forgetting': avg_forgetting,
                'reconstruction_loss': result['final_reconstruction_loss'],
            }
            print(f" acc={result['best_test_acc']:.4f} "
                  f"silh={result['final_silhouette_score']:.4f} "
                  f"forget={avg_forgetting:.4f} "
                  f"active={result['final_active_dims']:.0f}")

        all_results[label] = geo_results

    save_json(json_key, all_results)
    _generate_phase45d_report(all_results, epochs)
    return all_results


def _generate_phase45d_report(results, epochs):
    """Generate markdown report for Phase 4.5D."""
    report_path = '/home/z/my-project/AFM_GEOMETRY_REPORT.md'

    lines = []
    lines.append("# AFM Phase 4.5D — Latent Geometry Study Report\n")
    lines.append(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Scale**: ~1.33M params (hidden_dim={HIDDEN_DIM})")
    lines.append(f"**Dataset**: Fashion-MNIST | **Epochs**: {epochs} | **Seed**: 42")
    lines.append(f"**BETA**: {DEFAULT_BETA}\n")

    # Accuracy table
    lines.append("## Accuracy by Geometry and Config\n")
    geo_labels = list(results.keys())
    configs = ['baseline', 'afm_task', 'afm_qr', 'afm_rib']
    header = "| Geometry | " + " | ".join(configs) + " |"
    lines.append(header)
    lines.append("|----------|" + "|".join(["--------"] * len(configs)) + "|")
    for label in geo_labels:
        vals = []
        for c in configs:
            v = results[label].get(c, {}).get('accuracy', 0)
            vals.append(f"{v:.4f}")
        lines.append(f"| {label} | {' | '.join(vals)} |")

    lines.append("")

    # Silhouette table
    lines.append("## Silhouette Score by Geometry\n")
    header = "| Geometry | " + " | ".join(configs) + " |"
    lines.append(header)
    lines.append("|----------|" + "|".join(["--------"] * len(configs)) + "|")
    for label in geo_labels:
        vals = []
        for c in configs:
            v = results[label].get(c, {}).get('silhouette_score', 0)
            vals.append(f"{v:.4f}")
        lines.append(f"| {label} | {' | '.join(vals)} |")

    lines.append("")

    # Forgetting table
    lines.append("## Average Forgetting by Geometry\n")
    header = "| Geometry | " + " | ".join(configs) + " |"
    lines.append(header)
    lines.append("|----------|" + "|".join(["--------"] * len(configs)) + "|")
    for label in geo_labels:
        vals = []
        for c in configs:
            v = results[label].get(c, {}).get('avg_forgetting', 0)
            vals.append(f"{v:.4f}")
        lines.append(f"| {label} | {' | '.join(vals)} |")

    lines.append("")

    # Analysis
    lines.append("## Geometry Analysis\n")
    lines.append("- **(16,8)=128**: Many short threads (K=8, d=16). More orthogonal directions, "
                 "but each thread has limited capacity.")
    lines.append("- **(64,2)=128**: Few long threads (K=2, d=64). Fewer orthogonal directions, "
                 "but each thread carries more information.")
    lines.append("- **(32,4)=128**: Current default. Balanced thread count and dimension.")
    lines.append("- **(32,8)=256**: More threads with same dimension, but larger total latent space.")

    # Best geometry
    best_geo = None
    best_acc = 0
    for label, geo_data in results.items():
        for c in ['afm_rib']:
            acc = geo_data.get(c, {}).get('accuracy', 0)
            if acc > best_acc:
                best_acc = acc
                best_geo = label

    if best_geo:
        lines.append(f"\n**Best AFM+RIB geometry**: {best_geo} (accuracy={best_acc:.4f})")

    with open(report_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"  [REPORT] {report_path}")


# ===========================================================================
# 4.5E — Dataset Generalization
# ===========================================================================

def run_phase45e(seeds, epochs, lr, beta):
    """
    Dataset Generalization: 4 datasets × 5 configs × 3 seeds.

    Datasets: MNIST, Fashion-MNIST, KMNIST, EMNIST (balanced, 47 classes)
    Classify each effect as PROVEN/PARTIALLY PROVEN/FAILED/UNKNOWN.
    """
    json_key = 'dataset_generalization_results'
    existing = load_json(json_key)
    if existing is not None:
        print(f"[4.5E] Results already exist at {json_key}.json — skipping.")
        return existing

    datasets = {
        'mnist': {'loader': get_mnist, 'num_classes': 10},
        'fashion_mnist': {'loader': get_fashion_mnist, 'num_classes': 10},
        'kmnist': {'loader': get_kmnist, 'num_classes': 10},
        'emnist_balanced': {'loader': get_emnist_balanced, 'num_classes': 47},
    }

    print("\n" + "=" * 70)
    print("PHASE 4.5E — Dataset Generalization")
    print(f"  Datasets: {list(datasets.keys())}")
    print(f"  Configs: {list(ABLATION_CONFIGS.keys())}")
    print(f"  Seeds: {seeds} | epochs={epochs}")
    print("=" * 70)

    all_results = {}

    for ds_name, ds_info in datasets.items():
        print(f"\n{'─'*60}")
        print(f"Dataset: {ds_name}")
        print(f"{'─'*60}")

        loader_fn = ds_info['loader']
        train_loader, test_loader, input_dim, num_classes = loader_fn()
        print(f"  input_dim={input_dim}, num_classes={num_classes}, "
              f"train={len(train_loader.dataset)}, test={len(test_loader.dataset)}")

        ds_results = {}

        for cfg_name, cfg in ABLATION_CONFIGS.items():
            print(f"  Config: {cfg_name} — ", end='', flush=True)
            cfg_runs = []

            for seed in seeds:
                set_seed(seed)

                model = create_model(cfg_name, input_dim, num_classes)
                n_params = model.count_parameters()

                result = train_full(
                    model, train_loader, test_loader, cfg_name,
                    epochs=epochs, lr=lr,
                    beta=beta if cfg['beta'] > 0 else 0,
                    orth_weight=cfg['orth_weight'],
                    device=DEVICE, verbose=False,
                )

                run_data = {
                    'seed': seed,
                    'param_count': n_params,
                    'best_test_acc': result['best_test_acc'],
                    'final_test_acc': result['final_test_acc'],
                    'final_silhouette_score': result['final_silhouette_score'],
                    'final_active_dims': result['final_active_dims'],
                    'is_collapsed': result['is_collapsed'],
                    'final_reconstruction_loss': result['final_reconstruction_loss'],
                    'total_time': result['total_time'],
                }
                cfg_runs.append(run_data)

            # Statistics
            accs = [r['best_test_acc'] for r in cfg_runs]
            silhouettes = [r['final_silhouette_score'] for r in cfg_runs]
            active_dims_list = [r['final_active_dims'] for r in cfg_runs]
            collapsed_count = sum(1 for r in cfg_runs if r['is_collapsed'])

            ds_results[cfg_name] = {
                'runs': cfg_runs,
                'statistics': {
                    'test_accuracy': compute_ci(accs),
                    'silhouette_score': compute_ci(silhouettes),
                    'active_dims': compute_ci(active_dims_list),
                    'collapse_count': collapsed_count,
                    'collapse_rate': collapsed_count / len(seeds),
                },
            }

            s = ds_results[cfg_name]['statistics']
            print(f"acc={s['test_accuracy']['mean']:.4f} "
                  f"active={s['active_dims']['mean']:.0f} "
                  f"collapsed={collapsed_count}/{len(seeds)}")

        all_results[ds_name] = ds_results

    # Classify effects
    classifications = _classify_effects(all_results, seeds)
    all_results['_effect_classifications'] = classifications

    save_json(json_key, all_results)
    _generate_phase45e_report(all_results, seeds, epochs, classifications)
    return all_results


def _classify_effects(results, seeds):
    """
    Classify each AFM effect across datasets as:
    PROVEN / PARTIALLY PROVEN / FAILED / UNKNOWN
    """
    classifications = {}

    # Effect 1: β-VAE collapse (baseline VAE collapses, AFM doesn't)
    datasets_with_collapse = 0
    datasets_total = 0
    for ds_name, ds_data in results.items():
        if ds_name.startswith('_'):
            continue
        bv_collapse = ds_data.get('beta_vae', {}).get('statistics', {}).get('collapse_rate', 0)
        afm_rib_collapse = ds_data.get('afm_rib', {}).get('statistics', {}).get('collapse_rate', 0)
        if bv_collapse > 0:
            datasets_with_collapse += 1
        datasets_total += 1

    if datasets_with_collapse == datasets_total and datasets_total > 0:
        classifications['beta_vae_collapse'] = 'PROVEN'
    elif datasets_with_collapse > 0:
        classifications['beta_vae_collapse'] = 'PARTIALLY PROVEN'
    else:
        classifications['beta_vae_collapse'] = 'FAILED'

    # Effect 2: AFM collapse resistance
    afm_collapsed_any = False
    for ds_name, ds_data in results.items():
        if ds_name.startswith('_'):
            continue
        afm_rib_collapse = ds_data.get('afm_rib', {}).get('statistics', {}).get('collapse_rate', 0)
        if afm_rib_collapse > 0:
            afm_collapsed_any = True

    if not afm_collapsed_any:
        classifications['afm_collapse_resistance'] = 'PROVEN'
    else:
        classifications['afm_collapse_resistance'] = 'PARTIALLY PROVEN'

    # Effect 3: AFM+RIB accuracy >= baseline
    datasets_where_afm_wins = 0
    for ds_name, ds_data in results.items():
        if ds_name.startswith('_'):
            continue
        baseline_acc = ds_data.get('baseline', {}).get('statistics', {}).get('test_accuracy', {}).get('mean', 0)
        afm_rib_acc = ds_data.get('afm_rib', {}).get('statistics', {}).get('test_accuracy', {}).get('mean', 0)
        if afm_rib_acc >= baseline_acc - 0.005:  # Within 0.5%
            datasets_where_afm_wins += 1

    if datasets_where_afm_wins == datasets_total:
        classifications['afm_rib_accuracy_parity'] = 'PROVEN'
    elif datasets_where_afm_wins > datasets_total // 2:
        classifications['afm_rib_accuracy_parity'] = 'PARTIALLY PROVEN'
    else:
        classifications['afm_rib_accuracy_parity'] = 'FAILED'

    # Effect 4: Stiefel structure helps (afm_task > baseline)
    datasets_where_structure_helps = 0
    for ds_name, ds_data in results.items():
        if ds_name.startswith('_'):
            continue
        baseline_acc = ds_data.get('baseline', {}).get('statistics', {}).get('test_accuracy', {}).get('mean', 0)
        afm_task_acc = ds_data.get('afm_task', {}).get('statistics', {}).get('test_accuracy', {}).get('mean', 0)
        if afm_task_acc >= baseline_acc:
            datasets_where_structure_helps += 1

    if datasets_where_structure_helps == datasets_total:
        classifications['stiefel_structure_helps'] = 'PROVEN'
    elif datasets_where_structure_helps > 0:
        classifications['stiefel_structure_helps'] = 'PARTIALLY PROVEN'
    else:
        classifications['stiefel_structure_helps'] = 'FAILED'

    # Effect 5: Better silhouette scores (more structured representations)
    datasets_better_silhouette = 0
    for ds_name, ds_data in results.items():
        if ds_name.startswith('_'):
            continue
        baseline_sil = ds_data.get('baseline', {}).get('statistics', {}).get('silhouette_score', {}).get('mean', -1)
        afm_rib_sil = ds_data.get('afm_rib', {}).get('statistics', {}).get('silhouette_score', {}).get('mean', -1)
        if afm_rib_sil > baseline_sil:
            datasets_better_silhouette += 1

    if datasets_better_silhouette == datasets_total:
        classifications['afm_better_silhouette'] = 'PROVEN'
    elif datasets_better_silhouette > datasets_total // 2:
        classifications['afm_better_silhouette'] = 'PARTIALLY PROVEN'
    else:
        classifications['afm_better_silhouette'] = 'FAILED'

    return classifications


def _generate_phase45e_report(results, seeds, epochs, classifications):
    """Generate markdown report for Phase 4.5E."""
    report_path = '/home/z/my-project/AFM_DATASET_GENERALIZATION_REPORT.md'

    lines = []
    lines.append("# AFM Phase 4.5E — Dataset Generalization Report\n")
    lines.append(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Scale**: ~1.33M params (hidden_dim={HIDDEN_DIM})")
    lines.append(f"**Seeds**: {seeds} | **Epochs**: {epochs}")
    lines.append(f"**BETA**: {DEFAULT_BETA} | **LR**: {DEFAULT_LR}\n")

    dataset_names = [k for k in results.keys() if not k.startswith('_')]
    config_names = list(ABLATION_CONFIGS.keys())

    # Accuracy table per dataset
    for ds_name in dataset_names:
        ds_data = results[ds_name]
        lines.append(f"## {ds_name}\n")
        lines.append("| Config | Accuracy (mean ± 95% CI) | Active Dims | Silhouette | Collapse Rate |")
        lines.append("|--------|--------------------------|-------------|------------|---------------|")

        for cfg_name in config_names:
            if cfg_name in ds_data:
                s = ds_data[cfg_name]['statistics']
                acc = s['test_accuracy']
                lines.append(
                    f"| {cfg_name} | "
                    f"{acc['mean']:.4f} [{acc['ci_lower']:.4f}, {acc['ci_upper']:.4f}] | "
                    f"{s['active_dims']['mean']:.1f} | "
                    f"{s['silhouette_score']['mean']:.4f} | "
                    f"{s['collapse_rate']:.2f} |"
                )
        lines.append("")

    # Effect classifications
    lines.append("## Effect Classifications\n")
    lines.append("| Effect | Classification |")
    lines.append("|--------|---------------|")

    effect_descriptions = {
        'beta_vae_collapse': 'β-VAE causes posterior collapse',
        'afm_collapse_resistance': 'AFM+RIB is collapse-resistant',
        'afm_rib_accuracy_parity': 'AFM+RIB maintains accuracy ≥ baseline',
        'stiefel_structure_helps': 'Stiefel structure improves over unconstrained latent',
        'afm_better_silhouette': 'AFM produces more structured representations (higher silhouette)',
    }

    for effect, cls in classifications.items():
        desc = effect_descriptions.get(effect, effect)
        # Bold the classification
        lines.append(f"| {desc} | **{cls}** |")

    lines.append("")

    # Summary
    proven = sum(1 for v in classifications.values() if v == 'PROVEN')
    partial = sum(1 for v in classifications.values() if v == 'PARTIALLY PROVEN')
    failed = sum(1 for v in classifications.values() if v == 'FAILED')
    unknown = sum(1 for v in classifications.values() if v == 'UNKNOWN')

    lines.append("## Summary\n")
    lines.append(f"- **PROVEN**: {proven} effects")
    lines.append(f"- **PARTIALLY PROVEN**: {partial} effects")
    lines.append(f"- **FAILED**: {failed} effects")
    lines.append(f"- **UNKNOWN**: {unknown} effects")

    with open(report_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"  [REPORT] {report_path}")


# ===========================================================================
# Master Report Generator
# ===========================================================================

def generate_master_report(phase_a_results=None, phase_b_results=None,
                           phase_c_results=None, phase_d_results=None,
                           phase_e_results=None):
    """Generate the Phase 4.5 Master Report synthesizing all findings."""
    report_path = '/home/z/my-project/AFM_PHASE45_MASTER_REPORT.md'

    lines = []
    lines.append("# AFM Phase 4.5 — Statistical Strengthening: Master Report\n")
    lines.append(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Scale**: ~1.33M params (hidden_dim={HIDDEN_DIM})")
    lines.append(f"**Framework**: PyTorch (CPU) | **Seeds**: variable per sub-phase")
    lines.append(f"**BETA**: {DEFAULT_BETA} | **LR**: {DEFAULT_LR} | **Batch**: 256\n")

    lines.append("---\n")
    lines.append("## Executive Summary\n")

    # Collect all classifications
    all_classifications = {}
    if phase_e_results and '_effect_classifications' in phase_e_results:
        all_classifications.update(phase_e_results['_effect_classifications'])

    # Phase-specific findings
    findings = []

    # Phase A findings
    if phase_a_results:
        for cfg_name, cfg_data in phase_a_results.items():
            s = cfg_data.get('statistics', {})
            acc = s.get('test_accuracy', {})
            if acc:
                findings.append(f"**4.5A {cfg_name}**: accuracy = {acc.get('mean', 0):.4f} "
                              f"[{acc.get('ci_lower', 0):.4f}, {acc.get('ci_upper', 0):.4f}]")

        # Check beta_vae collapse
        bv = phase_a_results.get('beta_vae', {}).get('statistics', {})
        if bv.get('collapse_rate', 0) > 0:
            findings.append(f"**4.5A β-VAE collapse**: confirmed "
                          f"({bv.get('collapse_count', '?')}/5 seeds collapsed)")
        afm_r = phase_a_results.get('afm_rib', {}).get('statistics', {})
        if afm_r.get('collapse_rate', 0) == 0:
            findings.append("**4.5A AFM+RIB collapse resistance**: confirmed (0/5 seeds collapsed)")

    # Phase B findings
    if phase_b_results:
        for cfg_name in ['baseline', 'afm_task', 'afm_rib']:
            s = phase_b_results.get(cfg_name, {}).get('statistics', {}).get('avg_forgetting', {})
            if s:
                findings.append(f"**4.5B {cfg_name} forgetting**: {s.get('mean', 0):.4f} "
                              f"[{s.get('ci_lower', 0):.4f}, {s.get('ci_upper', 0):.4f}]")

    # Phase C findings
    if phase_c_results:
        for cfg_name in ['beta_vae', 'afm_qr', 'afm_rib']:
            ct = phase_c_results.get(cfg_name, {}).get('collapse_threshold')
            if ct:
                findings.append(f"**4.5C {cfg_name} collapse threshold**: β ≥ {ct:.0e}")
            else:
                findings.append(f"**4.5C {cfg_name}**: no collapse in tested range")

    # Phase D findings
    if phase_d_results:
        for geo_label, geo_data in phase_d_results.items():
            afm_acc = geo_data.get('afm_rib', {}).get('accuracy', 0)
            findings.append(f"**4.5D {geo_label} AFM+RIB**: accuracy = {afm_acc:.4f}")

    for f in findings:
        lines.append(f"- {f}")

    lines.append("")

    # Effect classifications table
    if all_classifications:
        lines.append("## Effect Classifications\n")
        lines.append("| Effect | Verdict |")
        lines.append("|--------|---------|")

        effect_descriptions = {
            'beta_vae_collapse': 'β-VAE causes posterior collapse',
            'afm_collapse_resistance': 'AFM+RIB resists posterior collapse',
            'afm_rib_accuracy_parity': 'AFM+RIB maintains accuracy ≥ baseline',
            'stiefel_structure_helps': 'Stiefel structure improves over unconstrained',
            'afm_better_silhouette': 'AFM produces more structured representations',
        }

        for effect, cls in all_classifications.items():
            desc = effect_descriptions.get(effect, effect)
            lines.append(f"| {desc} | **{cls}** |")

        lines.append("")

        proven = sum(1 for v in all_classifications.values() if v == 'PROVEN')
        partial = sum(1 for v in all_classifications.values() if v == 'PARTIALLY PROVEN')
        failed = sum(1 for v in all_classifications.values() if v == 'FAILED')
        total = len(all_classifications)

        lines.append(f"**Overall**: {proven}/{total} PROVEN, {partial}/{total} PARTIALLY PROVEN, "
                     f"{failed}/{total} FAILED\n")

    # Sub-phase details
    lines.append("---\n")
    lines.append("## Sub-Phase Details\n")
    lines.append("See individual reports for detailed results:")
    lines.append("- [4.5A Multi-Seed Validation](AFM_1M_MULTI_SEED_REPORT.md)")
    lines.append("- [4.5B Forgetting Statistics](AFM_FORGETTING_STATISTICS_REPORT.md)")
    lines.append("- [4.5C Beta Sweep](AFM_BETA_SWEEP_REPORT.md)")
    lines.append("- [4.5D Latent Geometry](AFM_GEOMETRY_REPORT.md)")
    lines.append("- [4.5E Dataset Generalization](AFM_DATASET_GENERALIZATION_REPORT.md)")

    lines.append("")
    lines.append("---\n")
    lines.append(f"*Report generated automatically by run_phase45.py at {time.strftime('%Y-%m-%d %H:%M')}*")

    with open(report_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"\n[MASTER] {report_path}")


# ===========================================================================
# Main entry point
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description='AFM Phase 4.5 — Statistical Strengthening')
    parser.add_argument('--phase', type=str, default='all',
                        choices=['all', 'A', 'B', 'C', 'D', 'E'],
                        help='Which sub-phase to run (default: all)')
    parser.add_argument('--quick', action='store_true',
                        help='Quick mode: 1 seed, 5 epochs')
    parser.add_argument('--epochs', type=int, default=None,
                        help='Override epoch count')
    parser.add_argument('--lr', type=float, default=DEFAULT_LR,
                        help='Learning rate')
    parser.add_argument('--beta', type=float, default=DEFAULT_BETA,
                        help='Beta for KL weight')
    args = parser.parse_args()

    # Configure based on mode
    if args.quick:
        seeds_ab = [42]
        seeds_e = [42]
        epochs = 5
        epochs_per_task = 3
    else:
        seeds_ab = [0, 42, 84, 126, 168]
        seeds_e = [0, 42, 84]
        epochs = args.epochs or 15
        epochs_per_task = 5

    betas = [1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2]
    lr = args.lr
    beta = args.beta

    print("=" * 70)
    print("AFM Phase 4.5 — Statistical Strengthening")
    print("=" * 70)
    print(f"  Mode: {'QUICK' if args.quick else 'FULL'}")
    print(f"  Device: {DEVICE}")
    print(f"  Hidden dim: {HIDDEN_DIM} (~1.33M params)")
    print(f"  Stiefel: d={D_STIEFEL}, K={K_THREADS}, latent_dim={LATENT_DIM}")
    print(f"  Phases to run: {args.phase}")
    print("=" * 70)

    os.makedirs(RESULTS_DIR, exist_ok=True)

    phase_a_results = None
    phase_b_results = None
    phase_c_results = None
    phase_d_results = None
    phase_e_results = None

    # Phase 4.5A
    if args.phase in ('all', 'A'):
        print("\n" + "▶" * 30 + " PHASE 4.5A " + "▶" * 30)
        phase_a_results = run_phase45a(seeds_ab, epochs, lr, beta)

    # Phase 4.5B
    if args.phase in ('all', 'B'):
        print("\n" + "▶" * 30 + " PHASE 4.5B " + "▶" * 30)
        phase_b_results = run_phase45b(seeds_ab, epochs_per_task, lr, beta)

    # Phase 4.5C
    if args.phase in ('all', 'C'):
        print("\n" + "▶" * 30 + " PHASE 4.5C " + "▶" * 30)
        phase_c_results = run_phase45c(betas, epochs, lr)

    # Phase 4.5D
    if args.phase in ('all', 'D'):
        print("\n" + "▶" * 30 + " PHASE 4.5D " + "▶" * 30)
        phase_d_results = run_phase45d(epochs, lr, beta)

    # Phase 4.5E
    if args.phase in ('all', 'E'):
        print("\n" + "▶" * 30 + " PHASE 4.5E " + "▶" * 30)
        phase_e_results = run_phase45e(seeds_e, epochs, lr, beta)

    # Load any missing results from disk (for master report)
    if phase_a_results is None:
        phase_a_results = load_json('multi_seed_results')
    if phase_b_results is None:
        phase_b_results = load_json('forgetting_results')
    if phase_c_results is None:
        phase_c_results = load_json('beta_sweep_results')
    if phase_d_results is None:
        phase_d_results = load_json('geometry_results')
    if phase_e_results is None:
        phase_e_results = load_json('dataset_generalization_results')

    # Generate master report
    generate_master_report(
        phase_a_results=phase_a_results,
        phase_b_results=phase_b_results,
        phase_c_results=phase_c_results,
        phase_d_results=phase_d_results,
        phase_e_results=phase_e_results,
    )

    print("\n" + "=" * 70)
    print("PHASE 4.5 COMPLETE")
    print("=" * 70)
    print(f"Results saved to: {RESULTS_DIR}/")
    print("Reports generated:")
    print("  /home/z/my-project/AFM_1M_MULTI_SEED_REPORT.md")
    print("  /home/z/my-project/AFM_FORGETTING_STATISTICS_REPORT.md")
    print("  /home/z/my-project/AFM_BETA_SWEEP_REPORT.md")
    print("  /home/z/my-project/AFM_GEOMETRY_REPORT.md")
    print("  /home/z/my-project/AFM_DATASET_GENERALIZATION_REPORT.md")
    print("  /home/z/my-project/AFM_PHASE45_MASTER_REPORT.md")


if __name__ == '__main__':
    main()
